# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""OpenSearch direct client for log export with resource protection."""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from typing import Any, AsyncIterator

import httpx

from glogarch.core.config import OpenSearchConfig
from glogarch.utils.logging import get_logger

log = get_logger("opensearch.client")


class IncompleteIndexScan(Exception):
    """A scan returned fewer documents than the index said it held.

    The pagination cursor is `(timestamp, _doc)`, and `_doc` is a SHARD-LOCAL
    Lucene document id — it is NOT unique across shards. Two documents on
    different shards can therefore carry an identical sort key, and the next
    `search_after` request excludes BOTH, including the one that was never
    returned. On a multi-shard index that silently drops records, which for an
    archiving tool is the worst failure available.

    This exception does not prevent that; it makes it impossible to miss.
    Raised only on a SHORTFALL — reading more than `_count` reported is drift,
    not loss, and is merely logged.
    """

    def __init__(self, index: str, expected: int, fetched: int, shards=None):
        self.index, self.expected, self.fetched, self.shards = (
            index, expected, fetched, shards)
        missing = expected - fetched
        # Terse on purpose. The exporter wraps this as "Index <name> failed:
        # <msg>" and notification channels cut each error line at 80 chars —
        # repeating the index name here pushed the numbers past the cut, so
        # the operator saw that something failed but not that records went
        # missing. The index is still on the exception as `.index`.
        msg = (f"incomplete scan: {fetched:,} of {expected:,} docs "
               f"({missing:,} missing")
        msg += f", {shards} shards)" if shards and shards > 1 else ")"
        super().__init__(msg)


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
        n_hosts = len(self._hosts)
        for attempt in range(n_hosts):
            host_idx = (self._active_host + attempt) % n_hosts
            url = f"{self._hosts[host_idx]}{path}"
            host_exhausted = False  # transient failure on this host → try next
            for retry in range(max_retries):
                try:
                    resp = await self._client.request(method, url, **kwargs)
                    if resp.status_code in (429, 500, 502, 503):
                        last_error = httpx.HTTPStatusError(
                            f"HTTP {resp.status_code} from {self._hosts[host_idx]}",
                            request=resp.request, response=resp)
                        if retry < max_retries - 1:
                            wait = 2 ** retry
                            log.warning("Transient error, retrying",
                                        host=self._hosts[host_idx],
                                        status=resp.status_code,
                                        retry=retry + 1, wait=wait)
                            await _aio.sleep(wait)
                            continue
                        # Retries exhausted on THIS host — fail over to the next
                        # host instead of aborting. A single overloaded node
                        # (503/429 from a circuit breaker or GC pause) must not
                        # silently drop the whole index when a healthy node exists.
                        log.warning("Transient errors exhausted, failing over to next host",
                                    host=self._hosts[host_idx], status=resp.status_code)
                        host_exhausted = True
                        break
                    resp.raise_for_status()
                    if host_idx != self._active_host:
                        log.info("Failover to host", host=self._hosts[host_idx])
                        self._active_host = host_idx
                    return resp.json()
                except (httpx.ConnectError, httpx.ConnectTimeout) as e:
                    last_error = e
                    log.warning("Host unreachable, trying next",
                                host=self._hosts[host_idx], error=str(e))
                    host_exhausted = True
                    break  # try next host
                except httpx.HTTPStatusError:
                    raise  # non-transient HTTP error (4xx) — fail immediately
            if host_exhausted:
                continue  # advance outer loop to the next host
        # All hosts exhausted their retries — raise the last error seen.
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
        except Exception as e:
            log.debug("Could not resolve the deflector alias to a concrete index", error=str(e))
        # Fallback: highest numbered index
        indices = await self.list_indices(prefix)
        if indices:
            return indices[-1]["index"]
        return None

    # --- Search with search_after ---
    #
    # Page-size guards, shared by both scan paths. `batch_size` bounds the DOC
    # COUNT only; how many BYTES a page weighs depends on how wide the documents
    # are. At 10,000 docs a page is ~14 MB for typical 1.2 KB messages but ~90 MB
    # for 9 KB Windows Event Log records — a large fetch-phase heap spike on
    # OpenSearch and a big JSON parse on our side, on a box where the two often
    # share RAM.
    _TARGET_PAGE_BYTES = 16 * 1024 * 1024
    _MIN_PAGE_DOCS = 500

    @staticmethod
    def _hits_to_docs(hits: list[dict]) -> list[dict]:
        """Extract `_source` and strip Graylog internal `gl2_*` metadata.

        Those reference the SOURCE cluster's nodes/inputs and are meaningless in
        a restored target. EXCEPTION: `gl2_message_id` is preserved so the bulk
        import path can use it as a deterministic `_id` for deduplication —
        re-importing the same archive overwrites instead of duplicating. The
        GELF path is unaffected because Graylog regenerates all gl2_* on receive.
        """
        docs = []
        for hit in hits:
            doc = hit.get("_source", {})
            for key in list(doc.keys()):
                if key.startswith("gl2_") and key != "gl2_message_id":
                    doc.pop(key)
            docs.append(doc)
        return docs

    def _fit_page_size(self, hits: list[dict], current: int, ceiling: int,
                       target_bytes: int, index_name: str,
                       floor: int | None = None) -> int:
        """Right-size the NEXT page from what this one actually weighed.

        Adjusts in BOTH directions, and that matters. The per-shard scan starts
        each shard on a deliberately small first page (nothing has been measured
        yet, and N shards fetching a full wide-document page at once is exactly
        the heap spike this guard exists to prevent). If the size could only
        shrink, narrow documents would stay stuck on that small page forever:
        measured on a real 1.26M-doc index of 4 shards, that was 504 requests
        instead of 126 and turned a 90 s scan into 219 s. The bound that matters
        is BYTES in flight, not document count.
        """
        try:
            sample = hits[:20]
            avg = max(1, len(json.dumps(sample, default=str)) // len(sample))
            fit = max(floor or self._MIN_PAGE_DOCS,
                      min(ceiling, target_bytes // avg))
            if fit < current:
                log.info("Reducing OpenSearch page size for wide documents",
                         index=index_name, avg_doc_bytes=avg,
                         page_size=fit, was=current)
            return fit
        except Exception as e:
            # Never silently swallow: a bug here (e.g. a missing import) would
            # disable the guard invisibly while every test still passed.
            log.warning("Page-size adaptation failed", error=str(e))
        return current

    async def get_shard_count(self, index_name: str) -> int:
        """Number of PRIMARY shards, or 1 if it cannot be read.

        Falling back to 1 keeps the old single-cursor behaviour rather than
        inventing a shard layout — an unreadable setting must not change how an
        index is scanned.
        """
        try:
            s = await self.get(f"/{index_name}/_settings")
            n = int(next(iter(s.values()))["settings"]["index"]["number_of_shards"])
            return max(1, n)
        except Exception as e:
            log.debug("Could not read shard count; scanning as single-shard",
                      index=index_name, error=str(e))
            return 1

    async def iter_index_docs(
        self,
        index_name: str,
        batch_size: int = 300,
        delay_between_requests_ms: int = 100,
        query: dict | None = None,
        fields: list[str] | None = None,
        progress_callback: Any = None,
    ) -> AsyncIterator[list[dict]]:
        """Iterate every document in an index, in ascending timestamp order.

        No depth limit — `search_after`, so any number of documents.

        **Why the scan is per-shard on a multi-shard index.** The cursor sorts on
        `(timestamp, _doc)`, and `_doc` is a SHARD-LOCAL Lucene id: two documents
        on different shards can carry an identical sort key, and the next
        `search_after` then excludes BOTH — including the one never returned. On
        a 4-shard production index that silently dropped records, and because the
        chunks already written are recorded as covering their time range, dedup
        suppressed the gap on every later run. Scanning each shard separately
        (`preference=_shards:N|_primary`) makes `_doc` unique again, because
        within one shard it always was.

        `_primary` pins the copy: `_shards:N` alone may round-robin between
        primary and replica between requests, and their `_doc` order can differ —
        which would reintroduce exactly the bug being fixed.

        The per-shard streams are MERGED here, so this method still yields in
        global timestamp order. That is not cosmetic: the exporter closes and
        RECORDS a chunk archive the moment a timestamp crosses an hour boundary,
        so a scan that restarted at t0 for each shard would reopen chunks it had
        already written.

        Set `JT_OS_SCAN_SINGLE_CURSOR=1` to force the old single-cursor scan.
        That is an emergency escape hatch, not a tuning knob: it restores the
        record-dropping behaviour on multi-shard indices.
        """
        body: dict[str, Any] = {
            "size": batch_size,
            # `_doc` (not `_id`) as the tiebreaker: sorting by `_id` forces
            # OpenSearch to load the entire field into fielddata (in-heap),
            # which blows the circuit breaker on large indices (680K docs ->
            # 1.6 GB > 1.5 GB limit). `_doc` is index order — zero cost.
            "sort": [
                {"timestamp": "asc"},
                {"_doc": "asc"},
            ],
        }
        body["query"] = query if query else {"match_all": {}}
        if fields:
            body["_source"] = fields

        # Total count first — this is what the scan reconciles against at the end.
        count_resp = await self.post(f"/{index_name}/_count", json={"query": body["query"]})
        total = count_resp.get("count", 0)
        if total == 0:
            return

        shards = 1
        if os.environ.get("JT_OS_SCAN_SINGLE_CURSOR") != "1":
            shards = await self.get_shard_count(index_name)

        log.info("Fetching from index", index=index_name, total=total, shards=shards)

        total_fetched = 0
        per_shard_fetched: dict[int, int] = {}

        if shards > 1:
            scan = self._scan_shards_merged(
                index_name, body, shards, batch_size,
                delay_between_requests_ms, per_shard_fetched)
        else:
            scan = self._scan_single_cursor(
                index_name, body, batch_size, delay_between_requests_ms)

        async for docs in scan:
            yield docs
            total_fetched += len(docs)
            if progress_callback:
                progress_callback(total_fetched, total)

        # Reconcile what we actually read against what the index said it held.
        # Without this the scan reports success no matter how much it skipped,
        # and the exporter records the chunks it DID write as covering their
        # time range — so the gap is suppressed by dedup on every later run and
        # can never be noticed, let alone recovered. See IncompleteIndexScan.
        #
        # This runs only on natural completion. A consumer that breaks out of
        # the loop (cancel, backpressure abort) closes the generator, so an
        # intentional early stop can never be reported as data loss.
        if total_fetched < total:
            log.error(
                "Index scan returned fewer documents than the index reported. "
                "The chunks already written are valid, but this index is NOT "
                "completely archived for this run.",
                index=index_name, expected=total, fetched=total_fetched,
                missing=total - total_fetched, shards=shards,
                per_shard=per_shard_fetched or None)
            raise IncompleteIndexScan(index_name, total, total_fetched, shards)

        if total_fetched > total:
            # More than the pre-scan count: documents arrived, or the count was
            # stale. Nothing is lost, so this is information, not a failure.
            log.info("Index held more documents than the pre-scan count",
                     index=index_name, counted=total, fetched=total_fetched)

        log.info("Index fetch completed", index=index_name, fetched=total_fetched,
                 shards=shards)

    async def _scan_single_cursor(
        self, index_name: str, body: dict, batch_size: int, delay_ms: int,
    ) -> AsyncIterator[list[dict]]:
        """One `search_after` cursor over the whole index (single-shard only)."""
        body = dict(body)
        search_after = None
        while True:
            if search_after:
                body["search_after"] = search_after

            resp = await self.post(f"/{index_name}/_search", json=body)
            hits = resp.get("hits", {}).get("hits", [])
            if not hits:
                break

            body["size"] = self._fit_page_size(
                hits, body["size"], batch_size, self._TARGET_PAGE_BYTES, index_name)

            yield self._hits_to_docs(hits)

            if delay_ms > 0:
                await asyncio.sleep(delay_ms / 1000.0)

            # Terminate ONLY when the sort cursor is gone or the page ran dry.
            # Do NOT stop at `fetched >= total`: `total` is a point-in-time
            # `_count`; if it under-counts (concurrent merge/refresh drift) the
            # loop would stop early and skip the tail.
            search_after = hits[-1].get("sort")
            if not search_after:
                break

    async def _scan_shards_merged(
        self, index_name: str, body: dict, shards: int, batch_size: int,
        delay_ms: int, fetched_out: dict[int, int],
    ) -> AsyncIterator[list[dict]]:
        """One cursor PER SHARD, merged back into global timestamp order.

        Every shard keeps a page IN FLIGHT while we merge the one it already
        delivered. That is the whole performance story, and it was measured, not
        reasoned about, on a real 4-shard 1.26M-document index:

            fan-out, one cursor (the old, lossy scan)   81-95 s
            per-shard, refilled only when a buffer ran dry  180 s
            per-shard, all four pages in flight             52 s

        A fan-out `_search` queries all N shards in parallel by construction.
        Refilling a shard only once its buffer empties throws that away — the
        shards drain one at a time, so the scan goes serial and takes twice as
        long at the SAME request count. Prefetching restores the parallelism,
        and the result is FASTER than the query it replaces, because each
        request collects from one shard instead of asking all N for a full page
        and discarding (N-1)/N of it at the coordinator.

        Peak memory is held at the old single-page budget: with a page in hand
        AND a page in flight per shard, the per-shard byte target is
        `_TARGET_PAGE_BYTES / (2 * shards)`, so 2N buffers weigh what one page
        used to on the co-located VM this product keeps getting OOM-killed on.
        """
        # A page in hand + a page in flight, per shard.
        per_shard_target = max(1, self._TARGET_PAGE_BYTES // (2 * shards))
        # The 500-document floor is a THROUGHPUT floor, sized for one cursor.
        # Applied unchanged to every shard it becomes a MEMORY floor instead:
        # 2 x 4 shards x 500 x 9 KB documents is 36 MB in flight against a
        # 16 MB budget, on the box that gets OOM-killed. Divide it — the pages
        # are fetched in parallel now, so smaller ones cost less than they did.
        per_shard_floor = max(100, self._MIN_PAGE_DOCS // shards)
        state = [{
            "shard": s,
            "hits": [],
            "pos": 0,
            "after": None,
            "done": False,
            "task": None,
            "size": max(per_shard_floor, batch_size // shards),
            "fetched": 0,
        } for s in range(shards)]

        async def fetch(st: dict, after) -> list[dict]:
            b = dict(body)
            b["size"] = st["size"]
            if after:
                b["search_after"] = after
            if delay_ms > 0:
                await asyncio.sleep(delay_ms / 1000.0)
            resp = await self.post(
                f"/{index_name}/_search", json=b,
                # `_primary` pins the copy — see iter_index_docs' docstring.
                params={"preference": f"_shards:{st['shard']}|_primary"})
            return resp.get("hits", {}).get("hits", [])

        def prefetch(st: dict) -> None:
            """Start the NEXT page for this shard, now, while we merge."""
            if st["done"] or st["task"] is not None:
                return
            st["task"] = asyncio.create_task(fetch(st, st["after"]))

        async def land(st: dict) -> None:
            """Take delivery of the page in flight and queue the one after it."""
            prefetch(st)
            hits = await st["task"]
            st["task"] = None
            if not hits:
                st["hits"], st["pos"], st["done"] = [], 0, True
                return
            st["size"] = self._fit_page_size(
                hits, st["size"], batch_size, per_shard_target, index_name,
                floor=per_shard_floor)
            st["hits"], st["pos"] = hits, 0
            st["after"] = hits[-1].get("sort")
            st["fetched"] += len(hits)
            fetched_out[st["shard"]] = st["fetched"]
            if not st["after"]:
                st["done"] = True      # cannot page further; drain, then stop
            else:
                prefetch(st)

        try:
            for st in state:                      # first pages, all at once
                prefetch(st)

            out: list[dict] = []
            while True:
                # Every live shard must hold a candidate before we can know
                # which head is globally smallest.
                hungry = [st for st in state
                          if not st["done"] and st["pos"] >= len(st["hits"])]
                if hungry:
                    await asyncio.gather(*(land(st) for st in hungry))

                live = [st for st in state if st["pos"] < len(st["hits"])]
                if not live:
                    break

                # Merge key is the TIMESTAMP plus the shard number. Deliberately
                # not the raw sort array: `_doc` is shard-local, so comparing it
                # across shards is meaningless (and could compare mismatched
                # types). Order among equal timestamps does not matter — hourly
                # chunking is all that depends on this ordering.
                def _key(st: dict):
                    sort = st["hits"][st["pos"]].get("sort") or [0]
                    return (sort[0], st["shard"])

                best = min(live, key=_key)
                out.append(best["hits"][best["pos"]])
                best["pos"] += 1

                if len(out) >= batch_size:
                    yield self._hits_to_docs(out)
                    out = []

            if out:
                yield self._hits_to_docs(out)
        finally:
            # Cancel and the backpressure guard close this generator mid-scan.
            # An in-flight page must not outlive it — an orphaned task would
            # log "Task exception was never retrieved" long after the job the
            # operator cancelled appeared to stop.
            for st in state:
                if st["task"] is not None:
                    st["task"].cancel()
