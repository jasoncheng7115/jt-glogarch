# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Sigma rule library (added 1.33): SigmaHQ's official rule packages, downloaded.

OFF by default (internet egress is the site's decision). When on, the latest
release of SigmaHQ/sigma is checked about once a day and the chosen package is
downloaded only when the release changed. Every rule is parsed and converted
with this site's field map and kept in the DB as a library entry; nothing runs
until someone adds a rule to their own Sigma rules and enables it.

What the page can say about each entry, so a rule that can never match is not
mistaken for a quiet network: whether it converts (and why not), which Graylog
fields it uses, and which of those fields Graylog has actually seen
(`GET /api/system/fields`).

A rule added from the library remembers that (`origin`); when a newer release
changes it, it is converted again and replaced, keeping enabled / group by /
threshold; one that no longer converts is disabled with the reason. A rule
someone pasted by hand is never touched, even with the same Sigma id.

The download URLs are fixed here (nothing from the page), https only, and
redirects are followed only to GitHub's own hosts. The archive is read in
memory with size limits; nothing is written to disk.

SigmaHQ rules are published under the Detection Rule License (DRL) 1.1, which
asks that the rule's authors and source be credited: each entry keeps its
author and its path in the SigmaHQ repository, and the page shows both.
"""
from __future__ import annotations

import asyncio
import io
import json
import zipfile
from urllib.parse import urlparse

import httpx
import yaml

from glogarch.security.sigma import (MAX_RULE_BYTES, YAML_LOADER, SigmaError, convert, parse_rule,
                                     refuse_aliases, rule_from_doc)
from glogarch.utils.logging import get_logger

log = get_logger("security.sigma_library")

REPO = "SigmaHQ/sigma"
RELEASES_API = f"https://api.github.com/repos/{REPO}/releases/latest"
DOWNLOAD = f"https://github.com/{REPO}/releases/download/{{tag}}/{{asset}}"
SOURCE_URL = f"https://github.com/{REPO}/blob/master/{{path}}"
LICENSE = "Detection Rule License (DRL) 1.1"
LICENSE_URL = "https://github.com/SigmaHQ/Detection-Rule-License"
ALLOWED_HOSTS = {"api.github.com", "github.com", "objects.githubusercontent.com",
                 "release-assets.githubusercontent.com", "codeload.github.com"}

# Measured 2026-11-20 on release r2026-07-01: core = 1,376 rules (status test/stable,
# level high/critical), 1.4 MB; all rules = 3.2 MB.
PACKAGES: dict[str, dict] = {
    "core": {"asset": "sigma_core.zip", "about": "stable and test rules, high and critical level"},
    "core+": {"asset": "sigma_core+.zip", "about": "core plus medium level"},
    "core++": {"asset": "sigma_core++.zip", "about": "core+ plus experimental rules"},
    "emerging_threats": {"asset": "sigma_emerging_threats_addon.zip",
                         "about": "rules for specific recent threats and campaigns"},
    "all": {"asset": "sigma_all_rules.zip", "about": "every rule in the release"},
}
DEFAULT_PACKAGE = "core"
MAX_ZIP_BYTES = 30 * 1024 * 1024
MAX_UNZIPPED_BYTES = 120 * 1024 * 1024
MAX_RULES = 10000
MAX_FIELDS = 100000


class LibraryError(RuntimeError):
    pass


# --- reading a package -----------------------------------------------------------

def rule_fields(rule: dict, field_map: dict) -> list[str]:
    """The Graylog fields a parsed rule's detection looks at (after the field map).
    Keyword lists search `message`."""
    from glogarch.security.sigma import _GELF_FIELDS
    out: list[str] = []

    def add(name: str):
        f = field_map.get(name, _GELF_FIELDS.get(name, name))
        if f and f not in out:
            out.append(f)

    def walk(sel):
        if isinstance(sel, dict):
            for k in sel:
                add(str(k).split("|", 1)[0])
        elif isinstance(sel, list):
            for x in sel:
                if isinstance(x, (dict, list)):
                    walk(x)
                else:
                    add("message")
        elif sel is not None:
            add("message")

    for name, sel in (rule.get("detection") or {}).items():
        if name not in ("condition", "timeframe"):
            walk(sel)
    return out[:50]


def entry_from_yaml(text: str, path: str, field_map: dict) -> dict | None:
    """One library entry, or None when the file is not a Sigma rule with an id.
    A rule that does not parse or convert is kept, with the reason."""
    try:
        if len(text) > MAX_RULE_BYTES:
            return None
        refuse_aliases(text)          # a few nested aliases expand into gigabytes when stringified
        raw = yaml.load(text, Loader=YAML_LOADER)  # nosec B506 - a safe loader
    except (yaml.YAMLError, SigmaError):
        raw = None
    if not isinstance(raw, dict) or not raw.get("id"):
        return None
    ls = raw.get("logsource") if isinstance(raw.get("logsource"), dict) else {}
    base = {"sigma_id": str(raw["id"])[:64], "path": path[:300], "yaml": text,
            "title": str(raw.get("title") or path)[:200], "status": str(raw.get("status") or "")[:30],
            "level": str(raw.get("level") or "")[:20], "author": str(raw.get("author") or "")[:300],
            "modified": str(raw.get("modified") or raw.get("date") or "")[:20],
            "product": str(ls.get("product") or "")[:60], "category": str(ls.get("category") or "")[:60],
            "service": str(ls.get("service") or "")[:60],
            "tags": [str(t).lower() for t in (raw.get("tags") if isinstance(raw.get("tags"), list) else [])
                     if isinstance(t, (str, int))][:50]}
    return {**base, **convert_entry(text, field_map, raw)}


def convert_entry(text: str, field_map: dict, raw=None) -> dict:
    """Conversion of one rule's YAML (`raw` = the document already loaded from it)."""
    try:
        rule = rule_from_doc(raw) if raw is not None else parse_rule(text)
        return {"query": convert(rule, field_map), "error": "", "fields": rule_fields(rule, field_map)}
    except SigmaError as e:
        return {"query": "", "error": str(e)[:300], "fields": []}
    except Exception as e:   # one odd rule must not stop the whole package (or every later update)
        log.info("Sigma library rule could not be converted", error=f"{type(e).__name__}: {e}"[:200])
        return {"query": "", "error": f"Could not be converted ({type(e).__name__})", "fields": []}


def read_package(data: bytes, field_map: dict) -> tuple[list[dict], dict]:
    """A release zip -> (entries, info). In memory, size-limited, `rules*/…/*.yml` only."""
    if len(data) > MAX_ZIP_BYTES:
        raise LibraryError(f"package larger than {MAX_ZIP_BYTES // (1024 * 1024)} MB")
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as e:
        raise LibraryError(f"not a zip archive: {e}")
    entries: dict[str, dict] = {}
    info = {"version": "", "files": 0, "skipped": 0}
    total = 0
    with zf:
        for zi in zf.infolist():
            name = zi.filename
            if zi.is_dir():
                continue
            if name.rsplit("/", 1)[-1] == "version.txt":
                with zf.open(zi) as fh:   # read 2,000 bytes, never the whole (possibly huge) entry
                    info["version"] = fh.read(2000).decode("utf-8", "replace")
                continue
            if not name.startswith("rules") or not name.endswith((".yml", ".yaml")) or ".." in name:
                continue
            if zi.file_size > MAX_RULE_BYTES * 4:
                info["skipped"] += 1
                continue
            total += zi.file_size
            if total > MAX_UNZIPPED_BYTES:
                raise LibraryError("package expands to more than the size limit")
            info["files"] += 1
            try:
                e = entry_from_yaml(zf.read(zi).decode("utf-8", "replace"), name, field_map)
            except Exception as ex:   # never let one file end the whole refresh
                log.info("Sigma library file skipped", path=name[:200], error=f"{type(ex).__name__}: {ex}"[:200])
                e = None
            if e is None or e["sigma_id"] in entries:
                info["skipped"] += 1
                continue
            entries[e["sigma_id"]] = e
            if len(entries) >= MAX_RULES:
                break
    if not entries:
        raise LibraryError("the package held no Sigma rules")
    return list(entries.values()), info


def version_label(text: str) -> str:
    for ln in (text or "").splitlines():
        if ln.lower().startswith("label:"):
            return ln.split(":", 1)[1].strip()[:80]
    return ""


# --- download --------------------------------------------------------------------

def _allowed(url: str) -> bool:
    u = urlparse(url)
    try:
        port = u.port
    except ValueError:
        return False
    return u.scheme == "https" and (u.hostname or "") in ALLOWED_HOSTS and port in (None, 443)


DOWNLOAD_DEADLINE_SEC = 600   # the whole download: a server trickling one chunk a minute cannot hold it forever


async def _get(client: httpx.AsyncClient, url: str, limit: int) -> bytes:
    """_get_once with an overall deadline (httpx's timeout applies per read)."""
    try:
        return await asyncio.wait_for(_get_once(client, url, limit), DOWNLOAD_DEADLINE_SEC)
    except asyncio.TimeoutError:
        raise LibraryError(f"download took longer than {DOWNLOAD_DEADLINE_SEC // 60} minutes")


async def _get_once(client: httpx.AsyncClient, url: str, limit: int) -> bytes:
    """GET following at most 5 redirects, each to an allowed GitHub host, with a size cap."""
    for _ in range(6):
        if not _allowed(url):
            raise LibraryError(f"refusing to download from {urlparse(url).hostname or url!r}")
        async with client.stream("GET", url) as r:
            if r.status_code in (301, 302, 303, 307, 308):
                url = str(r.url.join(r.headers.get("location", "")))
                continue
            r.raise_for_status()
            buf = bytearray()
            async for chunk in r.aiter_bytes():
                buf += chunk
                if len(buf) > limit:
                    raise LibraryError(f"download larger than {limit // (1024 * 1024)} MB")
            return bytes(buf)
    raise LibraryError("too many redirects")


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=60, follow_redirects=False,
                             headers={"User-Agent": "jt-glogarch sigma-library",
                                      "Accept": "application/vnd.github+json"})


