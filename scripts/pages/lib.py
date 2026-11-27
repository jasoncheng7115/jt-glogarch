"""Builder for the jt-glogarch project pages (github/docs/index.html + how.html).

Layout follows jt-waf-mgr's project pages (owner 2026-11-27). Every text is written once in its
three languages side by side: English goes into the HTML (readable without JavaScript), and
pages-i18n.js carries zh-TW and ja for the language menu. Diagrams are inline SVG drawn here, their
labels translated the same way.
"""
from __future__ import annotations

import html as _html
import re

TR: dict[str, tuple[str, str, str]] = {}
_N = {"n": 0}
PREFIX = {"p": "x"}


def _key(key):
    if key:
        return key
    _N["n"] += 1
    return f"{PREFIX['p']}{_N['n']}"


def reg(key, en, zh, ja):
    key = _key(key)
    if key in TR and TR[key] != (en, zh, ja):
        raise ValueError(f"key {key} registered twice with different text")
    TR[key] = (en, zh, ja)
    return key


def t(en, zh, ja, tag="span", key=None, cls=None, attrs=""):
    """A translated HTML element (inline HTML allowed in the strings)."""
    k = reg(key, en, zh, ja)
    c = f' class="{cls}"' if cls else ""
    return f'<{tag}{c} data-t="{k}"{attrs}>{en}</{tag}>'


def tk(key):
    """Re-use a registered text."""
    en = TR[key][0]
    return f'<span data-t="{key}">{en}</span>'


def esc(s):
    return _html.escape(s, quote=True)


# ---- page pieces -------------------------------------------------------------------------------

def card(icon, h, body, cls=""):
    return (f'<div class="card{(" " + cls) if cls else ""}"><h3><span class="ic">{icon}</span>{h}</h3>'
            f'<p>{body}</p></div>')


def card_list(icon, h, by, items, cls=""):
    lis = "".join(f"<li>{x}</li>" for x in items)
    byp = f'<p class="by">{by}</p>' if by else ""
    return (f'<div class="card{(" " + cls) if cls else ""}"><h3><span class="ic">{icon}</span>{h}</h3>{byp}'
            f'<ul class="src">{lis}</ul></div>')


def steps(items):
    """ol.flow: [(title, text)]"""
    return '<ol class="flow">' + "".join(f"<li><b>{a}</b>{b}</li>" for a, b in items) + "</ol>"


def ticks(items, cls="ticks"):
    return f'<ul class="{cls}">' + "".join(f"<li>{x}</li>" for x in items) + "</ul>"


def section(sid, h, sub, body, alt=False, wrap_cls=""):
    a = ' class="alt"' if alt else ""
    w = f"wrap {wrap_cls}".strip()
    subp = f'<p class="sub">{sub}</p>' if sub else ""
    return f'<section id="{sid}"{a}><div class="{w}">\n  <h2>{h}</h2>{subp}\n{body}\n</div></section>\n'


def shot(name, cap, cls=""):
    """A screenshot that follows the language: docs/screenshots/<name>_<en|zhtw|ja>.png"""
    return (f'<figure class="{cls}"><a class="shotlink" href="screenshots/{name}_en.png" data-shot="{name}">'
            f'<img class="shot" src="screenshots/{name}_en.png" alt="" loading="lazy"></a>'
            + (f"<figcaption>{cap}</figcaption>" if cap else "") + "</figure>")


def code(lines):
    """A code block with a copy button; lines are (comment_or_None, command) or plain strings."""
    out = []
    for ln in lines:
        if isinstance(ln, tuple):
            out.append(f'<span class="c">{ln[0]}</span>')
        else:
            out.append(esc(ln))
    copy = tk("copy")
    return f'<div class="code"><button type="button" class="copy">{copy}</button><pre>' + "\n".join(out) + "</pre></div>"


# ---- SVG -----------------------------------------------------------------------------------------

