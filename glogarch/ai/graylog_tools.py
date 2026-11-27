# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""The ONE tool registry behind the AI chat and the MCP endpoint.

Tools come from two places:
  * the owner's mcp_graylog, vendored unmodified in glogarch/vendor/ (its own
    tool definitions and its own execute_tool()), and
  * jt-glogarch's own tools: exact counts and top values through Graylog's
    aggregation API, security incidents, archive status.

Every call runs as a given Graylog identity (the signed-in user's Graylog
session for the chat, the caller's token for MCP), so Graylog's permissions
apply. Read-only only.

Embedding notes (gaps reported to the mcp_graylog developer 2026-11-19, worked
around HERE, never by editing the vendored file; 1.10.2 fixed loading on Python
3.10, its single-request counting and server-side distributions, the rest stands):
  * it imports the `mcp` SDK at module level but jt-glogarch never runs its
    server -> a minimal stand-in for the names it uses (only when the real SDK
    is not installed), so jt-glogarch needs no new dependency;
  * importing it calls logging.basicConfig() and opens ~/.mcp_graylog.log at
    DEBUG -> HOME points at a throwaway dir for the import, the file handler is
    closed and the root logger restored;
  * one module-level `graylog_config` -> set per call under a lock, which also
    serialises its heavier sampling tools against a production Graylog;
  * hardcoded limits -> a time-range cap here on every tool that pulls
    messages, and on the look-back of its aggregations (`lookback_hours`).
    The own `count_messages` / `top_values` stay: they were written when its
    distributions were sampled (fixed upstream in 1.10.1) and the chat's prompt
    and the incident analysis use them by name.
"""
from __future__ import annotations

import asyncio
from collections import Counter
import importlib
import json
import logging
import os
import re
import shutil
import sys
import tempfile
import threading
import types as _pytypes
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable

from glogarch.core.archive_status import archive_status
from glogarch.ai.query_syntax import query_problem
from glogarch.utils.logging import get_logger
from glogarch.security.attack import techniques_for
from glogarch.security.risk import score_entities

log = get_logger("ai.tools")

# mcp_graylog tools offered by default. Left out: its two [Debug] tools,
# search_messages_export (bulk export, the heaviest pull), and the content-pack
# detail tools - a pack can carry notification addresses and credentials, which
# the owner's rule keeps from leaving without a decision.
MCPG_DEFAULT = (
    "analyze_time_patterns", "analyze_source_distribution", "analyze_field_distribution",
    "get_log_sample", "search_logs_paginated", "get_streams", "get_system_info",
    "get_current_time", "list_inputs", "list_index_sets", "list_indices", "list_fields",
    "list_content_packs", "list_dashboards", "get_dashboard",
    # 1.10: Graylog's own health, read-only
    "get_cluster_health", "get_node_metrics", "list_indexer_failures",
    "list_system_notifications", "find_silent_sources",
    # 1.11/1.12: event definitions and triggered events (alerts), read-only.
    # Notifications come back with which settings are set, never recipients,
    # URLs, tokens or headers (owner's rule; checked on log4 2026-11-22).
    "list_event_definitions", "get_event_definition", "search_events",
    "get_event_source_messages", "list_event_notifications",
)
# Tools with a time range that read no messages (the events index): the 31-day
# limit of the aggregations, not max_range_hours ("which alerts fired this week").
MCPG_LONG_RANGE = ("search_events",)
# Offered only when an administrator ticks them: measured 2026-11-20 on Graylog 7.2.2
# (1.10.2), each pulls messages for 120-140 s and returns partial results on a
# timeout, after three export endpoints that fail on 7.2 - two minutes of paging
# through a production Graylog for one question. count_messages / top_values
# answer the same questions with one aggregation.
MCPG_OPTIONAL = ("get_log_statistics", "analyze_error_patterns", "get_log_level_analysis")
# its debug tools: listed only with GRAYLOG_ENABLE_DEBUG_TOOLS=1 since 1.12, never offered here
MCPG_NEVER = ("test_accurate_counting", "test_source_analysis_fix")
MAX_LOOKBACK_HOURS = 24 * 31   # find_silent_sources' lookback_hours (an aggregation, no messages pulled)

_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
_WORDS = {"second": 1, "minute": 60, "hour": 3600, "day": 86400, "week": 604800}


# --- the vendored module ------------------------------------------------------

def _install_mcp_stand_in() -> None:
    """Names mcp_graylog uses at import time, when the real SDK is absent."""
    import importlib.util
    if "mcp" in sys.modules:    # the real SDK, or the stand-in from an earlier import
        return
    if importlib.util.find_spec("mcp") is not None:   # the real SDK is installed: use it
        return

    class _Obj:
        def __init__(self, *a, **kw):
            self.__dict__.update(kw)

    class Server:
        def __init__(self, name, *a, **kw):
            self.name = name

        def list_tools(self):
            return lambda fn: fn

        def call_tool(self, *a, **kw):
            return lambda fn: fn

        def __getattr__(self, item):  # run(), get_capabilities(), ...: never used here
            raise RuntimeError(f"mcp SDK not installed: Server.{item} is unavailable in jt-glogarch")

    mcp = _pytypes.ModuleType("mcp")
    server = _pytypes.ModuleType("mcp.server")
    models = _pytypes.ModuleType("mcp.server.models")
    mtypes = _pytypes.ModuleType("mcp.types")
    server.Server, server.NotificationOptions = Server, _Obj
    models.InitializationOptions = _Obj
    for n in ("Resource", "Tool", "TextContent", "ImageContent", "EmbeddedResource"):
        setattr(mtypes, n, type(n, (_Obj,), {}))
    mcp.server, mcp.types, server.models = server, mtypes, models
    sys.modules.update({"mcp": mcp, "mcp.server": server, "mcp.server.models": models,
                        "mcp.types": mtypes})


_mod = None
_mod_error: str | None = None
_mod_lock = threading.Lock()


def mcpg():
    """The vendored mcp_graylog module, imported once with its side effects
    contained. A failed import is remembered (and raised again) rather than
    retried on every call (1.9.44 did not compile before Python 3.12: an
    f-string with a backslash in its expression; fixed upstream in 1.10.2)."""
    global _mod, _mod_error
    with _mod_lock:
        if _mod is not None:
            return _mod
        if _mod_error is not None:
            raise RuntimeError(_mod_error)
        _install_mcp_stand_in()
        root = logging.getLogger()
        saved = (list(root.handlers), root.level)
        home = os.environ.get("HOME")
        tmp = tempfile.mkdtemp(prefix="jt-mcpg-")
        os.environ["HOME"] = tmp
        try:
            mod = importlib.import_module("glogarch.vendor.mcp_graylog")
        except Exception as e:
            _mod_error = (f"mcp_graylog could not be loaded on Python "
                          f"{sys.version_info.major}.{sys.version_info.minor}: "
                          f"{type(e).__name__}: {e}")
            raise RuntimeError(_mod_error) from e
        finally:
            if home is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = home
            lg = logging.getLogger("graylog-mcp-server")
            for h in list(lg.handlers):
                if isinstance(h, logging.FileHandler):
                    lg.removeHandler(h)
                    h.close()
            lg.setLevel(logging.WARNING)
            root.handlers[:] = saved[0]
            root.setLevel(saved[1])
            shutil.rmtree(tmp, ignore_errors=True)
        _mod = mod
        return mod


def mcpg_status() -> dict:
    """For the settings page: which version is vendored and whether it loads here."""
    from pathlib import Path
    man = {}
    try:
        man = json.loads((Path(__file__).resolve().parents[1] / "vendor" / "mcp_graylog.json").read_text())
    except (OSError, ValueError) as e:
        log.warning("mcp_graylog manifest unreadable", error=str(e))
    try:
        mcpg()
        return {"version": man.get("version", "?"), "available": True, "error": ""}
    except Exception as e:
        return {"version": man.get("version", "?"), "available": False, "error": str(e)[:300]}


# --- time ranges --------------------------------------------------------------

def _point(value: str | None, now: datetime) -> datetime | None:
    s = str(value or "").strip().lower()
    if not s or s == "now":
        return now
    try:   # a range the model writes can be absurd: unreadable, never a crash
        m = re.fullmatch(r"now-(\d+)([smhdw])", s)
        if m:
            return now - timedelta(seconds=int(m.group(1)) * _UNITS[m.group(2)])
        m = re.fullmatch(r"(\d+)\s*(second|minute|hour|day|week)s?\s*ago", s)
        if m:
            return now - timedelta(seconds=int(m.group(1)) * _WORDS[m.group(2)])
        dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        dt = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        dt.astimezone(timezone.utc)
        return dt
    except (ValueError, OverflowError):
        return None


def range_hours(range_from, range_to, now: datetime | None = None) -> float | None:
    """Length of a tool's time range in hours, or None when either end is not
    a form we can read (refused: the cap must not be bypassable)."""
    now = now or datetime.now(timezone.utc)
    a, b = _point(range_from, now), _point(range_to, now)
    if a is None or b is None:
        return None
    return max(0.0, (b - a).total_seconds() / 3600)


def call_scope(schema: dict, args: dict, now: datetime | None = None) -> dict:
    """The query and absolute range a call runs with, from its arguments and the
    tool's own defaults (mcp_graylog's results do not say), for the record kept
    with the answer: {"query"?, "range"?: {"from", "to"}} in UTC."""
    props = (schema or {}).get("properties") or {}
    out: dict = {}
    if "query" in props:
        q = args.get("query") if isinstance(args.get("query"), str) else props["query"].get("default")
        if isinstance(q, str):
            out["query"] = q
    if "range_from" in props:
        now = now or datetime.now(timezone.utc)
        a = _point(args.get("range_from") or props["range_from"].get("default") or "now-1h", now)
        b = _point(args.get("range_to") or (props.get("range_to") or {}).get("default") or "now", now)
        if a is not None and b is not None:
            f = lambda d: d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            try:
                out["range"] = {"from": f(a), "to": f(b)}
            except (ValueError, OverflowError) as e:   # the tool itself reports the bad range
                log.debug("No range to record for this call", error=str(e))
    return out


# --- registry -----------------------------------------------------------------

@dataclass
class Ctx:
    """Who is asking and where: one Graylog server, one identity."""
    settings: Any
    db: Any
    server: Any              # GraylogServerConfig of the target
    auth: tuple[str, str]    # (token, "token") or (session_id, "session")
    username: str = ""
    channel: str = "chat"    # chat | mcp
    result_budget: int = 12000   # characters of one tool result the caller can take (chat: from the model's context)

    @property
    def owner(self) -> str:
        """Who may read a kept result again (results.py): same channel, user and server."""
        return (f"{getattr(self, 'channel', '')}|{getattr(self, 'username', '')}|"
                f"{getattr(getattr(self, 'server', None), 'name', '')}")


@dataclass
class Tool:
    name: str
    description: str
    schema: dict
    run: Callable[[dict, Ctx], Awaitable[Any]]
    source: str = "jt-glogarch"
    range_capped: bool = False


def _cfg(settings):
    return getattr(settings, "ai", None)


def _base_url(server) -> str:
    u = server.url.rstrip("/")
    return u[:-4] if u.endswith("/api") else u


_call_locks: dict[int, asyncio.Lock] = {}


def _loop_lock() -> asyncio.Lock:
    loop = asyncio.get_running_loop()
    lk = _call_locks.get(id(loop))
    if lk is None:
        lk = _call_locks[id(loop)] = asyncio.Lock()
    return lk


_ALL_WILDCARD = re.compile(r"\s*(\*|\*:\*)?\s*")


def mcpg_query(args: dict) -> dict:
    """Graylog 7.2 refuses a query that starts with a wildcard on the endpoint
    mcp_graylog pages with, and 1.10.2 then retried ~900 times in one call
    (measured with `*:*`). "Everything" is sent as an empty query; any other
    leading wildcard is refused before it reaches Graylog."""
    if "query" not in args or not isinstance(args.get("query"), str):
        return args
    q = args["query"]
    if _ALL_WILDCARD.fullmatch(q):
        return {**args, "query": ""}
    if re.search(r"(^|[\s(:])[*?](?![\s)]|$)", q):
        raise ValueError("query: Graylog does not allow a leading wildcard; search a field "
                         "instead, e.g. source:web* or user_name:admin*")
    return args


def _mcpg_runner(name: str):
    async def run(args: dict, ctx: Ctx):
        args = mcpg_query(args)
        mod = mcpg()
        user, secret = ctx.auth
        conf = {"host": _base_url(ctx.server), "verify_ssl": bool(ctx.server.verify_ssl),
                "timeout": 30.0, "api_token": None, "username": None, "password": None}  # nosec B105 - empty slots, filled from the caller's identity below
        if secret == "token":  # nosec B105 - Graylog's fixed Basic-auth password for an API token, not a secret
            conf["api_token"] = user
        else:
            conf["username"], conf["password"] = user, secret
        async with _loop_lock():
            mod.graylog_config = conf
            try:
                return await mod.execute_tool(name, dict(args))
            finally:
                mod.graylog_config = None
    return run


GRAYLOG_TIMEOUT_SEC = 60


async def _graylog_post(ctx: Ctx, path: str, body: dict) -> dict:
    import httpx
    async with httpx.AsyncClient(verify=bool(ctx.server.verify_ssl), timeout=GRAYLOG_TIMEOUT_SEC,
                                 auth=ctx.auth, headers={"X-Requested-By": "jt-glogarch",
                                                         "Accept": "application/json"}) as c:
        try:
            r = await c.post(_base_url(ctx.server) + path, json=body)
        except httpx.TimeoutException:
            raise RuntimeError(f"Graylog did not answer within {GRAYLOG_TIMEOUT_SEC} s: "
                               "narrow the time range or the query")
        if r.status_code >= 400:
            try:
                msg = r.json().get("message") or r.text
            except ValueError:
                msg = r.text
            raise RuntimeError(f"Graylog HTTP {r.status_code}: {str(msg)[:300]}")
        return r.json()


def _timerange(args: dict) -> dict:
    now = datetime.now(timezone.utc)
    a = _point(args.get("range_from") or "now-1h", now)
    b = _point(args.get("range_to") or "now", now)
    if a is None or b is None:
        raise ValueError("range_from / range_to: use now, now-<N><s|m|h|d|w> or an ISO-8601 UTC time")
    f = lambda d: d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    return {"type": "absolute", "from": f(a), "to": f(b)}


async def _top_values(args: dict, ctx: Ctx):
    fld = str(args.get("field") or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_.@-]{1,100}", fld):
        raise ValueError("field: a Graylog field name, e.g. source_ip")
    limit = max(1, min(int(args.get("limit") or 10), 50))
    body = {"query": str(args.get("query") or "*"), "timerange": _timerange(args),
            "group_by": [{"field": fld, "limit": limit}], "metrics": [{"function": "count"}]}
    if args.get("distinct_field"):
        df = str(args["distinct_field"])
        if not re.fullmatch(r"[A-Za-z0-9_.@-]{1,100}", df):
            raise ValueError("distinct_field: a Graylog field name")
        body["metrics"].append({"function": "card", "field": df})
    res = await _graylog_post(ctx, "/api/search/aggregate", body)
    rows = []
    for r in res.get("datarows") or []:
        item = {"value": r[0], "count": int(r[1])}
        if len(r) > 2:
            item["distinct_" + args["distinct_field"]] = int(r[2])
        rows.append(item)
    return {"field": fld, "query": body["query"], "timerange": body["timerange"],
            "exact": True, "rows": rows,
            "note": '"(Empty Value)" counts the matching messages that have no value in this field.'}


async def _count(args: dict, ctx: Ctx):
    body = {"query": str(args.get("query") or "*"), "timerange": _timerange(args),
            "group_by": [{"field": "gl2_source_input", "limit": 1000}],
            "metrics": [{"function": "count"}]}
    res = await _graylog_post(ctx, "/api/search/aggregate", body)
    total = sum(int(r[1]) for r in res.get("datarows") or [])
    return {"query": body["query"], "timerange": body["timerange"], "count": total, "exact": True}


SAMPLE_MAX = 20
SAMPLE_TEXT_CHARS = 300
_SAMPLE_BASE_FIELDS = ("timestamp", "source", "message")


async def _graylog_get(ctx: Ctx, path: str, params: dict) -> dict:
    import httpx
    async with httpx.AsyncClient(verify=bool(ctx.server.verify_ssl), timeout=GRAYLOG_TIMEOUT_SEC,
                                 auth=ctx.auth, headers={"X-Requested-By": "jt-glogarch",
                                                         "Accept": "application/json"}) as c:
        try:
            r = await c.get(_base_url(ctx.server) + path, params=params)
        except httpx.TimeoutException:
            raise RuntimeError(f"Graylog did not answer within {GRAYLOG_TIMEOUT_SEC} s: "
                               "narrow the time range or the query")
        if r.status_code >= 400:
            try:
                msg = r.json().get("message") or r.text
            except ValueError:
                msg = r.text
            raise RuntimeError(f"Graylog HTTP {r.status_code}: {str(msg)[:300]}")
        return r.json()


async def _sample(args: dict, ctx: Ctx):
    """A few of the newest matching messages, chosen fields only, long text cut.
    For looking at examples; never for counting (use count_messages)."""
    limit = max(1, min(int(args.get("limit") or 10), SAMPLE_MAX))
    extra = [f for f in (args.get("fields") or []) if isinstance(f, str)]
    for f in extra:
        if not re.fullmatch(r"[A-Za-z0-9_.@-]{1,100}", f):
            raise ValueError("fields: Graylog field names, e.g. [\"source_ip\", \"user_name\"]")
    fields = list(dict.fromkeys([*_SAMPLE_BASE_FIELDS, *extra[:15]]))
    tr = _timerange(args)
    res = await _graylog_get(ctx, "/api/search/universal/absolute", {
        "query": str(args.get("query") or "*"), "from": tr["from"], "to": tr["to"],
        "limit": limit, "fields": ",".join(fields), "sort": "timestamp:desc", "decorate": "false"})
    out = []
    for m in res.get("messages") or []:
        msg = m.get("message") or {}
        row = {}
        for f in fields:
            v = msg.get(f)
            if v in (None, ""):
                continue
            v = v if isinstance(v, (int, float, bool)) else str(v)
            if isinstance(v, str) and len(v) > SAMPLE_TEXT_CHARS:
                v = v[:SAMPLE_TEXT_CHARS] + "..."
            row[f] = v
        out.append(row)
    return {"query": str(args.get("query") or "*"), "timerange": tr,
            "total_matching": res.get("total_results"), "messages": out,
            "note": "Newest first. A SAMPLE for reading examples; use count_messages for numbers."}


# --- statistics and summaries computed here, not by the model (1.36) ------------
# Owner 2026-11-26: "有沒有先我們程式處理完可以先統計 篩選 處理 之類再給 llm 處理"; and
# "撈資料時 要留意 graylog opensearch 的 timeout 與筆數上限".
# Measured on Graylog 7.2.2 (/api/search/aggregate): up to 3 groupings with any of
# count/card/min/max/sum/avg/latest/percentile/stddev; a grouping takes ONE of
# limit / timeunit; "timestamp" with a timeunit = time buckets; no grouping = 400;
# a field nobody has gives "(Empty Value)" and its metrics read 0.0;
# count(field) = messages that have the field; limit 100000 is accepted, so the
# caps below protect OpenSearch's search.max_buckets (65,535 by default).
AGG_MAX_GROUPS = 3
AGG_MAX_LIMIT = 1000
AGG_MAX_ROWS = 10000               # product of the group sizes
AGG_MAX_TIME_BUCKETS = 500
AGG_MAX_METRICS = 8
_TIME_METRICS = ("min(timestamp)", "max(timestamp)", "latest(timestamp)")
_FIELD = r"[A-Za-z0-9_.@-]{1,100}"
_METRIC_RE = re.compile(rf"(count|card|min|max|sum|avg|latest|stddev|p(\d{{1,2}}(?:\.\d+)?))(?::({_FIELD}))?")
_GROUP_RE = re.compile(rf"({_FIELD})(?::(\d+|\d+[smhdw]))?")
_STEPS = ((60, "1m"), (300, "5m"), (900, "15m"), (1800, "30m"), (3600, "1h"), (10800, "3h"),
          (21600, "6h"), (43200, "12h"), (86400, "1d"), (604800, "1w"))


def _span_sec(tr: dict) -> float:
    a = datetime.fromisoformat(tr["from"].replace("Z", "+00:00"))
    b = datetime.fromisoformat(tr["to"].replace("Z", "+00:00"))
    return max(1.0, (b - a).total_seconds())


def _metric_spec(m: str) -> tuple[dict, str]:
    mm = _METRIC_RE.fullmatch(str(m).strip())
    if not mm:
        raise ValueError(f"metrics: '{m}' is not one of count, count:<field>, card:<field>, min:<field>, "
                         "max:<field>, sum:<field>, avg:<field>, latest:<field>, stddev:<field>, p95:<field>")
    fn, pct, fld = mm.group(1), mm.group(2), mm.group(3)
    if fn != "count" and not fld:
        raise ValueError(f"metrics: '{m}' needs a field, e.g. {fn}:source_ip")
    if pct:
        spec = {"function": "percentile", "field": fld, "configuration": {"percentile": float(pct)}}
    else:
        spec = {"function": fn}
        if fld:
            spec["field"] = fld
    return spec, (f"{fn}({fld})" if fld else fn)


async def _aggregate(args: dict, ctx: Ctx):
    tr = _timerange(args)
    span = _span_sec(tr)
    raw_groups = args.get("group_by") or []
    if isinstance(raw_groups, str):
        raw_groups = [raw_groups]
    if not raw_groups or len(raw_groups) > AGG_MAX_GROUPS:
        raise ValueError(f"group_by: 1 to {AGG_MAX_GROUPS} fields, e.g. [\"user_name\", \"source_ip:5\"] "
                         "or [\"timestamp:1h\", \"event_outcome\"]")
    groups, names, notes, rows_max = [], [], [], 1
    for i, g in enumerate(raw_groups):
        gm = _GROUP_RE.fullmatch(str(g).strip())
        if not gm:
            raise ValueError(f"group_by: '{g}' is not a field name (optionally field:<rows> or timestamp:<1h>)")
        fld, opt = gm.group(1), gm.group(2)
        if fld == "timestamp":
            want = opt if opt and not opt.isdigit() else ""
            secs = 0
            if want:
                n, u = int(want[:-1]), want[-1]
                secs = n * {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}[u]
            if not secs or span / secs > AGG_MAX_TIME_BUCKETS:
                # the smallest standard step that keeps the buckets under the cap (200 when not asked)
                cap = AGG_MAX_TIME_BUCKETS if secs else 200
                step = next(((s_, n_) for s_, n_ in _STEPS if span / s_ <= cap), _STEPS[-1])
                if want:
                    notes.append(f"timestamp:{want} would make {int(span / secs):,} buckets; "
                                 f"used {step[1]} instead (at most {AGG_MAX_TIME_BUCKETS})")
                secs, want = step
            groups.append({"field": "timestamp", "timeunit": want})
            rows_max *= max(1, int(span / secs) + 1)
            names.append(f"timestamp ({want})")
        else:
            lim = int(opt) if opt and opt.isdigit() else (int(args.get("limit") or 10) if i == 0 else 5)
            lim = max(1, min(lim, AGG_MAX_LIMIT))
            groups.append({"field": fld, "limit": lim})
            rows_max *= lim
            names.append(fld)
    if rows_max > AGG_MAX_ROWS:
        raise ValueError(f"group_by: up to {rows_max:,} rows; at most {AGG_MAX_ROWS:,} "
                         "(fewer rows per field, a coarser time step or a shorter range)")
    raw_metrics = args.get("metrics") or ["count"]
    if isinstance(raw_metrics, str):
        raw_metrics = [raw_metrics]
    if len(raw_metrics) > AGG_MAX_METRICS:
        raise ValueError(f"metrics: at most {AGG_MAX_METRICS}")
    specs, labels = [], []
    for m in raw_metrics:
        sp, lb = _metric_spec(m)
        specs.append(sp)
        labels.append(lb)
    sort = str(args.get("sort") or "").strip()
    if sort:
        parts = sort.split()
        target = parts[0]
        order = parts[1].lower() if len(parts) > 1 else "desc"
        lb = _metric_spec(target)[1]
        if lb not in labels or order not in ("asc", "desc"):
            raise ValueError("sort: one of the metrics and asc|desc, e.g. \"count desc\" or \"card:user_name desc\"")
        specs[labels.index(lb)]["sort"] = order
    # how many matching messages have each metric field: a field nobody has reads 0
    probe_fields = sorted({sp["field"] for sp in specs if sp.get("field")})
    hidden = [{"function": "count", "field": f} for f in probe_fields]
    body = {"query": str(args.get("query") or "*"), "timerange": tr, "group_by": groups,
            "metrics": specs + hidden}
    res = await _graylog_post(ctx, "/api/search/aggregate", body)
    ng, nm = len(groups), len(specs)
    rows, have = [], {f: 0 for f in probe_fields}
    for r in res.get("datarows") or []:
        row = {names[i]: r[i] for i in range(ng)}
        for j, lb in enumerate(labels):
            v = r[ng + j] if ng + j < len(r) else None
            if isinstance(v, float) and v.is_integer() and lb.startswith(("count", "card")):
                v = int(v)
            elif lb in _TIME_METRICS and isinstance(v, (int, float)) and v > 0:
                # min/max/latest of timestamp come back as epoch milliseconds
                v = datetime.fromtimestamp(v / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
            row[lb] = v
        for k, f in enumerate(probe_fields):
            v = r[ng + nm + k] if ng + nm + k < len(r) else 0
            have[f] += int(v or 0)
        rows.append(row)
    for f, n in have.items():
        if rows and n == 0:
            notes.append(f"no matching message has the field {f}: its metrics read 0 (check the field name with list_fields)")
    return {"query": body["query"], "timerange": tr, "group_by": names, "metrics": labels, "exact": True,
            "rows_total": len(rows), "rows": rows, "notes": notes,
            "note": '"(Empty Value)" = matching messages without a value in that field. Every number is exact '
                    "(an aggregation in Graylog), not a sample."}


SUMMARY_PAGE = 500                 # messages per Graylog request
SUMMARY_DEFAULT = 2000
SUMMARY_MAX = 10000                # Graylog's paging stops at index.max_result_window (10,000)
SUMMARY_DEADLINE_SEC = 60
SUMMARY_PATTERNS = 40
_NORM = [
    (re.compile(r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?"), "<TIME>"),
    (re.compile(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) +\d{1,2} \d{2}:\d{2}:\d{2}\b"), "<TIME>"),
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I), "<UUID>"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "<EMAIL>"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}(?::\d{1,5})?\b"), "<IP>"),
    (re.compile(r"\b(?:[0-9a-f]{1,4}:){2,7}[0-9a-f]{1,4}\b", re.I), "<IP>"),
    (re.compile(r"\b(?:0x)?[0-9a-f]{12,}\b", re.I), "<HEX>"),
    (re.compile(r"\d+"), "<N>"),
    (re.compile(r"\s+"), " "),
]


def message_pattern(text: str) -> str:
    """The shape of a log line: times, ids, addresses and numbers replaced."""
    t = str(text or "")[:2000]
    for rx, rep in _NORM:
        t = rx.sub(rep, t)
    return t.strip()[:300]


def merge_patterns(pats: dict[str, dict], keep: int = SUMMARY_PATTERNS) -> dict[str, dict]:
    """When there are more patterns than `keep`: patterns with the same words except
    ONE position (an account, a host, a file name) become one, that word <*>.
    Repeated while it still merges and there are too many."""
    for _ in range(3):
        if len(pats) <= keep:
            break
        buckets: dict[str, list[str]] = {}
        for key in pats:
            toks = key.split(" ")
            if len(toks) < 3:
                continue
            for i in range(len(toks)):
                if toks[i].startswith("<"):
                    continue
                buckets.setdefault(" ".join(toks[:i] + ["<*>"] + toks[i + 1:]), []).append(key)
        merged_any, used = False, set()
        for mkey, members in sorted(buckets.items(), key=lambda kv: -len(kv[1])):
            members = [m for m in members if m not in used and m in pats]
            if len(members) < 3:
                continue
            base = pats.pop(members[0])
            used.add(members[0])
            for m in members[1:]:
                o = pats.pop(m)
                used.add(m)
                base["count"] += o["count"]
                base["first"] = min(filter(None, [base["first"], o["first"]]), default="")
                base["last"] = max(base["last"], o["last"])
                base["sources"].update(o["sources"])
                for f, c in o["fields"].items():
                    base["fields"].setdefault(f, Counter()).update(c)
            base["pattern"] = mkey
            prev = pats.get(mkey)
            if prev is not None:      # the same shape again: add to it
                prev["count"] += base["count"]
                prev["sources"].update(base["sources"])
            else:
                pats[mkey] = base
            merged_any = True
        if not merged_any:
            break
    return pats


async def _summarize(args: dict, ctx: Ctx):
    import time as _time
    want = max(100, min(int(args.get("max_messages") or SUMMARY_DEFAULT), SUMMARY_MAX))
    extra = [f for f in (args.get("fields") or []) if isinstance(f, str)][:5]
    for f in extra:
        if not re.fullmatch(_FIELD, f):
            raise ValueError("fields: Graylog field names, e.g. [\"user_name\"]")
    fields = list(dict.fromkeys(["timestamp", "source", "message", *extra]))
    tr = _timerange(args)
    q = str(args.get("query") or "*")
    t0 = _time.monotonic()
    got, total, stopped = 0, None, ""
    pats: dict[str, dict] = {}
    while got < want:
        if _time.monotonic() - t0 > SUMMARY_DEADLINE_SEC:
            stopped = f"stopped after {SUMMARY_DEADLINE_SEC} s"
            break
        asked = min(SUMMARY_PAGE, want - got)
        res = await _graylog_get(ctx, "/api/search/universal/absolute", {
            "query": q, "from": tr["from"], "to": tr["to"], "limit": asked,
            "offset": got, "fields": ",".join(fields), "sort": "timestamp:desc", "decorate": "false"})
        if total is None:
            total = res.get("total_results")
        page = res.get("messages") or []
        for m in page:
            msg = m.get("message") or {}
            text = str(msg.get("message") or "")
            key = message_pattern(text)
            p = pats.get(key)
            ts = str(msg.get("timestamp") or "")
            if p is None:
                p = pats[key] = {"pattern": key, "count": 0, "first": ts, "last": ts,
                                 "sources": Counter(), "example": text[:300], "fields": {f: Counter() for f in extra}}
            p["count"] += 1
            if ts and ts < p["first"]:
                p["first"] = ts
            if ts and ts > p["last"]:
                p["last"] = ts
            p["sources"][str(msg.get("source") or "")] += 1
            for f in extra:
                v = msg.get(f)
                if v not in (None, ""):
                    p["fields"][f][str(v)[:100]] += 1
        got += len(page)
        if len(page) < asked:
            break
    pats = merge_patterns(pats)
    top = sorted(pats.values(), key=lambda p: -p["count"])[:SUMMARY_PATTERNS]
    out = []
    for p in top:
        item = {"pattern": p["pattern"], "count": p["count"], "share_pct": round(100 * p["count"] / max(got, 1), 1),
                "first": p["first"], "last": p["last"], "sources": p["sources"].most_common(3),
                "example": p["example"]}
        for f, c in p["fields"].items():
            if c:
                item[f] = c.most_common(3)
        out.append(item)
    covers = "all of them" if total is not None and got >= int(total) else f"the newest {got:,} of {total if total is not None else '?'}"
    return {"query": q, "timerange": tr, "total_matching": total, "messages_read": got, "covers": covers,
            "patterns_total": len(pats), "patterns": out, "stopped": stopped,
            "note": "Message patterns found by jt-glogarch (times, addresses, ids and numbers replaced). "
                    "Counts are within the messages read; for exact totals use count_messages or aggregate."}


async def _read_result(args: dict, ctx: Ctx):
    from glogarch.ai import results as R
    e = R.get(str(args.get("result_id") or ""), ctx.owner)
    if e is None:
        raise ValueError("result_id: unknown or expired (results are kept 30 minutes); run the tool again")
    return R.read(e, args, ctx.result_budget)


async def _incidents(args: dict, ctx: Ctx):
    rows, total = ctx.db.list_security_incidents(
        server=args.get("server") or None, status=args.get("status") or None,
        severity=args.get("severity") or None, limit=max(1, min(int(args.get("limit") or 20), 100)))
    keep = ("id", "server", "detector", "entity", "entity_field", "severity", "status", "is_new",
            "external", "first_seen", "last_seen", "runs", "peak_count", "metrics", "query")
    return {"total": total, "incidents": [{k: r.get(k) for k in keep} for r in rows]}


async def _incident(args: dict, ctx: Ctx):
    inc = ctx.db.get_security_incident(int(args.get("id")))
    if not inc:
        raise ValueError("no incident with that id")
    inc["mitre_attack"] = [{"id": t["id"], "name": t["name"]}
                           for t in techniques_for(inc["detector"], inc["entity"], (inc.get("metrics") or {}).get("sigma_tags"))]
    return inc


async def _cases(args: dict, ctx: Ctx):
    st = args.get("status") or None
    if st not in (None, "open", "in_progress", "closed"):
        raise ValueError("status: open, in_progress or closed")
    keep = ("id", "title", "status", "severity", "assignee", "created_at", "updated_at", "incidents", "notes")
    return {"cases": [{k: c.get(k) for k in keep} for c in ctx.db.list_security_cases(st, limit=50)]}


async def _case(args: dict, ctx: Ctx):
    c = ctx.db.get_security_case(int(args.get("id")))
    if not c:
        raise ValueError("no case with that id")
    keep = ("id", "detector", "entity", "entity_field", "severity", "status", "first_seen", "last_seen", "metrics")
    c["incidents"] = [{**{k: i.get(k) for k in keep},
                       "mitre_attack": [t["id"] for t in techniques_for(i["detector"], i["entity"],
                                                                        (i.get("metrics") or {}).get("sigma_tags"))]}
                      for i in c["incidents"]]
    return c


async def _risk(args: dict, ctx: Ctx):
    days = max(1, min(int(args.get("days") or 7), 90))
    incs = ctx.db.security_incidents_since(datetime.utcnow() - timedelta(days=days))
    from glogarch.security.threat_intel import matcher_for
    ranked = score_entities(incs, ctx.db.list_security_assets(),
                            ctx.db.latest_security_verdicts([i["id"] for i in incs]), limit=20,
                            ti=matcher_for(ctx.settings, ctx.db))
    return {"days": days, "entities": ranked,
            "note": "score = sum over open incidents of severity weight x external 1.5 x asset criticality x AI verdict"}


async def _archive_status(args: dict, ctx: Ctx):
    # own DB + a disk_usage call; SQLite reads are quick but keep them off the loop
    return await asyncio.to_thread(archive_status, ctx.db, ctx.settings)


def _own_tools() -> list[Tool]:
    rng = {"range_from": {"type": "string", "description": "Start: now-15m, now-24h, now-7d, or ISO-8601 UTC (2026-11-19T00:00:00Z). Default now-1h."},
           "range_to": {"type": "string", "description": "End: now or ISO-8601 UTC. Default now."}}
    q = {"query": {"type": "string", "description": "Graylog search query (Lucene). Quote values: source_ip:\"203.0.113.9\". Failed logins: event_category:authentication AND event_outcome:failure. Default *."}}
    return [
        Tool("count_messages", "EXACT number of messages matching a Graylog query in a time range (aggregation, nothing is sampled). Use this for any 'how many' question.",
             {"type": "object", "properties": {**q, **rng}}, _count),
        Tool("top_values", "EXACT top values of one field for a query, with counts (and optionally the number of distinct values of another field per row, e.g. distinct user_name per source_ip). Use this for top-N questions.",
             {"type": "object", "properties": {"field": {"type": "string", "description": "Field to group by, e.g. source_ip, user_name, source, alert_signature."},
                                               **q, **rng,
                                               "limit": {"type": "integer", "description": "Rows, 1-50. Default 10."},
                                               "distinct_field": {"type": "string", "description": "Optional: count distinct values of this field per row."}},
              "required": ["field"]}, _top_values),
        Tool("sample_messages", "A few of the NEWEST messages matching a Graylog query (at most 20, chosen fields, long text cut), to read what the events look like. Never use it to count.",
             {"type": "object", "properties": {**q, **rng,
                                               "limit": {"type": "integer", "description": "Messages, 1-20. Default 10."},
                                               "fields": {"type": "array", "items": {"type": "string"},
                                                          "description": "Extra fields besides timestamp, source and message, e.g. [\"source_ip\", \"user_name\"]."}}},
             _sample, range_capped=True),
        Tool("aggregate", "EXACT statistics computed by Graylog (nothing sampled, no messages pulled): group by 1-3 fields and get counts and other metrics per group. Use it for any breakdown: who/what/where x count, distinct values, first/last time, sums, averages, time trends. Ranges up to 31 days.",
             {"type": "object", "properties": {
                 **q, **rng,
                 "group_by": {"type": "array", "items": {"type": "string"},
                              "description": "1-3 fields. 'field' or 'field:<rows>' (default 10 for the first, 5 for the others, at most 1000); 'timestamp:<step>' for time buckets (1m 5m 15m 30m 1h 3h 6h 12h 1d 1w; too fine a step is made coarser). E.g. [\"user_name\", \"source_ip:5\"] or [\"timestamp:1h\", \"event_outcome\"]."},
                 "metrics": {"type": "array", "items": {"type": "string"},
                             "description": "Default [\"count\"]. Any of: count, count:<field> (messages having it), card:<field> (distinct values), min:<field>, max:<field> (min:timestamp / max:timestamp = first / last seen), sum:<field>, avg:<field>, latest:<field>, stddev:<field>, p95:<field> (any percentile)."},
                 "sort": {"type": "string", "description": "One metric and asc|desc, e.g. \"count desc\" (default) or \"card:user_name desc\"."},
                 "limit": {"type": "integer", "minimum": 1, "maximum": 1000, "description": "Rows of the first group_by field when it gives none, 1-1000. Default 10."}},
              "required": ["group_by"]}, _aggregate),
        Tool("summarize_messages", "Reads up to 10,000 of the NEWEST matching messages in jt-glogarch and returns their PATTERNS (times, addresses, ids and numbers replaced; similar lines merged), each with a count, first/last time, top sources and one example. Use it to see WHAT kinds of events a query returns when there are too many to read one by one. Not for exact totals (count_messages / aggregate).",
             {"type": "object", "properties": {
                 **q, **rng,
                 "max_messages": {"type": "integer", "minimum": 100, "maximum": 10000, "description": "Messages to read, 100-10000. Default 2000."},
                 "fields": {"type": "array", "items": {"type": "string"},
                            "description": "Up to 5 extra fields whose top values are given per pattern, e.g. [\"user_name\"]."}}},
             _summarize, range_capped=True),
        Tool("read_result", "Reads more of a tool result that was too big to show at once (its first part said result_id). Page through it, keep the rows where a field has a value, sort it, or count its rows by one field. Results are kept 30 minutes. Reading more costs no Graylog query.",
             {"type": "object", "properties": {
                 "result_id": {"type": "string"},
                 "offset": {"type": "integer", "minimum": 0, "maximum": 1000000, "description": "First row, default 0."},
                 "limit": {"type": "integer", "minimum": 1, "maximum": 500, "description": "Rows, 1-500, default 50."},
                 "page": {"type": "integer", "minimum": 1, "maximum": 100000, "description": "For a text result: the page number."},
                 "where": {"type": "object", "description": "Keep rows whose field equals a value, or contains it with a leading ~: {\"source\": \"web01\", \"message\": \"~timeout\"}."},
                 "sort_by": {"type": "string"}, "descending": {"type": "boolean"},
                 "fields": {"type": "array", "items": {"type": "string"}, "description": "Only these fields of each row."},
                 "group_by": {"type": "string", "description": "Count the (matching) rows by this field instead of listing them."}},
              "required": ["result_id"]}, _read_result),
        Tool("list_security_incidents", "Security incidents found by jt-glogarch's scheduled detections (brute force, password spraying, IDS alerts not blocked, web scanners...), newest first.",
             {"type": "object", "properties": {"status": {"type": "string", "enum": ["open", "acknowledged", "closed"]},
                                               "severity": {"type": "string", "enum": ["high", "medium", "low"]},
                                               "limit": {"type": "integer", "description": "1-100, default 20"}}}, _incidents),
        Tool("get_security_incident", "One security incident by id, with its metrics and the Graylog query that shows its events.",
             {"type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"]}, _incident),
        Tool("list_security_cases", "Investigations (cases) in jt-glogarch: groups of security incidents being worked on, with status, assignee and counts.",
             {"type": "object", "properties": {"status": {"type": "string", "enum": ["open", "in_progress", "closed"]}}}, _cases),
        Tool("get_security_case", "One investigation (case) by id: its incidents (with MITRE ATT&CK technique ids) and its timeline of notes and changes.",
             {"type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"]}, _case),
        Tool("security_risk_ranking", "Entities (addresses, accounts, signatures) ranked by risk score from the open security incidents of the last N days, with the asset each one is and how every point was counted.",
             {"type": "object", "properties": {"days": {"type": "integer", "description": "1-90, default 7"}}}, _risk),
        Tool("archive_status", "How jt-glogarch's archiving is doing. Per Graylog server: number of archives, earliest and latest archived time, hours since the latest, records, bytes, and the GAPS (time between the earliest and latest archive that no archive covers). Also: archives the last verify found corrupted/missing/tampered, running jobs with progress and estimated hours left, the last export, verify and cleanup jobs with their result notes and 7-day counts, every schedule with last and next run, and the archive disk's free space with months left at the current rate. Archives keep logs Graylog may already have deleted. Use it for any question about archiving, backups, retention or whether last night's export worked.",
             {"type": "object", "properties": {}}, _archive_status),
    ]


_mcpg_tools_cache: list[Tool] | None = None


async def _mcpg_tools() -> list[Tool]:
    global _mcpg_tools_cache
    if _mcpg_tools_cache is None:
        out = []
        for t in await mcpg().handle_list_tools():
            name = getattr(t, "name", "")
            if not name or name in MCPG_NEVER:
                continue
            schema = getattr(t, "inputSchema", None) or {"type": "object", "properties": {}}
            capped = "range_from" in (schema.get("properties") or {}) and name not in MCPG_LONG_RANGE
            out.append(Tool(name, getattr(t, "description", ""), schema, _mcpg_runner(name),
                            source="mcp_graylog", range_capped=capped))
        _mcpg_tools_cache = out
    return _mcpg_tools_cache


async def available_tools(settings) -> list[Tool]:
    cfg = _cfg(settings)
    enabled = set(getattr(cfg, "mcp_graylog_tools", None) or MCPG_DEFAULT)
    tools = list(_own_tools())
    try:
        tools += [t for t in await _mcpg_tools() if t.name in enabled]
    except Exception as e:  # the own tools still work without it
        global _warned
        if not _warned:
            _warned = True
            log.warning("mcp_graylog could not be loaded; its tools are unavailable", error=str(e))
    return tools


_warned = False


MAX_RESULT_CHARS = 12000          # default budget of one result (MCP, incident analysis); the chat sizes its own
GRAYLOG_RESULT_WINDOW = 10000     # index.max_result_window: paging past it fails
NUMBER_CAP = 1000   # a number argument without a schema maximum (top_n, limit...) stops here


def clamp_to_schema(schema: dict, args: dict) -> dict:
    """Numbers kept within the tool's own schema minimum/maximum (and NUMBER_CAP when it
    states none). The vendored mcp_graylog passes e.g. top_n straight into a Graylog
    aggregation; top_n=1000000 on `message` would run on the production heap (review)."""
    props = (schema or {}).get("properties") or {}
    out = dict(args)
    for k, v in args.items():
        spec = props.get(k) or {}
        if spec.get("type") not in ("integer", "number") or isinstance(v, bool):
            continue
        try:
            n = float(v) if spec.get("type") == "number" else int(v)
        except (TypeError, ValueError) as e:   # the tool reports a bad value itself
            log.debug("Tool argument left as given", arg=k, error=str(e))
            continue
        hi = spec.get("maximum", NUMBER_CAP if k not in ("lookback_hours", "hours", "days", "silent_minutes") else None)
        lo = spec.get("minimum")
        if hi is not None and n > hi:
            n = hi
        if lo is not None and n < lo:
            n = lo
        out[k] = n
    return out


async def call_tool(name: str, args: dict, ctx: Ctx) -> dict:
    """Run one tool and return {"ok": bool, "result"|"error", "truncated"}.
    Never raises: a failed tool is an answer the model can read."""
    tools = {t.name: t for t in await available_tools(ctx.settings)}
    t = tools.get(name)
    if t is None:
        return {"ok": False, "error": f"unknown or disabled tool: {name}"}
    if not isinstance(args, dict):
        return {"ok": False, "error": "arguments must be a JSON object"}
    allowed = set((t.schema.get("properties") or {}).keys())
    extra = set(args) - allowed
    if extra:
        return {"ok": False, "error": f"unknown argument(s): {', '.join(sorted(extra))}"}
    args = clamp_to_schema(t.schema, args)
    problem = query_problem(args.get("query")) if "query" in allowed else None
    if problem:
        return {"ok": False, "error": problem}
    cap = float(getattr(_cfg(ctx.settings), "max_range_hours", 24) or 24)
    if t.range_capped or "range_from" in allowed:
        rf = args.get("range_from") or (t.schema["properties"].get("range_from") or {}).get("default") or "now-1h"
        hrs = range_hours(rf, args.get("range_to") or "now")
        limit = cap if t.range_capped else max(cap, 24 * 31)
        if hrs is None:
            return {"ok": False, "error": "range_from / range_to: use now, now-<N><s|m|h|d|w> or an ISO-8601 UTC time"}
        if hrs > limit:
            return {"ok": False, "error": f"time range {hrs:.0f} h is over the {limit:.0f} h limit for {name}"
                                          + (" (it pulls messages); use count_messages or top_values for longer ranges"
                                             if t.range_capped else "")}
    if "lookback_hours" in allowed:
        try:
            lb = int(args.get("lookback_hours") or 0)
        except (TypeError, ValueError):
            return {"ok": False, "error": "lookback_hours: a whole number of hours"}
        if lb > MAX_LOOKBACK_HOURS:
            return {"ok": False, "error": f"lookback_hours {lb} is over the {MAX_LOOKBACK_HOURS} h limit"}
    if "offset" in allowed and name != "read_result":
        # Graylog pages with from/size: past index.max_result_window (10,000) the search fails
        try:
            end = int(args.get("offset") or 0) + int(args.get("limit") or 0)
        except (TypeError, ValueError):
            end = 0
        if end > GRAYLOG_RESULT_WINDOW:
            return {"ok": False, "error": f"offset + limit = {end:,} is past Graylog's {GRAYLOG_RESULT_WINDOW:,}-message "
                                          "window; narrow the time range or the query, or use summarize_messages / "
                                          "aggregate"}
    try:
        result = await t.run(args, ctx)
    except Exception as e:
        log.info("AI tool failed", tool=name, channel=ctx.channel, error=str(e))
        return {"ok": False, "error": str(e)[:500]}
    from glogarch.ai import results as R
    budget = max(2000, int(getattr(ctx, "result_budget", 0) or MAX_RESULT_CHARS))
    text, partial = R.shape(result, budget, ctx.owner, name, args)
    return {"ok": True, "result": text, "truncated": partial}
