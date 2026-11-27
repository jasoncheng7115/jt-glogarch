# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Create a Graylog dashboard from an answer's chart specs (1.37).

Owner 2026-11-27: "以此看板為基底 在 graylog 的dashboard 裡建立一個 dashboard ...
產 dashboard 也很多語法格式等等要注意 我們系統要做出正確格式". So THIS code
builds the views JSON from the specs (glogarch.ai.charts), never the model.
It creates only (no update, no delete), as the signed-in user's own Graylog
session, so Graylog's permissions decide and the dashboard is theirs.

Shapes measured on throwaway Graylog 7.2.2 and 6.3.15 (see tests and
scripts/e2e-ai-dashboard-test.py): a search is created first
(`POST /api/views/search`), then the view (`POST /api/views`) whose state maps
each widget to its search type.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from glogarch.ai import charts as C
from glogarch.ai import graylog_tools as G

VIS = ("line", "area", "bar", "pie", "table", "numeric")
DEFAULT_VIS = {"timeseries": "line", "bar": "bar", "table": "table", "number": "numeric"}
ALLOWED_VIS = {"timeseries": ("line", "area", "bar", "table"),
               "bar": ("bar", "pie", "table"),
               "table": ("table",),
               "number": ("numeric",)}
RANGES = {"8h": 8 * 3600, "1d": 86400, "7d": 7 * 86400, "30d": 30 * 86400}
MAX_WIDGETS = C.MAX_SPECS
TITLE_MAX = 120
_UNITS = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days", "w": "weeks"}


def _uid() -> str:
    return str(uuid.uuid4())


def timerange_for(choice: str, abs_from: str = "", abs_to: str = "") -> dict:
    """The dashboard's time range: relative 8h/1d/7d/30d, or absolute (UTC ISO)."""
    if choice in RANGES:
        return {"type": "relative", "from": RANGES[choice]}
    if choice == "custom":
        a = G._point(abs_from, datetime.now(timezone.utc)) if abs_from else None
        b = G._point(abs_to, datetime.now(timezone.utc)) if abs_to else None
        if a is None or b is None or b <= a:
            raise ValueError("custom range: a start before the end (ISO-8601)")
        f = lambda d: d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        return {"type": "absolute", "from": f(a), "to": f(b)}
    raise ValueError("range: one of 8h, 1d, 7d, 30d, custom")


def series_of(metric: str) -> tuple[dict, dict]:
    """Our metric string -> (widget series, search-type series)."""
    mm = G._METRIC_RE.fullmatch(metric)
    if not mm:
        raise ValueError(f"metric {metric!r}")
    fn, pct, fld = mm.group(1), mm.group(2), mm.group(3)
    if pct:
        p = float(pct)
        sid = f"percentile({fld},{p:g})"
        st = {"type": "percentile", "id": sid, "field": fld, "percentile": p}
    else:
        sid = f"{fn}({fld or ''})"
        st = {"type": fn, "id": sid, "field": fld}
    return {"config": {"name": None}, "function": sid}, st


def pivots_of(group: str, n_groups: int) -> tuple[dict, dict]:
    """'field[:rows]' or 'timestamp[:step]' -> (widget pivot, search-type group).
    A time grouping uses Graylog's automatic interval: the dashboard's range is
    chosen by the user and may be far longer than the answer's."""
    fld, _, opt = group.partition(":")
    if fld == "timestamp":
        return ({"fields": ["timestamp"], "type": "time", "config": {"interval": {"type": "auto", "scaling": 1.0}}},
                {"type": "time", "fields": ["timestamp"], "interval": {"type": "auto", "scaling": 1.0}})
    lim = int(opt) if opt.isdigit() else (10 if n_groups == 1 else 5)
    lim = max(1, min(lim, G.AGG_MAX_LIMIT))
    return ({"fields": [fld], "type": "values", "config": {"limit": lim}},
            {"type": "values", "fields": [fld], "limit": lim})


def build_widget(spec: dict, vis: str) -> tuple[dict, dict, list[str]]:
    """One spec -> (widget, search type, notes about what Graylog shows differently)."""
    allowed = ALLOWED_VIS.get(spec["kind"], ("table",))
    if vis not in allowed:
        vis = DEFAULT_VIS.get(spec["kind"], "table")
    notes: list[str] = []
    wseries, sseries = [], []
    for m in spec.get("metrics") or ["count"]:
        w, s = series_of(m)
        wseries.append(w)
        sseries.append(s)
    groups = list(spec.get("group_by") or [])
    rows, cols, srows, scols = [], [], [], []
    if spec["kind"] == "timeseries" and len(groups) == 2 and vis != "table":
        # timestamp + a field: lines per value, as the answer's chart drew them
        r, sr = pivots_of(groups[0], 2)
        c, sc = pivots_of(groups[1], 2)
        rows, srows, cols, scols = [r], [sr], [c], [sc]
    else:
        for g in groups:
            r, sr = pivots_of(g, len(groups))
            rows.append(r)
            srows.append(sr)
    if any(g.startswith("timestamp:") and not g.endswith(":") for g in groups):
        notes.append("time_auto")
    sort, ssort = [], []
    srt = (spec.get("sort") or "").split()
    if srt and rows and vis != "numeric":
        try:
            sid = series_of(srt[0])[0]["function"]
        except ValueError:
            sid = ""
        if sid and sid in [w["function"] for w in wseries]:
            d = "Ascending" if len(srt) > 1 and srt[1].lower() == "asc" else "Descending"
            sort = [{"type": "series", "field": sid, "direction": d}]
            ssort = [{"type": "series", "field": sid, "direction": d}]
    query = {"type": "elasticsearch", "query_string": spec.get("query") if spec.get("query") not in ("*", "*:*") else ""}
    wid, stid = _uid(), _uid()
    vis_cfg = None
    if vis == "area":
        vis_cfg = {"interpolation": "linear"}
    elif vis == "line":
        vis_cfg = {"interpolation": "linear"}
    elif vis == "bar":
        vis_cfg = {"barmode": "group"}
    elif vis == "numeric":
        vis_cfg = {"trend": False, "trend_preference": "NEUTRAL"}
    widget = {"id": wid, "type": "aggregation", "filter": None, "filters": [], "timerange": None,
              "query": query, "streams": [], "stream_categories": [],
              "config": {"visualization": vis, "event_annotation": False, "row_pivots": rows,
                         "column_pivots": cols, "series": wseries, "rollup": not cols,
                         "visualization_config": vis_cfg, "formatting_settings": None, "sort": sort}}
    stype = {"id": stid, "type": "pivot", "name": "chart", "query": query, "timerange": None,
             "streams": [], "stream_categories": [], "filter": None, "filters": [],
             "rollup": not cols, "row_groups": srows, "column_groups": scols,
             "series": sseries, "sort": ssort}
    return widget, stype, notes