class D:
    """A diagram. Coordinates in viewBox units; labels translated like the page."""

    def __init__(self, w, h, title, cls="archsvg"):
        self.w, self.h, self.cls = w, h, cls
        self.title_key = reg(None, *title)
        self.parts: list[str] = []
        self.edges: list[str] = []
        self.labels: list[str] = []

    def text(self, x, y, label, cls="nm", anchor="middle", w=None, into=None):
        k = reg(None, *label)
        ww = f' data-w="{w}"' if w else ""
        s = (f'<text class="{cls}" x="{x}" y="{y}" text-anchor="{anchor}" data-t="{k}"{ww}>{esc(label[0])}</text>')
        (into if into is not None else self.parts).append(s)

    def raw_text(self, x, y, s, cls="sb mono", anchor="middle", w=None):
        ww = f' data-w="{w}"' if w else ""
        self.parts.append(f'<text class="{cls}" x="{x}" y="{y}" text-anchor="{anchor}"{ww}>{esc(s)}</text>')

    def box(self, x, y, w, h, kind, title, sub=None, mono=None, dash=False, rx=10):
        cls = f"n {kind}" + (" dash" if dash else "")
        self.parts.append(f'<g class="{cls}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}"/></g>')
        cx = x + w / 2
        lines = 1 + (1 if sub else 0) + (1 if mono else 0)
        top = y + h / 2 - (lines - 1) * 8.5 + 5
        self.text(cx, top, title, "nm", w=w - 14)
        yy = top + 17
        if sub:
            self.text(cx, yy, sub, "sb", w=w - 14)
            yy += 16
        if mono:
            self.raw_text(cx, yy, mono, w=w - 14)

    def group(self, x, y, w, h, label=None, lx=None, ly=None, anchor="end"):
        self.parts.insert(0, f'<rect class="grp" x="{x}" y="{y}" width="{w}" height="{h}" rx="12"/>')
        if label:
            self.text(lx if lx is not None else x + w - 12, ly if ly is not None else y + h - 10, label, "grplabel",
                      anchor=anchor, w=w - 24)

    def edge(self, d, kind="", label=None, lx=0, ly=0, anchor="middle", w=None, both=False):
        nohead = "nohead" in kind
        kind = kind.replace("nohead", "").strip()
        cls = "e" + (f" {kind}" if kind else "")
        mk = "ar-main" if "main" in kind else ("ar-bad" if "bad" in kind else "ar")
        start = f' marker-start="url(#{mk})"' if both else ""
        end = "" if nohead else f' marker-end="url(#{mk})"'
        self.edges.append(f'<path class="{cls}" d="{d}"{end}{start}/>')
        if label:
            self.text(lx, ly, label, "el", anchor=anchor, w=w, into=self.labels)

    def render(self, fig_id, legend=None, zoom=True):
        defs = ('<defs>'
                '<marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0,0 L10,5 L0,10 z"/></marker>'
                '<marker id="ar-main" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path class="ah main" d="M0,0 L10,5 L0,10 z"/></marker>'
                '<marker id="ar-bad" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah bad" d="M0,0 L10,5 L0,10 z"/></marker>'
                '</defs>')
        # markers are referenced by id: every diagram keeps its own copy (ids made unique per figure)
        defs = defs.replace('id="ar', f'id="{fig_id}-ar')
        body = "".join(self.edges) + "".join(self.parts) + "".join(self.labels)
        body = body.replace("url(#ar", f"url(#{fig_id}-ar")
        en_title = TR[self.title_key][0]
        svg = (f'<svg class="{self.cls}" viewBox="0 0 {self.w} {self.h}" role="img">'
               f'<title data-t="{self.title_key}">{esc(en_title)}</title>{defs}{body}</svg>')
        bar = ""
        if legend or zoom:
            lg = ""
            if legend:
                lg = '<div class="legend">' + "".join(f'<span><i class="{c}"></i>{lab}</span>' for c, lab in legend) + "</div>"
            zb = f'<button type="button" class="zoom" data-fig="{fig_id}">{tk("zoom")}</button>' if zoom else ""
            bar = f'<div class="figbar">{lg}{zb}</div>'
        return f'<figure class="fig" id="{fig_id}">{svg}{bar}</figure>'


# ---- page shell ----------------------------------------------------------------------------------

GH = "https://github.com/jasoncheng7115/jt-glogarch"

GH_ICON = ('<svg viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>')
GLOBE = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true">'
         '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.7 2.5 15.3 0 18M12 3c-2.5 2.7-2.5 15.3 0 18"/></svg>')
CARET = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">'
         '<path d="M6 9l6 6 6-6"/></svg>')


