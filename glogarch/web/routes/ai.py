# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""AI chat + MCP endpoint (added 1.21)."""
from __future__ import annotations

import asyncio
import json
import re
import time
from urllib.parse import urlencode

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from glogarch import __version__
from glogarch.ai import llm
from glogarch.ai import mcp_server as M
from glogarch.ai.chat import run_chat
from glogarch.ai.graylog_tools import MCPG_DEFAULT, MCPG_NEVER, MCPG_OPTIONAL, Ctx, available_tools, mcpg_status
from glogarch.core.config import ANTHROPIC_URL, LLM_KINDS, AiConfig, LLMServerConfig
from glogarch.core.database import AI_MAX_PINNED
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
    for srv in d.get("llm_servers") or []:
        srv["api_key"] = _mask(srv.get("api_key") or "")
    return d


def _llm_public(cfg: AiConfig) -> list[dict]:
    out = []
    for s_ in cfg.llm_servers:
        url = s_.url or (ANTHROPIC_URL if s_.kind == "anthropic" else "")
        out.append({"name": s_.name, "kind": s_.kind, "model": s_.model, "default": s_.name == cfg.default_llm,
                    "private": llm.host_is_private(url) if url else None})
    return out


@router.get("/ai/status")
async def ai_status(request: Request, server: str = ""):
    settings = _settings(request)
    cfg = settings.ai
    srv = _server(request, server)
    tools = await available_tools(settings)
    d = cfg.llm()
    durl = (d.url or (ANTHROPIC_URL if d.kind == "anthropic" else "")) if d else ""
    priv = llm.host_is_private(durl) if durl else None
    signed = gl_identity.signed_in_servers(request.session)
    db = _db(request)
    user = _user(request)
    return {
        "settings": _public_settings(cfg),
        "llm_private": priv,
        "llms": _llm_public(cfg),
        "servers": [s.name for s in settings.servers],
        "server": srv.name if srv else "",
        "signed_in": bool(srv and srv.name in signed),
        "graylog_user": signed.get(srv.name, "") if srv else "",
        "login_user": request.session.get("username", ""),
        "tools": [{"name": t.name, "source": t.source} for t in tools],
        "mcp_graylog": mcpg_status(),
        "mcp_graylog_default": list(MCPG_DEFAULT),
        "mcp_graylog_optional": list(MCPG_OPTIONAL),
        "usage": db.ai_usage(),
        "usage_mine": db.ai_usage(username=user),
        "usage_llm": {x.name: db.ai_usage(llm=x.name) for x in cfg.llm_servers},
        "max_pinned": AI_MAX_PINNED,
        "mcp_url": str(request.base_url).rstrip("/") + "/mcp",
    }


_LEGACY = ("url", "model", "api_key", "timeout_seconds", "allow_external", "temperature")


def _stored_llms(cur: AiConfig) -> list[LLMServerConfig]:
    """The stored servers; a config changed at runtime through the 1.35 fields only
    (no list yet) counts as that one server."""
    if cur.llm_servers:
        return list(cur.llm_servers)
    if cur.url:
        return [LLMServerConfig(name=(cur.model or "LLM")[:60], url=cur.url, model=cur.model, api_key=cur.api_key,
                                timeout_seconds=cur.timeout_seconds, allow_external=cur.allow_external,
                                temperature=cur.temperature)]
    return []


def _norm_url(kind: str, url) -> str:
    u = str(url or "").strip().rstrip("/")
    return u or (ANTHROPIC_URL if kind == "anthropic" else "")


_LLM_NAME = re.compile(r"[^\x00-\x1f<>\\\"]{1,60}")


def _merge_llms(sent, stored: list[LLMServerConfig]) -> tuple[list[dict], str | None]:
    """The servers the form sent, with stored keys kept where the key came back
    masked or empty AND the server's URL and kind are unchanged (a stored key is
    never sent to another host). Returns (servers, error)."""
    if not isinstance(sent, list):
        return [], "llm_servers: a list"
    by_name = {x.name: x for x in stored}
    out, names = [], set()
    for raw in sent:
        if not isinstance(raw, dict):
            return [], "llm_servers: each entry an object"
        name = " ".join(str(raw.get("name") or "").split())
        if not _LLM_NAME.fullmatch(name):
            return [], "Each LLM server needs a name (up to 60 characters)"
        if name in names:
            return [], f"Two LLM servers are named {name}"
        names.add(name)
        kind = str(raw.get("kind") or "openai")
        if kind not in LLM_KINDS:
            return [], f"Unknown LLM server type: {kind}"
        url = _norm_url(kind, raw.get("url"))
        old = by_name.get(str(raw.get("old_name") or name)) or by_name.get(name)
        key = raw.get("api_key")
        if not isinstance(key, str) or "***" in key:
            # masked or absent = the stored key, only for the same type and URL; "" = cleared
            same_host = old is not None and old.kind == kind and _norm_url(old.kind, old.url) == url
            key = old.api_key if same_host else ""
        item = {k: raw.get(k) for k in LLMServerConfig.model_fields if k in raw}
        item.update(name=name, kind=kind, url=url, api_key=key)
        out.append(item)
    return out, None


_LOGO_RE = re.compile(r"data:image/(png|jpeg|svg\+xml);base64,[A-Za-z0-9+/=]+")
SUMMARY_LOGO_MAX = 1_500_000      # characters of one data URI


def _clean_summary_style(v) -> tuple[dict, str]:
    """The summary PDF's own look (owner 2026-11-27: "要設定 報告的 logo 或文字"): the same fields a
    report has for its cover and watermark, nothing else."""
    if not isinstance(v, dict):
        return {}, "summary_style must be an object"
    out: dict = {}
    for k in ("logo_data_uri", "header_logo_data_uri"):
        u = str(v.get(k) or "")
        if u:
            if len(u) > SUMMARY_LOGO_MAX or not _LOGO_RE.fullmatch(u):
                return {}, "A logo must be a PNG, JPEG or SVG image under about 1 MB"
            out[k] = u
    for k, n in (("kicker", 80), ("author", 120), ("header_text", 120), ("watermark_text", 120)):
        if str(v.get(k) or "").strip():
            out[k] = re.sub(r"[\x00-\x1f\x7f]", " ", str(v[k])).strip()[:n]
    try:
        out["logo_height_px"] = max(20, min(int(v.get("logo_height_px") or 72), 200))
    except (TypeError, ValueError):
        out["logo_height_px"] = 72
    col = str(v.get("brand_color") or "").strip()
    if col:
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", col):
            return {}, "brand_color: a colour like #6c63ff"
        out["brand_color"] = col
    out["watermark_enabled"] = bool(v.get("watermark_enabled"))
    out["watermark_size"] = v.get("watermark_size") if v.get("watermark_size") in ("small", "medium", "large") else "large"
    out["watermark_direction"] = v.get("watermark_direction") if v.get("watermark_direction") in ("diagonal", "horizontal") else "diagonal"
    out["watermark_append"] = [a for a in (v.get("watermark_append") or []) if a in ("server", "ip", "time")]
    return out, ""


