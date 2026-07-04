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


def _basic_auth(server):
    if server.auth_token:
        return httpx.BasicAuth(server.auth_token, "token")
    return httpx.BasicAuth(server.username or "", server.password or "")


async def capture_dashboard_png(
    server, dashboard_id: str, *, web_username: str, web_password: str,
    time_range_seconds: int = 86400, wait_ms: int = 6000,
) -> bytes | None:
    """Log into the Graylog web UI with the given web credentials and screenshot
    a dashboard. Returns PNG bytes, or None on failure (caller degrades)."""
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
                await page.goto(base, wait_until="domcontentloaded")
                # Graylog login form: username + password inputs.
                await page.wait_for_selector('input[name="username"], input#username',
                                             timeout=15000)
                await page.fill('input[name="username"], input#username', web_username)
                await page.fill('input[name="password"], input#password', web_password)
                await page.click('button[type="submit"], button:has-text("Sign in"), button:has-text("登入")')
                await page.wait_for_timeout(2500)
                # Navigate to the dashboard and let widgets render.
                await page.goto(f"{base}/dashboards/{dashboard_id}", wait_until="networkidle")
                await page.wait_for_timeout(wait_ms)
                png = await page.screenshot(full_page=True)
                return png
            finally:
                await browser.close()
    except Exception as e:
        log.warning("capture_dashboard_png failed", dashboard=dashboard_id, error=str(e))
        return None


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
                                     lang: str = "zh-TW") -> list[dict]:
    """Return report `sections` reconstructed from a Graylog dashboard's widgets.
    Empty list on failure (caller degrades)."""
    auth = _basic_auth(server)
    base = server.url.rstrip("/")
    hdr = {"Accept": "application/json", "Content-Type": "application/json", "X-Requested-By": "jt-glogarch"}
    try:
        async with httpx.AsyncClient(verify=server.verify_ssl, timeout=30.0) as c:
            view = (await c.get(f"{base}/api/views/{dashboard_id}", auth=auth, headers=hdr)).json()
            title = view.get("title") or dashboard_id
            sid = view.get("search_id")
            states = view.get("state") or {}
            if not sid or not states:
                return []
            # Execute the dashboard's search and poll the async job to COMPLETION
            # (a heavy multi-tab dashboard finishes tab-by-tab; a partial result
            # would miss some tabs' widgets).
            ex = (await c.post(f"{base}/api/views/search/{sid}/execute", auth=auth, headers=hdr,
                               json={"global_override": {"timerange": {"type": "relative", "range": time_range_seconds}}})).json()
            results = ex.get("results") or {}
            job = ex.get("id")
            done = (ex.get("execution") or {}).get("done")
            waited = 0.0
            while not done and job and waited < 120:
                await __import_asyncio_sleep(2.0)
                waited += 2.0
                pj = (await c.get(f"{base}/api/views/search/status/{job}", auth=auth, headers=hdr)).json()
                done = (pj.get("execution") or {}).get("done")
                if done:
                    results = pj.get("results") or {}
    except Exception as e:
        log.warning("rebuild_dashboard failed", dashboard=dashboard_id, error=str(e))
        return []

    # Correlate PER STATE (tab): a state's widgets map to that state's results.
    rendered = []
    for state_id, state in states.items():
        if len(rendered) >= max_widgets:
            break
        st_res = ((results.get(state_id) or {}).get("search_types")) or {}
        if not st_res:
            continue
        wmap = state.get("widget_mapping") or {}
        titles = ((state.get("titles") or {}).get("widget")) or {}
        positions = state.get("positions") or {}

        def _pos(w):
            p = positions.get(w.get("id"), {}) or {}
            return (p.get("row", 999), p.get("col", 999))

        widgets = sorted([w for w in (state.get("widgets") or [])
                          if w.get("type") == "aggregation"], key=_pos)
        for w in widgets:
            if len(rendered) >= max_widgets:
                break
            wid = w.get("id")
            res = None
            for sid2 in (wmap.get(wid) or [wid]):
                if sid2 in st_res:
                    res = st_res[sid2]
                    break
            if not res or not res.get("rows"):
                continue
            wt = titles.get(wid) or _widget_autotitle(w) or wid[:8]
            widget = _pivot_to_widget(w.get("config") or {}, wt, res)
            if widget:
                rendered.append(widget)

    if not rendered:
        return []
    return [{"type": "charts", "title": title,
             "description": _rebuild_desc(lang, len(rendered), time_range_seconds),
             "widgets": rendered}]


