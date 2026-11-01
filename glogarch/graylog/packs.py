# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Graylog content packs: explain one, check it before install, keep a local library.

What Graylog actually does (measured on 7.1.9, 2026-11-01):

* A revision is immutable: uploading the same id + rev is a 400. "Editing" a pack means
  uploading it again with a higher rev; nothing already installed changes.
* Graylog does not check the id: `not-a-uuid` uploads fine. validate_pack() does.
* A failed install is a bare HTTP 500 ("Failed to install content pack") and rolls back the
  whole pack, so check_install() has to name the reason BEFORE it happens. Pipeline and rule
  titles are unique, which is why a site cannot install a pack it was built from.
* A stream comes out of an install PAUSED whatever the pack says ("disabled": false is
  ignored). Dashboards built on it stay empty until someone starts it; a customer hit this.
* A revision with an installation cannot be deleted (400).
* Install takes {"entity": {...}, "share_request": null} on 7 and a flat body on 6.

The library has two sources. The directory inside this package is what GitHub and every
customer gets, and it ships EMPTY; a pack gets there only when its owner publishes it. The
local directory holds the rest and is never published, see local_library_dir().
"""

from __future__ import annotations

import asyncio
import copy
import difflib
import json
import os
import re
import uuid
from pathlib import Path
from typing import Any

from glogarch.graylog.alerting import AlertingClient, GraylogPermissionError
from glogarch.utils.logging import get_logger

log = get_logger("graylog.packs")

BUNDLED_DIR = Path(__file__).resolve().parent.parent / "jt_library"
DEFAULT_STREAM_ID = "000000000000000000000001"
MAX_PACK_BYTES = 32 * 1024 * 1024
GUIDE_NOTES_FILE = "guide-notes.i18n"
_DIFF_LINES = 400
_RULE_NAME = re.compile(r'^\s*rule\s+"([^"]+)"', re.M)
_PIPE_NAME = re.compile(r'^\s*pipeline\s+"([^"]+)"', re.M)
_STAGE = re.compile(r'^\s*stage\s+(-?\d+)\s+match\s+(\w+)', re.M)
_LOOKUP = re.compile(r'\blookup\w*\(\s*"([^"]+)"')


class PackError(ValueError):
    """The pack or the request is wrong; the message is shown to the user."""


def val(x: Any, default: Any = "") -> Any:
    """{"@type": "string", "@value": "x"} -> "x"; packs wrap most scalars that way."""
    if isinstance(x, dict) and "@value" in x:
        return x["@value"]
    return default if x is None else x


def is_pack_id(s: Any) -> bool:
    try:
        return str(uuid.UUID(str(s))) == str(s).lower()
    except ValueError:
        return False


def validate_pack(pack: Any) -> list[str]:
    """What is wrong with this as a pack; empty when it can be sent to Graylog."""
    if not isinstance(pack, dict):
        return ["Not a content pack: expected a JSON object"]
    errs = []
    if not is_pack_id(pack.get("id")):
        errs.append("Content pack id must be a UUID")
    if not isinstance(pack.get("rev"), int) or isinstance(pack.get("rev"), bool) or pack["rev"] < 1:
        errs.append("Content pack rev must be a positive integer")
    if not str(pack.get("name") or "").strip():
        errs.append("Content pack name is required")
    if not pack.get("v"):
        errs.append("Not a content pack: the format version is missing")
    ents = pack.get("entities")
    if not isinstance(ents, list):
        errs.append("Not a content pack: the entity list is missing")
        return errs
    seen = set()
    for i, e in enumerate(ents):
        if not (isinstance(e, dict) and e.get("id") and isinstance(e.get("type"), dict)
                and e["type"].get("name") and e.get("v") and isinstance(e.get("data"), dict)):
            errs.append(f"Entity {i + 1} is malformed")
        elif e["id"] in seen:
            errs.append(f"Entity {i + 1} repeats an id")
        else:
            seen.add(e["id"])
    return errs


def _title(e: dict) -> str:
    d = e.get("data") or {}
    for k in ("title", "name", "pattern_name"):
        t = val(d.get(k))
        if t:
            return str(t)
    return str(e.get("id") or "")


def _pivot_fields(pivots: Any) -> list[str]:
    return [f for p in pivots or [] for f in p.get("fields") or []]


def _dashboard_tabs(data: dict) -> list[dict]:
    """Tabs and widget layout, enough to draw the dashboard without running a query."""
    page_queries = {q.get("id"): (q.get("query") or {}).get("query_string") or ""
                    for q in ((data.get("search") or {}).get("queries") or [])}
    tabs = []
    state = data.get("state") or {}
    for sid, s in state.items():
        titles = s.get("titles") or {}
        names = titles.get("widget") or {}
        pos = s.get("positions") or {}
        widgets = []
        for w in s.get("widgets") or []:
            cfg = w.get("config") or {}
            p = pos.get(w.get("id")) or {}
            widgets.append({
                "id": w.get("id"), "title": names.get(w.get("id")) or "",
                "type": w.get("type") or "",
                "viz": cfg.get("visualization") or ("messages" if w.get("type") == "messages" else ""),
                "query": (w.get("query") or {}).get("query_string") or "",
                "rows": _pivot_fields(cfg.get("row_pivots")),
                "cols": _pivot_fields(cfg.get("column_pivots")),
                "series": [(x.get("config") or {}).get("name") or x.get("function") or ""
                           for x in cfg.get("series") or []],
                "fields": cfg.get("fields") or [],
                "col": p.get("col") or 1, "row": p.get("row") or 1,
                "width": p.get("width") or 4, "height": p.get("height") or 3,
            })
        widgets.sort(key=lambda x: (x["row"] if isinstance(x["row"], int) else 10 ** 6,
                                    x["col"] if isinstance(x["col"], int) else 10 ** 6))
        tabs.append({"id": sid, "title": (titles.get("tab") or {}).get("title") or "",
                     "query": page_queries.get(sid, ""), "widgets": widgets})
    return tabs


def _series_text(cfg: dict) -> str:
    out = []
    for s in cfg.get("series") or []:
        fn = s.get("type") or s.get("function") or ""
        out.append(f"{fn}({s.get('field') or ''})")
    return ", ".join(out)


def entity_view(e: dict) -> dict:
    """One entity with its wrappers removed, for the viewer."""
    d = e.get("data") or {}
    name = (e.get("type") or {}).get("name") or ""
    v: dict[str, Any] = {"id": e.get("id"), "type": name, "title": _title(e),
                         "description": str(val(d.get("description")) or val(d.get("summary")) or "")}
    if name == "pipeline_rule":
        v["source"] = str(val(d.get("source")))
    elif name == "pipeline":
        src = str(val(d.get("source")))
        stages = []
        chunks = list(_STAGE.finditer(src))
        for i, m in enumerate(chunks):
            end = chunks[i + 1].start() if i + 1 < len(chunks) else len(src)
            stages.append({"stage": int(m.group(1)), "match": m.group(2),
                           "rules": _RULE_NAME.findall(src[m.end():end])})
        v.update(source=src, stages=stages,
                 connected_streams=[str(val(x)) for x in d.get("connected_streams") or []])
    elif name == "stream":
        v.update(matching_type=str(val(d.get("matching_type"))),
                 rules=[{"type": str(val(r.get("type"))), "field": str(val(r.get("field"))),
                         "value": str(val(r.get("value"))), "inverted": bool(val(r.get("inverted"), False))}
                        for r in d.get("stream_rules") or []])
    elif name == "event_definition":
        cfg = d.get("config") or {}
        v.update(query=str(val(cfg.get("query"))), priority=val(d.get("priority"), None),
                 streams=[str(val(x)) for x in cfg.get("streams") or []],
                 group_by=[str(val(x)) for x in cfg.get("group_by") or []],
                 series=_series_text(cfg),
                 search_within_ms=val(cfg.get("search_within_ms"), None),
                 execute_every_ms=val(cfg.get("execute_every_ms"), None),
                 notifications=len(d.get("notifications") or []))
    elif name == "dashboard":
        v["tabs"] = _dashboard_tabs(d)
    return v


def analyze(pack: dict) -> dict:
    """What the pack holds and which references it cannot satisfy by itself."""
    ents = pack.get("entities") or []
    counts: dict[str, int] = {}
    rules, pipelines, streams, tables = set(), [], [], set()
    used_tables: set[str] = set()
    mismatched = []
    for e in ents:
        name = (e.get("type") or {}).get("name") or "?"
        counts[name] = counts.get(name, 0) + 1
        d = e.get("data") or {}
        if name == "pipeline_rule":
            title = _title(e)
            rules.add(title)
            src = str(val(d.get("source")))
            used_tables.update(_LOOKUP.findall(src))
            declared = _RULE_NAME.findall(src)
            if declared and declared[0] != title:
                mismatched.append(title)
        elif name == "pipeline":
            pipelines.append(e)
        elif name == "stream":
            streams.append(e)
        elif name == "lookup_table":
            tables.add(str(val(d.get("name")) or _title(e)))
    ids = {e.get("id") for e in ents}
    missing_rules, stream_refs, default_conn, unconnected = [], set(), [], []
    for e in pipelines:
        d = e.get("data") or {}
        for r in _RULE_NAME.findall(str(val(d.get("source")))):
            if r not in rules:
                missing_rules.append({"pipeline": _title(e), "rule": r})
        conn = [str(val(x)) for x in d.get("connected_streams") or []]
        if not conn:
            unconnected.append(_title(e))
        if DEFAULT_STREAM_ID in conn:
            default_conn.append(_title(e))
        stream_refs.update(c for c in conn if c not in ids and c != DEFAULT_STREAM_ID)
    for e in ents:
        if (e.get("type") or {}).get("name") == "event_definition":
            cfg = (e.get("data") or {}).get("config") or {}
            stream_refs.update(str(val(x)) for x in cfg.get("streams") or []
                               if str(val(x)) not in ids and str(val(x)) != DEFAULT_STREAM_ID)
    return {
        "counts": counts, "entity_count": len(ents),
        "missing_rules": missing_rules, "title_mismatch": mismatched,
        "stream_refs": sorted(stream_refs), "default_stream_pipelines": default_conn,
        "unconnected_pipelines": unconnected,
        "lookup_tables_used": sorted(used_tables - tables),
        "streams": [_title(e) for e in streams],
    }


def view_of(pack: dict) -> dict:
    """The viewer's whole payload; `pack` itself goes along so the editor can change it."""
    return {
        "pack": pack,
        "meta": {k: pack.get(k) for k in ("id", "rev", "name", "summary", "description",
                                          "vendor", "url", "created_at")},
        "parameters": pack.get("parameters") or [],
        "analysis": analyze(pack),
        "sensitive": scan_sensitive(pack),
        "entities": [entity_view(e) for e in pack.get("entities") or []],
    }


