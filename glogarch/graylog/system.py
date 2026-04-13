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
