"""Import orchestrator — reads archives and sends to Graylog via GELF.

Supports:
- Pause/resume
- Adjustable speed rate (real-time)
- Journal monitoring (API or SSH) for dynamic rate control
"""

from __future__ import annotations

import asyncio
import time as _time
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
        self.mem_available_mb: float | None = None  # local box MemAvailable (OOM guard)

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


# Global registry of in-flight archive imports — prevents the same archive
# from being imported by two concurrent jobs (e.g. user clicks Import in two
# browser tabs, or schedule + manual click race). Maps archive_id → job_id.
import threading as _threading
_active_archive_imports: dict[int, str] = {}
_active_archive_lock = _threading.Lock()


def _claim_archives(archive_ids: list[int], job_id: str) -> list[int]:
    """Try to claim ``archive_ids`` for ``job_id``. Returns the list of IDs
    that were already locked by another job (the conflicts)."""
    conflicts: list[int] = []
    with _active_archive_lock:
        for aid in archive_ids:
            owner = _active_archive_imports.get(aid)
            if owner and owner != job_id:
                conflicts.append(aid)
        if not conflicts:
            for aid in archive_ids:
                _active_archive_imports[aid] = job_id
    return conflicts


def _release_archives(archive_ids: list[int], job_id: str) -> None:
    with _active_archive_lock:
        for aid in archive_ids:
            if _active_archive_imports.get(aid) == job_id:
                _active_archive_imports.pop(aid, None)


