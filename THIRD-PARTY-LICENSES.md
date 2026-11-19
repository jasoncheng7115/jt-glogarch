# Third-Party Licenses

## Iconoir Icons

- **Source**: https://iconoir.com
- **License**: MIT License
- **Copyright**: Copyright (c) 2021 Luca Burgio

Icons are embedded as inline SVG in the Web UI.

```
MIT License

Copyright (c) 2021 Luca Burgio

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Chart.js

- **Source**: https://www.chartjs.org (`glogarch/report/assets/chart.umd.min.js`, v4.4.1)
- **License**: MIT License
- **Copyright**: (c) 2023 Chart.js Contributors

Used to draw charts in PDF reports; the file keeps its own licence header.

## Natural Earth

- **Source**: https://www.naturalearthdata.com (1:110m Admin 0 - Countries)
- **License**: public domain ([terms of use](https://www.naturalearthdata.com/about/terms-of-use/))

`glogarch/report/assets/worldmap.svg`, the land outline of the PDF report's world
map, is drawn from this data (equirectangular, coordinates rounded to 0.01 degree,
two digitising artefacts removed).

## mcp_graylog

- **Source**: https://github.com/jasoncheng7115/jasontools-mcp/tree/main/mcp_graylog
- **Author**: Jason Cheng (Jason Tools)
- **License**: MIT
- **Usage**: `glogarch/vendor/mcp_graylog.py`, kept byte-for-byte as published (version, commit and
  SHA-256 in `glogarch/vendor/mcp_graylog.json`). Its read-only Graylog tools are offered by the AI
  chat and the MCP endpoint. Version 1.10.2 loads on Python 3.10 or later.

## Python packages, Chromium, fonts

Every Python package jt-glogarch runs on, the Chromium build used by PDF
reports and the CJK font in the offline bundle are listed with version and
licence in the SBOM (CycloneDX 1.5):

- `sbom.cdx.json` in this repository: the versions this release was built and tested with.
- `sbom.cdx.json` in each offline bundle: exactly the files that bundle ships, with SHA-256.
- `glogarch sbom` on an installed host: what that host actually runs.