def list_item(pack: dict) -> dict:
    counts: dict[str, int] = {}
    for e in pack.get("entities") or []:
        n = (e.get("type") or {}).get("name") or "?"
        counts[n] = counts.get(n, 0) + 1
    return {"id": pack.get("id"), "rev": pack.get("rev"), "name": pack.get("name") or "",
            "summary": pack.get("summary") or "", "description": pack.get("description") or "",
            "vendor": pack.get("vendor") or "", "created_at": pack.get("created_at"),
            "entity_count": sum(counts.values()), "counts": counts,
            "sensitive": len(blocking_sensitive(pack))}


# --------------------------------------------------------------------------- #
# Before an install                                                           #
# --------------------------------------------------------------------------- #

def _version_tuple(s: str) -> tuple[int, ...]:
    m = re.match(r"\s*(\d+)(?:\.(\d+))?(?:\.(\d+))?", s or "")
    return tuple(int(x or 0) for x in m.groups()) if m else ()


def version_ok(constraint: str, have: str) -> bool | None:
    """A server-version constraint such as ">=7.0.0"; None when it cannot be read."""
    m = re.match(r"\s*(>=|<=|>|<|=)?\s*(.+)", constraint or "")
    want, cur = _version_tuple(m.group(2)) if m else (), _version_tuple(have)
    if not want or not cur:
        return None
    return {">=": cur >= want, ">": cur > want, "<=": cur <= want, "<": cur < want,
            "=": cur == want, None: cur >= want}[m.group(1)]


