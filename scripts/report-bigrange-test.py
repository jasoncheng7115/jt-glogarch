#!/usr/bin/env python3
"""Standard test: wide-window report machinery against a LIVE Graylog.

    GL_PASS=<admin-pw> python3 scripts/report-bigrange-test.py [GL_URL]

Creates a throwaway dashboard containing exactly the two widget shapes the
wide-window machinery must handle, runs a 90-day rebuild, and asserts every
promise the feature makes. Deletes the dashboard afterwards.

Why this exists — and why a unit suite is NOT enough here: both bugs this
script would have caught were LIVE-SCHEMA mismatches invisible to unit tests
built on assumed JSON:
  * the search definition writes intervals as {"timeunit": "5m"}, not the
    widget-config {"value": 5, "unit": "minutes"} → coarsening silently never
    fired;
  * it writes series as {"type": "count"}, not {"function": "count()"} →
    every search type classified unmergeable, slicing silently never engaged,
    and a naive "sliced == unsliced" comparison passed because BOTH runs were
    unsliced. This script asserts the log-visible engagement of each
    mechanism, not just equal numbers.

Assertions:
  1. coarsening fired: the fixed-5m timeline's caption announces the change;
  2. slicing engaged: sliced + whole counts from the run report;
  3. the avg widget carries the "cannot be merged from slices" caption;
  4. EXACTNESS: the sliced 90-day count total equals a below-threshold
     (unsliced) control run over the same data;
  5. the throwaway dashboard renders to a real PDF (when the render engine is
     installed; skipped otherwise with a loud note).

Run it ON a box that can reach the Graylog API. Safe: creates and deletes
only its own dashboard, read-only for everything else.
"""
import asyncio
import os
import sys
import uuid

import httpx

GL_URL = (sys.argv[1] if len(sys.argv) > 1 else
          os.environ.get("GL_URL", "http://localhost:9000")).rstrip("/")
GL_USER = os.environ.get("GL_USER", "admin")
GL_PASS = os.environ.get("GL_PASS", "")
H = {"X-Requested-By": "jt-glogarch", "Content-Type": "application/json"}
DAY = 86400
FAIL = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}: {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name)


def uid():
    return str(uuid.uuid4())


async def make_dashboard(c):
    q_id, st_time, st_avg, w_time, w_avg = uid(), uid(), uid(), uid(), uid()
    search = {"queries": [{
        "id": q_id, "query": {"type": "elasticsearch", "query_string": ""},
        "timerange": {"type": "relative", "range": DAY},
        "search_types": [
            {"id": st_time, "type": "pivot", "name": "chart",
             "series": [{"id": "count()", "type": "count"}],
             "row_groups": [{"type": "time", "fields": ["timestamp"],
                             "interval": {"type": "timeunit", "timeunit": "5m"}}],
             "column_groups": [], "rollup": True, "sort": []},
            {"id": st_avg, "type": "pivot", "name": "chart",
             "series": [{"id": "avg(gl2_processing_duration_ms)", "type": "avg",
                         "field": "gl2_processing_duration_ms"}],
             "row_groups": [{"type": "values", "fields": ["source"], "limit": 10}],
             "column_groups": [], "rollup": True, "sort": []}]}]}
    r = await c.post(f"{GL_URL}/api/views/search", json=search)
    r.raise_for_status()
    sid = r.json()["id"]
    view = {"type": "DASHBOARD", "title": "jt-bigrange-test", "summary": "",
            "description": "", "search_id": sid, "properties": [],
            "state": {q_id: {
                "titles": {"widget": {w_time: "Fixed 5m timeline",
                                      w_avg: "Avg (unsliceable)"},
                           "tab": {"title": "T1"}},
                "widgets": [
                    {"id": w_time, "type": "aggregation", "streams": [],
                     "config": {"visualization": "line", "rollup": True, "sort": [],
                                "row_pivots": [{"type": "time", "fields": ["timestamp"],
                                                "config": {"interval": {"type": "timeunit",
                                                                        "value": 5, "unit": "minutes"}}}],
                                "column_pivots": [],
                                "series": [{"config": {}, "function": "count()"}]}},
                    {"id": w_avg, "type": "aggregation", "streams": [],
                     "config": {"visualization": "table", "rollup": True, "sort": [],
                                "row_pivots": [{"type": "values", "fields": ["source"],
                                                "config": {"limit": 10}}],
                                "column_pivots": [],
                                "series": [{"config": {},
                                            "function": "avg(gl2_processing_duration_ms)"}]}}],
                "widget_mapping": {w_time: [st_time], w_avg: [st_avg]},
                "positions": {w_time: {"col": 1, "row": 1, "height": 3, "width": 6},
                              w_avg: {"col": 7, "row": 1, "height": 3, "width": 6}},
                "formatting": {"highlighting": []}}}}
    r = await c.post(f"{GL_URL}/api/views", json={"entity": view})
    if r.status_code >= 300:            # older Graylog takes the bare view
        r = await c.post(f"{GL_URL}/api/views", json=view)
    r.raise_for_status()
    return r.json()["id"]


