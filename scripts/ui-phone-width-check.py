#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Every page must fit a phone screen (added 1.34).

    UI_URL=https://<host>:8990 UI_USER=localadmin UI_PASS=... python3 scripts/ui-phone-width-check.py

Signs in (a Graylog API token works as UI_USER with UI_PASS=token), opens each
page at 390 x 844 and fails when the page is wider than the screen; a wide
table may scroll inside its own box, the page itself may not. Prints the
outermost elements that stick out. Read-only: it only opens pages.

Why: from 1.18.0 refine.css re-set the sidebar links and the content padding
after the phone rules in style.css, so a phone got the menu labels as vertical
text and pages 600-990 px wide, and nothing noticed (measured 2026-11-21).
"""
import asyncio
import os
import sys

BASE = os.environ.get("UI_URL", "https://localhost:8990").rstrip("/")
USER = os.environ.get("UI_USER", "localadmin")
PW = os.environ.get("UI_PASS", "")
WIDTH = int(os.environ.get("UI_WIDTH", "390"))
PAGES = ["/", "/archives", "/jobs", "/schedules", "/notify-settings", "/logs", "/op-audit", "/reports",
         "/alerting", "/security", "/ai-chat", "/packs", "/settings"]

OFFENDERS = """() => {
  const vw = window.innerWidth, out = [];
  for (const el of document.querySelectorAll('.content *')) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.right <= vw + 1) continue;
    const p = el.parentElement && el.parentElement.getBoundingClientRect();
    if (p && p.right > vw + 1) continue;
    let box = el.parentElement, inside = false;
    while (box && box !== document.body) {
      if (getComputedStyle(box).overflowX !== 'visible' && box.getBoundingClientRect().right <= vw + 1) { inside = true; break; }
      box = box.parentElement;
    }
    if (!inside) out.push((el.id ? '#' + el.id : el.tagName.toLowerCase()) + (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\\s+/).join('.') : '') + ' right=' + Math.round(r.right));
  }
  return {width: document.documentElement.scrollWidth, offenders: out.slice(0, 6)};
}"""


async def main() -> int:
    if not PW:
        print("Set UI_PASS (and optionally UI_URL / UI_USER / UI_WIDTH).")
        return 2
    from playwright.async_api import async_playwright
    bad = 0
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        try:
            ctx = await browser.new_context(ignore_https_errors=True, viewport={"width": WIDTH, "height": 844})
            page = await ctx.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            await page.goto(BASE + "/login")
            await page.fill("input[name=username]", USER)
            await page.fill("input[name=password]", PW)
            await page.click("button[type=submit]")
            await page.wait_for_load_state("networkidle")
            if "/login" in page.url:
                print("FAIL sign-in refused")
                return 1
            for path in PAGES:
                await page.goto(BASE + path)
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(600)
                r = await page.evaluate(OFFENDERS)
                ok = r["width"] <= WIDTH + 1
                bad += not ok
                print(f"{'PASS' if ok else 'FAIL'} {path}: {r['width']} px wide at {WIDTH}"
                      + ("" if ok else f" — {', '.join(r['offenders'])}"))
            if errors:
                bad += 1
                print("FAIL page errors:", errors[:3])
        finally:
            await browser.close()
    print("RESULT:", "ALL PASS" if not bad else f"{bad} FAILED")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
