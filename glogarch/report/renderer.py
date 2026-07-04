"""Headless-Chromium HTML → PDF renderer for jt-glogarch Reports (beta).

Mirrors how Graylog Enterprise renders reports (a headless Chromium print), but
gives us full control over the layout: cover page, running header/footer with
page numbers, and CJK-capable fonts. Rendering is a single print pass over one
self-contained HTML document (cover + sections), so no PDF merging is needed.

Requirements on the host (same class as Graylog Enterprise reporting):
  - Playwright + a Chromium build (`playwright install chromium`)
  - CJK fonts for Traditional Chinese reports (WenQuanYi / Noto Sans CJK TC)
The Chromium path honours the PLAYWRIGHT_BROWSERS_PATH env var so the service
user (jt-glogarch) can share a system-wide browser install.
"""

from __future__ import annotations

import os

from glogarch.utils.logging import get_logger

log = get_logger("report.renderer")

# When Chromium is installed into a shared path (so the jt-glogarch service user
# can read it — root's ~/.cache is not readable by the service), point Playwright
# at it. Only applied if the dir exists and the env isn't already set, so a
# developer/root install using the default cache still works.
_SHARED_BROWSERS = "/opt/jt-glogarch/.playwright"
if "PLAYWRIGHT_BROWSERS_PATH" not in os.environ and os.path.isdir(_SHARED_BROWSERS):
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = _SHARED_BROWSERS

# The hardened systemd unit (ProtectSystem=strict) makes /tmp read-only; only
# /opt/jt-glogarch and /data/graylog-archives are writable. Chromium needs a
# writable temp dir (mkdtemp), so point TMPDIR at a writable location under the
# browsers path. setdefault so a dev/root run keeps its normal /tmp.
_bp = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
if _bp:
    _tmp = os.path.join(_bp, "tmp")
    try:
        os.makedirs(_tmp, exist_ok=True)
        os.environ.setdefault("TMPDIR", _tmp)
    except Exception:
        pass

# A4 in CSS px at 96dpi is ~794x1123; we let Chromium handle page sizing.
# The top/bottom margins hold the brand band (BAND_MM) PLUS a gap so page
# content never touches the band. The band sits at the outer edge of the margin;
# the remaining (margin − band) is clear space before the content starts.
_BAND_MM = 11
_GAP_MM = 6
_MARGIN_MM = _BAND_MM + _GAP_MM   # 17mm
_DEFAULT_MARGIN = {"top": f"{_MARGIN_MM}mm", "bottom": f"{_MARGIN_MM}mm",
                   "left": "0mm", "right": "0mm"}


def _footer_template(report_title: str, generated_at: str, brand: str = "#6c63ff") -> str:
    """Chromium footer template — a brand-coloured running band with page numbers.

    Chromium substitutes .pageNumber / .totalPages / .date / .title spans, and
    ignores the page CSS, so styles must be inline and font-size explicit. The
    outer div fills the whole bottom margin box so the band bleeds full-width."""
    from html import escape
    left = escape(report_title or "jt-glogarch")
    mid = escape(generated_at or "")
    band = (
        f'<div style="width:100%;height:{_BAND_MM}mm;box-sizing:border-box;'
        f'background:{brand};color:rgba(255,255,255,.92);font-size:8px;'
        'padding:0 14mm;-webkit-print-color-adjust:exact;print-color-adjust:exact;'
        'display:flex;justify-content:space-between;align-items:center;">'
        f'<span>{left}</span>'
        f'<span>{mid}</span>'
        '<span>jt-glogarch &nbsp;•&nbsp; '
        '<span class="pageNumber"></span> / <span class="totalPages"></span></span>'
        '</div>'
    )
    # Full-height container aligns the band to the BOTTOM of the bottom margin,
    # leaving the gap between content and band.
    return (f'<div style="width:100%;height:100%;margin:0;display:flex;'
            f'flex-direction:column;justify-content:flex-end;">{band}</div>')


