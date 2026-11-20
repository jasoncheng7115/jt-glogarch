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
GELF TCP input (container port 32202) when there is none. Then the silent-source
detection (1.26): a host whose 60 messages are 3 h old is silent, one still sending is not;
the volume anomaly (1.30): a 600-message burst against a usual of 20 an hour.
Prints RESULT: ALL PASS.
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


def seed_silent(tag: str) -> tuple[str, str]:
    """60 messages from a host that stopped 3 h ago, and 60 old + 5 fresh from one that still sends."""
    quiet, alive = f"e2e-quiet-{tag}", f"e2e-alive-{tag}"
    old_ts = time.time() - 3 * 3600
    s = socket.create_connection(("127.0.0.1", GELF_PORT), timeout=10)
    for i in range(60):
        for host in (quiet, alive):
            s.sendall(json.dumps({"version": "1.1", "host": host, "short_message": "heartbeat",
                                  "timestamp": old_ts + i, "_e2e": tag}).encode() + b"\0")
    for _ in range(5):
        s.sendall(json.dumps({"version": "1.1", "host": alive, "short_message": "heartbeat",
                              "_e2e": tag}).encode() + b"\0")
    s.close()
    return quiet, alive


async def silent_step(srv, tag: str) -> None:
    """source_silent (added 1.26) against the real aggregation API: two windows."""
    from glogarch.security.detectors import DETECTORS
    quiet, alive = seed_silent(tag)
    only = {d.id: {"enabled": d.id == "source_silent"} for d in DETECTORS}
    res = None
    async with GraylogClient(srv, RateLimiter(RateLimitConfig())) as c:
        for _ in range(30):
            now = datetime.now(timezone.utc)
            res = await run_detectors(make_fetch(c), now - timedelta(minutes=30), now + timedelta(minutes=1),
                                      settings=only, global_exclude=f"_exists_:e2e AND NOT e2e:{tag}")
            if any(f.entity == quiet for f in res.findings):
                break
            await asyncio.sleep(2)
    hit = {f.entity: f for f in res.findings}
    check(not res.errors, f"silent-source aggregations answered ({res.queries} searches) {res.errors or ''}")
    check(quiet in hit and hit[quiet].metrics.get("baseline") == 60,
          f"a host that stopped 3 h ago is silent with 60 messages before ({hit.get(quiet) and hit[quiet].metrics})")
    check(alive not in hit, "a host that still sends is not")


SIGMA_RULE = """
title: e2e failed logins (Sigma)
level: high
tags: [attack.t1110]
detection:
  sel:
    event_category: authentication
    event_outcome: failure
    user_name|contains: '2e-user'
    source_ip|startswith: '45.33.'
  host1:
    source|endswith: '-host1'
  kw:
    - 'auth fail'
  condition: sel and kw and not host1
"""


async def sigma_step(srv, tag: str) -> None:
    """Sigma (added 1.27): the converted query (phrase, regex for contains/endswith,
    wildcard for startswith, NOT) must run on a real Graylog and count exactly."""
    from glogarch.security.detectors import DETECTORS
    from glogarch.security.sigma import convert, parse_rule
    r = parse_rule(SIGMA_RULE)
    query = convert(r)
    print("     sigma query:", query)
    none = {d.id: {"enabled": False} for d in DETECTORS}
    rule = {"id": 1, "title": r["title"], "level": r["level"], "query": query, "group_by": "source",
            "threshold": 10, "tags": r["tags"]}
    async with GraylogClient(srv, RateLimiter(RateLimitConfig())) as c:
        now = datetime.now(timezone.utc)
        res = await run_detectors(make_fetch(c), now - timedelta(minutes=30), now + timedelta(minutes=1),
                                  settings=none, global_exclude=f"_exists_:e2e AND NOT e2e:{tag}", sigma_rules=[rule])
    got = {f.entity: f.metrics["count"] for f in res.findings}
    check(not res.errors, f"Graylog accepted the converted Sigma query {res.errors or ''}")
    check(got == {"e2e-host0": 15, "e2e-host2": 15, "e2e-host3": 15},
          f"Sigma rule: 15 per host, host1 excluded by endswith, the no-ip event dropped by startswith ({got})")
    check(res.sigma.get(1, {}).get("count") == 45, f"rule total 45 ({res.sigma.get(1)})")
    # GELF short_message is stored as `message` (analyzed): contains must become a phrase, not a regex
    r2 = parse_rule("title: msg\ndetection:\n  s: {short_message|contains: 'auth fail'}\n  condition: s")
    rule2 = {"id": 2, "title": "msg", "level": "low", "query": convert(r2), "group_by": "source",
             "threshold": 1, "tags": []}
    async with GraylogClient(srv, RateLimiter(RateLimitConfig())) as c:
        now = datetime.now(timezone.utc)
        res2 = await run_detectors(make_fetch(c), now - timedelta(minutes=30), now + timedelta(minutes=1),
                                   settings=none, global_exclude=f"_exists_:e2e AND NOT e2e:{tag}", sigma_rules=[rule2])
    check(res2.sigma.get(2, {}).get("count") == 61, f"short_message|contains matches the 61 'auth fail' messages ({res2.sigma.get(2)})")


