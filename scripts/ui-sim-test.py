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

        # 2a2) capacity estimate is MODE-aware: GELF warns about mixing into
        # the live default set; bulk states isolation (it used to compute
        # against the default set for BOTH modes).
        if GL["host"] and GL["pw"]:
            await pg.wait_for_timeout(4000)
            cap = await pg.evaluate(
                "(document.getElementById('import-capacity-estimate')||{}).textContent||''")
            if cap.strip():
                check("GELF capacity estimate warns about live-set mixing",
                      ("正式" in cap) or ("LIVE" in cap), cap[:80])
                await pg.evaluate("() => { document.querySelector('input[name=\"import-mode\"][value=\"bulk\"]').checked = true; onImportModeChange('bulk'); }")
                await pg.wait_for_timeout(4000)
                cap2 = await pg.evaluate(
                    "(document.getElementById('import-capacity-estimate')||{}).textContent||''")
                check("bulk capacity estimate states isolation",
                      ("隔離" in cap2) or ("尚未存在" in cap2) or ("isolated" in cap2)
                      or ("does not exist" in cap2), cap2[:80])
                if "尚未存在" in cap2 or "does not exist" in cap2:
                    check("new-set estimate is sane (no '0 indices', no spurious red)",
                          ("0 個索引" not in cap2) and ("可能不足" not in cap2)
                          and ("MAY NOT FIT" not in cap2), cap2[:110])
                await pg.evaluate("() => { document.querySelector('input[name=\"import-mode\"][value=\"gelf\"]').checked = true; onImportModeChange('gelf'); }")

        # 2b) schedules: cron shown human-readable (raw only as small/tooltip)
        await pg.goto(f"{BASE}/schedules", wait_until="networkidle")
        await pg.wait_for_timeout(1500)
        rows = await pg.evaluate(
            "document.querySelectorAll('table tbody tr').length")
        if rows:
            human = await pg.evaluate(
                "!!document.querySelector('.cron-human') && "
                "(document.querySelector('.cron-human').textContent||'').trim().length > 0")
            check("schedules cron is human-readable", bool(human))

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

        # 4) record search: the tab, the plan line, and the LAYOUT on expand.
        # The layout half is the point. Expanding a hit used to shrink the
        # table: the detail row's colspan was hardcoded to 6 while the column
        # picker had hidden two columns, so the browser invented the missing
        # ones and table-layout:fixed handed them a share of the width. No
        # backend test can see that — it is pure rendered geometry — so the
        # rows here are injected through the SAME _appendHit() the real search
        # uses, which makes the check independent of what this box happens to
        # have archived.
        await pg.goto(f"{BASE}/archives", wait_until="networkidle")
        await pg.wait_for_timeout(1200)
        n0 = len(errs)
        await pg.evaluate("archTab('search')")
        await pg.wait_for_timeout(2500)
        plan = await pg.evaluate(
            "(document.getElementById('search-plan')||{}).textContent||''")
        check("record search tab opens and plans the range",
              bool(plan.strip()), plan.strip()[:80] or "empty")

        # Three hits, each carrying a marker unique to its own record. Two was
        # not enough: every hit occupies two rows, so an index computed from
        # the row count is right for hit 0 by coincidence (2×0 = 0) and wrong
        # for every hit after it — which is exactly the bug that shipped,
        # showing the reader a record they had not clicked.
        await pg.evaluate("""() => {
            document.getElementById('search-table').classList.remove('is-hidden');
            const tb = document.getElementById('search-tbody');
            tb.innerHTML = '';
            for (let n = 0; n < 3; n++) _appendHit({
                timestamp: '2026-08-23T06:22:20.000Z', source: 'router-007',
                level: '6', message: 'x'.repeat(120) + ' n=' + n,
                archive_file: 'a_' + n + '.json.gz',
                doc: {source: 'router-007', port: 443, marker: 'ROW' + n},
            });
        }""")
        await pg.wait_for_timeout(300)
        before = await pg.evaluate(
            "() => { const t = document.getElementById('search-table');"
            "  const r = t.querySelector('tbody .scol-record');"
            "  return [Math.round(t.getBoundingClientRect().width),"
            "          Math.round(r.getBoundingClientRect().width)]; }")
        # Expand the SECOND hit, not the first — see above.
        await pg.evaluate("() => document.querySelectorAll('#search-tbody "
                          "tr:not(.hit-detail) button')[1].click()")
        await pg.wait_for_timeout(400)
        opened = await pg.evaluate(
            "() => { const tb = document.getElementById('search-tbody');"
            "  const open = [...tb.children].filter(r => r.classList.contains('hit-detail')"
            "      && !r.classList.contains('is-hidden'));"
            "  return [open.length, open[0] ? [...tb.children].indexOf(open[0]) : -1,"
            "          open[0] ? open[0].textContent : '']; }")
        check("expanding a row opens THAT row's record",
              opened[0] == 1 and opened[1] == 3 and "ROW1" in opened[2],
              f"open={opened[0]} at row {opened[1]}, "
              f"marker={'ROW1' if 'ROW1' in opened[2] else opened[2][:40]!r}")
        after = await pg.evaluate(
            "() => { const t = document.getElementById('search-table');"
            "  const r = t.querySelector('tbody .scol-record');"
            "  const d = t.querySelector('tr.hit-detail:not(.is-hidden) > td');"
            "  const th = [...t.querySelectorAll('thead th')]"
            "      .filter(e => getComputedStyle(e).display !== 'none').length;"
            "  return [Math.round(t.getBoundingClientRect().width),"
            "          Math.round(r.getBoundingClientRect().width),"
            "          d ? d.colSpan : 0, th]; }")
        check("expanding a hit does not resize the table",
              abs(after[0] - before[0]) <= 1 and abs(after[1] - before[1]) <= 1,
              f"table {before[0]}->{after[0]}, record col {before[1]}->{after[1]}")
        check("detail row colspan matches the visible column count",
              after[2] == after[3], f"colspan={after[2]} visible th={after[3]}")

        # Header and body must agree on which columns exist. They did not:
        # hiding was applied per-cell, so it only reached rows that already
        # existed and every appended row kept all six — the body landed in the
        # wrong column slots and the record text was squeezed into 96px.
        align = await pg.evaluate(
            "() => { const t = document.getElementById('search-table');"
            "  const vis = e => getComputedStyle(e).display !== 'none';"
            "  const th = [...t.querySelectorAll('thead th')].filter(vis);"
            "  const td = [...t.querySelector('tbody tr').children].filter(vis);"
            "  const w = e => Math.round(e.getBoundingClientRect().width);"
            "  return [th.length, td.length,"
            "          w(t.querySelector('thead .scol-record')),"
            "          w(t.querySelector('tbody .scol-record')),"
            "          Math.round(t.getBoundingClientRect().width),"
            "          th.reduce((s, e) => s + w(e), 0)]; }")
        check("header and result rows have the same columns",
              align[0] == align[1], f"{align[0]} th vs {align[1]} td")
        check("record column is the same width in header and body",
              abs(align[2] - align[3]) <= 1, f"th={align[2]} td={align[3]}")
        check("visible columns fill the table width",
              abs(align[4] - align[5]) <= 2, f"table={align[4]} columns={align[5]}")

        # Every field, no second click: the "… N more fields" link is gone.
        shown_all = await pg.evaluate(
            "() => { const b = document.getElementById('hit-json-1');"
            "  return [(b.textContent.match(/\\\"[a-z_]+\\\":/g)||[]).length,"
            "          b.textContent.includes('more fields') ||"
            "          b.textContent.includes('個欄位（點選')]; }")
        check("expanded record shows every field with no second click",
              shown_all[0] >= 3 and not shown_all[1], repr(shown_all))
        # The two input boxes must SAY what they take, and every syntax
        # example must name the box it belongs in. Unlabelled, the pair was
        # unreadable even to us, and one example ("deny source=fw01, combine
        # both") described a syntax that silently matches nothing.
        helped = await pg.evaluate(
            "() => { const hints = [...document.querySelectorAll('.search-row .search-hint')]"
            "      .map(e => e.textContent.trim()).filter(Boolean);"
            "  const groups = [...document.querySelectorAll('.search-help-list .shelp-group')]"
            "      .map(e => e.textContent.trim()).filter(Boolean);"
            "  const both = (document.querySelector('.search-help-both')||{}).textContent||'';"
            "  return [hints.length, groups.length, both.trim().length]; }")
        check("both search boxes explain themselves, help is grouped by box",
              helped[0] == 2 and helped[1] == 2 and helped[2] > 20, repr(helped))

        # Highlighting says WHY a record is in the results — and it builds
        # HTML from a log line, so the escaping has to hold. A message
        # carrying markup must come back as text with the term marked, and
        # must not create an element.
        hl = await pg.evaluate("""() => {
            _searchTerms = ['proxy']; _searchFilters = {port: '443'};
            const tb = document.getElementById('search-tbody');
            tb.innerHTML = '';
            _appendHit({timestamp: '2026-08-23T06:22:20.000Z', source: 'router-007',
                        level: '6',
                        message: '<img src=x onerror=alert(1)> PROXY denied <b>x</b>',
                        archive_file: 'a.json.gz',
                        doc: {message: 'proxy denied', port: 443, other: 'x'}});
            document.querySelectorAll('#search-tbody tr:not(.hit-detail) button')[0].click();
            const cell = document.querySelector('#search-tbody .scol-record');
            const box = document.getElementById('hit-json-0');
            return {
                marks: cell.querySelectorAll('mark.hl').length,
                marked: [...cell.querySelectorAll('mark.hl')].map(m => m.textContent),
                injected: cell.querySelectorAll('img, b, script').length,
                text: cell.textContent,
                jsonMarks: box.querySelectorAll('mark.hl').length,
                filterKey: box.querySelectorAll('.j-key.hl-key').length,
            };
        }""")
        check("matched keyword is highlighted in the record, preserving case",
              hl["marks"] == 1 and hl["marked"] == ["PROXY"], repr(hl["marked"]))
        check("a log line containing markup is escaped, not rendered",
              hl["injected"] == 0 and "<img src=x" in hl["text"],
              f"elements={hl['injected']}")
        check("expanded record highlights the term and the matched field",
              hl["jsonMarks"] >= 2 and hl["filterKey"] == 1,
              f"marks={hl['jsonMarks']} filterKeys={hl['filterKey']}")
        check("source column is left unmarked",
              await pg.evaluate(
                  "document.querySelector('#search-tbody .scol-source')"
                  ".querySelectorAll('mark').length === 0"))

        # The download offer appears with results and carries its icons.
        dl = await pg.evaluate(
            "() => { const a = document.getElementById('search-actions');"
            "  const b = [...a.querySelectorAll('button[data-act=downloadSearch]')];"
            "  return [b.length, b.every(x => !!x.querySelector('svg')),"
            "          b.map(x => x.getAttribute('data-arg')).join(',')]; }")
        check("download controls render for CSV and JSON, with icons",
              dl[0] == 2 and dl[1] and dl[2] == "csv,jsonl", repr(dl))

        check("no JS errors during record-search flow", len(errs) == n0,
              "; ".join(errs[n0:][:2]))
        await b.close()

    print(f"=== RESULT: {'ALL PASS' if not FAIL else 'FAILURES: ' + ', '.join(FAIL)} ===")
    return 0 if not FAIL else 1

sys.exit(asyncio.run(main()))
