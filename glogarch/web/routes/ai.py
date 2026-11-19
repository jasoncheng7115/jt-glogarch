# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""AI chat + MCP endpoint (added 1.21)."""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from glogarch import __version__
from glogarch.ai import llm
from glogarch.ai import mcp_server as M
from glogarch.ai.chat import run_chat
from glogarch.ai.graylog_tools import MCPG_DEFAULT, MCPG_NEVER, MCPG_OPTIONAL, Ctx, available_tools, mcpg_status
from glogarch.core.config import AiConfig
from glogarch.utils.logging import get_logger
from glogarch.utils.sanitize import sanitize
from glogarch.web import gl_identity
from glogarch.web.routes.api import _audit, _config_path, _db, _mask, _settings

log = get_logger("web.ai")
router = APIRouter()        # under /api
mcp_router = APIRouter()    # at the root: /mcp (outside the session-cookie /api middleware)

KEEPALIVE_SEC = 10
MAX_QUESTION = 4000
_LANGS = ("en", "zh-TW", "ja")


def _server(request: Request, name: str | None):
    settings = _settings(request)
    if name:
        srv = next((s for s in settings.servers if s.name == name), None)
        if srv is not None:
            return srv
    try:
        return settings.get_server()
    except ValueError:
        return None


def _public_settings(cfg: AiConfig) -> dict:
    d = cfg.model_dump()
    d["api_key"] = _mask(cfg.api_key)
    return d


@router.get("/ai/status")
async def ai_status(request: Request, server: str = ""):
    settings = _settings(request)
    cfg = settings.ai
    srv = _server(request, server)
    tools = await available_tools(settings)
    priv = llm.host_is_private(cfg.url) if cfg.url else None
    signed = gl_identity.signed_in_servers(request.session)
    return {
        "settings": _public_settings(cfg),
        "llm_private": priv,
        "servers": [s.name for s in settings.servers],
        "server": srv.name if srv else "",
        "signed_in": bool(srv and srv.name in signed),
        "graylog_user": signed.get(srv.name, "") if srv else "",
        "login_user": request.session.get("username", ""),
        "tools": [{"name": t.name, "source": t.source} for t in tools],
        "mcp_graylog": mcpg_status(),
        "mcp_graylog_default": list(MCPG_DEFAULT),
        "mcp_graylog_optional": list(MCPG_OPTIONAL),
        "usage": _db(request).ai_usage(),
        "mcp_url": str(request.base_url).rstrip("/") + "/mcp",
    }


@router.post("/ai/settings")
async def ai_save_settings(request: Request):
    body = await request.json() or {}
    settings = _settings(request)
    cur = settings.ai.model_dump()
    merged = {**cur, **{k: v for k, v in body.items() if k in cur}}
    if isinstance(merged.get("api_key"), str) and "***" in merged["api_key"]:
        merged["api_key"] = settings.ai.api_key           # masked = unchanged
    if str(merged.get("url") or "") != settings.ai.url and "api_key" not in body:
        merged["api_key"] = ""   # a stored key is never sent to a different server
    merged["mcp_graylog_tools"] = [t for t in (merged.get("mcp_graylog_tools") or [])
                                   if isinstance(t, str) and t not in MCPG_NEVER]
    try:
        new = AiConfig(**merged)
    except Exception as e:
        return JSONResponse({"error": f"Invalid settings: {e}"}, status_code=400)
    new.timeout_seconds = max(10, min(int(new.timeout_seconds), 900))
    new.max_tool_rounds = max(1, min(int(new.max_tool_rounds), 10))
    new.max_range_hours = max(1.0, min(float(new.max_range_hours), 24 * 7))
    new.temperature = max(0.0, min(float(new.temperature), 1.0))
    if new.url:
        reason = llm.check_url(new.url, new.allow_external)
        if reason:
            return JSONResponse({"error": reason}, status_code=400)
    elif new.enabled or new.analysis_enabled:
        return JSONResponse({"error": "Set the LLM URL first"}, status_code=400)

    from glogarch.core.config_writer import update_config

    def _mut(cfg):
        cfg["ai"] = new.model_dump()
    update_config(_config_path(request), _mut)
    was_external = settings.ai.allow_external
    settings.ai = new
    _audit(request, "ai_settings_saved",
           f"chat={new.enabled} analysis={new.analysis_enabled} mcp={new.mcp_enabled} url={new.url} model={new.model} "
           f"allow_external={new.allow_external}")
    if new.allow_external and not was_external:
        _audit(request, "ai_external_llm_allowed", f"url={new.url}")
    return {"status": "saved"}


