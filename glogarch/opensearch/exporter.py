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
from glogarch.opensearch.client import OpenSearchClient
from glogarch.ratelimit.limiter import RateLimiter
from glogarch import __version__
from glogarch.utils.logging import get_logger

log = get_logger("opensearch.export")


_os_export_lock: dict[str, bool] = {}


class OpenSearchExporter:
    """Export logs directly from OpenSearch indices — no Graylog API pagination limits."""

    def __init__(
        self,
        server_config: GraylogServerConfig,
        opensearch_config: OpenSearchConfig,
        export_config: ExportConfig,
        rate_limit_config: RateLimitConfig,
        db: ArchiveDB,
    ):
        self.server_config = server_config
        self.os_config = opensearch_config
        self.export_config = export_config
        self.storage = ArchiveStorage(export_config)
        self.rate_limiter = RateLimiter(rate_limit_config)
        self.db = db
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

            # Resolve index prefixes from Graylog API
            prefixes = await self._resolve_prefixes(index_prefix, index_set_ids)

            async with OpenSearchClient(self.os_config) as os_client:
                for prefix in prefixes:
                    if self._cancelled:
                        break

                    # Get active write index to skip it
                    active_index = await os_client.get_active_write_index(prefix)
                    log.info("Active write index", prefix=prefix, active=active_index)

                    # List all indices for this prefix
                    indices = await os_client.list_indices(prefix)
                    total_indices = len(indices)

                    log.info("Found indices", prefix=prefix, count=total_indices)

                    # Filter: exclude active, empty, get time ranges
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

                    # Report scanning phase to UI
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
                        # Report scan progress
                        if progress_callback:
                            scanned = min(i + batch_size, len(scan_list))
                            progress_callback({
                                "phase": "scanning",
                                "pct": 0,
                                "detail": f"Scanned {scanned}/{len(scan_list)} indices...",
                            })

                    # Apply keep_indices limit (keep most recent N indices)
                    if keep_indices and keep_indices > 0:
                        # Sort by idx_to descending (newest first), take N
                        candidates.sort(key=lambda x: x[2], reverse=True)
                        selected = candidates[:keep_indices]
                        selected.sort(key=lambda x: x[1])  # Re-sort by time ascending for export order
                        log.info("Keep indices filter", keep=keep_indices,
                                 total_candidates=len(candidates), selected=len(selected))
                    else:
                        # Fallback: time range filter
                        selected = []
                        for c in candidates:
                            if c[2] < time_from or c[1] > time_to:
                                log.info("Index outside time range, skipping", index=c[0])
                                continue
                            selected.append(c)

                    # Dedup check
                    export_list = []
                    total_selected = len(selected)
                    for check_idx, (index_name, idx_from, idx_to, docs_count) in enumerate(selected):
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
                                    "phase": "dedup",
                                    "pct": 0,
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
                                    "phase": "dedup",
                                    "pct": 0,
                                    "detail": f"skipped {result.chunks_skipped}/{total_selected} indices (archived)",
                                })
                            continue
                        export_list.append((index_name, idx_from, idx_to, docs_count))

                    total_to_export = len(export_list)
                    # Get accurate doc counts via _count API (not _cat which includes deleted docs)
                    accurate_list = []
                    for idx_name, idx_from, idx_to, cat_count in export_list:
                        try:
                            resp = await os_client.post(f"/{idx_name}/_count", json={"query": {"match_all": {}}})
                            real_count = resp.get("count", cat_count)
                        except Exception:
                            real_count = cat_count
                        accurate_list.append((idx_name, idx_from, idx_to, real_count))
                    export_list = accurate_list
                    total_docs = sum(e[3] for e in export_list)
                    log.info("Indices to export", count=total_to_export, total_docs=total_docs)
                    self.db.update_job(job_id, messages_total=total_docs)

                    # Second pass: export
                    for idx_num, (index_name, idx_from, idx_to, docs_count) in enumerate(export_list):
                        if self._cancelled:
                            break

                        # Report start of index export
                        if progress_callback:
                            progress_callback({
                                "phase": "exporting",
                                "pct": (idx_num / max(total_to_export, 1)) * 100,
                                "index": index_name,
                                "messages_done": result.messages_total,
                                "messages_total": total_docs,
                                "detail": f"querying {index_name} ({docs_count:,} docs)...",
                            })

                        # Export this index
                        try:
                            msgs = await self._export_index(
                                os_client, index_name, prefix,
                                idx_from, idx_to,
                                idx_num, total_to_export,
                                progress_callback, result,
                                job_id, total_docs,
                            )
                            result.chunks_exported += 1
                            result.messages_total += msgs
                        except Exception as e:
                            err = f"Index {index_name} failed: {e}"
                            log.error(err)
                            result.errors.append(err)

                        # Periodic disk check
                        if (idx_num + 1) % 5 == 0:
                            has_space, _ = self.storage.check_disk_space()
                            if not has_space:
                                raise RuntimeError("Disk space exhausted during export")

            # Build completion note with skip info
            note = ""
            if result.chunks_skipped > 0:
                note = f"Skipped {result.chunks_skipped} indices (already archived)"
            self.db.update_job(
                job_id, status=JobStatus.COMPLETED, progress_pct=100.0,
                messages_done=result.messages_total, messages_total=result.messages_total,
                completed_at=datetime.utcnow(),
                error_message=note,
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
            raise RuntimeError(f"Insufficient disk space: {avail_mb:.0f} MB available")

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
                self.db.record_archive(record)
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
                if not batch or self._cancelled:
                    break

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
                        raise RuntimeError("Disk space exhausted during export")

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
    ) -> list[str]:
        """Resolve index prefixes from Graylog API."""
        if index_prefix:
            return [index_prefix]

        async with GraylogClient(self.server_config, self.rate_limiter) as client:
            if index_set_ids:
                index_sets = await client.get_index_sets()
                return [
                    iset["index_prefix"]
                    for iset in index_sets
                    if iset["id"] in index_set_ids
                ]
            else:
                # Default: use the default index set prefix
                index_sets = await client.get_index_sets()
                for iset in index_sets:
                    if iset.get("default", False):
                        return [iset["index_prefix"]]
                # Fallback: first index set
                if index_sets:
                    return [index_sets[0]["index_prefix"]]
        return ["graylog"]

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
