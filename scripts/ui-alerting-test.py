#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Alerting page, clicked in a real headless Chromium against a TEST Graylog.

The jt-glogarch at UI_URL must point at a test Graylog (never production): this
seeds event definitions there, changes them through the page and checks the
result in Graylog itself.

    UI_URL=https://127.0.0.1:8996 GL_URL=http://<test-graylog>:9000 \
    GL_USER=admin GL_PASS=... [RESTART_CMD='...'] python3 scripts/ui-alerting-test.py

RESTART_CMD (optional) restarts that jt-glogarch: the test then checks that the
page asks to sign in to Graylog again (identities live in memory only) and that
signing in from the dialog works.

Prints RESULT: ALL PASS on success. Closes the browser it opened.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time

import httpx
from playwright.sync_api import sync_playwright

UI = os.environ.get("UI_URL", "https://127.0.0.1:8996").rstrip("/")
GL = os.environ.get("GL_URL", "").rstrip("/")
USER = os.environ.get("GL_USER", "admin")
PW = os.environ.get("GL_PASS", "")
RESTART = os.environ.get("RESTART_CMD", "")
PFX = "jt-e2e-ui-"
H = {"Accept": "application/json", "X-Requested-By": "jt-e2e"}
fails: list[str] = []
errors: list[str] = []


def check(cond, msg):
    print(("  PASS " if cond else "  FAIL ") + msg)
    if not cond:
        fails.append(msg)


gl = httpx.Client(base_url=GL + "/api", auth=(USER, PW), headers=H, timeout=30)


def defs():
    out = gl.get("/events/definitions", params={"per_page": 500}).json()["event_definitions"]
    return {d["title"]: d for d in out if d["title"].startswith(("[JTUIA]", "[JTUIB]"))}


def cleanup():
    for d in gl.get("/events/definitions", params={"per_page": 500}).json()["event_definitions"]:
        if d["title"].startswith(("[JTUIA]", "[JTUIB]")):
            gl.delete(f"/events/definitions/{d['id']}")
    for n in gl.get("/events/notifications", params={"per_page": 500}).json()["notifications"]:
        if n["title"].startswith(PFX):
            gl.delete(f"/events/notifications/{n['id']}")


def seed():
    def post(path, body, params=None):
        r = gl.post(path, params=params, json={"entity": body})
        if r.status_code == 400:
            r = gl.post(path, params=params, json=body)
        r.raise_for_status()
        return r.json()["id"]
    n1 = post("/events/notifications", {"title": PFX + "mail", "description": "",
              "config": {"type": "http-notification-v1", "url": "http://127.0.0.1:9/a"}})
    n2 = post("/events/notifications", {"title": PFX + "zulip", "description": "",
              "config": {"type": "http-notification-v1", "url": "http://127.0.0.1:9/b"}})
    for i in range(25):
        tag = "[JTUIA]" if i < 15 else "[JTUIB]"
        body = {"title": f"{tag} rule {i:02d}", "description": "ui test", "priority": 2, "alert": False,
                "config": {"type": "aggregation-v1", "query": f"jt_ui_never_{i}", "query_parameters": [],
                           "streams": [], "filters": [], "search_within_ms": 300000,
                           "execute_every_ms": 300000, "use_cron_scheduling": False, "group_by": [],
                           "series": [], "conditions": {"expression": None}, "event_limit": 100},
                "field_spec": {}, "key_spec": [],
                "notification_settings": {"grace_period_ms": 0, "backlog_size": 0},
                "notifications": [{"notification_id": n1, "notification_parameters": None}] if i % 3 else [],
                "storage": [{"type": "persist-to-streams-v1", "streams": ["000000000000000000000002"]}]}
        post("/events/definitions", body, params={"schedule": "false" if i % 4 == 0 else "true"})
    return n1, n2


