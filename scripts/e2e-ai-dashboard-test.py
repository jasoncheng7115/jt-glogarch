#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""e2e for 1.37 "Graylog dashboard from an answer" against a THROWAWAY Graylog
(scripts/datanode-stack/up.sh; never log3/log4).

Seeds GELF messages, builds chart specs the way recorded tool calls give them,
creates the dashboard through glogarch.ai.gl_dashboard.create (the product
code), then checks: the view reads back with every widget mapped to a search
type, executing its search returns rows for every widget with no error, and
the chart re-run (glogarch.ai.charts.run_spec) agrees with Graylog. The test
deletes only the dashboard it created.

  GL_URL=http://127.0.0.1:19000 GL_PASS=... GELF_PORT=32212 python3 scripts/e2e-ai-dashboard-test.py
Prints RESULT: ALL PASS.
"""

import asyncio
import json
import os
import random
import socket
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402

from glogarch.ai import charts as C  # noqa: E402
from glogarch.ai import gl_dashboard as D  # noqa: E402
from glogarch.ai.graylog_tools import Ctx  # noqa: E402

GL = os.environ.get("GL_URL", "http://127.0.0.1:19000").rstrip("/")
USER = os.environ.get("GL_USER", "admin")
PW = os.environ["GL_PASS"]
GELF_PORT = int(os.environ.get("GELF_PORT", "32212"))
HDR = {"X-Requested-By": "jt-e2e", "Accept": "application/json"}
FAIL = []


def check(ok, what):
    print(("PASS " if ok else "FAIL ") + what)
    if not ok:
        FAIL.append(what)


def seed(tag: str, n: int = 300) -> None:
    s = socket.create_connection(("127.0.0.1", GELF_PORT), timeout=10)
    now = time.time()
    for i in range(n):
        ok = i % 3 != 0
        m = {"version": "1.1", "host": f"web{i % 3}", "short_message": f"login {'ok' if ok else 'failed'}",
             "timestamp": now - random.randint(10, 3000), "_e2e": tag,
             "_event_outcome": "success" if ok else "failure", "_source_ip": f"192.0.2.{i % 7 + 1}",
             "_user_name": f"u{i % 4}", "_took_ms": i % 97}
        s.sendall(json.dumps(m).encode() + b"\0")
    s.close()


async def session_auth() -> tuple[str, str]:
    async with httpx.AsyncClient(headers=HDR, timeout=30) as c:
        r = await c.post(GL + "/api/system/sessions", json={"username": USER, "password": PW, "host": ""})
        r.raise_for_status()
        return (r.json()["session_id"], "session")


async def wait_indexed(auth, tag: str, want: int) -> int:
    ctx = Ctx(settings=None, db=None, server=SimpleNamespace(url=GL, verify_ssl=False, name="e2e"), auth=auth)
    from glogarch.ai.graylog_tools import _count
    n = 0
    for _ in range(40):
        n = (await _count({"query": f"e2e:{tag}", "range_from": "now-2h"}, ctx))["count"]
        if n >= want:
            break
        await asyncio.sleep(3)
    return n


async def main():
    tag = uuid.uuid4().hex[:10]
    seed(tag)
    auth = await session_auth()
    n = await wait_indexed(auth, tag, 300)
    check(n == 300, f"seeded messages indexed ({n}/300)")
    now = datetime.now(timezone.utc)
    rng = {"from": (now - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
           "to": (now + timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%S.000Z")}
    q = f"e2e:{tag}"

    def call(name, args, query=q):
        return {"name": name, "ok": True, "args": args, "query": query, "range": rng, "server": "e2e"}
    specs = C.specs_from_calls([
        call("aggregate", {"group_by": ["timestamp:5m", "event_outcome"], "metrics": ["count"]}),
        call("top_values", {"field": "source_ip", "limit": 10}, q + " AND event_outcome:failure"),
        call("count_messages", {}, q + " AND event_outcome:failure"),
        call("aggregate", {"group_by": ["user_name", "source_ip:3"], "metrics": ["count", "p95:took_ms", "card:source"]}),
        call("aggregate", {"group_by": ["timestamp:15m"], "metrics": ["count", "avg:took_ms"]}),
    ])
    check([s["kind"] for s in specs] == ["timeseries", "bar", "number", "table", "timeseries"], "spec kinds")
    srv = SimpleNamespace(url=GL, verify_ssl=False, name="e2e")
    ctx = Ctx(settings=None, db=None, server=srv, auth=auth)
    data = {s["id"]: await C.run_spec(s, ctx) for s in specs}
    check(all(d["ok"] for d in data.values()), "every chart re-runs")
    fails = data[specs[2]["id"]]["count"]
    check(fails == 100, f"failure count re-run = 100 ({fails})")
    top = data[specs[1]["id"]]["rows"]
    check(sum(r["count"] for r in top) == 100, "top source_ip of failures sums to 100")
    picks = [{"id": s["id"], "vis": v, "title": f"e2e {k}"}
             for k, (s, v) in enumerate(zip(specs, ["area", "pie", "numeric", "table", "bar"]))]
    search, view, notes = D.build(specs, picks, f"jt e2e {tag}", D.timerange_for("1d"), "e2e")
    vid = await D.create(srv, auth, search, view)
    check(bool(vid), f"dashboard created ({vid})")
    async with httpx.AsyncClient(headers=HDR, auth=auth, timeout=60) as c:
        try:
            v = (await c.get(f"{GL}/api/views/{vid}")).json()
            check(v.get("type") == "DASHBOARD" and v.get("title") == f"jt e2e {tag}", "view reads back as a dashboard")
            st = next(iter(v["state"].values()))
            check(len(st["widgets"]) == 5, "five widgets")
            sid = v["search_id"]
            srch = (await c.get(f"{GL}/api/views/search/{sid}")).json()
            st_ids = {t["id"] for qq in srch["queries"] for t in qq["search_types"]}
            check(all(st["widget_mapping"][w["id"]][0] in st_ids for w in st["widgets"]),
                  "every widget maps to a search type of its search")
            # Graylog does not keep the widgets' order; the titles say which is which
            got = {st["titles"]["widget"][w["id"]]: w["config"]["visualization"] for w in st["widgets"]}
            want = {p["title"]: p["vis"] for p in picks}
            check(got == want, f"chart types and titles kept {got}")
            ex = (await c.post(f"{GL}/api/views/search/{sid}/execute", json={})).json()
            for _ in range(30):
                if (ex.get("execution") or {}).get("done"):
                    break
                await asyncio.sleep(1)
                ex = (await c.get(f"{GL}/api/views/search/status/{ex['id']}")).json()
            res = next(iter((ex.get("results") or {}).values()), {})
            check(not res.get("errors"), f"search runs without errors ({res.get('errors')})")
            rows = {k: len(t.get("rows") or []) for k, t in (res.get("search_types") or {}).items()}
            check(len(rows) == 5 and all(n > 0 for n in rows.values()), f"every widget has rows {sorted(rows.values())}")
            for k, t in (res.get("search_types") or {}).items():
                w = next(w for w in st["widgets"] if st["widget_mapping"][w["id"]][0] == k)
                if w["config"]["visualization"] == "numeric":
                    val = t["rows"][0]["values"][0]["value"]
                    check(val == fails, f"Graylog's number widget = our re-run ({val} vs {fails})")
        finally:
            r = await c.delete(f"{GL}/api/views/{vid}")     # the test's own dashboard only
            check(r.status_code < 300, "test dashboard removed")
    # a refused create says why
    bad = dict(view, state={"x": {}})
    try:
        await D.create(srv, auth, search, bad)
        check(False, "a broken view is refused")
    except RuntimeError as e:
        check("Graylog refused" in str(e), f"a broken view is refused ({str(e)[:80]})")
    print("RESULT: ALL PASS" if not FAIL else f"RESULT: {len(FAIL)} FAILED: {FAIL}")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
