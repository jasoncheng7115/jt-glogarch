#!/usr/bin/env python3
"""Standard test: Cancel on a RUNNING import, clicked in a real browser.

    UI_URL=https://<host>:8990 UI_USER=localadmin UI_PASS=... \
    GL_HOST=<target-graylog-ip> GL_USER=admin GL_PASS=... \
    python3 scripts/ui-cancel-test.py

Why a browser and not a route test: the shipped bug (v1.13.70) was
`customConfirm(...)` — undefined, syntactically perfect, invisible to
node --check and pytest — so the Cancel button died on its FIRST line and
silently did nothing while the API, the flow-control flag and every unit test
were fine. Only a real click reaches that layer.

Asserts: the confirm modal opens, the job leaves running/pending, and the
final status is `cancelled` (not `completed` — a cancelled import recorded as
completed at 100% reads as data loss).
"""
import asyncio
import os
import json
import re
import sys

BASE = os.environ.get("UI_URL", "https://localhost:8990").rstrip("/")
USER = os.environ.get("UI_USER", "localadmin")
PW = os.environ.get("UI_PASS", "")
GL = {"host": os.environ.get("GL_HOST", ""), "user": os.environ.get("GL_USER", "admin"),
      "pw": os.environ.get("GL_PASS", "")}


async def main():
    if not PW or not GL["host"] or not GL["pw"]:
        print("Set UI_PASS, GL_HOST, GL_PASS (and optionally UI_URL/UI_USER/GL_USER).")
        return 2
    from playwright.async_api import async_playwright
    errs = []
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--no-sandbox"])
        pg = await (await b.new_context(ignore_https_errors=True)).new_page()
        pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.goto(f"{BASE}/login", wait_until="networkidle")
        await pg.fill("#username, input[name=username]", USER)
        await pg.fill("#password, input[name=password]", PW)
        await pg.click("button[type=submit], #loginBtn")
        await pg.wait_for_load_state("networkidle")
        await pg.goto(f"{BASE}/archives", wait_until="networkidle")
        await pg.wait_for_timeout(1500)

        # Pick the LARGEST archive: a small one finishes before the click and
        # the run degenerates into cancelling a finished job (vacuous pass).
        aid = await pg.evaluate(
            "fetch('/api/archives?limit=200').then(r=>r.json())"
            ".then(d=>{const a=(d.archives||d.items||d);"
            "a.sort((x,y)=>(y.message_count||0)-(x.message_count||0));return a[0].id})")
        await pg.evaluate(f"importSingle({aid!r})")
        await pg.wait_for_timeout(1500)
        await pg.fill("#modal-gelf-host", GL["host"])
        await pg.fill("#modal-target-api-url", f"http://{GL['host']}:9000")
        await pg.fill("#modal-target-api-user", GL["user"])
        await pg.fill("#modal-target-api-pass", GL["pw"])
        await pg.click("#modal-import-btn")

        jid = ""
        for _ in range(15):
            await pg.wait_for_timeout(700)
            msg = await pg.evaluate(
                "(document.getElementById('modal-import-result')||{}).textContent||''")
            m = re.search(r"[:：]\s*([0-9a-f]{8})", msg or "")
            if m:
                jobs = await pg.evaluate("fetch('/api/jobs?limit=10').then(r=>r.json())")
                arr = (jobs.get("jobs") or jobs.get("items")) if isinstance(jobs, dict) else jobs
                jid = next((str(j.get("id")) for j in (arr or [])
                            if str(j.get("id", "")).startswith(m.group(1))), "")
                if jid:
                    break
        if not jid:
            # Fallback: the dialog text format can change; the job list is
            # authoritative. Any RUNNING import right after we pressed Start
            # is ours (the per-archive lock forbids a second one anyway).
            jobs = await pg.evaluate("fetch('/api/jobs?limit=10').then(r=>r.json())")
            arr = (jobs.get("jobs") or jobs.get("items")) if isinstance(jobs, dict) else jobs
            jid = next((str(j.get("id")) for j in (arr or [])
                        if j.get("job_type") == "import"
                        and j.get("status") == "running"), "")
        print("  running import job:", jid or "(none)")
        if not jid:
            print("  FAIL: import never started"); await b.close(); return 1

        # cancel IMMEDIATELY — the REAL user path: button, then confirm modal
        await pg.evaluate("document.getElementById('import-cancel-btn').click()")
        await pg.wait_for_timeout(700)
        clicked = await pg.evaluate("""() => {
            const m = document.getElementById('global-confirm-modal');
            if (!m) return 'no-modal';
            const btn = m.querySelector('.btn-danger,.btn-primary,button');
            if (!btn) return 'no-button';
            btn.click(); return 'ok';
        }""")
        print("  confirm modal:", clicked)

        status = None
        for _ in range(30):
            await pg.wait_for_timeout(2000)
            j = await pg.evaluate(f"fetch('/api/jobs/{jid}').then(r=>r.json())")
            status = j.get("status")
            if status not in ("running", "pending"):
                break
        print("  final status:", status)
        for e in errs:
            print("  pageerror:", e)
        ok = clicked == "ok" and status == "cancelled" and not errs
        print("  import cancel:", "PASS" if ok else
              f"FAIL (status={status!r} — cancelled required; "
              f"'completed' means the cancel was recorded dishonestly)")

        ok_export = await _export_cancel(pg, errs)
        ok = ok and ok_export
        print("  RESULT:", "ALL PASS" if ok else "FAILURES")
        await b.close()
        return 0 if ok else 1


