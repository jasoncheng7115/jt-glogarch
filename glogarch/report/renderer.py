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
_DEFAULT_MARGIN = {"top": "18mm", "bottom": "16mm", "left": "0mm", "right": "0mm"}


def _footer_template(report_title: str, generated_at: str) -> str:
    """Chromium footer template — running footer with page numbers.

    Chromium substitutes .pageNumber / .totalPages / .date / .title spans, and
    ignores the page CSS, so styles must be inline and font-size explicit."""
    from html import escape
    left = escape(report_title or "jt-glogarch")
    mid = escape(generated_at or "")
    return (
        '<div style="width:100%;font-size:8px;color:#8a8f98;'
        'padding:0 14mm;-webkit-print-color-adjust:exact;'
        'display:flex;justify-content:space-between;align-items:center;">'
        f'<span>{left}</span>'
        f'<span>{mid}</span>'
        '<span>jt-glogarch &nbsp;•&nbsp; '
        '<span class="pageNumber"></span> / <span class="totalPages"></span></span>'
        '</div>'
    )


def _header_template(header_text: str) -> str:
    from html import escape
    txt = escape(header_text or "")
    if not txt:
        return "<div></div>"
    return (
        '<div style="width:100%;font-size:8px;color:#8a8f98;'
        'padding:0 14mm;text-align:right;-webkit-print-color-adjust:exact;">'
        f'{txt}</div>'
    )


async def html_to_pdf(
    html: str,
    *,
    report_title: str = "",
    header_text: str = "",
    generated_at: str = "",
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
            # the right edge). device_scale_factor=2 keeps chart lines crisp.
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
            pdf = await page.pdf(
                format="A4",
                landscape=landscape,
                print_background=True,
                prefer_css_page_size=False,
                display_header_footer=with_header_footer,
                header_template=_header_template(header_text) if with_header_footer else "<div></div>",
                footer_template=_footer_template(report_title, generated_at) if with_header_footer else "<div></div>",
                margin=_DEFAULT_MARGIN,
            )
            return pdf
        finally:
            await browser.close()


def render_pdf_sync(html: str, **kwargs) -> bytes:
    """Blocking wrapper — safe to call from worker threads (own event loop)."""
    import asyncio
    return asyncio.run(html_to_pdf(html, **kwargs))