async def latest_release(client: httpx.AsyncClient) -> dict:
    d = json.loads(await _get(client, RELEASES_API, 2 * 1024 * 1024))
    tag = str(d.get("tag_name") or "")
    if not tag or "/" in tag or ".." in tag:
        raise LibraryError("GitHub returned no usable release")
    return {"tag": tag, "published_at": str(d.get("published_at") or "")[:30],
            "assets": [str(a.get("name") or "") for a in d.get("assets") or []]}


async def graylog_fields(server, rate_limit) -> list[str]:
    """Every field name Graylog has seen in its indices (`GET /api/system/fields`)."""
    from glogarch.graylog.client import GraylogClient
    from glogarch.ratelimit.limiter import RateLimiter
    async with GraylogClient(server, RateLimiter(rate_limit)) as c:
        d = await c.get("/api/system/fields", params={"limit": MAX_FIELDS})
    fields = d.get("fields") if isinstance(d, dict) else None
    if not isinstance(fields, list):
        raise LibraryError("Graylog returned no field list")
    return sorted({str(f) for f in fields})[:MAX_FIELDS]


async def refresh(settings, db, *, force: bool = False, client: httpx.AsyncClient | None = None) -> dict:
    """Check the latest release; download and replace the library when it (or the
    package) changed, or when forced. Then update the rules added from the library."""
    cfg = settings.security
    package = cfg.sigma_library_package if cfg.sigma_library_package in PACKAGES else DEFAULT_PACKAGE
    meta = db.sigma_library_meta()
    own = client is None
    client = client or _client()
    try:
        try:
            rel = await latest_release(client)
            asset = PACKAGES[package]["asset"]
            if rel["assets"] and asset not in rel["assets"]:
                raise LibraryError(f"release {rel['tag']} has no {asset}")
            if not force and meta.get("tag") == rel["tag"] and meta.get("package") == package and meta.get("count"):
                db.set_sigma_library_meta({"checked_at": _now(), "error": ""})
                result = {"status": "current", "tag": rel["tag"], "count": int(meta["count"])}
            else:
                data = await _get(client, DOWNLOAD.format(tag=rel["tag"], asset=asset), MAX_ZIP_BYTES)
                # parsing thousands of rules is CPU work: off the web server's event loop
                entries, info = await asyncio.to_thread(read_package, data, cfg.sigma_field_map)
                db.replace_sigma_library(entries)
                db.set_sigma_library_meta({
                    "package": package, "tag": rel["tag"], "published_at": rel["published_at"],
                    "label": version_label(info["version"]), "count": str(len(entries)),
                    "converted": str(sum(1 for e in entries if e["query"])),
                    "downloaded_at": _now(), "checked_at": _now(), "error": ""})
                result = {"status": "downloaded", "tag": rel["tag"], "count": len(entries)}
        except Exception as e:
            err = str(e)[:300] or type(e).__name__
            db.set_sigma_library_meta({"checked_at": _now(), "error": err})
            log.warning("Sigma library refresh failed", error=err)
            return {"status": "error", "error": err}
    finally:
        if own:
            await client.aclose()
    try:
        server = settings.get_server(cfg.server or None)
        fields = await graylog_fields(server, settings.rate_limit)
        db.set_sigma_library_meta({"graylog_fields": json.dumps(fields), "fields_server": server.name,
                                   "fields_at": _now(), "fields_error": ""})
    except Exception as e:
        db.set_sigma_library_meta({"fields_error": str(e)[:300] or type(e).__name__})
        log.warning("Reading Graylog's field list failed", error=str(e)[:300])
    result["updated_rules"] = update_added_rules(db, cfg.sigma_field_map) if cfg.sigma_library_auto_update else []
    return result