def _header_template(header_text: str, header_logo: str = "", brand: str = "#6c63ff") -> str:
    """A brand-coloured running header band. Always rendered (so every page —
    including page 2+ — carries the band); logo left, header text right."""
    from html import escape
    txt = escape(header_text or "")
    logo = ""
    if header_logo and header_logo.startswith("data:image"):
        logo = f'<img src="{header_logo}" style="height:22px;max-width:150px;object-fit:contain;">'
    band = (
        f'<div style="width:100%;height:{_BAND_MM}mm;box-sizing:border-box;'
        f'background:{brand};color:rgba(255,255,255,.92);font-size:8px;'
        'padding:0 14mm;display:flex;justify-content:space-between;align-items:center;'
        '-webkit-print-color-adjust:exact;print-color-adjust:exact;">'
        f'<span>{logo}</span><span>{txt}</span>'
        '</div>'
    )
    # Align the band to the TOP of the top margin; the gap falls below it, so
    # page content never butts against the band.
    return (f'<div style="width:100%;height:100%;margin:0;display:flex;'
            f'flex-direction:column;justify-content:flex-start;">{band}</div>')


async def html_to_pdf(
    html: str,
    *,
    report_title: str = "",
    header_text: str = "",
    header_logo: str = "",
    generated_at: str = "",
    brand_color: str = "#6c63ff",
    watermark: dict | None = None,
    toc_titles: list | None = None,
    landscape: bool = False,
    with_header_footer: bool = True,
) -> bytes:
    """Render a full HTML document to PDF bytes via headless Chromium."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            args=["--no-sandbox", "--disable-dev-shm-usage", "--font-render-hinting=none"],
        )
        try:
            # Viewport matched to the A4 print column (≈794px @96dpi) so Chart.js
            # sizes its canvases to the printed width instead of the default
            # 1280px viewport (which would render wider than the page and clip at
            # the right edge). device_scale_factor=2 keeps charts crisp without
            # bloating the file (embedded-logo softness some users saw is a PDF
            # *viewer* artifact — Apple Preview renders it fine; SVG logos are
            # always sharp).
            page = await browser.new_page(
                viewport={"width": 794, "height": 1123}, device_scale_factor=2,
            )
            await page.emulate_media(media="print")
            # set_content + wait for fonts/charts to settle.
            await page.set_content(html, wait_until="networkidle")
            try:
                await page.evaluate("document.fonts && document.fonts.ready")
            except Exception:
                pass
            await page.wait_for_timeout(250)  # let Chart.js finish drawing
            # Reserve the top/bottom margins for the bands, but DON'T use
            # Chromium's own header/footer — it leaves a white gap at the right
            # edge (a known Chromium quirk) and can't skip the cover page. We
            # draw the bands ourselves with PyMuPDF for pixel-perfect, full-bleed
            # control (below).
            pdf = await page.pdf(
                format="A4",
                landscape=landscape,
                print_background=True,
                prefer_css_page_size=False,
                display_header_footer=False,
                margin=_DEFAULT_MARGIN,
            )
            if with_header_footer:
                pdf = _draw_bands(pdf, brand_color, report_title, header_text,
                                  header_logo, generated_at)
            if toc_titles:
                pdf = _add_toc_page_numbers(pdf, toc_titles, brand_color)
            if watermark and watermark.get("text"):
                pdf = _apply_watermark(pdf, watermark)
            return pdf
        finally:
            await browser.close()


def _add_toc_page_numbers(pdf: bytes, toc_titles: list, brand_color: str) -> bytes:
    """Fill in the page number on the right of each table-of-contents entry.
    Page breaks are decided by Chromium at render time, so we resolve them here:
    find the TOC page, look up where each section header lands, and draw the
    number right-aligned on the matching TOC line. Best-effort."""
    try:
        import fitz
    except Exception:
        return pdf
    try:
        doc = fitz.open(stream=pdf, filetype="pdf")
        n = doc.page_count
        titles = [t for t in toc_titles if t]
        if not titles:
            doc.close()
            return pdf
        # 1) TOC page = the first page AFTER the cover that carries a section
        #    title. The TOC always precedes the section bodies, so the first such
        #    page is the contents list (works for 1 section or many).
        toc_page = None
        for i in range(1, min(n, 6)):
            txt = doc[i].get_text()
            if any(t in txt for t in titles):
                toc_page = i
                break
        if toc_page is None:
            doc.close()
            return pdf
        right = doc[toc_page].rect.width - 16 * _MM
        rgb = _hex_to_rgb01(brand_color)
        for t in titles:
            # 2) Section start page = first page AFTER the TOC that shows the header.
            start = None
            for i in range(toc_page + 1, n):
                if t in doc[i].get_text():
                    start = i + 1  # 1-based
                    break
            if start is None:
                continue
            # 3) Draw the number right-aligned on this entry's TOC line. Use
            #    point-based insert_text (insert_textbox silently drops text that
            #    doesn't fit its box); compute the x so it's right-aligned.
            rects = doc[toc_page].search_for(t)
            if not rects:
                continue
            r = rects[0]
            num = str(start)
            twid = fitz.get_text_length(num, fontname="helv", fontsize=11)
            doc[toc_page].insert_text((right - twid, r.y1 - 2), num, fontsize=11, color=rgb)
        out = doc.tobytes(garbage=4, deflate=True)
        doc.close()
        return out
    except Exception as e:
        log.warning("TOC page numbers failed", error=str(e))
        return pdf


def _apply_watermark(pdf: bytes, wm: dict) -> bytes:
    """Stamp a flattened, tiled text watermark over every page. Rendered as a
    transparent PNG (via PIL) and inserted as an image, so it is NOT selectable
    and cannot be deleted without editing the PDF content stream. Best-effort."""
    try:
        import fitz
        from PIL import Image, ImageDraw, ImageFont
        from io import BytesIO
    except Exception:
        return pdf
    text = (wm.get("text") or "").strip()
    if not text:
        return pdf
    try:
        angle = 45 if wm.get("direction", "diagonal") == "diagonal" else 0
        fontsize = {"small": 30, "medium": 46, "large": 70}.get(wm.get("size", "large"), 70)
        opacity = int(255 * float(wm.get("opacity", 0.10)))
        fontfile = _find_cjk_font()
        W, H = 1240, 1754  # ~150dpi A4 portrait canvas
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d0 = ImageDraw.Draw(canvas)
        # Auto-shrink the font so the WIDEST line fits within the page's diagonal
        # footprint — this guarantees every tile (and therefore every page) shows
        # the complete selected watermark text, never clipping any of it.
        lines = text.split("\n")
        limit = W * 1.35 if angle else W * 0.95   # diagonal allows a longer line
        def _fit(fs):
            f = ImageFont.truetype(fontfile, fs) if fontfile else ImageFont.load_default()
            return f, max((d0.textlength(ln, font=f) for ln in lines), default=1)
        font, widest = _fit(fontsize)
        while fontsize > 14 and widest > limit:
            fontsize -= 3
            font, widest = _fit(fontsize)
        # One text chip, then rotate + tile it across the page. Text may be two
        # lines (base + appended info) — measure/draw as multi-line, centred.
        spacing = int(fontsize * 0.3)
        bb = d0.multiline_textbbox((0, 0), text, font=font, spacing=spacing, align="center")
        tw, th = int(bb[2] - bb[0]), int(bb[3] - bb[1])
        chip = Image.new("RGBA", (tw + 40, th + 40), (0, 0, 0, 0))
        ImageDraw.Draw(chip).multiline_text((20, 20 - bb[1]), text, font=font,
                                            fill=(110, 110, 120, opacity),
                                            spacing=spacing, align="center")
        chip = chip.rotate(angle, expand=True, resample=Image.BICUBIC)
        step_x, step_y = chip.width + 70, chip.height + 90
        row = 0
        for y in range(-chip.height, H, step_y):
            offset = (step_x // 2) if (row % 2) else 0
            for x in range(-chip.width, W + step_x, step_x):
                canvas.alpha_composite(chip, (x - offset, y))
            row += 1
        buf = BytesIO()
        canvas.save(buf, format="PNG")
        png = buf.getvalue()
        doc = fitz.open(stream=pdf, filetype="pdf")
        for page in doc:
            page.insert_image(page.rect, stream=png, overlay=True, keep_proportion=False)
        out = doc.tobytes(garbage=4, deflate=True)
        doc.close()
        return out
    except Exception as e:
        log.warning("watermark failed", error=str(e))
        return pdf


def _hex_to_rgb01(h: str) -> tuple[float, float, float]:
    h = (h or "#6c63ff").lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255)
    except (ValueError, IndexError):
        return (0.4235, 0.388, 1.0)


import glob as _glob
import os as _os


def _find_cjk_font():
    """A CJK-capable TTF/TTC/OTF so fitz can draw Chinese header/footer text."""
    for p in (_glob.glob("/usr/share/fonts/truetype/jt-glogarch/*.tt[cf]")
              + ["/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"]
              + _glob.glob("/usr/share/fonts/**/NotoSansCJK*.[ot]t[cf]", recursive=True)
              + _glob.glob("/usr/share/fonts/**/wqy*.tt[cf]", recursive=True)):
        if _os.path.exists(p):
            return p
    return None


_MM = 72 / 25.4


def _draw_bands(pdf: bytes, brand_color: str, report_title: str, header_text: str,
                header_logo: str, generated_at: str) -> bytes:
    """Draw the brand header/footer bands ourselves (full-bleed, no right-edge
    gap) on every page EXCEPT the cover — the cover (page 0) instead gets its
    top/bottom margins painted brand so it reads as one clean block.
    Best-effort: returns the PDF unchanged if PyMuPDF is unavailable."""
    try:
        import fitz  # PyMuPDF (report extra)
    except Exception:
        return pdf
    try:
        rgb = _hex_to_rgb01(brand_color)
        white = (1, 1, 1)
        fontfile = _find_cjk_font()
        fontname = "cjk" if fontfile else "helv"
        band_h = _BAND_MM * _MM
        pad = 14 * _MM
        cover_paint = (_MARGIN_MM + 2) * _MM
        doc = fitz.open(stream=pdf, filetype="pdf")
        n = doc.page_count

        def _txt(page, rect, text, align):
            if not text:
                return
            try:
                page.insert_textbox(rect, text, fontsize=8, fontname=fontname,
                                    fontfile=fontfile, color=white, align=align)
            except Exception:
                page.insert_textbox(rect, text, fontsize=8, color=white, align=align)

        for i in range(n):
            page = doc[i]
            r = page.rect
            W, H = r.width, r.height
            if i == 0:
                # Cover: NO header/footer band — leave the top/bottom margins
                # plain white; only the centre brand block (the cover-panel)
                # shows. (Bands appear from page 2 onward.)
                continue
            # Header band (top edge) + footer band (bottom edge), full width.
            page.draw_rect(fitz.Rect(0, 0, W, band_h), color=rgb, fill=rgb, width=0)
            page.draw_rect(fitz.Rect(0, H - band_h, W, H), color=rgb, fill=rgb, width=0)
            # Optional header logo, LEFT-aligned to the same x as the footer text.
            if header_logo and header_logo.startswith("data:image"):
                try:
                    import base64
                    raw = base64.b64decode(header_logo.split(",", 1)[1])
                    lh = band_h * 0.62
                    # Fit the image box to the logo's aspect ratio so the image
                    # fills it exactly — otherwise keep_proportion centres it and
                    # it looks indented. Cap the width so a very wide logo behaves.
                    lw = 46 * _MM
                    try:
                        from PIL import Image as _PILImage
                        from io import BytesIO as _BytesIO
                        _im = _PILImage.open(_BytesIO(raw))
                        if _im.height:
                            lw = min(lh * (_im.width / _im.height), 60 * _MM)
                    except Exception:
                        pass
                    page.insert_image(fitz.Rect(pad, (band_h - lh) / 2, pad + lw,
                                                (band_h + lh) / 2),
                                      stream=raw, keep_proportion=True, overlay=True)
                except Exception:
                    pass
            # Vertically-centred text within each band (baseline tuned for 8pt).
            hy0, hy1 = band_h / 2 - 6, band_h / 2 + 8
            fy0, fy1 = H - band_h / 2 - 6, H - band_h / 2 + 8
            _txt(page, fitz.Rect(pad, hy0, W - pad, hy1), header_text, fitz.TEXT_ALIGN_RIGHT)
            _txt(page, fitz.Rect(pad, fy0, W * 0.5, fy1), report_title or "jt-glogarch", fitz.TEXT_ALIGN_LEFT)
            _txt(page, fitz.Rect(W * 0.3, fy0, W * 0.7, fy1), generated_at, fitz.TEXT_ALIGN_CENTER)
            _txt(page, fitz.Rect(W * 0.55, fy0, W - pad, fy1),
                 f"jt-glogarch   |   {i + 1} / {n}", fitz.TEXT_ALIGN_RIGHT)
        # Subset the embedded CJK font to only the glyphs actually used — a full
        # WenQuanYi embed is ~7MB; the subset is a few KB. garbage/deflate then
        # dedupe + compress.
        try:
            doc.subset_fonts()
        except Exception:
            pass
        out = doc.tobytes(garbage=4, deflate=True)
        doc.close()
        return out
    except Exception as e:
        log.warning("draw bands failed", error=str(e))
        return pdf


def render_pdf_sync(html: str, **kwargs) -> bytes:
    """Blocking wrapper — safe to call from worker threads (own event loop)."""
    import asyncio
    return asyncio.run(html_to_pdf(html, **kwargs))
