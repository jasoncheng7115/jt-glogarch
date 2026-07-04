"""Atomic, locked writer for config.yaml.

All Web UI / setup wizard endpoints that mutate config.yaml MUST go through
``update_config`` so that:

- Concurrent writers (FastAPI handlers, scheduler thread, audit listener) are
  serialized by a single process-wide lock — no lost updates.
- The write is atomic: we dump to a temp file in the same directory and then
  ``os.replace()`` it over the target. A crash mid-write can never truncate
  config.yaml to garbage; a reader either sees the old file or the new one.

Previously each endpoint did its own ``open(read) -> yaml.safe_load -> mutate
-> open(write) -> yaml.dump`` with no lock and no atomicity, which could lose
concurrent updates and, on a crash, leave a half-written config.
"""

from __future__ import annotations

import os
import tempfile
import threading
from pathlib import Path
from typing import Any, Callable

import yaml

# Process-wide lock. config.yaml is a single shared file; all writes serialize.
_config_lock = threading.Lock()


def update_config(config_path: str | Path, mutate: Callable[[dict], None]) -> dict:
    """Atomically read-modify-write config.yaml under a process-wide lock.

    ``mutate`` receives the parsed config dict and edits it in place. The
    resulting dict is dumped back atomically. Returns the written dict.

    Preserves every top-level key not touched by ``mutate`` (export, notify,
    schedule, …) because it round-trips the whole document.
    """
    path = Path(config_path)
    with _config_lock:
        cfg: dict[str, Any] = {}
        if path.is_file():
            with open(path) as f:
                cfg = yaml.safe_load(f) or {}

        mutate(cfg)

        # Write to a temp file in the SAME directory (so os.replace is atomic —
        # rename across filesystems is not), then swap it in.
        fd, tmp_name = tempfile.mkstemp(
            dir=str(path.parent), prefix=".config-", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w") as f:
                yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True,
                          sort_keys=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_name, path)
        except BaseException:
            # Best-effort cleanup; never leave the temp file behind on failure.
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise
    return cfg


def reconcile_secret(new_val: str | None, current_val: str | None) -> str | None:
    """Keep the stored secret when the incoming value is masked or empty.

    GET endpoints return secrets masked as ``***`` (see api.py ``_mask``). When
    the client saves without changing a secret field, the masked placeholder
    comes back — persisting it would overwrite the real secret. Treat any value
    containing ``***`` (or empty/None) as "unchanged" and retain ``current_val``.
    """
    if new_val is None or new_val == "" or "***" in new_val:
        return current_val
    return new_val
