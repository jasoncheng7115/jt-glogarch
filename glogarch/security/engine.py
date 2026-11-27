# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Runs the detectors against one Graylog and returns findings.

Pure with respect to I/O: the caller passes `fetch`, an async function that
performs ONE aggregation and returns its rows. The scheduler passes a Graylog
scripting-API fetcher; tests pass a fake.
"""
from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from typing import Awaitable, Callable

from glogarch.security.detectors import (
    BASELINE_HOURS, DETECTORS, SILENT_HOURS, Detector, Probe,
)
from glogarch.security.fieldmap import FieldMap

EMPTY = "(Empty Value)"
MAX_SUCCESS_CANDIDATES = 50

# fetch(query, group_field, metrics, time_from, time_to, limit) -> list[dict]
# Each row: {"entity": str, "count": int, "card:user_name": int, ...}
Fetch = Callable[[str, str, tuple, datetime, datetime, int], Awaitable[list[dict]]]


@dataclass
class Finding:
    detector: str
    entity: str
    entity_field: str
    severity: str
    metrics: dict
    external: bool | None
    query: str  # a Graylog search query that shows the events


@dataclass
class Coverage:
    probe: str
    field: str
    events: int = 0
    missing: int = 0     # events in the "(Empty Value)" bucket
    truncated: bool = False  # the group limit was reached
    error: str = ""


@dataclass
class RunResult:
    findings: list[Finding] = field(default_factory=list)
    coverage: list[Coverage] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    queries: int = 0
    sigma: dict = field(default_factory=dict)   # rule id -> {"count": int|None, "error": str}
    pairs: list = field(default_factory=list)   # (account, source, count) of successful logins
    # volume_anomaly: (field, key, count) of the window and the effective
    # min_count/exclude (the runner decides; it has the history).
    volumes: list = field(default_factory=list)
    volume_settings: dict | None = None


def metric_key(fn: str, fld: str | None) -> str:
    return fn if fld is None else f"{fn}:{fld}"


def is_external(value: str) -> bool | None:
    """True for a public address, False for private/loopback/link-local,
    None when the entity is not an address."""
    try:
        ip = ipaddress.ip_address(value.strip())
    except ValueError:
        return None
    return not (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified)


def lucene_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def build_query(base: str, *excludes: str) -> str:
    q = f"({base})"
    for ex in excludes:
        ex = (ex or "").strip()
        if ex:
            q += f" AND NOT ({ex})"
    return q


def severity_for(det: Detector, row: dict, external: bool | None) -> str | None:
    card = row.get(metric_key("card", det.min_card[0])) if det.min_card else None
    min_sev = row.get("min:alert_severity")
    for rule in det.severity:
        if "count" in rule and row.get("count", 0) < rule["count"]:
            continue
        if "card" in rule and (card is None or card < rule["card"]):
            continue
        if rule.get("external") and external is not True:
            continue
        if "max_sev" in rule and (min_sev is None or min_sev > rule["max_sev"]):
            continue
        return rule["sev"]
    return None


def canon_rows(probe: Probe, rows: list[dict]) -> list[dict]:
    """Metric keys back to their GIM names (`card:user` -> `card:user_name`)."""
    if not probe.canon or probe.canon == probe.metrics:
        return rows
    ren = {metric_key(*m): metric_key(*c) for m, c in zip(probe.metrics, probe.canon)}
    return [{ren.get(k, k): v for k, v in r.items()} for r in rows]


def qualifies(det: Detector, row: dict) -> bool:
    if row.get("count", 0) < det.min_count:
        return False
    if det.min_card:
        fld, n = det.min_card
        if (row.get(metric_key("card", fld)) or 0) < n:
            return False
    return True


async def run_detectors(fetch: Fetch, time_from: datetime, time_to: datetime, *,
                        settings: dict | None = None,
                        global_exclude: str = "",
                        sigma_rules: list[dict] | None = None,
                        fetch_pairs=None,
                        field_map: dict | None = None) -> RunResult:
    """`settings` maps detector id -> {"enabled": bool, "min_count": int,
    "exclude": str}; missing keys fall back to the detector's defaults.
    `field_map` = security.field_map (fieldmap.py): where this site keeps what."""
    settings = settings or {}
    fm = FieldMap.from_config(field_map)
    PROBES = fm.probes()
    res = RunResult()
    active: list[tuple[Detector, int, str]] = []
    for det in DETECTORS:
        s = settings.get(det.id) or {}
        if not s.get("enabled", det.default_enabled):
            continue
        min_count = int(s.get("min_count") or det.min_count)
        exclude = s["exclude"] if "exclude" in s else fm.exclude_default(det.exclude)
        blocked_min = int(s.get("blocked_min_count") or det.blocked_min_count) if det.blocked_min_count else 0
        active.append((replace(det, blocked_min_count=blocked_min), min_count, exclude))

    # One aggregation per (probe, field, exclusion): detectors sharing a probe
    # share its rows.
    cache: dict[tuple[str, str, str], list[dict] | None] = {}

    async def rows_for(probe: Probe, fld: str, exclude: str) -> list[dict] | None:
        key = (probe.id, fld, exclude)
        if key in cache:
            return cache[key]
        q = build_query(probe.query, exclude, global_exclude)
        cov = Coverage(probe.id, fld)
        try:
            res.queries += 1
            rows = canon_rows(probe, await fetch(q, fld, probe.metrics, time_from, time_to, probe.limit))
        except Exception as e:  # recorded per probe; the other probes still run
            cov.error = str(e)[:300]
            res.errors.append(f"{probe.id}/{fld}: {cov.error}")
            res.coverage.append(cov)
            cache[key] = None
            return None
        for r in rows:
            cov.events += int(r.get("count") or 0)
            if r.get("entity") == EMPTY:
                cov.missing += int(r.get("count") or 0)
        cov.truncated = len(rows) >= probe.limit
        res.coverage.append(cov)
        cache[key] = rows
        return rows

    for det, min_count, exclude in active:
        if det.id == "account_new_source":
            await _pairs(fetch_pairs, res, PROBES[det.probe], build_query(PROBES[det.probe].query, exclude, global_exclude),
                         time_from, time_to)
            continue
        if det.id == "volume_anomaly":
            await _volume(fetch, res, PROBES[det.probe], build_query("*", exclude, global_exclude), time_from, time_to)
            res.volume_settings = {"min_count": min_count, "exclude": exclude}
            continue
        if det.id == "source_silent":
            await _silent(fetch, res, PROBES[det.probe], min_count, build_query("*", exclude, global_exclude), time_to)
            continue
        probe = PROBES[det.probe]
        eff = replace(det, min_count=min_count)
        for fld in probe.fields:
            rows = await rows_for(probe, fld, exclude)
            if not rows:
                continue
            hits = [r for r in rows if r.get("entity") not in (None, "", EMPTY) and qualifies(eff, r)]
            if det.id == "auth_success_after_fail":
                hits = await _with_success(fetch, res, hits, fld, time_from, time_to,
                                           build_query(fm.q_auth_success, global_exclude))
            if det.blocked_min_count:
                hits = await _with_blocked(fetch, res, hits, fld, time_from, time_to,
                                           build_query(f"({probe.query}) AND ({fm.q_waf_blocked})",
                                                       exclude, global_exclude))
            for r in hits:
                ent = str(r["entity"])
                ext = is_external(ent)
                sev = severity_for(eff, r, ext)
                if sev is None:
                    continue
                if blocked_only(eff, r) and int(r.get("count") or 0) < det.blocked_min_count:
                    sev = "low"   # refused by the WAF and not a flood: recorded, not shouted
                res.findings.append(Finding(
                    detector=det.id, entity=ent, entity_field=fld, severity=sev,
                    metrics={k: v for k, v in r.items() if k != "entity"},
                    external=ext,
                    query=build_query(f"{probe.query} AND {fld}:{lucene_quote(ent)}",
                                      exclude, global_exclude),
                ))
    for rule in sigma_rules or []:
        await _sigma(fetch, res, rule, time_from, time_to, global_exclude)
    return res


SIGMA_LEVELS = {"informational": "low", "low": "low", "medium": "medium", "high": "high", "critical": "high"}


async def _sigma(fetch, res: RunResult, rule: dict, time_from, time_to, global_exclude: str) -> None:
    """One enabled Sigma rule: its converted query, counted per `group_by` (a host
    by default); every group at or above the rule's threshold is a finding."""
    fld = rule.get("group_by") or "source"
    q = build_query(rule["query"], global_exclude)
    try:
        res.queries += 1
        rows = await fetch(q, fld, (("count", None),), time_from, time_to, 100)
    except Exception as e:
        err = str(e)[:300]
        res.errors.append(f"sigma {rule['id']}: {err}")
        res.sigma[rule["id"]] = {"count": None, "error": err}
        return
    res.sigma[rule["id"]] = {"count": sum(int(r.get("count") or 0) for r in rows), "error": ""}
    for r in rows:
        ent = str(r.get("entity") or "")
        n = int(r.get("count") or 0)
        if not ent or ent == EMPTY or n < max(1, int(rule.get("threshold") or 1)):
            continue
        res.findings.append(Finding(
            detector=f"sigma:{rule['id']}", entity=ent, entity_field=fld,
            severity=SIGMA_LEVELS.get(rule.get("level"), "medium"),
            metrics={"count": n, "sigma_title": rule["title"], "sigma_tags": list(rule.get("tags") or [])},
            external=is_external(ent),
            query=build_query(f"({rule['query']}) AND {fld}:{lucene_quote(ent)}", global_exclude)))


