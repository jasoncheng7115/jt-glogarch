# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""The ONE tool registry behind the AI chat and the MCP endpoint.

Tools come from two places:
  * the owner's mcp_graylog, vendored unmodified in glogarch/vendor/ (its own
    tool definitions and its own execute_tool()), and
  * jt-glogarch's own tools: exact counts and top values through Graylog's
    aggregation API, security incidents, archive coverage.

Every call runs as a given Graylog identity (the signed-in user's Graylog
session for the chat, the caller's token for MCP), so Graylog's permissions
apply. Read-only only.

Embedding notes (gaps reported to the mcp_graylog developer 2026-11-19, worked
around HERE, never by editing the vendored file):
  * it imports the `mcp` SDK at module level but jt-glogarch never runs its
    server -> a minimal stand-in for the names it uses (only when the real SDK
    is not installed), so jt-glogarch needs no new dependency;
  * importing it calls logging.basicConfig() and opens ~/.mcp_graylog.log at
    DEBUG -> HOME points at a throwaway dir for the import, the file handler is
    closed and the root logger restored;
  * one module-level `graylog_config` -> set per call under a lock, which also
    serialises its heavier sampling tools against a production Graylog;
  * its field distributions are SAMPLED (up to 30,000 messages pulled) ->
    exact `top_values` / `count_messages` here, and a time-range cap on every
    tool that pulls messages.
"""
from __future__ import annotations

import asyncio
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

from glogarch.utils.logging import get_logger

log = get_logger("ai.tools")

# mcp_graylog tools offered by default. Left out: its two [Debug] tools,
# search_messages_export (bulk export, the heaviest pull), and the content-pack
# detail tools - a pack can carry notification addresses and credentials, which
# the owner's rule keeps from leaving without a decision.
MCPG_DEFAULT = (
    "get_log_statistics", "analyze_time_patterns", "analyze_source_distribution",
    "analyze_error_patterns", "get_log_level_analysis", "analyze_field_distribution",
    "get_log_sample", "search_logs_paginated", "get_streams", "get_system_info",
    "get_current_time", "list_inputs", "list_index_sets", "list_indices", "list_fields",
    "list_content_packs", "list_dashboards", "get_dashboard",
)
MCPG_NEVER = ("test_accurate_counting", "test_source_analysis_fix")

_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
_WORDS = {"second": 1, "minute": 60, "hour": 3600, "day": 86400, "week": 604800}


# --- the vendored module ------------------------------------------------------

def _install_mcp_stand_in() -> None:
    """Names mcp_graylog uses at import time, when the real SDK is absent."""
    import importlib.util
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
    retried on every call: 1.9.44 does not even compile before Python 3.12
    (an f-string with a backslash in its expression, line 2499)."""
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
    m = re.fullmatch(r"now-(\d+)([smhdw])", s)
    if m:
        return now - timedelta(seconds=int(m.group(1)) * _UNITS[m.group(2)])
    m = re.fullmatch(r"(\d+)\s*(second|minute|hour|day|week)s?\s*ago", s)
    if m:
        return now - timedelta(seconds=int(m.group(1)) * _WORDS[m.group(2)])
    try:
        dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def range_hours(range_from, range_to, now: datetime | None = None) -> float | None:
    """Length of a tool's time range in hours, or None when either end is not
    a form we can read (refused: the cap must not be bypassable)."""
    now = now or datetime.now(timezone.utc)
    a, b = _point(range_from, now), _point(range_to, now)
    if a is None or b is None:
        return None
    return max(0.0, (b - a).total_seconds() / 3600)


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


def _mcpg_runner(name: str):
    async def run(args: dict, ctx: Ctx):
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


async def _graylog_post(ctx: Ctx, path: str, body: dict) -> dict:
    import httpx
    async with httpx.AsyncClient(verify=bool(ctx.server.verify_ssl), timeout=60,
                                 auth=ctx.auth, headers={"X-Requested-By": "jt-glogarch",
                                                         "Accept": "application/json"}) as c:
        r = await c.post(_base_url(ctx.server) + path, json=body)
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
    return inc


async def _coverage(args: dict, ctx: Ctx):
    rows = ctx.db.conn.execute(
        """SELECT server_name, COUNT(*) AS archives, MIN(time_from) AS earliest,
                  MAX(time_to) AS latest, SUM(message_count) AS records,
                  SUM(file_size_bytes) AS bytes
           FROM archives WHERE status != 'deleted' GROUP BY server_name""").fetchall()
    return {"servers": [dict(r) for r in rows],
            "note": "Archives hold logs that may already be gone from Graylog; times are UTC."}


def _own_tools() -> list[Tool]:
    rng = {"range_from": {"type": "string", "description": "Start: now-15m, now-24h, now-7d, or ISO-8601 UTC (2026-11-19T00:00:00Z). Default now-1h."},
           "range_to": {"type": "string", "description": "End: now or ISO-8601 UTC. Default now."}}
    q = {"query": {"type": "string", "description": "Graylog search query (Lucene). Quote values: source_ip:\"203.0.113.9\". Failed logins: event_category:authentication AND event_outcome:failure. Default *."}}
    return [
        Tool("count_messages", "EXACT number of messages matching a Graylog query in a time range (aggregation, nothing is sampled). Use this for any 'how many' question.",
             {"type": "object", "properties": {**q, **rng}}, _count),
        Tool("top_values", "EXACT top values of one field for a query, with counts (and optionally the number of distinct values of another field per row, e.g. distinct user_name per source_ip). Prefer this over analyze_field_distribution, which samples.",
             {"type": "object", "properties": {"field": {"type": "string", "description": "Field to group by, e.g. source_ip, user_name, source, alert_signature."},
                                               **q, **rng,
                                               "limit": {"type": "integer", "description": "Rows, 1-50. Default 10."},
                                               "distinct_field": {"type": "string", "description": "Optional: count distinct values of this field per row."}},
              "required": ["field"]}, _top_values),
        Tool("list_security_incidents", "Security incidents found by jt-glogarch's scheduled detections (brute force, password spraying, IDS alerts not blocked, web scanners...), newest first.",
             {"type": "object", "properties": {"status": {"type": "string", "enum": ["open", "acknowledged", "closed"]},
                                               "severity": {"type": "string", "enum": ["high", "medium", "low"]},
                                               "limit": {"type": "integer", "description": "1-100, default 20"}}}, _incidents),
        Tool("get_security_incident", "One security incident by id, with its metrics and the Graylog query that shows its events.",
             {"type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"]}, _incident),
        Tool("archive_coverage", "What jt-glogarch has archived per server: number of archives, earliest and latest time, records, bytes. Archives keep logs Graylog may already have deleted.",
             {"type": "object", "properties": {}}, _coverage),
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
            capped = "range_from" in (schema.get("properties") or {})
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


MAX_RESULT_CHARS = 12000


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
    try:
        result = await t.run(args, ctx)
    except Exception as e:
        log.info("AI tool failed", tool=name, channel=ctx.channel, error=str(e))
        return {"ok": False, "error": str(e)[:500]}
    text = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, default=str)
    truncated = len(text) > MAX_RESULT_CHARS
    return {"ok": True, "result": text[:MAX_RESULT_CHARS], "truncated": truncated}
