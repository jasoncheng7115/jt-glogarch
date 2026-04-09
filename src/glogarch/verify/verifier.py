"""Verify orchestrator — checks archive file integrity and DB consistency."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from glogarch.archive.integrity import verify_file
from glogarch.archive.storage import ArchiveStorage
from glogarch.core.config import ExportConfig
from glogarch.core.database import ArchiveDB
from glogarch.core.models import ArchiveStatus
from glogarch.utils.logging import get_logger

log = get_logger("verify")


class VerifyResult:
    def __init__(self):
        self.total_checked: int = 0
        self.valid: int = 0
        self.corrupted: list[str] = []
        self.missing_files: list[str] = []   # DB record exists, file missing
        self.orphan_files: list[str] = []     # File exists, no DB record
        self.errors: list[str] = []


class Verifier:
    """Verifies archive file integrity and DB consistency."""

    def __init__(self, export_config: ExportConfig, db: ArchiveDB):
        self.storage = ArchiveStorage(export_config)
        self.db = db

    def verify_all(
        self,
        server: str | None = None,
        progress_callback: Callable[[dict], None] | None = None,
    ) -> VerifyResult:
        """Verify all archives (or filter by server).

        Checks:
        1. SHA256 of each file matches DB record
        2. Files referenced in DB exist on disk
        3. Files on disk have DB records (orphan check)
        """
        result = VerifyResult()

        archives = self.db.list_archives(server=server, status=ArchiveStatus.COMPLETED)
        total = len(archives)

        log.info("Verification started", total_archives=total)

        # Step 1: Check each DB record
        for idx, archive in enumerate(archives):
            if progress_callback:
                progress_callback({
                    "phase": "verifying",
                    "current": idx + 1,
                    "total": total,
                    "file_path": archive.file_path,
                })

            result.total_checked += 1
            file_path = Path(archive.file_path)

            if not file_path.exists():
                result.missing_files.append(archive.file_path)
                log.warning("Missing file", archive_id=archive.id, path=archive.file_path)
                # Mark as missing in DB
                self.db.update_archive_status(archive.id, ArchiveStatus.MISSING)
                continue

            is_valid, actual_checksum = verify_file(file_path, archive.checksum_sha256)
            if is_valid:
                result.valid += 1
            else:
                result.corrupted.append(archive.file_path)
                log.error("Corrupted file", archive_id=archive.id, path=archive.file_path,
                          expected=archive.checksum_sha256, actual=actual_checksum)
                # Mark as corrupted in DB
                self.db.update_archive_status(archive.id, ArchiveStatus.CORRUPTED)

        # Step 2: Orphan check — find files on disk not in DB
        db_paths = {a.file_path for a in archives}
        if self.storage.base_path.exists():
            for gz_file in self.storage.base_path.rglob("*.json.gz"):
                if str(gz_file) not in db_paths:
                    result.orphan_files.append(str(gz_file))
                    log.warning("Orphan file (no DB record)", path=str(gz_file))

        log.info("Verification completed",
                 total=result.total_checked,
                 valid=result.valid,
                 corrupted=len(result.corrupted),
                 missing=len(result.missing_files),
                 orphans=len(result.orphan_files))

        if result.corrupted or result.missing_files:
            try:
                import asyncio
                from glogarch.notify.sender import notify_verify_failed
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(notify_verify_failed(result.corrupted, result.missing_files))
                except RuntimeError:
                    asyncio.run(notify_verify_failed(result.corrupted, result.missing_files))
            except Exception:
                pass

        return result

    def verify_single(self, archive_id: int) -> tuple[bool, str]:
        """Verify a single archive by ID. Returns (is_valid, message)."""
        archive = self.db.get_archive(archive_id)
        if not archive:
            return False, f"Archive {archive_id} not found"

        if not Path(archive.file_path).exists():
            return False, f"File missing: {archive.file_path}"

        is_valid, actual = verify_file(archive.file_path, archive.checksum_sha256)
        if is_valid:
            return True, f"OK (SHA256: {actual[:16]}...)"
        return False, f"Corrupted: expected {archive.checksum_sha256[:16]}... got {actual[:16]}..."
