#!/usr/bin/env python3
"""Standard test: full browser SIMULATION of the main user flows.

    UI_URL=https://<host>:8990 UI_USER=localadmin UI_PASS=... \
    [GL_HOST=<import-target-ip> GL_USER=admin GL_PASS=...] \
    python3 scripts/ui-sim-test.py

Where this sits: `node --check` catches syntax, `js-undefined-check` catches
missing names, `ui-smoke` catches login/i18n breakage — this walks what a USER
does: every page, the import dialog end to end (autofill, custom-dropdown
painting, clear-section auto-load), settings (derived API URL, never
overwriting typed values), and the zh-TW/en switch on every page. It asserts
the layer the user SEES — three shipped bugs each passed a check one layer
below (class vs route, <option> vs painted skin, syntax vs runtime).

With GL_* set, the clear-section check runs against the live target; without,
it only asserts the section's controls and collapsed state.
"""
import asyncio
import os
import sys

BASE = os.environ.get("UI_URL", "https://localhost:8990").rstrip("/")
USER = os.environ.get("UI_USER", "localadmin")
PW = os.environ.get("UI_PASS", "")
GL = {"host": os.environ.get("GL_HOST", ""), "user": os.environ.get("GL_USER", "admin"),
      "pw": os.environ.get("GL_PASS", "")}
PAGES = ["/", "/archives", "/jobs", "/schedules", "/notify-settings",
         "/logs", "/op-audit", "/reports", "/settings"]
FAIL = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}: {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name)


async def main():
    if not PW:
        print("Set UI_PASS (and optionally UI_URL / UI_USER / GL_*)."); return 2
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--no-sandbox"])
        pg = await (await b.new_context(ignore_https_errors=True)).new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(f"pageerror: {e}"))
        # "Failed to fetch" = a request aborted by OUR navigation between
        # pages (the language switch re-triggers page loaders) — harness noise,
        # not a product error. CSP inline-style is a known pre-existing item.
        pg.on("console", lambda m: errs.append(f"console: {m.text}")
              if m.type == "error" and "Content Security Policy" not in m.text
              and "Failed to fetch" not in m.text else None)

        await pg.goto(f"{BASE}/login", wait_until="networkidle")
        await pg.fill("#username, input[name=username]", USER)
        await pg.fill("#password, input[name=password]", PW)
        await pg.click("button[type=submit], #loginBtn")
        await pg.wait_for_load_state("networkidle")

        # 1) every page loads, renders visible content, survives a zh<->en switch
        for path in PAGES:
            n0 = len(errs)
            await pg.goto(f"{BASE}{path}", wait_until="networkidle")
            await pg.wait_for_timeout(1200)
            body = (await pg.evaluate("document.body.innerText")) or ""
            for lang in ("zh-TW", "en"):
                await pg.evaluate(f"setLang('{lang}')")
                await pg.wait_for_timeout(250)
            check(f"page {path}", len(errs) == n0 and len(body.strip()) > 50,
                  "; ".join(errs[n0:][:2]) or f"{len(body)} chars")

        # 2) import dialog end to end (what the user actually sees)
        await pg.goto(f"{BASE}/archives", wait_until="networkidle")
        await pg.wait_for_timeout(1200)
        aid = await pg.evaluate(
            "fetch('/api/archives?limit=1').then(r=>r.json()).then(d=>(d.archives||d.items||d)[0]?.id)")
        if aid:
            n0 = len(errs)
            await pg.evaluate(f"importSingle({aid!r})")
            await pg.wait_for_timeout(2500)
            host = await pg.eval_on_selector("#modal-gelf-host", "e=>e.value")
            api = await pg.eval_on_selector("#modal-target-api-url", "e=>e.value")
            check("import dialog opens, API URL derived from host",
                  (not host) or api == f"http://{host}:9000", f"host={host!r} api={api!r}")
            collapsed = await pg.evaluate(
                "document.getElementById('import-clear-target')?.open !== true")
            check("danger section collapsed by default", bool(collapsed))
            if GL["host"] and GL["pw"]:
                await pg.fill("#modal-target-api-url", f"http://{GL['host']}:9000")
                await pg.fill("#modal-target-api-user", GL["user"])
                await pg.fill("#modal-target-api-pass", GL["pw"])
                await pg.evaluate("document.getElementById('import-clear-target').open = true")
                await pg.evaluate(
                    "document.getElementById('import-clear-target').dispatchEvent(new Event('toggle'))")
                await pg.wait_for_timeout(5000)
                shown = await pg.evaluate(
                    "(document.querySelector('#clear-idx-select')?.closest('.custom-select')"
                    "?.querySelector('.custom-select-trigger')?.textContent || '').trim()")
                check("clear dropdown auto-loads and PAINTS a selection",
                      bool(shown) and shown != "—", f"visible: {shown!r}")
            check("no JS errors during import-dialog flow", len(errs) == n0,
                  "; ".join(errs[n0:][:2]))

        # 3) settings: suggestion follows host, typed value never overwritten
        await pg.goto(f"{BASE}/settings", wait_until="networkidle")
        await pg.wait_for_timeout(2000)
        if await pg.query_selector("#settings-imp-host"):
            was_suggestion = await pg.eval_on_selector(
                "#settings-imp-api-url", "e=>e.dataset.suggested === '1' || !e.value")
            was_suggestion = await pg.eval_on_selector(
                "#settings-imp-api-url", "e=>e.dataset.suggested === '1' || !e.value")
            await pg.fill("#settings-imp-host", "203.0.113.9")
            await pg.wait_for_timeout(300)
            v1 = await pg.eval_on_selector("#settings-imp-api-url", "e=>e.value")
            await pg.fill("#settings-imp-api-url", "http://keep.me:9000")
            await pg.fill("#settings-imp-host", "203.0.113.10")
            await pg.wait_for_timeout(300)
            v2 = await pg.eval_on_selector("#settings-imp-api-url", "e=>e.value")
            if was_suggestion:
                check("settings API-URL suggestion tracks host",
                      v1 == "http://203.0.113.9:9000", repr(v1))
            else:
                # a STORED value must stay put — that is the contract
                check("stored settings API URL not clobbered by host edit",
                      v1 and "203.0.113.9" not in v1, repr(v1))
            check("typed API URL never overwritten", v2 == "http://keep.me:9000", repr(v2))
        await b.close()

    print(f"=== RESULT: {'ALL PASS' if not FAIL else 'FAILURES: ' + ', '.join(FAIL)} ===")
    return 0 if not FAIL else 1

sys.exit(asyncio.run(main()))
