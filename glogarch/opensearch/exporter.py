"""OpenSearch direct export — bypasses Graylog API for high-performance archiving."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Callable

from glogarch.archive.storage import ArchiveStorage
from glogarch.core.config import ExportConfig, GraylogServerConfig, OpenSearchConfig, RateLimitConfig
from glogarch.core.database import ArchiveDB
from glogarch.core.models import (
    ArchiveMetadata,
    ArchiveRecord,
    ArchiveStatus,
    JobRecord,
    JobStatus,
    JobType,
)
from glogarch.export.exporter import ExportResult, _ensure_naive
from glogarch.graylog.client import GraylogClient
from glogarch.graylog.system import SystemMonitor
from glogarch.export.health_guard import HealthGuard
from glogarch.opensearch.client import OpenSearchClient
from glogarch.ratelimit.limiter import RateLimiter
from glogarch import __version__
from glogarch.utils.logging import get_logger

log = get_logger("opensearch.export")


_os_export_lock: dict[str, bool] = {}


class _FatalExportError(RuntimeError):
    """A run-wide fatal condition (disk full) that must abort the WHOLE export,
    not be swallowed by the per-index error handler and retried on every index."""


class OpenSearchExporter:
    """Export logs directly from OpenSearch indices — no Graylog API pagination limits."""

    def __init__(
        self,
        server_config: GraylogServerConfig,
        opensearch_config: OpenSearchConfig,
        export_config: ExportConfig,
        rate_limit_config: RateLimitConfig,
        db: ArchiveDB,
        integrity=None,
    ):
        self.server_config = server_config
        self.os_config = opensearch_config
        self.export_config = export_config
        self.storage = ArchiveStorage(export_config)
        self.rate_limiter = RateLimiter(rate_limit_config)
        self.db = db
        self.integrity = integrity   # IntegrityConfig or None (optional sealing)
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    async def export(
        self,
        time_from: datetime,
        time_to: datetime,
        index_prefix: str | None = None,
        index_set_ids: list[str] | None = None,
        progress_callback: Callable[[dict], None] | None = None,
        source: str = "",
        job_id: str | None = None,
        keep_indices: int | None = None,
    ) -> ExportResult:
        """Export by iterating OpenSearch indices directly.

        1. Query Graylog API for index set → index prefix mapping
        2. List indices from OpenSearch
        3. Skip active (write) index
        4. For each index in time range, use search_after to export all docs
        """
        self._cancelled = False
        time_from = _ensure_naive(time_from)
        time_to = _ensure_naive(time_to)

        # Prevent concurrent exports
        server_key = self.server_config.name + "_os"
        if _os_export_lock.get(server_key):
            raise RuntimeError(f"OpenSearch export already running for '{self.server_config.name}'.")
        _os_export_lock[server_key] = True

        try:
            import time as _time
            _start_time = _time.time()
            result = ExportResult()
            job_id = job_id or str(uuid.uuid4())
            result.job_id = job_id

            job = JobRecord(id=job_id, job_type=JobType.EXPORT, status=JobStatus.RUNNING,
                            source=source, started_at=datetime.utcnow())
            self.db.create_job(job)

            has_space, avail_mb = self.storage.check_disk_space()
            if not has_space:
                raise RuntimeError(f"Insufficient disk space: {avail_mb:.0f} MB available")

            # Resolve index prefixes from Graylog API. `skipped` names any index set
            # this run will NOT cover (recorded on the result + logged as a warning).
            prefixes, skipped_index_sets = await self._resolve_prefixes(index_prefix, index_set_ids)
            result.index_sets_skipped = skipped_index_sets
            log.info("Index sets resolved for export", prefixes=prefixes,
                     covered=len(prefixes), skipped=skipped_index_sets)

            # Backpressure guard — OS-direct export still loads the same OpenSearch
            # cluster (especially on slow HDD storage), which can starve Graylog
            # ingestion. Watch Graylog's journal/buffers and pause if they climb.
            # The Graylog client is opened manually here and closed in `finally`.
            _gl_client = GraylogClient(self.server_config, self.rate_limiter)
            try:
                await _gl_client.__aenter__()
                guard = HealthGuard(SystemMonitor(_gl_client), self.export_config, progress_callback)
            except Exception:
                _gl_client = None
                guard = HealthGuard(None, self.export_config, progress_callback)  # disabled

            async with OpenSearchClient(self.os_config) as os_client:
                # === PHASE A (plan): scan / filter / dedup / count EVERY prefix
                # (index set) UP FRONT so the progress denominator is STABLE for
                # the whole run. Accumulating per-prefix (the previous approach)
                # kept done <= total but made the % bar regress each time a new
                # index set was reached; pre-scanning gives one fixed grand total.
                grand_total_docs = 0
                export_plan = []  # flat: (prefix, index_name, idx_from, idx_to, docs_count)
                for prefix in prefixes:
                    if self._cancelled:
                        break

                    # Get active write index to skip it
                    active_index = await os_client.get_active_write_index(prefix)
                    log.info("Active write index", prefix=prefix, active=active_index)

                    # List all indices for this prefix
                    indices = await os_client.list_indices(prefix)
                    log.info("Found indices", prefix=prefix, count=len(indices))

                    # First pass: filter out active/empty indices quickly
                    scan_list = []
                    for idx_info in indices:
                        index_name = idx_info["index"]
                        if index_name == active_index:
                            log.info("Skipping active write index", index=index_name)
                            continue
                        if idx_info["docs_count"] == 0:
                            continue
                        scan_list.append(idx_info)

                    if progress_callback:
                        progress_callback({
                            "phase": "scanning",
                            "pct": 0,
                            "detail": f"Scanning {len(scan_list)} indices...",
                        })

                    # Parallel time range queries (batch of 10 to avoid overwhelming OS)
                    async def _get_range(idx_info):
                        min_ts, max_ts = await os_client.get_index_time_range(idx_info["index"])
                        return idx_info, min_ts, max_ts

                    candidates = []  # [(index_name, idx_from, idx_to, docs_count)]
                    batch_size = 10
                    for i in range(0, len(scan_list), batch_size):
                        if self._cancelled:
                            break
                        batch = scan_list[i:i + batch_size]
                        results = await asyncio.gather(
                            *[_get_range(info) for info in batch],
                            return_exceptions=True,
                        )
                        for res in results:
                            if isinstance(res, Exception):
                                continue
                            idx_info, min_ts, max_ts = res
                            index_name = idx_info["index"]
                            if not min_ts or not max_ts:
                                log.warning("Cannot determine time range", index=index_name)
                                continue
                            idx_from = self._parse_ts(min_ts)
                            idx_to = self._parse_ts(max_ts)
                            if not idx_from or not idx_to:
                                log.warning("Cannot parse timestamps", index=index_name,
                                            min_ts=min_ts, max_ts=max_ts)
                                continue
                            candidates.append((index_name, idx_from, idx_to, idx_info["docs_count"]))
                        if progress_callback:
                            scanned = min(i + batch_size, len(scan_list))
                            progress_callback({
                                "phase": "scanning",
                                "pct": 0,
                                "detail": f"Scanned {scanned}/{len(scan_list)} indices...",
                            })

                    # Apply keep_indices limit (keep most recent N indices)
                    if keep_indices and keep_indices > 0:
                        candidates.sort(key=lambda x: x[2], reverse=True)
                        selected = candidates[:keep_indices]
                        selected.sort(key=lambda x: x[1])  # ascending for export order
                        log.info("Keep indices filter", keep=keep_indices,
                                 total_candidates=len(candidates), selected=len(selected))
                    else:
                        selected = []
                        for c in candidates:
                            if c[2] < time_from or c[1] > time_to:
                                log.info("Index outside time range, skipping", index=c[0])
                                continue
                            selected.append(c)

                    # Dedup check + accurate _count → add survivors to the plan.
                    total_selected = len(selected)
                    for index_name, idx_from, idx_to, docs_count in selected:
                        log.info("Index time range",
                                 index=index_name, idx_from=str(idx_from), idx_to=str(idx_to),
                                 docs=docs_count)
                        existing = self.db.find_archive(
                            self.server_config.name, index_name, idx_from, idx_to
                        )
                        if existing and existing.status == ArchiveStatus.COMPLETED:
                            result.chunks_skipped += 1
                            log.info("Index already exported, skipping", index=index_name)
                            if progress_callback:
                                progress_callback({
                                    "phase": "dedup", "pct": 0,
                                    "detail": f"skipped {result.chunks_skipped}/{total_selected} indices (archived)",
                                })
                            continue
                        coverage = self.db.get_coverage_ratio(self.server_config.name, idx_from, idx_to)
                        if coverage >= 0.95:
                            result.chunks_skipped += 1
                            log.info("Index already covered by other archives, skipping",
                                     coverage_pct=f"{coverage * 100:.0f}%", index=index_name)
                            if progress_callback:
                                progress_callback({
                                    "phase": "dedup", "pct": 0,
                                    "detail": f"skipped {result.chunks_skipped}/{total_selected} indices (archived)",
                                })
                            continue
                        # Accurate doc count via _count (not _cat which includes deleted docs)
                        try:
                            resp = await os_client.post(f"/{index_name}/_count", json={"query": {"match_all": {}}})
                            real_count = resp.get("count", docs_count)
                        except Exception:
                            real_count = docs_count
                        export_plan.append((prefix, index_name, idx_from, idx_to, real_count))
                        grand_total_docs += real_count

                # Stable denominator, set ONCE before any export writes.
                total_docs = grand_total_docs
                total_to_export = len(export_plan)
                self.db.update_job(job_id, messages_total=grand_total_docs)
                log.info("Export plan built", indices=total_to_export,
                         grand_total_docs=grand_total_docs, prefixes=len(prefixes))

                # === PHASE B (export): every planned index against the STABLE total.
                for idx_num, (prefix, index_name, idx_from, idx_to, docs_count) in enumerate(export_plan):
                    if self._cancelled:
                        break

                    # Pause here if Graylog ingestion is backing up.
                    await guard.checkpoint({
                        "phase": "exporting", "index": index_name,
                        "messages_done": result.messages_total,
                        "messages_total": total_docs,
                        "pct": (idx_num / max(total_to_export, 1)) * 100,
                    })

                    if progress_callback:
                        progress_callback({
                            "phase": "exporting",
                            "pct": (idx_num / max(total_to_export, 1)) * 100,
                            "index": index_name,
                            "messages_done": result.messages_total,
                            "messages_total": total_docs,
                            "detail": f"querying {index_name} ({docs_count:,} docs)...",
                        })

                    try:
                        msgs = await self._export_index(
                            os_client, index_name, prefix,
                            idx_from, idx_to,
                            idx_num, total_to_export,
                            progress_callback, result,
                            job_id, total_docs, guard=guard,
                        )
                        result.chunks_exported += 1
                        result.messages_total += msgs
                    except _FatalExportError:
                        raise  # disk full etc. — abort the whole run
                    except Exception as e:
                        err = f"Index {index_name} failed: {e}"
                        log.error(err)
                        result.errors.append(err)

                    # Periodic disk check
                    if (idx_num + 1) % 5 == 0:
                        has_space, _ = self.storage.check_disk_space()
                        if not has_space:
                            raise RuntimeError("Disk space exhausted during export")

            # Build completion note with skip + failure info. A failed index is
            # not recorded, so it retries next run — but the operator must still
            # see that this run was partial rather than a misleading green.
            note_parts = []
            # Index-set coverage — surface the multi-index-set scope on the job
            # itself (was log-only). A non-empty skip list is a data-integrity
            # warning: those index sets were NOT archived this run.
            if result.index_sets_skipped:
                note_parts.append(
                    f"⚠ Archived {len(prefixes)} index set(s); NOT covered: "
                    f"{', '.join(result.index_sets_skipped)} — their logs are not archived")
            else:
                note_parts.append(f"Covered all {len(prefixes)} index set(s)")
            if result.chunks_skipped > 0:
                note_parts.append(f"Skipped {result.chunks_skipped} indices (already archived)")
            if result.errors:
                sample = "; ".join(result.errors[:3])
                note_parts.append(
                    f"⚠ {len(result.errors)} index(es) failed — data may be "
                    f"incomplete, will retry next run: {sample}")
            note = ". ".join(note_parts)
            import json as _json
            result_json = _json.dumps({
                "index_sets_covered": len(prefixes),
                "index_sets_skipped": result.index_sets_skipped,
            })
            self.db.update_job(
                job_id, status=JobStatus.COMPLETED, progress_pct=100.0,
                messages_done=result.messages_total, messages_total=result.messages_total,
                completed_at=datetime.utcnow(),
                error_message=note,
                result_json=result_json,
            )
            log.info("OpenSearch export completed", job_id=job_id,
                     exported=result.chunks_exported, skipped=result.chunks_skipped,
                     messages=result.messages_total)

            try:
                from glogarch.notify.sender import notify_export_complete
                result.duration_seconds = _time.time() - _start_time
                await notify_export_complete(
                    result.chunks_exported, result.messages_total,
                    result.chunks_skipped, result.errors,
                    files=len(result.files_written),
                    original_bytes=result.original_bytes,
                    compressed_bytes=result.compressed_bytes,
                    duration_seconds=result.duration_seconds,
                    mode="opensearch",
                )
            except Exception:
                pass

        except Exception as e:
            self.db.update_job(job_id, status=JobStatus.FAILED,
                               error_message=str(e), completed_at=datetime.utcnow())
            result.errors.append(str(e))
            log.error("OpenSearch export failed", error=str(e))
            try:
                from glogarch.notify.sender import notify_error
                await notify_error("Export (OpenSearch)", str(e))
            except Exception:
                pass
            raise
        finally:
            _os_export_lock.pop(server_key, None)
            _gl = locals().get("_gl_client")
            if _gl is not None:
                try:
                    await _gl.__aexit__(None, None, None)
                except Exception:
                    pass

        return result

    async def _export_index(
        self,
        os_client: OpenSearchClient,
        index_name: str,
        prefix: str,
        idx_from: datetime,
        idx_to: datetime,
        idx_num: int,
        total_indices: int,
        progress_callback: Callable[[dict], None] | None,
        result: ExportResult,
        job_id: str = "",
        total_docs: int = 0,
        guard=None,
    ) -> int:
        """Export an OpenSearch index using single scan + split write by time.

        Scans the entire index once (fast, one search context), but splits output
        into hourly archive files. Each file is recorded in DB immediately.
        If interrupted, completed files are preserved and skipped on retry via dedup.
        """
        chunk_minutes = self.export_config.chunk_duration_minutes
        os_batch = max(self.export_config.batch_size, 10000)
        total_msgs_this_index = 0

        # Pre-check disk space
        has_space, avail_mb = self.storage.check_disk_space(required_mb=50)
        if not has_space:
            raise _FatalExportError(f"Insufficient disk space: {avail_mb:.0f} MB available")

        log.info("Single-scan export starting", index=index_name, batch_size=os_batch)

        # Current chunk tracking
        current_chunk_from = None
        current_chunk_to = None
        writer = None
        path = None
        chunk_count = 0
        file_count = 0

        def _ts_to_dt(doc: dict) -> datetime | None:
            """Extract timestamp from document."""
            ts = doc.get("timestamp", "")
            if not ts:
                return None
            return self._parse_ts(str(ts))

        def _chunk_boundary(dt: datetime) -> tuple[datetime, datetime]:
            """Calculate the chunk (hourly) boundary for a given timestamp."""
            truncated = dt.replace(minute=0, second=0, microsecond=0)
            return truncated, truncated + timedelta(minutes=chunk_minutes)

        async def _close_and_record(w, p, c_from, c_to):
            """Close current writer and record in DB."""
            nonlocal file_count
            try:
                # Snapshot field schema BEFORE close (close() resets internal state)
                field_schema_json = w.get_field_schema_json()
                file_path, checksum, file_size, msg_count, original_bytes = w.close()
            except OSError as e:
                self._cleanup_writer(w, p)
                log.error("Failed to finalize archive", path=str(p), error=str(e))
                return 0

            if file_size == 0 or msg_count == 0:
                self._cleanup_writer(None, p)
                return 0

            try:
                record = ArchiveRecord(
                    server_name=self.server_config.name,
                    stream_id=index_name,
                    stream_name=prefix,
                    time_from=c_from,
                    time_to=c_to,
                    file_path=str(file_path),
                    file_size_bytes=file_size,
                    original_size_bytes=original_bytes,
                    message_count=msg_count,
                    part_number=file_count + 1,
                    total_parts=0,  # unknown total until scan completes
                    checksum_sha256=checksum,
                    status=ArchiveStatus.COMPLETED,
                    field_schema=field_schema_json,
                )
                record.id = self.db.record_archive(record)
                try:
                    from glogarch.integrity import seal_archive
                    seal_archive(self.integrity, self.db, record)
                except Exception:
                    pass
                file_count += 1
                result.original_bytes += original_bytes
                result.compressed_bytes += file_size
            except Exception as e:
                log.error("Failed to record archive in DB", path=str(file_path), error=str(e))
                result.errors.append(f"DB error for {file_path}: {e}")

            result.files_written.append(str(file_path))
            log.info("Chunk exported", index=index_name, time_from=str(c_from), messages=msg_count)
            return msg_count

        try:
            async for batch in os_client.iter_index_docs(
                index_name=index_name,
                batch_size=os_batch,
                delay_between_requests_ms=2,
            ):
                if self._cancelled:
                    break
                # Backpressure sampling on a fixed ~15s cadence, throughout the
                # (potentially long) single-index scan — not only between indices.
                if guard is not None:
                    await guard.checkpoint({"phase": "exporting", "index": index_name,
                                            "messages_done": result.messages_total,
                                            "messages_total": total_docs})
                if not batch:
                    # An empty batch is NOT end-of-stream — skip it and let the
                    # iterator's own StopIteration end the loop. Treating "empty
                    # batch" as a terminator would silently truncate the index.
                    continue

                # Group docs in this batch by chunk boundary, then write each group
                chunk_groups = {}  # {(c_from, c_to): [docs]}
                for doc in batch:
                    doc_ts = _ts_to_dt(doc)
                    if not doc_ts:
                        continue
                    c_from, c_to = _chunk_boundary(doc_ts)
                    chunk_groups.setdefault((c_from, c_to), []).append(doc)

                for (c_from, c_to), docs in sorted(chunk_groups.items()):
                    # New chunk? Close previous writer, open new one
                    if c_from != current_chunk_from:
                        if writer and writer.message_count > 0:
                            msgs = await _close_and_record(writer, path, current_chunk_from, current_chunk_to)
                            total_msgs_this_index += msgs
                        elif writer:
                            self._cleanup_writer(writer, path)
                            writer = None

                        current_chunk_from = c_from
                        current_chunk_to = c_to

                        # Check dedup before opening new writer.
                        # exclude_stream_id_prefix=prefix prevents sister indices in
                        # the SAME OpenSearch run from blocking each other when an
                        # hourly chunk spans an index rotation boundary. API-mode
                        # archives (which use stream UUIDs as stream_id) still block.
                        existing = self.db.find_archive(
                            self.server_config.name, index_name, c_from, c_to
                        )
                        cross_covered = self.db.is_time_range_covered(
                            self.server_config.name, c_from, c_to,
                            exclude_stream_id_prefix=prefix,
                        )
                        if (existing and existing.status == ArchiveStatus.COMPLETED) or cross_covered:
                            writer = None
                            chunk_count += 1
                            continue

                        # Open new writer
                        metadata = ArchiveMetadata(
                            server=self.server_config.name,
                            stream_id=index_name,
                            stream_name=prefix,
                            time_from=c_from.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            time_to=c_to.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            query="*",
                            exported_at=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                            glogarch_version=__version__,
                        )
                        path = self.storage.get_archive_path(
                            self.server_config.name, index_name, c_from, c_to, part=1,
                        )
                        try:
                            path.parent.mkdir(parents=True, exist_ok=True)
                        except PermissionError:
                            raise RuntimeError(f"Permission denied: cannot write to {path.parent}")

                        writer = self.storage.create_streaming_writer(path, metadata)
                        try:
                            writer.open()
                        except (PermissionError, OSError) as e:
                            raise RuntimeError(f"Cannot create archive file {path}: {e}")
                        chunk_count += 1

                    # Write all docs for this chunk at once
                    if writer:
                        try:
                            writer.write_batch(docs)
                        except OSError as e:
                            raise RuntimeError(f"Disk write error: {e}")

                # Progress update after each batch
                current_done = result.messages_total + total_msgs_this_index + (writer.message_count if writer else 0)
                current_pct = (current_done / max(total_docs, 1)) * 100 if total_docs else 0
                if progress_callback:
                    cb_info = {
                        "phase": "exporting",
                        "chunk_index": idx_num + 1,
                        "total_chunks": total_indices,
                        "messages_done": current_done,
                        "messages_total": total_docs,
                        "pct": current_pct,
                        "index": index_name,
                    }
                    # Keep detail visible while first batch is still loading
                    if not current_done:
                        cb_info["detail"] = f"querying {index_name} ({total_docs:,} docs)..."
                    progress_callback(cb_info)
                self.db.update_job(job_id, progress_pct=min(current_pct, 99), messages_done=current_done)

                # Periodic disk check
                if chunk_count % 20 == 0:
                    has_space, _ = self.storage.check_disk_space()
                    if not has_space:
                        raise _FatalExportError("Disk space exhausted during export")

        except Exception:
            # Clean up current writer on error
            if writer:
                self._cleanup_writer(writer, path)
            raise

        # Close the last writer
        if writer and writer.message_count > 0:
            msgs = await _close_and_record(writer, path, current_chunk_from, current_chunk_to)
            total_msgs_this_index += msgs
        elif writer:
            self._cleanup_writer(writer, path)

        if progress_callback:
            progress_callback({
                "phase": "done",
                "chunk_index": idx_num + 1,
                "total_chunks": total_indices,
                "messages_done": result.messages_total + total_msgs_this_index,
                "messages_total": total_docs,
                "pct": ((result.messages_total + total_msgs_this_index) / max(total_docs, 1)) * 100 if total_docs else 0,
                "index": index_name,
            })

        return total_msgs_this_index

    @staticmethod
    def _cleanup_writer(writer, path):
        """Safely close writer and remove partial/empty files."""
        try:
            if writer and writer._file:
                writer._file.close()
                writer._file = None
        except Exception:
            pass
        try:
            if path.exists():
                path.unlink()
            sha_path = path.with_suffix(path.suffix + ".sha256")
            if sha_path.exists():
                sha_path.unlink()
        except Exception:
            pass

    async def _resolve_prefixes(
        self, index_prefix: str | None, index_set_ids: list[str] | None
    ) -> tuple[list[str], list[str]]:
        """Resolve which index prefixes to export from Graylog.

        Returns ``(prefixes, skipped)`` where ``skipped`` names any Graylog index
        set NOT covered by this run — always logged as a WARNING so a partial export
        can never be silent.

        When neither an explicit ``index_prefix`` nor ``index_set_ids`` is given,
        **ALL** index sets are covered. (This used to return only the *default*
        index set, which silently skipped every other index set — a data-loss bug in
        multi-index-set deployments, since those logs were never archived and were
        eventually deleted by Graylog retention.)
        """
        if index_prefix:
            return [index_prefix], []

        async with GraylogClient(self.server_config, self.rate_limiter) as client:
            index_sets = await client.get_index_sets()

        valid = [iset for iset in index_sets if iset.get("index_prefix")]
        if index_set_ids:
            want = set(index_set_ids)
            prefixes = [iset["index_prefix"] for iset in valid if iset.get("id") in want]
            found_ids = {iset.get("id") for iset in valid}
            missing = [i for i in want if i not in found_ids]
            if missing:
                log.warning("Requested index set id(s) not found on Graylog", missing=missing)
        else:
            # Safe default for an archival tool: cover every index set.
            prefixes = [iset["index_prefix"] for iset in valid]

        covered = set(prefixes)
        skipped = [
            (iset.get("title") or iset.get("id") or iset.get("index_prefix"))
            for iset in valid
            if iset["index_prefix"] not in covered
        ]
        if skipped:
            log.warning(
                "Index sets NOT covered by this OpenSearch export — their logs will "
                "NOT be archived and will be lost when Graylog retention deletes them",
                skipped=skipped, covered=sorted(covered),
            )

        if not prefixes:
            return ["graylog"], skipped
        return prefixes, skipped

    def get_resume_point(self, stream_id: str | None = None) -> datetime | None:
        """Find latest exported time_to for resume.

        Only considers archives that match the same export mode to prevent
        cross-mode resume points from causing 0-record exports.
        """
        archives = self.db.list_archives(
            server=self.server_config.name,
            stream=stream_id,
            status=ArchiveStatus.COMPLETED,
        )
        if not archives:
            return None
        if stream_id:
            archives = [a for a in archives if a.stream_id == stream_id]
        if not archives:
            return None
        return max(a.time_to for a in archives)

    @staticmethod
    def _parse_ts(ts: str) -> datetime | None:
        for fmt in (
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%f+00:00",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
        ):
            try:
                return datetime.strptime(ts, fmt)
            except ValueError:
                continue
        return None