@router.post("/ai/settings")
async def ai_save_settings(request: Request):
    body = await request.json() or {}
    settings = _settings(request)
    cur = settings.ai.model_dump()
    merged = {**cur, **{k: v for k, v in body.items() if k in cur and k not in ("api_key", "llm_servers") + _LEGACY}}
    if "llm_servers" not in body and any(k in body for k in _LEGACY):
        # a 1.21-1.35 client (or script): its single-server fields edit the default server
        stored = _stored_llms(settings.ai)
        target = next((x for x in stored if x.name == settings.ai.default_llm), stored[0] if stored else None)
        entry = target.model_dump() if target else {"name": str(body.get("model") or "LLM")[:60] or "LLM",
                                                    "kind": "openai"}
        for k in _LEGACY:
            if k in body and k != "api_key":
                entry[k] = body[k]
        entry["old_name"] = entry["name"]
        entry["api_key"] = body["api_key"] if "api_key" in body else None   # absent = the stored one (same URL)
        others = [x.model_dump() | {"api_key": None, "old_name": x.name} for x in stored
                  if target is None or x.name != target.name]
        body = {**body, "llm_servers": ([entry] + others) if target is None else
                [entry if x.name == target.name else next(o for o in others if o["name"] == x.name) for x in stored]}
    if "llm_servers" in body:
        servers, err = _merge_llms(body["llm_servers"], _stored_llms(settings.ai))
        if err:
            return JSONResponse({"error": err}, status_code=400)
        merged["llm_servers"] = servers
    merged["mcp_graylog_tools"] = [t for t in (merged.get("mcp_graylog_tools") or [])
                                   if isinstance(t, str) and t not in MCPG_NEVER]
    if "summary_style" in body:
        style, err = _clean_summary_style(body.get("summary_style"))
        if err:
            return JSONResponse({"error": err}, status_code=400)
        merged["summary_style"] = style
    try:
        new = AiConfig(**merged)
    except Exception as e:
        return JSONResponse({"error": f"Invalid settings: {e}"}, status_code=400)
    new.max_tool_rounds = max(1, min(int(new.max_tool_rounds), 10))
    new.max_range_hours = max(1.0, min(float(new.max_range_hours), 24 * 7))
    for x in new.llm_servers:
        x.timeout_seconds = max(10, min(int(x.timeout_seconds), 900))
        x.temperature = max(0.0, min(float(x.temperature), 1.0))
        x.context_tokens = max(0, min(int(x.context_tokens), 10_000_000))
        if x.effort not in ("", "low", "medium", "high", "xhigh", "max"):
            return JSONResponse({"error": f"LLM server {x.name}: effort must be low, medium, high, xhigh or max"},
                                status_code=400)
        reason = llm.check_url(x.url or (ANTHROPIC_URL if x.kind == "anthropic" else ""), x.allow_external)
        if reason:
            return JSONResponse({"error": f"LLM server {x.name}: {reason}"}, status_code=400)
    if (new.enabled or new.analysis_enabled) and not new.llm_servers:
        return JSONResponse({"error": "Set up an LLM server first"}, status_code=400)
    new.mirror_legacy()

    from glogarch.core.config_writer import update_config

    def _mut(cfg):
        cfg["ai"] = new.model_dump()
    update_config(_config_path(request), _mut)
    was = {x.name: x.allow_external for x in settings.ai.llm_servers}
    settings.ai = new
    _audit(request, "ai_settings_saved",
           f"chat={new.enabled} analysis={new.analysis_enabled} mcp={new.mcp_enabled} default={new.default_llm} "
           + " ".join(f"llm[{x.name}]={x.kind}:{x.url or ANTHROPIC_URL}:{x.model}:external={x.allow_external}"
                      for x in new.llm_servers))
    for x in new.llm_servers:
        if x.allow_external and not was.get(x.name):
            _audit(request, "ai_external_llm_allowed", f"llm={x.name} url={x.url or ANTHROPIC_URL}")
    return {"status": "saved"}


def _form_llm(request: Request, body: dict) -> LLMServerConfig | JSONResponse:
    """An LLM server from the settings form (not yet saved), or the stored one by name.
    A masked key means the stored one, and only for the stored URL and type."""
    cur = _settings(request).ai
    stored = _stored_llms(cur)
    if body.get("url") is None and body.get("kind") is None:
        if not body.get("llm") and request.url.path.endswith("/models"):
            return JSONResponse({"error": "Set the LLM URL first"}, status_code=400)   # an empty form
        want = str(body.get("llm") or "")
        x = next((s_ for s_ in stored if s_.name == want), None) or cur.llm(want or None) or (stored[0] if stored else None)
        if x is None:
            return JSONResponse({"error": "Set up an LLM server first"}, status_code=400)
        return x
    kind = str(body.get("kind") or "openai")
    if kind not in LLM_KINDS:
        return JSONResponse({"error": f"Unknown LLM server type: {kind}"}, status_code=400)
    url = str(body.get("url") or "").strip()
    if not url and kind == "openai":
        return JSONResponse({"error": "Set the LLM URL first"}, status_code=400)
    named = str(body.get("old_name") or body.get("name") or "")
    # the entry the form edits; a form without a name (a 1.35 page) edits the default
    old = next((x for x in stored if x.name == named), None) if named else (
        next((x for x in stored if x.name == cur.default_llm), stored[0] if stored else None))
    key = body.get("api_key")
    if not isinstance(key, str) or "***" in key:
        key = old.api_key if (old and old.kind == kind and _norm_url(old.kind, old.url) == _norm_url(kind, url)) else ""
    try:
        timeout = int(body.get("timeout_seconds") or 60)
    except (TypeError, ValueError):
        timeout = 60
    return LLMServerConfig(name=str(body.get("name") or "test")[:60], kind=kind, url=url, api_key=key,
                           model=str(body.get("model") or ""), allow_external=bool(body.get("allow_external")),
                           timeout_seconds=max(10, min(timeout, 300)),
                           context_tokens=int(body.get("context_tokens") or 0) if str(body.get("context_tokens") or "0").isdigit() else 0)


@router.post("/ai/models")
async def ai_models(request: Request):
    """The models the LLM server offers, for the settings form's model list."""
    body = await request.json() or {}
    cfg = _form_llm(request, body)
    if isinstance(cfg, JSONResponse):
        return cfg
    try:
        models = await llm.list_models(cfg)
    except llm.LLMError as e:
        return JSONResponse({"error": sanitize(str(e))}, status_code=502)
    except Exception as e:  # unreachable host, bad JSON: say so, never a bare 500
        return JSONResponse({"error": sanitize(f"LLM server unreachable ({e})")}, status_code=502)
    return {"models": sorted(set(models))}


@router.post("/ai/profile")
async def ai_profile(request: Request):
    """What jt-glogarch knows about the model: its context window and where that came from."""
    body = await request.json() or {}
    cfg = _form_llm(request, body)
    if isinstance(cfg, JSONResponse):
        return cfg
    from glogarch.ai.model_profile import profile
    return await profile(cfg)


