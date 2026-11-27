# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Which Graylog fields and queries the built-in detectors read (added 1.35).

The detectors were written for GIM field names (`event_category`,
`source_ip`, `user_name`, ...), which is what the Jason Tools parsing packs
produce. A site whose logs carry other names saw every detection as "no data".
`security.field_map` lets a site say where each thing is; a key that is not
set keeps the GIM default, so a site that never sets one behaves exactly as
before.

This is the ONE place the detectors, the AI evidence and the Security page
read field names and event queries from. Two rules for one decision is how
they would start to disagree.

Measured on a production site (2026-11-21): 42% of the sshd login failures had
the peer in `sourceip` and the account in `user` (an older extractor), the
rest had them only in the message text; `source_ip` / `user_name` were empty
for 9,595 of 9,599. `detect()` is what finds that kind of thing.
"""
from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass

from glogarch.security.detectors import AUTH_FAIL, AUTH_OK, PROBES, WAF_BLOCKED, Probe

FIELD_RE = re.compile(r"[A-Za-z0-9_.@-]{1,100}")
MAX_QUERY = 500
MAX_LIST = 4

# key -> (kind, default). kind: query | field | fields (comma list, first one first)
SPEC: dict[str, tuple[str, str]] = {
    "q_auth_failure": ("query", AUTH_FAIL),
    "q_auth_success": ("query", AUTH_OK),
    "q_ids_passed": ("query", PROBES["ids_passed"].query),
    "q_web_attack": ("query", PROBES["waf_peer"].query),
    # which of those the WAF refused (1.35; read together with q_web_attack)
    "q_waf_blocked": ("query", WAF_BLOCKED),
    "f_peer": ("fields", ",".join(PROBES["auth_fail_peer"].fields)),
    "f_account": ("field", "user_name"),
    "f_host": ("field", "source"),
    "f_ids_signature": ("field", "alert_signature"),
    "f_ids_severity": ("field", "alert_severity"),
    "f_ids_peer": ("field", "source_ip"),
    "f_waf_peer": ("fields", ",".join(PROBES["waf_peer"].fields)),
    "f_uri": ("field", "uri"),
    "f_vhost": ("field", "vhost"),
    "f_status": ("field", "http_response_code"),
    "f_category": ("field", "event_category"),
}
KEYS = tuple(SPEC)

# Which keys belong to which group of the page, and the query a group's fields
# are looked for under (detect()).
GROUPS = {
    "auth": ("q_auth_failure", "q_auth_success", "f_peer", "f_account", "f_host"),
    "ids": ("q_ids_passed", "f_ids_signature", "f_ids_severity", "f_ids_peer"),
    "waf": ("q_web_attack", "q_waf_blocked", "f_waf_peer", "f_uri", "f_vhost", "f_status"),
    "other": ("f_category",),
}


def _split(v: str) -> tuple[str, ...]:
    return tuple(x.strip() for x in str(v or "").split(",") if x.strip())


def validate(raw: dict) -> tuple[dict[str, str], list[str]]:
    """The stored form of a field map from what a page or a file sent: unknown
    keys refused, an empty value or the default left out (= default)."""
    out, errors = {}, []
    if not isinstance(raw, dict):
        return {}, ["Field map: expected an object"]
    for k, v in raw.items():
        if k not in SPEC:
            errors.append(f"Field map: unknown key {k}")
            continue
        kind, default = SPEC[k]
        v = re.sub(r"\s+", " ", str(v if v is not None else "")).strip()
        if not v:
            continue
        if kind == "query":
            if len(v) > MAX_QUERY:
                errors.append(f"Field map: {k} is longer than {MAX_QUERY} characters")
                continue
        else:
            parts = _split(v)
            if kind == "field" and len(parts) != 1:
                errors.append(f"Field map: {k} takes one field")
                continue
            if len(parts) > MAX_LIST:
                errors.append(f"Field map: {k} takes at most {MAX_LIST} fields")
                continue
            bad = [p for p in parts if not FIELD_RE.fullmatch(p) or p.startswith("gl2_")]
            if bad:
                errors.append(f"Field map: {bad[0]} is not a usable Graylog field name")
                continue
            v = ",".join(dict.fromkeys(parts))
        if v != default:
            out[k] = v
    return out, errors


@dataclass(frozen=True)
class FieldMap:
    q_auth_failure: str
    q_auth_success: str
    q_ids_passed: str
    q_web_attack: str
    q_waf_blocked: str
    peer: tuple[str, ...]
    account: str
    host: str
    ids_signature: str
    ids_severity: str
    ids_peer: str
    waf_peer: tuple[str, ...]
    uri: str
    vhost: str
    status: str
    category: str

    @classmethod
    def from_config(cls, stored: dict | None) -> "FieldMap":
        """A stored map that no longer validates falls back key by key to the
        default: a hand-edited config.yaml must not stop the analysis."""
        clean, _ = validate(stored or {})
        v = {k: clean.get(k, SPEC[k][1]) for k in KEYS}
        return cls(q_auth_failure=v["q_auth_failure"], q_auth_success=v["q_auth_success"],
                   q_ids_passed=v["q_ids_passed"], q_web_attack=v["q_web_attack"],
                   q_waf_blocked=v["q_waf_blocked"], peer=_split(v["f_peer"]), account=v["f_account"], host=v["f_host"],
                   ids_signature=v["f_ids_signature"], ids_severity=v["f_ids_severity"],
                   ids_peer=v["f_ids_peer"], waf_peer=_split(v["f_waf_peer"]),
                   uri=v["f_uri"], vhost=v["f_vhost"], status=v["f_status"],
                   category=v["f_category"])

    def values(self) -> dict[str, str]:
        return {"q_auth_failure": self.q_auth_failure, "q_auth_success": self.q_auth_success,
                "q_ids_passed": self.q_ids_passed, "q_web_attack": self.q_web_attack,
                "q_waf_blocked": self.q_waf_blocked, "f_peer": ",".join(self.peer), "f_account": self.account, "f_host": self.host,
                "f_ids_signature": self.ids_signature, "f_ids_severity": self.ids_severity,
                "f_ids_peer": self.ids_peer, "f_waf_peer": ",".join(self.waf_peer),
                "f_uri": self.uri, "f_vhost": self.vhost, "f_status": self.status,
                "f_category": self.category}

    def field(self, name: str, ids: bool = False) -> str:
        """A GIM field name as this site spells it (fields the map does not
        cover are returned as they are). `ids`: the peer of an IDS alert."""
        return {"user_name": self.account, "source": self.host,
                "source_ip": self.ids_peer if ids else self.peer[0],
                "client_ip": self.waf_peer[0], "alert_signature": self.ids_signature,
                "alert_severity": self.ids_severity, "uri": self.uri, "vhost": self.vhost,
                "http_response_code": self.status, "event_category": self.category}.get(name, name)

    def probes(self) -> dict[str, Probe]:
        """detectors.PROBES with this site's queries and fields. Metric keys stay
        in GIM names (`canon`): stored incidents, severity rules and notification
        labels read them, whatever field a site counts."""
        a, h, p = self.account, self.host, self.peer

        def mk(base: Probe, query: str, fields: tuple, metrics: tuple) -> Probe:
            return Probe(base.id, query, fields, metrics, base.limit, canon=base.metrics)

        P = PROBES
        return {
            "auth_fail_peer": mk(P["auth_fail_peer"], self.q_auth_failure, p,
                                 (("count", None), ("card", a), ("card", h))),
            "auth_fail_account": mk(P["auth_fail_account"], self.q_auth_failure, (a,),
                                    (("count", None), ("card", h), ("card", p[0]))),
            "ids_passed": mk(P["ids_passed"], self.q_ids_passed, (self.ids_signature,),
                             (("count", None), ("card", self.ids_peer), ("min", self.ids_severity))),
            "waf_peer": mk(P["waf_peer"], self.q_web_attack, self.waf_peer,
                           (("count", None), ("card", self.uri), ("card", self.vhost))),
            "silent_sources": mk(P["silent_sources"], "*", (h,), (("count", None),)),
            "auth_ok_pairs": mk(P["auth_ok_pairs"], self.q_auth_success, (a, p[0]), (("count", None),)),
            "volume": mk(P["volume"], "*", (h, self.category), (("count", None),)),
        }

    def exclude_default(self, exclude: str) -> str:
        """A detector's default exclusion names the account field (machine accounts)."""
        if exclude.startswith("user_name:"):
            return f"{self.account}:" + exclude[len("user_name:"):]
        return exclude


