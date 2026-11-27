# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""An answer's recorded tool calls -> chart specs -> data -> report widgets (1.37).

Owner 2026-11-27: a Graylog dashboard and a PDF summary made from an answer.
Both read the SAME specs so their charts agree. A spec is what one call asked
Graylog (query, groupings, metrics, the absolute range it ran with); the rows
are never stored with the answer, so `run_spec` asks Graylog again, as the
signed-in user, through the same code the chat tool used (`_aggregate`,
`_count`). The model writes no query here: only calls it already made and that
succeeded become charts.
"""

from __future__ import annotations

import ast
import re
from datetime import datetime, timedelta, timezone

from glogarch.ai import graylog_tools as G

CHARTABLE = ("aggregate", "top_values", "count_messages")
MAX_SPECS = 12                 # charts per answer
SERIES_MAX = 8                 # lines in one time chart; the rest are left out and said so
BAR_ROWS_MAX = 20
TABLE_ROWS_MAX = 50
_FIELD = re.compile(r"[A-Za-z0-9_.@-]{1,100}")


def _as_list(v) -> list[str]:
    """A list argument as recorded: a real list (1.37+) or its str() (before)."""
    if isinstance(v, list):
        items = v
    elif isinstance(v, str):
        s = v.strip()
        if s.startswith("["):
            try:
                items = ast.literal_eval(s)
            except (ValueError, SyntaxError, MemoryError, RecursionError):
                return []    # cut at 300 characters, or not a list: no chart from it
            if not isinstance(items, list):
                return []
        else:
            items = [s] if s else []
    else:
        return []
    return [str(x).strip() for x in items if isinstance(x, (str, int, float)) and str(x).strip()][:10]


def _group_field(g: str) -> str:
    return g.split(":", 1)[0]


def spec_from_call(call: dict, index: int) -> dict | None:
    """One recorded call -> a chart spec, or None when it cannot be one."""
    if not isinstance(call, dict) or not call.get("ok") or call.get("name") not in CHARTABLE:
        return None
    rng = call.get("range") or {}
    if not (isinstance(rng.get("from"), str) and isinstance(rng.get("to"), str)):
        return None
    args = call.get("args") or {}
    query = call.get("query") if isinstance(call.get("query"), str) else str(args.get("query") or "*")
    name = call["name"]
    spec = {"id": f"c{index}", "call": index, "tool": name, "query": query or "*",
            "range": {"from": rng["from"], "to": rng["to"]}, "group_by": [], "metrics": ["count"],
            "sort": "", "server": call.get("server") or ""}
    if name == "count_messages":
        spec["kind"] = "number"
    elif name == "top_values":
        fld = str(args.get("field") or "").strip()
        if not _FIELD.fullmatch(fld):
            return None
        try:
            lim = max(1, min(int(args.get("limit") or 10), 50))
        except (TypeError, ValueError):
            lim = 10
        spec["group_by"] = [f"{fld}:{lim}"]
        df = str(args.get("distinct_field") or "").strip()
        if _FIELD.fullmatch(df):
            spec["metrics"] = ["count", f"card:{df}"]
        spec["sort"] = "count desc"
        spec["kind"] = "bar"
    else:
        groups = _as_list(args.get("group_by"))
        if not groups or len(groups) > G.AGG_MAX_GROUPS or not all(G._GROUP_RE.fullmatch(g) for g in groups):
            return None
        metrics = _as_list(args.get("metrics")) or ["count"]
        if len(metrics) > G.AGG_MAX_METRICS or not all(G._METRIC_RE.fullmatch(m) for m in metrics):
            return None
        spec["group_by"], spec["metrics"] = groups, metrics
        spec["sort"] = str(args.get("sort") or "")[:80]
        if isinstance(args.get("limit"), int) and not isinstance(args.get("limit"), bool):
            spec["limit"] = max(1, min(args["limit"], G.AGG_MAX_LIMIT))
        time_first = _group_field(groups[0]) == "timestamp"
        if time_first and (len(groups) == 1 or (len(groups) == 2 and _group_field(groups[1]) != "timestamp")):
            spec["kind"] = "timeseries"
        elif len(groups) == 1 and len(metrics) == 1:
            spec["kind"] = "bar"
        else:
            spec["kind"] = "table"     # 3 groupings, several metrics per group, or time not first
    spec["title"] = default_title(spec)
    return spec


def specs_from_calls(calls) -> list[dict]:
    """Every call of an answer that can be a chart, in the order they ran; the
    same query asked twice with the same shape is kept once (the later one)."""
    out: dict[tuple, dict] = {}
    for i, c in enumerate(calls or []):
        s = spec_from_call(c, i)
        if s is None:
            continue
        key = (s["tool"], s["query"], tuple(s["group_by"]), tuple(s["metrics"]))
        out.pop(key, None)
        out[key] = s
    return list(out.values())[:MAX_SPECS]


def default_title(spec: dict) -> str:
    """A plain, language-neutral title: 'count by user_name, source_ip'."""
    metrics = ", ".join(G._metric_spec(m)[1] for m in spec.get("metrics") or ["count"])
    groups = [_group_field(g) for g in spec.get("group_by") or []]
    return f"{metrics} by {', '.join(groups)}" if groups else metrics


def tool_args(spec: dict, rng: dict | None = None) -> tuple[str, dict]:
    """The chat tool and arguments that re-run a spec (over `rng` when given)."""
    r = rng or spec["range"]
    base = {"query": spec.get("query") or "*", "range_from": r["from"], "range_to": r["to"]}
    if spec["kind"] == "number":
        return "count_messages", base
    args = {**base, "group_by": list(spec["group_by"]), "metrics": list(spec["metrics"])}
    if spec.get("sort"):
        args["sort"] = spec["sort"]
    if spec.get("limit"):
        args["limit"] = spec["limit"]
    return "aggregate", args


async def run_spec(spec: dict, ctx, rng: dict | None = None) -> dict:
    """Ask Graylog again for one spec. Returns {"ok", "rows", "group_by",
    "metrics", "count", "timerange", "notes"} or {"ok": False, "error"}.
    Raises nothing: a chart that cannot be drawn says why."""
    tool, args = tool_args(spec, rng)
    try:
        if tool == "count_messages":
            res = await G._count(args, ctx)
            return {"ok": True, "count": res["count"], "timerange": res["timerange"], "rows": [],
                    "group_by": [], "metrics": ["count"], "notes": []}
        res = await G._aggregate(args, ctx)
    except Exception as e:     # Graylog refused, timed out, field gone: the chart says so
        return {"ok": False, "error": str(e)[:300] or e.__class__.__name__}
    return {"ok": True, "rows": res["rows"], "group_by": res["group_by"], "metrics": res["metrics"],
            "timerange": res["timerange"], "notes": res.get("notes") or []}


# --- data -> report widgets (glogarch.report.builder) ---------------------------

def _local(ts) -> datetime | None:
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return dt.astimezone() if dt.tzinfo else dt


def time_labels(keys: list) -> list[str]:
    """HH:MM, with MM-DD on a second line when the day changes (as the report's
    Graylog charts do); local time of this host."""
    out, prev = [], None
    for k in keys:
        dt = _local(k)
        if dt is None:
            out.append(str(k)[:16])
            prev = None
            continue
        day = dt.strftime("%m-%d")
        out.append(dt.strftime("%H:%M") + ("\n" + day if day != prev else ""))
        prev = day
    return out


def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


_ISO = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})")


def fmt_number(v) -> str:
    """A cell for people: 12,345 / 1.50 / an ISO time in this host's local time."""
    if isinstance(v, bool) or v is None:
        return str(v) if v is not None else ""
    if isinstance(v, (int, float)):
        return f"{int(v):,}" if float(v).is_integer() else f"{v:,.2f}"
    if isinstance(v, str) and _ISO.fullmatch(v):
        dt = _local(v)
        if dt is not None:
            return dt.strftime("%Y-%m-%d %H:%M:%S")
    return str(v)