def check_install(pack: dict, live: dict) -> list[dict]:
    """Findings, worst first. level "block" means Graylog would refuse the install.

    live: version + sets of existing titles, or None for what this user may not read.
    """
    a = analyze(pack)
    out: list[dict] = []

    def add(level, code, items):
        if items:
            out.append({"level": level, "code": code, "items": sorted(set(items))})

    titles = {t: [_title(e) for e in pack.get("entities") or []
                  if (e.get("type") or {}).get("name") == t]
              for t in ("pipeline_rule", "pipeline", "stream", "dashboard", "event_definition")}
    for code, key, level, live_key in (("rule_title_taken", "pipeline_rule", "block", "rules"),
                                       ("pipeline_title_taken", "pipeline", "block", "pipelines"),
                                       ("stream_title_taken", "stream", "warn", "stream_titles"),
                                       ("dashboard_title_taken", "dashboard", "warn", "dashboards"),
                                       ("event_title_taken", "event_definition", "warn", "events")):
        have = live.get(live_key)
        if have is not None:
            add(level, code, [t for t in titles[key] if t in have])
    bad, other = set(), set()
    for e in pack.get("entities") or []:
        for c in e.get("constraints") or []:
            if c.get("type") == "server-version":
                if version_ok(str(c.get("version")), live.get("version") or "") is False:
                    bad.add(str(c.get("version")))
            elif c.get("type"):
                other.add(f"{c.get('plugin') or c.get('type')} {c.get('version') or ''}".strip())
    add("block", "version_too_old", bad)
    add("warn", "plugin_required", other)
    if live.get("lookup_tables") is not None:
        add("warn", "lookup_missing", [t for t in a["lookup_tables_used"]
                                       if t not in live["lookup_tables"]])
    if live.get("rules") is not None:
        add("warn", "rule_missing", [f'{m["pipeline"]}: {m["rule"]}' for m in a["missing_rules"]
                                     if m["rule"] not in live["rules"]])
    if live.get("stream_ids") is not None:
        add("warn", "stream_missing", [s for s in a["stream_refs"] if s not in live["stream_ids"]])
    add("warn", "title_mismatch", a["title_mismatch"])
    add("warn", "default_stream", a["default_stream_pipelines"])
    add("warn", "streams_start_paused", a["streams"])
    add("info", "pipeline_unconnected", a["unconnected_pipelines"])
    add("info", "parameters", [str(p.get("name")) for p in pack.get("parameters") or []])
    add("info", "not_checked", [k for k in ("rules", "pipelines", "stream_titles", "dashboards",
                                            "events", "lookup_tables") if live.get(k) is None])
    return sorted(out, key=lambda f: ("block", "warn", "info").index(f["level"]))


