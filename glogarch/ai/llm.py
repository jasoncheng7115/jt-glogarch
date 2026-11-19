# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""OpenAI-compatible chat client for the AI chat.

Measured against the owner's llama.cpp server (2026-11-19): native `tool_calls`
come back with finish_reason "tool_calls"; 343 prompt tokens + one tool call took
10 s. Lessons carried over from jt-waf-mgr / jt-ipam: strip <think> blocks
(reasoning models), accept a tool call written as text (`<tool_call>{...}`), one
retry on a gateway error, never follow redirects, cap the response size.
"""
from __future__ import annotations

import asyncio
import ipaddress
import json
import re
import socket
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx

from glogarch.utils.logging import get_logger
from glogarch.utils.netguard import ssrf_block_reason

log = get_logger("ai.llm")

MAX_RESPONSE_BYTES = 4 * 1024 * 1024
_THINK = re.compile(r"<think>.*?</think>", re.S | re.I)
_TEXT_CALL = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.S)


class LLMError(Exception):
    pass


def host_is_private(url: str) -> bool | None:
    """True when every address the host resolves to is private/loopback,
    False when any is public, None when it cannot be resolved."""
    host = urlparse(url).hostname or ""
    if not host:
        return None
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return None
    addrs = {i[4][0] for i in infos}
    if not addrs:
        return None
    for a in addrs:
        ip = ipaddress.ip_address(a.split("%")[0])
        if not (ip.is_private or ip.is_loopback):
            return False
    return True


def check_url(url: str, allow_external: bool) -> str | None:
    """Why this LLM URL is refused, or None."""
    u = urlparse(url or "")
    if u.scheme not in ("http", "https") or not u.hostname:
        return "LLM URL must be http(s)://host[:port]/v1"
    reason = ssrf_block_reason(url)
    if reason:
        return reason
    priv = host_is_private(url)
    if priv is None:
        return "LLM host could not be resolved"
    if not priv and not allow_external:
        return ("LLM server is outside the private network; log data would leave it. "
                "Turn on 'Allow an external LLM' to use it anyway")
    return None


@dataclass
class Reply:
    content: str = ""
    tool_calls: list[dict] = field(default_factory=list)   # [{id, name, arguments(dict|str)}]
    tokens: int = 0
    finish: str = ""
    model: str = ""


def clean_text(text: str | None) -> str:
    return _THINK.sub("", text or "").strip()


def parse_reply(data: dict) -> Reply:
    ch = (data.get("choices") or [{}])[0]
    msg = ch.get("message") or {}
    rep = Reply(content=clean_text(msg.get("content")), finish=ch.get("finish_reason") or "",
                tokens=int((data.get("usage") or {}).get("total_tokens") or 0),
                model=data.get("model") or "")
    for tc in msg.get("tool_calls") or []:
        fn = tc.get("function") or {}
        rep.tool_calls.append({"id": tc.get("id") or f"call_{len(rep.tool_calls)}",
                               "name": fn.get("name") or "", "arguments": fn.get("arguments") or "{}"})
    if not rep.tool_calls and "<tool_call>" in (msg.get("content") or ""):
        # some local models write the call as text instead of using the field
        for i, m in enumerate(_TEXT_CALL.finditer(msg.get("content") or "")):
            try:
                obj = json.loads(m.group(1))
            except ValueError as e:
                log.debug("Ignoring a text tool call that is not JSON", error=str(e))
                continue
            if isinstance(obj, dict) and obj.get("name"):
                rep.tool_calls.append({"id": f"text_call_{i}", "name": obj["name"],
                                       "arguments": obj.get("arguments") or {}})
        if rep.tool_calls:
            rep.content = clean_text(_TEXT_CALL.sub("", msg.get("content") or ""))
    return rep


def _headers(cfg) -> dict:
    h = {"Content-Type": "application/json", "Accept": "application/json"}
    if cfg.api_key:
        h["Authorization"] = f"Bearer {cfg.api_key}"
    return h


def _scrub(text: str, cfg) -> str:
    return text.replace(cfg.api_key, "***") if cfg.api_key else text


async def chat(cfg, messages: list[dict], tools: list[dict] | None = None,
               max_tokens: int = 2048) -> Reply:
    reason = check_url(cfg.url, cfg.allow_external)
    if reason:
        raise LLMError(reason)
    body = {"model": cfg.model, "messages": messages, "temperature": float(cfg.temperature),
            "max_tokens": int(max_tokens), "stream": False}
    if tools:
        body["tools"] = tools
    url = cfg.url.rstrip("/") + "/chat/completions"
    last = ""
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=float(cfg.timeout_seconds), follow_redirects=False) as c:
                r = await c.post(url, headers=_headers(cfg), json=body)
            if r.status_code in (502, 503, 504) and attempt == 0:
                last = f"HTTP {r.status_code}"
                await asyncio.sleep(5)
                continue
            if r.status_code >= 400:
                raise LLMError(_scrub(f"LLM server answered HTTP {r.status_code}: {r.text[:300]}", cfg))
            if len(r.content) > MAX_RESPONSE_BYTES:
                raise LLMError("LLM response too large")
            return parse_reply(r.json())
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            last = type(e).__name__
            if attempt == 0:
                await asyncio.sleep(5)
                continue
        except httpx.TimeoutException:
            raise LLMError(f"LLM server did not answer within {cfg.timeout_seconds} s")
        except ValueError:
            raise LLMError("LLM server returned something that is not JSON")
    raise LLMError(f"LLM server unreachable ({last})")


async def list_models(cfg) -> list[str]:
    reason = check_url(cfg.url, cfg.allow_external)
    if reason:
        raise LLMError(reason)
    async with httpx.AsyncClient(timeout=20, follow_redirects=False) as c:
        r = await c.get(cfg.url.rstrip("/") + "/models", headers=_headers(cfg))
    if r.status_code >= 400:
        raise LLMError(f"LLM server answered HTTP {r.status_code} on /models")
    return [m.get("id") for m in (r.json().get("data") or []) if m.get("id")]


def budget_left(cfg, usage: dict) -> str | None:
    """Why the token budget refuses another call, or None."""
    if cfg.daily_tokens and usage["day"] >= cfg.daily_tokens:
        return f"Daily AI token budget used up ({usage['day']:,} of {cfg.daily_tokens:,})"
    if cfg.monthly_tokens and usage["month"] >= cfg.monthly_tokens:
        return f"Monthly AI token budget used up ({usage['month']:,} of {cfg.monthly_tokens:,})"
    return None