def series_of(spec: dict, data: dict) -> dict:
    """Time series: {"keys": [bucket...], "series": [{"label", "data"}], "dropped": n}.
    One grouping -> one line per metric; timestamp + a field -> one line per
    value of that field (first metric), the biggest SERIES_MAX kept."""
    names, metrics, rows = data["group_by"], data["metrics"], data["rows"]
    tname = names[0]
    keys = sorted({r.get(tname) for r in rows if r.get(tname) is not None}, key=str)
    keys = _fill_buckets(keys, tname, data.get("timerange") or spec.get("range") or {})
    if len(names) == 1:
        idx = {r.get(tname): r for r in rows}
        series = [{"label": column_label(m, spec.get("_lang", "en")), "data": [_num((idx.get(k) or {}).get(m)) for k in keys]}
                  for m in metrics]
        return {"keys": keys, "series": series, "dropped": 0}
    fname, m = names[1], metrics[0]
    totals: dict = {}
    cells: dict = {}
    for r in rows:
        v = str(r.get(fname))
        totals[v] = totals.get(v, 0.0) + _num(r.get(m))
        cells[(r.get(tname), v)] = _num(r.get(m))
    top = sorted(totals, key=lambda v: -totals[v])[:SERIES_MAX]
    series = [{"label": v, "data": [cells.get((k, v), 0.0) for k in keys]} for v in top]
    return {"keys": keys, "series": series, "dropped": max(0, len(totals) - len(top))}


