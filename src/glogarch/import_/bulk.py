"""OpenSearch direct bulk import — bypasses Graylog entirely.

When the source archive already contains fully-processed Graylog documents
(e.g., when exported via OpenSearch Direct mode), there's no point in re-running
them through Graylog's input → processor → indexer chain. Direct bulk write to
OpenSearch is 5-10x faster and avoids the journal pressure / process buffer
overflow that GELF imports cause.

Trade-offs vs GELF import:
    + 5-10x faster (no GELF framing, no Graylog journal write)
    + Per-document success/failure from _bulk response (precise reconciliation)
    + No back-pressure / no auto-pause complexity
    + No alert / pipeline / extractor side effects
    - Skips ALL Graylog processing rules (pipelines, extractors, stream routing)
    - Requires direct OpenSearch credentials in addition to Graylog API
    - `gl2_*` fields (other than gl2_message_id from v1.1+ archives) are missing

For zero-loss compliance, BulkImporter:
    1. Uses preserved `gl2_message_id` (v1.1+ archives) as the OpenSearch _id
       so re-imports overwrite instead of duplicate.
    2. Adds a `_jt_glogarch_imported_at` marker field for traceability.
    3. Reads per-document errors from _bulk response and reports them as
       Compliance violations in the job result.
"""

from __future__ import annotations

import asyncio
import gzip
import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable

import httpx

from glogarch.utils.logging import get_logger

log = get_logger("import.bulk")


class BulkImportResult:
    def __init__(self):
        self.archives_processed: int = 0
        self.messages_sent: int = 0
        self.messages_indexed: int = 0
        self.messages_failed: int = 0
        self.errors: list[str] = []
        self.failure_samples: list[str] = []
        self.bulk_requests: int = 0
        self.bytes_sent: int = 0
        self.duration_sec: float = 0.0


