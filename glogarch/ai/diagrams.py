# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Pictures an answer already holds, for the summary PDF (1.37).

Owner 2026-11-27: "有時序圖 的 有時間軸的 要轉成精美的圖放進去報告", "報告可以放的圖 要增加
不只是原本的那些widget圖類型", "有這類看板 也要轉成適合放pdf的". Kinds:
* ```html (a dashboard page), ```svg and ```mermaid blocks: drawn exactly as the chat's
  preview draws them (same document builder), in a headless Chromium context that is
  OFFLINE with every request refused, then captured as PNG and cut between widgets for
  the pages. Model-written content never reaches the network or jt-glogarch.
* a Markdown table whose cells are times (a start, and an end when there is one): drawn
  here as a timeline SVG, the same rules as the chat page's Timeline button
  (web/static/js/ai_export.js).
Nothing is asked again: these are the answer's own content.
"""

from __future__ import annotations

import html
import re
from datetime import datetime, timedelta, timezone

MAX_DIAGRAMS = 12
MERMAID_MAX = 20000          # characters of one diagram
TIMELINE_MAX_ROWS = 60

_BLOCK = re.compile(r"```[ \t]*(html|mermaid|svg)[ \t]*\n(.*?)\n```", re.S | re.I)
BLOCK_MAX = 400000           # characters of one page / drawing
CAPTURE_WIDTH = 1100         # CSS px the page is drawn at (scaled to the PDF's width)
CAPTURE_MAX_HEIGHT = 9000    # CSS px; a longer page is cut there
_FENCE_ANY = re.compile(r"```.*?```", re.S)
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$")


def _title_before(text: str, pos: int) -> str:
    """The nearest heading above a block, else the last short line before it."""
    lines = text[:pos].rstrip().splitlines()
    near = [ln for ln in lines[-3:] if ln.strip()]
    if near:     # a heading or a bold label right above wins over an older heading further up
        m = _HEADING.match(near[-1])
        if m:
            return _plain(m.group(1))
        if re.fullmatch(r"\s*\*\*[^*]{1,80}\*\*[：:]?\s*", near[-1]):
            return _plain(near[-1]).rstrip("：:")
    for ln in reversed(lines[-12:]):
        m = _HEADING.match(ln)
        if m:
            return _plain(m.group(1))
    for ln in reversed(lines[-3:]):
        s = _plain(ln)
        if s and len(s) <= 80 and not s.startswith("|"):
            return s.rstrip("：:")
    return ""


def _plain(s: str) -> str:
    s = re.sub(r"[*_`]+", "", s or "").strip()
    return s[:120]


# --- time cells -----------------------------------------------------------------

_T_FULL = re.compile(r"^(\d{4})[-/](\d{2})[-/](\d{2})[T ](\d{2}):(\d{2})(?::(\d{2})(?:[.,](\d{1,6}))?)?\s*(Z|[+-]\d{2}:?\d{2})?$")
_T_MD = re.compile(r"^(\d{1,2})[-/](\d{1,2})\s+(\d{1,2}):(\d{2})(?::(\d{2}))?$")
_T_HM = re.compile(r"^(\d{1,2}):(\d{2})(?::(\d{2})(?:[.,]\d+)?)?$")
_DAY0 = datetime(2000, 1, 1, tzinfo=timezone.utc)


def parse_time(s: str) -> datetime | None:
    """2026-11-27 10:00:00(.mmm)(Z|+08:00), 11/27 10:00(:00), 10:00(:00); None otherwise.
    A time without a zone is read as this host's local time (as the chat page reads the
    reader's); a time of day alone is on a fixed day, for order and length only."""
    s = str(s or "").strip()
    m = _T_FULL.match(s)
    if m:
        y, mo, d, h, mi, sec, frac, tz = m.groups()
        try:
            dt = datetime(int(y), int(mo), int(d), int(h), int(mi), int(sec or 0),
                          int((frac or "0")[:6].ljust(6, "0")))
        except ValueError:
            return None
        if tz:
            off = 0 if tz == "Z" else (1 if tz[0] == "+" else -1) * (int(tz[1:3]) * 60 + int(tz[-2:]))
            return dt.replace(tzinfo=timezone(timedelta(minutes=off)))
        return dt.astimezone()
    m = _T_MD.match(s)
    if m:
        mo, d, h, mi, sec = m.groups()
        try:
            return datetime(2000, int(mo), int(d), int(h), int(mi), int(sec or 0)).astimezone()
        except ValueError:
            return None
    m = _T_HM.match(s)
    if m and int(m.group(1)) < 24 and int(m.group(2)) < 60:
        return _DAY0.replace(hour=int(m.group(1)), minute=int(m.group(2)), second=int(m.group(3) or 0))
    return None


