"""Hardware sizing advisor.

The common jt-glogarch deployment is a SINGLE co-located VM running Graylog +
OpenSearch (+ MongoDB) alongside jt-glogarch. RAM is the binding constraint: two
JVMs plus the OS page cache they depend on will happily exceed the box, and a
heavy import then tips it into swap (imports crawl) or the OOM killer (jobs die
as "Interrupted by service restart"). Operators consistently discover this the
hard way — one customer had to go 16 GB/16 core -> 32 GB/24 core before imports
behaved.

So compute the recommendation from what is ACTUALLY on the box rather than a
generic table:

    required RAM = graylog_heap + os_heap        (the JVMs themselves)
                 + os_heap                        (OpenSearch NEEDS file cache
                                                   roughly equal to its heap —
                                                   Lucene reads through the page
                                                   cache; starving it is why
                                                   search/indexing crawls)
                 + mongo_and_os_base              (MongoDB + kernel + agents)
                 + jt_glogarch                    (us: streaming, but peaks)
                 + 15% headroom

Everything is reported with the inputs that produced it, so the advice can be
audited rather than taken on faith.
"""
from __future__ import annotations

import os
import re

_GB = 1024.0

# Baseline working sets (MiB).
_MONGO_AND_OS_BASE_MB = 2048.0     # MongoDB + kernel + journald/agents
_JT_GLOGARCH_MB = 1024.0           # us — ~214 MB steady, but peaks during jobs
_HEADROOM = 0.15

# Cores: co-located ingest + archive work is CPU-hungry (gzip/JSON/GELF on our
# side, indexing + merges on OpenSearch's).
_CORES_MIN = 4
_CORES_COLOCATED = 8
_CORES_HEAVY = 16          # heavy = large archive corpus / large imports


def read_host_resources() -> dict:
    """Total/available RAM, swap usage and CPU count for THIS box (Linux)."""
    info: dict = {"mem_total_mb": None, "mem_available_mb": None,
                  "swap_total_mb": None, "swap_used_mb": None,
                  "cpu_count": os.cpu_count()}
    try:
        vals = {}
        with open("/proc/meminfo") as f:
            for line in f:
                k, _, rest = line.partition(":")
                parts = rest.split()
                if parts:
                    vals[k] = int(parts[0]) / 1024.0        # kB -> MiB
        info["mem_total_mb"] = vals.get("MemTotal")
        info["mem_available_mb"] = vals.get("MemAvailable")
        st, sf = vals.get("SwapTotal"), vals.get("SwapFree")
        info["swap_total_mb"] = st
        if st is not None and sf is not None:
            info["swap_used_mb"] = max(0.0, st - sf)
    except Exception:
        pass
    return info


def _xmx_to_mb(token: str) -> float | None:
    """Parse a -Xmx value like 4g / 4096m / 8G into MiB."""
    m = re.match(r"^(\d+)([kKmMgGtT]?)$", token)
    if not m:
        return None
    n = float(m.group(1))
    unit = (m.group(2) or "").lower()
    return {"k": n / 1024, "m": n, "g": n * 1024, "t": n * 1024 * 1024, "": n / (1024 * 1024)}[unit]


def detect_local_jvms() -> dict:
    """Find co-located Graylog / OpenSearch JVMs and their -Xmx, by scanning
    /proc. Returns {"graylog_heap_mb", "opensearch_heap_mb", "colocated": bool}.
    Absent component -> None (it lives on another host, or isn't running)."""
    found: dict = {"graylog_heap_mb": None, "opensearch_heap_mb": None}
    try:
        for pid in os.listdir("/proc"):
            if not pid.isdigit():
                continue
            try:
                with open(f"/proc/{pid}/cmdline", "rb") as f:
                    cmd = f.read().decode("utf-8", "replace")
            except Exception:
                continue
            if "java" not in cmd:
                continue
            low = cmd.lower()
            if "graylog" in low:
                key = "graylog_heap_mb"
            elif "opensearch" in low or "elasticsearch" in low:
                key = "opensearch_heap_mb"
            else:
                continue
            for tok in cmd.split("\x00"):
                if tok.startswith("-Xmx"):
                    mb = _xmx_to_mb(tok[4:])
                    if mb and (found[key] is None or mb > found[key]):
                        found[key] = mb
    except Exception:
        pass
    found["colocated"] = bool(found["graylog_heap_mb"] or found["opensearch_heap_mb"])
    return found