async def _pairs(fetch_pairs, res: RunResult, probe: Probe, query: str, time_from, time_to) -> None:
    """Collects (account, source) pairs; the runner decides which are new (it has the history)."""
    cov = Coverage(probe.id, "+".join(probe.fields))
    if fetch_pairs is None:
        cov.error = "no pair aggregation available"
        res.coverage.append(cov)
        return
    try:
        res.queries += 1
        rows = await fetch_pairs(query, probe.fields, time_from, time_to, probe.limit)
    except Exception as e:
        cov.error = str(e)[:300]
        res.errors.append(f"{probe.id}: {cov.error}")
        res.coverage.append(cov)
        return
    for r in rows:
        n = int(r.get("count") or 0)
        cov.events += n
        a, b = str(r.get("a") or ""), str(r.get("b") or "")
        if a in ("", EMPTY) or b in ("", EMPTY):
            cov.missing += n
            continue
        res.pairs.append((a, b, n))
    cov.truncated = len(rows) >= probe.limit
    res.coverage.append(cov)


async def _volume(fetch, res: RunResult, probe: Probe, query: str, time_from, time_to) -> None:
    """Counts of the window per host and per event category; the runner compares
    them with their history (it has it)."""
    for fld in probe.fields:
        cov = Coverage(probe.id, fld)
        try:
            res.queries += 1
            rows = await fetch(query, fld, probe.metrics, time_from, time_to, probe.limit)
        except Exception as e:
            cov.error = str(e)[:300]
            res.errors.append(f"{probe.id}/{fld}: {cov.error}")
            res.coverage.append(cov)
            continue
        for r in rows:
            n = int(r.get("count") or 0)
            cov.events += n
            ent = str(r.get("entity") or "")
            if ent in ("", EMPTY):
                cov.missing += n
                continue
            res.volumes.append((fld, ent, n))
        cov.truncated = len(rows) >= probe.limit
        res.coverage.append(cov)


