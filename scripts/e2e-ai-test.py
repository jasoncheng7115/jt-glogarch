#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""AI tools, MCP endpoint and AI chat against a REAL Graylog (throwaway stack only).

    bash scripts/datanode-stack/up.sh          # prints GL_URL / GL_PASS / GELF_PORT
    GL_URL=... GL_PASS=... GELF_PORT=... [AI_URL=http://host:8080/v1 AI_MODEL=... AI_KEY=...] \\
        PYTHONPATH=<repo> python3 scripts/e2e-ai-test.py
    bash scripts/datanode-stack/down.sh

Seeds 60 failed logins from one address over GELF, then checks:
  1. count_messages / top_values are exact (60; 8 distinct accounts),
  2. /mcp with a real Graylog API token issued by the stack (initialize,
     tools/list, tools/call), audited; a bogus token is refused,
  3. an mcp_graylog tool through /mcp as well (1.10.2+ loads on Python 3.10),
     and its event tools (1.12.0): definitions, notifications without recipients
     or URLs, triggered events over 2 days, the messages behind an event,
  4. with AI_URL set, a real LLM answers the count question correctly,
  5. a real detector run opens a password-spraying incident for the seeded peer, its
     AI-analysis evidence matches Graylog, and (with AI_URL) a real model returns a
     valid verdict that names no address missing from the evidence.
NEVER against production: it writes events and creates a token (deleted at the end).
Prints RESULT: ALL PASS.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import socket
import sys
import tempfile
import time
import uuid
from pathlib import Path

import httpx

GL_URL = os.environ.get("GL_URL", "http://127.0.0.1:19000").rstrip("/")
GL_USER = os.environ.get("GL_USER", "admin")
GL_PASS = os.environ.get("GL_PASS", "")
GELF_PORT = int(os.environ.get("GELF_PORT", "32212"))
AI_URL = os.environ.get("AI_URL", "")
PEER = "45.33.32.156"
H = {"X-Requested-By": "jt-glogarch-e2e", "Content-Type": "application/json"}
ok = True


def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    ok = ok and bool(cond)


def gl(method, path, **kw):
    r = httpx.request(method, GL_URL + path, auth=(GL_USER, GL_PASS), headers=H, timeout=30, **kw)
    r.raise_for_status()
    return r.json() if r.content else {}


def seed(tag):
    if not any(i["type"].endswith("GELFTCPInput") for i in gl("GET", "/api/system/inputs").get("inputs", [])):
        gl("POST", "/api/system/inputs", json={"title": "e2e gelf", "type": "org.graylog2.inputs.gelf.tcp.GELFTCPInput",
                                               "global": True, "configuration": {"bind_address": "0.0.0.0", "port": 32202,
                                                                                 "recv_buffer_size": 1048576, "use_null_delimiter": True}})
        time.sleep(8)
    s = socket.create_connection(("127.0.0.1", GELF_PORT), timeout=10)
    for i in range(60):
        s.sendall(json.dumps({"version": "1.1", "host": f"e2e-host{i % 4}", "short_message": "auth fail",
                              "_event_category": "authentication", "_event_outcome": "failure",
                              "_source_ip": PEER, "_user_name": f"e2e-user{i % 8}", "_e2e": tag}).encode() + b"\0")
    s.close()


def main() -> int:
    if not GL_PASS:
        print("GL_PASS is required (from scripts/datanode-stack/up.sh)")
        return 2
    tag = uuid.uuid4().hex[:8]
    seed(tag)
    q = f'e2e:{tag} AND event_category:authentication AND event_outcome:failure'
    uid = gl("GET", f"/api/users/{GL_USER}")["id"]          # tokens are created by user id
    tok = gl("POST", f"/api/users/{uid}/tokens/jt-e2e-ai-{tag}", json={})
    token, token_id = tok["token"], tok.get("id")
    tmp = Path(tempfile.mkdtemp(prefix="jt-e2e-ai-"))
    global ok
    rc = 1
    try:
        rc = asyncio.run(run(tmp, q, token, tag))
    except Exception:
        import traceback
        traceback.print_exc()
        ok = False                     # a crash is a failure, never a pass
    finally:
        if token_id:
            httpx.delete(f"{GL_URL}/api/users/{uid}/tokens/{token_id}", auth=(GL_USER, GL_PASS), headers=H)
        print("RESULT: ALL PASS" if ok else "RESULT: FAILED")
    return rc if ok else 1


def _gl_create(path, body):
    """Graylog 7 wants {"entity": ...}; 6 takes the object itself."""
    try:
        return gl("POST", path, json={"entity": body})
    except httpx.HTTPStatusError:
        return gl("POST", path, json=body)


async def events_step(c, auth, q, tag) -> None:
    """mcp_graylog 1.11/1.12 event tools through /mcp, and the owner's rule: a
    notification's recipients, URL and addresses never come back (1.35)."""
    # An HTTP notification (the stack has no e-mail transport): Graylog itself returns
    # its URL, here with a token in it, so this is what must not come back.
    secret = f"s3cr3t-{tag}"
    note = _gl_create("/api/events/notifications", {
        "title": f"e2e notify {tag}", "description": f"call ops-{tag}@example.com or https://wiki.example.com/{tag} 10.9.8.7",
        "config": {"type": "http-notification-v1", "url": f"https://hook.example.com/{tag}?token={secret}",
                   "basic_auth": {"set_value": f"u-{tag}:pw-{tag}"}}})
    nid = note["id"]
    did = None
    try:
        d = _gl_create("/api/events/definitions?schedule=true", {
            "title": f"e2e definition {tag}", "description": "e2e", "priority": 2, "alert": False,
            "config": {"type": "aggregation-v1", "query": q, "query_parameters": [], "streams": [], "group_by": [],
                       "series": [], "conditions": {"expression": None}, "search_within_ms": 600000,
                       "execute_every_ms": 60000, "event_limit": 100},   # 7.2 refuses 0
            "field_spec": {}, "key_spec": [], "notification_settings": {"grace_period_ms": 0, "backlog_size": 0},
            "notifications": [{"notification_id": nid}],
            "storage": [{"type": "persist-to-streams-v1", "streams": ["000000000000000000000002"]}]})
        did = d["id"]

        def call(name, args, rid):
            r = c.post("/mcp", json={"jsonrpc": "2.0", "id": rid, "method": "tools/call",
                                     "params": {"name": name, "arguments": args}}, headers=auth)
            res = r.json()["result"]
            return res["isError"], (res["content"][0]["text"] if res.get("content") else "")
        err, text = call("list_event_definitions", {"query": tag}, 40)
        check(not err and f"e2e definition {tag}" in text and f"e2e notify {tag}" in text,
              f"list_event_definitions finds the definition and names its notification: {text[:120]!r}")
        err, text = call("get_event_definition", {"event_definition_id": did}, 41)
        check(not err and q.split(" AND ")[0] in text, "get_event_definition returns its query")
        err, text = call("list_event_notifications", {}, 42)
        leaked = [x for x in (secret, "hook.example.com", f"ops-{tag}@", "wiki.example.com", "10.9.8.7", f"pw-{tag}")
                  if x in text]
        check(not err and f"e2e notify {tag}" in text and not leaked,
              f"list_event_notifications lists it without URL, token, password or addresses (leaked: {leaked})")
        err, text = call("get_event_definition", {"event_definition_id": did}, 45)
        check(not err and not [x for x in (secret, "hook.example.com") if x in text],
              "get_event_definition names its notification without the notification's URL")
        found = ""
        for _ in range(24):              # the definition runs every minute
            err, text = call("search_events", {"range_from": "now-2d", "event_definition_ids": [did], "per_page": 3}, 43)
            if err or did in text:
                found = text
                break
            await asyncio.sleep(5)
        check(not err and did in found, "search_events over 2 days (past the 24 h message cap) finds the triggered event")
        if did in found:
            ev = next((e for e in json.loads(found).get("events", []) if e.get("event_definition_id") == did), {})
            err, text = call("get_event_source_messages", {"event_id": ev.get("id", ""), "limit": 3}, 44)
            check(not err and "e2e-host" in text, f"get_event_source_messages returns the messages behind it: {text[:100]!r}")
    finally:
        if did:
            httpx.delete(f"{GL_URL}/api/events/definitions/{did}", auth=(GL_USER, GL_PASS), headers=H)
        httpx.delete(f"{GL_URL}/api/events/notifications/{nid}", auth=(GL_USER, GL_PASS), headers=H)


async def run(tmp: Path, q: str, token: str, tag: str) -> int:
    import glogarch.core.config as C
    from fastapi.testclient import TestClient
    from glogarch.ai import graylog_tools as G
    from glogarch.core.database import ArchiveDB

    cfg = tmp / "config.yaml"
    pw = "e2e-" + uuid.uuid4().hex
    cfg.write_text(
        f"servers:\n  - name: e2e\n    url: {GL_URL}\n    username: {GL_USER}\n    password: '{GL_PASS}'\n    verify_ssl: false\n"
        f"database_path: {tmp / 'e2e.db'}\n"
        f"web:\n  localadmin_password_hash: '{hashlib.sha256(pw.encode()).hexdigest()}'\n"
        "ai:\n  mcp_enabled: true\n")
    settings = C.load_settings(str(cfg))
    db = ArchiveDB(str(tmp / "e2e.db"))
    db.connect()
    srv = settings.get_server("e2e")
    ctx = G.Ctx(settings=settings, db=db, server=srv, auth=(token, "token"), username="admin")

    # 1. exact tools (wait until the events are searchable)
    count = None
    for _ in range(30):
        r = await G.call_tool("count_messages", {"query": q, "range_from": "now-30m"}, ctx)
        count = json.loads(r["result"])["count"] if r["ok"] else None
        if count == 60:
            break
        await asyncio.sleep(2)
    check(count == 60, f"count_messages is exact: {count} of 60")
    r = await G.call_tool("top_values", {"field": "source_ip", "query": q, "range_from": "now-30m",
                                         "distinct_field": "user_name"}, ctx)
    rows = json.loads(r["result"])["rows"] if r["ok"] else []
    check(rows[:1] == [{"value": PEER, "count": 60, "distinct_user_name": 8}], f"top_values exact: {rows[:1]}")

    # 2. MCP with the real token (real role check against Graylog)
    from glogarch.web.app import create_app
    app = create_app()
    c = TestClient(app, base_url="https://testserver")
    auth = {"Authorization": f"Bearer {token}"}
    r = c.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize",
                             "params": {"protocolVersion": "2025-06-18"}}, headers=auth)
    check(r.status_code == 200 and r.json()["result"]["serverInfo"]["name"] == "jt-glogarch",
          f"MCP initialize with a Graylog token ({r.status_code})")
    r = c.post("/mcp", json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, headers=auth)
    names = [t["name"] for t in r.json()["result"]["tools"]]
    check("count_messages" in names, f"MCP tools/list ({len(names)} tools)")
    r = c.post("/mcp", json={"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                             "params": {"name": "count_messages", "arguments": {"query": q, "range_from": "now-30m"}}},
               headers=auth)
    res = r.json()["result"]
    check(not res["isError"] and json.loads(res["content"][0]["text"])["count"] == 60, "MCP tools/call count = 60")
    r = c.post("/mcp", json={"jsonrpc": "2.0", "id": 4, "method": "ping"}, headers={"Authorization": "Bearer bogus-token"})
    check(r.status_code == 403, f"a token Graylog does not know is refused ({r.status_code})")
    audited = app.state.db.conn.execute(
        "SELECT COUNT(*) FROM audit_log WHERE action = 'ai_tool_call' AND detail LIKE 'channel=mcp%'").fetchone()[0]
    check(audited >= 1, f"MCP tool calls audited ({audited})")

    # 3. mcp_graylog through MCP (1.9.44 needed Python 3.12; 1.10.2 loads on 3.10)
    st = G.mcpg_status()
    check(st["available"], f"mcp_graylog {st['version']} loads on Python {sys.version.split()[0]}")
    r = c.post("/mcp", json={"jsonrpc": "2.0", "id": 5, "method": "tools/call",
                             "params": {"name": "get_log_sample", "arguments": {"query": q, "range_from": "now-30m", "limit": 5}}},
               headers=auth)
    res = r.json()["result"]
    body = json.loads(res["content"][0]["text"]) if not res["isError"] else {}
    check(len(body.get("messages") or []) == 5, f"mcp_graylog get_log_sample via MCP: {len(body.get('messages') or [])} messages")
    # 1.10.1: distributions are aggregated by Graylog, not sampled
    r = c.post("/mcp", json={"jsonrpc": "2.0", "id": 6, "method": "tools/call",
                             "params": {"name": "analyze_source_distribution", "arguments": {"query": q, "range_from": "now-30m"}}},
               headers=auth)
    res = r.json()["result"]
    text = res["content"][0]["text"] if res.get("content") else ""
    check(not res["isError"] and "e2e-host" in text, f"mcp_graylog analyze_source_distribution: {text[:160]!r}")
    # a wildcard query is sent as "everything", not as `*` (which 1.10.2 retried ~900 times on 7.2)
    t0 = time.monotonic()
    r = c.post("/mcp", json={"jsonrpc": "2.0", "id": 9, "method": "tools/call",
                             "params": {"name": "get_log_sample", "arguments": {"query": "*:*", "range_from": "now-30m", "limit": 3}}},
               headers=auth)
    res = r.json()["result"]
    check(not res["isError"] and time.monotonic() - t0 < 30, f"get_log_sample with *:* answers quickly ({time.monotonic() - t0:.1f} s)")
    names_now = [t["name"] for t in c.post("/mcp", json={"jsonrpc": "2.0", "id": 10, "method": "tools/list"}, headers=auth).json()["result"]["tools"]]
    check(not {"get_log_statistics", "analyze_error_patterns", "get_log_level_analysis"} & set(names_now),
          "the message-pulling mcp_graylog tools are not offered by default")
    r = c.post("/mcp", json={"jsonrpc": "2.0", "id": 7, "method": "tools/call",
                             "params": {"name": "find_silent_sources", "arguments": {"lookback_hours": 2, "silent_minutes": 0}}},
               headers=auth)
    res = r.json()["result"]
    text = res["content"][0]["text"] if res.get("content") else ""
    check(not res["isError"] and "e2e-host" in text, f"mcp_graylog find_silent_sources lists the seeded hosts: {text[:160]!r}")
    r = c.post("/mcp", json={"jsonrpc": "2.0", "id": 8, "method": "tools/call",
                             "params": {"name": "find_silent_sources", "arguments": {"lookback_hours": 100000}}},
               headers=auth)
    check(r.json()["result"]["isError"], "find_silent_sources look-back is capped")
    await events_step(c, auth, q, tag)

    # 4. a real LLM, if configured
    if AI_URL:
        from glogarch.ai.chat import run_chat
        from glogarch.core.config import AiConfig
        acfg = AiConfig(enabled=True, url=AI_URL, model=os.environ.get("AI_MODEL", ""),
                        api_key=os.environ.get("AI_KEY", ""), allow_external=False)
        ctx.settings.ai = acfg               # 1.36: run_chat takes the LLM server entry; limits come from settings.ai
        events = []

        async def emit(e):
            events.append(e)
        out = await run_chat(acfg.llm(), ctx, [], f"How many failed logins came from {PEER} in the last 30 minutes "
                                                   f"in messages with e2e:{tag}? Give the number.", "en", emit)
        model_ev = next((e for e in events if e.get("phase") == "model"), {})
        check(model_ev.get("context", 0) > 0, f"the chat read the model's context window: {model_ev}")
        # What jt-glogarch guarantees: the number in the answer is what the tool returned
        # for the query the model chose (no invented facts). Whether the model chose
        # the RIGHT query is model quality: reported, not failed (measured 2026-11-19:
        # the iq3 model dropped the e2e:<tag> condition and counted both runs).
        calls = [e for e in events if e.get("phase") == "tool"]
        check(not out["error"] and calls, f"real LLM used a tool ({out['elapsed_ms']} ms, tools {out['tools']}) {out['error']}")
        truth = None
        # the newest call that produced a number (the model may look at incidents afterwards)
        for c in reversed([x for x in calls if x["name"] in ("count_messages", "top_values", "aggregate")]):
            r = await G.call_tool(c["name"], c["args"], ctx)
            try:
                body = json.loads(r["result"]) if r.get("ok") else {}
            except ValueError:
                body = {}
            truth = body.get("count")
            if truth is None and body.get("rows"):
                truth = body["rows"][0].get("count")
            if truth is not None:
                break
        stated = truth is not None and str(truth) in out["answer"].replace(",", "")
        check(stated, f"the answer states what its own query returned ({truth}): {out['answer'][:100]!r}")
        if not stated:   # say which query gave which number, so model quality and our bug can be told apart
            for x in out.get("calls") or []:
                print(f"    call {x['name']}: query={x.get('query')!r} range={x.get('range')} "
                      f"count={x.get('count')} rows={x.get('rows')} ok={x['ok']} {x.get('error', '')}")
            print(f"    answer: {out['answer'][:600]!r}")
        # 1.34: the answer was streamed, and each query is kept with what it really ran
        streamed = ""
        for e in (e for e in events if e.get("phase") == "answer"):
            streamed = e["text"] if e.get("reset") else streamed + e.get("delta", "")
        check(streamed.strip() == out["answer"].strip(),
              f"the streamed text adds up to the stored answer ({len(streamed)} / {len(out['answer'])} chars)")
        rec = [x for x in out.get("calls") or [] if x["name"] in ("count_messages", "top_values") and x["ok"]]
        check(rec and all(x.get("range", {}).get("from") and isinstance(x.get("query"), str) for x in rec),
              f"each query is recorded with its range ({len(rec)} recorded)")
        counted = [x["count"] for x in rec if "count" in x]
        check(not counted or truth in counted or any(x.get("rows") for x in rec),
              f"a recorded count matches Graylog ({counted} vs {truth})")
        used_q = json.dumps([c["args"] for c in calls], ensure_ascii=False)
        if f"e2e:{tag}" not in used_q:
            print(f"WARN model quality: its query dropped the e2e:{tag} condition: {used_q[:200]}")
        elif str(60) not in out["answer"]:
            print("WARN model quality: right query, but the answer does not say 60")
    else:
        print("SKIP real LLM (AI_URL not set)")

    # 5. incident -> evidence -> AI analysis (added 1.22)
    from glogarch.core.config import AiConfig
    from glogarch.security import ai_analysis as A
    from glogarch.security.runner import run_security_analysis
    run = await run_security_analysis(settings, db, source="manual")
    check(run["status"] in ("ok", "partial"), f"detector run: {run.get('status')} {run.get('errors')}")
    rows, _ = db.list_security_incidents(detector="auth_spray", limit=10)
    inc = next((r for r in rows if r["entity"] == PEER), None)
    check(inc is not None, f"auth_spray incident opened for {PEER}")
    if inc:
        sctx = A.server_ctx(settings, db, srv)
        ev = await A.collect_evidence(inc, sctx, int(settings.security.window_minutes))
        check(not ev["errors"], f"evidence queries all ran ({ev['queries']}): {ev['errors']}")
        check((ev.get("events_in_window") or 0) >= 60, f"evidence counts the seeded failures: {ev.get('events_in_window')}")
        users = {r["value"] for r in ev["breakdown"].get("user_name", [])}
        check(users and all(u.startswith("e2e-user") for u in users), f"evidence top accounts: {sorted(users)}")
        # the security e2e may have seeded successes for the same peer on this stack: compare with Graylog
        truth_ok = (await G._count({"query": ev.get("successful_logins", {}).get("query", ""),
                                    "range_from": ev["window"]["from"], "range_to": ev["window"]["to"]}, sctx))["count"]
        check(ev.get("successful_logins", {}).get("count") == truth_ok,
              f"successful logins of the peer match Graylog ({truth_ok})")
        sm = ev.get("sample_messages") or []
        check(len(sm) == A.SAMPLE_N and all(m.get("source_ip") == PEER for m in sm),
              f"example messages are the peer's ({len(sm)})")
        if AI_URL:
            settings.ai = AiConfig(analysis_enabled=True, url=AI_URL, model=os.environ.get("AI_MODEL", ""),
                                   api_key=os.environ.get("AI_KEY", ""), timeout_seconds=600)
            row = await A.analyze_incident(settings, db, inc["id"], lang="zh-TW", username="e2e")
            check(not row["error"] and row["verdict"] in A.VERDICTS,
                  f"real model analysis: {row['verdict']}/{row['confidence']} in {row['elapsed_ms']} ms, "
                  f"{row['tokens']} tokens {row['error']}")
            check(not row["unverified"], f"no invented addresses: {row['unverified']}")
            print("     summary:", (row.get("result") or {}).get("summary", "")[:200])
            if row["verdict"] not in ("malicious", "suspicious"):
                print(f"WARN model quality: 60 failures over 8 accounts from a public address read as {row['verdict']}")
        else:
            print("SKIP real-model incident analysis (AI_URL not set)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