async def __import_asyncio_sleep(sec):
    import asyncio
    await asyncio.sleep(sec)


def _rebuild_desc(lang, n, secs):
    hrs = secs // 3600
    if lang == "zh-TW":
        return f"由 Graylog 儀表板重建的 {n} 個 widget（時間範圍：近 {hrs} 小時）。"
    return f"{n} widgets rebuilt from the Graylog dashboard (time range: last {hrs}h)."


def _widget_autotitle(w):
    c = w.get("config") or {}
    series = c.get("series") or []
    rp = c.get("row_pivots") or []
    fn = series[0].get("function") if series else ""
    field = (rp[0].get("fields") or [""])[0] if rp else ""
    return (f"{fn} by {field}".strip() if (fn or field) else "")


def _pivot_to_widget(cfg: dict, title: str, res: dict) -> dict | None:
    """Map a Graylog pivot result to one of our report widgets."""
    from glogarch.report import builder
    rows = res.get("rows") or []
    viz = cfg.get("visualization") or "table"
    row_pivots = cfg.get("row_pivots") or []
    col_pivots = cfg.get("column_pivots") or []
    is_time = bool(row_pivots) and (row_pivots[0].get("type") == "time")

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
        return {"kind": "single", "title": title, "value": _fmt_metric(val), "label": ""}

    labels = [_rowkey(r) for r in drows]

    if not col_pivots:
        values = [_first_value(r) for r in drows]
        if viz == "pie":
            top = sorted(zip(labels, values), key=lambda x: (x[1] or 0), reverse=True)[:8]
            return {"kind": "chart", "title": title,
                    "config": builder.pie_chart([l for l, _ in top], [v for _, v in top])}
        if is_time:
            return {"kind": "chart", "title": title, "tall": True,
                    "config": builder.line_chart(labels, [{"label": title, "data": values}])}
        # bar (cap to top 15 for readability)
        top = sorted(zip(labels, values), key=lambda x: (x[1] or 0), reverse=True)[:15]
        return {"kind": "chart", "title": title,
                "config": builder.bar_chart([l for l, _ in top], [v for _, v in top],
                                            horizontal=len(top) > 6)}

    # column pivots -> multiple series
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
    if is_time:
        return {"kind": "chart", "title": title, "tall": True,
                "config": builder.line_chart(labels, series)}
    # grouped bar
    from glogarch.report.builder import PALETTE
    datasets = [{"label": s["label"], "data": s["data"], "backgroundColor": PALETTE[i % len(PALETTE)]}
                for i, s in enumerate(series)]
    return {"kind": "chart", "title": title,
            "config": {"type": "bar", "data": {"labels": labels, "datasets": datasets},
                       "options": {"responsive": True, "maintainAspectRatio": False,
                                   "plugins": {"legend": {"display": True}},
                                   "scales": {"y": {"beginAtZero": True}}}}}


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


def _fmt_metric(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return str(v) if v is not None else "0"
    if v >= 1_000_000_000:
        return f"{v/1e9:.1f}B"
    if v >= 1_000_000:
        return f"{v/1e6:.1f}M"
    if v >= 1_000:
        return f"{v/1e3:.1f}K"
    return str(int(v)) if v == int(v) else f"{v:.1f}"


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
