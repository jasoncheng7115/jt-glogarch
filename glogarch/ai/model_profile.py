# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""How much the connected model can take (owner 2026-11-26: "我們程式要同時考慮當時接取的
llm 與模型能力").

The context window decides how much of a tool result, of the conversation and
of the tool list goes into one request (chat.py). Asked from the server itself:
  * llama.cpp: GET <root>/props -> default_generation_settings.n_ctx (per slot)
  * vLLM: GET <url>/models -> data[].max_model_len
  * LM Studio: GET <root>/api/v0/models/<model> -> loaded_context_length / max_context_length
  * Ollama: GET <root>/api/ps -> models[].context_length of the loaded model;
    else POST <root>/api/show -> num_ctx in parameters; else Ollama's default
  * Claude API: models.retrieve(model).max_input_tokens
`context_tokens` on the server entry overrides all of it. Read-only GETs to the
configured server, short timeout, cached 10 minutes; unknown -> UNKNOWN_CONTEXT.
"""
from __future__ import annotations

import re
import time

import httpx

from glogarch.utils.logging import get_logger

log = get_logger("ai.profile")

UNKNOWN_CONTEXT = 32768
OLLAMA_DEFAULT_CONTEXT = 4096
CACHE_SEC = 600
PROBE_TIMEOUT = 5.0
MAX_PROBE_BYTES = 2 * 1024 * 1024

_cache: dict[tuple, tuple[float, dict]] = {}


def _root(url: str) -> str:
    u = (url or "").rstrip("/")
    return u[:-3] if u.endswith("/v1") else u


async def _get(c: httpx.AsyncClient, url: str, headers: dict) -> dict | None:
    try:
        r = await c.get(url, headers=headers)
    except httpx.HTTPError:
        return None
    if r.status_code != 200 or len(r.content) > MAX_PROBE_BYTES:
        return None
    try:
        d = r.json()
    except ValueError:
        return None
    return d if isinstance(d, dict) else None


def _int(v) -> int | None:
    try:
        n = int(v)
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


async def _probe_openai(cfg) -> tuple[int | None, str]:
    from glogarch.ai.llm import _headers
    h = _headers(cfg)
    root = _root(cfg.url)
    async with httpx.AsyncClient(timeout=PROBE_TIMEOUT, follow_redirects=False) as c:
        props = await _get(c, root + "/props", h)
        if props:
            n = _int((props.get("default_generation_settings") or {}).get("n_ctx")) or _int(props.get("n_ctx"))
            if n:
                return n, "llama.cpp /props"
        models = await _get(c, cfg.url.rstrip("/") + "/models", h)
        for m in (models or {}).get("data") or []:
            if isinstance(m, dict) and (m.get("id") == cfg.model or not cfg.model):
                n = _int(m.get("max_model_len")) or _int(m.get("context_length")) or _int(m.get("context_window"))
                if n:
                    return n, "/v1/models"
        lms = await _get(c, f"{root}/api/v0/models/{cfg.model}", h) if cfg.model else None
        if lms:
            n = _int(lms.get("loaded_context_length")) or _int(lms.get("max_context_length"))
            if n:
                return n, "LM Studio /api/v0/models"
        ps = await _get(c, root + "/api/ps", h)
        if ps is not None and isinstance(ps.get("models"), list):
            for m in ps["models"]:
                if isinstance(m, dict) and (m.get("name") == cfg.model or m.get("model") == cfg.model):
                    n = _int(m.get("context_length"))
                    if n:
                        return n, "Ollama /api/ps"
            try:
                r = await c.post(root + "/api/show", headers=h, json={"model": cfg.model})
                show = r.json() if r.status_code == 200 and len(r.content) < MAX_PROBE_BYTES else {}
            except (httpx.HTTPError, ValueError):
                show = {}
            m = re.search(r"(?m)^num_ctx\s+(\d+)", str((show or {}).get("parameters") or ""))
            if m:
                return int(m.group(1)), "Ollama num_ctx"
            return OLLAMA_DEFAULT_CONTEXT, "Ollama default"
    return None, ""


async def profile(cfg) -> dict:
    """{context: int, source: str, known: bool} for one LLM server entry."""
    if getattr(cfg, "context_tokens", 0):
        return {"context": int(cfg.context_tokens), "source": "set", "known": True}
    key = (getattr(cfg, "kind", "openai"), cfg.url, cfg.model)
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_SEC:
        return hit[1]
    n, src = None, ""
    try:
        if getattr(cfg, "kind", "openai") == "anthropic":
            from glogarch.ai import claude_api
            n = await claude_api.context_tokens(cfg)
            src = "Claude models API" if n else ""
        else:
            from glogarch.ai.llm import check_url
            if not check_url(cfg.url, cfg.allow_external):
                n, src = await _probe_openai(cfg)
    except Exception as e:   # a probe never stops a question
        log.info("Model context not read", error=str(e)[:200])
    out = ({"context": int(n), "source": src, "known": True} if n
           else {"context": UNKNOWN_CONTEXT, "source": "unknown", "known": False})
    _cache[key] = (time.time(), out)
    return out


def estimate_tokens(text: str) -> int:
    """Rough tokens of a text: ~4 ASCII characters a token, ~1 token a CJK character
    (Qwen / Claude tokenizers measure close to that on mixed log JSON)."""
    if not text:
        return 0
    ascii_n = sum(1 for ch in text if ord(ch) < 128)
    return ascii_n // 4 + (len(text) - ascii_n) + 1


def chars_for_tokens(tokens: int) -> int:
    """Characters of tool-result JSON that fit `tokens` (mostly ASCII, some CJK)."""
    return int(tokens * 3)
