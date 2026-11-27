# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""CycloneDX 1.5 SBOM of what jt-glogarch runs on.

Two sources, one builder:

  python3 -m glogarch.sbom                    # what is INSTALLED on this host
  python3 -m glogarch.sbom --wheels DIR       # what an offline bundle SHIPS
  glogarch sbom [-o FILE]                     # the same as the first, via the CLI

The dependency versions are ranges (`>=`), so they are decided when pip installs
them; a list written by hand would not say what a given host really runs. Both
modes therefore read the real distributions: the installed metadata
(importlib.metadata) or each wheel's own METADATA, and walk the requirement
closure from jt-glogarch itself. Development tools (the `dev` extra) are not
shipped and are left out.

Standard library only: this runs on the bundle build host from the source tree
and on a customer host as the service user, and must not add a package.
"""

from __future__ import annotations

import argparse
import datetime
import email.parser
import hashlib
import json
import os
import re
import sys
import uuid
import zipfile
from pathlib import Path
from typing import Iterable

ROOT_NAME = "jt-glogarch"
SHIPPED_EXTRAS = {"report"}  # optional, but shipped by the offline bundle
_PKG_DIR = Path(__file__).resolve().parent

# Trove classifier -> SPDX id, for distributions that declare no SPDX expression.
_CLASSIFIER_SPDX = {
    "MIT License": "MIT",
    "BSD License": "BSD-3-Clause",
    "Apache Software License": "Apache-2.0",
    "ISC License (ISCL)": "ISC",
    "Mozilla Public License 2.0 (MPL 2.0)": "MPL-2.0",
    "Python Software Foundation License": "PSF-2.0",
    "GNU Affero General Public License v3 or later (AGPLv3+)": "AGPL-3.0-or-later",
    "GNU Affero General Public License v3": "AGPL-3.0-only",
    "GNU Lesser General Public License v2 or later (LGPLv2+)": "LGPL-2.0-or-later",
    "GNU Lesser General Public License v3 (LGPLv3)": "LGPL-3.0-only",
    "GNU General Public License v3 (GPLv3)": "GPL-3.0-only",
    "The Unlicense (Unlicense)": "Unlicense",
    "Historical Permission Notice and Disclaimer (HPND)": "HPND",
}
# Common short `License:` values that already are SPDX ids (or nearly).
_LICENSE_ALIASES = {
    "mit": "MIT", "mit license": "MIT", "bsd": "BSD-3-Clause", "bsd-3-clause": "BSD-3-Clause",
    "bsd-2-clause": "BSD-2-Clause", "apache 2.0": "Apache-2.0", "apache-2.0": "Apache-2.0",
    "apache license 2.0": "Apache-2.0", "apache software license": "Apache-2.0",
    "isc": "ISC", "mpl-2.0": "MPL-2.0", "psf": "PSF-2.0", "psf-2.0": "PSF-2.0",
    "agpl-3.0": "AGPL-3.0-only", "agpl-3.0-or-later": "AGPL-3.0-or-later",
}
_FONT_LICENSES = {"wqy": "GPL-2.0-only WITH Font-exception-2.0", "noto": "OFL-1.1"}


def canonical(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


class Dist:
    """One Python distribution: name, version, METADATA headers, optional file hash."""

    def __init__(self, name: str, version: str, meta, sha256: str | None = None,
                 extra_files: dict[str, bytes] | None = None):
        self.name = name
        self.version = version
        self.meta = meta
        self.sha256 = sha256
        self.extra_files = extra_files or {}

    @property
    def key(self) -> str:
        return canonical(self.name)

    def requires(self) -> list[str]:
        return list(self.meta.get_all("Requires-Dist") or [])


def _parse_meta(text: str):
    return email.parser.Parser().parsestr(text, headersonly=True)


def installed_dists() -> dict[str, Dist]:
    import importlib.metadata as md
    out: dict[str, Dist] = {}
    # A source checkout on sys.path carries a build leftover (*.egg-info) whose
    # version and requirements can be stale: an installed *.dist-info wins.
    found = list(md.distributions())
    found.sort(key=lambda d: 0 if str(getattr(d, "_path", "")).endswith(".dist-info") else 1)
    for d in found:
        name = d.metadata.get("Name")
        if not name or canonical(name) in out:
            continue
        extra = {}
        if canonical(name) == "playwright":
            p = Path(d.locate_file("playwright/driver/package/browsers.json"))
            if p.is_file():
                extra["browsers.json"] = p.read_bytes()
        out[canonical(name)] = Dist(name, d.version, d.metadata, extra_files=extra)
    return out


def wheel_dists(directory: str | os.PathLike) -> dict[str, Dist]:
    out: dict[str, Dist] = {}
    for whl in sorted(Path(directory).glob("*.whl")):
        with zipfile.ZipFile(whl) as z:
            metas = [n for n in z.namelist()
                     if n.count("/") == 1 and n.endswith(".dist-info/METADATA")]
            if not metas:
                continue
            meta = _parse_meta(z.read(metas[0]).decode("utf-8", "replace"))
            extra = {}
            if "playwright/driver/package/browsers.json" in z.namelist():
                extra["browsers.json"] = z.read("playwright/driver/package/browsers.json")
        name, version = meta.get("Name"), meta.get("Version")
        if not name or not version:
            continue
        digest = hashlib.sha256(whl.read_bytes()).hexdigest()
        out[canonical(name)] = Dist(name, version, meta, sha256=digest, extra_files=extra)
    return out


_REQ = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(\[[^\]]*\])?\s*([^;]*)(;(.*))?$")
_EXTRA_IN_MARKER = re.compile(r"""extra\s*==\s*['"]([^'"]+)['"]""")


def parse_requirement(req: str) -> tuple[str, set[str], set[str]]:
    """(name, extras it asks of that dist, extras of OUR dist it is gated on)."""
    m = _REQ.match(req)
    if not m:
        return "", set(), set()
    asked = {canonical(e) for e in (m.group(2) or "").strip("[]").split(",") if e.strip()}
    gated = {canonical(e) for e in _EXTRA_IN_MARKER.findall(m.group(5) or "")}
    return m.group(1), asked, gated


def _marker_evaluator():
    """packaging's Marker if this Python has it (pip always vendors one)."""
    import importlib
    import importlib.util
    for mod in ("packaging.markers", "pip._vendor.packaging.markers"):
        top = mod.split(".")[0]
        if importlib.util.find_spec(top) is None:
            continue
        if top == "pip" and importlib.util.find_spec("pip._vendor.packaging") is None:
            continue
        return importlib.import_module(mod).Marker
    return None


