# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Make wide-window (e.g. 3-month) reports tractable — without lying.

A dashboard widget saved with a FIXED time interval (say 5 minutes) was tuned
for interactive use over a day. Rendered over 90 days it asks Graylog for
25,920 buckets — multiplied by every widget in the SAME search execution. That
is what pushed a customer's 3-month report past the search wait and produced a
silently truncated result (see CHANGELOG 1.13.69).

Two mechanisms, both HONEST by construction:

1. **Interval coarsening** (`coarsen_intervals`): rewrite fixed `timeunit`
   pivots whose bucket count over the report window exceeds a cap, and RECORD
   every change so the widget's caption can say "interval adjusted 5m -> 6h".
   `auto` intervals are left alone — Graylog already scales those.

2. **Time slicing** (`slice_windows` + `merge_search_type_results`): split the
   window into slices executed separately, then merge. Only aggregations that
   merge EXACTLY are eligible (`mergeable_functions`): count/sum/min/max over
   disjoint time slices are exact; avg/cardinality/percentiles are NOT
   derivable from per-slice values and must never be stitched — those search
   types run un-sliced instead, and the caller labels them. A wrong number
   that looks plausible is strictly worse than a slow report.
"""
from __future__ import annotations

import copy
import math
from datetime import datetime, timedelta

_UNIT_SECONDS = {
    "seconds": 1, "minutes": 60, "hours": 3600,
    "days": 86400, "weeks": 604800, "months": 2592000, "years": 31536000,
}

# Nice ladder of intervals to coarsen onto (seconds). Chosen so the result is
# something an operator would themselves pick — never "17 minutes".
_NICE_STEPS = [
    60, 300, 600, 900, 1800, 3600, 2 * 3600, 3 * 3600, 6 * 3600, 12 * 3600,
    86400, 2 * 86400, 7 * 86400, 30 * 86400,
]

DEFAULT_MAX_BUCKETS = 500


_ABBR_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}


def _interval_seconds(iv: dict) -> int | None:
    """Seconds of a fixed `timeunit` interval; None for auto/unknown.

    Graylog uses TWO schemas for the same thing (verified against a live 6.3
    API — creating a search with the widget-config schema is rejected with
    "Known properties include: timeunit, type"):
      - search definition (/api/views/search): {"type":"timeunit","timeunit":"5m"}
      - widget config (view state):            {"type":"timeunit","value":5,"unit":"minutes"}
    We coarsen the SEARCH DEFINITION, so the combined-string form is the one
    that matters — parsing only the widget form made coarsening silently never
    fire on real data.
    """
    if not isinstance(iv, dict) or iv.get("type") != "timeunit":
        return None
    tu = iv.get("timeunit")
    if isinstance(tu, str) and len(tu) >= 2:
        unit = _ABBR_SECONDS.get(tu[-1].lower())
        num = tu[:-1]
        if unit and num.isdigit() and int(num) > 0:
            return int(num) * unit
        return None
    val = iv.get("value")
    unit = _UNIT_SECONDS.get(str(iv.get("unit") or "").lower())
    if not isinstance(val, (int, float)) or val <= 0 or not unit:
        return None
    return int(val * unit)


def _nice_interval_at_least(seconds: float) -> int:
    for step in _NICE_STEPS:
        if step >= seconds:
            return step
    return _NICE_STEPS[-1]


def _fmt_interval(seconds: int, lang: str = "en") -> str:
    zh = lang == "zh-TW"
    for unit, div in (("d", 86400), ("h", 3600), ("m", 60), ("s", 1)):
        if seconds % div == 0 and seconds >= div:
            n = seconds // div
            if zh:
                return f"{n}{dict(d='天', h='小時', m='分鐘', s='秒')[unit]}"
            return f"{n}{unit}"
    return f"{seconds}s"


def _seconds_to_timeunit(seconds: int) -> dict:
    """A timeunit dict in the SEARCH-DEFINITION schema ("6h"), which is the
    document we rewrite and re-POST. The widget-config schema would be
    rejected by /api/views/search (see _interval_seconds)."""
    for abbr, div in (("d", 86400), ("h", 3600), ("m", 60), ("s", 1)):
        if seconds % div == 0 and seconds >= div:
            return {"type": "timeunit", "timeunit": f"{seconds // div}{abbr}"}
    return {"type": "timeunit", "timeunit": f"{seconds}s"}


def coarsen_intervals(search_def: dict, window_seconds: int,
                      max_buckets: int = DEFAULT_MAX_BUCKETS,
                      lang: str = "en"):
    """Return (new_search_def, notes) with exploding fixed intervals coarsened.

    notes: {search_type_id: human-readable "5m -> 6h" description}. The input
    is not mutated. Only pivots with a FIXED timeunit interval are touched —
    `auto` already scales with the range on Graylog's side.
    """
    notes: dict[str, str] = {}
    if not window_seconds or window_seconds <= 0:
        return search_def, notes
    out = copy.deepcopy(search_def)
    for q in out.get("queries") or []:
        for st in q.get("search_types") or []:
            changed = None
            for axis in ("row_groups", "column_groups"):
                for grp in st.get(axis) or []:
                    if grp.get("type") != "time":
                        continue
                    iv = grp.get("interval")
                    secs = _interval_seconds(iv)
                    if not secs:
                        continue                     # auto — Graylog handles it
                    buckets = window_seconds / secs
                    if buckets <= max_buckets:
                        continue
                    new_secs = _nice_interval_at_least(window_seconds / max_buckets)
                    if new_secs <= secs:
                        continue
                    grp["interval"] = _seconds_to_timeunit(new_secs)
                    changed = (secs, new_secs)
            if changed and st.get("id"):
                old_s, new_s = changed
                if lang == "zh-TW":
                    notes[st["id"]] = (f"時間間隔已由 {_fmt_interval(old_s, lang)} 調整為 "
                                       f"{_fmt_interval(new_s, lang)}（範圍過大）")
                else:
                    notes[st["id"]] = (f"interval adjusted {_fmt_interval(old_s)} -> "
                                       f"{_fmt_interval(new_s)} (wide range)")
    return out, notes


# --------------------------------------------------------------------------
# Phase 2 — time slicing + exact merge
# --------------------------------------------------------------------------

# Functions whose per-slice results combine EXACTLY over disjoint time slices.
_MERGE_EXACT = {"count": "sum", "sum": "sum", "min": "min", "max": "max"}


def _fn_name(fn: str) -> str:
    """'count()' / 'sum(bytes)' / 'card(src_ip)' -> bare function name."""
    return (fn or "").split("(", 1)[0].strip().lower()


def mergeable_functions(series: list) -> bool:
    """True iff EVERY series in this search type merges exactly across slices.

    avg/card(inality)/percentile/stddev/variance/latest cannot be derived from
    per-slice values — a search type containing any of them must NOT be sliced.

    Schema note (the second live-schema trap in this file): the SEARCH
    DEFINITION writes a series as {"type": "count", "field": ...} while the
    widget config writes {"function": "count()"}. Reading only `function`
    classified every real search type as unmergeable, so slicing silently
    never engaged — and the "verification" compared two identical unsliced
    runs. Prefer `type`, fall back to parsing `function`.
    """
    if not series:
        return False
    for s in series:
        s = s or {}
        name = str(s.get("type") or "").strip().lower() or _fn_name(s.get("function"))
        if name not in _MERGE_EXACT:
            return False
    return True


def slice_windows(t_from: datetime, t_to: datetime,
                  slice_seconds: int = 7 * 86400) -> list[tuple[datetime, datetime]]:
    """Split [t_from, t_to) into consecutive, disjoint slices (last one short)."""
    if t_to <= t_from:
        return []
    out, cur = [], t_from
    step = timedelta(seconds=max(int(slice_seconds), 3600))
    while cur < t_to:
        nxt = min(cur + step, t_to)
        out.append((cur, nxt))
        cur = nxt
    return out


def _merge_leaf(values: list, fn: str):
    vals = [v for v in values if isinstance(v, (int, float))]
    if not vals:
        return values[0] if values else None
    op = _MERGE_EXACT.get(_fn_name(fn), "sum")
    if op == "min":
        return min(vals)
    if op == "max":
        return max(vals)
    total = sum(vals)
    # keep ints int (counts), floats float
    return int(total) if all(isinstance(v, int) for v in vals) else total


def merge_search_type_results(slices: list[dict]) -> dict:
    """Merge per-slice pivot results for a search type whose series all pass
    `mergeable_functions`. Rows are keyed by their full key path; leaf values
    combine per their function (count/sum add, min/min, max/max). Row order:
    first-seen, which for a time pivot over ordered slices is chronological.
    """
    slices = [s for s in slices if s]
    if not slices:
        return {}
    out = copy.deepcopy(slices[0])
    index: dict[tuple, dict] = {}
    merged_rows: list[dict] = []

    def _key(row):
        return tuple(tuple(k) if isinstance(k, list) else (k,) for k in (row.get("key") or []))

    for sl in slices:
        for row in sl.get("rows") or []:
            k = _key(row)
            if k not in index:
                r = copy.deepcopy(row)
                index[k] = r
                merged_rows.append(r)
                continue
            tgt = index[k]
            # merge leaf values positionally by their own key (function id)
            tv = {tuple(v.get("key") or []): v for v in tgt.get("values") or []}
            for v in row.get("values") or []:
                vk = tuple(v.get("key") or [])
                if vk in tv:
                    fn = "/".join(str(p) for p in vk)
                    tv[vk]["value"] = _merge_leaf([tv[vk].get("value"), v.get("value")], fn)
                else:
                    nv = copy.deepcopy(v)
                    tgt.setdefault("values", []).append(nv)
                    tv[vk] = nv
    out["rows"] = merged_rows
    if "total" in out:
        totals = [s.get("total") for s in slices if isinstance(s.get("total"), (int, float))]
        out["total"] = sum(totals) if totals else out.get("total")
    # the merged result spans the whole window, not the first slice
    effs_from = [s.get("effective_timerange", {}).get("from") for s in slices]
    effs_to = [s.get("effective_timerange", {}).get("to") for s in slices]
    if any(effs_from) and any(effs_to):
        out.setdefault("effective_timerange", {})
        out["effective_timerange"]["from"] = min(e for e in effs_from if e)
        out["effective_timerange"]["to"] = max(e for e in effs_to if e)
    return out


def merge_message_results(slices: list[dict], limit: int) -> dict:
    """Merge per-slice message-list results: newest `limit` messages overall.
    Exact for a "latest N" list because slices are disjoint."""
    slices = [s for s in slices if s]
    if not slices:
        return {}
    out = copy.deepcopy(slices[-1])          # keep newest slice's metadata
    msgs = []
    for sl in slices:
        msgs.extend(sl.get("messages") or [])

    def _ts(m):
        return ((m.get("message") or {}).get("timestamp")) or ""

    msgs.sort(key=_ts, reverse=True)
    out["messages"] = msgs[: max(int(limit or 0), 1)]
    totals = [s.get("total_results") for s in slices
              if isinstance(s.get("total_results"), (int, float))]
    if totals:
        out["total_results"] = sum(totals)
    return out
