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
from datetime import datetime
from typing import Awaitable, Callable

from glogarch.security.detectors import (
    AUTH_OK, DETECTORS, PROBES, Detector, Probe,
)

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
                        global_exclude: str = "") -> RunResult:
    """`settings` maps detector id -> {"enabled": bool, "min_count": int,
    "exclude": str}; missing keys fall back to the detector's defaults."""
    settings = settings or {}
    res = RunResult()
    active: list[tuple[Detector, int, str]] = []
    for det in DETECTORS:
        s = settings.get(det.id) or {}
        if not s.get("enabled", det.default_enabled):
            continue
        min_count = int(s.get("min_count") or det.min_count)
        exclude = s["exclude"] if "exclude" in s else det.exclude
        active.append((det, min_count, exclude))

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
            rows = await fetch(q, fld, probe.metrics, time_from, time_to, probe.limit)
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
        probe = PROBES[det.probe]
        eff = replace(det, min_count=min_count)
        for fld in probe.fields:
            rows = await rows_for(probe, fld, exclude)
            if not rows:
                continue
            hits = [r for r in rows if r.get("entity") not in (None, "", EMPTY) and qualifies(eff, r)]
            if det.id == "auth_success_after_fail":
                hits = await _with_success(fetch, res, hits, fld, time_from, time_to,
                                           build_query(AUTH_OK, global_exclude))
            for r in hits:
                ent = str(r["entity"])
                ext = is_external(ent)
                sev = severity_for(eff, r, ext)
                if sev is None:
                    continue
                res.findings.append(Finding(
                    detector=det.id, entity=ent, entity_field=fld, severity=sev,
                    metrics={k: v for k, v in r.items() if k != "entity"},
                    external=ext,
                    query=build_query(f"{probe.query} AND {fld}:{lucene_quote(ent)}",
                                      exclude, global_exclude),
                ))
    return res


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