@router.post("/ai/test")
async def ai_test(request: Request):
    body = {}
    try:
        body = await request.json() or {}
    except ValueError:
        body = {}
    cfg = _form_llm(request, body)
    if isinstance(cfg, JSONResponse):
        return cfg
    try:
        models = await llm.list_models(cfg)
        rep = await llm.chat(cfg, [{"role": "user", "content": "Reply with the single word OK."}],
                             max_tokens=256)
    except llm.LLMError as e:
        return JSONResponse({"error": sanitize(str(e))}, status_code=502)
    _db(request).ai_add_usage(rep.tokens, llm=cfg.name, username=_user(request))
    from glogarch.ai.model_profile import profile
    prof = await profile(cfg)
    url = cfg.url or (ANTHROPIC_URL if cfg.kind == "anthropic" else "")
    return {"models": models, "model_listed": cfg.model in models, "reply": rep.content[:200],
            "tokens": rep.tokens, "private": llm.host_is_private(url), "context": prof}


def _user(request: Request) -> str:
    return request.session.get("username", "")


CONV_PAGE = 50
CONV_MAX = 1000


@router.get("/ai/conversations")
def ai_conversations(request: Request, q: str = "", limit: int = CONV_PAGE):
    """The newest `limit` conversations (pinned ones on top, not counted); `more`
    says older ones exist, and the page asks again with a larger limit (owner
    2026-11-27: "超過的是不是不顯示 ... 顯示更多")."""
    user = _user(request)
    limit = max(1, min(int(limit or CONV_PAGE), CONV_MAX))
    items = _db(request).ai_list_conversations(user, limit=limit + 1, q=q)
    rest = [c for c in items if not c.get("pinned_at")]
    more = len(rest) > limit
    if more:
        drop = rest[-1]["id"]
        items = [c for c in items if c["id"] != drop]
    for c in items:
        st = _run_state(c["id"], user)
        c["running"] = bool(st and st["running"])
    return {"items": items, "more": more, "limit": limit}


@router.get("/ai/conversations/{cid}")
def ai_conversation(request: Request, cid: int):
    user = _user(request)
    c = _db(request).ai_get_conversation(cid, user)
    if not c:
        return JSONResponse({"error": "Conversation not found"}, status_code=404)
    c["run"] = _run_state(cid, user)
    settings = _settings(request)
    for m in c["messages"]:
        _link_calls(settings, c.get("server", ""), m.get("calls"))
    return c


def _link_calls(settings, server: str, calls) -> None:
    """Each recorded query gets a link to the same search in Graylog: the query
    and the absolute range the tool really ran with."""
    from glogarch.web.routes.alerting import _web_url
    bases: dict[str, str] = {}
    for c in calls or []:
        name = c.get("server") or server   # a conversation can switch server between questions
        if name not in bases:
            # exact name only: a removed server must not link to another one
            srv = next((x for x in settings.servers if x.name == name), None)
            bases[name] = _web_url(srv.url) if srv else ""
        base = bases[name]
        rng = c.get("range") or {}
        if not base:
            continue
        if c.get("ok") and isinstance(c.get("query"), str) and rng.get("from") and rng.get("to"):
            c["graylog_url"] = base + "/search?" + urlencode(
                {"q": c["query"], "rangetype": "absolute", "from": rng["from"], "to": rng["to"]})


@router.patch("/ai/conversations/{cid}")
async def ai_rename(request: Request, cid: int):
    body = await request.json() or {}
    if "pinned" in body and "title" not in body:
        res = _db(request).ai_pin_conversation(cid, _user(request), bool(body.get("pinned")))
        if res == "not_found":
            return JSONResponse({"error": "Conversation not found"}, status_code=404)
        if res == "full":
            return JSONResponse({"error": f"At most {AI_MAX_PINNED} conversations can be pinned"}, status_code=409)
        _audit(request, "ai_conversation_pinned", f"conversation={cid} pinned={bool(body.get('pinned'))}")
        return {"status": "pinned" if body.get("pinned") else "unpinned"}
    title = " ".join(str(body.get("title") or "").split())
    if not title:
        return JSONResponse({"error": "Give the conversation a title"}, status_code=400)
    if len(title) > 200:
        return JSONResponse({"error": "Title too long (over 200 characters)"}, status_code=400)
    if not _db(request).ai_rename_conversation(cid, _user(request), title):
        return JSONResponse({"error": "Conversation not found"}, status_code=404)
    _audit(request, "ai_conversation_renamed", f"conversation={cid} title={title[:80]}")
    return {"status": "renamed", "title": title}


# async (on the event loop): Task.cancel() is not thread-safe, and a plain def runs in a worker thread
@router.post("/ai/conversations/{cid}/stop")
async def ai_stop(request: Request, cid: int):
    r = _RUNNING.get(int(cid))
    if not r or r["user"] != _user(request) or r.get("done_at"):
        return JSONResponse({"error": "Nothing is running in this conversation"}, status_code=409)
    r["task"].cancel()
    _audit(request, "ai_chat_stopped", f"conversation={cid}")
    return {"status": "stopping"}


@router.delete("/ai/conversations/{cid}")
async def ai_delete_conversation(request: Request, cid: int):
    r = _RUNNING.get(int(cid))
    if r and r["user"] == _user(request) and not r.get("done_at"):
        r["task"].cancel()
    if not _db(request).ai_delete_conversation(cid, _user(request)):
        return JSONResponse({"error": "Conversation not found"}, status_code=404)
    _audit(request, "ai_conversation_deleted", f"conversation={cid}")
    return {"status": "deleted"}


# Questions being answered, by conversation id. An answer goes on when the browser
# leaves the page (owner, 2026-11-20: "我如果離開頁面再回來 可以點回此對話與進度嗎?"):
# only Stop or deleting the conversation cancels it. A finished entry stays a while
# so a page that comes back can still read an error. This process only.
_RUNNING: dict[int, dict] = {}
_KEEP_FINISHED_SEC = 15 * 60


REASONING_KEEP = 20000   # chars of the current reasoning a page that comes back is shown


def _prune_running() -> None:
    now = time.time()
    for cid in [c for c, r in _RUNNING.items() if r.get("done_at") and now - r["done_at"] > _KEEP_FINISHED_SEC]:
        _RUNNING.pop(cid, None)


def _run_state(cid: int, user: str) -> dict | None:
    r = _RUNNING.get(int(cid))
    if not r or r["user"] != user:
        return None
    return {"running": not r.get("done_at"), "progress": r.get("progress") or {},
            "partial": "" if r.get("done_at") else r.get("partial", ""),
            "reasoning": "" if r.get("done_at") else r.get("reasoning", ""),
            "started_at": r["started_at"], "error": r.get("error", ""), "question": r.get("question", "")}


def _sse(event: str, data: dict) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode()