async def _silent(fetch, res: RunResult, probe: Probe, min_count: int, query: str, time_to: datetime) -> None:
    """Sources with >= min_count messages in the baseline window and none in the
    last SILENT_HOURS. Two aggregations; if the recent list is truncated (1000+
    sources still sending) nothing can be concluded, so nothing is reported."""
    recent_from = time_to - timedelta(hours=SILENT_HOURS)
    base_from = recent_from - timedelta(hours=BASELINE_HOURS)
    host = probe.fields[0]
    cov = Coverage(probe.id, host)
    try:
        res.queries += 2
        base = await fetch(query, host, probe.metrics, base_from, recent_from, probe.limit)
        recent = await fetch(query, host, probe.metrics, recent_from, time_to, probe.limit)
    except Exception as e:
        cov.error = str(e)[:300]
        res.errors.append(f"{probe.id}/{host}: {cov.error}")
        res.coverage.append(cov)
        return
    for r in base:
        cov.events += int(r.get("count") or 0)
        if r.get("entity") == EMPTY:
            cov.missing += int(r.get("count") or 0)
    cov.truncated = len(base) >= probe.limit
    res.coverage.append(cov)
    if len(recent) >= probe.limit:
        res.errors.append(f"{probe.id}/{host}: {probe.limit}+ sources in the last {SILENT_HOURS} h; "
                          "silence cannot be judged")
        return
    still = {str(r.get("entity")) for r in recent}
    for r in base:
        ent = str(r.get("entity") or "")
        n = int(r.get("count") or 0)
        if not ent or ent == EMPTY or ent in still or n < min_count:
            continue
        res.findings.append(Finding(
            detector="source_silent", entity=ent, entity_field=host, severity="medium",
            metrics={"baseline": n, "silent_hours": SILENT_HOURS},
            external=None, query=f"{host}:{lucene_quote(ent)}"))