class ImportResult:
    """Result of an import operation."""

    def __init__(self):
        self.archives_processed: int = 0
        self.messages_sent: int = 0
        self.errors: list[str] = []
        self.notices: list[str] = []  # informational messages (e.g. "find your data in stream X")
        self.job_id: str = ""
        self.duration_seconds: float = 0.0
        self.indexer_failure_fields: list[str] = []  # fields auto-diagnosed on failure
        self.messages_indexed: int = 0  # destination-verified: sent - indexer failures


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

    async def _mid_import_remediate(self, preflight_result, result, baseline: int) -> int:
        """Poll the target's indexer-failure count DURING the import; on a rise,
        diagnose the offending field(s), pin them as string and cycle the index
        so the REST of the import indexes cleanly — instead of losing every
        conflicting message and only fixing the mapping after the whole run.

        Returns the updated baseline. GELF is fire-and-forget (no per-message
        ack), so the handful sent-and-failed BEFORE detection aren't recovered
        here — post-import reconciliation + the one-click retry cover those. Only
        NEW fields (not already pinned this run) trigger a cycle, so an
        already-fixed field's in-flight stragglers don't re-cycle repeatedly."""
        if self.preflight is None or preflight_result is None or not preflight_result.index_set_id:
            return baseline
        try:
            cur = await self.preflight.get_indexer_failures_count()
        except Exception:
            return baseline
        if cur <= baseline:
            return baseline
        try:
            details = await self.preflight.get_indexer_failure_details()
            fields = list(details.get("fields", {}).keys())
            new_fields = [f for f in fields if f not in result.indexer_failure_fields]
            if new_fields:
                await self.preflight.remediate_fields_as_string(
                    preflight_result.index_set_id, new_fields)
                try:
                    await self.preflight.wait_for_index_ready(
                        preflight_result.index_set_id, timeout_sec=20)
                except Exception:
                    pass
                result.indexer_failure_fields.extend(new_fields)
                log.warning("Mid-import auto-remediation applied",
                            fields=new_fields, failures_delta=cur - baseline)
        except Exception as e:
            log.warning("Mid-import remediation failed", error=str(e))
        return cur

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
        job_config: dict | None = None,
        ignore_capacity: bool = False,
        estimated_indices: int = 0,
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
        _start_time = _time.time()

        fc = flow_control or ImportFlowControl()
        # Only seed rate/batch from config when the CALLER did not provide a flow
        # control. The Web UI path (web/routes/api.py) creates the fc and sets
        # rate_ms/batch_size from the import dialog BEFORE passing it in; blindly
        # overwriting here clobbered the user's chosen batch (e.g. 50 -> config
        # default 500) and rate, so the dialog values were silently ignored.
        if flow_control is None:
            fc.rate_ms = self.import_config.delay_between_batches_ms
            fc.batch_size = self.import_config.batch_size
        fc._base_rate_ms = fc.rate_ms

        # Register flow control globally
        _import_controls[job_id] = fc

        # Persist the retry params (archives + target, NEVER secrets) so a failed
        # import can be re-run with one click after auto-remediation.
        import json as _json_cfg
        job = JobRecord(id=job_id, job_type=JobType.IMPORT, status=JobStatus.RUNNING,
                        started_at=datetime.utcnow(),
                        config_json=_json_cfg.dumps(job_config) if job_config else None)
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

            # === Concurrency lock: prevent two jobs from importing the same
            # archive simultaneously (two browser tabs, schedule + manual,
            # CLI + Web UI). Conflicts → fail fast with a clear error.
            claim_ids = [a.id for a in archives if a.id is not None]
            conflicts = _claim_archives(claim_ids, job_id)
            if conflicts:
                err = (
                    f"Archive(s) {conflicts} are already being imported by "
                    "another job. Wait for it to finish or cancel it first."
                )
                log.warning(err)
                self.db.update_job(
                    job_id, status=JobStatus.FAILED,
                    error_message=err, completed_at=datetime.utcnow(),
                )
                result.errors.append(err)
                return result
            self._claimed_archive_ids = claim_ids

            total_archives = len(archives)
            total_messages = sum(a.message_count for a in archives)
            self.db.update_job(job_id, messages_total=total_messages)

            log.info("Import started", job_id=job_id, archives=total_archives,
                     total_messages=total_messages)

            # === Preflight: detect & fix mapping conflicts BEFORE any GELF send ===
            preflight_result: PreflightResult | None = None
            if self.preflight is not None:
                if fc.cancelled:
                    log.info("Import cancelled by user before preflight")
                    self.db.update_job(
                        job_id, status=JobStatus.CANCELLED,
                        error_message="Cancelled by user",
                        completed_at=datetime.utcnow(),
                    )
                    return result
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
                    self.db, pf_ids, cancel_check=lambda: fc.cancelled,
                    ignore_capacity=ignore_capacity, estimated_indices=estimated_indices,
                    **pf_kwargs,
                )
                # User cancelled during preflight — mark CANCELLED, not FAILED.
                if preflight_result.cancelled or fc.cancelled:
                    log.info("Import cancelled by user during preflight")
                    self.db.update_job(
                        job_id, status=JobStatus.CANCELLED,
                        error_message="Cancelled by user",
                        completed_at=datetime.utcnow(),
                    )
                    return result
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
                # Tell BulkImporter the target stream ID so it can rewrite
                # each doc's streams field. Without this rewrite, Graylog
                # Search filters the docs out (source-cluster stream UUIDs).
                if preflight_result and preflight_result.bulk_stream_id:
                    self.bulk_importer.target_stream_id = preflight_result.bulk_stream_id
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

                # Remediation callback: pin the offending field(s) as string +
                # cycle the index (via the target's Graylog API), so bulk can
                # re-send the failed docs and reach zero loss in the same run.
                async def _bulk_remediate(fields: list[str]) -> bool:
                    if self.preflight is None or preflight_result is None \
                            or not preflight_result.index_set_id:
                        return False
                    try:
                        done = await self.preflight.remediate_fields_as_string(
                            preflight_result.index_set_id, fields)
                        try:
                            await self.preflight.wait_for_index_ready(
                                preflight_result.index_set_id, timeout_sec=20)
                        except Exception:
                            pass
                        if done:
                            for f in done:
                                if f not in result.indexer_failure_fields:
                                    result.indexer_failure_fields.append(f)
                        return bool(done)
                    except Exception as e:
                        log.warning("Bulk in-line remediation failed", error=str(e))
                        return False

                bulk_result = await self.bulk_importer.import_archives(
                    paths, progress_callback=_bulk_cb,
                    cancel_check=lambda: fc.cancelled,
                    remediate_cb=_bulk_remediate,
                )
                result.archives_processed = bulk_result.archives_processed
                result.messages_sent = bulk_result.messages_sent

                # Tell the user where to find the imported data in Graylog UI
                where_msg = ""
                if preflight_result and preflight_result.bulk_stream_id:
                    where_msg = (
                        f"To search the imported data: in Graylog Search, "
                        f"select stream '{preflight_result.bulk_stream_title}' "
                        f"(id: {preflight_result.bulk_stream_id})."
                    )
                    log.info("Bulk import: where to find data", msg=where_msg)
                    result.notices.append(where_msg)

                # Build precise reconciliation report from bulk response
                if bulk_result.messages_failed > 0:
                    msg = (
                        f"Compliance violation: {bulk_result.messages_failed} of "
                        f"{bulk_result.messages_sent:,} messages failed to index. "
                        f"Sample errors: " + " | ".join(bulk_result.failure_samples[:5])
                    )
                    log.warning(msg)
                    result.errors.append(msg)
                    # Combine the violation with the where-to-find note
                    full_msg = msg + ((" | " + where_msg) if where_msg else "")
                    self.db.update_job(
                        job_id, status=JobStatus.COMPLETED, progress_pct=100.0,
                        messages_done=bulk_result.messages_indexed,
                        completed_at=datetime.utcnow(),
                        error_message=full_msg,
                    )
                else:
                    log.info(
                        "Bulk reconciliation OK: 0 failed",
                        sent=bulk_result.messages_sent,
                        indexed=bulk_result.messages_indexed,
                    )
                    # Even with 0 failures, surface the where-to-find note via
                    # error_message column so the Job History row shows it on
                    # hover (where-to-find is informational, not a violation).
                    self.db.update_job(
                        job_id, status=JobStatus.COMPLETED, progress_pct=100.0,
                        messages_done=bulk_result.messages_indexed,
                        completed_at=datetime.utcnow(),
                        error_message=(where_msg or None),
                    )

                try:
                    from glogarch.notify.sender import notify_import_complete
                    result.duration_seconds = _time.time() - _start_time
                    await notify_import_complete(
                        result.archives_processed, result.messages_sent, result.errors,
                        duration_seconds=result.duration_seconds,
                    )
                except Exception:
                    pass
                return result

            # === GELF MODE (default) ===
            gelf_host = self.import_config.gelf_host
            gelf_port = self.import_config.gelf_port
            gelf_protocol = getattr(self.import_config, 'gelf_protocol', 'udp')

            check_interval = 0  # counter for journal checks
            # Running indexer-failure baseline for mid-import auto-remediation.
            _fail_baseline = (preflight_result.indexer_failures_baseline
                              if preflight_result is not None else 0)

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

                            # --- Backpressure monitoring (target Graylog + this box)
                            # Check on a ~5000-message cadence (not a fixed batch
                            # count) so a large batch size doesn't leave a huge blind
                            # window where a stuck journal / rising memory could
                            # balloon unnoticed.
                            check_interval += 1
                            _check_every = max(1, 5000 // max(1, fc.batch_size))
                            if check_interval % _check_every == 0:
                                from glogarch.utils.memguard import mem_action, SEVERITY
                                action = "normal"
                                uncommitted = None
                                if self.journal_monitor:
                                    status = await self.journal_monitor.check()
                                    fc.journal_status = status
                                    action = self.journal_monitor.recommend_action(status)
                                    uncommitted = status.uncommitted
                                # Local box-memory guard — jt-glogarch usually shares
                                # the VM with Graylog + OpenSearch, so a big import can
                                # OOM-kill the box ("Interrupted by service restart").
                                # Back off before MemAvailable runs out.
                                mem_act, avail = mem_action(self.import_config.mem_pause_mb,
                                                            self.import_config.mem_slow_mb)
                                fc.mem_available_mb = avail
                                if SEVERITY[mem_act] > SEVERITY[action]:
                                    action = mem_act
                                fc.journal_action = action
                                fc.auto_rate = True

                                if action == "stop":
                                    log.error("Journal overflow, stopping import",
                                              uncommitted=uncommitted)
                                    try:
                                        from glogarch.notify.sender import notify_error
                                        await notify_error("Import",
                                            f"Graylog journal overflow: {uncommitted:,} uncommitted entries. "
                                            f"Import stopped to prevent data loss.")
                                    except Exception:
                                        pass
                                    raise RuntimeError(
                                        f"Graylog journal overflow ({uncommitted:,} uncommitted). "
                                        f"Import stopped.")

                                if action == "pause":
                                    log.warning("Backpressure, pausing import",
                                                reason=("memory" if mem_act == "pause" else "journal/buffer"),
                                                journal_action=action, uncommitted=uncommitted,
                                                mem_available_mb=avail)
                                    # Interruptible auto-pause (~30s) — poll the cancel
                                    # flag every second so the user can ALWAYS stop a
                                    # paused import immediately (an uninterruptible
                                    # sleep made Cancel look dead while backed up).
                                    for _ in range(30):
                                        if fc.cancelled:
                                            break
                                        await asyncio.sleep(1)
                                    continue  # Re-check after pause

                                # --- Mid-import indexer-failure remediation ---
                                # On the same cadence, catch a mapping conflict
                                # EARLY (pin the field as string + cycle) so the
                                # rest of the import indexes cleanly, instead of
                                # losing every conflicting message until the end.
                                _fail_baseline = await self._mid_import_remediate(
                                    preflight_result, result, _fail_baseline)

                            # --- Send batch ---
                            batch_sent = await sender.send_batch(
                                messages=msg_batch,
                                batch_size=fc.batch_size,
                                delay_ms=fc.get_effective_delay(),
                                # Poll cancel DURING the batch — on a loaded box a
                                # single batch can take tens of seconds, and a
                                # between-batches-only check made Cancel look dead.
                                cancel_check=lambda: fc.cancelled,
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
                    # Destination verification: how many of the sent messages the
                    # TARGET actually indexed (sent minus what its indexer rejected).
                    result.messages_indexed = max(0, result.messages_sent - max(0, delta))
                    if delta > 0:
                        # Don't just report a count and tell the operator to go
                        # read Graylog — auto-diagnose WHICH field(s) failed and
                        # auto-fix the mapping so a re-import indexes cleanly.
                        details = await self.preflight.get_indexer_failure_details()
                        flds = details.get("fields", {})
                        reasons = details.get("reasons", {})
                        remediated: list[str] = []
                        if flds and preflight_result.index_set_id:
                            try:
                                remediated = await self.preflight.remediate_fields_as_string(
                                    preflight_result.index_set_id, list(flds.keys()))
                            except Exception as e:
                                log.warning("Auto-remediation failed", error=str(e))
                        result.indexer_failure_fields = list(flds.keys())
                        field_desc = ", ".join(
                            f"'{k}' (×{v})" for k, v in
                            sorted(flds.items(), key=lambda x: -x[1])[:6]
                        ) or "unidentified field(s)"
                        reason_desc = ", ".join(sorted(reasons.keys())) or "mapping conflict"
                        if remediated:
                            recon_msg = (
                                f"{delta} indexer failures on field(s): {field_desc} "
                                f"[{reason_desc}]. Auto-remediated: pinned "
                                f"{len(remediated)} field(s) as string and cycled the "
                                f"index — re-import these archives to recover the "
                                f"{delta} affected message(s) (Bulk mode dedups; a GELF "
                                f"re-send duplicates already-indexed messages)."
                            )
                        elif flds:
                            recon_msg = (
                                f"{delta} indexer failures on field(s): {field_desc} "
                                f"[{reason_desc}]. Could not auto-fix the mapping — set "
                                f"these field(s) to type 'string' in the target index set, "
                                f"then re-import."
                            )
                        else:
                            recon_msg = (
                                f"{delta} indexer failures during this import (could not "
                                f"parse the offending field). Reasons: {reason_desc}."
                            )
                        log.warning(recon_msg)
                        result.errors.append(recon_msg)
                        # Mark as completed_with_failures via error_message
                        final_status = JobStatus.COMPLETED
                    else:
                        log.info(
                            "Reconciliation OK: 0 indexer failures — all messages "
                            "verified at destination",
                            sent=result.messages_sent, indexed=result.messages_indexed,
                            failures_before=preflight_result.indexer_failures_baseline,
                            failures_after=after,
                        )
                        result.notices.append(
                            f"✓ Verified at target: {result.messages_indexed:,} of "
                            f"{result.messages_sent:,} messages indexed (0 indexer failures)."
                        )
                except Exception as e:
                    log.warning("Post-import reconciliation failed", error=str(e))
            else:
                # No reconciliation available — treat sent as indexed (best effort).
                result.messages_indexed = result.messages_sent

            import json as _json_rj
            self.db.update_job(
                job_id, status=final_status, progress_pct=100.0,
                messages_done=result.messages_sent, completed_at=datetime.utcnow(),
                error_message=recon_msg or None,
                result_json=_json_rj.dumps({
                    "messages_sent": result.messages_sent,
                    "messages_indexed": result.messages_indexed,
                    "indexer_failures": result.messages_sent - result.messages_indexed,
                }),
            )
            log.info("Import completed", job_id=job_id,
                     archives=result.archives_processed, messages=result.messages_sent)

            try:
                from glogarch.notify.sender import notify_import_complete
                result.duration_seconds = _time.time() - _start_time
                await notify_import_complete(
                    result.archives_processed, result.messages_sent, result.errors,
                    duration_seconds=result.duration_seconds,
                )
            except Exception as nerr:
                # Surface notification failures so they're not silently lost.
                log.warning("Notification send failed", error=str(nerr))
                result.errors.append(f"notify: {nerr}")

        except Exception as e:
            err_str = str(e)
            # Friendlier message on Graylog API auth failures
            if "401" in err_str or "Unauthorized" in err_str:
                err_str = (f"Graylog API authentication failed (401). "
                           f"Check that the API token is still valid: {err_str}")
            self.db.update_job(job_id, status=JobStatus.FAILED,
                               error_message=err_str, completed_at=datetime.utcnow())
            result.errors.append(err_str)
            log.error("Import failed", job_id=job_id, error=err_str)
            try:
                from glogarch.notify.sender import notify_error
                await notify_error("Import", err_str)
            except Exception as nerr:
                log.warning("Notification send failed", error=str(nerr))
            raise
        finally:
            _import_controls.pop(job_id, None)
            # Release the per-archive concurrency lock
            claimed = getattr(self, "_claimed_archive_ids", None)
            if claimed:
                _release_archives(claimed, job_id)
                self._claimed_archive_ids = None

        return result
