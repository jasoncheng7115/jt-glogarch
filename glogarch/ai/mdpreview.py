# SPDX-License-Identifier: AGPL-3.0-or-later
"""Markdown the model wrote, as a page for the sandboxed preview pane.

Owner 2026-11-27: "如果內容是 markdown 原始格式 ... 也會有預覽可以用嗎". A small,
escape-first renderer (no dependency): everything is HTML-escaped BEFORE any
formatting, links only for http(s), images are not loaded (the preview has no
network) but shown as their text. ```mermaid inside it becomes a diagram.
"""
from __future__ import annotations

import html
import re

_FENCE_OPEN = re.compile(r"^(```|~~~)\s*([A-Za-z0-9_+-]*)\s*$")
_HR = re.compile(r"^\s{0,3}([-*_])(\s*\1){2,}\s*$")
_HEAD = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_LIST = re.compile(r"^\s*([-*+]|\d+[.)])\s+(.*)$")
_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")


def _inline(s: str) -> str:
    """`s` is already escaped."""
    codes: list[str] = []

    def keep(m):
        codes.append(f"<code>{m.group(1)}</code>")
        return f"\x00{len(codes) - 1}\x00"
    s = re.sub(r"`([^`]+)`", keep, s)
    # images: no network in the preview, show what they are
    s = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)", lambda m: f"<span class=\"img\">[{m.group(1) or 'image'}]</span>", s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
               lambda m: f"<a href=\"{m.group(2)}\" rel=\"noopener noreferrer\">{m.group(1)}</a>", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"__(.+?)__", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
    s = re.sub(r"(?<![\w_])_(?!\s)(.+?)(?<!\s)_(?![\w_])", r"<em>\1</em>", s)
    s = re.sub(r"~~(.+?)~~", r"<del>\1</del>", s)
    return re.sub(r"\x00(\d+)\x00", lambda m: codes[int(m.group(1))], s)


def _cells(row: str) -> list[str]:
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]
    return [c.strip() for c in row.split("|")]


def render(src: str) -> tuple[str, bool]:
    """(HTML body, has a mermaid diagram)."""
    lines = html.escape(src or "", quote=True).split("\n")
    out: list[str] = []
    mermaid = False
    i = 0
    while i < len(lines):
        ln = lines[i]
        m = _FENCE_OPEN.match(ln)
        if m:
            fence, lang = m.group(1), m.group(2).lower()
            buf = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith(fence):
                buf.append(lines[i])
                i += 1
            i += 1
            if lang == "mermaid":
                mermaid = True
                out.append(f"<pre class=\"mermaid\">{chr(10).join(buf)}</pre>")
            else:
                out.append(f"<pre><code>{chr(10).join(buf)}</code></pre>")
            continue
        if not ln.strip():
            i += 1
            continue
        if _HR.match(ln):
            out.append("<hr>")
            i += 1
            continue
        h = _HEAD.match(ln)
        if h:
            n = len(h.group(1))
            out.append(f"<h{n}>{_inline(h.group(2))}</h{n}>")
            i += 1
            continue
        if "|" in ln and i + 1 < len(lines) and _TABLE_SEP.match(lines[i + 1]):
            head = _cells(ln)
            i += 2
            rows = []
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                rows.append(_cells(lines[i]))
                i += 1
            out.append("<table><thead><tr>" + "".join(f"<th>{_inline(c)}</th>" for c in head) + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>" for r in rows)
                       + "</tbody></table>")
            continue
        if ln.lstrip().startswith("&gt;"):
            buf = []
            while i < len(lines) and lines[i].lstrip().startswith("&gt;"):
                buf.append(lines[i].lstrip()[4:].lstrip())
                i += 1
            out.append("<blockquote>" + "<br>".join(_inline(b) for b in buf) + "</blockquote>")
            continue
        lm = _LIST.match(ln)
        if lm:
            ordered = lm.group(1)[0].isdigit()
            items = []
            while i < len(lines) and _LIST.match(lines[i]):
                items.append(_inline(_LIST.match(lines[i]).group(2)))
                i += 1
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{x}</li>" for x in items) + f"</{tag}>")
            continue
        para = []
        while i < len(lines) and lines[i].strip() and not (
                _FENCE_OPEN.match(lines[i]) or _HEAD.match(lines[i]) or _HR.match(lines[i])
                or _LIST.match(lines[i]) or lines[i].lstrip().startswith("&gt;")):
            para.append(_inline(lines[i]))
            i += 1
        if para:
            out.append("<p>" + "<br>".join(para) + "</p>")
        else:   # a line no rule took
            out.append(f"<p>{_inline(ln)}</p>")
            i += 1
    return "\n".join(out), mermaid


CSS = {
    "light": ("--bg:#ffffff;--fg:#1c1e2b;--muted:#5e6277;--line:#d9dce4;--code:#f3f4f7;--head:#f6f7f9;"
              "--link:#4a42cc;"),
    "dark": ("--bg:#12131c;--fg:#eef0f5;--muted:#a2a6ba;--line:#363a50;--code:#1e2030;--head:#1b1d2a;"
             "--link:#a29cff;"),
}


def page_style(theme: str) -> str:
    v = CSS.get(theme, CSS["light"])
    return ("<style>:root{" + v + "}body{margin:0;padding:20px 24px;background:var(--bg);color:var(--fg);"
            "font-family:system-ui,-apple-system,'Segoe UI','PingFang TC','Noto Sans TC','Microsoft JhengHei',sans-serif;"
            "line-height:1.65;font-size:15px}h1,h2,h3,h4{line-height:1.3;margin:1.2em 0 .5em}"
            "h1{font-size:1.6em;border-bottom:1px solid var(--line);padding-bottom:.3em}h2{font-size:1.3em}"
            "code{background:var(--code);padding:1px 5px;border-radius:4px;font-size:.9em}"
            "pre{background:var(--code);padding:12px 14px;border-radius:6px;overflow:auto}pre code{background:none;padding:0}"
            "pre.mermaid{background:none;text-align:center}"
            "table{border-collapse:collapse;margin:12px 0}th,td{border:1px solid var(--line);padding:6px 10px;text-align:left}"
            "th{background:var(--head)}blockquote{margin:12px 0;padding:4px 14px;border-left:4px solid var(--line);color:var(--muted)}"
            "hr{border:0;border-top:1px solid var(--line);margin:20px 0}a{color:var(--link)}.img{color:var(--muted)}"
            "pre.err{color:#e5484d;white-space:pre-wrap}</style>")