@router.post("/ai/test")
async def ai_test(request: Request):
    cfg = _settings(request).ai
    if not cfg.url:
        return JSONResponse({"error": "Set the LLM URL first"}, status_code=400)
    try:
        models = await llm.list_models(cfg)
        rep = await llm.chat(cfg, [{"role": "user", "content": "Reply with the single word OK."}],
                             max_tokens=256)
    except llm.LLMError as e:
        return JSONResponse({"error": sanitize(str(e))}, status_code=502)
    _db(request).ai_add_usage(rep.tokens)
    return {"models": models, "model_listed": cfg.model in models, "reply": rep.content[:200],
            "tokens": rep.tokens, "private": llm.host_is_private(cfg.url)}


def _user(request: Request) -> str:
    return request.session.get("username", "")


@router.get("/ai/conversations")
def ai_conversations(request: Request):
    return {"items": _db(request).ai_list_conversations(_user(request))}


@router.get("/ai/conversations/{cid}")
def ai_conversation(request: Request, cid: int):
    c = _db(request).ai_get_conversation(cid, _user(request))
    if not c:
        return JSONResponse({"error": "Conversation not found"}, status_code=404)
    return c


@router.delete("/ai/conversations/{cid}")
def ai_delete_conversation(request: Request, cid: int):
    if not _db(request).ai_delete_conversation(cid, _user(request)):
        return JSONResponse({"error": "Conversation not found"}, status_code=404)
    _audit(request, "ai_conversation_deleted", f"conversation={cid}")
    return {"status": "deleted"}


def _sse(event: str, data: dict) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode()


