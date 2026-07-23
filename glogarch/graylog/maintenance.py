"""Non-destructive 'flush / relieve' operations for a target Graylog.

When a large import wedges the target Graylog (journal backlog piling up, a
ring buffer stuck near capacity, or a write index that won't accept writes),
the operator needs a safe way to nudge it WITHOUT touching any message data.

Every action here is non-destructive — it NEVER deletes messages, indices, or
index sets:

  * ``cycle_deflector`` — rotate to a fresh write index. Unsticks an active
    write index that has a bad mapping or has grown too large; Graylog keeps
    the old index intact and just starts writing to a new one.
  * ``rebuild_index_ranges`` — recompute index ranges (async system job). Fixes
    "data is present but Search finds nothing / shows a 1970 range".

Works with either a configured :class:`GraylogServerConfig` or ad-hoc target
credentials passed from an import dialog, so it can be triggered both from the
Settings server list and from a running import's progress screen.
"""
from __future__ import annotations

import httpx
import structlog

log = structlog.get_logger(__name__)

# Same backpressure signals SystemMonitor.get_health reads — so before/after
# snapshots let the UI show whether the journal/buffers are actually draining.
_HEALTH_METRICS = [
    "org.graylog2.journal.entries-uncommitted",
    "org.graylog2.buffers.process.usage",
    "org.graylog2.buffers.output.usage",
    "org.graylog2.buffers.input.usage",
]


class GraylogFlusher:
    """Runs safe, non-destructive relief actions against one target Graylog."""

    def __init__(
        self,
        api_url: str,
        api_token: str = "",
        api_username: str = "",
        api_password: str = "",
        verify_ssl: bool = False,
    ):
        self.api_url = api_url.rstrip("/")
        self.api_token = api_token
        self.api_username = api_username
        self.api_password = api_password
        self.verify_ssl = verify_ssl

    # ---------------------------------------------------------------- HTTP
    def _auth(self):
        if self.api_token:
            return (self.api_token, "token")
        return (self.api_username, self.api_password)

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            verify=self.verify_ssl,
            timeout=30,
            auth=self._auth(),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-Requested-By": "jt-glogarch",
            },
        )

    # ---------------------------------------------------------------- reads
    async def snapshot(self) -> dict:
        """Read the backpressure signals. Returns {} if unreachable (best effort
        — a snapshot failing must never block the relief actions)."""
        try:
            async with self._client() as c:
                r = await c.post(
                    f"{self.api_url}/api/system/metrics/multiple",
                    json={"metrics": _HEALTH_METRICS},
                )
                if r.status_code != 200:
                    return {}
                data = r.json()
        except Exception as e:
            log.warning("flush snapshot failed", error=str(e))
            return {}
        m = {}
        for item in (data or {}).get("metrics", []):
            name = item.get("full_name") or item.get("name")
            val = (item.get("metric") or {}).get("value")
            if name is not None and val is not None:
                m[name] = val
        return {
            "journal_uncommitted": int(m.get("org.graylog2.journal.entries-uncommitted") or 0),
            "buffer_process": int(m.get("org.graylog2.buffers.process.usage") or 0),
            "buffer_output": int(m.get("org.graylog2.buffers.output.usage") or 0),
            "buffer_input": int(m.get("org.graylog2.buffers.input.usage") or 0),
        }

    async def _default_index_set_id(self) -> str | None:
        try:
            async with self._client() as c:
                r = await c.get(f"{self.api_url}/api/system/indices/index_sets")
                if r.status_code != 200:
                    return None
                for s in (r.json() or {}).get("index_sets", []):
                    if s.get("default"):
                        return s.get("id")
        except Exception:
            return None
        return None

    # ---------------------------------------------------------------- actions
    async def cycle_deflector(self, index_set_id: str | None) -> dict:
        """Rotate the write index (per index-set, else global). Non-destructive."""
        try:
            async with self._client() as c:
                if index_set_id:
                    r = await c.post(
                        f"{self.api_url}/api/cluster/deflector/{index_set_id}/cycle"
                    )
                    if r.status_code in (200, 201, 202, 204):
                        return {"name": "cycle_deflector", "status": "ok",
                                "detail": f"index_set={index_set_id}"}
                r = await c.post(f"{self.api_url}/api/cluster/deflector/cycle")
                if r.status_code in (200, 201, 202, 204):
                    return {"name": "cycle_deflector", "status": "ok", "detail": "global"}
                return {"name": "cycle_deflector", "status": "error",
                        "detail": f"HTTP {r.status_code}: {r.text[:200]}"}
        except Exception as e:
            return {"name": "cycle_deflector", "status": "error", "detail": str(e)}

    async def rebuild_index_ranges(self) -> dict:
        """Recompute index ranges (async system job). Non-destructive."""
        try:
            async with self._client() as c:
                r = await c.post(f"{self.api_url}/api/system/indices/ranges/rebuild")
                if r.status_code in (200, 201, 202, 204):
                    return {"name": "rebuild_index_ranges", "status": "ok",
                            "detail": "system job started"}
                return {"name": "rebuild_index_ranges", "status": "error",
                        "detail": f"HTTP {r.status_code}: {r.text[:200]}"}
        except Exception as e:
            return {"name": "rebuild_index_ranges", "status": "error", "detail": str(e)}

    # ---------------------------------------------------------------- orchestration
    async def flush(
        self,
        index_set_id: str | None = None,
        do_cycle: bool = True,
        do_rebuild: bool = True,
    ) -> dict:
        """Run the requested non-destructive relief actions, with before/after
        backpressure snapshots. NEVER deletes data."""
        if do_cycle and not index_set_id:
            index_set_id = await self._default_index_set_id()

        before = await self.snapshot()
        actions: list[dict] = []
        if do_cycle:
            actions.append(await self.cycle_deflector(index_set_id))
        if do_rebuild:
            actions.append(await self.rebuild_index_ranges())
        after = await self.snapshot()

        ok = bool(actions) and all(a["status"] == "ok" for a in actions)
        log.info("graylog flush done", ok=ok,
                 actions=[a["name"] + ":" + a["status"] for a in actions])
        return {
            "ok": ok,
            "index_set_id": index_set_id,
            "actions": actions,
            "before": before,
            "after": after,
        }
