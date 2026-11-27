# Diagram check for the project pages: a label on a line or a box, or a text wider than its box, in any
# diagram of index.html / how.html in all three languages. Prints nothing when clean.
#   python3 scripts/pages/check_diagrams.py
import asyncio, sys
from playwright.async_api import async_playwright
JS = r"""
() => {
  const out = [];
  for (const svg of document.querySelectorAll('figure.fig svg')) {
    const fig = svg.closest('figure').id;
    const rects = [...svg.querySelectorAll('g.n rect')].map(r => r.getBBox());
    const segs = [];
    for (const p of svg.querySelectorAll('path.e')) {
      const pts = [...p.getAttribute('d').matchAll(/[ML]\s*([\d.]+)[ ,]([\d.]+)/g)].map(m => [+m[1], +m[2]]);
      for (let i = 1; i < pts.length; i++) segs.push([pts[i-1], pts[i]]);
    }
    for (const t of svg.querySelectorAll('text.el, text.grplabel')) {
      const b = t.getBBox(); const pad = 2;
      const x1 = b.x - pad, y1 = b.y - pad, x2 = b.x + b.width + pad, y2 = b.y + b.height + pad;
      for (const r of rects) if (x1 < r.x + r.width && x2 > r.x && y1 < r.y + r.height && y2 > r.y) out.push(fig + ' BOX  ' + t.textContent);
      for (const [[ax, ay], [bx, by]] of segs) {
        const sx1 = Math.min(ax, bx), sx2 = Math.max(ax, bx), sy1 = Math.min(ay, by), sy2 = Math.max(ay, by);
        if (x1 < sx2 + 0.5 && x2 > sx1 - 0.5 && y1 < sy2 + 0.5 && y2 > sy1 - 0.5) { out.push(fig + ' LINE ' + t.textContent); break; }
      }
    }
  }
  for (const svg of document.querySelectorAll('figure.fig svg')) {
    const fig = svg.closest('figure').id;
    const rects = [...svg.querySelectorAll('g.n rect')].map(r => r.getBBox());
    for (const t of svg.querySelectorAll('text.nm, text.sb')) {
      const b = t.getBBox(), cx = b.x + b.width / 2, cy = b.y + b.height / 2;
      const r = rects.find(r => cx > r.x && cx < r.x + r.width && cy > r.y && cy < r.y + r.height);
      if (r && (b.x < r.x + 2 || b.x + b.width > r.x + r.width - 2)) out.push(fig + ' OVERFLOW ' + t.textContent);
    }
  }
  return [...new Set(out)];
}
"""
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for page in ("index", "how"):
            for lang in ("en", "zh-TW", "ja"):
                pg = await b.new_page(viewport={"width": 1436, "height": 900})
                await pg.goto(f"file:///opt/jt-glogarch/github/docs/{page}.html?lang={lang}"); await pg.wait_for_timeout(700)
                for x in await pg.evaluate(JS): print(page, lang, x)
        await b.close()
asyncio.run(main())
