"""Export orchestrator — coordinates search, storage, and DB for archiving."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable

from glogarch.archive.storage import ArchiveStorage


def _ensure_naive(dt: datetime) -> datetime:
    """Strip timezone info for consistent comparison."""
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt
from glogarch.core.config import ExportConfig, GraylogServerConfig, RateLimitConfig
from glogarch.core.database import ArchiveDB
from glogarch.core.models import (
    ArchiveMetadata,
    ArchiveRecord,
    ArchiveStatus,
    JobRecord,
    JobStatus,
    JobType,
)
from glogarch.graylog.client import GraylogClient
from glogarch.graylog.search import GraylogSearch
from glogarch.graylog.system import SystemMonitor
from glogarch.ratelimit.limiter import RateLimiter
from glogarch import __version__
from glogarch.utils.logging import get_logger

log = get_logger("export")

# Global lock to prevent concurrent exports against the same Graylog server
_export_lock: dict[str, bool] = {}


class ExportResult:
    """Result of an export operation."""

    def __init__(self):
        self.chunks_exported: int = 0
        self.chunks_skipped: int = 0
        self.messages_total: int = 0
        self.files_written: list[str] = []
        self.errors: list[str] = []
        self.job_id: str = ""
        self.original_bytes: int = 0
        self.compressed_bytes: int = 0
        self.duration_seconds: float = 0.0


class Exporter:
    """Orchestrates log export from Graylog to archive files."""

    def __init__(
        self,
        server_config: GraylogServerConfig,
        export_config: ExportConfig,
        rate_limit_config: RateLimitConfig,
        db: ArchiveDB,
    ):
        self.server_config = server_config
        self.export_config = export_config
        self.db = db
        self.storage = ArchiveStorage(export_config)
        self.rate_limiter = RateLimiter(rate_limit_config)
        self._cancelled = False

    def cancel(self) -> None:
        """Request cancellation of the current export."""
        self._cancelled = True

    async def export(
        self,
        time_from: datetime,
        time_to: datetime,
        streams: list[str] | None = None,
        stream_names: dict[str, str] | None = None,
        progress_callback: Callable[[dict], None] | None = None,
        source: str = "",
        job_id: str | None = None,
    ) -> ExportResult:
        """Export messages from Graylog for the given time range.

        Splits time range into chunks (chunk_duration_minutes), skips already-exported chunks.

        Args:
            time_from: Start of export range (UTC).
            time_to: End of export range (UTC).
            streams: Optional list of stream IDs to filter.
            stream_names: Optional mapping of stream_id -> stream_name.
            progress_callback: Called with progress dict:
                {phase, chunk_index, total_chunks, messages_done, messages_total, pct}
            job_id: Optional job ID to reuse (from Web UI). If None, generates a new one.
        """
        import time as _time
        _start_time = _time.time()
        self._cancelled = False
        result = ExportResult()
        job_id = job_id or str(uuid.uuid4())
        result.job_id = job_id

        # Normalize to naive UTC datetimes
        time_from = _ensure_naive(time_from)
        time_to = _ensure_naive(time_to)

        # Prevent concurrent exports against the same server
        server_key = self.server_config.name
        if _export_lock.get(server_key):
            raise RuntimeError(f"Export already running for server '{server_key}'. "
                               "Concurrent exports are blocked to protect Graylog from OOM.")
        _export_lock[server_key] = True

        # Create job record
        job = JobRecord(id=job_id, job_type=JobType.EXPORT, status=JobStatus.RUNNING,
                        source=source, started_at=datetime.utcnow())
        self.db.create_job(job)

        try:
            # Check disk space
            has_space, avail_mb = self.storage.check_disk_space()
            if not has_space:
                raise RuntimeError(f"Insufficient disk space: {avail_mb:.0f} MB available")

            # Build time chunks
            chunks = self._build_time_chunks(time_from, time_to)
            total_chunks = len(chunks)
            log.info("Export started", job_id=job_id, chunks=total_chunks,
                     time_from=str(time_from), time_to=str(time_to))

            async with GraylogClient(self.server_config, self.rate_limiter) as client:
                monitor = SystemMonitor(client)
                search = GraylogSearch(
                    client, monitor,
                    delay_between_requests_ms=self.export_config.delay_between_requests_ms,
                )

                # If no streams specified, export all
                stream_list = streams or self.export_config.streams or [None]

                # Pre-count total records for progress
                total_records = 0
                try:
                    total_records = await search.count_messages(
                        query=self.export_config.query or "*",
                        time_from=time_from,
                        time_to=time_to,
                        streams=streams,
                    )
                    self.db.update_job(job_id, messages_total=total_records)
                    log.info("Total records to export", total=total_records,
                             streams=streams, time_from=str(time_from), time_to=str(time_to))
                except Exception as e:
                    log.warning("Failed to pre-count records", error=str(e))

                for stream_id in stream_list:
                    stream_name = (stream_names or {}).get(stream_id, None) if stream_id else None

                    for chunk_idx, (chunk_from, chunk_to) in enumerate(chunks):
                        if self._cancelled:
                            log.info("Export cancelled by user", job_id=job_id)
                            break

                        # Check if already exported (same-mode exact match)
                        existing = self.db.find_archive(
                            self.server_config.name, stream_id, chunk_from, chunk_to
                        )
                        # Cross-mode dedup: check if any archive covers this time range
                        if not existing:
                            if self.db.is_time_range_covered(self.server_config.name, chunk_from, chunk_to):
                                existing = True  # Treat as already exported
                                log.debug("Chunk covered by cross-mode archive, skipping",
                                          time_from=str(chunk_from), time_to=str(chunk_to))
                        if (existing is True) or (existing and existing.status == ArchiveStatus.COMPLETED):
                            result.chunks_skipped += 1
                            log.debug("Chunk already exported, skipping",
                                      time_from=str(chunk_from), time_to=str(chunk_to))
                            if progress_callback:
                                pct = (result.messages_total / max(total_records, 1)) * 100 if total_records else ((chunk_idx + 1) / total_chunks) * 100
                                progress_callback({
                                    "phase": "skipping",
                                    "chunk_index": chunk_idx + 1,
                                    "total_chunks": total_chunks,
                                    "stream_id": stream_id,
                                    "messages_done": result.messages_total,
                                    "messages_total": total_records,
                                    "pct": min(pct, 99),
                                })
                            continue

                        # Export this chunk
                        try:
                            msgs_in_chunk = await self._export_chunk(
                                search, stream_id, stream_name,
                                chunk_from, chunk_to, chunk_idx, total_chunks,
                                progress_callback, result, total_records, job_id,
                            )
                            result.chunks_exported += 1
                            result.messages_total += msgs_in_chunk

                        except Exception as e:
                            err_msg = f"Chunk {chunk_idx+1} failed: {e}"
                            log.error(err_msg, chunk_from=str(chunk_from))
                            result.errors.append(err_msg)
                            # Continue with next chunk

                        # Update DB progress periodically (every chunk)
                        pct = ((chunk_idx + 1) / total_chunks) * 100 if total_chunks else 0
                        self.db.update_job(
                            job_id,
                            progress_pct=min(pct, 99),
                            messages_done=result.messages_total,
                        )

                        # Periodic disk space check
                        if (chunk_idx + 1) % 10 == 0:
                            has_space, _ = self.storage.check_disk_space()
                            if not has_space:
                                raise RuntimeError("Disk space exhausted during export")

                        # JVM memory guard — check every 5 chunks
                        if (chunk_idx + 1) % 5 == 0 and monitor:
                            mem_pct = await monitor.get_memory_percent()
                            threshold = self.export_config.jvm_memory_threshold_pct
                            if mem_pct > threshold:
                                log.error("Graylog JVM heap too high, stopping export",
                                          mem_pct=f"{mem_pct:.1f}%", threshold=f"{threshold:.0f}%")
                                try:
                                    from glogarch.notify.sender import notify_error
                                    await notify_error("Export",
                                        f"Graylog JVM heap {mem_pct:.0f}% (threshold {threshold:.0f}%). "
                                        f"Export stopped. Please increase Xmx/Xms or reduce batch_size.")
                                except Exception:
                                    pass
                                raise RuntimeError(
                                    f"Graylog JVM heap {mem_pct:.0f}% exceeds {threshold:.0f}% threshold. "
                                    f"Export stopped to prevent OOM. Adjust Xmx/Xms or batch_size.")

            # Update job status
            self.db.update_job(
                job_id,
                status=JobStatus.COMPLETED,
                progress_pct=100.0,
                messages_done=result.messages_total,
                messages_total=result.messages_total,
                completed_at=datetime.utcnow(),
            )
            log.info("Export completed", job_id=job_id,
                     chunks_exported=result.chunks_exported,
                     chunks_skipped=result.chunks_skipped,
                     messages_total=result.messages_total)

            # Send notification
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
                    mode="api",
                )
            except Exception:
                pass

        except Exception as e:
            err_str = str(e)
            if "401" in err_str or "Unauthorized" in err_str:
                err_str = (f"Graylog API authentication failed (401). "
                           f"Check that the API token is still valid: {err_str}")
            self.db.update_job(
                job_id,
                status=JobStatus.FAILED,
                error_message=err_str,
                completed_at=datetime.utcnow(),
            )
            result.errors.append(err_str)
            log.error("Export failed", job_id=job_id, error=err_str)
            try:
                from glogarch.notify.sender import notify_error
                await notify_error("Export", err_str)
            except Exception as nerr:
                log.warning("Notification send failed", error=str(nerr))
            raise
        finally:
            _export_lock.pop(server_key, None)

        return result

    async def _export_chunk(
        self,
        search: GraylogSearch,
        stream_id: str | None,
        stream_name: str | None,
        chunk_from: datetime,
        chunk_to: datetime,
        chunk_idx: int,
        total_chunks: int,
        progress_callback: Callable[[dict], None] | None,
        result: ExportResult,
        total_records: int = 0,
        job_id: str = "",
    ) -> int:
        """Export a single time chunk using streaming write. Returns message count.

        Messages are written directly to gzip as they arrive — never held all in memory.

        Error handling:
        - Disk full during write → partial file deleted, error raised
        - API timeout mid-stream → partial file deleted, error raised (will retry next run)
        - Corrupt batch data → skipped with warning, export continues
        - Permission error on path → error raised before writing
        """
        query = self.export_config.query or "*"
        streams = [stream_id] if stream_id else None
        fields = self.export_config.fields or None

        metadata = ArchiveMetadata(
            server=self.server_config.name,
            stream_id=stream_id,
            stream_name=stream_name,
            time_from=chunk_from.strftime("%Y-%m-%dT%H:%M:%SZ"),
            time_to=chunk_to.strftime("%Y-%m-%dT%H:%M:%SZ"),
            query=query,
            exported_at=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            glogarch_version=__version__,
        )

        path = self.storage.get_archive_path(
            self.server_config.name, stream_name, chunk_from, chunk_to, part=1,
        )

        # Pre-check: can we write to this path?
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            raise RuntimeError(f"Permission denied: cannot write to {path.parent}")

        # Pre-check: disk space for this chunk (estimate ~30MB per hour)
        has_space, avail_mb = self.storage.check_disk_space(required_mb=50)
        if not has_space:
            raise RuntimeError(f"Insufficient disk space: {avail_mb:.0f} MB available")

        writer = self.storage.create_streaming_writer(path, metadata)

        try:
            writer.open()
        except (PermissionError, OSError) as e:
            raise RuntimeError(f"Cannot create archive file {path}: {e}")

        has_data = False

        try:
            async for batch in search.iter_all_messages(
                query=query,
                time_from=chunk_from,
                time_to=chunk_to,
                streams=streams,
                fields=fields,
                batch_size=self.export_config.batch_size,
            ):
                # Skip empty batches
                if not batch:
                    continue

                try:
                    writer.write_batch(batch)
                except OSError as e:
                    # Disk full or I/O error during write
                    raise RuntimeError(f"Disk write error: {e}")

                has_data = True
                current_done = result.messages_total + writer.message_count
                current_pct = (current_done / max(total_records, 1)) * 100 if total_records else ((chunk_idx) / total_chunks) * 100
                if progress_callback:
                    progress_callback({
                        "phase": "exporting",
                        "chunk_index": chunk_idx + 1,
                        "total_chunks": total_chunks,
                        "stream_id": stream_id,
                        "messages_done": current_done,
                        "messages_total": total_records,
                        "pct": current_pct,
                    })
                # Update DB progress every ~10 batches for sidebar display
                if writer.message_count % (self.export_config.batch_size * 10) < self.export_config.batch_size:
                    self.db.update_job(job_id, progress_pct=min(current_pct, 99), messages_done=current_done)

            if not has_data:
                # No messages — clean up empty file
                self._cleanup_writer(writer, path)
                log.debug("No messages in chunk", time_from=str(chunk_from), time_to=str(chunk_to))
                return 0

            # Finalize — close gzip, compute checksum
            try:
                # Snapshot field schema BEFORE close (close() resets internal state)
                field_schema_json = writer.get_field_schema_json()
                file_path, checksum, file_size, msg_count, original_bytes = writer.close()
            except OSError as e:
                self._cleanup_writer(writer, path)
                raise RuntimeError(f"Failed to finalize archive: {e}")

        except Exception:
            # Any error during streaming — clean up partial file
            self._cleanup_writer(writer, path)
            raise

        # Verify the written file is valid
        if file_size == 0 or msg_count == 0:
            log.warning("Empty archive produced, removing", path=str(path))
            if path.exists():
                path.unlink()
            sha_path = path.with_suffix(path.suffix + ".sha256")
            if sha_path.exists():
                sha_path.unlink()
            return 0

        # Record in database
        try:
            record = ArchiveRecord(
                server_name=self.server_config.name,
                stream_id=stream_id,
                stream_name=stream_name,
                time_from=chunk_from,
                time_to=chunk_to,
                file_path=str(file_path),
                file_size_bytes=file_size,
                original_size_bytes=original_bytes,
                message_count=msg_count,
                part_number=1,
                total_parts=1,
                checksum_sha256=checksum,
                status=ArchiveStatus.COMPLETED,
                field_schema=field_schema_json,
            )
            self.db.record_archive(record)
            result.original_bytes += original_bytes
            result.compressed_bytes += file_size
        except Exception as e:
            # DB error — file was written successfully, log but don't delete
            log.error("Failed to record archive in DB (file exists on disk)",
                      path=str(file_path), error=str(e))
            result.errors.append(f"DB error for {file_path}: {e}")

        result.files_written.append(str(file_path))

        if progress_callback:
            progress_callback({
                "phase": "done",
                "chunk_index": chunk_idx + 1,
                "total_chunks": total_chunks,
                "stream_id": stream_id,
                "messages_done": result.messages_total + msg_count,
                "pct": ((chunk_idx + 1) / total_chunks) * 100,
            })

        return msg_count

    @staticmethod
    def _cleanup_writer(writer, path):
        """Safely close writer and remove partial file."""
        try:
            if writer._file:
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

    def _build_time_chunks(
        self, time_from: datetime, time_to: datetime
    ) -> list[tuple[datetime, datetime]]:
        """Split time range into chunks."""
        chunk_minutes = self.export_config.chunk_duration_minutes
        chunks = []
        current = time_from
        while current < time_to:
            chunk_end = min(current + timedelta(minutes=chunk_minutes), time_to)
            chunks.append((current, chunk_end))
            current = chunk_end
        return chunks

    def get_resume_point(self, stream_id: str | None = None) -> datetime | None:
        """Find the latest exported time_to for resume after interruption.

        When stream_id is provided, first tries archives for that specific stream.
        Falls back to any archive for this server if no stream-specific match found.
        This avoids re-scanning time ranges that were already exported under a
        different stream configuration (e.g. NULL stream_id vs explicit stream).
        """
        all_archives = self.db.list_archives(
            server=self.server_config.name,
            status=ArchiveStatus.COMPLETED,
        )
        if not all_archives:
            return None

        # Try exact stream match first
        if stream_id:
            matched = [a for a in all_archives if a.stream_id == stream_id]
            if matched:
                return max(a.time_to for a in matched)
        else:
            matched = [a for a in all_archives if a.stream_id is None]
            if matched:
                return max(a.time_to for a in matched)

        # Fallback: use the latest time_to from any archive on this server
        return max(a.time_to for a in all_archives)
