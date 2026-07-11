"""Report content sources.

Phase 1 (native): capture a live Graylog dashboard as an image via a headless
browser that logs in through the Graylog web form (version-agnostic; needs
Graylog *web* credentials, since API tokens are not accepted by the login form).

Phase 2 (data): build branded chart sections from data jt-glogarch can read
reliably via API/DB — its own archive/job/audit statistics, plus a best-effort
list of Graylog dashboards for the picker.
"""

from __future__ import annotations

import base64
from datetime import datetime, timedelta

import httpx

from glogarch.report import builder
from glogarch.utils.logging import get_logger

log = get_logger("report.graylog_data")

# Max viewport height (CSS px) used when growing the window to render a whole
# dashboard for a screenshot. Doubled by device_scale_factor=2, so 12000 → a
# 24000px-tall image; large enough for very tall dashboards, bounded so an
# extreme one can't exhaust memory.
_MAX_CAPTURE_VIEWPORT = 12000

# Declared capture width (CSS px). Headless Chromium renders at exactly this
# width on EVERY host — independent of the machine's physical display — so the
# capture is identical across dev and customer deployments. The report is
# PORTRAIT A4 (~178mm content width), so a WIDER capture is scaled down MORE and
# its text ends up SMALLER on the page; 1600 keeps a normal desktop layout while
# leaving on-page text a touch larger than a wider grab would. At
# device_scale_factor=2 that is ~3060px across A4 → ~440 DPI, well above the
# 300 DPI that prints cleanly.
_CAPTURE_WIDTH = 1600
_CAPTURE_SCALE = 2

_MONTH_NAMES = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], start=1)}


def _parse_caption(text):
    """react-day-picker month caption 'July 2026' -> (2026, 7); None if unknown."""
    import re
    m = re.search(r"([A-Za-z]+)\s+(\d{4})", text or "")
    if not m:
        return None
    mo = _MONTH_NAMES.get(m.group(1))
    return (int(m.group(2)), mo) if mo else None


# --------------------------------------------------------------------------
# Graylog dashboards
# --------------------------------------------------------------------------

async def list_dashboards(server) -> list[dict]:
    """List Graylog dashboards (id + title) for the report-config picker."""
    auth = _basic_auth(server)
    out = []
    try:
        async with httpx.AsyncClient(verify=server.verify_ssl, timeout=15.0) as c:
            r = await c.get(f"{server.url.rstrip('/')}/api/dashboards",
                            params={"per_page": 500}, auth=auth,
                            headers={"Accept": "application/json"})
            if r.status_code == 200:
                data = r.json()
                for v in (data.get("elements") or data.get("views") or []):
                    out.append({"id": v.get("id"), "title": v.get("title") or v.get("id")})
    except Exception as e:
        log.warning("list_dashboards failed", error=str(e))
    return out


async def list_dashboard_tabs(server, dashboard_id: str) -> list[dict]:
    """List a dashboard's tabs (state_id + tab title) for the report picker."""
    auth = _basic_auth(server)
    out = []
    try:
        async with httpx.AsyncClient(verify=server.verify_ssl, timeout=15.0) as c:
            v = (await c.get(f"{server.url.rstrip('/')}/api/views/{dashboard_id}",
                             auth=auth, headers={"Accept": "application/json"})).json()
            for sid, s in (v.get("state") or {}).items():
                title = (((s.get("titles") or {}).get("tab") or {}).get("title")) or ""
                out.append({"id": sid, "title": title})
    except Exception as e:
        log.warning("list_dashboard_tabs failed", error=str(e))
    return out


def _basic_auth(server):
    if server.auth_token:
        return httpx.BasicAuth(server.auth_token, "token")
    return httpx.BasicAuth(server.username or "", server.password or "")


async def get_graylog_version(server) -> str:
    """Best-effort Graylog version string for the report meta line."""
    try:
        async with httpx.AsyncClient(verify=server.verify_ssl, timeout=10.0) as c:
            r = await c.get(f"{server.url.rstrip('/')}/api/system",
                            auth=_basic_auth(server), headers={"Accept": "application/json"})
            if r.status_code == 200:
                return (r.json().get("version") or "").split("+")[0]
    except Exception:
        pass
    return ""


async def capture_dashboard_png(
    server, dashboard_id: str, *, web_username: str, web_password: str,
    time_range_seconds: int = 86400, wait_ms: int = 6000,
    abs_from=None, abs_to=None,
) -> tuple[bytes | None, str]:
    """Log into the Graylog web UI with the given web credentials and screenshot
    a dashboard. Returns (PNG bytes, "") on success or (None, reason) on failure
    so the caller can show WHY the capture failed instead of a generic note.

    When abs_from/abs_to (datetimes) are given, the dashboard's global time range
    is best-effort overridden to that absolute window before capture so the
    screenshot honours the report's time-range / snap-to-midnight setting."""
    from playwright.async_api import async_playwright
    base = server.url.rstrip("/")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
            ctx = await browser.new_context(ignore_https_errors=True,
                                            viewport={"width": _CAPTURE_WIDTH, "height": 1000},
                                            device_scale_factor=_CAPTURE_SCALE)
            page = await ctx.new_page()
            try:
                user_sel = 'input[name="username"], input#username, input[placeholder*="sername"]'
                pass_sel = 'input[name="password"], input#password, input[type="password"]'
                # Go straight to the dashboard. If not authenticated, Graylog
                # redirects to login with a returnTo, so after we log in it
                # bounces us BACK to the dashboard automatically — no fragile
                # second navigation that can race the session being set.
                await page.goto(f"{base}/dashboards/{dashboard_id}", wait_until="domcontentloaded")
                try:
                    await page.wait_for_selector(user_sel, timeout=15000)
                except Exception:
                    return None, ("Graylog login form not found — is the web URL correct "
                                  f"and reachable? ({base})")
                await page.fill(user_sel, web_username)
                await page.fill(pass_sel, web_password)
                # Submit + press Enter (some Graylog builds only submit on Enter).
                try:
                    await page.click('button[type="submit"], button:has-text("Sign in"), button:has-text("登入")', timeout=3000)
                except Exception:
                    pass
                await page.press(pass_sel, "Enter")
                # Success signal = the dashboard grid mounts. Waiting for the grid
                # directly is far more reliable than watching the login form
                # detach (some Graylog builds keep a hidden input, so the detach
                # never fires even on a good login).
                try:
                    await page.wait_for_selector(
                        ".react-grid-layout, [data-testid='dashboard'], .widget-list",
                        timeout=30000)
                except Exception:
                    # Grid never appeared. Still on the login form → bad creds;
                    # otherwise the dashboard just didn't render in time.
                    if await page.query_selector(user_sel):
                        return None, ("Graylog web login did not complete — check the "
                                      "web username/password (these are the Graylog UI "
                                      "login, not the API token).")
                    return None, "Dashboard did not finish loading after login (timed out)."
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(wait_ms)
                # Apply the report's absolute time window to the LIVE dashboard so
                # the screenshot matches the report's range / snap-to-midnight
                # setting (best-effort; falls back to the dashboard's own range).
                if abs_from is not None and abs_to is not None:
                    ok = await _apply_absolute_override(page, abs_from, abs_to)
                    if ok:
                        await page.wait_for_timeout(3000)   # let widgets refetch
                        try:
                            await page.wait_for_load_state("networkidle", timeout=25000)
                        except Exception:
                            pass
                # Graylog lazy-renders each widget's chart ONLY while it is inside
                # the viewport (IntersectionObserver). With a normal-height viewport
                # an element screenshot of the tall grid therefore captures every
                # off-screen widget as BLANK. The reliable fix is to grow the
                # viewport tall enough to hold the whole grid at once — then every
                # widget is "in view", renders, and the single screenshot is
                # complete. (Scrolling first still helps kick off data fetches.)
                grid_sel = None
                for sel in (".react-grid-layout", "[data-testid='dashboard']", ".widget-list"):
                    if await page.query_selector(sel):
                        grid_sel = sel
                        break
                await _autoscroll_dashboard(page)
                grid_h = 0
                if grid_sel:
                    try:
                        grid_h = await page.evaluate(
                            "(s)=>{const g=document.querySelector(s);return g?g.scrollHeight:0;}", grid_sel)
                    except Exception:
                        grid_h = 0
                if grid_h and grid_h > 900:
                    # Cap so an enormous dashboard can't blow Chromium's max image
                    # size (device_scale_factor=2 doubles the pixel height).
                    tall = min(int(grid_h) + 400, _MAX_CAPTURE_VIEWPORT)
                    if grid_h + 400 > _MAX_CAPTURE_VIEWPORT:
                        log.warning("dashboard taller than capture cap; bottom may clip",
                                    dashboard=dashboard_id, grid_h=grid_h, cap=_MAX_CAPTURE_VIEWPORT)
                    try:
                        await page.set_viewport_size({"width": _CAPTURE_WIDTH, "height": tall})
                    except Exception:
                        pass
                    await page.evaluate("()=>window.scrollTo(0,0)")
                    await page.wait_for_timeout(1500)
                try:
                    await page.wait_for_load_state("networkidle", timeout=25000)
                except Exception:
                    pass
                # Give every widget's chart a moment to finish drawing now that
                # they are all on-screen.
                await page.wait_for_timeout(4000)
                grid = await page.query_selector(grid_sel) if grid_sel else None
                if grid:
                    png = await grid.screenshot()
                else:
                    png = await page.screenshot(full_page=True)
                if not png:
                    return None, "Screenshot produced no image."
                return png, ""
            finally:
                await browser.close()
    except Exception as e:
        log.warning("capture_dashboard_png failed", dashboard=dashboard_id, error=str(e))
        return None, f"Capture error: {e}"


