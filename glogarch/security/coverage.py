# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Which detections run and what they saw: shared by the Security page, the
ATT&CK view and the weekly digest (moved out of web/routes/security.py in 1.32)."""
from __future__ import annotations

from datetime import datetime, timedelta

from glogarch.core.config import SecurityConfig
from glogarch.security.detectors import DETECTORS, PROBES
from glogarch.security.runner import parse_db_ts


def detector_rows(cfg: SecurityConfig) -> list[dict]:
    out = []
    for d in DETECTORS:
        s = cfg.detectors.get(d.id) or {}
        p = PROBES[d.probe]
        out.append({
            "id": d.id,
            "enabled": bool(s.get("enabled", d.default_enabled)),
            "min_count": int(s.get("min_count") or d.min_count),
            "default_min_count": d.min_count,
            "exclude": s["exclude"] if "exclude" in s else d.exclude,
            "default_exclude": d.exclude,
            "probe": d.probe,
            "query": p.query,
            "fields": list(p.fields),
        })
    return out


def recent_coverage(db, hours: int = 24) -> tuple[list[dict], bool, str | None]:
    """Coverage merged over the finished runs of the last `hours`: a probe field
    counts its events across them, and is an error only if it failed in all.
    One quiet hour (no WAF traffic at 3 am) must not read as "no data"."""
    since = datetime.utcnow() - timedelta(hours=hours)
    runs = [r for r in db.list_security_runs(limit=500) if r["status"] in ("ok", "partial")
            and (parse_db_ts(r.get("started_at")) or datetime.min) >= since]
    merged: dict[tuple, dict] = {}
    for r in runs:
        for c in r.get("coverage") or []:
            m = merged.setdefault((c.get("probe"), c.get("field")),
                                  {"probe": c.get("probe"), "field": c.get("field"), "events": 0, "missing": 0,
                                   "error": "", "ok_runs": 0, "err_runs": 0})
            if c.get("error"):
                m["err_runs"] += 1
                m["error"] = c["error"]
            else:
                m["ok_runs"] += 1
                m["events"] += int(c.get("events") or 0)
                m["missing"] += int(c.get("missing") or 0)
    out = []
    for m in merged.values():
        if m["ok_runs"]:
            m["error"] = ""
        out.append({k: m[k] for k in ("probe", "field", "events", "missing", "error")})
    return out, bool(runs), (runs[0].get("finished_at") if runs else None)
