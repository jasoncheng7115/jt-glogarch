"""Graylog system metrics for adaptive rate limiting."""

from __future__ import annotations

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
                json={"metrics": self._HEALTH_METRICS},
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
            "journal_uncommitted": int(m.get("org.graylog2.journal.entries-uncommitted") or 0),
            "journal_size": int(m.get("org.graylog2.journal.size") or 0),
            "buffer_input": int(m.get("org.graylog2.buffers.input.usage") or 0),
            "buffer_process": int(m.get("org.graylog2.buffers.process.usage") or 0),
            "buffer_output": int(m.get("org.graylog2.buffers.output.usage") or 0),
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