@router.post("/ai/chat")
async def ai_chat(request: Request):
    settings = _settings(request)
    body = await request.json() or {}
    if not settings.ai.enabled or settings.ai.llm() is None:
        return JSONResponse({"error": "AI chat is turned off"}, status_code=400)
    want_llm = str(body.get("llm") or "")
    if want_llm and not any(x.name == want_llm for x in settings.ai.llm_servers):
        return JSONResponse({"error": f"Unknown LLM server {want_llm}"}, status_code=400)
    cfg = settings.ai.llm(want_llm or None)
    question = str(body.get("message") or "").strip()
    retry = bool(body.get("retry"))
    if retry:
        question = question or "-"   # the stored question is used; checked below
    if not question:
        return JSONResponse({"error": "Ask a question"}, status_code=400)
    if len(question) > MAX_QUESTION:
        return JSONResponse({"error": f"Question too long (over {MAX_QUESTION} characters)"}, status_code=400)
    lang = body.get("lang") if body.get("lang") in _LANGS else "en"
    theme = body.get("theme") if body.get("theme") in ("light", "dark") else "light"
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
    why = llm.limits_left(settings.ai, cfg, db, user)
    if why:
        return JSONResponse({"error": why}, status_code=429)
    cid = body.get("conversation_id")
    history: list[dict] = []
    _prune_running()
    if cid:
        # whose it is first: another user's conversation reads as not found, running or not
        conv = db.ai_get_conversation(int(cid), user)
        if not conv:
            return JSONResponse({"error": "Conversation not found"}, status_code=404)
        if (_RUNNING.get(int(cid)) or {}).get("task") and not _RUNNING[int(cid)].get("done_at"):
            return JSONResponse({"error": "This conversation is still answering the previous question"},
                                status_code=409)
        history = conv["messages"]
    elif retry:
        return JSONResponse({"error": "Nothing to answer again"}, status_code=409)
    else:
        cid = db.ai_create_conversation(user, srv.name, question[:80])
    if retry:
        # a question left without an answer (a restart, an error): answer it, once,
        # without storing it a second time
        if not history or history[-1]["role"] != "user":
            return JSONResponse({"error": "Nothing to answer again"}, status_code=409)
        question = history[-1]["content"]
        qid = history[-1].get("id")
        history = history[:-1]
    else:
        qid = db.ai_add_message(int(cid), "user", question)
    _audit(request, "ai_chat", f"conversation={cid} server={srv.name} llm={cfg.name} graylog_user={ident.username} "
                               f"{'retry=1 ' if retry else ''}question={question[:200]}")
    try:
        db.ai_prune(int(settings.ai.chat_retention_days))
    except Exception as e:
        log.warning("AI chat retention prune failed", error=str(e))
    ctx = Ctx(settings=settings, db=db, server=srv, auth=ident.auth,
              username=ident.username or user, channel="chat")
    ip = request.client.host if request.client else ""
    queue: asyncio.Queue = asyncio.Queue()

    run = {"user": user, "started_at": time.time(), "question": question[:200], "progress": {}}

    async def emit(ev: dict):
        if ev.get("phase") == "answer":
            # the answer as it is written; a page that comes back reads it whole
            run["partial"] = ev["text"] if ev.get("reset") else run.get("partial", "") + ev.get("delta", "")
            run["progress"] = {"phase": "writing"}
        elif ev.get("phase") == "reasoning":
            # the model's thinking as it is written; the phase line (round, tool) stays as it is
            r = ev["text"] if ev.get("reset") else run.get("reasoning", "") + ev.get("delta", "")
            run["reasoning"] = r[-REASONING_KEEP:]
        else:
            run["progress"] = ev
        await queue.put(("progress", ev))

    async def work():
        try:
            res = await run_chat(cfg, ctx, history, question, lang, emit, ip=ip, username=user,
                                 theme=theme)
        except asyncio.CancelledError:
            res = {"answer": "", "tools": [], "calls": [], "tokens": 0, "model": cfg.model, "elapsed_ms": 0,
                   "error": "Stopped", "stopped": True}
            try:
                if qid:
                    db.ai_mark_stopped(int(qid))   # the page shows the question as stopped
            except Exception as e:
                log.warning("Could not mark the question as stopped", conversation=cid, error=str(e))
        except Exception as e:  # never leave the stream hanging
            log.warning("AI chat failed", error=str(e))
            res = {"answer": "", "tools": [], "calls": [], "tokens": 0, "model": cfg.model, "elapsed_ms": 0,
                   "error": sanitize(str(e))[:300]}
        try:
            for c in res.get("calls") or []:
                c["server"] = srv.name
            if res["answer"]:
                res["message_id"] = db.ai_add_message(int(cid), "assistant", res["answer"], model=res["model"],
                                  tools=res["tools"], tokens=res["tokens"], elapsed_ms=res["elapsed_ms"],
                                  truncated=bool(res.get("truncated")), calls=res.get("calls") or [],
                                  followups=res.get("followups") or [], llm=cfg.name)
            _link_calls(settings, srv.name, res.get("calls"))
        except Exception as e:  # the answer could not be stored: say so, never stay "running"
            log.warning("AI answer could not be stored", conversation=cid, error=str(e))
            res = {**res, "answer": "", "error": sanitize(f"The answer could not be stored: {e}")[:300]}
        finally:
            run["error"] = "" if res["answer"] else res.get("error", "")
            run["done_at"] = time.time()
            await queue.put(("done", {**res, "conversation_id": int(cid)}))

    task = asyncio.create_task(work())
    run["task"] = task
    _RUNNING[int(cid)] = run

    async def stream():
        yield _sse("start", {"conversation_id": int(cid), "model": cfg.model, "llm": cfg.name,
                             "private": llm.host_is_private(cfg.url or ANTHROPIC_URL)})
        # A browser that goes away ends only this stream: the answer goes on and is
        # stored (Stop is POST .../stop). Measured with a real uvicorn in test_ai.py.
        while True:
            try:
                kind, data = await asyncio.wait_for(queue.get(), timeout=KEEPALIVE_SEC)
            except asyncio.TimeoutError:
                yield b": keepalive\n\n"
                continue
            yield _sse(kind, data)
            if kind == "done":
                break

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# --- preview of an HTML page / Mermaid diagram / SVG in an answer (1.36) ----------
# Owner 2026-11-26: "如果我們在對話中請模型產看板 (例如 html 的) 我們可以長出一個預覽窗格"
# and the same for Mermaid. What the model writes can be steered by text inside the
# logs it read, so the page runs in a sandbox: CSP `sandbox allow-scripts` (an opaque
# origin: no cookies, no jt-glogarch API, no parent page), no network at all
# (connect/img/font/frame/form all 'none' except inline and data:), no navigation of
# the top page, no popups. Chart.js and Mermaid are inlined from the package.

PREVIEW_MAX_CHARS = 1_000_000
_FENCE = re.compile(r"```[ \t]*(html|mermaid|svg|markdown|md)[ \t]*\n(.*?)\n```", re.S | re.I)
_PREVIEW_CSP = ("sandbox allow-scripts; default-src 'none'; script-src 'unsafe-inline'; "
                "style-src 'unsafe-inline'; img-src data: blob:; font-src data:; connect-src 'none'; "
                "media-src 'none'; frame-src 'none'; worker-src 'none'; form-action 'none'; base-uri 'none'; "
                "frame-ancestors 'self'")


_OPEN_FENCE = re.compile(r"```[ \t]*(html|mermaid|svg|markdown|md)[ \t]*\n(.*)\Z", re.S | re.I)
_PREVIEW_THEMES = ("light", "dark")