_Marker = _marker_evaluator()


def marker_applies(req: str, extras: set[str]) -> bool | None:
    """Does the requirement's marker hold on THIS platform? None = cannot tell."""
    if ";" not in req or _Marker is None:
        return None
    try:
        m = _Marker(req.split(";", 1)[1].strip())
        return any(m.evaluate({"extra": e}) for e in (extras or {""}))
    except Exception:  # an unparsable marker: fall back to presence
        return None


def closure(dists: dict[str, Dist], root: str = ROOT_NAME,
            root_extras: Iterable[str] = SHIPPED_EXTRAS) -> tuple[list[Dist], dict[str, list[str]]]:
    """Every distribution reachable from `root`, and who depends on whom.

    A requirement counts when its environment marker holds here (Python
    version, platform; evaluated with the `packaging` copy pip vendors) AND the
    distribution it names is present. Without an evaluator only presence
    counts. The offline bundle is built on the target's Python and platform,
    so "here" is the target.
    """
    rk = canonical(root)
    if rk not in dists:
        raise SystemExit(f"{root} not found in the distributions to describe")
    seen: dict[str, set[str]] = {rk: {canonical(e) for e in root_extras}}
    graph: dict[str, list[str]] = {}
    queue = [rk]
    while queue:
        k = queue.pop(0)
        deps: list[str] = []
        for req in dists[k].requires():
            name, asked, gated = parse_requirement(req)
            if not name:
                continue
            if gated and not (gated & seen[k]):
                continue
            if marker_applies(req, seen[k] if gated else set()) is False:
                continue
            dk = canonical(name)
            if dk not in dists:
                continue
            if dk not in deps:
                deps.append(dk)
            before = seen.get(dk)
            if before is None:
                seen[dk] = set(asked)
                queue.append(dk)
            elif not asked <= before:
                before |= asked
                queue.append(dk)
        graph[k] = deps
    ordered = [dists[k] for k in seen]
    return ordered, graph


