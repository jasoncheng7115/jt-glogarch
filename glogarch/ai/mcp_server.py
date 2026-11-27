# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""MCP endpoint for external AI clients (Claude Desktop, Open WebUI, opencode...).

Stateless Streamable HTTP, JSON-RPC 2.0 by hand (the jt-ipam pattern; no SDK):
initialize / ping / tools/list / tools/call, notifications accepted and ignored.
The tools are the SAME registry the built-in chat uses (glogarch/ai/graylog_tools).

Authentication is the caller's own Graylog API token (`Authorization: Bearer
<token>`, or Basic `<token>:token`), checked like a web login (allowed Graylog
roles), so Graylog's permissions apply and revoking the token in Graylog revokes
MCP access. Off by default (ai.mcp_enabled).
"""
from __future__ import annotations

import base64
import hashlib
import secrets
import threading
import time

import httpx

from glogarch.ai.chat import _audit_tool
from glogarch.ai.graylog_tools import Ctx, available_tools, call_tool
from glogarch.utils.logging import get_logger

log = get_logger("ai.mcp")

PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")
RATE_PER_MIN = 120
_AUTH_TTL = 60
# found by a review: refused tokens are limited per address (each new token costs two
# Graylog calls), a batch counts every call and has a size cap, and the tables stay small
AUTH_FAILS_PER_MIN = 20
MAX_BATCH = 20
MAX_BODY_BYTES = 1024 * 1024
_MAX_KEYS = 10_000

_auth_cache: dict[str, tuple[float, str | None, str]] = {}
_rate: dict[str, list[float]] = {}
_lock = threading.Lock()


def token_from_headers(headers) -> str:
    h = headers.get("authorization") or ""
    if h.lower().startswith("bearer "):
        return h[7:].strip()
    if h.lower().startswith("basic "):
        try:
            user, _, pw = base64.b64decode(h[6:].strip()).decode().partition(":")
        except ValueError:
            return ""
        return user if pw == "token" else ""
    return ""


def rate_key(kind: str, value: str) -> str:
    """A rate-limit key: a hash of the whole value (a token prefix let one caller use
    up another's quota), never the value itself."""
    return kind + ":" + hashlib.sha256(value.encode()).hexdigest()[:32]


def _prune(table: dict, now: float, keep: float) -> None:
    if len(table) <= _MAX_KEYS:
        return
    for k in [k for k, v in table.items() if not v or now - (v[-1] if isinstance(v, list) else v[0]) > keep]:
        table.pop(k, None)
    while len(table) > _MAX_KEYS:          # still too many: drop the oldest entries
        table.pop(next(iter(table)))


def rate_ok(key: str, now: float | None = None, limit: int = RATE_PER_MIN, cost: int = 1) -> bool:
    now = now or time.time()
    with _lock:
        _prune(_rate, now, 60)
        hits = [t for t in _rate.get(key, []) if now - t < 60]
        if len(hits) + cost > limit:
            _rate[key] = hits
            return False
        hits.extend([now] * cost)
        _rate[key] = hits
        return True


def auth_fail_blocked(ip: str, now: float | None = None) -> bool:
    """This address has had too many refused tokens in the last minute."""
    now = now or time.time()
    with _lock:
        return len([t for t in _rate.get(rate_key("fail", ip), []) if now - t < 60]) >= AUTH_FAILS_PER_MIN


def note_auth_fail(ip: str, now: float | None = None) -> None:
    rate_ok(rate_key("fail", ip), now, limit=10 ** 9)


async def authenticate(settings, server, token: str) -> tuple[str | None, str]:
    """(username, reason). Cached a minute per token+server."""
    from glogarch.web.authz import check_graylog_role
    key = hashlib.sha256(f"{server.name}\0{token}".encode()).hexdigest()
    now = time.time()
    with _lock:
        hit = _auth_cache.get(key)
        if hit and now - hit[0] < _AUTH_TTL:
            return hit[1], hit[2]
    async with httpx.AsyncClient(verify=bool(server.verify_ssl), timeout=15) as c:
        rc = await check_graylog_role(c, server.url, (token, "token"), settings.web.allowed_graylog_roles)
    user = rc.username if rc.allowed else None
    reason = "" if rc.allowed else (rc.reason or "not allowed")
    with _lock:
        _prune(_auth_cache, now, _AUTH_TTL)
        _auth_cache[key] = (now, user, reason)
    return user, reason


def _err(id_, code: int, msg: str) -> dict:
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": msg}}


def _ok(id_, result) -> dict:
    return {"jsonrpc": "2.0", "id": id_, "result": result}


async def handle(msg, ctx: Ctx, version: str, ip: str = "") -> dict | None:
    """One JSON-RPC message -> response (None for a notification)."""
    if isinstance(msg, dict) and msg.get("jsonrpc") == "2.0" and "method" not in msg \
            and ("result" in msg or "error" in msg):
        return None   # a response from the client (to a request we never send): nothing to answer
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or not isinstance(msg.get("method"), str):
        return _err(msg.get("id") if isinstance(msg, dict) else None, -32600, "Invalid Request")
    id_ = msg.get("id")
    method = msg["method"]
    params = msg.get("params") or {}
    if id_ is None:  # notification (notifications/initialized, cancelled, ...)
        return None
    if not isinstance(params, dict):
        return _err(id_, -32602, "Invalid params: an object is expected")
    if method == "initialize":
        asked = params.get("protocolVersion")
        return _ok(id_, {
            "protocolVersion": asked if asked in PROTOCOLS else PROTOCOLS[1],
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "jt-glogarch", "version": version},
            "instructions": (f"Read-only access to the logs in Graylog server '{ctx.server.name}' and to "
                             "jt-glogarch's security incidents and archive status. Times are UTC. "
                             "Use count_messages / top_values for exact numbers."),
        })
    if method == "ping":
        return _ok(id_, {})
    if method == "tools/list":
        tools = await available_tools(ctx.settings)
        return _ok(id_, {"tools": [{"name": t.name, "description": t.description, "inputSchema": t.schema}
                                   for t in tools]})
    if method == "tools/call":
        name = params.get("name") or ""
        args = params.get("arguments") or {}
        if not isinstance(name, str) or not isinstance(args, dict):
            return _err(id_, -32602, "Invalid params: name must be a string and arguments an object")
        res = await call_tool(name, args, ctx)
        _audit_tool(ctx, name, args, res, ip)
        text = res["result"] if res.get("ok") else f"Error: {res.get('error')}"
        if res.get("truncated"):
            text += "\n[truncated]"
        return _ok(id_, {"content": [{"type": "text", "text": text}], "isError": not res.get("ok")})
    return _err(id_, -32601, f"Method not found: {method}")


def new_session_id() -> str:
    return secrets.token_hex(16)