async def _apply_absolute_override(page, dt_from, dt_to) -> bool:
    """Best-effort: drive Graylog's global time-range picker to an ABSOLUTE
    window (dt_from..dt_to) so a screenshot reflects the report's time range.

    This automates Graylog's own React (react-day-picker) date picker, so it is
    inherently version-sensitive — every step is guarded and ANY failure returns
    False, in which case the caller just captures the dashboard's own range.
    Requires TRUSTED events (Playwright .click()/.fill()); programmatic JS clicks
    do not update the controlled React inputs. Assumes an English Graylog UI."""
    import re as _re
    try:
        # A fresh browser context shows the global override as "No Override".
        await page.get_by_text("No Override", exact=True).first.click(timeout=6000)
        await page.wait_for_timeout(700)
        await page.get_by_text("Absolute", exact=True).first.click(timeout=6000)
        await page.wait_for_timeout(1000)
        months = page.locator(".rdp-month")
        if await months.count() < 1:
            return False
        to_idx = 1 if await months.count() > 1 else 0
        prevs = page.locator(".rdp-button_previous")
        nexts = page.locator(".rdp-button_next")

        async def _goto_month(cal_idx, target):
            # Navigate calendar cal_idx to target month by reading its caption and
            # stepping prev/next; self-correcting, bounded so it can't spin.
            for _ in range(24):
                cap = (await months.nth(cal_idx).locator("[class*=caption]").first
                       .inner_text()).strip()
                cur = _parse_caption(cap)
                if cur is None:
                    return False
                if cur == (target.year, target.month):
                    return True
                btn = prevs if (target.year, target.month) < cur else nexts
                idx = cal_idx if await btn.count() > cal_idx else 0
                if await btn.count() <= idx:
                    return False
                await btn.nth(idx).click()
                await page.wait_for_timeout(220)
            return False

        async def _click_day(cal_idx, day):
            btns = months.nth(cal_idx).locator("button.rdp-day_button")
            for i in range(await btns.count()):
                b = btns.nth(i)
                if (await b.inner_text()).strip() != str(day):
                    continue
                cls = (await b.get_attribute("class")) or ""
                outside = await b.evaluate(
                    "e=>{const c=e.closest('td,[role=gridcell]');return (c&&c.className||'')+' '+(e.className||'');}")
                if "outside" in cls or "outside" in (outside or ""):
                    continue
                await b.click()
                return True
            return False

        if not await _goto_month(0, dt_from):
            return False
        if not await _goto_month(to_idx, dt_to):
            return False
        if not await _click_day(0, dt_from.day):
            return False
        if not await _click_day(to_idx, dt_to.day):
            return False
        # Six number inputs in DOM order: from H/M/S then to H/M/S.
        nums = page.locator("input[type=number]")
        if await nums.count() >= 6:
            for i, v in enumerate([dt_from.hour, dt_from.minute, dt_from.second,
                                   dt_to.hour, dt_to.minute, dt_to.second]):
                await nums.nth(i).fill(str(v))
        await page.wait_for_timeout(400)
        upd = page.get_by_role("button", name=_re.compile("Update time range", _re.I))
        if await upd.count() == 0 or await upd.first.is_disabled():
            return False
        await upd.first.click()
        await page.wait_for_timeout(1500)
        # Confirm it took: the global-override control no longer reads "No Override".
        still_default = await page.get_by_text("No Override", exact=True).count()
        return still_default == 0
    except Exception as e:
        log.warning("time-range override failed; using dashboard default range",
                    error=str(e))
        return False


async def _autoscroll_dashboard(page):
    """Scroll the dashboard through its full height so Graylog renders every
    lazily-mounted widget before we screenshot the grid. Scrolls whichever
    element actually owns the overflow (window or an inner container)."""
    try:
        await page.evaluate("""async () => {
            const sleep = ms => new Promise(r => setTimeout(r, ms));
            function scroller() {
                let best = document.scrollingElement || document.documentElement;
                let bestDiff = best.scrollHeight - best.clientHeight;
                for (const el of document.querySelectorAll('*')) {
                    const oy = getComputedStyle(el).overflowY;
                    if (oy !== 'auto' && oy !== 'scroll') continue;
                    const diff = el.scrollHeight - el.clientHeight;
                    if (diff > bestDiff) { best = el; bestDiff = diff; }
                }
                return best;
            }
            const el = scroller();
            // Step through the whole height in viewport-sized chunks so EVERY
            // widget passes through the viewport and fetches its data (Graylog
            // loads widget data lazily on mount). Jumping straight to the bottom
            // leaves the middle widgets blank.
            const step = Math.max(300, Math.floor(el.clientHeight * 0.75));
            let pos = 0;
            for (let i = 0; i < 120; i++) {
                el.scrollTo(0, pos); window.scrollTo(0, pos);
                await sleep(450);
                if (pos >= el.scrollHeight) break;
                pos += step;
            }
            el.scrollTo(0, el.scrollHeight); window.scrollTo(0, el.scrollHeight);
            await sleep(900);
            el.scrollTo(0, 0); window.scrollTo(0, 0);
            await sleep(500);
        }""")
    except Exception:
        pass


def slice_tall_png(png: bytes, first_ratio: float = 1.28, rest_ratio: float = 1.42) -> list[str]:
    """Split a tall dashboard screenshot into page-sized data-URIs. The FIRST
    slice is shorter (first_ratio) because it shares its page with the section
    title + description; later slices sit on their own page (rest_ratio). Ratios
    are height:width vs the A4 content width (~178mm). Returns [data-uri, ...]."""
    from io import BytesIO
    try:
        from PIL import Image
    except Exception:
        return [png_to_data_uri(png)]
    im = Image.open(BytesIO(png))
    w, h = im.size
    first_h = max(1, int(w * first_ratio))
    rest_h = max(1, int(w * rest_ratio))
    if h <= int(first_h * 1.06):          # fits one page (with a little slack)
        return [png_to_data_uri(png)]
    # Snap each page cut to a GAP between widget rows so no widget is split across
    # pages. A gap is horizontally uniform (the dashboard background), whereas a
    # row crossing a chart/table/text has a wide spread of pixel values. We
    # measure per-row spread on a narrow grayscale strip (no numpy needed) and,
    # for each target height, cut at the most-uniform row just above it.
    row_spread = None
    try:
        COLS = 40
        strip = list(im.convert("L").resize((COLS, h)).getdata())
        row_spread = [0] * h
        for r in range(h):
            seg = strip[r * COLS:(r + 1) * COLS]
            row_spread[r] = max(seg) - min(seg)
    except Exception:
        row_spread = None

    def _snap(target, floor):
        """Nearest clean (min-spread) cut row in (floor, target]; falls back to
        target when spread data is unavailable."""
        if not row_spread:
            return min(target, h)
        hi = min(target, h - 1)
        lo = max(floor, target - int(w * 0.18))   # search window above target
        if lo >= hi:
            return min(target, h)
        best_r, best_s = hi, row_spread[hi]
        for r in range(hi, lo - 1, -1):
            if row_spread[r] < best_s:
                best_s, best_r = row_spread[r], r
                if best_s == 0:
                    break
        return best_r

    slices = []
    y = 0
    first = True
    while y < h:
        ph = first_h if first else rest_h
        target = y + ph
        if target >= h:
            cut = h
        else:
            cut = _snap(target, y + int(w * 0.35))   # keep slices from getting tiny
            if cut <= y:
                cut = min(target, h)
        part = im.crop((0, y, w, min(cut, h)))
        buf = BytesIO()
        part.save(buf, format="PNG")
        slices.append(png_to_data_uri(buf.getvalue()))
        if cut >= h:
            break
        y = cut
        first = False
    return slices


