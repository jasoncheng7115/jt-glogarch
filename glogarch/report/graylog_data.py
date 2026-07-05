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
) -> tuple[bytes | None, str]:
    """Log into the Graylog web UI with the given web credentials and screenshot
    a dashboard. Returns (PNG bytes, "") on success or (None, reason) on failure
    so the caller can show WHY the capture failed instead of a generic note."""
    from playwright.async_api import async_playwright
    base = server.url.rstrip("/")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
            ctx = await browser.new_context(ignore_https_errors=True,
                                            viewport={"width": 1600, "height": 1000},
                                            device_scale_factor=2)
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
                # The dashboard widget grid is a react-grid-layout container. We
                # screenshot ONLY that element so the Graylog top nav, the left
                # sidebar and the query/time bar are excluded. Scroll first so
                # every lazily-rendered widget is painted before capture.
                await _autoscroll_dashboard(page)
                try:
                    await page.wait_for_load_state("networkidle", timeout=20000)
                except Exception:
                    pass
                # Give every widget's chart a moment to finish drawing after its
                # data lands (scrolling only triggers the fetch).
                await page.wait_for_timeout(3500)
                grid = None
                for sel in (".react-grid-layout", "[data-testid='dashboard']", ".widget-list"):
                    grid = await page.query_selector(sel)
                    if grid:
                        break
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
    slices = []
    y = 0
    first = True
    while y < h:
        ph = first_h if first else rest_h
        part = im.crop((0, y, w, min(y + ph, h)))
        buf = BytesIO()
        part.save(buf, format="PNG")
        slices.append(png_to_data_uri(buf.getvalue()))
        y += ph
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
                                     abs_to: str | None = None) -> list[dict]:
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
                            trend_prev[wid] = _numeric_of(pr)
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
                widget = _messages_to_table(w.get("config") or {}, wt, res, message_rows, message_max_cols)
            else:
                if not res.get("rows"):
                    continue
                widget = _pivot_to_widget(w.get("config") or {}, wt, res, bar_horizontal=bar_horizontal,
                                          heatmap_values=heatmap_values)
            if widget:
                eff = res.get("effective_timerange") or {}
                es = _parse_ts(eff.get("from")) if eff.get("from") else None
                ee = _parse_ts(eff.get("to")) if eff.get("to") else None
                widget["range_label"] = _range_label(time_range_seconds, lang, start=es, end=ee)
                # Attach a trend badge to single-value widgets that enable it.
                if widget.get("kind") == "single" and wid in trend_prev:
                    pref = ((w.get("config") or {}).get("visualization_config") or {}).get("trend_preference", "NEUTRAL")
                    widget["trend"] = _compute_trend(_numeric_of(res), trend_prev[wid], pref)
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
                     heatmap_values: bool = False) -> dict | None:
    """Map a Graylog pivot result to one of our report widgets."""
    from glogarch.report import builder
    rows = res.get("rows") or []
    viz = cfg.get("visualization") or "table"
    row_pivots = cfg.get("row_pivots") or []
    col_pivots = cfg.get("column_pivots") or []
    is_time = bool(row_pivots) and (row_pivots[0].get("type") == "time")
    unit = _widget_unit(cfg)   # Graylog metric unit (e.g. size/bytes), or None

    # data rows only (drop rollup/total rows)
    drows = [r for r in rows if r.get("source") == "leaf"]
    if not drows:
        drows = rows

    # numeric single value: no row pivot (just a total)
    if viz == "numeric" or (not row_pivots):
        val = None
        # prefer the grand total
        tot = res.get("total")
        if drows:
            vv = drows[0].get("values") or []
            if vv:
                val = vv[0].get("value")
        if val is None:
            val = tot
        return {"kind": "single", "title": title, "value": _fmt_unit(val, unit), "label": ""}

    # A Graylog data table stays a table.
    if viz == "table":
        return _pivot_to_table(cfg, title, drows, col_pivots)
    # A geo/world-map is drawn as a self-contained SVG bubble map (the row key is
    # a "lat,long" geolocation string, the value is the count → bubble size).
    if viz in ("map", "world_map"):
        m = _pivot_to_map(title, drows)
        if m:
            return m
        return _pivot_to_table(cfg, title, drows, col_pivots)   # fallback if no coords
    # A heatmap stays a heatmap: a colour-graded grid of row-pivot × column-pivot.
    if viz == "heatmap":
        h = _pivot_to_heatmap(cfg, title, drows, col_pivots, show_values=heatmap_values)
        if h:
            return h
        return _pivot_to_table(cfg, title, drows, col_pivots)   # fallback if 1-D

    labels = [_rowkey(r) for r in drows]                       # keys (for lookups)
    disp = _time_axis_labels(drows) if is_time else labels     # display labels

    if not col_pivots:
        values = [_first_value(r) for r in drows]
        # No data at all → a clean "(no data)" note, not a broken empty chart.
        if not any((v or 0) for v in values):
            return {"kind": "empty", "title": title}
        if viz == "pie":
            top = sorted(zip(disp, values), key=lambda x: (x[1] or 0), reverse=True)[:8]
            return {"kind": "chart", "title": title,
                    "config": builder.pie_chart([l for l, _ in top], [v for _, v in top])}
        if is_time and viz != "bar":
            return {"kind": "chart", "title": title, "tall": True, "unit": unit,
                    "config": builder.line_chart(disp, [{"label": title, "data": values}])}
        if is_time and viz == "bar":
            return {"kind": "chart", "title": title, "tall": True, "unit": unit,
                    "config": _bar_multi(disp, [{"label": title, "data": values}], _barmode(cfg))}
        # non-time bar (cap to top 15). Vertical by default to match Graylog;
        # the report can opt into horizontal for long category labels.
        top = sorted(zip(disp, values), key=lambda x: (x[1] or 0), reverse=True)[:15]
        return {"kind": "chart", "title": title, "unit": unit,
                "config": builder.bar_chart([l for l, _ in top], [v for _, v in top],
                                            horizontal=bar_horizontal)}

    # column pivots -> multiple series (data keyed by raw rowkey, displayed via disp)
    series_map = {}
    order = []
    for r in drows:
        for v in (r.get("values") or []):
            if v.get("source") not in ("col-leaf", "leaf"):
                continue
            k = v.get("key") or []
            colname = " / ".join(str(x) for x in k[:-1]) or (k[0] if k else "")
            if colname not in series_map:
                series_map[colname] = {}
                order.append(colname)
            series_map[colname][_rowkey(r)] = v.get("value")
    series = [{"label": name, "data": [series_map[name].get(l, 0) for l in labels]} for name in order[:6]]
    if not any(any((v or 0) for v in s["data"]) for s in series):
        return {"kind": "empty", "title": title}
    if is_time and viz != "bar":
        return {"kind": "chart", "title": title, "tall": True, "unit": unit,
                "config": builder.line_chart(disp, series)}
    # bar: preserve Graylog's bar mode (grouped / stacked / overlay), incl. time bars
    return {"kind": "chart", "title": title, "tall": bool(is_time), "unit": unit,
            "config": _bar_multi(disp, series, _barmode(cfg))}