def _cells(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [_plain(c) for c in line.split("|")]


def _tables(text: str):
    """(position, header, rows) of each Markdown table outside code blocks."""
    masked = _FENCE_ANY.sub(lambda m: " " * len(m.group(0)), text)
    lines = masked.splitlines(keepends=True)
    pos, i = 0, 0
    starts = []
    for ln in lines:
        starts.append(pos)
        pos += len(ln)
    while i < len(lines) - 1:
        if lines[i].strip().startswith("|") and re.match(r"^\s*\|?\s*:?-{2,}", lines[i + 1]):
            head = _cells(lines[i])
            rows, j = [], i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                rows.append(_cells(lines[j]))
                j += 1
            yield starts[i], head, rows
            i = j
        else:
            i += 1


def timeline_of(head: list[str], rows: list[list[str]]) -> dict | None:
    """The same test as the page: a column is a time when >= 80% of its cells parse."""
    if len(rows) < 2 or not head:
        return None
    tcols = []
    for k in range(len(head)):
        vals = [r[k] for r in rows if k < len(r) and r[k]]
        if len(vals) >= 2 and sum(parse_time(v) is not None for v in vals) / len(vals) >= 0.8:
            tcols.append(k)
    if not tcols:
        return None
    a = tcols[0]
    b = tcols[1] if len(tcols) > 1 else None
    label_col = next((k for k in range(len(head)) if k not in tcols), None)
    out = []
    for r in rows[:TIMELINE_MAX_ROWS]:
        st = parse_time(r[a]) if a < len(r) else None
        if st is None:
            continue
        en = parse_time(r[b]) if b is not None and b < len(r) else None
        if en is not None and en < st and _T_HM.match(r[b] or "") and (st - en) < timedelta(days=1):
            en += timedelta(days=1)     # a time of day past midnight
        out.append({"label": r[label_col] if label_col is not None and label_col < len(r) else "",
                    "start": st, "end": en if en is not None and en >= st else None,
                    "start_text": r[a], "end_text": r[b] if b is not None and b < len(r) else ""})
    if len(out) < 2:
        return None
    # what kind of picture fits (owner 2026-11-27: start-only rows drawn as dots read as a scatter
    # plot): from-to rows are bars; a number per time is a series (columns); named events with a
    # time are a real timeline, in time order
    kind = "span" if any(r["end"] is not None for r in out) else "events"
    if kind == "events":
        nums = [_number(r["label"]) for r in out]
        if sum(n is not None for n in nums) / len(nums) >= 0.8:
            kind = "series"
            for r, n in zip(out, nums):
                r["value"] = n or 0.0
        else:
            extra = [k for k in range(len(head)) if k not in tcols and k != label_col][:2]
            src = [r for r in rows[:TIMELINE_MAX_ROWS] if a < len(r) and parse_time(r[a]) is not None]
            for r, raw in zip(out, src):
                r["note"] = " · ".join(f"{head[k]} {raw[k]}" for k in extra if k < len(raw) and raw[k])
    return {"rows": out, "kind": kind, "start_name": head[a], "end_name": head[b] if b is not None else "",
            "label_name": head[label_col] if label_col is not None else "",
            "more": max(0, len(rows) - TIMELINE_MAX_ROWS)}


def _number(v: str):
    v = (v or "").strip().replace(",", "")
    try:
        return float(v) if re.fullmatch(r"-?\d+(\.\d+)?", v) else None
    except ValueError:
        return None


def extract(message_id, text: str) -> list[dict]:
    """Diagram specs of one answer, in the order they appear."""
    found = []
    for m in _BLOCK.finditer(text or ""):
        kind, src = m.group(1).lower(), m.group(2).strip()
        if src:
            found.append((m.start(), {"kind": kind, "src": src[:MERMAID_MAX if kind == "mermaid" else BLOCK_MAX],
                                      "title": _title_before(text, m.start())}))
    for pos, head, rows in _tables(text or ""):
        tl = timeline_of(head, rows)
        if tl:
            found.append((pos, {"kind": "timeline", "timeline": tl, "title": _title_before(text, pos)}))
    found.sort(key=lambda x: x[0])
    out = []
    for n, (_, d) in enumerate(found[:MAX_DIAGRAMS]):
        d.update(id=f"m{message_id}-d{n}", message=message_id, query="", group_by=[], metrics=[])
        out.append(d)
    return out


# --- timeline SVG for the PDF ------------------------------------------------------

_STEPS_MIN = (1, 5, 10, 15, 30, 60, 120, 180, 360, 720, 1440, 2880, 10080)


def _fmt(dt: datetime, span_s: float, time_only: bool) -> str:
    d = dt if time_only else dt.astimezone()
    hm = d.strftime("%H:%M") + (d.strftime(":%S") if span_s < 3600 else "")
    return d.strftime("%m-%d ") + hm if span_s > 86400 and not time_only else hm


def _bars_too_short(tl: dict) -> bool:
    """From-to rows whose durations are invisible on the whole span (nine connections of a few
    seconds over three hours drew as dots): read better as events with their duration."""
    rows = tl["rows"]
    lo = min(r["start"] for r in rows)
    hi = max(r["end"] or r["start"] for r in rows)
    span = max((hi - lo).total_seconds(), 1.0)
    durs = [(r["end"] - r["start"]).total_seconds() for r in rows if r["end"] is not None]
    return bool(durs) and sum(d / span < 0.01 for d in durs) / len(durs) >= 0.6


def _dur(sec: float) -> str:
    sec = int(round(sec))
    return f"{sec}s" if sec < 60 else f"{sec // 60}m{sec % 60:02d}s" if sec < 3600 else f"{sec // 3600}h{sec % 3600 // 60:02d}m"


def timeline_svg(tl: dict, accent: str = "#6c63ff") -> str:
    kind = tl.get("kind") or ("span" if any(r["end"] is not None for r in tl["rows"]) else "events")
    if kind == "span" and _bars_too_short(tl):
        rows = []
        for r in tl["rows"]:
            note = f'{r["start_text"]} → {r["end_text"]}' + (f' ({_dur((r["end"] - r["start"]).total_seconds())})' if r["end"] else "")
            rows.append(dict(r, note=(r.get("note") + " · " if r.get("note") else "") + note))
        tl = dict(tl, rows=rows, kind="events")
        kind = "events"
    if kind == "events":
        return _events_svg(tl, accent)
    if kind == "series":
        return _series_svg(tl, accent)
    return _span_svg(tl, accent)


def _events_svg(tl: dict, accent: str) -> str:
    """A real timeline: events in time order down a line, the time on the left, what happened on the right."""
    rows = sorted(tl["rows"], key=lambda r: r["start"])
    span = max((rows[-1]["start"] - rows[0]["start"]).total_seconds(), 1.0)
    time_only = rows[0]["start"].tzinfo is timezone.utc and rows[0]["start"].date() == _DAY0.date()
    esc = lambda v: html.escape(str(v), quote=True)
    W, TX, LX, NX, top = 760, 150, 172, 192, 14
    parts, ys, y, last_day = [], [], top, None
    for r in rows:
        d = r["start"] if time_only else r["start"].astimezone()
        day = d.strftime("%m-%d")
        tlabel = d.strftime("%H:%M") + (d.strftime(":%S") if span < 3600 else "")
        if not time_only and span > 86400 and day != last_day:
            tlabel = f"{day} {tlabel}"
        last_day = day
        h = 46 if r.get("note") else 32
        cy = y + 12
        ys.append(cy)
        label = r["label"] if len(r["label"]) <= 60 else r["label"][:59] + "…"
        parts.append(f'<text x="{TX}" y="{cy + 4.5}" text-anchor="end" font-size="13" fill="#6b7280">{esc(tlabel)}</text>'
                     f'<circle cx="{LX}" cy="{cy}" r="6" fill="{accent}" stroke="#ffffff" stroke-width="2.5"/>'
                     f'<text x="{NX}" y="{cy + 4.5}" font-size="13.5" font-weight="600" fill="#1f2430">{esc(label)}</text>')
        if r.get("note"):
            note = r["note"] if len(r["note"]) <= 90 else r["note"][:89] + "…"
            parts.append(f'<text x="{NX}" y="{cy + 22}" font-size="12" fill="#6b7280">{esc(note)}</text>')
        y += h
    line = f'<line x1="{LX}" x2="{LX}" y1="{ys[0]}" y2="{ys[-1]}" stroke="#d6d9e6" stroke-width="2"/>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {y + 4}" width="100%" role="img">'
            + line + "".join(parts) + "</svg>")


