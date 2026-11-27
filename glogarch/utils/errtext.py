# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Text for an exception that is never empty.

httpx timeouts (ReadTimeout, PoolTimeout, ...) carry no message, so
`f"Chunk 9 failed: {e}"` was stored as "Chunk 9 failed: " — the .36 nightly
export of 2026-11-22 lost an hour to four 60-second timeouts during a Graylog
full GC, and nothing on the page or in the log said what had happened.
"""
from __future__ import annotations


def exc_text(e: BaseException) -> str:
    """str(e), or the exception's class name when that is empty."""
    text = str(e).strip()
    return text or type(e).__name__