_WORDS = {
    "count": {"en": "Count", "zh-TW": "筆數", "ja": "件数"},
    "card": {"en": "Distinct {f}", "zh-TW": "{f} 相異數", "ja": "{f} の種類数"},
    "first": {"en": "First seen", "zh-TW": "首次出現", "ja": "初回"},
    "last": {"en": "Last seen", "zh-TW": "最後出現", "ja": "最終"},
    "time": {"en": "Time", "zh-TW": "時間", "ja": "時刻"},
    "trend": {"en": "{m} over time", "zh-TW": "{m}趨勢", "ja": "{m}の推移"},
    "split": {"en": " by {g}", "zh-TW": "（依 {g}）", "ja": "（{g} 別）"},
    "top": {"en": "Top {g} ({m})", "zh-TW": "{g} 排行（{m}）", "ja": "{g} の上位（{m}）"},
    "by": {"en": "{m} by {g}", "zh-TW": "{m}（依 {g}）", "ja": "{m}（{g} 別）"},
}


def _w(key: str, lang: str) -> str:
    return _WORDS[key].get(lang) or _WORDS[key]["en"]


def column_label(name: str, lang: str = "en") -> str:
    """A result column for people: count -> 筆數, card(x) -> x 相異數, min(timestamp) ->
    首次出現; a grouping keeps its field name (timestamp (1h) -> 時間)."""
    if name == "count":
        return _w("count", lang)
    if name.startswith("timestamp ("):
        return _w("time", lang)
    m = re.fullmatch(r"(\w+)\((.+)\)", name)
    if m:
        fn, fld = m.group(1), m.group(2)
        if fn == "card":
            return _w("card", lang).replace("{f}", fld)
        if fld == "timestamp" and fn == "min":
            return _w("first", lang)
        if fld == "timestamp" and fn in ("max", "latest"):
            return _w("last", lang)
    return name


def local_title(spec: dict, lang: str = "en") -> str:
    """The same default title the page's dialog shows (ai_export.js aixChartTitle)."""
    sep = ", " if lang == "en" else "、"
    ms = sep.join(column_label(G._metric_spec(m)[1], lang) for m in spec.get("metrics") or ["count"])
    gs = [_group_field(g) for g in spec.get("group_by") or [] if _group_field(g) != "timestamp"]
    if spec["kind"] == "number":
        # a count alone says nothing ("筆數" four times, owner 2026-11-27): name what it counts
        q = short_query(spec.get("query") or "")
        return f"{ms}（{q}）" if q and lang != "en" else (f"{ms} ({q})" if q else ms)
    if spec["kind"] == "timeseries":
        return _w("trend", lang).replace("{m}", ms) + (_w("split", lang).replace("{g}", sep.join(gs)) if gs else "")
    if spec["kind"] == "bar":
        return _w("top", lang).replace("{g}", sep.join(gs)).replace("{m}", ms)
    return _w("by", lang).replace("{m}", ms).replace("{g}", sep.join(gs))


_UNIT_S = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
FILL_MAX = 500