class BulkImporter:
    """Direct OpenSearch _bulk writer."""

    # OpenSearch typically accepts up to ~100MB bulk requests; we keep ours
    # well under that to leave headroom for large messages.
    DEFAULT_BATCH_DOCS = 5000
    DEFAULT_BATCH_BYTES_LIMIT = 50 * 1024 * 1024  # 50 MB

    def __init__(
        self,
        opensearch_url: str,
        os_username: str = "",
        os_password: str = "",
        target_index_pattern: str = "graylog",
        dedup_strategy: str = "id",  # "id", "none", "fail"
        batch_docs: int = DEFAULT_BATCH_DOCS,
        marker_field: str | None = "_jt_glogarch_imported_at",
        marker_value: str | None = None,
        verify_tls: bool = False,
    ):
        self.opensearch_url = opensearch_url.rstrip("/")
        self.os_username = os_username
        self.os_password = os_password
        self.target_index_pattern = target_index_pattern
        self.dedup_strategy = dedup_strategy
        self.batch_docs = batch_docs
        self.marker_field = marker_field
        self.marker_value = marker_value or datetime.utcnow().isoformat() + "Z"
        self.verify_tls = verify_tls

    def _client(self) -> httpx.AsyncClient:
        auth = None
        if self.os_username:
            auth = (self.os_username, self.os_password)
        return httpx.AsyncClient(
            verify=self.verify_tls,
            timeout=120,
            auth=auth,
            headers={"Content-Type": "application/x-ndjson"},
        )

    @staticmethod
    def _index_name_for_doc(doc: dict, target_pattern: str) -> str:
        """Build the actual index name for a doc.
        Uses doc's timestamp to create a daily index under the pattern.
        """
        ts = doc.get("timestamp", "")
        if ts and len(ts) >= 10:
            # Extract YYYY-MM-DD
            day = ts[:10].replace("-", "_")
        else:
            day = datetime.utcnow().strftime("%Y_%m_%d")
        return f"{target_pattern}_{day}"

    def _build_bulk_body(
        self, docs: list[dict]
    ) -> tuple[bytes, int]:
        """Serialize a batch of docs into NDJSON bulk format.
        Returns (body_bytes, doc_count).
        """
        lines: list[str] = []
        for doc in docs:
            # Inject the marker field
            if self.marker_field:
                doc[self.marker_field] = self.marker_value

            index_name = self._index_name_for_doc(doc, self.target_index_pattern)

            # Action line
            action: dict = {"index": {"_index": index_name}}

            if self.dedup_strategy == "id":
                # Use gl2_message_id as deterministic _id (v1.1+ archives)
                msg_id = doc.get("gl2_message_id")
                if msg_id:
                    action["index"]["_id"] = msg_id
                # else: let OpenSearch auto-generate (graceful degrade for v1.0 archives)

            lines.append(json.dumps(action, ensure_ascii=False))
            lines.append(json.dumps(doc, ensure_ascii=False, default=str))

        body = ("\n".join(lines) + "\n").encode("utf-8")
        return body, len(docs)

    async def _send_bulk(
        self, client: httpx.AsyncClient, body: bytes
    ) -> tuple[int, int, list[str]]:
        """POST one bulk request. Returns (indexed, failed, error_samples)."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                r = await client.post(
                    f"{self.opensearch_url}/_bulk",
                    content=body,
                )
                if r.status_code == 429:
                    # OpenSearch overloaded — exponential backoff
                    wait = 2 ** attempt
                    log.warning("OpenSearch 429, backing off", attempt=attempt, wait_sec=wait)
                    await asyncio.sleep(wait)
                    continue
                r.raise_for_status()
                resp = r.json()
                break
            except httpx.HTTPStatusError as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise RuntimeError(f"Bulk request failed after {max_retries} attempts: {e}")
            except (httpx.RequestError, asyncio.TimeoutError) as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise RuntimeError(f"Bulk request network error after {max_retries} attempts: {e}")
        else:
            raise RuntimeError("Bulk request failed (retries exhausted)")

        # Parse response
        items = resp.get("items", [])
        indexed = 0
        failed = 0
        error_samples: list[str] = []
        for item in items:
            op = item.get("index") or item.get("create") or {}
            status = op.get("status", 0)
            if 200 <= status < 300:
                indexed += 1
            else:
                failed += 1
                if len(error_samples) < 5:
                    err = op.get("error", {})
                    error_samples.append(
                        f"{err.get('type', '?')}: {err.get('reason', '?')[:200]}"
                    )
        return indexed, failed, error_samples

    @staticmethod
    def _read_archive(path: Path):
        """Yield messages from a .json.gz archive file."""
        with gzip.open(path, "rt", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("messages", []) if isinstance(data, dict) else []

    async def _ensure_index(self, client: httpx.AsyncClient, index_name: str) -> None:
        """Pre-create an index if it doesn't exist.
        Required because Graylog clusters typically have
        action.auto_create_index = false. The OpenSearch index template
        installed by preflight applies on creation, so we don't need to
        specify mappings here.
        """
        # HEAD first (cheap)
        r = await client.head(f"{self.opensearch_url}/{index_name}")
        if r.status_code == 200:
            return
        # PUT to create
        r = await client.put(
            f"{self.opensearch_url}/{index_name}",
            content=b"{}",
        )
        if r.status_code in (200, 201):
            log.info("Created bulk target index", index=index_name)
            return
        # 400 with "resource_already_exists_exception" is ok (race condition)
        if r.status_code == 400:
            try:
                err = r.json().get("error", {}).get("type", "")
                if "resource_already_exists" in err:
                    return
            except Exception:
                pass
        raise RuntimeError(
            f"Failed to create index {index_name}: HTTP {r.status_code}: {r.text[:300]}"
        )

    async def import_archives(
        self,
        archive_paths: list[Path],
        progress_callback: Callable[[dict], None] | None = None,
    ) -> BulkImportResult:
        """Bulk-import every archive in archive_paths."""
        result = BulkImportResult()
        start = time.time()

        # Compute total messages + collect unique index names so we can
        # pre-create them (action.auto_create_index is typically false on
        # Graylog clusters).
        total_msgs = 0
        index_names: set[str] = set()
        for p in archive_paths:
            try:
                msgs = self._read_archive(p)
                total_msgs += len(msgs)
                for m in msgs:
                    if isinstance(m, dict):
                        index_names.add(self._index_name_for_doc(m, self.target_index_pattern))
            except Exception as e:
                log.warning("Cannot pre-count archive", path=str(p), error=str(e))

        if total_msgs == 0:
            log.warning("No messages to import")
            return result

        log.info("Bulk import starting",
                 archives=len(archive_paths),
                 total_messages=total_msgs,
                 batch_docs=self.batch_docs,
                 target_pattern=self.target_index_pattern,
                 indices_to_create=len(index_names))

        async with self._client() as client:
            # Pre-create all target indices
            for idx_name in sorted(index_names):
                await self._ensure_index(client, idx_name)
            for arch_idx, path in enumerate(archive_paths):
                try:
                    msgs = self._read_archive(path)
                except Exception as e:
                    err = f"Failed to read archive {path}: {e}"
                    log.error(err)
                    result.errors.append(err)
                    continue

                # Send in batches
                for batch_start in range(0, len(msgs), self.batch_docs):
                    batch = msgs[batch_start:batch_start + self.batch_docs]
                    body, count = self._build_bulk_body(batch)
                    result.bytes_sent += len(body)
                    result.bulk_requests += 1

                    indexed, failed, samples = await self._send_bulk(client, body)
                    result.messages_sent += count
                    result.messages_indexed += indexed
                    result.messages_failed += failed
                    for s in samples:
                        if s not in result.failure_samples and len(result.failure_samples) < 20:
                            result.failure_samples.append(s)

                    if progress_callback:
                        progress_callback({
                            "phase": "bulk_writing",
                            "archive_index": arch_idx + 1,
                            "total_archives": len(archive_paths),
                            "messages_done": result.messages_sent,
                            "messages_total": total_msgs,
                            "pct": (result.messages_sent / max(total_msgs, 1)) * 100,
                            "indexed": result.messages_indexed,
                            "failed": result.messages_failed,
                        })

                result.archives_processed += 1

        result.duration_sec = time.time() - start
        log.info("Bulk import completed",
                 archives=result.archives_processed,
                 sent=result.messages_sent,
                 indexed=result.messages_indexed,
                 failed=result.messages_failed,
                 duration=f"{result.duration_sec:.1f}s")
        return result

    async def verify_opensearch(self) -> tuple[bool, str]:
        """Quick reachability + auth check."""
        try:
            async with self._client() as c:
                r = await c.get(f"{self.opensearch_url}/")
                if r.status_code == 401:
                    return False, "OpenSearch authentication failed (401)"
                if r.status_code >= 400:
                    return False, f"OpenSearch HTTP {r.status_code}: {r.text[:200]}"
                # Sanity check: should return cluster info
                d = r.json()
                if "cluster_name" not in d and "name" not in d:
                    return False, f"Unexpected OpenSearch response: {str(d)[:200]}"
                return True, ""
        except Exception as e:
            return False, f"Cannot reach OpenSearch: {e}"
