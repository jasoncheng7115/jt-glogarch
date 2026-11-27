#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""The AI chat page in a real browser, against a running jt-glogarch whose AI chat
is on and connected to an LLM (added 1.34).

    UI_URL=https://<host>:8990 UI_USER=<user or Graylog token> UI_PASS=<password or "token"> \\
        python3 scripts/ui-ai-chat-test.py

UI_USER must be a Graylog login (a token works), so the chat can read Graylog as
that user. It asks two short questions through the configured LLM (a few
thousand tokens), creates two conversations and deletes them at the end. It
never changes settings. Steps:

  1. ask a question; the answer streams in (a partial bubble with a caret) and
     the progress line counts the time
  2. the answer's "Queries" panel lists each query with a range and a link to
     Graylog; the copy button copies a query
  3. leave the page mid-answer and come back: the text written so far is there
  4. rename in the header (Enter), search the list, download as Markdown
  5. Stop before the first event, then "Answer it": answered once, the question
     is not stored twice
  6. delete the conversation being followed: the page is not left busy
Prints PASS / FAIL per check and RESULT.
"""
import asyncio
import os
import sys
import tempfile
import time

BASE = os.environ.get("UI_URL", "https://localhost:8990").rstrip("/")
USER = os.environ.get("UI_USER", "")
PW = os.environ.get("UI_PASS", "")
Q1 = "過去 1 小時有幾筆事件？依 source 列出前 3 名，用表格。"
Q2 = "過去 15 分鐘有幾筆事件？"
fails = []


def check(cond, label, detail=""):
    print(f"{'PASS' if cond else 'FAIL'} {label}{(' — ' + str(detail)) if detail else ''}")
    if not cond:
        fails.append(label)


async def wait_for(page, js, timeout=300, step=0.5):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if await page.evaluate(js):
            return True
        await page.wait_for_timeout(int(step * 1000))
    return False


async def main() -> int:
    if not USER or not PW:
        print("Set UI_USER / UI_PASS (a Graylog login; a token works with UI_PASS=token).")
        return 2
    from playwright.async_api import async_playwright
    created = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        try:
            ctx = await browser.new_context(ignore_https_errors=True, viewport={"width": 1436, "height": 900},
                                            accept_downloads=True, permissions=["clipboard-read", "clipboard-write"])
            await ctx.add_init_script("localStorage.setItem('jt-glogarch-lang','zh-TW')")
            page = await ctx.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            await page.goto(BASE + "/login")
            await page.fill("input[name=username]", USER)
            await page.fill("input[name=password]", PW)
            await page.click("button[type=submit]")
            await page.wait_for_load_state("networkidle")
            await page.goto(BASE + "/ai-chat")
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(800)
            if await page.query_selector("#ai-notice:not(.hidden)"):
                print("FAIL the page asks to turn AI chat on or to sign in to Graylog: "
                      + (await page.inner_text("#ai-notice")))
                return 1

            # 1 + 3. ask, watch it stream, leave mid-answer and come back
            await page.click("[data-act=aiNewChat]")
            await page.fill("#ai-input", Q1)
            await page.click("#ai-send")
            streamed = await wait_for(page, "!!document.getElementById('ai-partial')", timeout=240)
            check(streamed, "the answer streams in (partial bubble)")
            if streamed:
                check(await page.query_selector("#ai-partial .ai-caret") is not None, "a caret marks where it writes")
                check(":" in (await page.inner_text("#ai-elapsed")), "the progress line counts the time",
                      await page.inner_text("#ai-elapsed"))
                await page.goto(BASE + "/archives")
                await page.goto(BASE + "/ai-chat")
                await page.wait_for_load_state("networkidle")
                await page.click(".ai-conv-open >> nth=0")
                back = await wait_for(page, "!!document.getElementById('ai-partial') || "
                                            "document.querySelectorAll('.ai-msg-bot:not(.ai-partial)').length > 0",
                                      timeout=30)
                check(back, "coming back mid-answer shows the text so far (or the finished answer)")
            done = await wait_for(page, "document.querySelectorAll('.ai-msg-bot:not(.ai-partial)').length > 0 "
                                        "&& !document.getElementById('ai-partial')", timeout=300)
            check(done, "the answer arrives and replaces the partial text")
            cid = await page.evaluate("_ai.conv && _ai.conv.id")
            if cid:
                created.append(cid)

            # 2. the queries panel
            toggle = await page.query_selector(".ai-calls-toggle")
            check(toggle is not None, "the answer has a Queries button")
            if toggle:
                await toggle.click()
                n = len(await page.query_selector_all(".ai-calls:not(.hidden) .ai-call"))
                links = await page.eval_on_selector_all(".ai-call-open", "e => e.map(x => x.href)")
                check(n > 0, "the panel lists the queries", n)
                check(any("/search?" in u and "rangetype=absolute" in u for u in links),
                      "a query links to the same search in Graylog", links[:1])
                await page.click(".ai-call-copy >> nth=0")
                await page.wait_for_timeout(300)
                clip = await page.evaluate("navigator.clipboard.readText()")
                check(bool(clip), "the copy button copies the query", clip[:60])

            # 4. rename, search, download
            await page.click("#ai-head [data-act=aiRenameStart]")
            await page.fill("#ai-rename", "ui-ai-chat-test renamed")
            await page.press("#ai-rename", "Enter")
            await page.wait_for_timeout(800)
            check((await page.inner_text(".ai-head-title")) == "ui-ai-chat-test renamed", "rename in the header")
            await page.fill("#ai-conv-search", "ui-ai-chat-test renamed")
            await page.wait_for_timeout(900)
            check(len(await page.query_selector_all(".ai-conv")) == 1, "the list search finds it")
            await page.fill("#ai-conv-search", "")
            await page.wait_for_timeout(600)
            async with page.expect_download() as dl:
                await page.click("#ai-head [data-act=aiExportConv]")
            d = await dl.value
            path = os.path.join(tempfile.mkdtemp(), d.suggested_filename)
            await d.save_as(path)
            text = open(path, encoding="utf-8").read()
            check(text.startswith("# ui-ai-chat-test renamed") and Q1 in text, "Download as Markdown", d.suggested_filename)

            # 5. Stop before the first event, then "Answer it"
            await page.click("[data-act=aiNewChat]")
            await page.fill("#ai-input", Q2)
            await page.click("#ai-send")
            await page.click("#ai-stop")
            got = await wait_for(page, "!_ai.busy && !!document.querySelector('.ai-unanswered')", timeout=60)
            check(got, "Stop at once: the question shows as unanswered")
            cid2 = await page.evaluate("_ai.conv && _ai.conv.id")
            if cid2:
                created.append(cid2)
                run = await page.evaluate(f"fetch('/api/ai/conversations/{cid2}').then(r => r.json()).then(d => d.run)")
                check(bool(run) and not run.get("running"), "the server stopped it too", run and run.get("error"))
                await page.click("[data-act=aiAnswerAgain]")
                answered = await wait_for(page, "document.querySelectorAll('.ai-msg-bot:not(.ai-partial)').length > 0 "
                                                "&& !_ai.busy", timeout=300)
                roles = await page.eval_on_selector_all(".ai-msg", "e => e.map(x => x.classList.contains('ai-msg-user') ? 'q' : 'a')")
                check(answered and roles == ["q", "a"], "Answer it: answered once, the question not stored twice", roles)

            # 6. delete the conversation being followed
            await page.click("[data-act=aiNewChat]")
            await page.fill("#ai-input", Q2)
            await page.click("#ai-send")
            started = await wait_for(page, "!!(_ai.conv && _ai.conv.id)", timeout=30)
            if started:
                cid3 = await page.evaluate("_ai.conv.id")
                await page.goto(BASE + "/ai-chat")
                await page.wait_for_load_state("networkidle")
                await page.click(".ai-conv-open >> nth=0")
                await page.wait_for_timeout(1200)
                await page.click(".ai-conv-del >> nth=0")
                await page.click("#confirm-buttons .btn-danger, #confirm-buttons .btn-primary")
                await page.wait_for_timeout(2500)
                st = await page.evaluate("({busy: _ai.busy, send: document.getElementById('ai-send').disabled, "
                                         "partial: !!document.getElementById('ai-partial')})")
                check(not st["busy"] and not st["send"] and not st["partial"],
                      "deleting the followed conversation frees the page", st)
                created = [c for c in created if c != cid3]
            check(not errors, "no page errors", errors[:2])
        finally:
            for cid in created:   # leave nothing behind
                try:
                    await page.evaluate(f"fetch('/api/ai/conversations/{cid}', {{method: 'DELETE'}})")
                except Exception as e:
                    print("could not delete conversation", cid, e)
            await browser.close()
    print("RESULT:", "ALL PASS" if not fails else f"{len(fails)} FAILED: {', '.join(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