def _kind(k: str) -> str:
    k = k.lower()
    return "markdown" if k == "md" else k


def preview_blocks(text: str, partial: bool = False) -> list[tuple[str, str]]:
    """The previewable blocks of an answer. `partial`: the answer is still being
    written, so a last block whose closing fence has not come yet counts too."""
    text = text or ""
    out, end = [], 0
    for m in _FENCE.finditer(text):
        out.append((_kind(m.group(1)), m.group(2)))
        end = m.end()
    if partial:
        m = _OPEN_FENCE.search(text, end)
        if m and "```" not in m.group(2):
            out.append((_kind(m.group(1)), m.group(2)))
    return out


def _asset(rel: str) -> str:
    from pathlib import Path
    p = Path(__file__).resolve().parent.parent.parent / rel
    try:
        return p.read_text(encoding="utf-8")
    except OSError as e:
        log.warning("Preview asset missing", path=str(p), error=str(e))
        return ""


def _script(js: str) -> str:
    return "<script>" + js.replace("</script", "<\\/script") + "</script>"


def _mermaid_script(theme: str) -> str:
    return (_script(_asset("ai/assets/mermaid.min.js"))
            + _script("mermaid.initialize({startOnLoad:false,securityLevel:'strict',theme:'"
                      + ("dark" if theme == "dark" else "default") + "'});"
                      "mermaid.run().catch(function(e){var p=document.createElement('pre');p.className='err';"
                      "p.textContent='Mermaid: '+(e&&e.message||e);document.body.appendChild(p);});"))


def preview_document(kind: str, src: str, theme: str = "light") -> str:
    """An HTML page keeps its own colours; Markdown and Mermaid follow the page's theme."""
    src = src[:PREVIEW_MAX_CHARS]
    theme = theme if theme in _PREVIEW_THEMES else "light"
    if kind == "markdown":
        from glogarch.ai import mdpreview
        body, has_mermaid = mdpreview.render(src)
        return ("<!doctype html><html><head><meta charset=\"utf-8\">" + mdpreview.page_style(theme)
                + "</head><body>" + body + (_mermaid_script(theme) if has_mermaid else "") + "</body></html>")
    if kind == "html":
        doc = src if re.search(r"<html|<body|<!doctype", src, re.I) else (
            "<!doctype html><html><head><meta charset=\"utf-8\"></head><body>" + src + "</body></html>")
        if "Chart(" in doc or "chart.js" in doc.lower():
            lib = _script(_asset("report/assets/chart.umd.min.js"))
            # Chart.js before the page's own scripts; any <script src=...> stays blocked by the CSP
            doc = re.sub(r"<head[^>]*>", lambda m: m.group(0) + lib, doc, count=1, flags=re.I) \
                if re.search(r"<head[^>]*>", doc, re.I) else lib + doc
        return doc
    if kind == "svg":
        return ("<!doctype html><html><head><meta charset=\"utf-8\"><style>body{margin:16px;background:#fff}"
                "svg{max-width:100%;height:auto}</style></head><body>" + src + "</body></html>")
    # mermaid: the source as text, rendered by the bundled library (securityLevel strict)
    esc = src.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    bg = "#12131c" if theme == "dark" else "#fff"
    return ("<!doctype html><html><head><meta charset=\"utf-8\"><style>body{margin:16px;background:" + bg + ";"
            "font-family:sans-serif}pre.err{color:#e5484d;white-space:pre-wrap}</style></head><body>"
            "<pre class=\"mermaid\">" + esc + "</pre>" + _mermaid_script(theme) + "</body></html>")


@router.get("/ai/messages/{mid}/preview/{n}")
def ai_preview(request: Request, mid: int, n: int, download: int = 0, theme: str = "light"):
    m = _db(request).ai_get_message(mid, _user(request))
    if not m or m.get("role") != "assistant":
        return JSONResponse({"error": "Message not found"}, status_code=404)
    blocks = preview_blocks(m.get("content") or "")
    if n < 0 or n >= len(blocks):
        return JSONResponse({"error": "Nothing to preview"}, status_code=404)
    kind, src = blocks[n]
    if download:
        ext = {"html": "html", "svg": "svg", "mermaid": "mmd", "markdown": "md"}[kind]
        body = src if kind != "html" else preview_document(kind, src)
        return Response(body, media_type="application/octet-stream",
                        headers={"Content-Disposition": f'attachment; filename="jt-glogarch-ai-{mid}-{n + 1}.{ext}"',
                                 "X-JT-Preview": "1"})
    return Response(preview_document(kind, src, theme), media_type="text/html; charset=utf-8",
                    headers={"X-JT-Preview": "1", "Content-Security-Policy": _PREVIEW_CSP})


@router.get("/ai/conversations/{cid}/live-preview/{n}")
def ai_live_preview(request: Request, cid: int, n: int, theme: str = "light"):
    """The page / diagram the model is writing right now, as far as it got (owner
    2026-11-27: open the preview as soon as it can show something and keep it up to
    date). Same sandbox as a stored answer's preview; 404 once the answer is done."""
    r = _RUNNING.get(int(cid))
    if not r or r["user"] != _user(request) or r.get("done_at"):
        return JSONResponse({"error": "Nothing is being written"}, status_code=404)
    blocks = preview_blocks(r.get("partial", ""), partial=True)
    if n < 0 or n >= len(blocks):
        return JSONResponse({"error": "Nothing to preview"}, status_code=404)
    kind, src = blocks[n]
    return Response(preview_document(kind, src, theme), media_type="text/html; charset=utf-8",
                    headers={"X-JT-Preview": "1", "Content-Security-Policy": _PREVIEW_CSP,
                             "Cache-Control": "no-store"})


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
    wanted = request.headers.get("x-graylog-server")
    if wanted and not settings.has_server(wanted):
        # an unknown name would silently read the default server (another cluster's data)
        return JSONResponse({"error": f"Unknown Graylog server '{wanted}'"}, status_code=400)
    srv = _server(request, wanted)
    if srv is None:
        return JSONResponse({"error": "No Graylog server configured"}, status_code=400)
    ip = request.client.host if request.client else ""
    if M.auth_fail_blocked(ip):
        return JSONResponse({"error": "Too many refused tokens"}, status_code=429, headers={"Retry-After": "60"})
    key = M.rate_key("tok", srv.name + "\0" + token)
    if not M.rate_ok(key):
        return JSONResponse({"error": "Too many requests"}, status_code=429, headers={"Retry-After": "60"})
    user, reason = await M.authenticate(settings, srv, token)
    if not user:
        M.note_auth_fail(ip)
        return JSONResponse({"error": f"Graylog token refused: {reason}"}, status_code=403)
    if int(request.headers.get("content-length") or 0) > M.MAX_BODY_BYTES:
        return JSONResponse(M._err(None, -32600, "Request too large"), status_code=413)
    raw = await request.body()
    if len(raw) > M.MAX_BODY_BYTES:
        return JSONResponse(M._err(None, -32600, "Request too large"), status_code=413)
    try:
        payload = json.loads(raw or b"null")
    except (ValueError, RecursionError):
        return JSONResponse(M._err(None, -32700, "Parse error"), status_code=400)
    ctx = Ctx(settings=settings, db=request.app.state.db, server=srv, auth=(token, "token"),
              username=user, channel="mcp")
    batch = payload if isinstance(payload, list) else [payload]
    if isinstance(payload, list) and not batch:
        return JSONResponse(M._err(None, -32600, "Invalid Request: empty batch"), status_code=400)
    if len(batch) > M.MAX_BATCH:
        return JSONResponse(M._err(None, -32600, f"Invalid Request: more than {M.MAX_BATCH} messages in a batch"),
                            status_code=400)
    calls = sum(1 for m in batch if isinstance(m, dict) and m.get("method") == "tools/call")
    if calls > 1 and not M.rate_ok(key, cost=calls - 1):   # each tool call counts, not the POST
        return JSONResponse({"error": "Too many requests"}, status_code=429, headers={"Retry-After": "60"})

    async def one(m):
        try:
            return await M.handle(m, ctx, __version__, ip)
        except Exception as e:   # one malformed message must not lose the whole batch's answers
            log.info("MCP message failed", error=str(e))
            return M._err(m.get("id") if isinstance(m, dict) else None, -32603, "Internal error")
    out = [r for r in [await one(m) for m in batch] if r is not None]
    headers = {}
    if any(isinstance(m, dict) and m.get("method") == "initialize" for m in batch):
        headers["Mcp-Session-Id"] = M.new_session_id()
    if not out:
        return Response(status_code=202, headers=headers)
    return JSONResponse(out if isinstance(payload, list) else out[0], headers=headers)


