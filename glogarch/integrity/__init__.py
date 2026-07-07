"""Optional tamper-evidence for archives (HMAC-SHA256 + ledger).

Opt-in (default OFF). See core.config.IntegrityConfig and CONFIG.md.
"""
from glogarch.integrity.core import (
    compute_hmac_sha256,
    generate_key_file,
    load_hmac_key,
    seal_archive,
    verify_archive_integrity,
    verify_hmac,
)

__all__ = [
    "compute_hmac_sha256",
    "generate_key_file",
    "load_hmac_key",
    "seal_archive",
    "verify_archive_integrity",
    "verify_hmac",
]
