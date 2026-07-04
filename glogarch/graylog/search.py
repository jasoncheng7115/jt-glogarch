"""Graylog 6.x/7.x search API with time-based pagination."""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Any, AsyncIterator, Callable

from glogarch.graylog.client import GraylogClient
from glogarch.graylog.system import SystemMonitor
from glogarch.utils.logging import get_logger

log = get_logger("graylog.search")

# OpenSearch/Elasticsearch default index.max_result_window. Graylog's universal
# search returns 500 "Result window is too large" when (from + size) exceeds it.
# We never issue a request with offset + batch beyond this.
RESULT_WINDOW = 10000
# Kept for backward compatibility (older references); pagination now bounds by
# RESULT_WINDOW so that offset + batch never crosses the ceiling.
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

        # Millisecond precision is REQUIRED. Truncating to `.000Z` (whole second)
        # makes deep-pagination window advancement re-fetch from the start of the
        # boundary second, duplicating every message between second.000 and the
        # actual boundary millisecond. With ms precision, `from` lands exactly on
        # the last-fetched timestamp and carry-dedup removes only that ms's overlap.
        time_from_str = self._fmt_ts(time_from)
        time_to_str = self._fmt_ts(time_to)

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
        fetched_total = 0

        # First, get total count
        total = await self.count_messages(query, time_from, time_to, streams)
        if total == 0:
            log.info("Total messages to fetch", total=0)
            return
        log.info("Total messages to fetch", total=total)

        # Never let a request's (from + size) exceed the OpenSearch/Elasticsearch
        # result window, or Graylog returns 500 "Result window is too large". The
        # effective batch is clamped so even offset 0 is safe.
        eff_batch = min(batch_size, RESULT_WINDOW)

        # When a window fills to the result-window ceiling we advance the next
        # window to the EXACT timestamp of the last message fetched (NOT +1ms).
        # Advancing by +1ms silently drops every message that shares that same
        # millisecond beyond the ceiling — a real data-loss bug on high-volume
        # inputs. Instead we re-include the boundary millisecond and skip exactly
        # the message ids already emitted at that timestamp, so no message in the
        # boundary millisecond is ever lost or duplicated.
        carry_ids: set[str] = set()
        carry_boundary: str | None = None

        while current_from < time_to:
            offset = 0
            last_ts = None
            hit_window = False
            # Identities of emitted messages sharing the maximum timestamp seen
            # in THIS window — carried forward if we hit the ceiling.
            win_max_ts: str | None = None
            win_max_ids: set[str] = set()

            while True:
                # Stop paging this time window before (offset + batch) would cross
                # the result window; we then advance the window by timestamp.
                if offset + eff_batch > RESULT_WINDOW:
                    hit_window = True
                    break

                result = await self.search_messages(
                    query=query,
                    time_from=current_from,
                    time_to=time_to,
                    streams=streams,
                    fields=fields,
                    limit=eff_batch,
                    offset=offset,
                )

                raw = result.messages
                if not raw:
                    # No more messages in this time window
                    current_from = time_to  # Exit outer loop
                    break

                # Page by RAW fetched count so the result-window ceiling math
                # stays correct even when we skip boundary duplicates.
                offset += len(raw)
                last_ts = raw[-1].get("timestamp") or last_ts

                # Drop boundary-overlap duplicates carried from the previous
                # window (only messages at the exact carry timestamp), and track
                # the ids at this window's maximum timestamp.
                emit = []
                for msg in raw:
                    mts = msg.get("timestamp")
                    ident = self._msg_identity(msg)
                    if carry_ids and mts == carry_boundary and ident in carry_ids:
                        continue
                    emit.append(msg)
                    if mts is not None:
                        if win_max_ts is None or mts > win_max_ts:
                            win_max_ts = mts
                            win_max_ids = {ident}
                        elif mts == win_max_ts:
                            win_max_ids.add(ident)

                if emit:
                    yield emit
                    fetched_total += len(emit)
                    if progress_callback and total > 0:
                        progress_callback(min(fetched_total, total), total)

                # Mandatory delay between requests to protect Graylog memory
                if self._delay_ms > 0:
                    await asyncio.sleep(self._delay_ms / 1000.0)

                # A short page is the reliable end-of-window signal. Do NOT rely
                # on `offset >= result.total`: `total` is a live per-request count
                # that can shrink mid-pagination if an index rotates/retention-
                # deletes, which would terminate the window early and drop its tail.
                if len(raw) < eff_batch:
                    current_from = time_to  # Exit outer loop
                    break

            # Hit the result-window ceiling for this window — advance the time
            # window to the last message's EXACT timestamp and carry its ids.
            if hit_window:
                new_from = self._parse_timestamp(last_ts) if last_ts else None
                if new_from is None:
                    # Unparseable boundary timestamp: raising surfaces the problem
                    # instead of silently truncating the chunk (which was the old
                    # behaviour — a `break` that dropped the rest of the window).
                    raise RuntimeError(
                        f"Cannot parse boundary timestamp {last_ts!r} during deep "
                        f"pagination; aborting to avoid silent data loss.")
                if new_from > current_from:
                    carry_ids = set(win_max_ids) if win_max_ts == last_ts else set()
                    carry_boundary = last_ts if carry_ids else None
                    log.info("Advancing time window for deep pagination",
                             old_from=str(current_from), new_from=str(new_from),
                             carry=len(carry_ids), fetched_so_far=fetched_total)
                    current_from = new_from
                else:
                    # The entire 10K result window is a single millisecond
                    # (>RESULT_WINDOW messages share one ms) — offset pagination
                    # cannot advance without risking loss. Surface it loudly.
                    raise RuntimeError(
                        f"More than {RESULT_WINDOW} messages share timestamp "
                        f"{last_ts}; cannot paginate safely. Reduce "
                        f"chunk_duration_minutes or use OpenSearch export mode.")

    @staticmethod
    def _fmt_ts(dt: datetime) -> str:
        """Format a datetime for the Graylog absolute-search API at millisecond
        precision (Graylog/Joda accepts `...S.SSSZ`, not microseconds)."""
        return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"

    @staticmethod
    def _msg_identity(msg: dict) -> str:
        """Stable dedup identity for a message across window-boundary re-fetches."""
        mid = msg.get("gl2_message_id") or msg.get("_id")
        if mid:
            return str(mid)
        try:
            return json.dumps(msg, sort_keys=True, default=str)
        except Exception:
            return repr(sorted((k, str(v)) for k, v in msg.items()))

    # ISO-8601: date, time, optional fractional seconds (ANY length), optional
    # timezone. Used as a robust fallback when the fast strptime paths miss.
    _TS_RE = re.compile(
        r"^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})"
        r"(?:\.(\d+))?"
        r"(Z|[+-]\d{2}:?\d{2})?$"
    )

    @staticmethod
    def _parse_timestamp(ts_str: str) -> datetime | None:
        """Parse a Graylog timestamp string to a naive-UTC datetime.

        Handles Graylog's normal millisecond output plus any other ISO-8601
        shape (no fraction, microseconds, nanoseconds, explicit offset). Python
        3.10's ``datetime.fromisoformat`` rejects >6 fractional digits, so we
        parse explicitly rather than relying on it.
        """
        if not ts_str:
            return None
        s = ts_str.strip()
        for fmt in (
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%f+00:00",
        ):
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                continue
        m = GraylogSearch._TS_RE.match(s)
        if not m:
            return None
        y, mo, d, h, mi, sec = (int(m.group(i)) for i in range(1, 7))
        frac = m.group(7) or ""
        micros = int((frac + "000000")[:6]) if frac else 0
        try:
            dt = datetime(y, mo, d, h, mi, sec, micros)
        except ValueError:
            return None
        tz = m.group(8)
        if tz and tz != "Z":
            # Normalise an explicit offset to naive UTC.
            sign = 1 if tz[0] == "+" else -1
            digits = tz[1:].replace(":", "")
            dt = dt - sign * timedelta(hours=int(digits[:2]), minutes=int(digits[2:4]))
        return dt
