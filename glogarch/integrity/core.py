"""HMAC-SHA256 tamper-evidence for archives (optional feature).

Security model
--------------
Plain SHA256 only detects change relative to the stored value; anyone who can
edit both the archive file AND the DB checksum can forge a consistent pair.
An HMAC is *keyed* — without the secret key you cannot compute a valid MAC for
altered content, so editing the file + DB no longer fools verification.

The key comes from the env var ``JT_HMAC_KEY`` (base64 or hex) if set, else the
``integrity.hmac_key_file`` on disk. For protection even against a root/service
attacker, do NOT store the key file — supply the key via env only at seal/verify
time, and keep the independent ledger off-box.

Honest limitation: sealing an *already-tampered* archive only attests it from
that point on; it cannot prove the past.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import os
from datetime import datetime, timezone
from pathlib import Path

from glogarch.utils.logging import get_logger

log = get_logger(__name__)

_CHUNK = 1024 * 1024


def _decode_key(s: str) -> bytes | None:
    """Accept a base64 or hex key (>=16 bytes); fall back to raw UTF-8."""
    s = (s or "").strip()
    if not s:
        return None
    try:
        k = base64.b64decode(s, validate=True)
        if len(k) >= 16:
            return k
    except (binascii.Error, ValueError):
        pass
    try:
        k = bytes.fromhex(s)
        if len(k) >= 16:
            return k
    except ValueError:
        pass
    return s.encode("utf-8") if len(s) >= 16 else None


def load_hmac_key(integ) -> bytes | None:
    """Resolve the HMAC key: env ``JT_HMAC_KEY`` first, then the key file.
    ``integ`` is an IntegrityConfig (or None). Returns None when unavailable."""
    env = os.environ.get("JT_HMAC_KEY")
    if env:
        k = _decode_key(env)
        if k:
            return k
        log.warning("JT_HMAC_KEY is set but could not be decoded (need base64/hex/>=16 chars)")
    path = getattr(integ, "hmac_key_file", "") or ""
    if path and Path(path).is_file():
        try:
            return _decode_key(Path(path).read_text())
        except OSError as e:
            log.warning("Could not read hmac_key_file", error=str(e))
    return None


def generate_key_file(path: str) -> str:
    """Create a new random 256-bit key file (base64, mode 0600). Refuses to
    overwrite an existing key (would orphan every already-sealed archive)."""
    p = Path(path)
    if p.exists():
        raise FileExistsError(f"key file already exists: {path} (refusing to overwrite)")
    p.parent.mkdir(parents=True, exist_ok=True)
    b64 = base64.b64encode(os.urandom(32)).decode("ascii")
    p.write_text(b64 + "\n")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return b64


def compute_hmac_sha256(file_path, key: bytes) -> str:
    """Streaming HMAC-SHA256 of a file's bytes (hex)."""
    h = hmac.new(key, digestmod=hashlib.sha256)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_hmac(file_path, key: bytes, expected: str | None) -> bool:
    """Constant-time compare of the recomputed HMAC against the expected value."""
    actual = compute_hmac_sha256(file_path, key)
    return hmac.compare_digest(actual, expected or "")


def seal_archive(integ, db, archive, key: bytes | None = None) -> str | None:
    """Compute + persist the HMAC for one archive and append a ledger entry.
    ``integ`` is an IntegrityConfig (or None).

    No-op (returns None) when the feature is disabled, no key is available, or
    the file is missing. Never raises on a missing key/file — sealing is
    best-effort and must not break an export.
    """
    if not (integ and integ.enabled):
        return None
    if key is None:
        key = load_hmac_key(integ)
    if not key:
        log.warning("Integrity enabled but no HMAC key available — archive not sealed",
                    archive_id=getattr(archive, "id", None))
        return None
    p = Path(archive.file_path)
    if not p.is_file():
        return None
    try:
        mac = compute_hmac_sha256(p, key)
        if archive.id is not None:
            db.set_archive_hmac(archive.id, mac)
            if integ.ledger_enabled:
                db.add_ledger_entry(
                    archive.id, str(p), archive.checksum_sha256 or "", mac,
                    archive.file_size_bytes or 0,
                    datetime.now(timezone.utc).isoformat(),
                )
        return mac
    except Exception as e:   # best-effort — a sealing failure must not fail export
        log.warning("Archive sealing failed", archive_id=getattr(archive, "id", None), error=str(e))
        return None


def verify_archive_integrity(integ, archive, key: bytes | None = None) -> tuple[str, str]:
    """Return (result, detail):
      'ok'       — HMAC present and matches
      'tampered' — HMAC present and MISMATCHES (keyed → strong signal)
      'skip'     — not sealed / no key / file missing (fall back to SHA256)
    ``integ`` is an IntegrityConfig (or None).
    """
    if not getattr(archive, "hmac_sha256", None):
        return ("skip", "not HMAC-sealed")
    if key is None:
        key = load_hmac_key(integ)
    if not key:
        return ("skip", "no HMAC key available")
    p = Path(archive.file_path)
    if not p.is_file():
        return ("skip", "file missing")
    return ("ok", "") if verify_hmac(p, key, archive.hmac_sha256) else ("tampered", "HMAC mismatch")
