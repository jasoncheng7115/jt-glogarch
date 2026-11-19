#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Security detectors against a REAL Graylog (throwaway stack only).

Seeds GIM-style authentication events over GELF TCP, then runs the detectors
through Graylog's scripting API and checks what they find. NEVER point it at
production: it writes test events into the target.

    bash scripts/datanode-stack/up.sh            # prints GL_URL / GL_PASS / GELF_PORT
    GL_URL=http://127.0.0.1:19000 GL_PASS=... GELF_PORT=32212 \\
        python3 scripts/e2e-security-test.py
    bash scripts/datanode-stack/down.sh

Run it from /tmp with PYTHONPATH=<repo> to use this checkout's code. Creates a
GELF TCP input (container port 32202) when there is none. Prints RESULT: ALL PASS.
"""
from __future__ import annotations

import asyncio
import json
import os
import socket
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone

import httpx

from glogarch.core.config import GraylogServerConfig, RateLimitConfig
from glogarch.graylog.client import GraylogClient
from glogarch.ratelimit.limiter import RateLimiter
from glogarch.security.engine import run_detectors
from glogarch.security.graylog_fetch import make_fetch

GL_URL = os.environ.get("GL_URL", "http://127.0.0.1:19000").rstrip("/")
GL_USER = os.environ.get("GL_USER", "admin")
GL_PASS = os.environ.get("GL_PASS", "")
GELF_PORT = int(os.environ.get("GELF_PORT", "32212"))
PEER = "45.33.32.156"
FAILS = 60

ok = True


def check(cond: bool, what: str) -> None:
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    ok = ok and cond


def ensure_gelf_input() -> None:
    auth = (GL_USER, GL_PASS)
    h = {"X-Requested-By": "jt-glogarch-e2e", "Content-Type": "application/json"}
    r = httpx.get(f"{GL_URL}/api/system/inputs", auth=auth)
    r.raise_for_status()
    if any(i["type"].endswith("GELFTCPInput") for i in r.json().get("inputs", [])):
        return
    httpx.post(f"{GL_URL}/api/system/inputs", auth=auth, headers=h, json={
        "title": "e2e-security gelf", "type": "org.graylog2.inputs.gelf.tcp.GELFTCPInput",
        "global": True, "configuration": {"bind_address": "0.0.0.0", "port": 32202,
                                          "recv_buffer_size": 1048576, "use_null_delimiter": True}},
    ).raise_for_status()
    time.sleep(8)


def seed(tag: str) -> None:
    s = socket.create_connection(("127.0.0.1", GELF_PORT), timeout=10)
    for i in range(FAILS):
        s.sendall(json.dumps({"version": "1.1", "host": f"e2e-host{i % 4}", "short_message": "auth fail",
                              "_event_category": "authentication", "_event_outcome": "failure",
                              "_source_ip": PEER, "_user_name": f"e2e-user{i % 8}", "_e2e": tag}).encode() + b"\0")
    for _ in range(3):
        s.sendall(json.dumps({"version": "1.1", "host": "e2e-host0", "short_message": "auth ok",
                              "_event_category": "authentication", "_event_outcome": "success",
                              "_source_ip": PEER, "_user_name": "e2e-user1", "_e2e": tag}).encode() + b"\0")
    # an event with no peer field: must show up as coverage, never as an incident
    s.sendall(json.dumps({"version": "1.1", "host": "e2e-host9", "short_message": "auth fail, no ip",
                          "_event_category": "authentication", "_event_outcome": "failure",
                          "_e2e": tag}).encode() + b"\0")
    s.close()


async def main() -> int:
    if not GL_PASS:
        print("GL_PASS is required (from scripts/datanode-stack/up.sh)")
        return 2
    ensure_gelf_input()
    tag = uuid.uuid4().hex[:8]
    seed(tag)
    srv = GraylogServerConfig(name="e2e", url=GL_URL, username=GL_USER, password=GL_PASS, verify_ssl=False)
    async with GraylogClient(srv, RateLimiter(RateLimitConfig())) as c:
        print("Graylog", (await c.get("/api/system"))["version"])
        res = None
        # GELF "_e2e" is stored as field `e2e`. Earlier runs on the same stack are
        # left out so the counts below are this run's only.
        for _ in range(30):                   # wait until the events are searchable
            now = datetime.now(timezone.utc)
            res = await run_detectors(make_fetch(c), now - timedelta(minutes=30), now + timedelta(minutes=1),
                                      global_exclude=f"_exists_:e2e AND NOT e2e:{tag}")
            if any(f.detector == "auth_success_after_fail" for f in res.findings):
                break
            await asyncio.sleep(2)
    check(not res.errors, f"every aggregation answered ({res.queries} searches) {res.errors or ''}")
    found = {(f.detector, f.entity): f for f in res.findings}
    for det, sev in (("auth_bruteforce", "medium"), ("auth_spray", "high"),
                     ("auth_multi_host", "high"), ("auth_success_after_fail", "high")):
        f = found.get((det, PEER))
        check(f is not None and f.severity == sev, f"{det} on {PEER} -> {sev} (got {f and f.severity})")
    sp = found.get(("auth_spray", PEER))
    check(bool(sp) and sp.metrics.get("card:user_name") == 8 and sp.metrics.get("card:source") == 4,
          f"distinct accounts/hosts counted by Graylog (8 / 4): {sp and sp.metrics}")
    sa = found.get(("auth_success_after_fail", PEER))
    check(bool(sa) and sa.metrics.get("success") == 3, "3 successful logins found by the second search")
    cov = next((c for c in res.coverage if c.probe == "auth_fail_peer" and c.field == "source_ip"), None)
    check(bool(cov) and cov.events == FAILS + 1 and cov.missing == 1,
          f"the event without a peer field is coverage, not an incident ({cov and (cov.events, cov.missing)})")
    check(not [f for f in res.findings if f.entity == "(Empty Value)"], "no incident for '(Empty Value)'")
    print("RESULT: ALL PASS" if ok else "RESULT: FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
