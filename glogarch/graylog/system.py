# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Graylog system metrics for adaptive rate limiting."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from glogarch.graylog.client import GraylogClient
from glogarch.utils.logging import get_logger

log = get_logger("graylog.system")


class SystemMonitor:
    """Monitor Graylog system metrics."""

    def __init__(self, client: GraylogClient):
        self.client = client

    async def get_jvm_stats(self) -> dict:
        """Get JVM statistics including CPU and memory."""
        try:
            return await self.client.get("/api/system/jvm")
        except Exception as e:
            log.warning("Failed to get JVM stats", error=str(e))
            return {}

    async def get_cpu_percent(self) -> float:
        """Get current CPU usage percentage from Graylog JVM stats."""
        stats = await self.get_jvm_stats()
        # Graylog 6.x/7.x: system_load_average / available_processors * 100
        load = stats.get("system_load_average", 0.0)
        processors = stats.get("available_processors", 1)
        if processors > 0 and load > 0:
            return (load / processors) * 100.0
        return 0.0

    async def get_memory_percent(self) -> float:
        """Get JVM heap memory usage percentage (used / max * 100)."""
        stats = await self.get_jvm_stats()
        used = stats.get("used_memory", {}).get("bytes", 0)
        max_mem = stats.get("max_memory", {}).get("bytes", 1)
        if max_mem > 0:
            return (used / max_mem) * 100.0
        return 0.0

    # Graylog ingestion-backpressure signals. If the disk journal or the ring
    # buffers keep climbing, indexing is falling behind — a heavy export is
    # likely starving log collection and must back off.
    _HEALTH_METRICS = [
        "org.graylog2.journal.entries-uncommitted",
        "org.graylog2.journal.size",
        "org.graylog2.buffers.input.usage",
        "org.graylog2.buffers.process.usage",
        "org.graylog2.buffers.output.usage",
    ]
    # Garbage-collector metrics (the Dropwizard jvm.* set Graylog registers).
    # Pool and collector names depend on the GC in use, so ask for the common
    # ones: /metrics/multiple silently omits names that do not exist. The
    # guard judges heap pressure from these instead of used/max (see
    # HealthGuard._gc_pressure) and falls back to used/max when none exist.
    _OLD_POOLS = ("G1-Old-Gen", "PS-Old-Gen", "Tenured-Gen")
    _FULL_GC = ("G1-Old-Generation", "PS-MarkSweep", "MarkSweepCompact")
    _OTHER_GC = ("G1-Young-Generation", "G1-Concurrent-GC", "PS-Scavenge", "Copy")
    _GC_METRICS = (
        [f"jvm.memory.pools.{p}.{k}" for p in _OLD_POOLS for k in ("used-after-gc", "max")]
        + [f"jvm.gc.{c}.{k}" for c in _FULL_GC for k in ("count", "time")]
        + [f"jvm.gc.{c}.time" for c in _OTHER_GC]
    )

    async def get_health(self) -> dict | None:
        """One-shot read of ALL backpressure signals (JVM heap + disk journal +
        ring buffers). Returns a dict, or **None when Graylog can't be reached** —
        callers MUST treat None as 'under pressure' and pause (fail-safe): an
        unreachable Graylog is exactly when we must stop hammering it, not a
        green light to keep going."""
        try:
            jvm = await self.client.get("/api/system/jvm")
            resp = await self.client.post(
                "/api/system/metrics/multiple",
                json={"metrics": self._HEALTH_METRICS + self._GC_METRICS},
                headers={"X-Requested-By": "jt-glogarch"},
            )
        except Exception as e:
            log.warning("health read failed (treating as under pressure)", error=str(e))
            return None
        m = {}
        for item in (resp or {}).get("metrics", []):
            name = item.get("full_name") or item.get("name")
            val = (item.get("metric") or {}).get("value")
            if name is not None and val is not None:
                m[name] = val
        used = (jvm.get("used_memory") or {}).get("bytes", 0)
        max_mem = (jvm.get("max_memory") or {}).get("bytes", 1) or 1
        return {
            "jvm_pct": (used / max_mem) * 100.0,
            "heap_max_bytes": max_mem,
            "heap_used_bytes": used,
            **self._gc_signals(m, max_mem),
            "journal_uncommitted": int(m.get("org.graylog2.journal.entries-uncommitted") or 0),
            "journal_size": int(m.get("org.graylog2.journal.size") or 0),
            "buffer_input": int(m.get("org.graylog2.buffers.input.usage") or 0),
            "buffer_process": int(m.get("org.graylog2.buffers.process.usage") or 0),
            "buffer_output": int(m.get("org.graylog2.buffers.output.usage") or 0),
        }

    async def release_expired_searches(self, count: int = 8) -> int:
        """Send `count` 1-message searches so Graylog drops expired results.

        Graylog 7 holds each search job — with its full result — in a Guava
        cache (InMemorySearchJobService: expireAfterAccess 5 min, maximumSize
        1000). Guava removes expired entries only while serving later cache
        writes, one segment at a time, so once an export pauses nothing ever
        releases the results it left behind: log4 sat at 90-91% heap after GC
        through 30-minute pauses (G1 ran 19 concurrent cycles and found it all
        live), then went 91% -> 74% within 5 minutes of four such searches.
        Several searches, because each one only cleans the segment its job
        lands in. Returns how many were answered."""
        now = datetime.now(timezone.utc)
        params = {
            "query": "*", "limit": 1, "offset": 0, "sort": "timestamp:desc",
            "from": (now - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "to": now.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        }
        done = 0
        for _ in range(max(0, count)):
            try:
                await self.client.get("/api/search/universal/absolute", params=params)
                done += 1
            except Exception as e:
                log.warning("Search to release Graylog's expired search results failed",
                            error=str(e))
                break
        return done

    @classmethod
    def _gc_signals(cls, m: dict, heap_max: int) -> dict:
        """Cumulative GC counters + old-generation occupancy after the last
        collection. Each value is None when this Graylog does not expose it."""
        full = [m[f"jvm.gc.{c}.count"] for c in cls._FULL_GC if f"jvm.gc.{c}.count" in m]
        times = [m[f"jvm.gc.{c}.time"] for c in cls._FULL_GC + cls._OTHER_GC
                 if f"jvm.gc.{c}.time" in m]
        after_pct = None
        for p in cls._OLD_POOLS:
            after = m.get(f"jvm.memory.pools.{p}.used-after-gc")
            if after is None or after < 0:
                continue
            pool_max = m.get(f"jvm.memory.pools.{p}.max") or 0
            denom = pool_max if pool_max > 0 else heap_max
            if denom > 0:
                after_pct = after / denom * 100.0
            break
        return {
            "gc_full_count": int(sum(full)) if full else None,
            "gc_time_ms": int(sum(times)) if full and times else None,
            "heap_after_gc_pct": after_pct,
        }


# API export speed on ONE Graylog node is bound by its heap: Graylog 7 keeps
# every search result 5 minutes (InMemorySearchJobService), about 10-12 KB per
# exported message, and the export's pacing slows down as that fills the heap.
# Measured 2026-11-24 on a throwaway Graylog 7.2.2 with real archive data and
# the shipped pacing: 3 GB heap 622 msg/s, 1.5 GB 281 msg/s (with 2 full GCs
# and 7 pauses) -> about 200 msg/s per GB. Above ~4 GB the per-search cost
# (~0.55 s on a site with many fields, ~890 msg/s at 1000/page) is the limit.
API_EXPORT_MSGS_PER_SEC_PER_GB = 200
API_EXPORT_HEAP_BOUND_BELOW_GB = 4.0


def api_export_estimate(max_heap_bytes: int) -> dict | None:
    """Roughly how fast an API export can read from a Graylog with this -Xmx.
    None when the heap is unknown. `heap_bound` = below the size where the heap,
    not the per-search cost, sets the speed (the UI shows its hint only then)."""
    gb = (max_heap_bytes or 0) / (1024 ** 3)
    if gb <= 0:
        return None
    per_sec = int(round(gb * API_EXPORT_MSGS_PER_SEC_PER_GB / 10.0)) * 10
    return {
        "heap_max_gb": round(gb, 1),
        "heap_bound": gb < API_EXPORT_HEAP_BOUND_BELOW_GB,
        "per_sec": per_sec,
        "per_day": per_sec * 86400,
    }


def heap_advice(max_heap_bytes: int, used_pct: float | None = None) -> dict:
    """Advise on Graylog JVM heap sizing from the current -Xmx. Graylog's
    production guidance is >= 4 GB heap, scaled up for high throughput / heavy
    archiving, capped at ~50% of system RAM and <= 31 GB (compressed oops).
    Returns structured data; the UI localises the wording."""
    gb = (max_heap_bytes or 0) / (1024 ** 3)
    if gb < 4:
        level, rec = "low", 4
    elif gb < 8:
        level, rec = "ok", 8
    else:
        level, rec = "good", int(round(gb))
    return {
        "heap_max_mb": round((max_heap_bytes or 0) / (1024 * 1024)),
        "heap_max_gb": round(gb, 1),
        "recommended_min_gb": rec,
        "used_pct": round(used_pct, 1) if used_pct is not None else None,
        "level": level,   # low | ok | good
    }

    async def get_system_overview(self) -> dict:
        """Get system overview for dashboard display."""
        try:
            system = await self.client.get("/api/system")
            jvm = await self.get_jvm_stats()
            return {
                "version": system.get("version"),
                "hostname": system.get("hostname"),
                "is_leader": system.get("is_leader", system.get("is_master")),
                "lifecycle": system.get("lifecycle"),
                "lb_status": system.get("lb_status"),
                "jvm_memory_used": jvm.get("used_memory", {}).get("bytes", 0),
                "jvm_memory_total": jvm.get("total_memory", {}).get("bytes", 0),
                "cpu_load": await self.get_cpu_percent(),
            }
        except Exception as e:
            log.warning("Failed to get system overview", error=str(e))
            return {"error": str(e)}