DEFAULT = FieldMap.from_config({})


# ---- finding the fields (the "Find fields" button) ---------------------------------

_DEST = re.compile(r"(^|[_.])(dst|dest|destination|target_ip|server_ip|serverip|local|nat|translated)", re.I)
# Fields Graylog or a pipeline derives from another field (GeoIP, lookups): never the thing itself.
_DERIVED = re.compile(r"_(city_name|country_code|country_name|geolocation|reserved_ip|asn|as_organization|"
                      r"as_number|region|region_name|continent_code|latitude|longitude|port|hostname)$", re.I)
HINTS = {
    "f_account": re.compile(r"(^|[_.])(user|usr|account|acct|login|uid|principal|subject)([_.]|$)|user_?name$", re.I),
    "f_host": re.compile(r"^(source|host|hostname|host_name|computer|computer_?name|device|device_?name|dvc|"
                         r"agent_?name|beat_hostname|winlogbeat_computer_name)$", re.I),
    "f_ids_signature": re.compile(r"(signature|^sig_|rule_?name|alert_?name|alert_?msg|^msg$)", re.I),
    "f_ids_severity": re.compile(r"(sever|prio|level)", re.I),
    "f_uri": re.compile(r"(uri|url|path)", re.I),
    "f_vhost": re.compile(r"(vhost|virtual_?host|server_?name|http_?host|^domain$|^site$)", re.I),
    "f_status": re.compile(r"(status|response_?code|resp_?code)", re.I),
}
ADDRESS_KEYS = ("f_peer", "f_ids_peer", "f_waf_peer")
SAMPLE_SOURCES = 8
SAMPLE_PER_SOURCE = 15
MAX_CANDIDATES = 6
DETECT_DAYS = 7
GROUP_BY_INPUT = "gl2_source_input"


