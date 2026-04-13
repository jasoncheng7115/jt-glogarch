"""Reconstruct the SQLite metadata DB by scanning the archive directory.

The .json.gz files are the source of truth — each one carries an
``ArchiveMetadata`` block plus a sibling ``.sha256`` sidecar. If the SQLite
DB is lost or corrupted, this module walks the archive root and re-inserts
one row per file.
"""

from __future__ import annotations

import gzip
import json
import shutil
from datetime import datetime
from pathlib import Path

from glogarch.core.database import ArchiveDB
from glogarch.core.models import ArchiveMetadata, ArchiveRecord, ArchiveStatus
from glogarch.utils.logging import get_logger

log = get_logger("db_rebuild")


def _read_metadata(path: Path) -> ArchiveMetadata | None:
    """Open a .json.gz archive, parse the metadata block, return it.

    The archive layout is ``{"metadata": {...}, "messages": [...]}``. We only
    need the metadata block — the messages are not loaded.
    """
    try:
        with gzip.open(path, "rt", encoding="utf-8") as f:
            # Streaming-aware: most archives are small enough to load whole,
            # but for very large ones we still pay the cost of decompression.
            # That's acceptable for an offline rebuild.
            data = json.load(f)
        meta_dict = data.get("metadata") or {}
        if not meta_dict:
            return None
        return ArchiveMetadata(**meta_dict)
    except Exception as e:
        log.warning("Cannot read metadata", path=str(path), error=str(e))
        return None


def _read_sidecar_sha(path: Path) -> str:
    """Read the SHA256 from ``<archive>.sha256`` if present."""
    side = path.with_suffix(path.suffix + ".sha256")
    if not side.exists():
        return ""
    try:
        return side.read_text().strip().split()[0]
    except Exception:
        return ""


def _parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def rebuild(
    db: ArchiveDB,
    archive_root: Path,
    dry_run: bool = False,
) -> dict:
    """Walk ``archive_root`` and insert one DB row per .json.gz found.

    Returns a summary dict.
    """
    if not archive_root.exists():
        raise FileNotFoundError(f"Archive root not found: {archive_root}")

    summary = {
        "scanned": 0,
        "inserted": 0,
        "skipped_existing": 0,
        "errors": 0,
    }

    # Build a set of existing file_paths so we don't double-insert
    existing = set()
    for r in db.list_archives():
        existing.add(r.file_path)

    for path in sorted(archive_root.rglob("*.json.gz")):
        summary["scanned"] += 1
        rel = str(path)
        if rel in existing:
            summary["skipped_existing"] += 1
            continue

        meta = _read_metadata(path)
        if meta is None:
            summary["errors"] += 1
            continue

        sha = _read_sidecar_sha(path) or meta.checksum_sha256
        try:
            stat = path.stat()
        except OSError:
            summary["errors"] += 1
            continue

        rec = ArchiveRecord(
            server_name=meta.server,
            stream_id=meta.stream_id,
            stream_name=meta.stream_name,
            time_from=_parse_dt(meta.time_from) or datetime.utcnow(),
            time_to=_parse_dt(meta.time_to) or datetime.utcnow(),
            file_path=rel,
            file_size_bytes=stat.st_size,
            original_size_bytes=0,  # cannot recover without re-reading whole file
            message_count=meta.message_count,
            part_number=meta.part,
            total_parts=meta.total_parts,
            checksum_sha256=sha,
            status=ArchiveStatus.COMPLETED,
            created_at=datetime.utcfromtimestamp(stat.st_mtime),
        )
        if dry_run:
            log.info("Would insert", path=rel,
                     server=meta.server, time_from=meta.time_from)
            summary["inserted"] += 1
            continue

        try:
            db.record_archive(rec)
            summary["inserted"] += 1
        except Exception as e:
            log.error("Failed to insert", path=rel, error=str(e))
            summary["errors"] += 1

    return summary


def backup_db(db_path: Path, dest_dir: Path) -> Path:
    """Hot-copy the SQLite DB (and -wal / -shm sidecars) to ``dest_dir``.

    Uses SQLite ``.backup`` API for a consistent snapshot — safe even while
    the live DB is being written.
    """
    import sqlite3
    if not db_path.exists():
        raise FileNotFoundError(f"DB not found: {db_path}")
    dest_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    dest = dest_dir / f"{db_path.stem}-{ts}.db"
    src = sqlite3.connect(str(db_path))
    try:
        dst = sqlite3.connect(str(dest))
        try:
            with dst:
                src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()
    return dest


def prune_backups(dest_dir: Path, keep: int = 14) -> int:
    """Keep the newest ``keep`` backups, delete the rest. Returns # deleted."""
    if not dest_dir.exists():
        return 0
    files = sorted(dest_dir.glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    to_delete = files[keep:]
    for f in to_delete:
        try:
            f.unlink()
        except OSError:
            pass
    return len(to_delete)