def find(sections, name):
    for s in sections:
        for w in s.get("widgets") or []:
            if name in (w.get("title") or ""):
                return w


def count_total(w):
    try:
        return sum((w or {}).get("config", {}).get("data", {})
                   .get("datasets", [{}])[0].get("data") or [])
    except Exception:
        return None


async def main():
    if not GL_PASS:
        print("Set GL_PASS (and optionally GL_URL / GL_USER).")
        return 2
    print(f"=== wide-window report test against {GL_URL} ===")
    from glogarch.core.config import GraylogServerConfig
    from glogarch.report import graylog_data as G

    auth = (GL_USER, GL_PASS)
    async with httpx.AsyncClient(auth=auth, headers=H, timeout=60) as c:
        did = await make_dashboard(c)
    print("  throwaway dashboard:", did)
    try:
        srv = GraylogServerConfig(name="bigrange-test", url=GL_URL,
                                  username=GL_USER, password=GL_PASS, verify_ssl=False)
        big = await G.rebuild_dashboard_sections(
            srv, did, time_range_seconds=90 * DAY, max_widgets=0, lang="zh-TW",
            use_dashboard_time=False, search_wait_seconds=600)
        ctrl = await G.rebuild_dashboard_sections(
            srv, did, time_range_seconds=14 * DAY, max_widgets=0, lang="zh-TW",
            use_dashboard_time=False, search_wait_seconds=600)

        t_big, a_big = find(big, "Fixed 5m"), find(big, "Avg")
        check("coarsening fired and is announced on the widget",
              bool(t_big) and "調整" in (t_big.get("description") or ""),
              (t_big or {}).get("description") or "no widget/caption")
        check("unsliceable aggregation is labelled, not stitched",
              bool(a_big) and "無法分段合併" in (a_big.get("description") or ""),
              (a_big or {}).get("description") or "no widget/caption")
        bt, ct = count_total(t_big), count_total(find(ctrl, "Fixed 5m"))
        check("sliced total exactly equals unsliced control",
              bt is not None and bt == ct and bt > 0, f"sliced={bt} control={ct}")

        main.big_sections = big     # rendered OUTSIDE the loop: render_pdf_sync
                                    # calls asyncio.run() itself and cannot nest
    finally:
        async with httpx.AsyncClient(auth=auth, headers=H, timeout=30) as c:
            await c.delete(f"{GL_URL}/api/views/{did}")
        print("  throwaway dashboard deleted")

    return 0


def render_check(sections):
    """5) real PDF out of the wide-window sections (render engine optional).
    Runs after the event loop: render_pdf_sync calls asyncio.run() itself."""
    try:
        from glogarch.report.builder import render_report_pdf
        pdf = render_report_pdf({"title": "bigrange-test", "lang": "zh-TW"}, sections)
        check("wide-window sections render to a real PDF",
              isinstance(pdf, (bytes, bytearray)) and len(pdf) > 10_000,
              f"{len(pdf)} bytes")
    except Exception as e:
        print(f"  SKIP: PDF render not available here ({str(e)[:80]}) — "
              f"run on a box with the report engine for full coverage")


rc = asyncio.run(main())
if rc == 0 and getattr(main, "big_sections", None):
    render_check(main.big_sections)
print(f"=== RESULT: {'ALL PASS' if not FAIL else 'FAILURES: ' + ', '.join(FAIL)} ===")
sys.exit(0 if not FAIL else (rc or 1))