def _parse_ts(ts):
    from datetime import datetime
    s = str(ts).strip()
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


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
            out.append([hm, day])   # two-line label at a day boundary
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


def _pivot_to_table(cfg, title, drows, col_pivots):
    """Render a Graylog table widget as a report table (columns + rows)."""
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
        pivot_cols = sorted(pivot_cols)[:12]
        colnames = (total_cols if cfg.get("rollup") else []) + pivot_cols
        columns = rp_fields + colnames
        raw = []
        for r in drows[:40]:
            vmap = {" / ".join(str(x) for x in (v.get("key") or [])): v.get("value")
                    for v in (r.get("values") or [])}
            cells = [str(x) for x in (r.get("key") or [])]
            cells += [(_fmt_metric(vmap[c]) if vmap.get(c) is not None else "") for c in colnames]
            raw.append(cells)
        return {"kind": "table", "title": title, "columns": columns,
                "rows": _grouped_rows(raw, len(rp_fields)), "numeric_from": len(rp_fields)}
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
        for i, fn in enumerate(series_fns or [None]):
            if fn is not None and fn in vmap:
                val = vmap[fn]
            else:
                val = ordered[i] if i < len(ordered) else None
            cells.append(_fmt_metric(val) if val is not None else "")
        raw.append(cells)
    return {"kind": "table", "title": title, "columns": columns,
            "rows": _grouped_rows(raw, len(rp_fields)), "numeric_from": len(rp_fields)}


def _barmode(cfg: dict) -> str:
    """Graylog bar visualization mode: group | stack | relative | overlay."""
    vc = cfg.get("visualization_config") or {}
    return str(vc.get("barmode") or "group").lower()


def _bar_multi(labels, series, barmode="group"):
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
    return {"type": "bar", "data": {"labels": labels, "datasets": datasets},
            "options": {"responsive": True, "maintainAspectRatio": False,
                        "plugins": {"legend": {"display": len(datasets) > 1, "position": "bottom",
                                               "labels": {"padding": 16, "boxWidth": 14, "boxHeight": 12}}},
                        "scales": {"x": {"stacked": stacked,
                                         "ticks": {"autoSkip": True, "maxTicksLimit": 12,
                                                   "maxRotation": 0, "minRotation": 0}},
                                   "y": {"beginAtZero": True, "stacked": stacked}}}}


def _rowkey(r):
    k = r.get("key") or []
    s = " / ".join(str(x) for x in k)
    return (s[:40] + "…") if len(s) > 41 else (s or "-")


def _first_value(r):
    vv = r.get("values") or []
    for v in vv:
        if v.get("value") is not None:
            return v.get("value")
    return 0