def _is_ip(v) -> bool:
    try:
        ipaddress.ip_address(str(v).strip())
        return True
    except ValueError:
        return False


def candidates(messages: list[dict], key: str) -> list[tuple[str, int, list[str]]]:
    """(field, messages having it, up to 3 example values) of the sampled
    messages that could hold `key`, most present first, destination-like
    fields last. Pure, for tests."""
    seen: dict[str, list] = {}
    for m in messages:
        for f, v in m.items():
            if f.startswith(("gl2_", "_")) or f in ("message", "full_message", "timestamp", "streams") \
                    or v in (None, "") or isinstance(v, (dict, list)) or _DERIVED.search(f):
                continue
            seen.setdefault(f, []).append(v)
    out = []
    hint = HINTS.get(key)
    for f, vals in seen.items():
        ips = sum(1 for v in vals if _is_ip(v))
        numeric = all(isinstance(v, (int, float)) or str(v).strip().lstrip("-").isdigit() for v in vals)
        if key in ADDRESS_KEYS:
            ok = ips >= 0.8 * len(vals)
        elif key in ("f_ids_severity", "f_status"):
            ok = numeric and bool(hint.search(f))
        else:
            ok = ips < 0.5 * len(vals) and not numeric and bool(hint.search(f))
        if not ok:
            continue
        ex = list(dict.fromkeys(str(v)[:60] for v in vals))[:3]
        out.append((f, len(vals), ex))
    out.sort(key=lambda x: (bool(_DEST.search(x[0])), -x[1], x[0]))
    return out[:MAX_CANDIDATES]


def _neg(q: str) -> str:
    # Lucene reads `a AND NOT b` fine, but a bare leading NOT matches nothing:
    # same rule as sigma.neg.
    return f"(*:* AND NOT ({q}))"