def _plain_numbers(x: Any) -> Any:
    """10.0 -> 10. The browser cannot keep the difference, so an edit would otherwise show
    every event definition's threshold as changed and bury the change that was made."""
    if isinstance(x, float) and x.is_integer():
        return int(x)
    if isinstance(x, list):
        return [_plain_numbers(i) for i in x]
    if isinstance(x, dict):
        return {k: _plain_numbers(v) for k, v in x.items()}
    return x


# --------------------------------------------------------------------------- #
# What must not travel with a pack                                            #
# --------------------------------------------------------------------------- #
# The owner once handed a customer a pack with their own e-mail address in a notification.
# A pack exports whatever the notification holds, and nothing in Graylog warns about it.

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
_URL = re.compile(r"\bhttps?://[^\s\"'<>)\]]+", re.I)
_URL_CRED = re.compile(r"\b[a-z][a-z0-9+.-]*://[^/\s:@]+:[^/\s@]+@", re.I)
_BEARER = re.compile(r"\b(?:Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{10,}")
# password=abc inside a text; not when the "value" is a pattern or a reference.
_INLINE_CRED = re.compile(r"\b(?:pass(?:word|wd)?|pwd|secret|token|api[_-]?key)\s*[=:]\s*['\"]?([^\s'\",&;)]{4,})", re.I)
_CRED_KEY = re.compile(r"pass(word|wd)?|secret|token|api[_-]?key|apikey|authorization|bearer|credential"
                       r"|private[_-]?key|webhook|routing[_-]?key|integration[_-]?key|access[_-]?key", re.I)
