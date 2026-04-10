"""Strip secrets from strings before they are written to logs/DB.

Used to prevent passwords and API tokens from leaking into jobs.error_message,
audit_log, exception traces, etc. Always run user-supplied error/info text
through ``sanitize()`` before persisting.
"""

from __future__ import annotations

import re

# Order matters: more specific patterns first.
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Authorization: Basic xxxxx / Bearer xxxxx headers
    (re.compile(r"(?i)(authorization\s*[:=]\s*)(basic|bearer)\s+\S+"),
     r"\1\2 ***REDACTED***"),
    # http(s)://user:password@host
    (re.compile(r"(https?://)([^:/@\s]+):([^@\s]+)@"),
     r"\1\2:***REDACTED***@"),
    # password=..., pwd=..., passwd=... (URL-style or kwargs)
    (re.compile(r"(?i)\b(password|passwd|pwd|secret)\s*[=:]\s*([^\s&,;\"']+)"),
     r"\1=***REDACTED***"),
    # token=..., api_token=..., access_token=...
    (re.compile(r"(?i)\b([a-z_]*token|api[_-]?key|apikey)\s*[=:]\s*([^\s&,;\"']+)"),
     r"\1=***REDACTED***"),
    # JSON style: "password": "xxx"
    (re.compile(r"(?i)(\"(?:password|passwd|pwd|secret|[a-z_]*token|api[_-]?key|apikey)\"\s*:\s*\")([^\"]+)(\")"),
     r"\1***REDACTED***\3"),
]


def sanitize(text: str | None, max_len: int = 2000) -> str | None:
    """Return ``text`` with credentials masked. Pass-through for None/empty."""
    if not text:
        return text
    s = str(text)
    for pat, repl in _PATTERNS:
        s = pat.sub(repl, s)
    if len(s) > max_len:
        s = s[: max_len - 12] + "...[truncated]"
    return s