def _fill_buckets(keys: list, tname: str, rng: dict) -> list:
    """Every time bucket of the range, not only those with data: Graylog leaves empty
    buckets out, so a week with one busy day came back as ONE point and the chart
    drew nothing (owner's report 2026-11-27, "怎麼空的"). Missing buckets read 0."""
    m = re.search(r"\((\d+)([smhdw])\)", tname)
    a, b = _local(rng.get("from")), _local(rng.get("to"))
    if not (m and keys and a and b):
        return keys
    step = timedelta(seconds=int(m.group(1)) * _UNIT_S[m.group(2)])
    parsed = {k: _local(k) for k in keys}
    first = min((v for v in parsed.values() if v), default=None)
    if first is None:
        return keys
    fmt = lambda d: d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    by_time = {v.astimezone(timezone.utc): k for k, v in parsed.items() if v}
    start = first
    while start - step >= a and len(by_time) < FILL_MAX:
        start -= step
    out, t = [], start
    while t <= b and len(out) < FILL_MAX:
        out.append(by_time.get(t.astimezone(timezone.utc), fmt(t)))
        t += step
    extra = [k for k in keys if k not in out]      # odd keys (another zone) are kept, not lost
    return sorted(out + extra, key=lambda k: _local(k) or first) if extra else out


def short_query(q: str, n: int = 40) -> str:
    q = re.sub(r"\s+", " ", (q or "").strip())
    if q in ("", "*", "*:*"):
        return ""
    return q if len(q) <= n else q[:n - 1] + "…"


def table_of(data: dict, max_rows: int = TABLE_ROWS_MAX, lang: str = "en") -> dict:
    cols = list(data["group_by"]) + list(data["metrics"])
    rows = [[fmt_number(r.get(c)) for c in cols] for r in data["rows"][:max_rows]]
    return {"columns": [column_label(c, lang) for c in cols], "rows": rows, "total": len(data["rows"]),
            "numeric_from": len(data["group_by"])}


def report_widget(spec: dict, data: dict, title: str = "", notes_lang: str = "en") -> dict:
    """One spec's data as a widget for glogarch.report.builder."""
    from glogarch.report import builder as B
    title = title or local_title(spec, notes_lang)
    spec = dict(spec, _lang=notes_lang)
    if not data.get("ok"):
        return {"kind": "none", "title": title, "description": data.get("error") or ""}
    if spec["kind"] == "number":
        return {"kind": "single", "title": title, "value": fmt_number(data.get("count", 0)),
                "label": spec.get("query") or "*", "compact": True}
    if not data["rows"]:
        return {"kind": "none", "title": title}
    if spec["kind"] == "timeseries":
        s = series_of(spec, data)
        cfg = B.line_chart(time_labels(s["keys"]), s["series"], time_axis=True)
        if len(s["keys"]) <= 60:        # few buckets: show each value as a point too
            for ds in cfg["data"]["datasets"]:
                ds["pointRadius"] = 3
        w = {"kind": "chart", "title": title, "tall": True,
             "legend_heavy": len(s["series"]) > 15, "config": cfg}
        if s["dropped"]:
            w["rows_note"] = _more_series_note(s["dropped"], notes_lang)
        return w
    if spec["kind"] == "bar":
        names, m = data["group_by"], data["metrics"][0]
        rows = data["rows"][:BAR_ROWS_MAX]
        return {"kind": "chart", "title": title,
                "config": B.bar_chart([str(r.get(names[0])) for r in rows], [_num(r.get(m)) for r in rows],
                                      horizontal=True)}
    t = table_of(data, lang=notes_lang)
    w = {"kind": "table", "title": title, "columns": t["columns"], "rows": t["rows"],
         "numeric_from": t["numeric_from"], "keep_words": True}
    if t["total"] > len(t["rows"]):
        w["rows_note"] = _more_rows_note(t["total"], len(t["rows"]), notes_lang)
    return w


_NOTES = {
    "series": {"en": "{n} smaller series not shown", "zh-TW": "另有 {n} 個較小的數列未顯示",
               "ja": "ほかに小さい系列が {n} 件あります（非表示）"},
    "rows": {"en": "Showing {s} of {n} rows", "zh-TW": "顯示 {n} 列中的 {s} 列",
             "ja": "{n} 行のうち {s} 行を表示しています"},
}


def _more_series_note(n: int, lang: str) -> str:
    return _NOTES["series"].get(lang, _NOTES["series"]["en"]).replace("{n}", f"{n:,}")


def _more_rows_note(total: int, shown: int, lang: str) -> str:
    return (_NOTES["rows"].get(lang, _NOTES["rows"]["en"])
            .replace("{n}", f"{total:,}").replace("{s}", f"{shown:,}"))
