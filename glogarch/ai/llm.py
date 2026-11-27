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
import time
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


class LLMLoop(LLMError):
    """The reply went round in circles (loopguard); raised from a stream callback
    so the request stops at once (closing the stream frees the server's slot)."""

    def __init__(self, kind: str, why: str, partial: str = ""):
        super().__init__(f"model stuck in a loop ({kind}): {why}")
        self.kind, self.why, self.partial = kind, why, partial


def is_claude(cfg) -> bool:
    return getattr(cfg, "kind", "openai") == "anthropic"


def plain_messages(messages: list[dict]) -> list[dict]:
    """The messages without our private keys (`_claude_content`, `_is_error`):
    an OpenAI-compatible server must never see them."""
    return [{k: v for k, v in m.items() if not k.startswith("_")} for m in messages]


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
    raw: list | None = None        # Claude: the assistant content to send back unchanged
    refusal: str = ""              # Claude: the refusal category when stop_reason is "refusal"
    bad_calls: list = field(default_factory=list)   # tool calls whose input was not an object


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


class LLMRefused(LLMError):
    """HTTP 400 from the server: the request itself was not accepted (e.g. a
    response_format it does not support), so a caller may retry without it."""


async def chat(cfg, messages: list[dict], tools: list[dict] | None = None,
               max_tokens: int = 2048, response_format: dict | None = None, no_tools: bool = False) -> Reply:
    reason = check_url(cfg.url or ("https://api.anthropic.com" if is_claude(cfg) else ""), cfg.allow_external)
    if reason:
        raise LLMError(reason)
    if is_claude(cfg):
        from glogarch.ai import claude_api
        return await claude_api.chat(cfg, messages, tools, max_tokens, no_tools=no_tools,
                                     response_format=response_format)
    if no_tools:
        tools = None
    body = {"model": cfg.model, "messages": plain_messages(messages), "temperature": float(cfg.temperature),
            "max_tokens": int(max_tokens), "stream": False}
    if tools:
        body["tools"] = tools
    if response_format:
        body["response_format"] = response_format
    url = cfg.url.rstrip("/") + "/chat/completions"
    last = ""
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=float(cfg.timeout_seconds), follow_redirects=False) as c:
                r = await c.post(url, headers=_headers(cfg), json=body)
            if r.status_code in (502, 503, 504) and attempt == 0 and "structured_output_failed" not in r.text:
                last = f"HTTP {r.status_code}"
                await asyncio.sleep(5)
                continue
            if r.status_code == 400:
                raise LLMRefused(_scrub(f"LLM server answered HTTP 400: {r.text[:300]}", cfg))
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


# URLs whose server refused a streamed request: they get the plain one from then on
_NO_STREAM: set[str] = set()


def live_text(text: str) -> str:
    """What of a reply being streamed can be shown yet: finished <think> blocks
    removed, and nothing from an unfinished one or a text tool call on."""
    t = _THINK.sub("", text or "")
    for mark in ("<think>", "<tool_call>"):
        i = t.lower().find(mark)
        if i >= 0:
            t = t[:i]
    return t.lstrip()


def live_reasoning(text: str) -> str:
    """The reasoning in the last <think> block of a streamed reply, finished or not
    (servers that put the reasoning in content instead of reasoning_content)."""
    low = (text or "").lower()
    i = low.rfind("<think>")
    if i < 0:
        return ""
    j = low.find("</think>", i)
    return text[i + len("<think>"):j if j >= 0 else None].strip()


REASONING_EVERY_SEC = 0.15   # at most this often to the page; the last piece is always sent
# No streamed chunk at all for this long = the server has not started on this request
# (owner 2026-11-24, "卡很久": the one-slot llama.cpp sat 9 minutes on another
# client's 84K-token prompt and the page said "thinking" the whole time).
SILENT_SEC = 60


def _estimate_tokens(messages: list[dict], out: str) -> int:
    # a server that sends no usage in a stream: ~4 characters a token, so the budget still counts
    return (len(json.dumps(messages, ensure_ascii=False)) + len(out)) // 4 + 1