async def detect(ctx, group: str, fm: FieldMap) -> dict:
    """For one group of the page: how many events its queries match in the last
    DETECT_DAYS days, and for each field key the fields of a sample of those
    events that could hold it, with the EXACT number of events that have each
    (`count(field)` of one aggregation, measured 7.2.2: = events with the field)
    and how many have none of the listed fields, per Graylog input (which input
    needs parsing). Nothing is stored or changed: the administrator picks; a
    wrong field makes a detection quietly see nothing.

    Cost per group: per query one aggregation by input; one by host; a sample of
    up to SAMPLE_SOURCES x SAMPLE_PER_SOURCE messages (one chatty host must not
    hide the others' fields); per query one aggregation counting every candidate;
    per field key and query one count of events with none of them."""
    import asyncio

    from glogarch.ai.graylog_tools import _graylog_get, _graylog_post, _timerange
    from glogarch.security.engine import EMPTY, lucene_quote
    if group not in GROUPS or group == "other":
        raise ValueError("Unknown field group")
    vals = fm.values()
    # the blocked query only means something among the WAF events
    # (`event_action:blocked` alone is every firewall drop too)
    vals["q_waf_blocked"] = f"({vals['q_web_attack']}) AND ({vals['q_waf_blocked']})"
    qkeys = [k for k in GROUPS[group] if SPEC[k][0] == "query"]
    fkeys = [k for k in GROUPS[group] if SPEC[k][0] != "query"]
    tr = _timerange({"range_from": f"now-{DETECT_DAYS}d", "range_to": "now"})

    async def by_input(query: str, fields: list[str]) -> list[list]:
        body = {"query": query, "timerange": tr, "group_by": [{"field": GROUP_BY_INPUT, "limit": 100}],
                "metrics": [{"function": "count"}] + [{"function": "count", "field": f} for f in fields]}
        return (await _graylog_post(ctx, "/api/search/aggregate", body)).get("datarows") or []

    out: dict = {"group": group, "days": DETECT_DAYS, "queries": {}, "fields": {}, "sampled": 0}
    for qk in qkeys:
        rows = await by_input(vals[qk], [])
        out["queries"][qk] = {"query": vals[qk], "events": sum(int(r[1]) for r in rows)}
    live = [qk for qk in qkeys if out["queries"][qk]["events"]]
    if not live:
        return out
    either = " OR ".join(f"({vals[qk]})" for qk in live)
    tops = await _graylog_post(ctx, "/api/search/aggregate", {
        "query": either, "timerange": tr, "group_by": [{"field": "source", "limit": SAMPLE_SOURCES}],
        "metrics": [{"function": "count"}]})
    hosts = [r[0] for r in tops.get("datarows") or [] if r and r[0] not in (None, "", EMPTY)]
    sem = asyncio.Semaphore(3)

    async def sample(h):
        q = either if h is None else f"({either}) AND source:{lucene_quote(str(h))}"
        async with sem:
            res = await _graylog_get(ctx, "/api/search/universal/absolute", {
                "query": q, "from": tr["from"], "to": tr["to"], "limit": SAMPLE_PER_SOURCE,
                "sort": "timestamp:desc", "decorate": "false"})
        return [m.get("message") or {} for m in res.get("messages") or []]
    msgs = [m for part in await asyncio.gather(*(sample(h) for h in (hosts or [None]))) for m in part]
    out["sampled"] = len(msgs)

    names_by_key: dict[str, list[str]] = {}
    examples: dict[str, list[str]] = {}
    for key in fkeys:
        current = list(_split(vals[key]))
        found = candidates(msgs, key)
        for f, _, ex in found:
            examples.setdefault(f, ex)
        names_by_key[key] = list(dict.fromkeys([*current, *(f for f, _, _ in found)]))
    every = list(dict.fromkeys(f for names in names_by_key.values() for f in names))
    have: dict[str, dict[str, int]] = {}
    for qk in live:
        rows = await by_input(vals[qk], every)
        have[qk] = {f: sum(int(r[2 + i]) for r in rows) for i, f in enumerate(every)}
    for key in fkeys:
        current = set(_split(vals[key]))
        items = []
        for f in names_by_key[key]:
            share = {}
            for qk in live:
                tot = out["queries"][qk]["events"]
                n = have[qk].get(f, 0)
                share[qk] = {"events": n, "pct": round(100.0 * n / tot, 1) if tot else 0.0}
            items.append({"field": f, "current": f in current, "examples": examples.get(f, []),
                          "destination_like": bool(_DEST.search(f)), "share": share})
        none = {}
        for qk in live:
            ors = " OR ".join(f"_exists_:{f}" for f in names_by_key[key])
            rows = await by_input(f"({vals[qk]}) AND {_neg(ors)}", []) if ors else []
            none[qk] = {"events": sum(int(r[1]) for r in rows),
                        "inputs": [{"input": r[0], "events": int(r[1])} for r in
                                   sorted(rows, key=lambda r: -int(r[1]))[:5]]}
        out["fields"][key] = {"candidates": items, "none": none}
    return out