# --- 1.37: charts of an answer -> Graylog dashboard / summary PDF ----------------
# Owner 2026-11-27. Both read glogarch.ai.charts, so their charts agree. The page
# lists the specs, the user picks; Graylog is asked again as the signed-in user.

def _specs_for_message(m: dict) -> list[dict]:
    from glogarch.ai import charts as C
    return C.specs_from_calls(m.get("calls") or [])


def _spec_server(specs: list[dict], fallback: str) -> str | None:
    """The one Graylog server the picked charts came from (None when several)."""
    names = {s.get("server") or fallback for s in specs}
    return names.pop() if len(names) == 1 else None


@router.get("/ai/messages/{mid}/charts")
def ai_message_charts(request: Request, mid: int):
    m = _db(request).ai_get_message(mid, _user(request))
    if not m or m.get("role") != "assistant":
        return JSONResponse({"error": "Message not found"}, status_code=404)
    return {"charts": _specs_for_message(m), "server": m.get("server") or ""}


@router.get("/ai/conversations/{cid}/charts")
def ai_conversation_charts(request: Request, cid: int):
    from glogarch.ai import summary_report as SR
    conv = _db(request).ai_get_conversation(int(cid), _user(request))
    if not conv:
        return JSONResponse({"error": "Conversation not found"}, status_code=404)
    return {"charts": SR.conversation_specs(conv["messages"]), "server": conv.get("server") or ""}


@router.post("/ai/messages/{mid}/graylog-dashboard")
async def ai_graylog_dashboard(request: Request, mid: int):
    """Creates (never changes or deletes) one Graylog dashboard from the picked
    charts of this answer, as the signed-in user's Graylog session."""
    from glogarch.ai import gl_dashboard as D
    from glogarch.web.routes.alerting import _web_url
    settings = _settings(request)
    m = _db(request).ai_get_message(mid, _user(request))
    if not m or m.get("role") != "assistant":
        return JSONResponse({"error": "Message not found"}, status_code=404)
    body = await request.json() or {}
    title = D.clean_title(body.get("title"))
    if not title:
        return JSONResponse({"error": "Give the dashboard a title"}, status_code=400)
    picks = [p for p in (body.get("widgets") or []) if isinstance(p, dict)][:D.MAX_WIDGETS]
    specs = _specs_for_message(m)
    picked = [s for s in specs if s["id"] in {str(p.get("id")) for p in picks}]
    if not picked:
        return JSONResponse({"error": "Pick at least one chart"}, status_code=400)
    try:
        tr = D.timerange_for(str(body.get("range") or ""), str(body.get("from") or ""), str(body.get("to") or ""))
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    name = _spec_server(picked, m.get("server") or "")
    if name is None:
        return JSONResponse({"error": "The picked charts come from different Graylog servers; pick charts of one server"},
                            status_code=400)
    srv = next((s for s in settings.servers if s.name == name), None)   # exact name only
    if srv is None:
        return JSONResponse({"error": f"Graylog server {name} is no longer configured"}, status_code=400)
    ident = gl_identity.get(request.session, srv.name)
    if ident is None:
        return JSONResponse({"error": "Sign in to Graylog to continue", "need_signin": True,
                             "server": srv.name}, status_code=403)
    search, view, notes = D.build(specs, picks, title, tr, str(body.get("description") or ""))
    try:
        vid = await D.create(srv, ident.auth, search, view)
    except Exception as e:
        log.info("Graylog dashboard from an AI answer failed", server=srv.name, error=str(e)[:300])
        _audit(request, "ai_graylog_dashboard_failed",
               f"message={mid} server={srv.name} graylog_user={ident.username} error={sanitize(str(e))[:200]}")
        return JSONResponse({"error": sanitize(str(e))[:400]}, status_code=502)
    n = len(view["state"][search["queries"][0]["id"]]["widgets"])
    _audit(request, "ai_graylog_dashboard_created",
           f"message={mid} server={srv.name} graylog_user={ident.username} dashboard={vid} widgets={n} "
           f"range={body.get('range')} title={title[:80]}")
    return {"id": vid, "url": _web_url(srv.url) + f"/dashboards/{vid}", "widgets": n, "notes": notes}


_SUMMARY_RUNNING: dict[int, str] = {}     # conversation id -> job id (one PDF at a time per conversation)
_SUMMARY_JOBS: dict[str, dict] = {}       # job id -> {user, hist_id, error, done}