def update_added_rules(db, field_map: dict) -> list[dict]:
    """Rules added from the library whose upstream text changed: convert again and
    replace, keeping enabled / group by / threshold; disable one that no longer converts."""
    changed = []
    for r in db.list_sigma_rules():
        if r.get("origin") != "library" or not r.get("sigma_id"):
            continue
        lib = db.get_sigma_library_entry(r["sigma_id"])
        if not lib:
            continue                      # gone upstream: keep the rule as it is
        cur = db.get_sigma_rule(r["id"])
        if lib["yaml"] == cur["yaml"]:
            continue
        conv = convert_entry(lib["yaml"], field_map)
        ch = {"yaml": lib["yaml"], "title": lib["title"], "tags": lib["tags"],
              "level": parse_level(lib["level"]), "query": conv["query"], "error": conv["error"]}
        if conv["error"]:
            ch["enabled"] = False
        db.update_sigma_rule(r["id"], ch)
        changed.append({"id": r["id"], "title": lib["title"], "disabled": bool(conv["error"] and cur["enabled"])})
    if changed:
        log.info("Sigma rules updated from the library", rules=len(changed))
    return changed


def parse_level(level: str) -> str:
    from glogarch.security.sigma import LEVELS
    lv = str(level or "").lower()
    return lv if lv in LEVELS else "medium"


def _now() -> str:
    from datetime import datetime
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