def license_of(meta) -> list[dict]:
    expr = (meta.get("License-Expression") or "").strip()
    if expr:
        return [{"expression": expr}]
    ids = []
    for c in meta.get_all("Classifier") or []:
        if c.startswith("License :: "):
            leaf = c.split(" :: ")[-1]
            sid = _CLASSIFIER_SPDX.get(leaf)
            if sid and sid not in ids:
                ids.append(sid)
    if ids:
        return [{"license": {"id": i}} for i in ids]
    raw = (meta.get("License") or "").strip()
    if raw and "\n" not in raw and len(raw) <= 80:
        sid = _LICENSE_ALIASES.get(raw.lower())
        return [{"license": {"id": sid}}] if sid else [{"license": {"name": raw}}]
    return []


def _pypi_component(d: Dist) -> dict:
    purl = f"pkg:pypi/{d.key}@{d.version}"
    c = {"type": "library", "bom-ref": purl, "name": d.name, "version": d.version, "purl": purl}
    lic = license_of(d.meta)
    if lic:
        c["licenses"] = lic
    if d.sha256:
        c["hashes"] = [{"alg": "SHA-256", "content": d.sha256}]
    return c


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def vendored_components(pkg_dir: Path = _PKG_DIR) -> list[dict]:
    """Third-party files that live inside the jt-glogarch package itself."""
    out = []
    chart = pkg_dir / "report" / "assets" / "chart.umd.min.js"
    if chart.is_file():
        head = chart.read_bytes()[:400].decode("utf-8", "replace")
        m = re.search(r"chart\.js@([0-9][0-9A-Za-z.\-]*)", head)
        ver = m.group(1) if m else ""
        purl = f"pkg:npm/chart.js@{ver}" if ver else "pkg:npm/chart.js"
        out.append({"type": "library", "bom-ref": purl, "name": "chart.js", "version": ver,
                    "purl": purl, "licenses": [{"license": {"id": "MIT"}}],
                    "hashes": [{"alg": "SHA-256", "content": _sha256_file(chart)}],
                    "properties": [{"name": "jt-glogarch:location",
                                    "value": "glogarch/report/assets/chart.umd.min.js (PDF reports)"}]})
    # bundled browser libraries with a manifest beside them (glogarch/ai/assets/*.json)
    assets = pkg_dir / "ai" / "assets"
    for man_path in sorted(assets.glob("*.json")) if assets.is_dir() else []:
        man = json.loads(man_path.read_text(encoding="utf-8"))
        f = assets / str(man.get("file") or "")
        if not f.is_file():
            continue
        name, ver = man.get("name", f.stem), man.get("version", "")
        purl = f"pkg:npm/{name}@{ver}" if ver else f"pkg:npm/{name}"
        out.append({"type": "library", "bom-ref": purl, "name": name, "version": ver, "purl": purl,
                    "licenses": [{"license": {"id": man.get("license") or "NOASSERTION"}}],
                    "hashes": [{"alg": "SHA-256", "content": _sha256_file(f)}],
                    "externalReferences": [{"type": "distribution", "url": man.get("source", "")}],
                    "properties": [{"name": "jt-glogarch:location",
                                    "value": f"glogarch/ai/assets/{f.name} ({man.get('used_for', '')})"}]})
    i18n = pkg_dir / "web" / "static" / "js" / "i18n.js"
    if i18n.is_file() and "Iconoir" in i18n.read_text(encoding="utf-8", errors="replace")[:600]:
        out.append({"type": "library", "bom-ref": "pkg:npm/iconoir", "name": "iconoir",
                    "purl": "pkg:npm/iconoir", "licenses": [{"license": {"id": "MIT"}}],
                    "properties": [{"name": "jt-glogarch:location",
                                    "value": "glogarch/web/static/js/i18n.js (SVG icons embedded)"}]})
    world = pkg_dir / "report" / "assets" / "worldmap.svg"
    if world.is_file():
        # Every point is Natural Earth 1:110m Admin 0 - Countries (x = lon+180,
        # y = 90-lat, 0.01 deg), checked 2026-11-16: 10,587 of 10,587 within 0.01 deg.
        out.append({"type": "data", "bom-ref": "file:glogarch/report/assets/worldmap.svg",
                    "name": "worldmap.svg",
                    "description": "World land outline derived from Natural Earth 1:110m Admin 0 - Countries",
                    "licenses": [{"license": {"name": "Public domain (Natural Earth)",
                                              "url": "https://www.naturalearthdata.com/about/terms-of-use/"}}],
                    "hashes": [{"alg": "SHA-256", "content": _sha256_file(world)}],
                    "externalReferences": [{"type": "website", "url": "https://www.naturalearthdata.com/"}],
                    "properties": [{"name": "jt-glogarch:location",
                                    "value": "glogarch/report/assets/worldmap.svg (PDF report map widget)"}]})
    # Code kept byte-for-byte as published, with a manifest per file (glogarch/vendor/).
    vend = pkg_dir / "vendor"
    for man_path in sorted(vend.glob("*.json")) if vend.is_dir() else []:
        src = man_path.with_suffix(".py")
        if not src.is_file():
            continue
        man = json.loads(man_path.read_text(encoding="utf-8"))
        name, ver = man.get("name", src.stem), man.get("version", "")
        ref = f"pkg:github/jasoncheng7115/jasontools-mcp@{man.get('commit') or ver}#{name}"
        comp = {"type": "library", "bom-ref": ref, "name": name, "version": ver, "purl": ref,
                "licenses": [{"license": {"id": man.get("license", "")}}] if man.get("license") else [],
                "hashes": [{"alg": "SHA-256", "content": _sha256_file(src)}],
                "externalReferences": [{"type": "vcs", "url": man["upstream"]}] if man.get("upstream") else [],
                "properties": [{"name": "jt-glogarch:location",
                                "value": f"glogarch/vendor/{src.name} (unmodified; AI chat / MCP tools)"}]}
        if man.get("author"):
            comp["author"] = man["author"]
        out.append(comp)
    return out