_NOT_A_CRED = {"", "disabled", "optional", "required", "none", "null", "true", "false", "********"}
_PRIVATE_IP = re.compile(r"\b(?:10\.\d{1,3}|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b")
# Where a URL is an endpoint someone runs, not a link in a description.
_ENDPOINT_TYPES = {"notification", "output", "lookup_adapter", "input"}
# Graylog's own packs name these. A warning on every default pack teaches people to click past it.
_PUBLIC_EMAIL_DOMAINS = {"graylog.com", "graylog.org"}
_PUBLIC_URL = re.compile(r"https?://(?:[\w-]+\.)*(?:graylog\.(?:com|org)|alienvault\.com|spamhaus\.org|torproject\.org"
                         r"|abuse\.ch|github\.com/Graylog2)(?:[/:?#]|$)", re.I)
# level "block" stops a download or an upload until someone decides; "info" is only shown.
SENSITIVE_BLOCK = {"email", "credential", "endpoint"}


def _mask_email(v: str) -> str:
    name, _, dom = v.partition("@")
    return f"{name[:2]}***@{dom}"


def _mask_secret(v: str) -> str:
    return f"{v[:2]}*** ({len(v)})" if len(v) > 6 else "***"


def _walk_strings(o: Any, path: tuple = ()):
    """(path, parent container, key, string) for every string under o."""
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(v, str):
                yield (*path, str(k)), o, k, v
            else:
                yield from _walk_strings(v, (*path, str(k)))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            if isinstance(v, str):
                yield path, o, i, v
            else:
                yield from _walk_strings(v, path)


def _sensitive_in(entity_type: str, title: str, data: Any) -> list[dict]:
    out = []

    def add(kind, path, value):
        keys = [k for k in path if k != "@value"]
        out.append({"kind": kind, "entity_type": entity_type, "entity": title,
                    "where": ".".join(keys[-3:]), "value": value})

    for path, _, _, text in _walk_strings(data):
        keys = [k for k in path if k not in ("@value", "@type")]
        if path and path[-1] == "@type":
            continue
        key = keys[-1] if keys else ""
        if _CRED_KEY.search(key) and text.strip().lower() not in _NOT_A_CRED and not text.startswith("${"):
            add("credential", path, _mask_secret(text))
            continue
        for m in _EMAIL.finditer(text):
            if m.group().rpartition("@")[2].lower() not in _PUBLIC_EMAIL_DOMAINS:
                add("email", path, _mask_email(m.group()))
        if _URL_CRED.search(text) or _BEARER.search(text):
            add("credential", path, _mask_secret(text))
        else:
            for m in _INLINE_CRED.finditer(text):
                if m.group(1)[0] not in "%$([{\\<":
                    add("credential", path, _mask_secret(m.group(1)))
        for m in _URL.finditer(text):
            private = entity_type in _ENDPOINT_TYPES and not _PUBLIC_URL.match(m.group())
            add("endpoint" if private else "url", path, m.group()[:80])
        for m in _PRIVATE_IP.finditer(text):
            add("internal_ip", path, m.group())
    return out


def scan_sensitive(pack: dict) -> list[dict]:
    """Everything in a pack that identifies someone or opens something. Deduplicated."""
    found = []
    head = {k: pack.get(k) for k in ("name", "summary", "description", "vendor")}
    found += _sensitive_in("pack", str(pack.get("name") or ""), head)
    for e in pack.get("entities") or []:
        found += _sensitive_in((e.get("type") or {}).get("name") or "", _title(e), e.get("data") or {})
    seen, out = set(), []
    for f in found:
        k = (f["kind"], f["entity_type"], f["entity"], f["where"], f["value"])
        if k not in seen:
            seen.add(k)
            out.append(f)
    return out


def blocking_sensitive(pack: dict) -> list[dict]:
    return [f for f in scan_sensitive(pack) if f["kind"] in SENSITIVE_BLOCK]