async def _api(pg, path, method="GET", body=None):
    return await pg.evaluate(
        "(a) => fetch(a.path, {method: a.method, headers: {'Content-Type':'application/json'},"
        " body: a.body}).then(r => r.json())",
        {"path": path, "method": method, "body": json.dumps(body) if body is not None else None})


async def _export_cancel(pg, errs):
    """Cancel a real OpenSearch-direct EXPORT mid-run — the customer's scenario.

    Until this release, the script only cancelled an IMPORT, and export had its own
    cancel handling with its own defects: a cancelled run finished "completed,
    100%, 0 records", and on the flag path a half-scanned hour was recorded as a
    complete archive. Asserts the row, the badge, the live page AND that only
    whole-hour archives were added.
    """
    print("=== export cancel (OpenSearch-direct) ===")
    before = (await _api(pg, "/api/archives?page_size=1")).get("total", 0)
    r = await _api(pg, "/api/export", "POST", {"mode": "opensearch", "days": 2})
    jid = r.get("job_id")
    if not jid:
        print("  FAIL: could not start an export:", r); return False
    print(f"  export job {jid}")

    # Wait until at least one WHOLE hour has been closed and recorded, then
    # cancel while the next hour is in progress. The hour in progress is
    # discarded on cancel by design (recording it as complete is the data-loss
    # bug), so cancelling before any hour has closed would legitimately leave
    # 0 archives and 0 records — and prove nothing.
    live = 0
    j = {}
    for _ in range(200):
        await pg.wait_for_timeout(3000)
        j = await _api(pg, f"/api/jobs/{jid}")
        live = j.get("messages_done") or 0
        if j.get("status") != "running":
            print(f"  FAIL: job left running before cancel: {j.get('status')} — "
                  "nothing left to export on this target?"); return False
        now = (await _api(pg, "/api/archives?page_size=1")).get("total", 0)
        if now > before and live > 0:
            break
    else:
        print("  FAIL: no whole hour was recorded within the wait — cannot test a mid-run cancel")
        return False
    denominator = j.get("messages_total") or 0
    await _api(pg, f"/api/jobs/{jid}/cancel", "POST")
    for _ in range(100):
        await pg.wait_for_timeout(3000)
        j = await _api(pg, f"/api/jobs/{jid}")
        if j.get("status") != "running":
            break
    after = (await _api(pg, "/api/archives?page_size=1")).get("total", 0)
    added = await _api(pg, f"/api/archives?page_size={min(500, max(1, after - before))}"
                           "&sort=created_at&order=desc") \
        if after > before else {"items": []}
    partial = [a for a in (added.get("items") or [])
               if a.get("time_from") and a.get("time_to")
               and (a["time_from"][14:16] != "00" or a["time_to"][14:16] != "00")]

    status, done, pct = j.get("status"), j.get("messages_done") or 0, j.get("progress_pct")
    note, res = j.get("error_message") or "", j.get("result") or {}
    await pg.goto(f"{BASE}/jobs", wait_until="networkidle")
    await pg.wait_for_timeout(1500)
    badge = await pg.evaluate(
        "(id) => { const row=[...document.querySelectorAll('tr')].find(tr => tr.textContent.includes(id));"
        "  const s=row && row.querySelector('[class^=status-]'); return s ? s.className : null; }", jid[:8])
    chip = await pg.evaluate(
        "(id) => { const row=[...document.querySelectorAll('tr')].find(tr => tr.textContent.includes(id));"
        "  return !!(row && row.querySelector('.cov-ok')); }", jid[:8])

    checks = {
        "status is cancelled": status == "cancelled",
        "count kept (not 0)": done > 0,
        "denominator kept (not overwritten with the numerator)":
            (j.get("messages_total") or 0) == denominator and denominator > done,
        "progress not snapped to 100": pct is None or pct < 100,
        "note explains the cancel": "Cancelled by user" in note,
        "no 'Covered all' claim": "Covered all" not in note and "index_sets_covered" not in res,
        "badge is cancelled": badge == "status-cancelled",
        "no green coverage chip": not chip,
        "archives were recorded before the cancel": after > before,
        "no partial-hour archive recorded": not partial,
        "no page errors": not errs,
    }
    print(f"  live={live:,} final: status={status!r} done={done:,} total={j.get('messages_total')} "
          f"pct={pct} archives +{after - before}")
    for k, v in checks.items():
        print(f"  {'PASS' if v else 'FAIL'}: {k}")
    return all(checks.values())

sys.exit(asyncio.run(main()))