def png_to_data_uri(png: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


# --------------------------------------------------------------------------
# Phase 2 "rebuild" — reconstruct a Graylog dashboard from real widget data
# (execute its search via the Views API, poll the async job, map each pivot to
# one of our branded Chart.js charts / tables / single values).
# --------------------------------------------------------------------------

async def rebuild_dashboard_sections(server, dashboard_id: str, *,
                                     time_range_seconds: int = 86400,
                                     max_widgets: int = 20,
                                     lang: str = "zh-TW",
                                     tabs: list | None = None,
                                     message_rows: int = 20,
                                     message_max_cols: int = 0,
                                     bar_horizontal: bool = False,
                                     heatmap_values: bool = False,
                                     use_dashboard_time: bool = True,
                                     abs_from: str | None = None,
                                     abs_to: str | None = None,
                                     snap_midnight: bool = False) -> list[dict]:
    """Return report `sections` reconstructed from a Graylog dashboard's widgets.
    Empty list on failure (caller degrades)."""
    auth = _basic_auth(server)
    base = server.url.rstrip("/")
    hdr = {"Accept": "application/json", "Content-Type": "application/json", "X-Requested-By": "jt-glogarch"}
    # max_widgets <= 0 (or unset) means "no limit — render every widget".
    cap = max_widgets if (max_widgets and max_widgets > 0) else 10 ** 9
    try:
        async with httpx.AsyncClient(verify=server.verify_ssl, timeout=60.0) as c:
            view = (await c.get(f"{base}/api/views/{dashboard_id}", auth=auth, headers=hdr)).json()
            title = view.get("title") or dashboard_id
            # Which fields are date-typed → so min/max/latest(<date field>) metrics
            # render as datetimes, and message-list date columns format locally.
            date_fields = await _fetch_date_fields(c, base, auth, hdr, time_range_seconds)
            sid = view.get("search_id")
            states = view.get("state") or {}
            if not sid or not states:
                return []
            # Execute the dashboard's search and poll the async job to COMPLETION
            # (a heavy multi-tab dashboard finishes tab-by-tab; a partial result
            # would miss some tabs' widgets).
            # Respect each widget's OWN time range (match Graylog exactly) by
            # NOT sending a global timerange override. Only override when the
            # report explicitly asks for a single global range.
            async def _exec_and_wait(body):
                ex = (await c.post(f"{base}/api/views/search/{sid}/execute", auth=auth,
                                   headers=hdr, json=body)).json()
                res = ex.get("results") or {}
                jb = ex.get("id")
                dn = (ex.get("execution") or {}).get("done")
                w8 = 0.0
                # Heavy dashboards (many widgets) + a global override can take a
                # while; poll up to 300s and keep the LATEST partial results each
                # round so a timeout still yields as-complete-as-possible data
                # (an early cut-off previously left aggregations like the geo map
                # with only a couple of rows).
                while not dn and jb and w8 < 300:
                    await __import_asyncio_sleep(2.0)
                    w8 += 2.0
                    pj = (await c.get(f"{base}/api/views/search/status/{jb}", auth=auth, headers=hdr)).json()
                    dn = (pj.get("execution") or {}).get("done")
                    latest = pj.get("results")
                    if latest:
                        res = latest
                if not dn:
                    log.warning("dashboard search did not finish in time",
                                dashboard=dashboard_id, waited=w8)
                return res

            # Time range priority: an explicit absolute window (e.g. the
            # snap-to-midnight schedule option) > widget's own range > a single
            # relative range applied to every widget.
            if abs_from and abs_to:
                exec_body = {"global_override": {"timerange":
                             {"type": "absolute", "from": abs_from, "to": abs_to}}}
            elif use_dashboard_time:
                exec_body = {}
            else:
                exec_body = {"global_override": {"timerange": {"type": "relative", "range": time_range_seconds}}}
            results = await _exec_and_wait(exec_body)

            # Per-widget snap-to-midnight (used together with use_dashboard_time):
            # keep each widget's OWN duration but move its window to end at today
            # 00:00 local. Only whole-day durations snap — a "last 2 hours" widget
            # is left exactly as configured. We re-execute the search once per
            # distinct whole-day duration (an absolute [midnight-D, midnight]
            # window) and copy those results over the base ones.
            if snap_midnight and use_dashboard_time and not (abs_from and abs_to) and results:
                from datetime import datetime, timezone, timedelta
                midnight_utc = (datetime.now().astimezone()
                                .replace(hour=0, minute=0, second=0, microsecond=0)
                                .astimezone(timezone.utc))
                fmt = "%Y-%m-%dT%H:%M:%S.000Z"
                dur_of = {}   # (state_id, search_type_id) -> duration seconds
                for st_id, st in results.items():
                    for stype_id, sres in ((st.get("search_types") or {}).items()):
                        eff = sres.get("effective_timerange") or {}
                        f, t = _parse_ts(eff.get("from")), _parse_ts(eff.get("to"))
                        if f and t and t > f:
                            dur_of[(st_id, stype_id)] = round((t - f).total_seconds())
                day_durs = sorted({d for d in dur_of.values() if d > 0 and d % 86400 == 0})
                for d in day_durs:
                    body = {"global_override": {"timerange": {"type": "absolute",
                            "from": (midnight_utc - timedelta(seconds=d)).strftime(fmt),
                            "to": midnight_utc.strftime(fmt)}}}
                    try:
                        snapped = await _exec_and_wait(body)
                    except Exception:
                        continue
                    for (st_id, stype_id), dd in dur_of.items():
                        if dd != d:
                            continue
                        src = ((snapped.get(st_id) or {}).get("search_types") or {}).get(stype_id)
                        if src is not None:
                            results.setdefault(st_id, {}).setdefault("search_types", {})[stype_id] = src

            # Trend: numeric widgets with `trend` enabled compare the current
            # value with the immediately preceding equal-length window. The main
            # execute returns only the current period, so query the previous
            # window (absolute) for each such widget and stash the prior value.
            trend_prev = {}
            for state_id, state in states.items():
                for w in (state.get("widgets") or []):
                    wc = w.get("config") or {}
                    if wc.get("visualization") != "numeric":
                        continue
                    if not (wc.get("visualization_config") or {}).get("trend"):
                        continue
                    wid = w.get("id")
                    wmap = (state.get("widget_mapping") or {}).get(wid) or [wid]
                    st_res = ((results.get(state_id) or {}).get("search_types")) or {}
                    cur = next((st_res[s] for s in wmap if s in st_res), None)
                    if not cur:
                        continue
                    eff = cur.get("effective_timerange") or {}
                    f, t = _parse_ts(eff.get("from")), _parse_ts(eff.get("to"))
                    if not f or not t or t <= f:
                        continue
                    dur = t - f
                    pf, pt = f - dur, f
                    fmt = "%Y-%m-%dT%H:%M:%S.000Z"
                    body = {"global_override": {"timerange": {"type": "absolute",
                            "from": pf.strftime(fmt), "to": pt.strftime(fmt)}}}
                    try:
                        pres = await _exec_and_wait(body)
                        pst = ((pres.get(state_id) or {}).get("search_types")) or {}
                        pr = next((pst[s] for s in wmap if s in pst), None)
                        if pr is not None:
                            _tf, _tfld = _metric_fn_field(
                                ((wc.get("series") or [{}])[0] or {}).get("function") or "count()")
                            trend_prev[wid] = _numeric_of(pr, (_tf == "count" and not _tfld))
                    except Exception:
                        pass
    except Exception as e:
        log.warning("rebuild_dashboard failed", dashboard=dashboard_id, error=str(e))
        return []

    # Correlate PER STATE (tab). Emit ONE report section per tab (titled with
    # the tab name) so the reader can tell tabs apart. `tabs` (list of state_ids)
    # selects which tabs to include; empty/None = all tabs.
    want = set(tabs or [])
    sections_out = []
    total = 0
    for state_id, state in states.items():
        if want and state_id not in want:
            continue
        if total >= cap:
            break
        st_res = ((results.get(state_id) or {}).get("search_types")) or {}
        if not st_res:
            continue
        tab_title = (((state.get("titles") or {}).get("tab") or {}).get("title")) or ""
        wmap = state.get("widget_mapping") or {}
        titles = ((state.get("titles") or {}).get("widget")) or {}
        positions = state.get("positions") or {}

        def _pos(w):
            p = positions.get(w.get("id"), {}) or {}
            return (p.get("row", 999), p.get("col", 999))

        widgets = sorted([w for w in (state.get("widgets") or [])
                          if w.get("type") in ("aggregation", "messages")], key=_pos)
        tab_widgets = []
        for w in widgets:
            if total >= cap:
                break
            wid = w.get("id")
            res = None
            for sid2 in (wmap.get(wid) or [wid]):
                if sid2 in st_res:
                    res = st_res[sid2]
                    break
            if not res:
                continue
            wt = titles.get(wid) or _widget_autotitle(w) or wid[:8]
            if w.get("type") == "messages":
                if not res.get("messages"):
                    continue
                widget = _messages_to_table(w.get("config") or {}, wt, res, message_rows,
                                            message_max_cols, date_fields=date_fields, lang=lang)
            else:
                if not res.get("rows"):
                    continue
                widget = _pivot_to_widget(w.get("config") or {}, wt, res, bar_horizontal=bar_horizontal,
                                          heatmap_values=heatmap_values, date_fields=date_fields)
            if widget:
                eff = res.get("effective_timerange") or {}
                es = _parse_ts(eff.get("from")) if eff.get("from") else None
                ee = _parse_ts(eff.get("to")) if eff.get("to") else None
                widget["range_label"] = _range_label(time_range_seconds, lang, start=es, end=ee)
                # Attach a trend badge to single-value widgets that enable it.
                if widget.get("kind") == "single" and wid in trend_prev:
                    _wcfg = w.get("config") or {}
                    pref = (_wcfg.get("visualization_config") or {}).get("trend_preference", "NEUTRAL")
                    _cf, _cfld = _metric_fn_field(
                        ((_wcfg.get("series") or [{}])[0] or {}).get("function") or "count()")
                    widget["trend"] = _compute_trend(
                        _numeric_of(res, (_cf == "count" and not _cfld)),
                        trend_prev[wid], pref, unit=_widget_unit(_wcfg))
                tab_widgets.append(widget)
                total += 1
        if tab_widgets:
            sec_title = f"{title}｜{tab_title}" if tab_title else title
            sections_out.append({"type": "charts", "title": sec_title,
                                 "description": _rebuild_desc(lang, len(tab_widgets), time_range_seconds),
                                 "widgets": tab_widgets})

    return sections_out


async def __import_asyncio_sleep(sec):
    import asyncio
    await asyncio.sleep(sec)


def _rebuild_desc(lang, n, secs):
    hrs = secs // 3600
    if lang == "zh-TW":
        return f"由 Graylog 儀表板重現的 {n} 個 widget（時間範圍：近 {hrs} 小時）。"
    return f"{n} widgets rebuilt from the Graylog dashboard (time range: last {hrs}h)."


def _widget_autotitle(w):
    c = w.get("config") or {}
    series = c.get("series") or []
    rp = c.get("row_pivots") or []
    fn = series[0].get("function") if series else ""
    field = (rp[0].get("fields") or [""])[0] if rp else ""
    return (f"{fn} by {field}".strip() if (fn or field) else "")


def _pivot_to_widget(cfg: dict, title: str, res: dict, *, bar_horizontal: bool = False,
                     heatmap_values: bool = False, date_fields: set | None = None) -> dict | None:
    """Map a Graylog pivot result to one of our report widgets."""
    from glogarch.report import builder
    rows = res.get("rows") or []
    viz = cfg.get("visualization") or "table"
    row_pivots = cfg.get("row_pivots") or []
    col_pivots = cfg.get("column_pivots") or []
    is_time = bool(row_pivots) and (row_pivots[0].get("type") == "time")
    unit = _widget_unit(cfg)   # Graylog metric unit (e.g. size/bytes), or None
    axis = _axis_type(cfg)     # 'linear' | 'logarithmic' (Graylog y-axis scale)

    # A single-number/metric widget legitimately reads the rollup/total row;
    # every other widget (table, chart, heatmap, map) must use ONLY leaf data
    # rows. If there are no leaf rows the widget is genuinely EMPTY — do not
    # fall back to the rollup/total/non-leaf rows, or a table turns a stray
    # total into a phantom row (real bug: an empty external-IP table rendered
    # a bogus "443").
    is_numeric = (viz == "numeric") or (not row_pivots)
    leaf_rows = [r for r in rows if r.get("source") == "leaf"]
    drows = leaf_rows if leaf_rows else (rows if is_numeric else [])
    if is_time:
        # A time axis is ALWAYS chronological and continuous. Graylog returns
        # only the buckets that have data (sparse) but renders them on a
        # continuous timeline; if we plot the sparse rows in Graylog's returned
        # order (which may be sorted by the widget's sort = value/desc) and
        # evenly spaced, the temporal shape comes out reversed/compressed.
        # So: sort by bucket time and zero-fill the missing interval buckets.
        # Never apply "skip empty values" to a time pivot — empty buckets are
        # real zeros that must be shown.
        drows = _normalize_time_rows(drows, res.get("effective_timerange") or {}, cfg)
    elif not is_numeric:
        # Honour each row pivot's "Skip Empty Values" — drop rows whose
        # skip-empty field value is blank (values pivots only).
        drows = _skip_empty_rows(drows, row_pivots)

    # Non-numeric widget with no leaf data → render an explicit "(no data)"
    # note instead of a phantom row/value.
    if not is_numeric and not drows:
        return {"kind": "empty", "title": title}

    # numeric single value: no row pivot (just a total)
    if viz == "numeric" or (not row_pivots):
        val = None
        tot = res.get("total")   # search doc count — equals the metric ONLY for count()
        if drows:
            vv = drows[0].get("values") or []
            if vv:
                val = vv[0].get("value")
        func, field = _metric_fn_field(
            ((cfg.get("series") or [{}])[0] or {}).get("function") or "count()")
        is_count = (func == "count" and not field)
        if val is None and is_count:
            val = tot   # doc-count total is only a valid fallback for bare count()
        if val is None:
            # A non-count metric with no value is genuinely empty — show
            # "(no data)", never a phantom doc-count / "0" (real "443" bug).
            return {"kind": "empty", "title": title}
        # Date-typed metric (min/max/latest/avg on a date field) → local datetime,
        # like the table path; otherwise format with the widget's unit.
        typed = _fmt_metric_typed(val, (func + "(" + field + ")") if field else (func + "()"),
                                  date_fields or set())
        value = typed if typed != _fmt_metric(val) else _fmt_unit(val, unit)
        return {"kind": "single", "title": title, "value": value, "label": ""}

    # A Graylog data table stays a table.
    if viz == "table":
        return _pivot_to_table(cfg, title, drows, col_pivots, date_fields=date_fields)
    # A geo/world-map is drawn as a self-contained SVG bubble map (the row key is
    # a "lat,long" geolocation string, the value is the count → bubble size).
    if viz in ("map", "world_map"):
        m = _pivot_to_map(title, drows)
        if m:
            return m
        return _pivot_to_table(cfg, title, drows, col_pivots, date_fields=date_fields)   # fallback if no coords
    # A heatmap stays a heatmap: a colour-graded grid of row-pivot × column-pivot.
    if viz == "heatmap":
        h = _pivot_to_heatmap(cfg, title, drows, col_pivots, show_values=heatmap_values)
        if h:
            return h
        return _pivot_to_table(cfg, title, drows, col_pivots, date_fields=date_fields)   # fallback if 1-D

    labels = [_rowkey(r) for r in drows]                       # keys (for lookups)
    disp = _time_axis_labels(drows) if is_time else labels     # display labels
    # Non-time row-pivot empties render as "-" via _rowkey(); relabel to Graylog's
    # "(Empty Value)" convention. DISPLAY copy only — `labels` stays the lookup key
    # for series_map, and time labels (formatted) are untouched.
    if not is_time:
        disp = ["(Empty Value)" if d == "-" else d for d in disp]

    if not col_pivots:
        values = [_first_value(r) for r in drows]
        # No data at all → a clean "(no data)" note, not a broken empty chart.
        if not any((v or 0) for v in values):
            return {"kind": "empty", "title": title}
        if viz == "pie":
            ranked = sorted(zip(disp, values), key=lambda x: (x[1] or 0), reverse=True)
            top = ranked[:8]
            # Aggregate the remainder into one "(Others)" slice so the grand total
            # (and thus every on-slice percentage) matches Graylog instead of
            # silently dropping slices and inflating the shown percentages.
            rest = sum((v or 0) for _, v in ranked[8:])
            plabels = [l for l, _ in top]
            pvalues = [v for _, v in top]
            if rest > 0:
                plabels.append("(Others)")
                pvalues.append(rest)
            return {"kind": "chart", "title": title,
                    "config": builder.pie_chart(plabels, pvalues)}
        # Line / area = a trend or DISTRIBUTION curve — dispatch on the widget's
        # visualization, not just on whether the pivot is time. A numeric values
        # pivot (e.g. duration_us) must read left-to-right by its key, NOT be
        # sorted-by-value and capped like a bar (that turned Graylog's area curve
        # into 15 ranked bars).
        if viz == "scatter" or viz in ("line", "area") or (is_time and viz != "bar"):
            if is_time:
                d2, v2 = disp, values
            elif viz == "scatter":
                d2, v2 = disp, values          # scatter: keep Graylog's row order
            else:
                pr = sorted(zip(disp, values), key=lambda t: _numkey(t[0]))
                d2 = [d for d, _ in pr]; v2 = [v for _, v in pr]
            if viz == "scatter":
                chart_cfg = builder.scatter_chart(d2, [{"label": title, "data": v2}], axis_type=axis)
            else:
                chart_cfg = builder.line_chart(d2, [{"label": title, "data": v2}], axis_type=axis,
                                               fill=(viz == "area"), interpolation=_interpolation(cfg))
            return {"kind": "chart", "title": title, "tall": True, "unit": unit, "config": chart_cfg}
        if is_time and viz == "bar":
            return {"kind": "chart", "title": title, "tall": True, "unit": unit,
                    "config": _bar_multi(disp, [{"label": title, "data": values}], _barmode(cfg), axis_type=axis)}
        # non-time bar (cap to top 15). Preserve Graylog's returned row order
        # (already the widget's configured sort + limit) instead of re-sorting by
        # value desc — re-sorting reordered bars away from what Graylog shows.
        top = list(zip(disp, values))[:15]
        return {"kind": "chart", "title": title, "unit": unit,
                "config": _bar_multi([l for l, _ in top], [{"label": title, "data": [v for _, v in top]}],
                                     _barmode(cfg), axis_type=axis, horizontal=bar_horizontal)}

    # column pivots -> multiple series (data keyed by raw rowkey, displayed via disp)
    col_skip = any((cp.get("config") or {}).get("skip_empty_values") for cp in col_pivots)
    series_map = {}
    order = []
    for r in drows:
        for v in (r.get("values") or []):
            if v.get("source") not in ("col-leaf", "leaf"):
                continue
            k = v.get("key") or []
            colname = " / ".join(str(x) for x in k[:-1]) or (str(k[0]) if k else "")
            if _is_empty_val(colname):
                if col_skip:
                    continue                 # honour column "Skip Empty Values"
                colname = "(Empty Value)"    # else label it like Graylog, not a blank legend swatch
            if colname not in series_map:
                series_map[colname] = {}
                order.append(colname)
            series_map[colname][_rowkey(r)] = v.get("value")
    # Keep ALL column-pivot series (a stacked chart is only correct when every
    # series is present, not just the first few — Graylog shows them all). Cap
    # generously to avoid a pathological legend; the palette cycles like Graylog.
    series = [{"label": name, "data": [series_map[name].get(l, 0) for l in labels]}
              for name in order[:30]]
    if not any(any((v or 0) for v in s["data"]) for s in series):
        return {"kind": "empty", "title": title}
    # A many-series legend (Chart.js renders it on-canvas) needs a taller card so
    # the last rows aren't clipped — flag it for the .legend-heavy CSS tier.
    legend_heavy = len(series) > 15
    if viz == "scatter":
        return {"kind": "chart", "title": title, "tall": True, "unit": unit, "legend_heavy": legend_heavy,
                "config": builder.scatter_chart(disp, series, axis_type=axis)}
    if viz in ("line", "area") or (is_time and viz != "bar"):
        return {"kind": "chart", "title": title, "tall": True, "unit": unit, "legend_heavy": legend_heavy,
                "config": builder.line_chart(disp, series, axis_type=axis,
                                             fill=(viz == "area"), interpolation=_interpolation(cfg),
                                             stacked=(viz == "area"))}
    # bar: preserve Graylog's bar mode (grouped / stacked / overlay). A time bar
    # must stay vertical/chronological, so only a categorical bar may go horizontal.
    return {"kind": "chart", "title": title, "tall": bool(is_time), "unit": unit, "legend_heavy": legend_heavy,
            "config": _bar_multi(disp, series, _barmode(cfg), axis_type=axis,
                                 horizontal=(bar_horizontal and not is_time))}


def _parse_ts(ts):
    from datetime import datetime
    s = str(ts).strip()
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _interval_from_cfg(cfg):
    """An EXPLICIT timeunit interval from a time row-pivot config → timedelta.
    Returns None for 'auto' (never guess) or when absent/unknown."""
    from datetime import timedelta
    try:
        rp = (cfg.get("row_pivots") or [])[0]
        iv = (rp.get("config") or {}).get("interval") or {}
    except (IndexError, AttributeError, TypeError):
        return None
    if iv.get("type") != "timeunit":
        return None
    val = iv.get("value")
    if not isinstance(val, (int, float)) or val <= 0:
        return None
    unit_secs = {"seconds": 1, "minutes": 60, "hours": 3600, "days": 86400,
                 "weeks": 604800, "months": 2592000, "years": 31536000}
    s = unit_secs.get(str(iv.get("unit") or "").lower())
    return timedelta(seconds=val * s) if s else None


def _normalize_time_rows(drows, eff=None, cfg=None):
    """Make a time-bucketed pivot render like Graylog's continuous time axis.

    Graylog returns only the buckets that contain data (sparse) and may return
    them in the widget's sort order (e.g. by metric value, descending). Plotting
    those sparse rows in returned order and evenly spaced makes the temporal
    shape wrong (reversed / compressed). Here we:
      1. sort the rows chronologically by their bucket timestamp,
      2. zero-fill the missing interval buckets, and
      3. extend the fill to the widget's FULL effective time range (`eff`) so
         the leading/trailing empty buckets appear (data clustered at one end),
         exactly like Graylog — not just the span between first and last data.
    """
    from datetime import timedelta, timezone
    parsed = []
    any_naive = False
    for r in drows:
        dt = _parse_ts((r.get("key") or [""])[0])
        if dt is None:
            continue
        if dt.tzinfo is None:
            any_naive = True
        parsed.append((dt, r))
    if not parsed:
        return drows
    parsed.sort(key=lambda x: x[0])

    # Interval (step): smallest positive gap, else the widget's explicit interval.
    step = None
    if len(parsed) >= 2:
        deltas = [d for d in (parsed[i + 1][0] - parsed[i][0]
                              for i in range(len(parsed) - 1)) if d.total_seconds() > 0]
        if deltas:
            step = min(deltas)
    if step is None:
        step = _interval_from_cfg(cfg)
    if step is None or step.total_seconds() <= 0:
        return [r for _, r in parsed]   # can't fill safely → just the sorted data

    # Effective-range bounds (UTC). Usable ONLY when both parse, all buckets are
    # tz-aware (mixing naive + aware would raise), and to > from. Otherwise fall
    # back to filling just the data span (never let cross-source math raise).
    t_from = _parse_ts((eff or {}).get("from"))
    t_to = _parse_ts((eff or {}).get("to"))
    use_bounds = (t_from is not None and t_to is not None
                  and not any_naive and t_to > t_from)
    if use_bounds:
        import math
        t_from = t_from.astimezone(timezone.utc)
        t_to = t_to.astimezone(timezone.utc)
        first = parsed[0][0]
        last = parsed[-1][0]
        # DIAGNOSTIC (issue #3, time-bar left-empty): the effective_timerange can
        # come back much wider than the actual data window, filling the left half
        # of the axis with empty buckets. Log the spans so we can size a correct
        # guard from real values before clamping (no blind heuristic).
        data_span = (last - first).total_seconds()
        eff_span = (t_to - t_from).total_seconds()
        if eff_span > 0 and data_span >= 0:
            log.info("time-bucket fill spans",
                     eff_from=t_from.isoformat(), eff_to=t_to.isoformat(),
                     data_first=first.isoformat(), data_last=last.isoformat(),
                     eff_span_s=round(eff_span), data_span_s=round(data_span),
                     ratio=round(eff_span / data_span, 2) if data_span > 0 else None,
                     step_s=round(step.total_seconds()))
        k = math.floor((first - t_from).total_seconds() / step.total_seconds())
        start, end = first - step * k, t_to
    else:
        start, end = parsed[0][0], parsed[-1][0]

    n = int((end - start).total_seconds() / step.total_seconds())
    if n < 0 or n > 2000:   # don't explode; fall back to the data span
        start, end = parsed[0][0], parsed[-1][0]
        n = int((end - start).total_seconds() / step.total_seconds())
        if n < 0 or n > 2000:
            return [r for _, r in parsed]

    def _zero_bucket(dt):
        return {"key": [dt.isoformat()], "source": "leaf",
                "values": [{"key": [], "value": 0, "source": "leaf"}]}

    out = []
    i = 0
    cur = start
    tol = step.total_seconds() / 2.0
    while cur <= end + timedelta(seconds=tol):
        if i < len(parsed) and abs((parsed[i][0] - cur).total_seconds()) <= tol:
            out.append(parsed[i][1]); i += 1
        else:
            out.append(_zero_bucket(cur))
        cur = cur + step
    while i < len(parsed):   # safety: never drop a real bucket
        out.append(parsed[i][1]); i += 1
    return out


def _time_axis_labels(drows):
    """Graylog-style x-axis labels: time (HH:MM) on every tick, with the date
    (MM-DD) shown as a SECOND line only when the day changes — so date and time
    are visually separated like Graylog, not crammed as 'MM-DD HH:MM'."""
    out = []
    prev_day = None
    for r in drows:
        ts = (r.get("key") or [""])[0]
        dt = _parse_ts(ts)
        if dt is None:
            out.append(str(ts)[:16])
            prev_day = None
            continue
        hm = dt.strftime("%H:%M")
        day = dt.strftime("%m-%d")
        if day != prev_day:
            out.append(hm + "\n" + day)   # two-line label; JS ticks callback splits on \n
            prev_day = day
        else:
            out.append(hm)
    return out


def _range_label(secs, lang="zh-TW", start=None, end=None):
    """Time-window caption: relative span + the actual absolute start~end in
    parentheses, e.g. 最近 24 小時（2026-07-03 18:50 ~ 2026-07-04 18:50）.
    If start/end (the widget's effective range) are given, they drive the label
    so it matches exactly what Graylog used for that widget."""
    from datetime import datetime, timedelta
    if start is not None and end is not None:
        # Graylog's effective_timerange comes back in UTC (…Z). Show it in the
        # server's LOCAL timezone so the caption doesn't look hours/days off.
        now = end.astimezone() if getattr(end, "tzinfo", None) else end
        start_dt = start.astimezone() if getattr(start, "tzinfo", None) else start
        secs = int((now - start_dt).total_seconds())
    else:
        secs = int(secs or 0)
        now = datetime.now().astimezone()
        start_dt = now - timedelta(seconds=secs)
    fmt = "%Y-%m-%d %H:%M"
    span = f"{start_dt.strftime(fmt)} ~ {now.strftime(fmt)}"
    if secs and secs % 86400 == 0:
        base = (f"最近 {secs // 86400} 天" if lang == "zh-TW" else f"Last {secs // 86400}d")
    elif secs and secs % 3600 == 0:
        base = (f"最近 {secs // 3600} 小時" if lang == "zh-TW" else f"Last {secs // 3600}h")
    else:
        n = max(1, secs // 60)
        base = (f"最近 {n} 分鐘" if lang == "zh-TW" else f"Last {n}m")
    return f"{base}（{span}）" if lang == "zh-TW" else f"{base} ({span})"


def _series_label(s):
    if not isinstance(s, dict):
        return str(s)
    return s.get("function") or (s.get("config") or {}).get("name") or "count()"


def _grouped_rows(raw, n_keys):
    """Blank repeated leading row-pivot values (Graylog-style grouped rows) so a
    sub-divided key like `192.168.1.1` shows once, with its sub-rows visibly
    belonging to it; flag the first row of each top-level group for a separator.
    `raw` is a list of full cell lists (the n_keys key columns come first)."""
    out, prev = [], []
    for cells in raw:
        keys = cells[:n_keys]
        disp = list(cells)
        same = True
        for i in range(n_keys):
            if same and i < len(prev) and prev[i] == keys[i]:
                disp[i] = ""          # same as the row above → blank (grouped)
            else:
                same = False
        group = (not prev) or n_keys == 0 or keys[:1] != prev[:1]
        out.append({"cells": disp, "group": group})
        prev = keys
    return out


def _col_alignments(raw, key_cols, ncols):
    """Per-column alignment: right-align a metric column ONLY when every value in
    it is a plain number. String metrics (e.g. latest(interface_name) → 'WAN')
    and dates (latest(timestamp)) stay left-aligned like Graylog."""
    import re
    num = re.compile(r"-?[\d,]+(?:\.\d+)?$")
    align = []
    for c in range(ncols):
        if c < key_cols:
            align.append("text")
            continue
        vals = [row[c] for row in raw if c < len(row) and str(row[c]).strip() != ""]
        align.append("num" if (vals and all(num.match(str(v)) for v in vals)) else "text")
    return align


def _pivot_to_table(cfg, title, drows, col_pivots, date_fields=None):
    """Render a Graylog table widget as a report table (columns + rows)."""
    date_fields = date_fields or set()
    total_rows = len(drows)          # for the "showing first N" truncation note
    row_pivots = cfg.get("row_pivots") or []
    series = cfg.get("series") or []
    rp_fields = []
    for rp in row_pivots:
        rp_fields.extend(rp.get("fields") or [])
    if col_pivots:
        # Two kinds of metric column: the per-column-pivot values (source
        # 'col-leaf', key = [pivot_value, metric]) and — when rollup is on — the
        # grand total per metric (key = [metric] only). Graylog shows the total
        # column FIRST, then the pivot columns sorted; mirror that so the numbers
        # line up with Graylog (a missing total column made ours look different).
        total_cols, pivot_cols = [], []
        for r in drows:
            for v in (r.get("values") or []):
                k = v.get("key") or []
                if not k:
                    continue
                cn = " / ".join(str(x) for x in k)
                src = v.get("source")
                if src == "col-leaf":
                    if cn not in pivot_cols:
                        pivot_cols.append(cn)
                elif len(k) == 1 and cn not in total_cols:   # rollup grand total
                    total_cols.append(cn)
        # Preserve Graylog's column order: distinct pivot values in first-seen
        # order (that IS the widget's configured sort/limit), and within each
        # pivot value the metric columns in the widget's series order — NOT
        # alphabetical (sorting reordered columns away from Graylog).
        series_fns = [s.get("function") for s in (cfg.get("series") or [])]

        def _metric_rank(cn):
            m = cn.rpartition(" / ")[2]
            return series_fns.index(m) if m in series_fns else len(series_fns)

        colval_order, by_val = [], {}
        for cn in pivot_cols:
            val = cn.rpartition(" / ")[0]
            if not val or _is_empty_val(val):
                val = "(Empty Value)"     # label empty column-pivot like Graylog
            if val not in by_val:
                by_val[val] = []
                colval_order.append(val)
            by_val[val].append(cn)
        # Cap at 30 column-pivot values (matches the 30-series chart cap) instead
        # of 12 — Graylog renders far more; 30 fills the A4 width without blowing it.
        pivot_cols = [cn for val in colval_order
                      for cn in sorted(by_val[val], key=_metric_rank)][:30]
        colnames = (total_cols if cfg.get("rollup") else []) + pivot_cols
        columns = rp_fields + colnames
        raw = []
        for r in drows[:40]:
            vmap = {" / ".join(str(x) for x in (v.get("key") or [])): v.get("value")
                    for v in (r.get("values") or [])}
            cells = [str(x) for x in (r.get("key") or [])]
            # A null/empty trailing row-pivot value can be dropped from the row
            # key, leaving fewer key cells than row-pivot columns — which shifts
            # every metric value one column to the left. Pad to len(rp_fields).
            while len(cells) < len(rp_fields):
                cells.append("")
            # A column's metric fn is the last segment of its key (e.g.
            # 'pivotval / min(timestamp)' -> 'min(timestamp)') → format dates.
            cells += [(_fmt_metric_typed(vmap[c], c.rsplit(" / ", 1)[-1], date_fields)
                       if vmap.get(c) is not None else "") for c in colnames]
            raw.append(cells)
        out = {"kind": "table", "title": title, "columns": columns,
               "rows": _grouped_rows(raw, len(rp_fields)), "numeric_from": len(rp_fields),
               "col_align": _col_alignments(raw, len(rp_fields), len(columns))}
        if total_rows > 40:
            out["rows_note"] = "僅顯示前 40 筆"
        return out
    # simple table: row-pivot key columns + one column per series. Map each
    # value to its series by KEY (the last key element is the series function),
    # so a null metric (e.g. an empty latest(host_hostname)) leaves a BLANK cell
    # instead of shifting the next series' value (count) left into its column.
    series_labels = [_series_label(s) for s in series] or ["count()"]
    series_fns = [s.get("function") for s in series]
    columns = rp_fields + series_labels
    raw = []
    for r in drows[:40]:
        rvals = r.get("values") or []
        vmap = {}
        for v in rvals:
            k = v.get("key") or []
            if k:
                vmap[str(k[-1])] = v.get("value")
        ordered = [v.get("value") for v in rvals]   # positional fallback
        cells = [str(x) for x in (r.get("key") or [])]
        # Pad a short row key (a null/empty trailing row-pivot value gets dropped
        # from the key) so metric values don't shift left into a pivot column.
        while len(cells) < len(rp_fields):
            cells.append("")
        for i, fn in enumerate(series_fns or [None]):
            if fn is not None and fn in vmap:
                val = vmap[fn]
            else:
                val = ordered[i] if i < len(ordered) else None
            cells.append(_fmt_metric_typed(val, fn, date_fields) if val is not None else "")
        raw.append(cells)
    out = {"kind": "table", "title": title, "columns": columns,
           "rows": _grouped_rows(raw, len(rp_fields)), "numeric_from": len(rp_fields),
           "col_align": _col_alignments(raw, len(rp_fields), len(columns))}
    if total_rows > 40:
        out["rows_note"] = "僅顯示前 40 筆"
    return out


def _barmode(cfg: dict) -> str:
    """Graylog bar visualization mode: group | stack | relative | overlay."""
    vc = cfg.get("visualization_config") or {}
    return str(vc.get("barmode") or "group").lower()


def _interpolation(cfg: dict) -> str:
    """Graylog line/area interpolation: 'linear' (default) | 'spline' | 'step-after'."""
    vc = cfg.get("visualization_config") or {}
    return str(vc.get("interpolation") or "linear").lower()


def _axis_type(cfg: dict) -> str:
    """Graylog y-axis scale: 'linear' (default) or 'logarithmic'."""
    vc = cfg.get("visualization_config") or {}
    at = str(vc.get("axis_type") or "linear").lower()
    return "logarithmic" if at.startswith("log") else "linear"


def _y_scale(stacked: bool, axis_type: str) -> dict:
    """Chart.js y-axis honouring Graylog's linear/logarithmic axis choice.
    A logarithmic scale can't begin at zero, so beginAtZero only applies to
    linear axes."""
    if axis_type == "logarithmic":
        return {"type": "logarithmic", "stacked": stacked}
    return {"beginAtZero": True, "stacked": stacked}


def _bar_multi(labels, series, barmode="group", axis_type="linear", horizontal=False):
    """Multi-series bar chart honouring Graylog's bar mode.

    - stack / relative -> stacked bars
    - overlay          -> bars overlap at the same x (Chart.js grouped:false) + alpha
    - group (default)  -> side-by-side grouped bars
    """
    from glogarch.report.builder import PALETTE
    stacked = barmode in ("stack", "relative")
    overlay = barmode == "overlay"
    # Keep each series' colour stable to its position, but for OVERLAY draw the
    # largest-area series FIRST (behind) and the smallest LAST (in front) so no
    # series is fully hidden. A translucent fill + an OPAQUE same-colour outline
    # makes each layer's top edge legible — that's what distinguishes a proper
    # overlay from a stack at a glance.
    idx = list(range(len(series)))
    if overlay:
        idx.sort(key=lambda i: -sum((v or 0) for v in (series[i].get("data") or [])))
    datasets = []
    for i in idx:
        s = series[i]
        c = PALETTE[i % len(PALETTE)]
        d = {"label": s.get("label", ""), "data": s["data"], "borderRadius": 0}
        if overlay:
            d["backgroundColor"] = c + "59"   # ~35% fill
            d["borderColor"] = c              # opaque outline delineates layers
            d["borderWidth"] = 1
            d["grouped"] = False
        else:
            d["backgroundColor"] = c
        datasets.append(d)
    cat_scale = {"stacked": stacked,
                 "ticks": {"autoSkip": True, "maxTicksLimit": 12,
                           "maxRotation": 0, "minRotation": 0}}
    val_scale = _y_scale(stacked, axis_type)
    # Horizontal: category axis = y, value axis = x (Chart.js indexAxis='y').
    scales = ({"y": cat_scale, "x": val_scale} if horizontal
              else {"x": cat_scale, "y": val_scale})
    options = {"responsive": True, "maintainAspectRatio": False,
               "plugins": {"legend": {"display": len(datasets) > 1, "position": "bottom",
                                      "align": "start",   # left-align rows like Graylog (not centred/ragged)
                                      "labels": {"padding": 14, "boxWidth": 12, "boxHeight": 12}}},
               "scales": scales}
    if horizontal:
        options["indexAxis"] = "y"
    return {"type": "bar", "data": {"labels": labels, "datasets": datasets},
            "options": options}


def _rowkey(r):
    k = r.get("key") or []
    s = " / ".join(str(x) for x in k)
    return (s[:40] + "…") if len(s) > 41 else (s or "-")


def _numkey(s):
    """Sort key: numeric labels sort numerically (so a duration distribution reads
    left-to-right), non-numeric labels sort after, lexically."""
    try:
        return (0, float(str(s).replace(",", "")))
    except (ValueError, TypeError):
        return (1, str(s))


def _is_empty_val(v):
    """A blank/empty pivot bucket, as Graylog's 'Skip Empty Values' would drop."""
    return v is None or str(v).strip() in ("", "(Empty Value)", "(empty)")


def _skip_empty_rows(drows, row_pivots):
    """Drop rows whose value for a 'skip_empty_values' row pivot is blank."""
    skip_pos, pos = [], 0
    for rp in (row_pivots or []):
        n = len(rp.get("fields") or []) or 1
        if (rp.get("config") or {}).get("skip_empty_values"):
            skip_pos.extend(range(pos, pos + n))
        pos += n
    if not skip_pos:
        return drows
    out = []
    for r in drows:
        k = r.get("key") or []
        if not any(i < len(k) and _is_empty_val(k[i]) for i in skip_pos):
            out.append(r)
    return out


def _first_value(r):
    vv = r.get("values") or []
    for v in vv:
        if v.get("value") is not None:
            return v.get("value")
    return 0


def _numeric_of(res, is_count=True):
    """The single scalar value from a numeric widget's pivot result. The search
    doc-count `total` is a valid fallback ONLY for a bare count() metric — for
    any other metric it is a phantom value that would corrupt the trend badge."""
    for r in (res.get("rows") or []):
        for v in (r.get("values") or []):
            if v.get("value") is not None:
                return v.get("value")
    return res.get("total") if is_count else None


def _compute_trend(cur, prev, preference="NEUTRAL", *, unit=None):
    """Trend badge vs the previous period. `preference` (Graylog's
    trend_preference) decides colour: an increase is 'good' (green) when HIGHER
    is preferred, 'bad' (red) when LOWER is preferred, neutral otherwise."""
    try:
        cur = float(cur) if cur is not None else None
        prev = float(prev) if prev is not None else None
    except (TypeError, ValueError):
        return None
    if cur is None or prev is None:
        return None
    delta = cur - prev
    pct = (delta / prev * 100.0) if prev else None
    up = delta > 0
    down = delta < 0
    if preference == "HIGHER":
        cls = "good" if up else ("bad" if down else "neutral")
    elif preference == "LOWER":
        cls = "bad" if up else ("good" if down else "neutral")
    else:
        cls = "neutral"
    arrow = "▲" if up else ("▼" if down else "＝")
    sign = "+" if up else ("" if delta == 0 else "-")
    dtxt = f"{sign}{_fmt_unit(abs(delta), unit)}"
    ptxt = (f"{sign}{abs(pct):.1f}%") if pct is not None else ""
    return {"arrow": arrow, "delta": dtxt, "pct": ptxt, "cls": cls}


def _messages_to_table(cfg, title, res, max_rows, max_cols=0, date_fields=None, lang="zh-TW"):
    """Render a Graylog message-list widget as a table (its configured fields,
    capped at max_rows). max_rows<=0 means no cap. If max_cols>0 and the widget
    has more configured fields than that, the widget is skipped (returns None) —
    wide message tables overflow the A4 page, so the report omits them.

    Honours the widget's `show_message_row` setting (Graylog's "Show message in
    new row" / message preview): the full `message` field is rendered as a second
    row under each entry, matching the on-screen widget."""
    date_fields = date_fields or set()
    fields = cfg.get("fields") or ["timestamp", "source", "message"]
    if max_cols and max_cols > 0 and len(fields) > max_cols:
        return None
    show_preview = bool(cfg.get("show_message_row"))
    # When the message renders on its own preview row, don't ALSO keep it as a
    # column — Graylog shows the message once, not duplicated.
    cols = [f for f in fields if not (show_preview and f == "message")]
    msgs = res.get("messages") or []
    total = len(msgs)
    if max_rows and max_rows > 0:
        msgs = msgs[:max_rows]
    rows = []
    raw = []
    for m in msgs:
        doc = m.get("message") or m
        cells = []
        for f in cols:
            v = doc.get(f, "")
            if v is not None and (f == "timestamp" or f in date_fields):
                # Date column → local 'YYYY-MM-DD HH:MM:SS.mmm' like Graylog;
                # fall back to epoch-millis/seconds parsing before a raw string.
                cells.append(_fmt_iso_local(v) or _fmt_date_value(v) or (str(v) if v != "" else ""))
            else:
                cells.append(str(v) if v is not None else "")
        raw.append(cells)
        row = {"cells": cells}
        if show_preview:
            msg = doc.get("message")
            row["preview"] = str(msg) if msg not in (None, "") else ""
        rows.append(row)
    if not rows:
        return None
    # A message list has no row-pivot key columns → right-align only columns whose
    # every value is numeric; formatted dates (hyphens/colons) stay left-aligned.
    out = {"kind": "table", "title": title, "columns": list(cols), "rows": rows,
           "col_align": _col_alignments(raw, 0, len(cols))}
    # When a row cap actually truncated the widget, note it bottom-right.
    if max_rows and max_rows > 0 and total > max_rows:
        out["rows_note"] = (f"僅顯示前 {max_rows:,} 筆" if lang == "zh-TW"
                            else f"Showing first {max_rows:,} of {total:,} rows")
    return out


def _pivot_to_map(title, drows):
    """Build a bubble world-map widget from a geo pivot (row key = 'lat,long')."""
    from glogarch.report import builder
    points = []
    skipped = 0
    for r in drows:
        k = r.get("key") or []
        if not k:
            skipped += 1
            continue
        try:
            parts = str(k[0]).split(",")
            lat = float(parts[0]); lon = float(parts[1])
        except (ValueError, IndexError):
            skipped += 1
            continue
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            points.append((lat, lon, _first_value(r) or 0))
        else:
            skipped += 1
    if skipped:
        log.debug("geo map skipped coordinates", widget=title,
                  valid=len(points), skipped=skipped)
    if not points:
        return None
    return {"kind": "map", "title": title, "svg": builder.geo_map(points)}


# Plotly colorscales (name → RGB stops) so heatmaps match Graylog's
# `color_scale` setting. Graylog serialises Plotly scale names; we mirror the
# common ones and fall back to Viridis (Graylog's heatmap default).
_COLORSCALES = {
    "Portland": [(12, 51, 131), (10, 136, 186), (242, 211, 56), (242, 143, 56), (181, 49, 50)],
    "Viridis": [(68, 1, 84), (59, 82, 139), (33, 145, 140), (94, 201, 98), (253, 231, 37)],
    "Blues": [(247, 251, 255), (198, 219, 239), (107, 174, 214), (33, 113, 181), (8, 48, 107)],
    "Greens": [(247, 252, 245), (199, 233, 192), (116, 196, 118), (35, 139, 69), (0, 68, 27)],
    "Hot": [(0, 0, 0), (230, 0, 0), (255, 210, 0), (255, 255, 224), (255, 255, 255)],
    "YlOrRd": [(255, 255, 204), (254, 217, 118), (253, 141, 60), (227, 26, 28), (128, 0, 38)],
    "RdBu": [(103, 0, 31), (214, 96, 77), (247, 247, 247), (67, 147, 195), (5, 48, 97)],
    "Jet": [(0, 0, 131), (0, 128, 255), (0, 255, 128), (255, 255, 0), (255, 0, 0)],
    "Bluered": [(0, 0, 255), (128, 0, 128), (255, 0, 0)],
    "Electric": [(0, 0, 0), (30, 0, 100), (120, 0, 100), (230, 200, 0), (255, 255, 255)],
    "Cividis": [(0, 32, 76), (0, 67, 88), (89, 91, 97), (165, 146, 110), (255, 233, 69)],
    "Greys": [(255, 255, 255), (189, 189, 189), (115, 115, 115), (37, 37, 37), (0, 0, 0)],
    "Reds": [(255, 245, 240), (252, 187, 161), (251, 106, 74), (203, 24, 29), (103, 0, 13)],
    "YlGnBu": [(255, 255, 217), (199, 233, 180), (65, 182, 196), (34, 94, 168), (8, 29, 88)],
    "Earth": [(0, 0, 130), (0, 180, 180), (0, 160, 0), (230, 220, 50), (180, 60, 10)],
    "Picnic": [(0, 0, 255), (150, 150, 255), (255, 255, 255), (255, 150, 150), (255, 0, 0)],
    "Rainbow": [(150, 0, 90), (0, 0, 200), (0, 220, 220), (0, 200, 0), (255, 255, 0), (255, 0, 0)],
    "Blackbody": [(0, 0, 0), (230, 0, 0), (230, 210, 0), (255, 255, 255), (160, 200, 255)],
}


def _scale_rgb(ratio, stops):
    """Linear-interpolate an RGB tuple at ratio∈[0,1] across evenly-spaced stops."""
    if len(stops) == 1:
        return stops[0]
    ratio = max(0.0, min(1.0, ratio))
    seg = ratio * (len(stops) - 1)
    i = int(seg)
    if i >= len(stops) - 1:
        return stops[-1]
    f = seg - i
    a, b = stops[i], stops[i + 1]
    return tuple(round(a[j] + (b[j] - a[j]) * f) for j in range(3))


def _heat_color(val, lo, hi, scale="Viridis", rev=False):
    """Cell background from the widget's colour scale + a readable text colour.
    Value normalised over [lo, hi]; `rev` inverts the scale (Graylog
    reversescale). Empty cell = no fill."""
    if val is None:
        return "transparent", "#9ca3af"
    if hi <= lo:
        ratio = 0.5           # all cells equal → mid-scale, not a broken 0/÷
    else:
        ratio = max(0.0, min(1.0, (val - lo) / (hi - lo)))
    if rev:
        ratio = 1.0 - ratio
    stops = _COLORSCALES.get(scale) or _COLORSCALES["Viridis"]
    r, g, b = _scale_rgb(ratio, stops)
    # Perceived luminance → pick black/white text for contrast.
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    fg = "#1f2430" if lum > 150 else "#ffffff"
    return f"rgb({r},{g},{b})", fg


def _pivot_to_heatmap(cfg, title, drows, col_pivots, show_values=False):
    """Render a Graylog heatmap (row-pivot × column-pivot, one metric) as a
    colour-graded grid. Returns None if it isn't genuinely 2-D (no columns).
    show_values=False (default) matches Graylog: coloured cells, no numbers."""
    if not col_pivots:
        return None
    scale = (cfg.get("visualization_config") or {}).get("color_scale") or "Viridis"
    col_keys: list[str] = []
    matrix: dict[str, dict] = {}
    row_labels: list[str] = []
    for r in drows:
        rl = _rowkey(r)
        if rl not in matrix:
            matrix[rl] = {}
            row_labels.append(rl)
        for v in (r.get("values") or []):
            if v.get("source") not in ("col-leaf", "leaf"):
                continue
            k = v.get("key") or []
            colname = " / ".join(str(x) for x in k[:-1]) or (str(k[0]) if k else "")
            col_skip = any((cp.get("config") or {}).get("skip_empty_values") for cp in col_pivots)
            if _is_empty_val(colname):
                if col_skip:
                    continue                 # honour column "Skip Empty Values"
                colname = "(Empty Value)"    # else label it like Graylog
            if colname not in col_keys:
                col_keys.append(colname)
            matrix[rl][colname] = v.get("value")
    if not col_keys or not row_labels:
        return None
    # A4 can't scroll like Graylog's heatmap: a column pivot such as "dest port"
    # can have hundreds of values → an unreadable smear. Cap to the busiest rows
    # and columns (by total), matching what a reader actually cares about.
    # Fill the page instead of leaving whitespace: an A4 content row of ~5.5mm
    # columns holds ~26, and a page ~30 short heatmap rows. (Was 15/20, which
    # under-filled the grid vs Graylog even when there was room + data.)
    MAX_COLS, MAX_ROWS = 26, 30
    col_total = {c: sum((matrix[rl].get(c) or 0) for rl in row_labels) for c in col_keys}
    row_total = {rl: sum((matrix[rl].get(c) or 0) for c in col_keys) for rl in row_labels}
    truncated = len(col_keys) > MAX_COLS or len(row_labels) > MAX_ROWS
    col_keys = sorted(col_keys, key=lambda c: -col_total[c])[:MAX_COLS]
    row_labels = sorted(row_labels, key=lambda rl: -row_total[rl])[:MAX_ROWS]
    vals = [matrix[rl].get(c) for rl in row_labels for c in col_keys if matrix[rl].get(c) is not None]
    mx = max(vals) if vals else 0
    mn = min(vals) if vals else 0
    vc = cfg.get("visualization_config") or {}
    rev = bool(vc.get("reverse_scale"))
    # Empty-cell default fill: Graylog can paint blank cells with the smallest
    # value or an explicit default rather than leaving them transparent.
    if vc.get("use_smallest_as_default"):
        default_fill = min(vals) if vals else None
    else:
        default_fill = vc.get("default_value")
    if isinstance(default_fill, (int, float)):
        mx, mn = max(mx, default_fill), min(mn, default_fill)
    # Colour normalisation range: data min..max (auto) or the widget's z_min/z_max.
    if vc.get("auto_scale", True):
        lo, hi = mn, mx
    else:
        lo = vc.get("z_min") if isinstance(vc.get("z_min"), (int, float)) else mn
        hi = vc.get("z_max") if isinstance(vc.get("z_max"), (int, float)) else mx
    rows_out = []
    for rl in row_labels:
        cells = []
        for c in col_keys:
            val = matrix[rl].get(c)
            if val is None and default_fill is not None:
                val = default_fill
            bg, fg = _heat_color(val, lo, hi, scale, rev)
            txt = _fmt_metric(val) if (show_values and val is not None) else ""
            cells.append({"text": txt, "bg": bg, "fg": fg})
        rows_out.append({"label": rl, "cells": cells})
    # Colour-scale legend: a CSS gradient mirroring Graylog's colourbar. When the
    # scale is reversed, reverse the gradient AND swap the min/max end labels so
    # each end's colour matches the value under it.
    if scale not in _COLORSCALES:
        log.warning("heatmap color scale not recognized; using Viridis",
                    requested_scale=scale, widget_title=title,
                    available=list(_COLORSCALES.keys()))
    stops = _COLORSCALES.get(scale, _COLORSCALES["Viridis"])
    stops_leg = list(reversed(stops)) if rev else stops
    gradient = "linear-gradient(to right, " + ", ".join(f"rgb({r},{g},{b})" for r, g, b in stops_leg) + ")"
    lmin, lmax = ((_fmt_metric(hi), _fmt_metric(lo)) if rev
                  else (_fmt_metric(lo), _fmt_metric(hi)))
    # Truncate long category headers (they render vertically; keep them compact).
    col_hdrs = [(c if len(c) <= 20 else c[:19] + "…") for c in col_keys]
    return {"kind": "heatmap", "title": title, "columns": col_hdrs, "rows": rows_out,
            "wide": len(col_keys) > 8, "truncated": truncated,
            "legend_gradient": gradient, "legend_min": lmin, "legend_max": lmax}


def _widget_unit(cfg):
    """The Graylog unit for a widget's metric (from config.units, keyed by the
    field the series aggregates). Returns {'unit_type','abbrev'} or None."""
    import re
    units = cfg.get("units") or {}
    if not units:
        return None
    for s in (cfg.get("series") or []):
        m = re.search(r"\(([^)]+)\)", s.get("function") or "")
        field = m.group(1) if m else None
        if field and field in units:
            return units[field]
    for u in units.values():   # fallback: first unit defined
        return u
    return None


def _fmt_size(n, si=True):
    """Bytes → B/KB/MB/GB/… (SI 1000-based to match Graylog's Size/Byte)."""
    base = 1000.0 if si else 1024.0
    neg = n < 0
    n = abs(float(n))
    for u in ("B", "KB", "MB", "GB", "TB", "PB"):
        if n < base or u == "PB":
            s = f"{n:.0f} {u}" if u == "B" else f"{n:.1f} {u}"
            return ("-" + s) if neg else s
        n /= base
    return f"{n:.1f} EB"


def _fmt_unit(v, unit):
    """Format a value using a Graylog unit dict, else fall back to a raw number."""
    if not unit:
        return _fmt_metric(v)
    try:
        f = float(v)
    except (TypeError, ValueError):
        return _fmt_metric(v)
    ut = unit.get("unit_type")
    if ut == "size":
        return _fmt_size(f)
    if ut == "percent":
        return f"{f:.1f}%"
    # Any other Graylog unit (e.g. a custom abbrev) → append the abbrev so the
    # number isn't shown bare. No speculative time/duration humanising.
    abbrev = unit.get("abbrev")
    if abbrev:
        return f"{_fmt_metric(v)} {abbrev}"
    return _fmt_metric(v)


def _fmt_metric(v):
    """Raw number with thousands separators (like Graylog: 870,491) — NOT
    abbreviated to K/M/B."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v) if v is not None else "0"
    if f == int(f):
        return f"{int(f):,}"
    return f"{f:,.2f}"


def _metric_fn_field(fn):
    """'min(timestamp)' -> ('min', 'timestamp'); 'count()' -> ('count', '')."""
    import re
    m = re.match(r"\s*([a-zA-Z_]+)\s*\(([^)]*)\)", fn or "")
    if not m:
        return (fn or "").strip().lower(), ""
    return m.group(1).lower(), m.group(2).strip()


def _fmt_date_value(v):
    """Epoch-millis (Graylog date-metric result) -> local
    'YYYY-MM-DD HH:MM:SS.mmm'. Returns None if it isn't a plausible epoch."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    secs = f / 1000.0 if abs(f) >= 1e11 else f   # ms (Graylog date metrics) vs s
    try:
        dt = datetime.fromtimestamp(secs)
    except (OverflowError, OSError, ValueError):
        return None
    return dt.strftime("%Y-%m-%d %H:%M:%S") + f".{dt.microsecond // 1000:03d}"


def _fmt_metric_typed(v, fn, date_fields):
    """Format a metric value; when its aggregated field is a DATE type and the
    function preserves the timestamp (min/max/avg/latest/…, not count/card),
    render it as a datetime like Graylog does — not a raw epoch number."""
    if v is not None and date_fields is not None:
        func, field = _metric_fn_field(fn or "")
        if field and field in date_fields and func not in ("count", "card"):
            s = _fmt_date_value(v)
            if s is not None:
                return s
    return _fmt_metric(v)


def _fmt_iso_local(v):
    """Message-list date value ('2026-07-04T14:11:57.000Z') -> local
    'YYYY-MM-DD HH:MM:SS.mmm' (matches Graylog's message table timestamps)."""
    dt = _parse_ts(v)
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone()
    return dt.strftime("%Y-%m-%d %H:%M:%S") + f".{dt.microsecond // 1000:03d}"


async def _fetch_date_fields(c, base, auth, hdr, secs) -> set:
    """Ask Graylog which fields are DATE-typed (POST /api/views/fields) so metric
    values on those fields (e.g. min(timestamp)) render as datetimes. Best-effort:
    an empty set on any failure just means raw-number formatting (prior behaviour)."""
    try:
        body = {"streams": [], "timerange": {"type": "relative", "range": int(secs or 86400)}}
        r = await c.post(f"{base}/api/views/fields", auth=auth, headers=hdr, json=body)
        data = r.json()
        return {f.get("name") for f in data
                if isinstance(f, dict) and (f.get("type") or {}).get("type") == "date"}
    except Exception as e:
        log.debug("date-field lookup failed", error=str(e))
        return set()


# --------------------------------------------------------------------------
# Phase 2 — branded data sections from jt-glogarch's own data (reliable)
# --------------------------------------------------------------------------

def archive_summary_sections(db, lang: str = "zh-TW") -> tuple[dict, list[dict]]:
    """Executive KPIs + archive/job/audit charts from jt-glogarch's own DB."""
    L = {"zh-TW": {
            "kpi_arch": "封存份數", "kpi_msgs": "記錄總數", "kpi_size": "壓縮後大小", "kpi_orig": "原始大小",
            "sec_trend": "封存趨勢（近 30 天）", "trend_desc": "每日新增封存的記錄數。",
            "chart_msgs": "每日封存記錄數", "sec_jobs": "作業概況", "chart_jobs": "作業結果分布",
            "jobs_desc": "近期匯出／匯入／清除／驗證作業的結果。", "sec_audit": "操作稽核",
            "audit_desc": "近 7 天 Graylog 操作稽核統計。", "chart_ops": "每日操作次數",
            "ok": "成功", "failed": "失敗", "running": "執行中", "cancelled": "已取消"},
         "en": {
            "kpi_arch": "Archives", "kpi_msgs": "Total Records", "kpi_size": "Compressed", "kpi_orig": "Original",
            "sec_trend": "Archive Trend (last 30 days)", "trend_desc": "Records archived per day.",
            "chart_msgs": "Records archived / day", "sec_jobs": "Jobs Overview", "chart_jobs": "Job outcomes",
            "jobs_desc": "Recent export/import/cleanup/verify job results.", "sec_audit": "Operation Audit",
            "audit_desc": "Graylog operation audit — last 7 days.", "chart_ops": "Operations / day",
            "ok": "Completed", "failed": "Failed", "running": "Running", "cancelled": "Cancelled"}}
    t = L.get(lang, L["zh-TW"])

    stats = db.get_archive_stats()
    kpis = [
        {"value": _fmt_n(stats.get("total_archives", 0)), "label": t["kpi_arch"]},
        {"value": _fmt_n(stats.get("total_messages", 0)), "label": t["kpi_msgs"]},
        {"value": _fmt_bytes(stats.get("total_bytes", 0)), "label": t["kpi_size"]},
        {"value": _fmt_bytes(stats.get("total_original_bytes", 0) or 0), "label": t["kpi_orig"]},
    ]

    sections = []
    # 1) Archive trend (last 30 days)
    labels, values = _archive_daily(db, 30)
    if any(values):
        sections.append({"type": "charts", "title": t["sec_trend"], "description": t["trend_desc"],
                         "widgets": [{"kind": "chart", "title": t["chart_msgs"], "tall": True,
                                      "config": builder.line_chart(labels, [{"label": t["chart_msgs"], "data": values}])}]})
    # 2) Job outcomes (doughnut)
    jc = _job_outcomes(db)
    if sum(jc.values()):
        sections.append({"type": "charts", "title": t["sec_jobs"], "description": t["jobs_desc"],
                         "widgets": [{"kind": "chart", "title": t["chart_jobs"],
                                      "config": builder.pie_chart(
                                          [t["ok"], t["failed"], t["running"], t["cancelled"]],
                                          [jc["completed"], jc["failed"], jc["running"], jc["cancelled"]])}]})
    # 3) Audit ops per day (if available)
    try:
        alabels, avalues = _audit_daily(db, 7)
        if any(avalues):
            sections.append({"type": "charts", "title": t["sec_audit"], "description": t["audit_desc"],
                             "widgets": [{"kind": "chart", "title": t["chart_ops"],
                                          "config": builder.bar_chart(alabels, avalues, label=t["chart_ops"])}]})
    except Exception:
        pass

    header = {"kpis": kpis}
    return header, sections


def _archive_daily(db, days: int):
    labels, values = [], []
    today = datetime.now().date()
    rows = {}
    try:
        with db._lock:
            cur = db._conn.execute(
                "SELECT substr(time_to,1,10) d, SUM(message_count) m FROM archives "
                "WHERE status='completed' AND time_to >= ? GROUP BY d",
                ((today - timedelta(days=days)).isoformat(),))
            for r in cur.fetchall():
                rows[r[0]] = r[1] or 0
    except Exception:
        pass
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        labels.append(d.strftime("%m/%d"))
        values.append(int(rows.get(d.isoformat(), 0)))
    return labels, values


def _job_outcomes(db):
    out = {"completed": 0, "failed": 0, "running": 0, "cancelled": 0}
    try:
        with db._lock:
            cur = db._conn.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status")
            for st, n in cur.fetchall():
                if st in out:
                    out[st] = n
    except Exception:
        pass
    return out


def _audit_daily(db, days: int):
    labels, values = [], []
    today = datetime.now().date()
    rows = {}
    try:
        with db._lock:
            cur = db._conn.execute(
                "SELECT substr(timestamp,1,10) d, COUNT(*) FROM api_audit "
                "WHERE timestamp >= ? GROUP BY d",
                ((today - timedelta(days=days)).isoformat(),))
            for r in cur.fetchall():
                rows[r[0]] = r[1]
    except Exception:
        pass
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        labels.append(d.strftime("%m/%d"))
        values.append(int(rows.get(d.isoformat(), 0)))
    return labels, values


def _fmt_n(n):
    n = int(n or 0)
    if n >= 1_000_000_000: return f"{n/1e9:.1f}B"
    if n >= 1_000_000: return f"{n/1e6:.1f}M"
    if n >= 1_000: return f"{n/1e3:.1f}K"
    return str(n)


def _fmt_bytes(b):
    b = float(b or 0)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if b < 1024: return f"{b:.1f} {unit}" if unit != "B" else f"{int(b)} B"
        b /= 1024
    return f"{b:.1f} PB"
