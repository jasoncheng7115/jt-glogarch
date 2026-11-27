# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Tool results too big for the model: kept here, shown a page at a time.

Owner 2026-11-26: "如果一次撈比較長範圍資料 llm 不可能全吃 ... 如果過多 是不是也要有分頁機制".
Before 1.36 a result over 12,000 characters was cut there: the model read half
a JSON document and did not know what was missing.

Now `shape()` gives the model a VIEW that fits its budget:
  * the result's largest list (rows, messages, buckets) cut to the rows that fit,
    with the total, a summary of every column (distinct values, the most common
    ones with counts, min/max of numbers) and a result id;
  * any other big result in text pages;
and `read_result` (a tool) reads more of the kept result: a page, rows matching
a value, sorted, counted by one column. Results stay in this process for
STORE_TTL_SEC, for the user, channel and Graylog server that made them only;
they are never written to disk (log text gets no second copy, as in 1.21).
"""
from __future__ import annotations

import json
import secrets
import time
from collections import Counter
from typing import Any

STORE_TTL_SEC = 30 * 60
STORE_MAX_ENTRIES = 200
STORE_MAX_CHARS = 60_000_000          # all kept results together (approximate, characters)
SUMMARY_COLUMNS = 16
SUMMARY_TOP = 5
READ_MAX_ROWS = 500

_STORE: dict[str, dict] = {}


def _dumps(x) -> str:
    return x if isinstance(x, str) else json.dumps(x, ensure_ascii=False, default=str)


def _prune(now: float) -> None:
    for k in [k for k, v in _STORE.items() if now - v["at"] > STORE_TTL_SEC]:
        _STORE.pop(k, None)
    total = sum(v["size"] for v in _STORE.values())
    for k in sorted(_STORE, key=lambda k: _STORE[k]["at"]):
        if len(_STORE) <= STORE_MAX_ENTRIES and total <= STORE_MAX_CHARS:
            break
        total -= _STORE[k]["size"]
        _STORE.pop(k, None)


def keep(owner: str, tool: str, args: dict, kind: str, data, size: int) -> str:
    now = time.time()
    rid = "r" + secrets.token_hex(4)
    _STORE[rid] = {"owner": owner, "tool": tool, "args": args, "kind": kind, "data": data,
                   "size": size, "at": now}
    _prune(now)
    return rid


def get(rid: str, owner: str) -> dict | None:
    e = _STORE.get(str(rid))
    if not e or e["owner"] != owner or time.time() - e["at"] > STORE_TTL_SEC:
        return None
    e["at"] = time.time()      # reading keeps it
    return e


def _largest_list(obj) -> tuple[tuple, list] | None:
    """(path, list) of the biggest list in the result, up to two levels down."""
    best: tuple[tuple, list] | None = None
    best_size = 0

    def consider(path, v):
        nonlocal best, best_size
        if isinstance(v, list) and len(v) > 1:
            sz = len(_dumps(v))
            if sz > best_size:
                best, best_size = (path, v), sz

    consider((), obj)
    if isinstance(obj, dict):
        for k, v in obj.items():
            consider((k,), v)
            if isinstance(v, dict):
                for k2, v2 in v.items():
                    consider((k, k2), v2)
    return best


def summarize_rows(rows: list) -> dict:
    """Per column: how many rows have it, distinct values, the most common values
    with counts, min/max of numbers. Computed here, so the model sees the whole
    result's shape whatever page it reads."""
    if not rows or not all(isinstance(r, dict) for r in rows[:50]):
        if rows and all(isinstance(r, list) for r in rows[:50]):
            rows = [{f"col{i}": v for i, v in enumerate(r)} for r in rows]
        else:
            return {}
    cols: dict[str, list] = {}
    for r in rows:
        for k, v in r.items():
            if len(cols) >= SUMMARY_COLUMNS and k not in cols:
                continue
            cols.setdefault(k, []).append(v)
    out = {}
    for k, vals in cols.items():
        nums = [v for v in vals if isinstance(v, (int, float)) and not isinstance(v, bool)]
        info: dict[str, Any] = {"rows_with_value": sum(1 for v in vals if v not in (None, ""))}
        if nums and len(nums) == len(vals):
            info.update(min=min(nums), max=max(nums), sum=round(sum(nums), 3))
        else:
            hashable = [v if isinstance(v, (str, int, float, bool)) else _dumps(v)[:80] for v in vals]
            c = Counter(hashable)
            info["distinct"] = len(c)
            info["top"] = [[v if not isinstance(v, str) else v[:120], n] for v, n in c.most_common(SUMMARY_TOP)]
        out[k] = info
    return out