async def new_source_step(srv, tag: str) -> None:
    """account_new_source (added 1.29): two groupings in one real aggregation, then the
    runner's history logic: e2e-user1 had another source 8 days ago, now logs in from PEER."""
    import tempfile
    from glogarch.core.database import ArchiveDB
    from glogarch.security.detectors import DETECTORS
    from glogarch.security.graylog_fetch import make_pair_fetch
    from glogarch.security.runner import new_source_findings
    only = {d.id: {"enabled": d.id == "account_new_source"} for d in DETECTORS}
    async with GraylogClient(srv, RateLimiter(RateLimitConfig())) as c:
        now = datetime.now(timezone.utc)
        res = await run_detectors(make_fetch(c), now - timedelta(minutes=30), now + timedelta(minutes=1),
                                  settings=only, global_exclude=f"_exists_:e2e AND NOT e2e:{tag}",
                                  fetch_pairs=make_pair_fetch(c))
    check(not res.errors, f"pair aggregation answered {res.errors or ''}")
    check(("e2e-user1", PEER, 3) in res.pairs, f"(account, source) pairs from Graylog: {res.pairs}")
    db = ArchiveDB(tempfile.mktemp(suffix=".db"))
    db.connect()
    naive = now.replace(tzinfo=None)
    db.record_pairs("e2e", [("e2e-user1", "10.9.9.9")], naive - timedelta(days=8))
    f = new_source_findings(db, "e2e", res.pairs, naive)
    check([x["entity"] for x in f] == ["e2e-user1"] and f[0]["metrics"]["new_sources"] == [PEER]
          and f[0]["severity"] == "medium", f"new login source found for the account with history: {f}")


async def volume_step(srv, tag: str) -> None:
    """volume_anomaly (added 1.30): the real two aggregations, then the runner's
    history logic against 10 days of a quiet usual (20 messages an hour)."""
    import tempfile
    from glogarch.core.database import ArchiveDB
    from glogarch.security.detectors import DETECTORS
    from glogarch.security.runner import volume_findings
    host, cat, n = f"e2e-burst-{tag}", f"e2e_burst_{tag}", 600
    s = socket.create_connection(("127.0.0.1", GELF_PORT), timeout=10)
    for i in range(n):
        s.sendall(json.dumps({"version": "1.1", "host": host, "short_message": f"burst {i}",
                              "_event_category": cat, "_e2e": tag}).encode() + b"\0")
    s.close()
    only = {d.id: {"enabled": d.id == "volume_anomaly"} for d in DETECTORS}
    res = None
    async with GraylogClient(srv, RateLimiter(RateLimitConfig())) as c:
        for _ in range(30):
            now = datetime.now(timezone.utc)
            res = await run_detectors(make_fetch(c), now - timedelta(minutes=60), now,
                                      settings=only, global_exclude=f"_exists_:e2e AND NOT e2e:{tag}")
            if ("source", host, n) in res.volumes:
                break
            await asyncio.sleep(2)
    check(not res.errors and res.queries == 2, f"volume aggregations answered ({res.queries} searches) {res.errors or ''}")
    check(("source", host, n) in res.volumes and ("event_category", cat, n) in res.volumes,
          f"messages per host and per category from Graylog: {[v for v in res.volumes if tag in v[1]]}")
    db = ArchiveDB(tempfile.mktemp(suffix=".db"))
    db.connect()
    naive = now.replace(tzinfo=None, microsecond=0)
    base = naive.replace(minute=0, second=0)
    for k in range(1, 11):
        for d in (-1, 0, 1):
            db.record_volumes("e2e", [("source", host, 20.0), ("event_category", cat, 20.0)],
                              base - timedelta(days=k) + timedelta(hours=d))
    f = {(x["entity_field"], x["entity"]): x for x in
         volume_findings(db, "e2e", res.volumes, naive, 60, min_count=500)}
    check(set(f) == {("source", host), ("event_category", cat)},
          f"a host and a category far above their usual are found, nothing else: {sorted(f)}")
    fh = f.get(("source", host))
    check(bool(fh) and fh["metrics"]["usual"] == 20 and fh["metrics"]["ratio"] == 30.0 and fh["severity"] == "medium",
          f"usual 20/h, 30x, medium: {fh and (fh['metrics'], fh['severity'])}")
    async with GraylogClient(srv, RateLimiter(RateLimitConfig())) as c:
        now = datetime.now(timezone.utc)
        rows = await make_fetch(c)(fh["query"], "source", (("count", None),), now - timedelta(minutes=60), now, 10)
    check([(r["entity"], r["count"]) for r in rows] == [(host, n)], f"the incident's query finds the burst: {rows}")


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
    await silent_step(srv, tag)
    await sigma_step(srv, tag)
    await new_source_step(srv, tag)
    await volume_step(srv, tag)
    print("RESULT: ALL PASS" if ok else "RESULT: FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
