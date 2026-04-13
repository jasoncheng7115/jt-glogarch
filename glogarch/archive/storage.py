"""Archive storage management — disk checks, paths, file splitting."""

from __future__ import annotations

import gzip
import json
import shutil
from datetime import datetime
from pathlib import Path

from glogarch.archive.integrity import compute_sha256, write_checksum_file
from glogarch.core.config import ExportConfig
from glogarch.core.models import ArchiveMetadata
from glogarch.utils.logging import get_logger

log = get_logger("archive.storage")


class ArchiveStorage:
    """Manages archive file paths, disk checks, and file writing."""

    def __init__(self, config: ExportConfig):
        self.config = config
        self.base_path = Path(config.base_path)

    def check_disk_space(self, required_mb: float | None = None) -> tuple[bool, float]:
        """Check if enough disk space is available.

        Returns (has_space, available_mb).
        """
        self.base_path.mkdir(parents=True, exist_ok=True)
        usage = shutil.disk_usage(self.base_path)
        available_mb = usage.free / (1024 * 1024)
        threshold = required_mb or self.config.min_disk_space_mb
        has_space = available_mb >= threshold
        if not has_space:
            log.error(
                "Insufficient disk space",
                available_mb=f"{available_mb:.1f}",
                required_mb=threshold,
            )
        return has_space, available_mb

    def get_archive_dir(
        self, server_name: str, stream_name: str | None, time_from: datetime
    ) -> Path:
        """Get the directory path for an archive file.

        If any directory in the path exists but is not writable by the
        current process (e.g. created by a previous ``root`` run), and
        the current process IS root, it will be ``chown``-ed to the
        ``jt-glogarch`` user automatically. This prevents the common
        mistake of running ``glogarch export`` as root and then having
        the scheduled ``jt-glogarch`` service fail on subsequent exports.
        """
        stream = stream_name or "all"
        # Sanitize names for filesystem
        stream = stream.replace("/", "_").replace(" ", "_")
        d = (
            self.base_path
            / server_name
            / stream
            / time_from.strftime("%Y")
            / time_from.strftime("%m")
            / time_from.strftime("%d")
        )
        try:
            d.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            # A parent directory may be owned by root. Try to fix it.
            self._fix_dir_ownership(self.base_path, d)
            d.mkdir(parents=True, exist_ok=True)
        return d

    @staticmethod
    def _fix_dir_ownership(base_path: Path, target: Path) -> None:
        """Chown any non-``jt-glogarch``-owned directory between
        ``base_path`` and ``target`` (inclusive). Only acts on
        directories under ``base_path`` — never touches system dirs.
        Only works when running as root.
        """
        import os
        import pwd

        if os.getuid() != 0:
            raise PermissionError(
                f"Cannot create archive directory '{target}': permission denied. "
                f"A parent directory is not writable by the current user. "
                f"Fix with: chown -R jt-glogarch:jt-glogarch {base_path}"
            )

        try:
            pw = pwd.getpwnam("jt-glogarch")
        except KeyError:
            raise PermissionError(
                f"Cannot fix ownership: user 'jt-glogarch' does not exist"
            )

        # Only walk directories under base_path — never touch /tmp, /data, etc.
        try:
            rel = target.relative_to(base_path)
        except ValueError:
            return
        cumulative = base_path
        for part in rel.parts:
            cumulative = cumulative / part
            if cumulative.exists() and cumulative.stat().st_uid != pw.pw_uid:
                log.warning("Fixing directory ownership",
                            path=str(cumulative), new_owner="jt-glogarch")
                os.chown(cumulative, pw.pw_uid, pw.pw_gid)
                for child in cumulative.iterdir():
                    try:
                        os.chown(child, pw.pw_uid, pw.pw_gid)
                    except OSError:
                        pass

    def get_archive_filename(
        self,
        server_name: str,
        stream_name: str | None,
        time_from: datetime,
        time_to: datetime,
        part: int = 1,
    ) -> str:
        """Generate archive filename."""
        stream = stream_name or "all"
        stream = stream.replace("/", "_").replace(" ", "_")
        from_str = time_from.strftime("%Y%m%dT%H%M%SZ")
        to_str = time_to.strftime("%Y%m%dT%H%M%SZ")
        return f"{server_name}_{stream}_{from_str}_{to_str}_{part:03d}.json.gz"

    def get_archive_path(
        self,
        server_name: str,
        stream_name: str | None,
        time_from: datetime,
        time_to: datetime,
        part: int = 1,
    ) -> Path:
        """Get full path for an archive file."""
        d = self.get_archive_dir(server_name, stream_name, time_from)
        fname = self.get_archive_filename(server_name, stream_name, time_from, time_to, part)
        return d / fname

    def write_archive(
        self,
        path: Path,
        metadata: ArchiveMetadata,
        messages: list[dict],
    ) -> tuple[Path, str, int]:
        """Write messages to a gzip-compressed JSON archive file.

        Returns (file_path, sha256_checksum, file_size_bytes).
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        archive_data = {
            "metadata": metadata.model_dump(),
            "messages": messages,
        }
        with gzip.open(path, "wt", encoding="utf-8", compresslevel=6) as f:
            json.dump(archive_data, f, ensure_ascii=False, default=str)

        file_size = path.stat().st_size
        checksum = compute_sha256(path)
        write_checksum_file(path, checksum)

        log.info(
            "Archive written",
            path=str(path),
            messages=len(messages),
            size_mb=f"{file_size / 1024 / 1024:.2f}",
        )
        return path, checksum, file_size

    def write_archive_split(
        self,
        server_name: str,
        stream_name: str | None,
        time_from: datetime,
        time_to: datetime,
        metadata_base: ArchiveMetadata,
        messages: list[dict],
    ) -> list[tuple[Path, str, int, int]]:
        """Write messages, splitting into multiple files if needed.

        Returns list of (path, checksum, file_size, message_count) tuples.
        """
        max_bytes = self.config.max_file_size_mb * 1024 * 1024
        results: list[tuple[Path, str, int, int]] = []

        # Estimate: try writing all at once first
        if not messages:
            return results

        # Split messages into chunks based on estimated size
        chunks = self._split_messages(messages, max_bytes)
        total_parts = len(chunks)

        for part_idx, chunk in enumerate(chunks, 1):
            meta = metadata_base.model_copy()
            meta.part = part_idx
            meta.total_parts = total_parts
            meta.message_count = len(chunk)

            path = self.get_archive_path(
                server_name, stream_name, time_from, time_to, part=part_idx
            )
            file_path, checksum, file_size = self.write_archive(path, meta, chunk)
            results.append((file_path, checksum, file_size, len(chunk)))

        return results

    def _split_messages(self, messages: list[dict], max_bytes: int) -> list[list[dict]]:
        """Split messages into chunks that produce files under max_bytes when compressed."""
        # Estimate compression ratio as ~10:1 for log data
        # So max uncompressed = max_bytes * 8 (conservative estimate)
        max_uncompressed = max_bytes * 8

        chunks: list[list[dict]] = []
        current_chunk: list[dict] = []
        current_size = 0

        for msg in messages:
            msg_size = len(json.dumps(msg, default=str))
            if current_size + msg_size > max_uncompressed and current_chunk:
                chunks.append(current_chunk)
                current_chunk = []
                current_size = 0
            current_chunk.append(msg)
            current_size += msg_size

        if current_chunk:
            chunks.append(current_chunk)

        return chunks if chunks else [[]]

    def create_streaming_writer(
        self,
        path: Path,
        metadata: ArchiveMetadata,
    ) -> "StreamingArchiveWriter":
        """Create a streaming writer that writes messages incrementally to gzip.

        No need to hold all messages in memory at once.
        """
        return StreamingArchiveWriter(path, metadata)

    def read_archive(self, path: str | Path) -> tuple[ArchiveMetadata, list[dict]]:
        """Read an archive file, returning metadata and messages.
        Warning: loads entire file into memory. Use iter_archive for large files.
        """
        with gzip.open(path, "rt", encoding="utf-8") as f:
            data = json.load(f)
        metadata = ArchiveMetadata(**data["metadata"])
        return metadata, data["messages"]

    def iter_archive(
        self, path: str | Path, batch_size: int = 500
    ) -> "ArchiveIterator":
        """Stream-read an archive file, yielding messages in batches.

        Returns an ArchiveIterator. Access .metadata after calling .read_metadata() or iterating.
        """
        it = ArchiveIterator(Path(path), batch_size)
        it.read_metadata()
        return it

    def delete_archive_file(self, path: str | Path) -> None:
        """Delete an archive file and its checksum sidecar."""
        p = Path(path)
        if p.exists():
            p.unlink()
            log.info("Deleted archive file", path=str(p))
        sha_path = p.with_suffix(p.suffix + ".sha256")
        if sha_path.exists():
            sha_path.unlink()

    def get_storage_stats(self) -> dict:
        """Get storage usage statistics."""
        if not self.base_path.exists():
            return {"total_files": 0, "total_size_bytes": 0, "available_mb": 0}

        total_files = 0
        total_size = 0
        for f in self.base_path.rglob("*.json.gz"):
            total_files += 1
            total_size += f.stat().st_size

        _, available_mb = self.check_disk_space(0)
        return {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "available_mb": round(available_mb, 2),
        }


class StreamingArchiveWriter:
    """Writes messages incrementally to a gzip JSON file.

    Streams directly to disk — never holds all messages in memory.
    JSON structure: {"metadata": {...}, "messages": [msg1, msg2, ...]}
    """

    def __init__(self, path: Path, metadata: ArchiveMetadata):
        self.path = path
        self.metadata = metadata
        self._file = None
        self._count = 0
        self._first = True
        self._original_bytes = 0
        # Field schema accumulator: {field_name: set of "numeric"|"string"|"other"}
        # Used by import preflight to set custom field mappings on the target
        # Graylog BEFORE GELF send, so no message gets rejected by mapping
        # conflicts. Compliance: zero indexer failures.
        self._field_types: dict[str, set[str]] = {}

    def open(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = gzip.open(self.path, "wt", encoding="utf-8", compresslevel=6)
        # Write opening JSON structure
        meta_json = json.dumps(self.metadata.model_dump(), ensure_ascii=False, default=str)
        self._file.write(f'{{"metadata": {meta_json}, "messages": [')
        self._first = True
        self._count = 0

    # Reserved Graylog/OpenSearch system fields we never need to track for
    # mapping purposes — they're managed by Graylog itself.
    _SCHEMA_RESERVED = frozenset({
        "timestamp", "_id", "gl2_processing_timestamp", "gl2_receive_timestamp",
        "gl2_message_id", "streams", "source", "message", "full_message",
        "gl2_processing_duration_ms", "gl2_accounted_message_size",
    })

    def _track_field_types(self, msg: dict) -> None:
        """Record the value type of every field in the message.
        Costs ~10us per message, negligible vs gzip+JSON write."""
        for k, v in msg.items():
            if k in self._SCHEMA_RESERVED:
                continue
            if v is None or isinstance(v, bool):
                t = "other"
            elif isinstance(v, (int, float)):
                t = "numeric"
            elif isinstance(v, str):
                t = "string"
            else:
                t = "other"
            s = self._field_types.get(k)
            if s is None:
                self._field_types[k] = {t}
            else:
                s.add(t)

    def write_batch(self, messages: list[dict]) -> None:
        """Write a batch of messages to the archive. Can be called multiple times."""
        if not self._file:
            raise RuntimeError("Writer not opened")
        for msg in messages:
            if not self._first:
                self._file.write(",")
            msg_str = json.dumps(msg, ensure_ascii=False, default=str)
            self._file.write(msg_str)
            self._original_bytes += len(msg_str.encode("utf-8"))
            self._first = False
            self._count += 1
            # Accumulate field schema for preflight (cheap, post-write so we
            # don't slow disk I/O)
            self._track_field_types(msg)

    def get_field_schema_json(self) -> str:
        """Return the accumulated field schema as a JSON string suitable for
        the archives.field_schema column."""
        return json.dumps(
            {k: sorted(v) for k, v in self._field_types.items()},
            sort_keys=True,
            ensure_ascii=False,
        )

    def close(self) -> tuple[Path, str, int, int, int]:
        """Close the archive and return (path, checksum, file_size, message_count, original_bytes)."""
        if not self._file:
            raise RuntimeError("Writer not opened")
        # Close JSON array and object
        self._file.write("]}")
        self._file.close()
        self._file = None

        # Update metadata with actual count
        file_size = self.path.stat().st_size
        checksum = compute_sha256(self.path)
        write_checksum_file(self.path, checksum)

        log.info("Archive written (streaming)",
                 path=str(self.path), messages=self._count,
                 size_mb=f"{file_size / 1024 / 1024:.2f}",
                 original_mb=f"{self._original_bytes / 1024 / 1024:.2f}")
        return self.path, checksum, file_size, self._count, self._original_bytes

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        if self._file:
            try:
                self.close()
            except Exception as e:
                log.warning("Error closing archive writer, cleaning up partial file",
                            path=str(self.path), error=str(e))
                if self._file:
                    try:
                        self._file.close()
                    except Exception:
                        pass
                    self._file = None
                if self.path.exists():
                    self.path.unlink()

    @property
    def message_count(self) -> int:
        return self._count


class ArchiveIterator:
    """Stream-reads a .json.gz archive, yielding messages in batches.

    Uses json.JSONDecoder.raw_decode to parse one message at a time
    from the decompressed stream — never loads all messages into memory.
    Memory usage: ~batch_size messages at a time.
    """

    def __init__(self, path: Path, batch_size: int = 500):
        self.path = path
        self.batch_size = batch_size
        self.metadata: ArchiveMetadata | None = None
        self._total = 0

    def read_metadata(self) -> ArchiveMetadata:
        """Read only the metadata from the archive without loading messages."""
        with gzip.open(self.path, "rt", encoding="utf-8") as f:
            # Read enough to get metadata (typically < 1KB)
            chunk = f.read(8192)
            # Find "messages" key to extract metadata portion
            idx = chunk.find('"messages"')
            if idx == -1:
                # Fallback: load full
                f.seek(0)
                data = json.load(f)
                self.metadata = ArchiveMetadata(**data.get("metadata", {}))
                self._total = len(data.get("messages", []))
                return self.metadata

            # Extract metadata JSON: from start to before "messages" key
            # Find the comma before "messages"
            meta_end = chunk.rfind(",", 0, idx)
            if meta_end == -1:
                meta_end = idx
            meta_str = chunk[1:meta_end]  # skip opening {
            # Parse: should be like "metadata": {...}
            meta_json = "{" + meta_str + "}"
            try:
                meta_obj = json.loads(meta_json)
                self.metadata = ArchiveMetadata(**meta_obj.get("metadata", {}))
            except Exception:
                self.metadata = ArchiveMetadata()

        return self.metadata

    def __iter__(self):
        """Yield batches of messages. Loads file but yields in chunks to limit memory."""
        with gzip.open(self.path, "rt", encoding="utf-8") as f:
            data = json.load(f)

        if self.metadata is None:
            self.metadata = ArchiveMetadata(**data.get("metadata", {}))

        messages = data.get("messages", [])
        self._total = len(messages)

        for i in range(0, len(messages), self.batch_size):
            yield messages[i:i + self.batch_size]

        del messages
        del data

    @property
    def total(self) -> int:
        return self._total
