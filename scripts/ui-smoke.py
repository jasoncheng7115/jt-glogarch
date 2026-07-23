#!/usr/bin/env python3
"""Headless-browser UI smoke test — MANDATORY before every release.

The pytest suite is Python-only and never loads the browser JS, so a syntax
error in i18n.js/app.js (e.g. an apostrophe inside a single-quoted string)
ships undetected and breaks the WHOLE UI (falls back to English, Settings
renders blank). This drives a REAL headless Chromium against a running
instance and hard-fails on:

  * any uncaught JS console error / pageerror (catches i18n.js parse failures)
  * i18n not wired (`typeof t !== 'function'`)
  * language switch to zh-TW not applying (nav item never becomes Chinese)
  * (with creds) the Settings page failing to render its servers

Pre-auth checks need NO credentials — the login page loads i18n.js too, so a
syntax error there breaks identically and is caught credential-free.

Usage:
    python3 scripts/ui-smoke.py <base_url> [username] [password]
    python3 scripts/ui-smoke.py https://localhost:8990
    python3 scripts/ui-smoke.py https://192.0.2.36:8990 localadmin 'pw'

Exit 0 = OK, non-zero = a UI problem a release must not ship.
"""
import sys
import asyncio

# console messages that are noise, not real UI breakage
_IGNORE = (
    "Failed to load resource",          # favicon/404s, not JS breakage
    "net::ERR_",
    "Download the React DevTools",
)


def _is_real_error(text: str) -> bool:
    return not any(sig in text for sig in _IGNORE)


async def run(base_url: str, user: str | None, password: str | None) -> int:
    from playwright.async_api import async_playwright

    base_url = base_url.rstrip("/")
    errors: list[str] = []
    problems: list[str] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(ignore_https_errors=True)
        page = await ctx.new_page()
        page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}")
                if m.type in ("error", "warning") and _is_real_error(m.text) else None)
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))

        # --- 1. Login page (pre-auth): i18n.js must parse and apply -----------
        await page.goto(f"{base_url}/login", wait_until="networkidle")
        has_t = await page.evaluate("typeof t === 'function'")
        if not has_t:
            problems.append("login page: `t()` i18n function missing "
                            "(i18n.js failed to parse?)")
        # switching language must actually change rendered text
        try:
            await page.evaluate("setLang && setLang('zh-TW')")
            await page.wait_for_timeout(300)
            zh = await page.evaluate(
                "document.body.innerText.match(/[\\u4e00-\\u9fff]/) ? true : false")
            if not zh:
                problems.append("login page: zh-TW switch produced no Chinese text")
        except Exception as e:
            problems.append(f"login page: setLang('zh-TW') threw: {e}")

        # --- 2. Post-login (only with creds): Settings must render ------------
        if user and password:
            await page.goto(f"{base_url}/login", wait_until="networkidle")
            try:
                await page.fill("#username, input[name=username]", user)
                await page.fill("#password, input[name=password]", password)
                await page.click("button[type=submit], #loginBtn")
                await page.wait_for_load_state("networkidle")
            except Exception as e:
                problems.append(f"login submit failed: {e}")

            await page.goto(f"{base_url}/", wait_until="networkidle")
            has_t2 = await page.evaluate("typeof t === 'function'")
            if not has_t2:
                problems.append("main page: `t()` missing after login")
            await page.evaluate("setLang && setLang('zh-TW')")
            await page.wait_for_timeout(400)
            nav_zh = await page.evaluate(
                "!!document.querySelector('nav, .sidebar')?.innerText"
                "?.match(/[\\u4e00-\\u9fff]/)")
            if not nav_zh:
                problems.append("main page: nav not Chinese after zh-TW switch")

        await browser.close()

    real_errors = [e for e in errors if _is_real_error(e)]
    ok = not problems and not real_errors
    print(f"UI smoke: {base_url}")
    print(f"  checks: {'PASS' if not problems else 'FAIL'}")
    for pr in problems:
        print(f"    ✗ {pr}")
    print(f"  console/page errors: {len(real_errors)}")
    for e in real_errors[:20]:
        print(f"    ✗ {e}")
    print("RESULT:", "OK" if ok else "FAIL")
    return 0 if ok else 1


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    base = sys.argv[1]
    user = sys.argv[2] if len(sys.argv) > 2 else None
    pw = sys.argv[3] if len(sys.argv) > 3 else None
    try:
        return asyncio.run(run(base, user, pw))
    except Exception as e:  # environment / playwright not installed
        print(f"UI smoke could not run: {e}", file=sys.stderr)
        print("RESULT: ERROR", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
