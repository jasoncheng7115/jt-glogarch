"""Archive file integrity verification using SHA256."""

from __future__ import annotations

import hashlib
from pathlib import Path

from glogarch.utils.logging import get_logger

log = get_logger("archive.integrity")

CHUNK_SIZE = 8192


def compute_sha256(file_path: str | Path) -> str:
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def write_checksum_file(file_path: str | Path, checksum: str) -> Path:
    """Write a .sha256 checksum sidecar file."""
    p = Path(file_path)
    sha_path = p.with_suffix(p.suffix + ".sha256")
    sha_path.write_text(f"{checksum}  {p.name}\n")
    return sha_path


def read_checksum_file(file_path: str | Path) -> str | None:
    """Read checksum from a .sha256 sidecar file."""
    p = Path(file_path)
    sha_path = p.with_suffix(p.suffix + ".sha256")
    if not sha_path.exists():
        return None
    content = sha_path.read_text().strip()
    return content.split()[0] if content else None


def verify_file(file_path: str | Path, expected_checksum: str | None = None) -> tuple[bool, str]:
    """Verify file integrity.

    Returns (is_valid, actual_checksum).
    If expected_checksum is None, tries to read from .sha256 sidecar file.
    """
    p = Path(file_path)
    if not p.exists():
        log.error("File not found", file_path=str(p))
        return False, ""

    actual = compute_sha256(p)

    if expected_checksum is None:
        expected_checksum = read_checksum_file(p)

    if expected_checksum is None:
        log.warning("No expected checksum available", file_path=str(p))
        return True, actual  # Can't verify, return actual hash

    is_valid = actual == expected_checksum
    if not is_valid:
        log.error(
            "Checksum mismatch",
            file_path=str(p),
            expected=expected_checksum,
            actual=actual,
        )
    return is_valid, actual