def strip_sensitive(pack: dict) -> dict:
    """A copy safe to hand over: no notification at all (they exist to reach someone), and
    every address, endpoint and credential elsewhere blanked. Raises if anything is left."""
    out = copy.deepcopy(pack)
    gone = {e.get("id") for e in out.get("entities") or []
            if (e.get("type") or {}).get("name") == "notification"}
    out["entities"] = [e for e in out.get("entities") or [] if e.get("id") not in gone]
    for e in out["entities"]:
        d = e.get("data") or {}
        if (e.get("type") or {}).get("name") == "event_definition":
            d["notifications"] = []
    for root_type, root in [("pack", {k: out.get(k) for k in ("name", "summary", "description", "vendor")})] + \
            [((e.get("type") or {}).get("name") or "", e.get("data") or {}) for e in out["entities"]]:
        for path, parent, key, text in _walk_strings(root):
            if path and path[-1] == "@type":
                continue
            keys = [k for k in path if k not in ("@value", "@type")]
            if keys and _CRED_KEY.search(keys[-1]) and text.strip().lower() not in _NOT_A_CRED and not text.startswith("${"):
                parent[key] = ""
                continue
            email = lambda m: m.group() if m.group().rpartition("@")[2].lower() in _PUBLIC_EMAIL_DOMAINS else ""  # noqa: E731
            new = _BEARER.sub("", _URL_CRED.sub("", _EMAIL.sub(email, text)))
            new = _INLINE_CRED.sub(lambda m: m.group() if m.group(1)[0] in "%$([{\\<" else "", new)
            if root_type in _ENDPOINT_TYPES:
                new = _URL.sub(lambda m: m.group() if _PUBLIC_URL.match(m.group()) else "", new)
            parent[key] = new
        if root_type == "pack":
            for k, v in root.items():
                if k in out:
                    out[k] = v
    left = blocking_sensitive(out)
    if left:
        raise PackError("Could not remove all sensitive values from this content pack")
    return out


def _pretty(e: dict) -> list[str]:
    d = e.get("data") or {}
    src = val(d.get("source"))
    if isinstance(src, str) and src:
        return src.splitlines()
    return json.dumps(_plain_numbers(d), ensure_ascii=False, indent=2, sort_keys=True).splitlines()


def diff_packs(old: dict, new: dict) -> dict:
    """What an edit changes, for the review step before it is saved."""
    meta = [{"field": k, "old": old.get(k), "new": new.get(k)}
            for k in ("name", "summary", "description", "vendor", "url")
            if (old.get(k) or "") != (new.get(k) or "")]
    a = {e.get("id"): e for e in old.get("entities") or []}
    b = {e.get("id"): e for e in new.get("entities") or []}
    label = lambda e: {"type": (e.get("type") or {}).get("name"), "title": _title(e)}  # noqa: E731
    changed = []
    for i, e in b.items():
        if i in a and a[i].get("data") != e.get("data"):     # 10.0 == 10, as it should here
            lines = list(difflib.unified_diff(_pretty(a[i]), _pretty(e), lineterm="", n=2))[2:]
            changed.append({**label(e), "diff": lines[:_DIFF_LINES], "truncated": len(lines) > _DIFF_LINES})
    return {"meta": meta, "removed": [label(e) for i, e in a.items() if i not in b],
            "added": [label(e) for i, e in b.items() if i not in a], "changed": changed,
            "parameters_changed": (old.get("parameters") or []) != (new.get("parameters") or [])}


def as_new_revision(pack: dict, base_id: str, rev: int) -> dict:
    """The edited pack as revision `rev`; the id cannot change through an edit."""
    out = copy.deepcopy(pack)
    out.update(id=base_id, rev=rev)
    out.pop("created_at", None)
    return out


def same_content(a: dict, b: dict) -> bool:
    """Whether two copies of one id + rev are really the same pack."""
    def key(p):
        ents = sorted(p.get("entities") or [], key=lambda e: str(e.get("id")))
        return [p.get("name"), [[e.get("id"), e.get("data")] for e in ents]]
    return key(a) == key(b)


# --------------------------------------------------------------------------- #
# Graylog                                                                     #
# --------------------------------------------------------------------------- #