async def chat_stream(cfg, messages: list[dict], tools: list[dict] | None = None,
                      max_tokens: int = 2048, on_text=None, on_reasoning=None, on_silent=None,
                      no_tools: bool = False) -> Reply:
    """chat() with the reply streamed: on_text(text) is awaited with the text so far
    (live_text) as it grows, on_reasoning(text) with the model's reasoning so far
    (reasoning_content / reasoning, or an unfinished <think> block) - owner
    2026-11-23: text the model writes must show at once, its thinking too. Falls back to chat() when the server refuses a
    streamed request (HTTP 400) or does not stream; measured on the owner's
    llama.cpp (2026-11-21): tool-call deltas by index, reasoning_content apart,
    usage in the last chunk with stream_options.include_usage.
    on_silent(True) is awaited when SILENT_SEC pass with no streamed chunk (the
    server is busy elsewhere or still reading a long prompt), on_silent(False) at
    the first chunk after that; never for a plain request (nothing to measure)."""
    reason = check_url(cfg.url or ("https://api.anthropic.com" if is_claude(cfg) else ""), cfg.allow_external)
    if reason:
        raise LLMError(reason)
    if is_claude(cfg):
        from glogarch.ai import claude_api
        return await claude_api.chat(cfg, messages, tools, max_tokens, no_tools=no_tools,
                                     on_text=on_text, on_reasoning=on_reasoning, on_silent=on_silent)
    if no_tools:
        tools = None
    if on_text is None or cfg.url in _NO_STREAM:
        return await chat(cfg, messages, tools, max_tokens=max_tokens)
    body = {"model": cfg.model, "messages": plain_messages(messages), "temperature": float(cfg.temperature),
            "max_tokens": int(max_tokens), "stream": True, "stream_options": {"include_usage": True}}
    if tools:
        body["tools"] = tools
    url = cfg.url.rstrip("/") + "/chat/completions"
    hdrs = {**_headers(cfg), "Accept": "text/event-stream"}
    quiet = {"got": False, "fired": False}

    async def watch():
        await asyncio.sleep(SILENT_SEC)
        if not quiet["got"]:
            quiet["fired"] = True
            try:
                await on_silent(True)
            except Exception as e:  # a progress note must never fail the request
                log.warning("LLM wait notice failed", error=str(e))

    watcher = asyncio.create_task(watch()) if on_silent is not None else None
    try:
        return await _stream_attempts(cfg, messages, url, hdrs, body, tools, max_tokens,
                                      on_text, on_reasoning, on_silent, quiet)
    finally:
        if watcher:
            watcher.cancel()


async def _stream_attempts(cfg, messages, url, hdrs, body, tools, max_tokens,
                           on_text, on_reasoning, on_silent, quiet) -> Reply:
    last = ""
    for attempt in range(2):
        content, calls, size = "", {}, 0
        rep = Reply()
        try:
            async with httpx.AsyncClient(timeout=float(cfg.timeout_seconds), follow_redirects=False) as c:
                async with c.stream("POST", url, headers=hdrs, json=body) as r:
                    if r.status_code in (502, 503, 504) and attempt == 0:
                        last = f"HTTP {r.status_code}"
                        await r.aread()
                        await asyncio.sleep(5)
                        continue
                    if r.status_code == 400:
                        text = (await r.aread()).decode("utf-8", "replace")
                        # the same request plain: if that is accepted, streaming was the problem and
                        # this server gets plain requests from now on; if not (e.g. the context is too
                        # long), its own error is raised and streaming stays on
                        rep_plain = await chat(cfg, messages, tools, max_tokens=max_tokens)
                        log.info("LLM server refused a streamed request; using plain requests",
                                 error=_scrub(text[:200], cfg))
                        _NO_STREAM.add(cfg.url)
                        return rep_plain
                    if r.status_code >= 400:
                        text = (await r.aread()).decode("utf-8", "replace")
                        raise LLMError(_scrub(f"LLM server answered HTTP {r.status_code}: {text[:300]}", cfg))
                    if "text/event-stream" not in r.headers.get("content-type", ""):
                        raw = await r.aread()      # a server that ignored stream: true
                        if len(raw) > MAX_RESPONSE_BYTES:
                            raise LLMError("LLM response too large")
                        return parse_reply(json.loads(raw))
                    shown = ""
                    reasoning, r_sent, r_at = "", "", 0.0

                    async def think(force: bool = False):
                        nonlocal r_sent, r_at
                        now_r = reasoning + live_reasoning(content)
                        if on_reasoning is None or now_r == r_sent or not now_r:
                            return
                        t_now = time.monotonic()
                        if force or t_now - r_at >= REASONING_EVERY_SEC:
                            r_sent, r_at = now_r, t_now
                            await on_reasoning(now_r)

                    async for line in r.aiter_lines():
                        size += len(line)
                        if size > MAX_RESPONSE_BYTES:
                            raise LLMError("LLM response too large")
                        if not line.startswith("data:"):
                            continue
                        if not quiet["got"]:
                            quiet["got"] = True
                            if quiet["fired"] and on_silent is not None:
                                await on_silent(False)
                        data = line[5:].strip()
                        if data == "[DONE]":
                            break
                        try:
                            obj = json.loads(data)
                        except ValueError as e:     # one bad chunk: skip it, the rest still counts
                            log.debug("Skipping a streamed chunk that is not JSON", error=str(e))
                            continue
                        if obj.get("error"):     # an error sent inside the stream
                            err = obj["error"]
                            msg = err.get("message") if isinstance(err, dict) else err
                            raise LLMError(_scrub(f"LLM server error: {str(msg)[:300]}", cfg))
                        if obj.get("usage"):
                            rep.tokens = int(obj["usage"].get("total_tokens") or 0)
                        rep.model = obj.get("model") or rep.model
                        for ch in obj.get("choices") or []:
                            d = ch.get("delta") or {}
                            if ch.get("finish_reason"):
                                rep.finish = ch["finish_reason"]
                            for tc in d.get("tool_calls") or []:
                                k = tc.get("index")
                                if not isinstance(k, int):
                                    # no index: a fragment with an id starts a call, one without
                                    # continues the last
                                    k = len(calls) if (tc.get("id") or not calls) else max(calls)
                                cur = calls.setdefault(k, {"id": "", "name": "", "arguments": ""})
                                fn = tc.get("function") or {}
                                cur["id"] = tc.get("id") or cur["id"]
                                name = fn.get("name") or ""
                                if name and name != cur["name"]:   # some servers repeat the whole name
                                    cur["name"] += name
                                cur["arguments"] += fn.get("arguments") or ""
                            r_piece = d.get("reasoning_content") or d.get("reasoning")
                            if isinstance(r_piece, str) and r_piece:
                                reasoning += r_piece
                                await think()
                            if d.get("content"):
                                content += d["content"]
                                await think(force=bool(live_text(content)))   # the answer starts: last of the thinking
                                now = live_text(content)
                                if now != shown and not calls:
                                    shown = now
                                    await on_text(now)
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            last = type(e).__name__
            if attempt == 0:
                await asyncio.sleep(5)
                continue
            break
        except httpx.TimeoutException:
            raise LLMError(f"LLM server did not answer within {cfg.timeout_seconds} s")
        except httpx.HTTPError as e:     # the connection dropped mid-reply
            raise LLMError(f"LLM connection failed ({type(e).__name__})")
        except ValueError:
            raise LLMError("LLM server returned something that is not JSON")
        # the same shape a plain reply has, then the same parsing (think blocks, text tool calls)
        msg = {"content": content, "tool_calls": [
            {"id": v["id"] or f"call_{k}", "function": {"name": v["name"], "arguments": v["arguments"] or "{}"}}
            for k, v in sorted(calls.items())]}
        out = parse_reply({"choices": [{"message": msg, "finish_reason": rep.finish}],
                           "usage": {"total_tokens": rep.tokens or _estimate_tokens(messages, content)},
                           "model": rep.model})
        return out
    raise LLMError(f"LLM server unreachable ({last})")