def browser_components(dists: dict[str, Dist], tarball: Path | None = None) -> list[dict]:
    """The Chromium build the installed / bundled Playwright drives."""
    pw = dists.get("playwright")
    raw = pw.extra_files.get("browsers.json") if pw else None
    if not raw:
        return []
    try:
        browsers = json.loads(raw).get("browsers", [])
    except ValueError:
        return []
    out = []
    for b in browsers:
        if b.get("name") not in ("chromium", "chromium-headless-shell"):
            continue
        ver = b.get("browserVersion") or ""
        ref = f"browser:{b['name']}@{ver}"
        c = {"type": "application", "bom-ref": ref, "name": b["name"], "version": ver,
             "licenses": [{"license": {"id": "BSD-3-Clause"}}],
             "properties": [{"name": "playwright:revision", "value": str(b.get("revision", ""))},
                            {"name": "jt-glogarch:used-by", "value": f"playwright {pw.version} (PDF reports)"}]}
        if tarball is not None and tarball.is_file():
            c["properties"].append({"name": "jt-glogarch:bundle-file", "value": tarball.name})
        out.append(c)
    if tarball is not None and tarball.is_file() and out:
        out[0]["hashes"] = [{"alg": "SHA-256", "content": _sha256_file(tarball)}]
    return out