def header(nav_html, home_link=False):
    home = (f'<a class="home-top" id="home-top" href="index.html">← {tk("nav_home")}</a>' if home_link else "")
    return f'''<header class="top"><div class="wrap">
  <a class="brand" id="home-brand" href="index.html"><img src="favicon.svg" alt="">jt-glogarch</a>
  {home}
  <nav class="links">{nav_html}</nav>
  <a class="gh-btn" href="{GH}" target="_blank" rel="noopener" aria-label="GitHub">{GH_ICON}<span>GitHub</span></a>
  <div class="lang">
    <button type="button" class="lang-btn" id="lang-btn" aria-haspopup="true" aria-expanded="false" aria-controls="lang-menu" aria-label="Language">
      {GLOBE}<span id="lang-cur">EN</span>{CARET}
    </button>
    <div class="lang-menu" id="lang-menu" role="menu" hidden>
      <button type="button" role="menuitemradio" data-lang="en" lang="en">English</button>
      <button type="button" role="menuitemradio" data-lang="zh-TW" lang="zh-TW">繁體中文</button>
      <button type="button" role="menuitemradio" data-lang="ja" lang="ja">日本語</button>
    </div>
  </div>
</div></header>
'''


def dialogs():
    return f'''<dialog id="lb" aria-labelledby="lb-title">
  <div class="lb-bar"><span id="lb-title"></span><a id="lb-open" target="_blank" rel="noopener">{tk("open_full")}</a>
    <button type="button" class="lb-x" id="lb-x" aria-label="Close">✕</button></div>
  <div class="lb-body"><img id="lb-img" alt=""></div>
</dialog>
<dialog id="zoom" aria-labelledby="zm-title">
  <div class="zm-bar"><span id="zm-title"></span>
    <div class="zm-tools"><button type="button" id="zm-out" aria-label="-">−</button><span class="zm-pct" id="zm-pct">100%</span><button type="button" id="zm-in" aria-label="+">+</button><button type="button" id="zm-fit">{tk("zm_fit")}</button></div>
    <button type="button" class="zm-x" id="zm-x" aria-label="Close">✕</button></div>
  <div class="zm-body" id="zm-body"></div>
</dialog>
'''


def footer():
    return f'''<footer><div class="wrap">
  jt-glogarch · AGPL-3.0-or-later · <a href="{GH}">GitHub</a> · <a href="{GH}/blob/main/CHANGELOG.md" class="cl-link">{tk("changelog")}</a> · Jason Tools Co., Ltd.
  <p class="disc">{tk("disc")}</p>
</div></footer>
'''


def page(title_key, desc_key, body, page_id):
    tt, dd = TR[title_key][0], TR[desc_key][0]
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title data-t="{title_key}">{esc(tt)}</title>
<meta name="description" content="{esc(dd)}">
<meta property="og:title" content="{esc(tt)}">
<meta property="og:description" content="{esc(dd)}">
<meta property="og:image" content="og-image.png">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="style.css">
</head>
<body data-page="{page_id}">
{body}
<script src="pages-i18n.js"></script>
<script src="pages.js"></script>
</body>
</html>
'''


def js_dict():
    import json
    d = {lang: {k: v[i] for k, v in TR.items()} for i, lang in enumerate(("en", "zh-TW", "ja"))}
    return ("// Generated by scripts/pages/build.py from the texts written side by side there; do not edit by hand.\n"
            "window.PAGES_T = " + json.dumps(d, ensure_ascii=False, indent=0, sort_keys=True) + ";\n")


def lint():
    """zh: full-width punctuation next to CJK; Taiwan terms; ja: no Traditional-only glyphs."""
    probs = []
    cjk = r"[㐀-鿿぀-ヿ]"
    bad_terms = ["日誌", "高亮", "默認", "缺省", "刷新", "優先級", "腳本", "推薦", "前綴", "併發", "去重", "自適應", "過濾", "損壞", "甜甜圈", "\uff0f", "絕不", "永遠不"]
    trad_only = "錄檔們這說對點關體處應實與從讓將當來檢區產變數據圖顯"
    for k, (en, zh, ja) in TR.items():
        plain = re.sub(r"<[^>]+>", "", zh)
        plain = re.sub(r"<code>.*?</code>", "", plain)
        for m in re.finditer(r"[,;:!?]", plain):
            a = plain[m.start() - 1] if m.start() else ""
            b = plain[m.end()] if m.end() < len(plain) else ""
            if re.match(cjk, a) or re.match(cjk, b):
                probs.append(f"zh half-width '{m.group()}' in {k}: {zh[:60]}")
                break
        for w in bad_terms:
            if w in zh:
                probs.append(f"zh term {w} in {k}")
        jp = re.sub(r"<[^>]+>", "", ja)
        for ch in trad_only:
            if ch in jp:
                probs.append(f"ja glyph {ch} in {k}: {ja[:50]}")
                break
        if not en or not zh or not ja:
            probs.append(f"empty text in {k}")
    return probs
