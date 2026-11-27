# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""The Claude API as an LLM server (1.36, owner 2026-11-26: "也要能支援 claude api").

Official `anthropic` SDK, imported only when a Claude server is used: a site
without the package keeps every other LLM working and gets a plain message.

The chat loop speaks the OpenAI message shape (llm.py); this module converts it:
  * system messages -> the top-level `system`;
  * an assistant turn -> text + tool_use blocks, or, when the turn came from
    Claude, its own content exactly as returned (`_claude_content`): thinking
    blocks must go back unchanged and the history must stay append-only;
  * tool results -> tool_result blocks in ONE user message per round.

Request choices (the Claude API skill's defaults): streaming; adaptive thinking
with summarized display (the page shows the reasoning), sent again without it
when a model refuses the field; no temperature (the API refuses sampling
settings); `effort` only when the server entry sets one; automatic prompt
caching; server-side refusal fallback (`fallbacks: "default"`) on the models
that take it; eager input streaming on our tools, so a tool input is checked
here (stop_reason max_tokens / refusal, input not an object) before it runs.
"""
from __future__ import annotations

import json
from typing import Any

from glogarch.utils.logging import get_logger

log = get_logger("ai.claude")

DEFAULT_URL = "https://api.anthropic.com"
DEFAULT_MODEL = "claude-opus-5-5"
# server-side refusal fallback, Claude API only (not Haiku: it has none)
FALLBACK_MODELS = ("claude-opus-5-5", "claude-opus-5", "claude-fable-5-1", "claude-fable-5", "claude-sonnet-5-5")
FALLBACK_BETA = "server-side-fallback-2026-07-01"
MIN_MAX_TOKENS = 16000          # thinking counts against max_tokens: never give a thinking model less
MAX_MAX_TOKENS = 64000

# models that refused a field once: not sent to them again (this process)
_NO_THINKING: set[str] = set()
_NO_FALLBACK: set[str] = set()


def sdk():
    """The anthropic package, or LLMError saying how to get it."""
    from glogarch.ai.llm import LLMError
    try:
        import anthropic
    except ImportError as e:
        raise LLMError("The Claude API needs the Python package 'anthropic' (pip install 'anthropic>=2.14,<3'), "
                       f"not installed here ({e})")
    return anthropic


def _client(cfg):
    a = sdk()
    base = (cfg.url or DEFAULT_URL).rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]        # the SDK adds /v1 itself
    return a.AsyncAnthropic(api_key=cfg.api_key or "missing", base_url=base,
                            timeout=float(cfg.timeout_seconds), max_retries=2)


def is_first_party(cfg) -> bool:
    return (cfg.url or DEFAULT_URL).rstrip("/").removesuffix("/v1") == DEFAULT_URL


def convert_tools(tools: list[dict] | None) -> list[dict]:
    out = []
    for t in tools or []:
        f = t.get("function") or {}
        schema = f.get("parameters") or {"type": "object", "properties": {}}
        out.append({"name": f.get("name", ""), "description": (f.get("description") or "")[:1024],
                    "input_schema": schema, "eager_input_streaming": True})
    return out


def convert_messages(messages: list[dict]) -> tuple[str, list[dict]]:
    system: list[str] = []
    out: list[dict] = []
    for m in messages:
        role = m.get("role")
        if role == "system":
            system.append(str(m.get("content") or ""))
        elif role == "assistant":
            raw = m.get("_claude_content")
            if raw:
                out.append({"role": "assistant", "content": raw})
                continue
            blocks: list[dict] = []
            if m.get("content"):
                blocks.append({"type": "text", "text": str(m["content"])})
            for tc in m.get("tool_calls") or []:
                fn = tc.get("function") or {}
                args = fn.get("arguments")
                if isinstance(args, str):
                    try:
                        args = json.loads(args or "{}")
                    except ValueError:
                        args = {}
                blocks.append({"type": "tool_use", "id": tc.get("id") or "call", "name": fn.get("name") or "",
                               "input": args if isinstance(args, dict) else {}})
            out.append({"role": "assistant", "content": blocks or [{"type": "text", "text": "-"}]})
        elif role == "tool":
            block = {"type": "tool_result", "tool_use_id": m.get("tool_call_id") or "call",
                     "content": str(m.get("content") or "")}
            if m.get("_is_error"):
                block["is_error"] = True
            last = out[-1] if out else None
            if (last and last["role"] == "user" and isinstance(last["content"], list)
                    and all(isinstance(b, dict) and b.get("type") == "tool_result" for b in last["content"])):
                last["content"].append(block)     # every result of a round in one user message
            else:
                out.append({"role": "user", "content": [block]})
        else:
            out.append({"role": "user", "content": str(m.get("content") or "")})
    return "\n\n".join(s for s in system if s), out


def _block_dicts(content) -> list[dict]:
    """The response content as plain dicts, exactly as the API sent it (to replay)."""
    out = []
    for b in content or []:
        d = b.model_dump(exclude_none=True) if hasattr(b, "model_dump") else dict(b)
        out.append(d)
    return out


def _params(cfg, messages, tools, max_tokens, no_tools, response_format):
    system, msgs = convert_messages(messages)
    p: dict[str, Any] = {"model": cfg.model or DEFAULT_MODEL,
                         "max_tokens": max(MIN_MAX_TOKENS, min(int(max_tokens or 0), MAX_MAX_TOKENS)),
                         "messages": msgs, "cache_control": {"type": "ephemeral"}}
    if system:
        p["system"] = system
    ctools = convert_tools(tools)
    if ctools:
        # a history with tool_use blocks needs the tools declared even when none may be called
        p["tools"] = ctools
        if no_tools:
            p["tool_choice"] = {"type": "none"}
    if p["model"] not in _NO_THINKING:
        p["thinking"] = {"type": "adaptive", "display": "summarized"}
    oc: dict[str, Any] = {}
    if getattr(cfg, "effort", ""):
        oc["effort"] = cfg.effort
    if response_format and response_format.get("type") == "json_schema":
        schema = (response_format.get("json_schema") or {}).get("schema")
        if schema:
            oc["format"] = {"type": "json_schema", "schema": schema}
    if oc:
        p["output_config"] = oc
    if p["model"] in FALLBACK_MODELS and is_first_party(cfg) and p["model"] not in _NO_FALLBACK:
        p["extra_headers"] = {"anthropic-beta": FALLBACK_BETA}
        p["extra_body"] = {"fallbacks": "default"}
    return p


async def chat(cfg, messages: list[dict], tools: list[dict] | None = None, max_tokens: int = 2048, *,
               no_tools: bool = False, response_format: dict | None = None,
               on_text=None, on_reasoning=None, on_silent=None):
    """One Claude request, streamed. Returns llm.Reply (raw = the content to replay)."""
    from glogarch.ai.llm import LLMError, LLMRefused, Reply
    a = sdk()
    p = _params(cfg, messages, tools, max_tokens, no_tools, response_format)
    for attempt in range(4):
        try:
            return await _stream(cfg, p, on_text, on_reasoning, on_silent)
        except a.BadRequestError as e:
            msg = str(getattr(e, "message", "") or e)
            low = msg.lower()
            if "thinking" in p and "thinking" in low:
                _NO_THINKING.add(p["model"])
                p.pop("thinking")
                continue
            if "extra_body" in p and ("fallback" in low or "beta" in low):
                _NO_FALLBACK.add(p["model"])
                p.pop("extra_body")
                p.pop("extra_headers", None)
                continue
            raise LLMRefused(f"Claude API refused the request: {msg[:300]}")
        except ValueError as e:
            # eager input streaming: a tool input the SDK could not parse at all;
            # there is no tool_use id to answer, so the request is sent again (once)
            if attempt == 0:
                log.info("Claude tool input was not JSON; asking again", error=str(e)[:200])
                continue
            raise LLMError(f"Claude sent a tool call that is not JSON ({str(e)[:200]})")
        except a.AuthenticationError:
            raise LLMError("Claude API refused the API key (HTTP 401)")
        except a.PermissionDeniedError as e:
            raise LLMError(f"Claude API: permission denied ({str(getattr(e, 'message', e))[:200]})")
        except a.NotFoundError:
            raise LLMError(f"Claude API: model '{p['model']}' not found")
        except a.RateLimitError:
            raise LLMError("Claude API rate limit reached; try again in a minute")
        except a.APITimeoutError:
            raise LLMError(f"Claude API did not answer within {cfg.timeout_seconds} s")
        except a.APIConnectionError as e:
            raise LLMError(f"Claude API unreachable ({type(e).__name__})")
        except a.APIStatusError as e:
            raise LLMError(f"Claude API answered HTTP {e.status_code}: {str(getattr(e, 'message', e))[:300]}")
    return Reply()


async def _stream(cfg, p, on_text, on_reasoning, on_silent):
    from glogarch.ai.llm import Reply
    client = _client(cfg)
    text, reasoning = "", ""
    tool_started = False
    got = False
    try:
        async with client.messages.stream(**p) as stream:
            async for ev in stream:
                if not got:
                    got = True
                    if on_silent is not None:
                        await on_silent(False)
                t = getattr(ev, "type", "")
                if t == "content_block_start" and getattr(ev.content_block, "type", "") == "tool_use":
                    tool_started = True
                elif t == "content_block_delta":
                    d = ev.delta
                    if d.type == "thinking_delta" and on_reasoning is not None:
                        reasoning += d.thinking or ""
                        await on_reasoning(reasoning)
                    elif d.type == "text_delta":
                        text += d.text or ""
                        if on_text is not None and not tool_started:
                            await on_text(text)
            final = await stream.get_final_message()
    finally:
        await client.close()
    rep = Reply(model=final.model or p["model"])
    u = final.usage
    rep.tokens = int((u.input_tokens or 0) + (u.output_tokens or 0)
                     + (getattr(u, "cache_read_input_tokens", 0) or 0)
                     + (getattr(u, "cache_creation_input_tokens", 0) or 0))
    stop = final.stop_reason or ""
    rep.finish = {"end_turn": "stop", "max_tokens": "length", "tool_use": "tool_calls"}.get(stop, stop)
    texts, calls = [], []
    for b in final.content:
        if b.type == "text":
            texts.append(b.text)
        elif b.type == "tool_use":
            calls.append({"id": b.id, "name": b.name, "arguments": b.input})
    rep.content = "".join(texts).strip()
    if stop == "refusal":
        det = getattr(final, "stop_details", None)
        rep.refusal = str(getattr(det, "category", "") or "unspecified")
        return rep            # never run a refused turn's tools
    if stop == "max_tokens" and calls:
        return rep            # a cut-off tool input parses as a valid partial object: not run
    bad = [c for c in calls if not isinstance(c["arguments"], dict)]
    if bad:
        calls = [c for c in calls if isinstance(c["arguments"], dict)]
        rep.bad_calls = [{"id": c["id"], "name": c["name"], "raw": json.dumps(c["arguments"], default=str)[:500]}
                         for c in bad]
    rep.tool_calls = calls
    rep.raw = _block_dicts(final.content)
    return rep


async def list_models(cfg) -> list[str]:
    from glogarch.ai.llm import LLMError
    a = sdk()
    client = _client(cfg)
    try:
        out = []
        async for m in client.models.list(limit=100):
            out.append(m.id)
        return out
    except a.AuthenticationError:
        raise LLMError("Claude API refused the API key (HTTP 401)")
    except a.APIConnectionError as e:
        raise LLMError(f"Claude API unreachable ({type(e).__name__})")
    except a.APIStatusError as e:
        raise LLMError(f"Claude API answered HTTP {e.status_code} on /v1/models")
    finally:
        await client.close()


async def context_tokens(cfg) -> int | None:
    """The model's context window (max_input_tokens on the Models API)."""
    a = sdk()
    client = _client(cfg)
    try:
        m = await client.models.retrieve(cfg.model or DEFAULT_MODEL)
        n = getattr(m, "max_input_tokens", None)
        return int(n) if n else None
    except (a.APIError, ValueError) as e:
        log.info("Claude model context not read", error=str(e)[:200])
        return None
    finally:
        await client.close()
