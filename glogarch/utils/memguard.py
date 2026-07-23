"""Local box-memory guard.

jt-glogarch is usually deployed on the SAME VM as the target Graylog + OpenSearch
(+ MongoDB). A heavy import/export can exhaust the shared RAM and trip the kernel
OOM killer — which then kills jt-glogarch ("Interrupted by service restart") or
OpenSearch (Graylog wedges). Since we run on that box, we can read MemAvailable
directly and back off BEFORE memory runs out.

Fail-open: if /proc/meminfo can't be read (non-Linux, container quirk), return
"normal" — never block work just because the probe failed.
"""

from __future__ import annotations

# Shared throttle severity ordering (import + export).
SEVERITY = {"normal": 0, "slow": 1, "pause": 2, "stop": 3}


def mem_available_mb() -> float | None:
    """Kernel MemAvailable in MiB (Linux), or None if unreadable."""
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    # value is in kB
                    return int(line.split()[1]) / 1024.0
    except Exception:
        return None
    return None


def mem_action(pause_mb: float, slow_mb: float) -> tuple[str, float | None]:
    """Return ("normal"|"slow"|"pause", available_mb).

    available_mb <= pause_mb -> "pause" (OOM imminent — stop adding load)
    available_mb <= slow_mb  -> "slow"
    else                     -> "normal"
    Unreadable -> ("normal", None) (fail-open).
    """
    avail = mem_available_mb()
    if avail is None:
        return "normal", None
    if avail <= pause_mb:
        return "pause", avail
    if avail <= slow_mb:
        return "slow", avail
    return "normal", avail