def _numeric_of(res):
    """The single scalar value from a numeric widget's pivot result."""
    for r in (res.get("rows") or []):
        for v in (r.get("values") or []):
            if v.get("value") is not None:
                return v.get("value")
    return res.get("total")


def _compute_trend(cur, prev, preference="NEUTRAL"):
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
    dtxt = f"{sign}{_fmt_metric(abs(delta))}"
    ptxt = (f"{sign}{abs(pct):.1f}%") if pct is not None else ""
    return {"arrow": arrow, "delta": dtxt, "pct": ptxt, "cls": cls}


def _messages_to_table(cfg, title, res, max_rows, max_cols=0):
    """Render a Graylog message-list widget as a table (its configured fields,
    capped at max_rows). max_rows<=0 means no cap. If max_cols>0 and the widget
    has more configured fields than that, the widget is skipped (returns None) —
    wide message tables overflow the A4 page, so the report omits them."""
    fields = cfg.get("fields") or ["timestamp", "source", "message"]
    if max_cols and max_cols > 0 and len(fields) > max_cols:
        return None
    msgs = res.get("messages") or []
    total = len(msgs)
    if max_rows and max_rows > 0:
        msgs = msgs[:max_rows]
    rows = []
    for m in msgs:
        doc = m.get("message") or m
        cells = []
        for f in fields:
            v = doc.get(f, "")
            cells.append(str(v) if v is not None else "")
        rows.append(cells)
    if not rows:
        return None
    out = {"kind": "table", "title": title, "columns": list(fields), "rows": rows}
    # When a row cap actually truncated the widget, note it bottom-right.
    if max_rows and max_rows > 0 and total > max_rows:
        out["rows_note"] = f"僅顯示前 {max_rows:,} 筆"
    return out


def _pivot_to_map(title, drows):
    """Build a bubble world-map widget from a geo pivot (row key = 'lat,long')."""
    from glogarch.report import builder
    points = []
    for r in drows:
        k = r.get("key") or []
        if not k:
            continue
        try:
            parts = str(k[0]).split(",")
            lat = float(parts[0]); lon = float(parts[1])
        except (ValueError, IndexError):
            continue
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            points.append((lat, lon, _first_value(r) or 0))
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


def _heat_color(val, mx, scale="Viridis"):
    """Cell background from the widget's colour scale + a readable text colour.
    Empty cell = no fill."""
    if val is None or mx <= 0:
        return "transparent", "#9ca3af"
    ratio = max(0.0, min(1.0, (val or 0) / mx))
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
            if colname == "":
                continue
            if colname not in col_keys:
                col_keys.append(colname)
            matrix[rl][colname] = v.get("value")
    if not col_keys or not row_labels:
        return None
    # A4 can't scroll like Graylog's heatmap: a column pivot such as "dest port"
    # can have hundreds of values → an unreadable smear. Cap to the busiest rows
    # and columns (by total), matching what a reader actually cares about.
    MAX_COLS, MAX_ROWS = 15, 20
    col_total = {c: sum((matrix[rl].get(c) or 0) for rl in row_labels) for c in col_keys}
    row_total = {rl: sum((matrix[rl].get(c) or 0) for c in col_keys) for rl in row_labels}
    truncated = len(col_keys) > MAX_COLS or len(row_labels) > MAX_ROWS
    col_keys = sorted(col_keys, key=lambda c: -col_total[c])[:MAX_COLS]
    row_labels = sorted(row_labels, key=lambda rl: -row_total[rl])[:MAX_ROWS]
    vals = [matrix[rl].get(c) for rl in row_labels for c in col_keys if matrix[rl].get(c) is not None]
    mx = max(vals) if vals else 0
    rows_out = []
    for rl in row_labels:
        cells = []
        for c in col_keys:
            val = matrix[rl].get(c)
            bg, fg = _heat_color(val, mx, scale)
            txt = _fmt_metric(val) if (show_values and val is not None) else ""
            cells.append({"text": txt, "bg": bg, "fg": fg})
        rows_out.append({"label": rl, "cells": cells})
    # Colour-scale legend: a CSS gradient from the scale's low→high stops with
    # 0 and max labels (mirrors Graylog's heatmap colourbar).
    stops = _COLORSCALES.get(scale) or _COLORSCALES["Viridis"]
    gradient = "linear-gradient(to right, " + ", ".join(f"rgb({r},{g},{b})" for r, g, b in stops) + ")"
    # Truncate long category headers (they render vertically; keep them compact).
    col_hdrs = [(c if len(c) <= 20 else c[:19] + "…") for c in col_keys]
    return {"kind": "heatmap", "title": title, "columns": col_hdrs, "rows": rows_out,
            "wide": len(col_keys) > 8, "truncated": truncated,
            "legend_gradient": gradient, "legend_min": "0", "legend_max": _fmt_metric(mx)}


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
