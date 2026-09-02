# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
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

import asyncio
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


# --- Pre-import clear -------------------------------------------------------
#
# DESTRUCTIVE. Deletes every index of one index set on the IMPORT TARGET so an
# import starts from a known-empty state. Graylog's own internal event index
# sets are never listed and never touched.
#
# The order matters: cycle the deflector FIRST so Graylog creates a fresh write
# index, then delete the old ones. Deleting the current write index directly
# would leave the index set with no write target and wedge ingestion.
_PROTECTED_PREFIXES = ("gl-events", "gl-system-events", "gl_system_events")


class GraylogIndexCleaner(GraylogFlusher):
    """List / clear the indices of an index set on the import target."""

    @staticmethod
    def _is_protected(prefix: str) -> bool:
        p = (prefix or "").strip()
        return (not p) or any(p == q or p.startswith(q) for q in _PROTECTED_PREFIXES)

    @staticmethod
    def _iter_indices(payload: dict):
        """Yield (index_name, size_bytes) from Graylog's indices/list response.

        Graylog returns {"all": {"indices": [...]}, "closed": {...}, ...} — each
        group is a DICT wrapping an "indices" list, not a bare list. Reading it
        as a list silently yields nothing, which showed every index set as
        "0 indices, 0 bytes" and would have made a clear look like a no-op.
        """
        seen = set()
        for grp in ("all", "closed", "reopened"):
            g = payload.get(grp) or {}
            items = g.get("indices") if isinstance(g, dict) else g
            for idx in (items or []):
                if not isinstance(idx, dict):
                    continue
                name = idx.get("index_name")
                if not name or name in seen:
                    continue
                seen.add(name)
                # Size lives under all_shards.store_size_bytes (primary+replica);
                # fall back to the primaries if a replica figure is absent.
                shards = idx.get("all_shards") or idx.get("primary_shards") or {}
                yield name, int(shards.get("store_size_bytes") or 0)

    async def list_index_sets(self) -> list[dict]:
        """Index sets the operator may clear, with index count and total size.

        Graylog's internal event index sets are filtered out — clearing those
        would destroy alert/event history and is never what "clean slate before
        an import" means.
        """
        out: list[dict] = []
        async with self._client() as c:
            r = await c.get(f"{self.api_url}/api/system/indices/index_sets?limit=200")
            r.raise_for_status()
            sets = (r.json() or {}).get("index_sets", []) or []
            for s in sets:
                prefix = s.get("index_prefix", "")
                if self._is_protected(prefix):
                    continue
                count, size = 0, 0
                try:
                    # NOTE: this endpoint takes the index set ID, not the prefix,
                    # and each group is a DICT wrapping an "indices" list.
                    st = await c.get(
                        f"{self.api_url}/api/system/indexer/indices/{s.get('id')}/list")
                    if st.status_code == 200:
                        for name, sz in self._iter_indices(st.json() or {}):
                            count += 1
                            size += sz
                except Exception as e:
                    log.warning("Could not size index set", prefix=prefix, error=str(e))
                out.append({
                    "id": s.get("id"),
                    "title": s.get("title"),
                    "index_prefix": prefix,
                    "is_default": bool(s.get("default")),
                    "index_count": count,
                    "size_bytes": size,
                })
        return out

    async def clear_index_set(self, index_set_id: str) -> dict:
        """Rotate, then delete every index of this set except the new write one.

        Returns what was actually deleted so the caller can show it. Refuses to
        touch a protected (Graylog-internal) index set.
        """
        actions: list[dict] = []
        async with self._client() as c:
            r = await c.get(f"{self.api_url}/api/system/indices/index_sets/{index_set_id}")
            r.raise_for_status()
            iset = r.json() or {}
            prefix = iset.get("index_prefix", "")
            if self._is_protected(prefix):
                raise RuntimeError(
                    f"Refusing to clear '{prefix}': that is a Graylog-internal "
                    f"index set (events / system events).")

        # 1) rotate so Graylog provisions a fresh, empty write index
        actions.append(await self.cycle_deflector(index_set_id))
        await asyncio.sleep(3)   # let Graylog finish provisioning before we look

        # 2) find the current write index — it must survive
        write_index = None
        deleted, failed, freed = [], [], 0
        async with self._client() as c:
            try:
                dr = await c.get(f"{self.api_url}/api/system/deflector/{index_set_id}")
                if dr.status_code == 200:
                    write_index = (dr.json() or {}).get("current_target")
            except Exception as e:
                log.warning("Could not read deflector", error=str(e))

            # If we cannot identify the live write index we must NOT proceed:
            # deleting it would leave the target unable to accept the import we
            # are clearing space for. Rotating without deleting is harmless.
            if not write_index:
                raise RuntimeError(
                    "Could not determine the current write index for this index "
                    "set, so nothing was deleted. The index was rotated (which is "
                    "harmless); retry once the target reports a deflector target.")

            lr = await c.get(
                f"{self.api_url}/api/system/indexer/indices/{index_set_id}/list")
            lr.raise_for_status()
            names = list(self._iter_indices(lr.json() or {}))

            for name, size in names:
                if write_index and name == write_index:
                    continue          # never delete the live write target
                try:
                    dl = await c.delete(f"{self.api_url}/api/system/indexer/indices/{name}")
                    if dl.status_code in (200, 202, 204):
                        deleted.append(name)
                        freed += size
                    else:
                        failed.append(f"{name}: HTTP {dl.status_code}")
                except Exception as e:
                    failed.append(f"{name}: {e}")

        log.warning("Cleared index set before import",
                    index_set=prefix, deleted=len(deleted),
                    kept_write_index=write_index, failed=len(failed))
        return {
            "index_set_id": index_set_id,
            "index_prefix": prefix,
            "write_index_kept": write_index,
            "deleted": deleted,
            "deleted_count": len(deleted),
            "bytes_freed": freed,
            "failed": failed,
            "actions": actions,
        }