@router.post("/ai/chat")
async def ai_chat(request: Request):
    settings = _settings(request)
    cfg = settings.ai
    if not cfg.enabled or not cfg.url:
        return JSONResponse({"error": "AI chat is turned off"}, status_code=400)
    body = await request.json() or {}
    question = str(body.get("message") or "").strip()
    if not question:
        return JSONResponse({"error": "Ask a question"}, status_code=400)
    if len(question) > MAX_QUESTION:
        return JSONResponse({"error": f"Question too long (over {MAX_QUESTION} characters)"}, status_code=400)
    lang = body.get("lang") if body.get("lang") in _LANGS else "en"
    db = _db(request)
    user = _user(request)
    srv = _server(request, body.get("server"))
    if srv is None:
        return JSONResponse({"error": "No Graylog server configured"}, status_code=400)
    ident = gl_identity.get(request.session, srv.name)
    if ident is None:
        # 403 + need_signin (never 401: the page's fetch helper treats 401 as a jt-glogarch logout)
        return JSONResponse({"error": "Sign in to Graylog to continue", "need_signin": True,
                             "server": srv.name}, status_code=403)
    why = llm.budget_left(cfg, db.ai_usage())
    if why:
        return JSONResponse({"error": why}, status_code=429)
    cid = body.get("conversation_id")
    history: list[dict] = []
    if cid:
        conv = db.ai_get_conversation(int(cid), user)
        if not conv:
            return JSONResponse({"error": "Conversation not found"}, status_code=404)
        history = conv["messages"]
    else:
        cid = db.ai_create_conversation(user, srv.name, question[:80])
    db.ai_add_message(int(cid), "user", question)
    _audit(request, "ai_chat", f"conversation={cid} server={srv.name} graylog_user={ident.username} "
                               f"question={question[:200]}")
    try:
        db.ai_prune(int(cfg.chat_retention_days))
    except Exception as e:
        log.warning("AI chat retention prune failed", error=str(e))
    ctx = Ctx(settings=settings, db=db, server=srv, auth=ident.auth,
              username=ident.username or user, channel="chat")
    ip = request.client.host if request.client else ""
    queue: asyncio.Queue = asyncio.Queue()

    async def emit(ev: dict):
        await queue.put(("progress", ev))

    async def work():
        try:
            res = await run_chat(cfg, ctx, history, question, lang, emit, ip=ip)
        except Exception as e:  # never leave the stream hanging
            log.warning("AI chat failed", error=str(e))
            res = {"answer": "", "tools": [], "tokens": 0, "model": cfg.model, "elapsed_ms": 0,
                   "error": sanitize(str(e))[:300]}
        if res["answer"]:
            db.ai_add_message(int(cid), "assistant", res["answer"], model=res["model"],
                              tools=res["tools"], tokens=res["tokens"], elapsed_ms=res["elapsed_ms"])
        await queue.put(("done", {**res, "conversation_id": int(cid)}))

    task = asyncio.create_task(work())

    async def stream():
        yield _sse("start", {"conversation_id": int(cid), "model": cfg.model,
                             "private": llm.host_is_private(cfg.url)})
        try:
            while True:
                try:
                    kind, data = await asyncio.wait_for(queue.get(), timeout=KEEPALIVE_SEC)
                except asyncio.TimeoutError:
                    yield b": keepalive\n\n"
                    continue
                yield _sse(kind, data)
                if kind == "done":
                    break
        finally:
            if not task.done():   # the browser went away (Stop): stop asking the model
                task.cancel()

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# --- MCP ------------------------------------------------------------------------

@mcp_router.get("/mcp")
def mcp_get():
    return Response(status_code=405, headers={"Allow": "POST, DELETE"})


@mcp_router.delete("/mcp")
def mcp_delete():
    """Stateless: there is no session to end."""
    return Response(status_code=204)


@mcp_router.post("/mcp")
async def mcp_post(request: Request):
    settings = request.app.state.settings
    if not settings.ai.mcp_enabled:
        return JSONResponse({"error": "MCP is turned off in jt-glogarch"}, status_code=403)
    token = M.token_from_headers(request.headers)
    if not token:
        return JSONResponse({"error": "Send a Graylog API token: Authorization: Bearer <token>"},
                            status_code=401, headers={"WWW-Authenticate": "Bearer"})
    srv = _server(request, request.headers.get("x-graylog-server"))
    if srv is None:
        return JSONResponse({"error": "No Graylog server configured"}, status_code=400)
    key = srv.name + ":" + token[:12]
    if not M.rate_ok(key):
        return JSONResponse({"error": "Too many requests"}, status_code=429, headers={"Retry-After": "60"})
    user, reason = await M.authenticate(settings, srv, token)
    if not user:
        return JSONResponse({"error": f"Graylog token refused: {reason}"}, status_code=403)
    try:
        payload = json.loads(await request.body() or b"null")
    except ValueError:
        return JSONResponse(M._err(None, -32700, "Parse error"), status_code=400)
    ctx = Ctx(settings=settings, db=request.app.state.db, server=srv, auth=(token, "token"),
              username=user, channel="mcp")
    ip = request.client.host if request.client else ""
    batch = payload if isinstance(payload, list) else [payload]
    out = [r for r in [await M.handle(m, ctx, __version__, ip) for m in batch] if r is not None]
    headers = {}
    if any(isinstance(m, dict) and m.get("method") == "initialize" for m in batch):
        headers["Mcp-Session-Id"] = M.new_session_id()
    if not out:
        return Response(status_code=202, headers=headers)
    return JSONResponse(out if isinstance(payload, list) else out[0], headers=headers)