@router.post("/ai/conversations/{cid}/summary-pdf")
async def ai_summary_pdf(request: Request, cid: int):
    """Starts a report job: charts re-run, summary text by the model, PDF by the
    report engine. The PDF lands in the report history."""
    import uuid as _uuid
    from datetime import datetime as _dt
    from glogarch.core.models import JobRecord, JobStatus, JobType
    settings = _settings(request)
    db = _db(request)
    user = _user(request)
    if not settings.ai.enabled or settings.ai.llm() is None:
        return JSONResponse({"error": "AI chat is turned off"}, status_code=400)
    conv = db.ai_get_conversation(int(cid), user)
    if not conv:
        return JSONResponse({"error": "Conversation not found"}, status_code=404)
    if not any(m.get("role") == "assistant" for m in conv["messages"]):
        return JSONResponse({"error": "This conversation has no answer yet"}, status_code=400)
    body = await request.json() or {}
    want_llm = str(body.get("llm") or "")
    if want_llm and not any(x.name == want_llm for x in settings.ai.llm_servers):
        return JSONResponse({"error": f"Unknown LLM server {want_llm}"}, status_code=400)
    cfg = settings.ai.llm(want_llm or None)
    why = llm.limits_left(settings.ai, cfg, db, user)
    if why:
        return JSONResponse({"error": why}, status_code=429)
    lang = body.get("lang") if body.get("lang") in _LANGS else "en"
    title = str(body.get("title") or "").strip()[:120]
    ids = body.get("charts")
    ids = [str(x) for x in ids][:50] if isinstance(ids, list) else None
    titles = {str(k): str(v)[:120] for k, v in (body.get("chart_titles") or {}).items()} \
        if isinstance(body.get("chart_titles"), dict) else {}
    style_cfg = None
    if body.get("style") == "@ai":
        style_cfg = dict(settings.ai.summary_style or {})      # the look set in the AI settings
    elif body.get("style"):
        rec = db.get_report(str(body["style"])[:200])
        if not rec:
            return JSONResponse({"error": "Report not found"}, status_code=400)
        try:
            style_cfg = json.loads(rec.get("config_json") or "{}")
        except ValueError:
            style_cfg = {}
    from glogarch.ai import summary_report as SR
    specs = SR.conversation_specs(conv["messages"])
    if ids is not None:
        specs = [s for s in specs if s["id"] in set(ids)]
    name = _spec_server(specs, conv.get("server") or "") if specs else (conv.get("server") or "")
    if name is None:
        return JSONResponse({"error": "The picked charts come from different Graylog servers; pick charts of one server"},
                            status_code=400)
    srv = next((s for s in settings.servers if s.name == name), None) if name else _server(request, None)
    if srv is None:
        return JSONResponse({"error": f"Graylog server {name} is no longer configured"}, status_code=400)
    ident = gl_identity.get(request.session, srv.name)
    if ident is None and specs:
        return JSONResponse({"error": "Sign in to Graylog to continue", "need_signin": True,
                             "server": srv.name}, status_code=403)
    running = _SUMMARY_RUNNING.get(int(cid))
    if running and not (_SUMMARY_JOBS.get(running) or {}).get("done"):
        return JSONResponse({"error": "A summary of this conversation is already being made", "job_id": running},
                            status_code=409)
    job_id = str(_uuid.uuid4())
    db.create_job(JobRecord(id=job_id, job_type=JobType.REPORT, status=JobStatus.RUNNING,
                            source="manual:ai-summary", started_at=_dt.utcnow()))
    _SUMMARY_RUNNING[int(cid)] = job_id
    _SUMMARY_JOBS[job_id] = {"user": user, "cid": int(cid), "hist_id": None, "error": "", "done": False}
    while len(_SUMMARY_JOBS) > 200:
        _SUMMARY_JOBS.pop(next(iter(_SUMMARY_JOBS)))
    ctx = Ctx(settings=settings, db=db, server=srv, auth=ident.auth if ident else ("", ""),
              username=(ident.username if ident else "") or user, channel="chat")
    _audit(request, "ai_summary_pdf", f"conversation={cid} server={srv.name} llm={cfg.name} charts={len(specs)} lang={lang}")

    def _run():
        from glogarch.web.routes.api import _cancel_flags
        st = _SUMMARY_JOBS[job_id]
        try:
            res = asyncio.run(_make_summary_pdf(settings, db, ctx, conv, job_id, lang=lang, cfg=cfg, user=user,
                                                title=title, ids=ids, titles=titles, style_cfg=style_cfg,
                                                cancelled=lambda: bool(_cancel_flags.get(job_id))))
            st["hist_id"] = res["hist_id"]
            st["warning"] = res["text_error"]
            note = f"ai-summary conversation={cid} charts={res['charts']}"
            if res["text_error"]:
                note += f" | ⚠ Summary text missing: {res['text_error']}"
            if res["unverified"]:
                note += f" | {len(res['unverified'])} value(s) not found in the data"
            db.update_job(job_id, status=JobStatus.COMPLETED, completed_at=_dt.utcnow(), progress_pct=100.0,
                          messages_done=res["charts"], messages_total=res["charts"], error_message=note)
        except Exception as e:
            cancelled = bool(_cancel_flags.get(job_id))
            st["error"] = "Cancelled" if cancelled else (sanitize(str(e))[:400] or type(e).__name__)
            log.warning("AI summary PDF failed", conversation=cid, error=st["error"])
            try:
                db.update_job(job_id, status=JobStatus.CANCELLED if cancelled else JobStatus.FAILED,
                              completed_at=_dt.utcnow(), error_message=st["error"])
            except Exception as e2:
                log.warning("AI summary job status write failed", error=str(e2))
        finally:
            st["done"] = True
            _cancel_flags.pop(job_id, None)
            from glogarch.web.routes.api import _job_progress
            _job_progress.pop(job_id, None)

    asyncio.get_running_loop().run_in_executor(None, _run)
    return {"job_id": job_id}


def summary_filename(title: str, conv_id: int, when) -> str:
    """'<title>_<YYYYMMDD-HHMM>.pdf' (owner 2026-11-27: "檔名要含標題"); characters a file system
    refuses become '-', at most 60 characters of title, 'ai-summary-<id>' without one."""
    t_ = re.sub(r'[\\/:*?"<>|\x00-\x1f\x7f]+', "-", title or "").strip(" .-")
    t_ = re.sub(r"\s+", " ", t_)[:60].strip(" .-") or f"ai-summary-{conv_id}"
    return f"{t_}_{when:%Y%m%d-%H%M%S}.pdf"