class PackClient(AlertingClient):
    """Installing a big pack takes a while; a timeout here would lie about the outcome."""

    def __init__(self, url: str, auth: tuple[str, str], verify_ssl: bool = False):
        super().__init__(url, auth, verify_ssl, timeout=300.0)

    async def latest(self) -> tuple[list[dict], dict]:
        d = await self._req("GET", "/system/content_packs/latest")
        return d.get("content_packs") or [], d.get("content_packs_metadata") or {}

    async def revisions(self, pack_id: str) -> dict:
        return await self._req("GET", f"/system/content_packs/{pack_id}")

    async def get_pack(self, pack_id: str, rev: int) -> dict:
        d = await self._req("GET", f"/system/content_packs/{pack_id}/{rev}")
        return d.get("content_pack") or {}

    async def has_revision(self, pack_id: str, rev: int) -> dict | None:
        try:
            return await self.get_pack(pack_id, rev)
        except RuntimeError as e:
            if "HTTP 404" in str(e):
                return None
            raise

    async def upload(self, pack: dict) -> None:
        await self._req("POST", "/system/content_packs", json=pack)

    async def delete_revision(self, pack_id: str, rev: int) -> None:
        await self._req("DELETE", f"/system/content_packs/{pack_id}/{rev}")

    async def delete_all(self, pack_id: str) -> None:
        await self._req("DELETE", f"/system/content_packs/{pack_id}")

    async def installations(self, pack_id: str) -> list[dict]:
        d = await self._req("GET", f"/system/content_packs/{pack_id}/installations")
        return d.get("installations") or []

    async def install(self, pack_id: str, rev: int, parameters: dict, comment: str) -> dict:
        body = {"parameters": parameters or {}, "comment": comment or ""}
        path = f"/system/content_packs/{pack_id}/{rev}/installations"
        try:
            return await self._req("POST", path, json={"entity": body, "share_request": None})
        except RuntimeError as e:
            if "HTTP 400" not in str(e):
                raise
            return await self._req("POST", path, json=body)

    async def uninstall_details(self, pack_id: str, install_id: str) -> dict:
        return await self._req("GET", f"/system/content_packs/{pack_id}/installations/{install_id}/uninstall_details")

    async def uninstall(self, pack_id: str, install_id: str) -> dict:
        return await self._req("DELETE", f"/system/content_packs/{pack_id}/installations/{install_id}")

    async def start_stream(self, stream_id: str) -> None:
        await self._req("POST", f"/streams/{stream_id}/resume")

    async def parse_source(self, kind: str, source: str) -> list[dict]:
        """Graylog's own parser; writes nothing. Empty means the source is valid."""
        path = "/system/pipelines/rule/parse" if kind == "pipeline_rule" else "/system/pipelines/pipeline/parse"
        body = {"title": "", "description": "", "source": source}
        r = await self._client.post(self.base + path, json=body)
        if r.status_code in (200, 201):
            return []
        if r.status_code == 400:
            try:
                d = r.json()
            except ValueError:
                d = None
            if isinstance(d, list):
                return [{"line": x.get("line"), "reason": x.get("reason") or ""} for x in d]
            return [{"line": None, "reason": (d or {}).get("message") or r.text[:300]}]
        return await self._req("POST", path, json=body)

    async def _titles(self, path: str, key: str | None, field: str = "title") -> set[str] | None:
        try:
            if key:
                items = await self._paged(path, key)
            else:
                items = await self._req("GET", path)
        except (GraylogPermissionError, RuntimeError) as e:
            log.info("Could not read this for the install check", path=path, error=str(e))
            return None
        return {str(i.get(field)) for i in items}

    async def live_state(self) -> dict:
        """What an install can collide with. None = this user may not read it, and the
        finding says the check did not happen rather than reporting no conflict."""
        system, rules, pipes, lookups, dashes, events, streams = await asyncio.gather(
            self._req("GET", "/system"),
            self._titles("/system/pipelines/rule", None),
            self._titles("/system/pipelines/pipeline", None),
            self._titles("/system/lookup/tables", "lookup_tables", "name"),
            self._titles("/dashboards", "elements"),
            self._titles("/events/definitions", "event_definitions"),
            self._streams(),
        )
        return {"version": system.get("version") or "", "rules": rules, "pipelines": pipes,
                "lookup_tables": lookups, "dashboards": dashes, "events": events,
                "stream_titles": None if streams is None else {s.get("title") for s in streams},
                "stream_ids": None if streams is None else {s.get("id") for s in streams}}

    async def _streams(self) -> list[dict] | None:
        try:
            return (await self._req("GET", "/streams")).get("streams") or []
        except (GraylogPermissionError, RuntimeError) as e:
            log.info("Could not read streams for the install check", error=str(e))
            return None