def blocked_only(det: Detector, row: dict) -> bool:
    """The WAF refused (almost) all of it: what got through is below the
    detection's own minimum. Unknown (no `blocked` count) = not blocked."""
    return "blocked" in row and int(row.get("passed") or 0) < det.min_count


async def _with_blocked(fetch, res, hits, fld, time_from, time_to, blocked_query):
    """`blocked` / `passed` per peer: one more aggregation of the same events
    that the WAF refused. A failure leaves the hits as they were (counted as
    let through, the pre-1.35 behaviour), never drops them."""
    if not hits:
        return hits
    top = sorted(hits, key=lambda r: -int(r.get("count") or 0))[:MAX_SUCCESS_CANDIDATES]
    ids = " OR ".join(lucene_quote(str(r["entity"])) for r in top)
    try:
        res.queries += 1
        rows = await fetch(f"{blocked_query} AND {fld}:({ids})", fld,
                           (("count", None),), time_from, time_to, len(top))
    except Exception as e:
        res.errors.append(f"waf_blocked/{fld}: {str(e)[:300]}")
        return hits
    got = {str(r["entity"]): int(r.get("count") or 0) for r in rows
           if r.get("entity") not in (None, "", EMPTY)}
    known = {str(r["entity"]) for r in top}
    out = []
    for r in hits:
        ent = str(r["entity"])
        if ent in known:
            n = min(got.get(ent, 0), int(r.get("count") or 0))
            r = {**r, "blocked": n, "passed": int(r.get("count") or 0) - n}
        out.append(r)
    return out


async def _with_success(fetch, res, hits, fld, time_from, time_to, ok_query):
    """Keep only the failing peers that also logged in successfully."""
    if not hits:
        return []
    hits = sorted(hits, key=lambda r: -int(r.get("count") or 0))[:MAX_SUCCESS_CANDIDATES]
    ids = " OR ".join(lucene_quote(str(r["entity"])) for r in hits)
    try:
        res.queries += 1
        ok_rows = await fetch(f"{ok_query} AND {fld}:({ids})", fld,
                              (("count", None),), time_from, time_to, len(hits))
    except Exception as e:
        res.errors.append(f"auth_success/{fld}: {str(e)[:300]}")
        return []
    ok = {str(r["entity"]): int(r.get("count") or 0) for r in ok_rows
          if r.get("entity") not in (None, "", EMPTY)}
    out = []
    for r in hits:
        n = ok.get(str(r["entity"]))
        if n:
            out.append({**r, "success": n})
    return out