async def list_models(cfg) -> list[str]:
    reason = check_url(cfg.url or ("https://api.anthropic.com" if is_claude(cfg) else ""), cfg.allow_external)
    if reason:
        raise LLMError(reason)
    if is_claude(cfg):
        from glogarch.ai import claude_api
        return await claude_api.list_models(cfg)
    async with httpx.AsyncClient(timeout=20, follow_redirects=False) as c:
        r = await c.get(cfg.url.rstrip("/") + "/models", headers=_headers(cfg))
    if r.status_code >= 400:
        raise LLMError(f"LLM server answered HTTP {r.status_code} on /models")
    return [m.get("id") for m in (r.json().get("data") or []) if m.get("id")]


def limits_left(ai, server, db, username: str = "") -> str | None:
    """Why another request is refused, or None: the site's limits (every user and
    server, as before 1.36), then the LLM server's own, then the user's."""
    why = budget_left(ai, db.ai_usage())
    if why:
        return why
    if server is not None and (server.daily_tokens or server.monthly_tokens):
        u = db.ai_usage(llm=server.name)
        if server.daily_tokens and u["day"] >= server.daily_tokens:
            return f"Daily token limit of LLM server {server.name} used up ({u['day']:,} of {server.daily_tokens:,})"
        if server.monthly_tokens and u["month"] >= server.monthly_tokens:
            return (f"Monthly token limit of LLM server {server.name} used up "
                    f"({u['month']:,} of {server.monthly_tokens:,})")
    if username and (ai.user_daily_tokens or ai.user_monthly_tokens):
        u = db.ai_usage(username=username)
        if ai.user_daily_tokens and u["day"] >= ai.user_daily_tokens:
            return f"Your daily AI token limit is used up ({u['day']:,} of {ai.user_daily_tokens:,})"
        if ai.user_monthly_tokens and u["month"] >= ai.user_monthly_tokens:
            return f"Your monthly AI token limit is used up ({u['month']:,} of {ai.user_monthly_tokens:,})"
    return None


def budget_left(cfg, usage: dict) -> str | None:
    """Why the token budget refuses another call, or None."""
    if cfg.daily_tokens and usage["day"] >= cfg.daily_tokens:
        return f"Daily AI token budget used up ({usage['day']:,} of {cfg.daily_tokens:,})"
    if cfg.monthly_tokens and usage["month"] >= cfg.monthly_tokens:
        return f"Monthly AI token budget used up ({usage['month']:,} of {cfg.monthly_tokens:,})"
    return None