def positions(widgets: list[dict], kinds: list[str]) -> dict:
    """Two per row (a number takes a third), time charts full width."""
    pos, row, col = {}, 1, 1
    for w, k in zip(widgets, kinds):
        if k == "timeseries":
            if col != 1:
                row, col = row + 4, 1
            pos[w["id"]] = {"col": 1, "row": row, "height": 4, "width": "Infinity"}
            row += 4
            continue
        width = 4 if k == "number" else 6
        if col + width - 1 > 12:
            row, col = row + 4, 1
        pos[w["id"]] = {"col": col, "row": row, "height": 3 if k == "number" else 4, "width": width}
        col += width
        if col > 12:
            row, col = row + 4, 1
    return pos


def clean_title(s: str) -> str:
    s = re.sub(r"[\x00-\x1f\x7f]", " ", str(s or "")).strip()
    return s[:TITLE_MAX]


def build(specs: list[dict], picks: list[dict], title: str, timerange: dict,
          description: str = "") -> tuple[dict, dict, list[dict]]:
    """picks: [{"id": spec id, "vis": ..., "title": ...}] in display order.
    Returns (search body, view body without search_id, per-widget notes)."""
    by_id = {s["id"]: s for s in specs}
    qid = _uid()
    widgets, stypes, mapping, titles, kinds, notes = [], [], {}, {}, [], []
    for p in picks[:MAX_WIDGETS]:
        s = by_id.get(str(p.get("id")))
        if not s:
            continue
        w, st, n = build_widget(s, str(p.get("vis") or ""))
        widgets.append(w)
        stypes.append(st)
        mapping[w["id"]] = [st["id"]]
        titles[w["id"]] = clean_title(p.get("title") or s.get("title")) or s["id"]
        kinds.append(s["kind"])
        notes.append({"id": s["id"], "notes": n})
    if not widgets:
        raise ValueError("no chart picked")
    search = {"queries": [{"id": qid, "query": {"type": "elasticsearch", "query_string": ""},
                           "timerange": timerange, "filter": None, "filters": [],
                           "search_types": stypes}],
              "parameters": []}
    state = {qid: {"selected_fields": None, "static_message_list_id": None,
                   "titles": {"widget": titles, "tab": {"title": clean_title(title)}},
                   "widgets": widgets, "widget_mapping": mapping,
                   "positions": positions(widgets, kinds), "formatting": {"highlighting": []},
                   "display_mode_settings": {"positions": {}}}}
    view = {"type": "DASHBOARD", "title": clean_title(title), "summary": "",
            "description": clean_title(description) if description else "",
            "properties": [], "requires": {}, "state": state, "favorite": False}
    return search, view, notes


async def create(server, auth: tuple[str, str], search: dict, view: dict) -> str:
    """POST the search, then the view; returns the new dashboard's id. Graylog 7
    takes the view wrapped as {"entity", "share_request"} (flat = 400 "entity
    cannot be null", measured 7.2.2); when the wrapper is refused with 400 the
    flat form is tried once, and the wrapper's error is reported if both fail."""
    import httpx
    hdr = {"X-Requested-By": "jt-glogarch", "Accept": "application/json"}
    base = G._base_url(server)
    async with httpx.AsyncClient(verify=bool(server.verify_ssl), timeout=G.GRAYLOG_TIMEOUT_SEC,
                                 auth=auth, headers=hdr) as c:
        r = await c.post(base + "/api/views/search", json=search)
        _raise(r, "search")
        sid = r.json().get("id")
        if not isinstance(sid, str) or not re.fullmatch(r"[0-9a-f]{24}", sid):
            raise RuntimeError("Graylog did not return a search id")
        body = dict(view, search_id=sid)
        r = await c.post(base + "/api/views", json={"entity": body, "share_request": None})
        if r.status_code == 400:
            flat = await c.post(base + "/api/views", json=body)
            if flat.status_code < 400:
                r = flat
        _raise(r, "dashboard")
        vid = r.json().get("id")
        if not isinstance(vid, str) or not re.fullmatch(r"[0-9a-f]{24}", vid):
            raise RuntimeError("Graylog did not return a dashboard id")
        return vid


def _raise(r, what: str) -> None:
    if r.status_code < 400:
        return
    try:
        msg = r.json().get("message") or r.text
    except ValueError:
        msg = r.text
    if what == "search":
        raise RuntimeError(f"Graylog refused the search (HTTP {r.status_code}): {str(msg)[:300]}")
    raise RuntimeError(f"Graylog refused the dashboard (HTTP {r.status_code}): {str(msg)[:300]}")
