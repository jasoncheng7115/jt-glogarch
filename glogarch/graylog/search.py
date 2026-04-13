"""Graylog 6.x/7.x search API with time-based pagination."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any, AsyncIterator, Callable

from glogarch.graylog.client import GraylogClient
from glogarch.graylog.system import SystemMonitor
from glogarch.utils.logging import get_logger

log = get_logger("graylog.search")

# Maximum offset Graylog allows before returning 500 errors
# Graylog returns 500 when offset + limit > 10000
MAX_SAFE_OFFSET = 9500


class SearchResult:
    """Container for search results."""

    def __init__(self, messages: list[dict], total: int):
        self.messages = messages
        self.total = total


class GraylogSearch:
    """Paginated search using Graylog 6.x/7.x Universal Search API.

    Uses time-based pagination to avoid Graylog's deep pagination limit.
    """

    def __init__(self, client: GraylogClient, system_monitor: SystemMonitor | None = None,
                 delay_between_requests_ms: int = 200):
        self.client = client
        self.system_monitor = system_monitor
        self._delay_ms = delay_between_requests_ms

    async def search_messages(
        self,
        query: str,
        time_from: datetime,
        time_to: datetime,
        streams: list[str] | None = None,
        fields: list[str] | None = None,
        limit: int = 1000,
        offset: int = 0,
        sort_field: str = "timestamp",
        sort_order: str = "asc",
    ) -> SearchResult:
        """Execute a search using the Universal Absolute Search API (Graylog 6.x/7.x)."""
        # Adaptive backoff check
        if self.system_monitor:
            cpu = await self.system_monitor.get_cpu_percent()
            await self.client.rate_limiter.adaptive_backoff(cpu)

        time_from_str = time_from.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        time_to_str = time_to.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        params: dict[str, Any] = {
            "query": query,
            "from": time_from_str,
            "to": time_to_str,
            "limit": limit,
            "offset": offset,
            "sort": f"{sort_field}:{sort_order}",
        }

        if streams:
            filter_str = " OR ".join(f"streams:{sid}" for sid in streams)
            params["filter"] = filter_str

        if fields:
            params["fields"] = ",".join(fields)

        try:
            data = await self.client.get("/api/search/universal/absolute", params=params)
            messages = self._extract_messages(data, fields)
            total = data.get("total_results", 0)

            log.debug("Search completed", query=query, offset=offset,
                      limit=limit, returned=len(messages), total=total)
            return SearchResult(messages, total)

        except Exception as e:
            log.error("Search failed", error=str(e), query=query)
            raise

    def _extract_messages(self, data: dict, fields: list[str] | None = None) -> list[dict]:
        """Extract messages from Universal Search API response."""
        messages: list[dict] = []
        for msg_wrapper in data.get("messages", []):
            msg = msg_wrapper.get("message", {})
            if fields:
                msg = {k: v for k, v in msg.items() if k in fields or k == "timestamp"}
            # Strip Graylog internal `gl2_*` metadata that references source-
            # cluster nodes/inputs. EXCEPTION: `gl2_message_id` is preserved so
            # a future bulk-import path can use it as a deterministic `_id` for
            # OpenSearch deduplication (re-importing same archive overwrites
            # instead of duplicating). GELF import is unaffected — Graylog
            # regenerates all gl2_* on receive.
            for key in list(msg.keys()):
                if key.startswith("gl2_") and key != "gl2_message_id":
                    msg.pop(key)
            messages.append(msg)
        return messages

    async def count_messages(
        self,
        query: str,
        time_from: datetime,
        time_to: datetime,
        streams: list[str] | None = None,
    ) -> int:
        """Count messages matching query in time range."""
        result = await self.search_messages(
            query=query, time_from=time_from, time_to=time_to,
            streams=streams, limit=1, offset=0,
        )
        return result.total

    async def iter_all_messages(
        self,
        query: str,
        time_from: datetime,
        time_to: datetime,
        streams: list[str] | None = None,
        fields: list[str] | None = None,
        batch_size: int = 1000,
        progress_callback: Any = None,
    ) -> AsyncIterator[list[dict]]:
        """Iterate through all messages using time-based pagination.

        Uses offset pagination within safe limits, then advances the time window
        using the last message's timestamp to avoid Graylog's deep pagination errors.
        """
        current_from = time_from
        total = None
        fetched_total = 0

        # First, get total count
        total = await self.count_messages(query, time_from, time_to, streams)
        if total == 0:
            log.info("Total messages to fetch", total=0)
            return
        log.info("Total messages to fetch", total=total)

        while current_from < time_to:
            offset = 0

            while True:
                # Safety: don't exceed Graylog's offset limit
                if offset >= MAX_SAFE_OFFSET:
                    break

                result = await self.search_messages(
                    query=query,
                    time_from=current_from,
                    time_to=time_to,
                    streams=streams,
                    fields=fields,
                    limit=batch_size,
                    offset=offset,
                )

                if not result.messages:
                    # No more messages in this time window
                    current_from = time_to  # Exit outer loop
                    break

                yield result.messages
                fetched_total += len(result.messages)
                offset += len(result.messages)

                if progress_callback and total > 0:
                    progress_callback(fetched_total, total)

                # Mandatory delay between requests to protect Graylog memory
                if self._delay_ms > 0:
                    await asyncio.sleep(self._delay_ms / 1000.0)

                if offset >= result.total:
                    # All messages fetched
                    current_from = time_to  # Exit outer loop
                    break

            # If we hit the offset limit, advance time window using last message timestamp
            if offset >= MAX_SAFE_OFFSET:
                # Get the last batch to find the latest timestamp
                last_result = await self.search_messages(
                    query=query,
                    time_from=current_from,
                    time_to=time_to,
                    streams=streams,
                    fields=["timestamp"] if not fields else fields,
                    limit=1,
                    offset=MAX_SAFE_OFFSET - 1,
                    sort_order="asc",
                )
                if last_result.messages:
                    last_ts = last_result.messages[0].get("timestamp", "")
                    new_from = self._parse_timestamp(last_ts)
                    # Advance by 1ms to avoid re-fetching messages at exact boundary
                    if new_from:
                        new_from = new_from + timedelta(milliseconds=1)
                    if new_from and new_from > current_from:
                        log.info("Advancing time window for deep pagination",
                                 old_from=str(current_from), new_from=str(new_from),
                                 fetched_so_far=fetched_total)
                        current_from = new_from
                    else:
                        # Timestamp didn't advance, avoid infinite loop
                        log.warning("Cannot advance time window, stopping",
                                    timestamp=last_ts, fetched=fetched_total)
                        break
                else:
                    break

    @staticmethod
    def _parse_timestamp(ts_str: str) -> datetime | None:
        """Parse Graylog timestamp string to datetime."""
        for fmt in (
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%f+00:00",
        ):
            try:
                return datetime.strptime(ts_str, fmt)
            except ValueError:
                continue
        return None