def recommend_spec(host: dict | None = None, jvms: dict | None = None,
                   archive_count: int = 0) -> dict:
    """Recommend RAM/cores for THIS box and flag what is currently wrong.

    archive_count drives the "heavy" classification (large corpora mean large
    imports, which are the peak-memory events).
    """
    host = host if host is not None else read_host_resources()
    jvms = jvms if jvms is not None else detect_local_jvms()

    gl = jvms.get("graylog_heap_mb")
    osh = jvms.get("opensearch_heap_mb")
    colocated = bool(jvms.get("colocated"))
    heavy = archive_count >= 10000

    warnings: list[str] = []

    # --- RAM ---
    if colocated:
        # Assume a sane heap for any component present but unreadable.
        gl_eff = gl if gl else (4 * _GB if gl is None and colocated else 0.0)
        os_eff = osh if osh else (4 * _GB if osh is None and colocated else 0.0)
        required = (gl_eff                      # Graylog heap
                    + os_eff                    # OpenSearch heap
                    + os_eff                    # OpenSearch page cache (~= heap)
                    + _MONGO_AND_OS_BASE_MB
                    + _JT_GLOGARCH_MB)
        required *= (1 + _HEADROOM)
    else:
        # Archive-only node: us + OS. Modest, but imports still stream + gzip.
        required = (_JT_GLOGARCH_MB + 1024.0) * (1 + _HEADROOM)

    # Round up to a sensible VM size.
    rec_gb = max(4, int(-(-required // _GB)))
    steps = (4, 8, 12, 16, 24, 32, 48, 64, 96, 128)
    for step in steps:
        if rec_gb <= step:
            rec_gb = step
            break
    # Heavy corpus => large imports, and imports are the peak-memory event. Field
    # calibration: a 24.5K-archive site on a co-located 16 GB box only became
    # healthy at 32 GB, one size above the steady-state formula. Add that step.
    if heavy and colocated and rec_gb in steps and rec_gb != steps[-1]:
        rec_gb = steps[steps.index(rec_gb) + 1]

    # --- Cores ---
    if not colocated:
        rec_cores = _CORES_MIN
    elif heavy:
        rec_cores = _CORES_HEAVY
    else:
        rec_cores = _CORES_COLOCATED

    total_gb = (host.get("mem_total_mb") or 0) / _GB
    cpus = host.get("cpu_count") or 0

    # --- Findings ---
    swap_used = host.get("swap_used_mb") or 0
    if swap_used > 256:
        warnings.append("swap_in_use")          # THE symptom that kills import speed
    if total_gb and total_gb + 0.5 < rec_gb:
        warnings.append("ram_below_recommended")
    if cpus and cpus < rec_cores:
        warnings.append("cores_below_recommended")
    if colocated and gl and osh and total_gb:
        # Both JVMs' heaps should leave room for page cache + everything else.
        if (gl + osh) / _GB > total_gb * 0.6:
            warnings.append("jvm_heaps_too_large")
    if colocated and gl and gl / _GB < 4:
        warnings.append("graylog_heap_low")

    level = "ok"
    if "swap_in_use" in warnings or "ram_below_recommended" in warnings or "jvm_heaps_too_large" in warnings:
        level = "critical"
    elif warnings:
        level = "warn"

    return {
        "colocated": colocated,
        "heavy": heavy,
        "archive_count": archive_count,
        "current": {
            "ram_gb": round(total_gb, 1) if total_gb else None,
            "cpu_count": cpus or None,
            "mem_available_mb": round(host["mem_available_mb"]) if host.get("mem_available_mb") else None,
            "swap_used_mb": round(swap_used) if swap_used else 0,
            "swap_total_mb": round(host["swap_total_mb"]) if host.get("swap_total_mb") else 0,
        },
        "detected": {
            "graylog_heap_gb": round(gl / _GB, 1) if gl else None,
            "opensearch_heap_gb": round(osh / _GB, 1) if osh else None,
        },
        "recommended": {
            "ram_gb": rec_gb,
            "cpu_cores": rec_cores,
            # Keep each JVM heap <= 25% of the recommended RAM (both JVMs <= 50%),
            # leaving the rest for OpenSearch's page cache and everything else.
            # Never exceed 31 GB (compressed oops).
            "graylog_heap_gb": min(31, max(4, int(rec_gb * 0.25))) if colocated else None,
            "opensearch_heap_gb": min(31, max(4, int(rec_gb * 0.25))) if colocated else None,
            "required_ram_gb_raw": round(required / _GB, 1),
        },
        "warnings": warnings,
        "level": level,     # ok | warn | critical
    }