def font_components(font_dir: Path) -> list[dict]:
    out = []
    for f in sorted(font_dir.glob("*")) if font_dir.is_dir() else []:
        if not f.is_file():
            continue
        lic = next((v for k, v in _FONT_LICENSES.items() if k in f.name.lower()), None)
        c = {"type": "data", "bom-ref": f"file:fonts/{f.name}", "name": f.name,
             "hashes": [{"alg": "SHA-256", "content": _sha256_file(f)}],
             "properties": [{"name": "jt-glogarch:location", "value": "fonts/ (CJK font for PDF reports)"}]}
        if lic:
            c["licenses"] = [{"expression": lic}]
        out.append(c)
    return out


def build(dists: dict[str, Dist], *, source: str, bundle_dir: Path | None = None,
          pkg_dir: Path = _PKG_DIR) -> dict:
    ordered, graph = closure(dists)
    root = ordered[0]
    root_ref = f"pkg:pypi/{root.key}@{root.version}"
    libs = [_pypi_component(d) for d in ordered[1:]]
    ref_of = {d.key: f"pkg:pypi/{d.key}@{d.version}" for d in ordered}
    vendored = vendored_components(pkg_dir)
    browsers = browser_components(dists, (bundle_dir / "chromium-browser.tar.gz") if bundle_dir else None)
    fonts = font_components(bundle_dir / "fonts") if bundle_dir else []
    components = libs + vendored + browsers + fonts
    deps = [{"ref": root_ref,
             "dependsOn": [ref_of[k] for k in graph.get(root.key, [])] + [c["bom-ref"] for c in vendored + browsers + fonts]}]
    for d in ordered[1:]:
        deps.append({"ref": ref_of[d.key], "dependsOn": [ref_of[k] for k in graph.get(d.key, [])]})
    meta_root = {"type": "application", "bom-ref": root_ref, "name": ROOT_NAME, "version": root.version,
                 "purl": root_ref, "licenses": [{"license": {"id": "AGPL-3.0-or-later"}}],
                 "supplier": {"name": "Jason Tools"},
                 "externalReferences": [{"type": "vcs", "url": "https://github.com/jasoncheng7115/jt-glogarch"}]}
    if root.sha256:
        meta_root["hashes"] = [{"alg": "SHA-256", "content": root.sha256}]
    py = "%d.%d.%d" % sys.version_info[:3]
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(),
            "tools": {"components": [{"type": "application", "name": "glogarch.sbom", "version": root.version}]},
            "component": meta_root,
            "properties": [
                {"name": "jt-glogarch:sbom-source", "value": source},
                {"name": "jt-glogarch:python", "value": f"CPython {py} ({sys.platform})"},
                {"name": "jt-glogarch:extras", "value": ",".join(sorted(SHIPPED_EXTRAS))
                 + " (included when present; dev extra excluded)"},
            ],
        },
        "components": components,
        "dependencies": deps,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="glogarch.sbom", description=__doc__.split("\n\n")[0])
    ap.add_argument("--wheels", help="describe the wheels in this directory (offline bundle) "
                                     "instead of what is installed")
    ap.add_argument("-o", "--output", help="write here instead of stdout")
    a = ap.parse_args(argv)
    if a.wheels:
        bom = build(wheel_dists(a.wheels), source="offline bundle wheels", bundle_dir=Path(a.wheels))
    else:
        bom = build(installed_dists(), source="installed distributions on the host that ran it")
    text = json.dumps(bom, indent=1, ensure_ascii=False) + "\n"
    if a.output:
        tmp = a.output + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, a.output)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
