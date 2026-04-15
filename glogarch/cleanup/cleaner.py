"""Cleanup orchestrator — removes expired archive files based on retention policy."""

from __future__ import annotations

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

# Skip files modified within this many seconds — they may still be being
# written by an in-flight export. Prevents cleanup from racing the writer
# and deleting a partial archive that the DB record will momentarily point at.
RECENT_FILE_GRACE_SECONDS = 600  # 10 minutes

from glogarch.archive.storage import ArchiveStorage
from glogarch.core.config import ExportConfig, RetentionConfig
from glogarch.core.database import ArchiveDB
from glogarch.core.models import ArchiveStatus
from glogarch.utils.logging import get_logger

log = get_logger("cleanup")


class CleanupResult:
    def __init__(self):
        self.files_deleted: int = 0
        self.bytes_freed: int = 0
        self.errors: list[str] = []


class Cleaner:
    """Removes expired archive files based on retention_days."""

    def __init__(
        self,
        retention_config: RetentionConfig,
        export_config: ExportConfig,
        db: ArchiveDB,
    ):
        self.retention = retention_config
        self.storage = ArchiveStorage(export_config)
        self.db = db

    def cleanup(
        self,
        retention_days: int | None = None,
        dry_run: bool = False,
        progress_callback: Callable[[dict], None] | None = None,
    ) -> CleanupResult:
        """Delete archives older than retention_days.

        Args:
            retention_days: Override config retention_days if provided.
            dry_run: If True, only report what would be deleted.
            progress_callback: Called with {phase, current, total, file_path}.
        """
        days = retention_days or self.retention.retention_days
        result = CleanupResult()

        old_archives = self.db.get_archives_older_than(days)
        if not old_archives:
            log.info("No archives to clean up", retention_days=days)
            return result

        total = len(old_archives)
        log.info("Cleanup started", archives_to_delete=total, retention_days=days, dry_run=dry_run)

        for idx, archive in enumerate(old_archives):
            if progress_callback:
                progress_callback({
                    "phase": "deleting",
                    "current": idx + 1,
                    "total": total,
                    "file_path": archive.file_path,
                })

            if dry_run:
                log.info("Would delete", file_path=archive.file_path,
                         size_mb=f"{archive.file_size_bytes / 1024 / 1024:.2f}")
                result.files_deleted += 1
                result.bytes_freed += archive.file_size_bytes
                continue

            try:
                # Race guard: never delete a file that was modified very
                # recently — an export job may still be writing it.
                try:
                    mtime = os.path.getmtime(archive.file_path)
                    if (time.time() - mtime) < RECENT_FILE_GRACE_SECONDS:
                        log.warning(
                            "Skipping recent file (race guard)",
                            file_path=archive.file_path,
                            age_seconds=int(time.time() - mtime),
                        )
                        continue
                except FileNotFoundError:
                    pass
                self.storage.delete_archive_file(archive.file_path)
                self.db.update_archive_status(archive.id, ArchiveStatus.DELETED)
                result.files_deleted += 1
                result.bytes_freed += archive.file_size_bytes
            except Exception as e:
                err = f"Failed to delete {archive.file_path}: {e}"
                log.error(err)
                result.errors.append(err)

        # Clean empty directories
        if not dry_run:
            self._clean_empty_dirs()

        # Clean old operation audit records (same retention as archives)
        if not dry_run:
            try:
                audit_deleted = self.db.cleanup_api_audit(days)
                if audit_deleted:
                    log.info("Cleaned audit records", deleted=audit_deleted, retention_days=days)
            except Exception as e:
                log.warning("Audit cleanup failed", error=str(e))

        log.info("Cleanup completed", files_deleted=result.files_deleted,
                 bytes_freed=result.bytes_freed)

        if result.files_deleted > 0 and not dry_run:
            try:
                import asyncio
                from glogarch.notify.sender import notify_cleanup_complete
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(notify_cleanup_complete(result.files_deleted, result.bytes_freed))
                except RuntimeError:
                    asyncio.run(notify_cleanup_complete(result.files_deleted, result.bytes_freed))
            except Exception:
                pass

        return result

    def _clean_empty_dirs(self) -> None:
        """Remove empty directories under the archive base path."""
        base = self.storage.base_path
        if not base.exists():
            return
        # Walk bottom-up to remove empty dirs
        for dirpath, dirnames, filenames in os.walk(str(base), topdown=False):
            if dirpath == str(base):
                continue
            try:
                if not os.listdir(dirpath):
                    os.rmdir(dirpath)
                    log.debug("Removed empty directory", path=dirpath)
            except OSError:
                pass
