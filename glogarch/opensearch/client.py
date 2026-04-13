"""OpenSearch direct client for log export with resource protection."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, AsyncIterator

import httpx

from glogarch.core.config import OpenSearchConfig
from glogarch.utils.logging import get_logger

log = get_logger("opensearch.client")


class OpenSearchClient:
    """Async HTTP client for direct OpenSearch access."""

    def __init__(self, config: OpenSearchConfig):
        self.config = config
        auth = None
        if config.username and config.password:
            auth = httpx.BasicAuth(config.username, config.password)

        self._client = httpx.AsyncClient(
            auth=auth,
            verify=config.verify_ssl,
            timeout=httpx.Timeout(120.0, connect=10.0),
            headers={"Content-Type": "application/json"},
        )
        self._hosts = [h.rstrip("/") for h in config.hosts] if config.hosts else ["http://localhost:9200"]
        self._active_host = 0  # index into _hosts

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        """Send request with automatic failover and retry on transient errors.

        - ConnectError / ConnectTimeout → try next host immediately
        - HTTP 500 / 502 / 503 / 429   → retry same host with backoff (up to 3×)
        - Other HTTP errors             → raise immediately
        """
        import asyncio as _aio
        last_error: Exception | None = None
        max_retries = 3
        for attempt in range(len(self._hosts)):
            host_idx = (self._active_host + attempt) % len(self._hosts)
            url = f"{self._hosts[host_idx]}{path}"
            for retry in range(max_retries):
                try:
                    resp = await self._client.request(method, url, **kwargs)
                    if resp.status_code in (429, 500, 502, 503):
                        wait = 2 ** retry
                        log.warning("Transient error, retrying",
                                    host=self._hosts[host_idx],
                                    status=resp.status_code,
                                    retry=retry + 1, wait=wait)
                        await _aio.sleep(wait)
                        continue
                    resp.raise_for_status()
                    if host_idx != self._active_host:
                        log.info("Failover to host", host=self._hosts[host_idx])
                        self._active_host = host_idx
                    return resp.json()
                except (httpx.ConnectError, httpx.ConnectTimeout) as e:
                    last_error = e
                    log.warning("Host unreachable, trying next",
                                host=self._hosts[host_idx], error=str(e))
                    break  # try next host
                except httpx.HTTPStatusError as e:
                    raise  # non-transient HTTP error
            else:
                # Retries exhausted on this host — raise last response
                last_error = httpx.HTTPStatusError(
                    f"Retries exhausted: HTTP {resp.status_code}",
                    request=resp.request, response=resp)
                break
        if last_error:
            raise last_error
        raise RuntimeError("No hosts configured")

    async def get(self, path: str, **kwargs) -> dict:
        return await self._request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs) -> dict:
        return await self._request("POST", path, **kwargs)

    # --- Health & Info ---

    async def test_connection(self) -> dict:
        """Test connectivity and return cluster info."""
        try:
            info = await self.get("/")
            health = await self.get("/_cluster/health")
            return {
                "connected": True,
                "cluster_name": info.get("cluster_name"),
                "version": info.get("version", {}).get("distribution", "")
                           + " " + info.get("version", {}).get("number", ""),
                "status": health.get("status"),
                "nodes": health.get("number_of_nodes"),
                "indices": health.get("active_shards"),
            }
        except Exception as e:
            return {"connected": False, "error": str(e)}

    # --- Index Operations ---

    async def list_indices(self, prefix: str = "graylog") -> list[dict]:
        """List indices matching prefix, with doc counts and time ranges."""
        data = await self.get(f"/_cat/indices/{prefix}_*?format=json&h=index,docs.count,store.size,status")
        indices = []
        for idx in data:
            index_name = idx.get("index", "")
            # Skip internal/system indices
            if index_name.startswith("."):
                continue
            indices.append({
                "index": index_name,
                "docs_count": int(idx.get("docs.count", 0) or 0),
                "store_size": idx.get("store.size", "0b"),
                "status": idx.get("status", ""),
            })
        # Sort by index name (which includes the rotation number)
        indices.sort(key=lambda x: x["index"])
        return indices

    async def get_index_time_range(self, index_name: str) -> tuple[str | None, str | None]:
        """Get the earliest and latest timestamp in an index."""
        try:
            min_resp = await self.post(f"/{index_name}/_search", json={
                "size": 0,
                "aggs": {
                    "min_ts": {"min": {"field": "timestamp"}},
                    "max_ts": {"max": {"field": "timestamp"}},
                }
            })
            aggs = min_resp.get("aggregations", {})
            min_ts = aggs.get("min_ts", {}).get("value_as_string")
            max_ts = aggs.get("max_ts", {}).get("value_as_string")
            return min_ts, max_ts
        except Exception:
            return None, None

    async def get_active_write_index(self, prefix: str = "graylog") -> str | None:
        """Get the current active write index (deflector target)."""
        try:
            data = await self.get(f"/_alias/{prefix}_deflector")
            # The alias points to the active index
            for index_name in data:
                return index_name
        except Exception:
            pass
        # Fallback: highest numbered index
        indices = await self.list_indices(prefix)
        if indices:
            return indices[-1]["index"]
        return None

    # --- Search with search_after ---

    async def iter_index_docs(
        self,
        index_name: str,
        batch_size: int = 300,
        delay_between_requests_ms: int = 100,
        query: dict | None = None,
        fields: list[str] | None = None,
        progress_callback: Any = None,
    ) -> AsyncIterator[list[dict]]:
        """Iterate all documents in an index using search_after pagination.

        No depth limit — can handle any number of documents.
        """
        # Use _doc as tiebreaker instead of _id. Sorting by _id forces
        # OpenSearch to load the entire _id field into fielddata (in-heap),
        # which blows the circuit breaker on large indices (e.g. 680K docs
        # → 1.6 GB fielddata > 1.5 GB limit → circuit_breaking_exception).
        # _doc is an implicit sort by index order — zero-cost, no fielddata.
        body: dict[str, Any] = {
            "size": batch_size,
            "sort": [
                {"timestamp": "asc"},
                {"_doc": "asc"},
            ],
        }

        if query:
            body["query"] = query
        else:
            body["query"] = {"match_all": {}}

        if fields:
            body["_source"] = fields

        total_fetched = 0
        search_after = None

        # Get total count first
        count_resp = await self.post(f"/{index_name}/_count", json={"query": body["query"]})
        total = count_resp.get("count", 0)

        if total == 0:
            return

        log.info("Fetching from index", index=index_name, total=total)

        while True:
            if search_after:
                body["search_after"] = search_after

            resp = await self.post(f"/{index_name}/_search", json=body)
            hits = resp.get("hits", {}).get("hits", [])

            if not hits:
                break

            # Extract _source documents.
            # We strip Graylog internal `gl2_*` metadata because they reference
            # the source cluster's nodes/inputs and are not meaningful in a
            # restored target. EXCEPTION: `gl2_message_id` is preserved so that
            # a future bulk-import path (writing directly to OpenSearch via
            # `_bulk`) can use it as a deterministic `_id` for deduplication —
            # re-importing the same archive overwrites instead of duplicating.
            # The GELF import path is unaffected because Graylog regenerates
            # all gl2_* fields on receive (including a new gl2_message_id).
            docs = []
            for hit in hits:
                doc = hit.get("_source", {})
                for key in list(doc.keys()):
                    if key.startswith("gl2_") and key != "gl2_message_id":
                        doc.pop(key)
                docs.append(doc)

            yield docs
            total_fetched += len(docs)

            if progress_callback:
                progress_callback(total_fetched, total)

            # Delay between requests to protect OpenSearch cluster
            if delay_between_requests_ms > 0:
                await asyncio.sleep(delay_between_requests_ms / 1000.0)

            # Set search_after to the sort values of the last hit
            search_after = hits[-1].get("sort")

            if not search_after or total_fetched >= total:
                break

        log.info("Index fetch completed", index=index_name, fetched=total_fetched)