async def _make_summary_pdf(settings, db, ctx, conv, job_id, *, lang, cfg, user, title, ids, titles, cancelled,
                            style_cfg=None):
    import hashlib
    from datetime import datetime as _dt
    from glogarch.ai import summary_report as SR
    from glogarch.report import builder, renderer
    from glogarch.report.generator import _chown_if_root, _reports_dir

    from glogarch.web.routes.api import _job_progress
    st = _SUMMARY_JOBS.get(job_id) or {}
    now_phase = {"text": "", "waiting": False, "since": time.monotonic()}

    def publish():
        """What the job is doing now, for the dialog (summary-jobs) and the sidebar /
        Job History (the job's live detail). A step that waits for the model carries
        its elapsed time: the bar cannot move while the model writes."""
        text = now_phase["text"]
        if now_phase["waiting"]:
            secs = int(time.monotonic() - now_phase["since"])
            took = f"{secs // 60}m{secs % 60:02d}s" if secs >= 60 else f"{secs}s"
            text = f"{text}; {took} so far"     # "; " = its own segment for the page's translation
        st["detail"] = text
        _job_progress.setdefault(job_id, []).append({"phase": "running", "detail": text})
        del _job_progress[job_id][:-20]

    def phase(text, waiting=False):
        now_phase.update(text=text, waiting=waiting, since=time.monotonic())
        publish()

    async def ticker():
        while True:
            await asyncio.sleep(5)
            if now_phase["waiting"]:
                publish()

    def progress(done, total):
        try:
            db.update_job(job_id, progress_pct=min(95.0, done / max(total, 1) * 95.0),
                          messages_done=done, messages_total=total)
        except Exception as e:
            log.debug("AI summary progress write failed", error=str(e))

    from datetime import datetime as _now
    from urllib.parse import urlparse
    style = SR.style_from_report(style_cfg, server=getattr(ctx.server, "name", ""),
                                 host=urlparse(getattr(ctx.server, "url", "") or "").hostname or "",
                                 made_at=_now.now().astimezone()) if style_cfg else None
    tick = asyncio.create_task(ticker())
    try:
        out = await SR.make_summary(settings, db, ctx, conv, lang=lang, cfg=cfg, username=user, title=title,
                                    chart_ids=ids, chart_titles=titles, progress=progress, cancelled=cancelled,
                                    phase=phase, style=style)
        if cancelled():
            raise RuntimeError("Cancelled")
        phase("Rendering the PDF")
    finally:
        tick.cancel()
    rep, sections = out["report"], out["sections"]
    html = builder.build_html(rep, sections)
    pdf = await renderer.html_to_pdf(html, report_title=rep["title"], header_text=rep["header_text"],
                                     header_logo=rep.get("header_logo_data_uri", ""), brand_color=rep["brand_color"],
                                     watermark=rep.get("watermark"),
                                     toc_titles=[s.get("title") for s in sections if s.get("title")],
                                     generated_at=rep["generated_at"], lang=lang)
    fname = summary_filename(rep.get("title") or "", conv["id"], _dt.now())
    path = _reports_dir(settings) / fname
    path.write_bytes(pdf)
    sha = hashlib.sha256(pdf).hexdigest()
    try:
        path.with_name(fname + ".sha256").write_text(f"{sha}  {fname}\n", encoding="utf-8")
        _chown_if_root(path)
        _chown_if_root(path.with_name(fname + ".sha256"))
    except OSError as e:
        log.warning("AI summary sidecar / ownership", error=str(e))
    hist_id = db.record_report_history("ai-summary", str(path), fname, len(pdf), "completed",
                                       triggered_by=f"ai:{user}", sha256=sha, title=rep.get("title") or "")
    return {"hist_id": hist_id, "charts": len(out["specs"]), "unverified": out["unverified"],
            "text_error": out["text_error"]}


@router.get("/ai/summary-jobs/{job_id}")
def ai_summary_job(request: Request, job_id: str):
    st = _SUMMARY_JOBS.get(job_id)
    if not st or st["user"] != _user(request):
        return JSONResponse({"error": "Not found"}, status_code=404)
    job = _db(request).get_job(job_id)
    return {"done": st["done"], "error": st["error"], "hist_id": st["hist_id"], "warning": st.get("warning", ""),
            "detail": "" if st["done"] else st.get("detail", ""),
            "download": f"/api/reports/history/{st['hist_id']}/download" if st["hist_id"] else "",
            "progress": (job.progress_pct if job else 0) or 0}


# --- 1.37: a conversation saved as an investigation case (owner 2026-11-27) ----------

CASE_NOTE_MAX = 60000        # characters of the conversation note
CASE_BLOCK_MAX = 4000        # a code block longer than this (a whole dashboard page) is left out


def conversation_markdown(conv: dict, lang: str) -> str:
    """Questions, answers and the queries behind them, for a case's timeline. A big code block
    (an HTML dashboard) is replaced by one line saying so: the note is for reading."""
    from glogarch.ai.chat import visible_answer
    words = {"en": ("Question", "Answer", "Queries", "left out: {n} characters of {k}"),
             "zh-TW": ("問題", "回答", "查詢", "已省略：{k} 共 {n} 字"),
             "ja": ("質問", "回答", "クエリ", "省略：{k}（{n} 文字）")}.get(lang) or \
        ("Question", "Answer", "Queries", "left out: {n} characters of {k}")

    def shorten(text: str) -> str:
        def sub(m):
            body = m.group(2)
            if len(body) <= CASE_BLOCK_MAX:
                return m.group(0)
            return f"_({words[3].replace('{n}', f'{len(body):,}').replace('{k}', m.group(1) or 'code')})_"
        return re.sub(r"```([\w-]*)\n(.*?)\n```", sub, text, flags=re.S)

    # the case timeline shows notes as plain text: labels in 【】, no markdown marks
    plain = lambda t_: re.sub(r"\*\*(.+?)\*\*", r"\1", t_)
    out = []
    for m in conv.get("messages") or []:
        if m.get("role") == "user":
            out.append(f"【{words[0]}】\n{str(m.get('content') or '').strip()}")
        elif m.get("role") == "assistant":
            out.append(f"【{words[1]}】\n{plain(shorten(visible_answer(str(m.get('content') or '')).strip()))}")
            qs = [c for c in (m.get("calls") or []) if c.get("ok") and c.get("query") is not None]
            if qs:
                from glogarch.ai.summary_report import localize_times
                lines = [f"- {c.get('name')}: {str(c.get('query') or '*')[:300]}"
                         + (" (" + localize_times(f"{(c.get('range') or {}).get('from', '')}–{(c.get('range') or {}).get('to', '')}") + ")"
                            if c.get("range") else "") for c in qs[:20]]
                out.append(f"【{words[2]}】\n" + "\n".join(lines))
    text = "\n\n".join(out)
    return text if len(text) <= CASE_NOTE_MAX else text[:CASE_NOTE_MAX] + "\n\n…"


@router.post("/ai/conversations/{cid}/to-case")
async def ai_conversation_to_case(request: Request, cid: int):
    """Owner 2026-11-27: "智慧問答 ... 多一個按鈕 轉存為 調查案件". A new case whose timeline holds
    the conversation (questions, answers, queries); audited like a case made on its page."""
    from glogarch.security.detectors import SEVERITIES
    db = _db(request)
    user = _user(request)
    conv = db.ai_get_conversation(int(cid), user)
    if not conv:
        return JSONResponse({"error": "Conversation not found"}, status_code=404)
    if not conv["messages"]:
        return JSONResponse({"error": "This conversation has no answer yet"}, status_code=400)
    body = await request.json() or {}
    title = re.sub(r"[\x00-\x1f\x7f]", " ", str(body.get("title") or conv.get("title") or "")).strip()[:200]
    if not title:
        return JSONResponse({"error": "A case needs a title"}, status_code=400)
    sev = body.get("severity") or "medium"
    if sev not in SEVERITIES:
        return JSONResponse({"error": "Unknown severity"}, status_code=400)
    lang = body.get("lang") if body.get("lang") in _LANGS else "en"
    intro = {"en": "Saved from AI chat conversation #{c} (Graylog server {s}).",
             "zh-TW": "由智慧問答對話 #{c} 轉存（Graylog 伺服器 {s}）。",
             "ja": "AI チャットの会話 #{c} から保存しました（Graylog サーバー {s}）。"}[lang]
    case_id = db.create_security_case(title, sev, intro.replace("{c}", str(cid)).replace("{s}", conv.get("server") or "-"),
                                      user, [])
    db.add_security_case_note(case_id, conversation_markdown(conv, lang), user)
    _audit(request, "ai_conversation_to_case", f"conversation={cid} case={case_id} title={title[:120]}")
    return {"id": case_id, "url": f"/security?case={case_id}"}