def main():
    if not (GL and PW):
        print("GL_URL and GL_PASS are required")
        return 2
    cleanup()
    n1, n2 = seed()
    seeded = defs()
    disabled = {t for t, d in seeded.items() if d["state"] != "ENABLED"}
    print(f"seeded {len(seeded)} definitions ({len(disabled)} disabled) on {GL}")

    with sync_playwright() as p:
        b = p.chromium.launch()
        try:
            ctx = b.new_context(ignore_https_errors=True, viewport={"width": 1400, "height": 1000})
            pg = ctx.new_page()
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)

            print("[1] log in with a Graylog account, open Alerting")
            pg.goto(UI + "/login")
            pg.fill("input[name=username]", USER)
            pg.fill("input[name=password]", PW)
            pg.click("#login-btn")
            pg.wait_for_url(lambda u: "/login" not in u, timeout=20000)
            # Let the dashboard finish loading first; leaving mid-load aborts its
            # own fetches and logs "Failed to fetch" that has nothing to do with us.
            pg.wait_for_load_state("networkidle")
            # Hold the data request so the loading state can be looked at.
            held = []
            pg.route("**/api/alerting/data*", lambda route: held.append(route))
            pg.click("a[href='/alerting']")
            pg.wait_for_function("() => document.querySelector('#al-who .spinner-text')", timeout=15000)
            for _ in range(50):
                if held:
                    break
                pg.wait_for_timeout(100)
            check(bool(held), "the data request was made (and held for the check)")
            check(pg.locator("#al-defs-table td.al-loading .spinner-text").is_visible(),
                  "loading: spinner row in the table")
            check("e2e83" in pg.inner_text("#al-who"), "loading: the toolbar says which Graylog it is loading from")
            check(pg.locator("#al-batch button:disabled").count() == pg.locator("#al-batch button").count(),
                  "loading: the action buttons are disabled")
            # A spinner that is drawn but does not turn reads as a frozen page.
            angles = """() => [...document.querySelectorAll('.spinner-text')].filter(e => e.offsetParent)
                .map(e => getComputedStyle(e, '::before').transform)"""
            a1 = pg.evaluate(angles)
            pg.wait_for_timeout(230)
            a2 = pg.evaluate(angles)
            check(len(a1) >= 3 and len(a1) == len(a2) and all(x != y for x, y in zip(a1, a2)),
                  f"loading: every visible spinner is turning ({len(a1)} spinners)")
            # Turning is not enough: a track the same colour as the arc looks like
            # a still circle (the first build used text-muted vs accent, ratio 1.2).
            ratio = pg.evaluate("""() => {
                const c = getComputedStyle(document.querySelector('#al-who .spinner-text'), '::before');
                const lum = s => { const v = s.match(/[\\d.]+/g).slice(0, 3).map(x => {
                    x = x / 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); });
                    return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; };
                const a = lum(c.borderTopColor), b = lum(c.borderBottomColor);
                return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05); }""")
            check(ratio >= 2, f"loading: the spinner's arc stands out from its track (contrast {ratio:.1f})")
            for r in held:
                r.continue_()
            pg.unroute("**/api/alerting/data*")
            pg.wait_for_selector("#al-defs-table tbody tr td input[type=checkbox]", timeout=30000)
            check(USER in pg.inner_text("#al-who"), "page says changes are made as the logged-in Graylog user")
            check(pg.locator("#al-batch button:disabled").count() == 0, "loaded: the action buttons are enabled again")

            print("[1b] layout: aligned toolbar, label column, every tab pane opens with a card")
            mid = lambda sel: (lambda bb: bb["y"] + bb["height"] / 2)(pg.locator(sel).first.bounding_box())
            ys = [mid(".al-bar-left .custom-select"), mid("#al-who"), mid("#al-reload")]
            check(max(ys) - min(ys) <= 6, f"toolbar items share one centre line ({[round(y) for y in ys]})")
            xs = [pg.locator(".al-filter-label").nth(i).bounding_box()["x"] for i in range(3)]
            cx = [pg.locator(sel).bounding_box()["x"] for sel in ("#al-presets", "#al-tags", ".al-search")]
            check(max(xs) - min(xs) <= 1 and max(cx) - min(cx) <= 1,
                  "filter labels in one column, their content starts on one line")
            first = pg.evaluate("""() => ['al-pane-notifs','al-pane-health','al-pane-changes']
                .map(id => document.getElementById(id).firstElementChild.classList.contains('card'))""")
            check(all(first), f"every tab pane starts with a card the tab attaches to ({first})")
            w_name = pg.evaluate("getComputedStyle(document.querySelector('.al-title .al-name')).fontWeight")
            c_desc = pg.evaluate("getComputedStyle(document.querySelector('.al-title .al-desc')).color")
            c_name = pg.evaluate("getComputedStyle(document.querySelector('.al-title .al-name')).color")
            check(int(w_name) >= 600 and c_desc != c_name, "title and description are styled differently")

            print("[1c] clicking a title opens the definition")
            pg.locator("#al-defs-table .al-title button.al-name").first.click()
            pg.wait_for_selector("#al-detail-modal:not(.hidden) .al-kv", timeout=20000)
            body = pg.inner_text("#al-detail-body")
            check("jt_ui_never_" in body, "detail shows the definition's query, read from Graylog")
            href = pg.get_attribute("#al-detail-buttons a.al-link-btn", "href") or ""
            check("/alerts/definitions/" in href, "detail links to the definition in Graylog")
            pg.click("#al-detail-buttons button[data-act=alCloseDetail]")
            check(pg.locator("#al-detail-modal.hidden").count() == 1, "detail closes")

            print("[2] tag chip + search narrow the list")
            pg.click("#al-tags .al-chip:has-text('JTUIA')")
            rows = pg.locator("#al-defs-table tbody tr")
            check(rows.count() == 15, f"tag JTUIA shows 15 rows (got {rows.count()})")
            pg.fill("#al-q", f"-notif:{PFX}zulip rule")
            pg.wait_for_timeout(500)
            check(rows.count() == 15, "search keeps the 15 (none has zulip yet)")
            check("tags=JTUIA" in pg.url and "q=" in pg.url, "filters are in the URL")

            print("[3] shift-click selects a range, then select all matching")
            boxes = pg.locator("#al-defs-table tbody input[type=checkbox]")
            boxes.nth(1).click()
            boxes.nth(4).click(modifiers=["Shift"])
            check("4" in pg.inner_text("#al-sel-count"), "shift-click selected rows 2-5 (4 rows)")
            pg.click("button[data-act=alClearSelection]")
            pg.click("button[data-act=alSelectAllMatching]")
            check("15" in pg.inner_text("#al-sel-count"), "select all matching = 15")

            print("[4] add notification: preview, then apply")
            pg.click("button[data-act=alOpenAction][data-arg=add]")
            pg.wait_for_selector("#al-action-modal:not(.hidden)")
            pg.locator(".al-pick label", has_text=PFX + "zulip").locator("input").check()
            pg.click("button[data-act=alPreview]")
            pg.wait_for_selector(".al-summary", timeout=20000)
            check(pg.inner_text(".al-sum-change .al-sum-n").strip() == "15", "preview: 15 will change")
            n_dis = sum(1 for t in disabled if t.startswith("[JTUIA]"))
            check(str(n_dis) in pg.inner_text("#al-action-preview"),
                  f"preview says the {n_dis} disabled ones stay disabled")
            pg.click("button[data-act=alApply]")
            pg.wait_for_selector("#al-action-buttons a[href='/jobs']", timeout=60000)
            check(pg.inner_text(".al-sum-change .al-sum-n").strip() == "15", "result: 15 changed")
            pg.click("#al-action-buttons button[data-act=alCloseAction]")
            after = defs()
            check(all(n2 in [x["notification_id"] for x in after[t]["notifications"]]
                      for t in after if t.startswith("[JTUIA]")), "Graylog: all 15 have the new notification")
            check(not any(n2 in [x["notification_id"] for x in after[t]["notifications"]]
                          for t in after if t.startswith("[JTUIB]")), "Graylog: the other tag is untouched")
            check({t for t, d in after.items() if d["state"] != "ENABLED"} == disabled,
                  "Graylog: no definition changed enabled/disabled state")

            print("[5] Job History shows the batch")
            pg.goto(UI + "/jobs")
            pg.wait_for_selector("#jobs-table tbody tr")
            check("alerting" in pg.inner_text("#jobs-table tbody tr:first-child"), "newest job is the alerting batch")

            print("[6] undo it from Change history")
            pg.goto(UI + "/alerting?tab=changes")
            pg.wait_for_selector("button[data-act=alUndo]", timeout=30000)
            pg.click("button[data-act=alUndo] >> nth=0")
            pg.wait_for_selector("#al-action-modal:not(.hidden) .al-summary", timeout=20000)
            pg.click("button[data-act=alApply]")
            pg.wait_for_selector("#al-action-buttons a[href='/jobs']", timeout=60000)
            pg.click("#al-action-buttons button[data-act=alCloseAction]")
            back = defs()
            check(all([x["notification_id"] for x in back[t]["notifications"]] ==
                      [x["notification_id"] for x in seeded[t]["notifications"]] for t in seeded),
                  "Graylog: every definition is back to its seeded notifications")
            check({t for t, d in back.items() if d["state"] != "ENABLED"} == disabled, "states unchanged")

            print("[7] health check + language")
            pg.click("button[data-act=alTab][data-arg=health]")
            check(pg.locator(".al-hcard").count() >= 6, "health cards render")
            pg.evaluate("setLang('zh-TW')")
            pg.wait_for_timeout(500)
            check("告警管理" in pg.inner_text("h1"), "zh-TW title")
            check("健檢" in pg.inner_text("#al-tabs"), "zh-TW tabs")
            pg.evaluate("setLang('en')")

            if RESTART:
                print("[8] after a service restart the page asks to sign in to Graylog again")
                mark = len(errors)
                subprocess.run(RESTART, shell=True, check=True)
                for _ in range(30):
                    try:
                        if httpx.get(UI + "/api/health", verify=False, timeout=2).status_code == 200:
                            break
                    except httpx.HTTPError:
                        time.sleep(1)
                pg.goto(UI + "/alerting")
                pg.wait_for_selector("#al-signin-modal:not(.hidden)", timeout=20000)
                check(True, "sign-in dialog opened")
                check(pg.input_value("#al-signin-user") == USER, "username prefilled from the jt-glogarch login")
                pg.fill("#al-signin-pass", PW)
                pg.click("button[data-act=alSignin]")
                pg.wait_for_selector("#al-defs-table tbody tr td input[type=checkbox]", timeout=30000)
                check(USER in pg.inner_text("#al-who"), "signed in from the dialog, list loaded")
                # The browser logs the intended "sign in to Graylog" 403 as a
                # console error; that one response, in this step only, is expected.
                expected = [e for e in errors[mark:] if "status of 403" in e]
                check(len(expected) <= 2, f"only the expected sign-in 403 ({len(expected)})")
                del errors[mark:]
        finally:
            b.close()
    cleanup()
    real_errors = [e for e in errors if "favicon" not in e]
    check(not real_errors, f"no JS errors ({real_errors[:3]})")
    print("RESULT: ALL PASS" if not fails else f"RESULT: {len(fails)} FAIL")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