# --------------------------------------------------------------------------- #
# The library                                                                 #
# --------------------------------------------------------------------------- #

def local_library_dir(database_path: str) -> Path:
    """Beside the database: inside the service's writable paths and outside the package,
    so neither a wheel, an offline bundle nor the GitHub mirror can pick it up."""
    env = os.environ.get("JT_PACK_LIBRARY", "").strip()
    return Path(env) if env else Path(database_path).resolve().parent / "jt-library"


class Library:
    def __init__(self, local_dir: Path, bundled_dir: Path = BUNDLED_DIR):
        self.local_dir, self.bundled_dir = Path(local_dir), Path(bundled_dir)

    def _scan(self) -> dict[tuple[str, int], tuple[Path, str]]:
        found: dict[tuple[str, int], tuple[Path, str]] = {}
        # Local last: an edited copy of a published pack wins over the published file.
        for root, origin in ((self.bundled_dir, "published"), (self.local_dir, "local")):
            if not root.is_dir():
                continue
            for p in sorted(root.rglob("*.json")):
                try:
                    pack = json.loads(p.read_text(encoding="utf-8"))
                except (OSError, ValueError) as e:
                    log.warning("Unreadable file in the content pack library", path=str(p), error=str(e))
                    continue
                if validate_pack(pack):
                    log.warning("Not a valid content pack, ignored", path=str(p))
                    continue
                found[(pack["id"], pack["rev"])] = (p, origin)
        return found

    def list(self) -> list[dict]:
        latest: dict[str, dict] = {}
        for (pid, rev), (path, origin) in self._scan().items():
            cur = latest.setdefault(pid, {"revs": [], "_top": -1})
            cur["revs"].append({"rev": rev, "origin": origin})
            if rev > cur["_top"]:
                cur.update(_top=rev, _path=path, origin=origin)
        items = []
        for pid, cur in latest.items():
            item = list_item(json.loads(cur["_path"].read_text(encoding="utf-8")))
            item.update(origin=cur["origin"], revs=sorted(cur["revs"], key=lambda r: r["rev"]))
            items.append(item)
        return sorted(items, key=lambda i: i["name"].lower())

    def get(self, pack_id: str, rev: int) -> tuple[dict, str]:
        hit = self._scan().get((pack_id, rev))
        if not hit:
            raise KeyError(f"{pack_id}/{rev}")
        return json.loads(hit[0].read_text(encoding="utf-8")), hit[1]

    def revisions(self, pack_id: str) -> list[int]:
        return sorted(r for (i, r) in self._scan() if i == pack_id)

    def guide_notes(self, pack_id: str) -> dict | None:
        """This pack's translated guide text, when the library has any. It is not named *.json
        so _scan() does not take it for a pack. Local wins, as for packs."""
        for root in (self.local_dir, self.bundled_dir):
            path = root / GUIDE_NOTES_FILE
            if not path.is_file():
                continue
            try:
                entry = json.loads(path.read_text(encoding="utf-8")).get(pack_id)
            except (OSError, ValueError, AttributeError) as e:
                log.warning("Unreadable guide notes in the library", path=str(path), error=str(e))
                continue
            if isinstance(entry, dict):
                return entry
        return None

    def add(self, pack: dict) -> Path:
        errs = validate_pack(pack)
        if errs:
            raise PackError(". ".join(errs))
        if (pack["id"], pack["rev"]) in self._scan():
            raise PackError("This revision is already in the library")
        folder = self.local_dir / pack["id"]
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{pack['rev']}.json"
        tmp = path.with_suffix(".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o640)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(pack, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
        return path

    def delete(self, pack_id: str, rev: int) -> None:
        hit = self._scan().get((pack_id, rev))
        if not hit:
            raise KeyError(f"{pack_id}/{rev}")
        if hit[1] != "local":
            raise PackError("A published content pack cannot be deleted here")
        hit[0].unlink()
        try:
            hit[0].parent.rmdir()
        except OSError:
            log.debug("Library folder still holds other revisions", path=str(hit[0].parent))