def _series_svg(tl: dict, accent: str) -> str:
    """A number per time: columns in time order on a value axis."""
    rows = sorted(tl["rows"], key=lambda r: r["start"])
    span = max((rows[-1]["start"] - rows[0]["start"]).total_seconds(), 1.0)
    time_only = rows[0]["start"].tzinfo is timezone.utc and rows[0]["start"].date() == _DAY0.date()
    esc = lambda v: html.escape(str(v), quote=True)
    W, L, R, top, H = 760, 56, 16, 18, 280
    base = H - 36
    vmax = max((r["value"] for r in rows), default=0) or 1
    mag = 10 ** max(0, len(str(int(vmax))) - 1)
    nice = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= vmax)
    parts = []
    for i in range(5):
        v = nice * i / 4
        y = base - (base - top) * i / 4
        txt = f"{v:,.0f}" if v == int(v) else f"{v:,.1f}"
        parts.append(f'<line x1="{L}" x2="{W - R}" y1="{y:.1f}" y2="{y:.1f}" stroke="#e5e7eb"/>'
                     f'<text x="{L - 8}" y="{y + 4:.1f}" text-anchor="end" font-size="12" fill="#6b7280">{txt}</text>')
    n = len(rows)
    slot = (W - L - R) / n
    bw = max(4.0, min(48.0, slot * 0.62))
    every = max(1, -(-n // 12))
    for i, r in enumerate(rows):
        cx = L + slot * (i + 0.5)
        hgt = (base - top) * r["value"] / nice
        parts.append(f'<rect x="{cx - bw / 2:.1f}" y="{base - hgt:.1f}" width="{bw:.1f}" height="{max(hgt, 0.5):.1f}" rx="3" fill="{accent}"/>')
        if n <= 24 and r["value"]:
            v = r["value"]
            parts.append(f'<text x="{cx:.1f}" y="{base - hgt - 5:.1f}" text-anchor="middle" font-size="11.5" fill="#374151">'
                         f'{(f"{v:,.0f}" if v == int(v) else f"{v:,.1f}")}</text>')
        if i % every == 0:
            parts.append(f'<text x="{cx:.1f}" y="{base + 20}" text-anchor="middle" font-size="12" fill="#6b7280">'
                         f'{esc(_fmt(r["start"], span, time_only))}</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" role="img">'
            + "".join(parts) + "</svg>")


def _span_svg(tl: dict, accent: str) -> str:
    """Bars from start to end, points without an end, round time steps; every text escaped."""
    rows = tl["rows"]
    lo = min(r["start"] for r in rows)
    hi = max(r["end"] or r["start"] for r in rows)
    span = max((hi - lo).total_seconds(), 1.0)
    time_only = lo.tzinfo is timezone.utc and lo.date() == _DAY0.date()
    W, L, R, row_h, top, axis_h = 760, 200, 18, 28, 8, 34     # drawn into the PDF at ~640 px: 13 px text reads at ~11
    H = top + len(rows) * row_h + axis_h
    x = lambda dt: L + (dt - lo).total_seconds() / span * (W - L - R)
    esc = lambda s: html.escape(str(s), quote=True)
    step = next((m * 60 for m in _STEPS_MIN if span / (m * 60) <= 6), 10080 * 60)
    base = lo if time_only else lo.astimezone()
    first = base.replace(second=0, microsecond=0)
    off = (first.utcoffset() or timedelta(0)).total_seconds()
    k = -(-((first.timestamp() + off) // 1) // step)      # ceil, on the local clock
    parts = []
    t = datetime.fromtimestamp(k * step - off, tz=first.tzinfo)
    while t <= hi:
        if t >= lo:
            px = x(t)
            anchor = "start" if px < L + 20 else "end" if px > W - R - 20 else "middle"
            parts.append(f'<line x1="{px:.1f}" x2="{px:.1f}" y1="{top}" y2="{H - axis_h}" stroke="#e5e7eb" stroke-width="1"/>'
                         f'<text x="{px:.1f}" y="{H - axis_h + 20}" text-anchor="{anchor}" font-size="13" fill="#6b7280">'
                         f'{esc(_fmt(t, span, time_only))}</text>')
        t += timedelta(seconds=step)
    for i, r in enumerate(rows):
        y = top + i * row_h
        label = r["label"] if len(r["label"]) <= 26 else r["label"][:25] + "…"
        parts.append(f'<text x="{L - 10}" y="{y + row_h / 2 + 4.5:.1f}" text-anchor="end" font-size="13" fill="#1f2430">'
                     f'{esc(label)}</text>')
        if r["end"] is not None and x(r["end"]) - x(r["start"]) >= 3:
            parts.append(f'<rect x="{x(r["start"]):.1f}" y="{y + 6}" width="{x(r["end"]) - x(r["start"]):.1f}" '
                         f'height="{row_h - 12}" rx="4" fill="{accent}"/>')
        else:
            parts.append(f'<circle cx="{x(r["start"]):.1f}" cy="{y + row_h / 2:.1f}" r="6" fill="{accent}" '
                         f'stroke="#ffffff" stroke-width="2"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" role="img">'
            + "".join(parts) + "</svg>")


async def capture(specs: list[dict]) -> dict:
    """{id: {"ok", "slices": [data URI ...]} | {"ok": False, "error"}} for the html / svg /
    mermaid specs. One browser for all; the context is offline and refuses every request."""
    todo = [s for s in specs if s["kind"] in ("html", "svg", "mermaid")]
    if not todo:
        return {}
    from playwright.async_api import async_playwright
    from glogarch.report.graylog_data import png_to_data_uri, slice_tall_png
    from glogarch.web.routes.ai import preview_document
    out: dict = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage",
                                                "--font-render-hinting=none"])
        try:
            ctx = await browser.new_context(viewport={"width": CAPTURE_WIDTH, "height": 800}, color_scheme="light",
                                            device_scale_factor=2, offline=True, java_script_enabled=True)
            await ctx.route("**/*", lambda route: route.abort())     # nothing leaves this page
            for s in todo:
                page = await ctx.new_page()
                try:
                    await page.set_content(preview_document(s["kind"], s["src"], "light"), wait_until="load",
                                           timeout=20000)
                    if s["kind"] == "mermaid":
                        await page.wait_for_selector("pre.mermaid svg, pre.err", timeout=15000)
                    else:
                        await page.wait_for_timeout(1500)      # charts drawing (Chart.js animates)
                    if s["kind"] == "mermaid" and await page.query_selector("pre.err"):
                        raise RuntimeError((await page.inner_text("pre.err"))[:200])
                    if s["kind"] in ("mermaid", "svg"):
                        # the drawing itself, not the page around it (a small diagram sat in a sea of white)
                        el = await page.query_selector("pre.mermaid svg" if s["kind"] == "mermaid" else "svg")
                        if el is None:
                            raise RuntimeError("nothing was drawn")
                        box = await el.bounding_box() or {}
                        png = await el.screenshot()
                        out[s["id"]] = {"ok": True, "slices": [png_to_data_uri(png)],
                                        "width": int(box.get("width") or CAPTURE_WIDTH)}
                        continue
                    # a report page is light: a dashboard the model wrote for the dark chat theme is
                    # turned light before the shot (owner 2026-11-27: "報告放的看板必須是淺色/白色主題")
                    await page.evaluate(LIGHTEN_JS)
                    await page.wait_for_timeout(100)
                    # measure with a short viewport: scrollHeight is never less than the viewport
                    await page.set_viewport_size({"width": CAPTURE_WIDTH, "height": 100})
                    await page.wait_for_timeout(300)
                    h = await page.evaluate("Math.min(document.documentElement.scrollHeight, %d)" % CAPTURE_MAX_HEIGHT)
                    await page.set_viewport_size({"width": CAPTURE_WIDTH, "height": max(120, int(h))})
                    await page.wait_for_timeout(400)          # charts redraw at the new size
                    # the dashboard's own blocks, one picture each, so the report can lay them out like
                    # widgets and never cut one at a page end (owner 2026-11-27: "一個一個拆過來放組合")
                    rects = await page.evaluate(BLOCKS_JS)
                    blocks = []
                    for r in rects or []:
                        clip = {"x": max(0, r["x"] - 2), "y": max(0, r["y"] - 2),
                                "width": min(CAPTURE_WIDTH, r["w"] + 4), "height": min(CAPTURE_MAX_HEIGHT, r["h"] + 4)}
                        if clip["width"] < 20 or clip["height"] < 16:
                            continue
                        blocks.append({"img": png_to_data_uri(await page.screenshot(clip=clip)),
                                       "width": int(clip["width"]), "height": int(clip["height"]), "half": bool(r["half"])})
                    if len(blocks) >= 2:
                        out[s["id"]] = {"ok": True, "blocks": blocks, "width": CAPTURE_WIDTH}
                        continue
                    png = await page.screenshot(full_page=False)
                    slices = slice_tall_png(png) if h > 1400 else [png_to_data_uri(png)]
                    out[s["id"]] = {"ok": True, "slices": slices, "width": CAPTURE_WIDTH}
                except Exception as e:       # one drawing that fails says why; the others go on
                    out[s["id"]] = {"ok": False, "error": str(e)[:300] or type(e).__name__}
                finally:
                    await page.close()
        finally:
            await browser.close()
    return out


# Dark page -> light page for the PDF: invert, turn the hues back, and invert photos again so they
# look as they were. Colours keep their hue (a red bar stays red), dark backgrounds become white.
LIGHTEN_JS = r"""() => {
  const rgb = (c) => { const m = /rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?/.exec(c || '');
    return m && (m[4] === undefined || +m[4] > 0.5) ? [+m[1], +m[2], +m[3]] : null; };
  const lum = (c) => (0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]) / 255;
  const root = document.documentElement, body = document.body;
  let bg = rgb(getComputedStyle(body).backgroundColor) || rgb(getComputedStyle(root).backgroundColor);
  if (!bg) {                       // a page whose colour sits on its first full-width block
    const big = [...body.children].find((e) => e.getBoundingClientRect().width >= innerWidth * 0.9);
    bg = big && rgb(getComputedStyle(big).backgroundColor);
  }
  if (!bg || lum(bg) >= 0.45) return false;
  // the page's own dark ground turns pure white (its inverse would be a pale tint)
  root.style.background = '#000';
  if (rgb(getComputedStyle(body).backgroundColor)) body.style.backgroundColor = '#000';
  root.style.filter = 'invert(1) hue-rotate(180deg)';
  const st = document.createElement('style');
  st.textContent = 'img, video, picture, [style*="background-image"] { filter: invert(1) hue-rotate(180deg); }';
  document.head.appendChild(st);
  return true;
}"""


# The blocks of a model-written dashboard: boxed panels (cards, charts, tables), a row of small tiles
# as one block, and the loose text between them (headings, notes) as bands. Page coordinates.
BLOCKS_JS = r"""() => {
  const W = document.documentElement.clientWidth, MAXH = 1250;
  const pageBg = getComputedStyle(document.body).backgroundColor;
  const clear = (c) => !c || /rgba\(0, 0, 0, 0\)/.test(c) || c === 'transparent';
  const boxed = (el) => { const cs = getComputedStyle(el);
    const bg = cs.backgroundColor, hasBg = !clear(bg) && bg !== pageBg;
    const border = ['Top', 'Right', 'Bottom', 'Left'].some((d) => parseFloat(cs['border' + d + 'Width']) > 0 && cs['border' + d + 'Style'] !== 'none');
    return hasBg || border || (cs.boxShadow && cs.boxShadow !== 'none'); };
  const rect = (el) => { const b = el.getBoundingClientRect(); return {x: b.left + scrollX, y: b.top + scrollY, w: b.width, h: b.height}; };
  const blocks = [];
  const visit = (el) => {
    for (const c of el.children) {
      if (['SCRIPT', 'STYLE', 'TEMPLATE'].includes(c.tagName)) continue;
      const r = c.getBoundingClientRect();
      if (r.width < 10 || r.height < 10) continue;
      const kids = [...c.children].filter((k) => { const b = k.getBoundingClientRect(); return b.width > 40 && b.height > 28; });
      const tiles = kids.length >= 2 && kids.every((k) => boxed(k) && k.getBoundingClientRect().width < W * 0.3)
                    && kids.every((k) => Math.abs(k.getBoundingClientRect().top - kids[0].getBoundingClientRect().top) < r.height);
      if (r.width >= W * 0.45 && tiles && r.height <= MAXH) { blocks.push(c); continue; }
      if (r.width >= W * 0.28 && r.height >= 50 && boxed(c) && (r.height <= MAXH || !c.querySelector('*'))) {
        // a wrapper around the whole page is not a block: look inside it
        const inner = [...c.querySelectorAll('*')].filter((k) => boxed(k) && k.getBoundingClientRect().width >= W * 0.28 && k.getBoundingClientRect().height >= 50);
        if (r.width >= W * 0.9 && inner.length >= 2 && r.height > 600) { visit(c); continue; }
        blocks.push(c); continue;
      }
      visit(c);
    }
  };
  visit(document.body);
  const rs = blocks.map((b) => Object.assign(rect(b), {half: b.getBoundingClientRect().width < W * 0.6}));
  // loose text outside every block: headings and notes, merged into full-width bands
  const inBlock = (el) => blocks.some((b) => b.contains(el));
  const bands = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const n = walker.currentNode, p = n.parentElement;
    if (!n.textContent.trim() || !p || inBlock(p) || ['SCRIPT', 'STYLE'].includes(p.tagName)) continue;
    const r = rect(p);
    if (r.h < 4) continue;
    const hit = bands.find((b) => r.y < b.y + b.h + 10 && r.y + r.h > b.y - 10);
    if (hit) { const top = Math.min(hit.y, r.y), bot = Math.max(hit.y + hit.h, r.y + r.h); hit.y = top; hit.h = bot - top;
               hit.x = Math.min(hit.x, r.x); hit.w = Math.max(hit.x + hit.w, r.x + r.w) - hit.x; }
    else bands.push({x: r.x, y: r.y, w: r.w, h: r.h, half: false});
  }
  return rs.concat(bands.filter((b) => !rs.some((r) => b.y >= r.y && b.y + b.h <= r.y + r.h)))
           .sort((a, b) => (a.y - b.y) || (a.x - b.x));
}"""


def report_widget(spec: dict, title: str = "", shot: dict | None = None) -> dict:
    title = title or spec.get("title") or ""
    if spec["kind"] in ("html", "svg", "mermaid"):
        shot = shot or {}
        if not shot.get("ok"):
            return {"kind": "none", "title": title, "description": shot.get("error") or ""}
        if shot.get("blocks"):
            return {"kind": "blocks", "title": title, "blocks": shot["blocks"]}
        # drawn at 2x: CSS width = what it measured on the page, never wider than the card
        return {"kind": "image", "title": title, "slices": shot["slices"],
                "img_width": min(int(shot.get("width") or CAPTURE_WIDTH), CAPTURE_WIDTH), "tall": len(shot["slices"]) > 1}
    tl = spec["timeline"]
    w = {"kind": "svg", "title": title, "svg": timeline_svg(tl),
         "description": tl["start_name"] + (" → " + tl["end_name"] if tl["end_name"] else "")}
    return w