def _fit_rows(rows: list, budget: int) -> int:
    """How many rows (from the start) fit in `budget` characters."""
    used, n = 0, 0
    for r in rows:
        sz = len(_dumps(r)) + 2
        if used + sz > budget and n > 0:
            break
        used += sz
        n += 1
    return n


def _set_path(obj, path: tuple, value):
    if not path:
        return value
    out = dict(obj)
    if len(path) == 1:
        out[path[0]] = value
    else:
        out[path[0]] = dict(out[path[0]])
        out[path[0]][path[1]] = value
    return out


def shape(result, budget: int, owner: str, tool: str, args: dict) -> tuple[str, bool]:
    """The text the model gets and whether it is a partial view."""
    text = _dumps(result)
    if len(text) <= budget:
        return text, False
    obj = result
    if isinstance(result, str):
        try:
            obj = json.loads(result)
        except ValueError:
            obj = None
    found = _largest_list(obj) if obj is not None else None
    if found:
        path, rows = found
        # the rest of the result + the column summary first; the rows get what is left
        summary = summarize_rows(rows)
        rid = keep(owner, tool, args, "rows", rows, len(text))
        frame = {"result_id": rid, "rows_total": len(rows), "rows_shown": 0,
                 "list": ".".join(map(str, path)) or "(the result itself)", "columns": summary,
                 "more": f"This is the first part only. read_result(result_id=\"{rid}\", offset=..., limit=..., "
                         "where=..., sort_by=..., group_by=...) reads more of it; do not run the query again."}
        base = _set_path(obj, path, [])
        room = budget - len(_dumps(base)) - len(_dumps(frame)) - 200
        n = _fit_rows(rows, max(room, budget // 4))
        frame["rows_shown"] = n
        view = _set_path(obj, path, rows[:n])
        view = {"_paging": frame, **view} if isinstance(view, dict) else {"_paging": frame, "rows": view}
        out = _dumps(view)
        if len(out) > budget * 1.5:      # a summary bigger than the budget (very wide rows): drop it
            frame["columns"] = {k: {"rows_with_value": v.get("rows_with_value")} for k, v in summary.items()}
            out = _dumps(view)
        return out, True
    pages = [text[i:i + budget] for i in range(0, len(text), budget)]
    rid = keep(owner, tool, args, "text", pages, len(text))
    head = (f"[result {rid}: page 1 of {len(pages)} ({len(text):,} characters). "
            f"read_result(result_id=\"{rid}\", page=2) reads the next page.]\n")
    return head + pages[0][:max(0, budget - len(head))], True


def _match(row, where: dict) -> bool:
    if not isinstance(row, dict):
        return False
    for k, want in where.items():
        v = row.get(k)
        w = str(want)
        if w.startswith("~"):
            if w[1:].lower() not in str(v).lower():
                return False
        elif str(v) != w:
            return False
    return True


def read(entry: dict, args: dict, budget: int) -> dict:
    """read_result over a kept result."""
    if entry["kind"] == "text":
        pages = entry["data"]
        p = max(1, min(int(args.get("page") or 1), len(pages)))
        return {"result_id_page": p, "pages": len(pages), "text": pages[p - 1][:budget]}
    rows = entry["data"]
    where = args.get("where") or {}
    if not isinstance(where, dict):
        raise ValueError('where: an object, e.g. {"source": "web01"} (exact) or {"message": "~timeout"} (contains)')
    sel = [r for r in rows if _match(r, where)] if where else list(rows)
    gb = args.get("group_by")
    if gb:
        c = Counter(str(r.get(gb)) if isinstance(r, dict) else "" for r in sel)
        top = c.most_common(max(1, min(int(args.get("limit") or 50), READ_MAX_ROWS)))
        return {"rows_matching": len(sel), "group_by": gb, "distinct": len(c),
                "counts": [{"value": v, "rows": n} for v, n in top],
                "note": "Counts of ROWS of the kept result (e.g. buckets or messages), not of all events."}
    sb = args.get("sort_by")
    if sb:
        def key(r):
            v = r.get(sb) if isinstance(r, dict) else None
            return (v is None, v if isinstance(v, (int, float)) else str(v))
        sel.sort(key=key, reverse=bool(args.get("descending")))
    fields = [f for f in (args.get("fields") or []) if isinstance(f, str)]
    if fields:
        sel = [{k: r.get(k) for k in fields} if isinstance(r, dict) else r for r in sel]
    off = max(0, int(args.get("offset") or 0))
    lim = max(1, min(int(args.get("limit") or 50), READ_MAX_ROWS))
    page = sel[off:off + lim]
    n = _fit_rows(page, budget - 400)
    return {"rows_total": len(rows), "rows_matching": len(sel), "offset": off, "rows_shown": n,
            "next_offset": off + n if off + n < len(sel) else None, "rows": page[:n]}
