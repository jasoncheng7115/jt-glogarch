"""Import orchestrator — reads archives and sends to Graylog via GELF.

Supports:
- Pause/resume
- Adjustable speed rate (real-time)
- Journal monitoring (API or SSH) for dynamic rate control
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Callable

from glogarch.archive.integrity import verify_file
from glogarch.archive.storage import ArchiveStorage
from glogarch.core.config import ExportConfig, ImportConfig
from glogarch.core.database import ArchiveDB
from glogarch.core.models import (
    ArchiveStatus,
    ImportHistoryRecord,
    JobRecord,
    JobStatus,
    JobType,
)
from glogarch.gelf.sender import GelfSender
from glogarch.import_.bulk import BulkImporter, BulkImportResult
from glogarch.import_.journal_monitor import JournalMonitor, JournalStatus
from glogarch.import_.preflight import PreflightChecker, PreflightResult
from glogarch.utils.logging import get_logger

log = get_logger("import")


class ImportFlowControl:
    """Runtime flow control state for an import job — shared with API endpoints."""

    def __init__(self):
        self.paused = False
        self.cancelled = False
        self.rate_ms: int = 100  # delay between batches in ms
        self.batch_size: int = 500
        self.auto_rate: bool = False  # True if journal monitoring controls rate
        self._base_rate_ms: int = 100  # user-set rate before auto adjustment
        self.journal_status: JournalStatus | None = None
        self.journal_action: str = "normal"

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def cancel(self):
        self.cancelled = True

    def set_rate(self, rate_ms: int, batch_size: int | None = None):
        self.rate_ms = max(1, rate_ms)
        self._base_rate_ms = self.rate_ms
        if batch_size is not None:
            self.batch_size = max(1, batch_size)

    def get_effective_delay(self) -> int:
        """Get current delay in ms, considering auto-rate from journal monitoring."""
        if not self.auto_rate:
            return self.rate_ms
        if self.journal_action == "slow":
            return max(self._base_rate_ms * 3, 500)
        elif self.journal_action == "pause":
            return 30_000  # 30 seconds
        return self._base_rate_ms


# Global registry of active import flow controls
_import_controls: dict[str, ImportFlowControl] = {}


def get_import_control(job_id: str) -> ImportFlowControl | None:
    return _import_controls.get(job_id)


class ImportResult:
    """Result of an import operation."""

    def __init__(self):
        self.archives_processed: int = 0
        self.messages_sent: int = 0
        self.errors: list[str] = []
        self.job_id: str = ""


class Importer:
    """Orchestrates importing archived logs back into Graylog.

    Two modes:
        gelf  — sends each message via GELF TCP/UDP. Goes through Graylog's
                full processing chain (input → process → indexer). Slower but
                preserves all Graylog processing semantics (pipelines,
                extractors, stream routing, alerts).
        bulk  — writes each message directly to OpenSearch via _bulk API,
                bypassing Graylog entirely. 5-10x faster, no journal pressure,
                no alert side effects, but skips ALL Graylog processing.
    """

    def __init__(
        self,
        import_config: ImportConfig,
        export_config: ExportConfig,
        db: ArchiveDB,
        journal_monitor: JournalMonitor | None = None,
        preflight: PreflightChecker | None = None,
        mode: str = "gelf",
        bulk_importer: BulkImporter | None = None,
    ):
        self.import_config = import_config
        self.export_config = export_config
        self.storage = ArchiveStorage(export_config)
        self.db = db
        self.journal_monitor = journal_monitor
        self.preflight = preflight
        self.mode = mode  # "gelf" or "bulk"
        self.bulk_importer = bulk_importer

    async def import_archives(
        self,
        archive_ids: list[int] | None = None,
        time_from: datetime | None = None,
        time_to: datetime | None = None,
        server_name: str | None = None,
        target_server: str | None = None,
        progress_callback: Callable[[dict], None] | None = None,
        job_id: str | None = None,
        flow_control: ImportFlowControl | None = None,
    ) -> ImportResult:
        """Import archived messages into Graylog.

        Args:
            archive_ids: Specific archive IDs to import.
            time_from/time_to: Time range filter (alternative to IDs).
            server_name: Server filter.
            target_server: Descriptive name for tracking.
            progress_callback: Progress updates.
            job_id: Reuse existing job ID (from Web UI).
            flow_control: Shared flow control for pause/resume/rate.
        """
        result = ImportResult()
        job_id = job_id or str(uuid.uuid4())
        result.job_id = job_id

        fc = flow_control or ImportFlowControl()
        fc.rate_ms = self.import_config.delay_between_batches_ms
        fc.batch_size = self.import_config.batch_size
        fc._base_rate_ms = fc.rate_ms

        # Register flow control globally
        _import_controls[job_id] = fc

        job = JobRecord(id=job_id, job_type=JobType.IMPORT, status=JobStatus.RUNNING,
                        started_at=datetime.utcnow())
        self.db.create_job(job)

        try:
            # Resolve archives
            if archive_ids:
                archives = []
                for aid in archive_ids:
                    rec = self.db.get_archive(aid)
                    if rec and rec.status == ArchiveStatus.COMPLETED:
                        archives.append(rec)
                    else:
                        log.warning("Archive not found or not completed", archive_id=aid)
            else:
                archives = self.db.list_archives(
                    server=server_name, time_from=time_from, time_to=time_to,
                    status=ArchiveStatus.COMPLETED,
                )

            if not archives:
                log.info("No archives to import")
                self.db.update_job(job_id, status=JobStatus.COMPLETED,
                                   completed_at=datetime.utcnow())
                return result

            total_archives = len(archives)
            total_messages = sum(a.message_count for a in archives)
            self.db.update_job(job_id, messages_total=total_messages)

            log.info("Import started", job_id=job_id, archives=total_archives,
                     total_messages=total_messages)

            # === Preflight: detect & fix mapping conflicts BEFORE any GELF send ===
            preflight_result: PreflightResult | None = None
            if self.preflight is not None:
                if progress_callback:
                    progress_callback({
                        "phase": "preflight",
                        "messages_done": 0,
                        "messages_total": total_messages,
                        "pct": 0,
                    })
                pf_ids = [a.id for a in archives if a.id is not None]
                # Estimate total bytes from archive original_size_bytes (uncompressed
                # size, closer to what Graylog will store after re-indexing)
                pf_total_bytes = sum(a.original_size_bytes or 0 for a in archives)
                # For bulk mode pass through OpenSearch URL/creds + target pattern
                # so preflight can write the OpenSearch template + create the
                # Graylog index set.
                pf_kwargs = {
                    "total_messages": total_messages,
                    "total_bytes": pf_total_bytes,
                    "mode": self.mode,
                }
                if self.mode == "bulk" and self.bulk_importer:
                    pf_kwargs["bulk_opensearch_url"] = self.bulk_importer.opensearch_url
                    pf_kwargs["bulk_os_username"] = self.bulk_importer.os_username
                    pf_kwargs["bulk_os_password"] = self.bulk_importer.os_password
                    pf_kwargs["bulk_target_pattern"] = self.bulk_importer.target_index_pattern
                preflight_result = await self.preflight.run(
                    self.db, pf_ids, **pf_kwargs,
                )
                if preflight_result.aborted:
                    err = f"Preflight aborted: {preflight_result.error}"
                    log.error(err)
                    self.db.update_job(
                        job_id, status=JobStatus.FAILED,
                        error_message=err,
                        completed_at=datetime.utcnow(),
                    )
                    result.errors.append(err)
                    return result
                log.info(
                    "Preflight passed",
                    duration=f"{preflight_result.duration_sec:.1f}s",
                    fields=preflight_result.fields_total,
                    fixed=len(preflight_result.fields_set_keyword),
                    rotated=preflight_result.rotated,
                )

            # === BULK MODE BRANCH ===
            # Direct OpenSearch _bulk write, bypassing Graylog entirely.
            if self.mode == "bulk":
                if not self.bulk_importer:
                    raise RuntimeError("mode='bulk' but no bulk_importer provided")
                from pathlib import Path as _P
                paths = [_P(a.file_path) for a in archives]

                def _bulk_cb(info):
                    if fc.cancelled:
                        raise RuntimeError("Job cancelled by user")
                    if progress_callback:
                        progress_callback(info)
                    # Update DB job progress periodically
                    self.db.update_job(
                        job_id,
                        progress_pct=min(info.get("pct", 0), 99),
                        messages_done=info.get("messages_done", 0),
                    )

                bulk_result = await self.bulk_importer.import_archives(
                    paths, progress_callback=_bulk_cb,
                )
                result.archives_processed = bulk_result.archives_processed
                result.messages_sent = bulk_result.messages_sent

                # Build precise reconciliation report from bulk response
                if bulk_result.messages_failed > 0:
                    msg = (
                        f"Compliance violation: {bulk_result.messages_failed} of "
                        f"{bulk_result.messages_sent:,} messages failed to index. "
                        f"Sample errors: " + " | ".join(bulk_result.failure_samples[:5])
                    )
                    log.warning(msg)
                    result.errors.append(msg)
                    self.db.update_job(
                        job_id, status=JobStatus.COMPLETED, progress_pct=100.0,
                        messages_done=bulk_result.messages_indexed,
                        completed_at=datetime.utcnow(),
                        error_message=msg,
                    )
                else:
                    log.info(
                        "Bulk reconciliation OK: 0 failed",
                        sent=bulk_result.messages_sent,
                        indexed=bulk_result.messages_indexed,
                    )
                    self.db.update_job(
                        job_id, status=JobStatus.COMPLETED, progress_pct=100.0,
                        messages_done=bulk_result.messages_indexed,
                        completed_at=datetime.utcnow(),
                    )

                try:
                    from glogarch.notify.sender import notify_import_complete
                    await notify_import_complete(
                        result.archives_processed, result.messages_sent, result.errors,
                    )
                except Exception:
                    pass
                return result

            # === GELF MODE (default) ===
            gelf_host = self.import_config.gelf_host
            gelf_port = self.import_config.gelf_port
            gelf_protocol = getattr(self.import_config, 'gelf_protocol', 'udp')

            check_interval = 0  # counter for journal checks

            async with GelfSender(gelf_host, gelf_port, protocol=gelf_protocol) as sender:
                for arch_idx, archive in enumerate(archives):
                    if fc.cancelled:
                        log.info("Import cancelled by user")
                        break

                    # Verify integrity
                    is_valid, actual_checksum = verify_file(
                        archive.file_path, archive.checksum_sha256
                    )
                    if not is_valid:
                        err = f"Integrity check failed for archive {archive.id}: {archive.file_path}"
                        log.error(err)
                        result.errors.append(err)
                        continue

                    # Stream-read archive
                    try:
                        archive_iter = self.storage.iter_archive(
                            archive.file_path, batch_size=fc.batch_size,
                        )
                    except Exception as e:
                        err = f"Failed to read archive {archive.id}: {e}"
                        log.error(err)
                        result.errors.append(err)
                        continue

                    self.db.update_archive_status(archive.id, ArchiveStatus.IMPORTING)

                    sent = 0
                    try:
                        for msg_batch in archive_iter:
                            # --- Pause loop ---
                            while fc.paused and not fc.cancelled:
                                await asyncio.sleep(0.5)
                                if progress_callback:
                                    progress_callback({
                                        "phase": "paused",
                                        "archive_index": arch_idx + 1,
                                        "total_archives": total_archives,
                                        "messages_done": result.messages_sent + sent,
                                        "messages_total": total_messages,
                                        "pct": ((result.messages_sent + sent) / max(total_messages, 1)) * 100,
                                        "journal_action": fc.journal_action,
                                    })

                            if fc.cancelled:
                                break

                            # --- Journal monitoring ---
                            check_interval += 1
                            if self.journal_monitor and check_interval % 10 == 0:
                                status = await self.journal_monitor.check()
                                fc.journal_status = status
                                action = self.journal_monitor.recommend_action(status)
                                fc.journal_action = action
                                fc.auto_rate = True

                                if action == "stop":
                                    log.error("Journal overflow, stopping import",
                                              uncommitted=status.uncommitted)
                                    try:
                                        from glogarch.notify.sender import notify_error
                                        await notify_error("Import",
                                            f"Graylog journal overflow: {status.uncommitted:,} uncommitted entries. "
                                            f"Import stopped to prevent data loss.")
                                    except Exception:
                                        pass
                                    raise RuntimeError(
                                        f"Graylog journal overflow ({status.uncommitted:,} uncommitted). "
                                        f"Import stopped.")

                                if action == "pause":
                                    log.warning("Journal high, pausing import",
                                                uncommitted=status.uncommitted)
                                    # Auto-pause for 30s
                                    await asyncio.sleep(30)
                                    continue  # Re-check after pause

                            # --- Send batch ---
                            batch_sent = await sender.send_batch(
                                messages=msg_batch,
                                batch_size=fc.batch_size,
                                delay_ms=fc.get_effective_delay(),
                            )
                            sent += batch_sent

                            if progress_callback:
                                progress_callback({
                                    "phase": "sending",
                                    "archive_index": arch_idx + 1,
                                    "total_archives": total_archives,
                                    "messages_done": result.messages_sent + sent,
                                    "messages_total": total_messages,
                                    "pct": ((result.messages_sent + sent) / max(total_messages, 1)) * 100,
                                    "rate_ms": fc.get_effective_delay(),
                                    "journal_action": fc.journal_action,
                                })

                    except Exception as e:
                        err = f"Import failed for archive {archive.id}: {e}"
                        log.error(err)
                        result.errors.append(err)
                    finally:
                        self.db.update_archive_status(archive.id, ArchiveStatus.COMPLETED)

                    result.messages_sent += sent
                    result.archives_processed += 1

                    self.db.record_import(ImportHistoryRecord(
                        archive_id=archive.id,
                        target_server=target_server or gelf_host,
                        messages_sent=sent,
                        job_id=job_id,
                    ))

                    self.db.update_job(job_id, messages_done=result.messages_sent,
                                       progress_pct=(result.messages_sent / max(total_messages, 1)) * 100)

            # === Post-import reconciliation: zero indexer failures required ===
            final_status = JobStatus.COMPLETED
            recon_msg = ""
            if self.preflight is not None and preflight_result is not None:
                # Give Graylog a moment to flush remaining buffered messages
                await asyncio.sleep(5)
                try:
                    after = await self.preflight.get_indexer_failures_count()
                    delta = after - preflight_result.indexer_failures_baseline
                    if delta > 0:
                        recon_msg = (
                            f"Compliance violation: {delta} indexer failures occurred "
                            f"during this import (baseline {preflight_result.indexer_failures_baseline} "
                            f"-> after {after}). Sent: {result.messages_sent:,}. "
                            f"Check Graylog System / Indices / Indexer failures for details."
                        )
                        log.warning(recon_msg)
                        result.errors.append(recon_msg)
                        # Mark as completed_with_failures via error_message
                        final_status = JobStatus.COMPLETED
                    else:
                        log.info(
                            "Reconciliation OK: 0 indexer failures",
                            sent=result.messages_sent,
                            failures_before=preflight_result.indexer_failures_baseline,
                            failures_after=after,
                        )
                except Exception as e:
                    log.warning("Post-import reconciliation failed", error=str(e))

            self.db.update_job(
                job_id, status=final_status, progress_pct=100.0,
                messages_done=result.messages_sent, completed_at=datetime.utcnow(),
                error_message=recon_msg or None,
            )
            log.info("Import completed", job_id=job_id,
                     archives=result.archives_processed, messages=result.messages_sent)

            try:
                from glogarch.notify.sender import notify_import_complete
                await notify_import_complete(
                    result.archives_processed, result.messages_sent, result.errors,
                )
            except Exception:
                pass

        except Exception as e:
            self.db.update_job(job_id, status=JobStatus.FAILED,
                               error_message=str(e), completed_at=datetime.utcnow())
            result.errors.append(str(e))
            log.error("Import failed", job_id=job_id, error=str(e))
            try:
                from glogarch.notify.sender import notify_error
                await notify_error("Import", str(e))
            except Exception:
                pass
            raise
        finally:
            _import_controls.pop(job_id, None)

        return result
