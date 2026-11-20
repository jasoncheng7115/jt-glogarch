# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Weekly security summary (added 1.32): what the last 7 days looked like, sent
through the notification channels. Everything comes from jt-glogarch's own DB:
building it asks nothing of Graylog.

Its first line answers "is the analysis even running?": a summary with no
incidents from an analysis that did not run is the most misleading message
this feature could send, so a week with no successful run says so in the title.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from glogarch.core.config import Settings
from glogarch.core.database import ArchiveDB
from glogarch.security.attack import coverage_matrix
from glogarch.security.coverage import detector_rows, recent_coverage
from glogarch.security.risk import score_entities
from glogarch.security.runner import parse_db_ts
from glogarch.security.threat_intel import matcher_for

DAYS = 7
TOP = 5
VERDICTS = ("malicious", "suspicious", "benign", "unclear")


def build_digest(settings: Settings, db: ArchiveDB, now: datetime | None = None) -> dict:
    now = now or datetime.utcnow()
    since = now - timedelta(days=DAYS)
    week = db.security_incidents_since(since, limit=20000)       # seen in the week (last_seen)
    new = [i for i in week if (parse_db_ts(i.get("first_seen")) or datetime.min) >= since]
    by_sev = {s: sum(1 for i in new if i.get("severity") == s) for s in ("high", "medium", "low")}
    dets: dict[str, dict] = {}
    for i in new:
        d = dets.setdefault(i["detector"], {"detector": i["detector"], "count": 0, "title": None})
        d["count"] += 1
        if i["detector"].startswith("sigma:"):
            d["title"] = "Sigma: " + str((i.get("metrics") or {}).get("sigma_title") or i["detector"])
    verdicts = db.latest_security_verdicts([i["id"] for i in week])
    v_count = {v: 0 for v in VERDICTS}
    for v in verdicts.values():
        if v.get("verdict") in v_count and (parse_db_ts(v.get("created_at")) or datetime.min) >= since:
            v_count[v["verdict"]] += 1
    risk = score_entities(week, db.list_security_assets(), verdicts, limit=TOP, ti=matcher_for(settings, db))
    runs = [r for r in db.list_security_runs(limit=5000)
            if (parse_db_ts(r.get("started_at")) or datetime.min) >= since]
    run_status = {s: sum(1 for r in runs if r.get("status") == s) for s in ("ok", "partial", "error", "skipped")}
    open_counts = db.open_security_counts()
    cases = db.list_security_cases()
    sups = db.list_suppressions()
    now_s = now.isoformat()
    active = [s for s in sups if not s.get("expires_at") or (parse_db_ts(s["expires_at"]) or now) > now]
    hit = [s for s in sups if (parse_db_ts(s.get("last_hit_at")) or datetime.min) >= since]
    cov, ran, _ = recent_coverage(db, 24 * DAYS)
    techs = [te for ta in coverage_matrix(detector_rows(settings.security), cov, ran) for te in ta["techniques"]]
    return {
        "since": since.isoformat(), "until": now_s, "days": DAYS,
        "enabled": settings.security.enabled,
        "new": by_sev, "new_total": sum(by_sev.values()),
        "top_detectors": sorted(dets.values(), key=lambda x: (-x["count"], x["detector"]))[:TOP],
        "risk_top": [{"entity": r["entity"], "score": r["score"]} for r in risk],
        "open": {s: int(open_counts.get(s, 0)) for s in ("high", "medium", "low")},
        "cases": {"open": sum(1 for c in cases if c["status"] == "open"),
                  "in_progress": sum(1 for c in cases if c["status"] == "in_progress"),
                  "closed_in_week": sum(1 for c in cases if c["status"] == "closed"
                                        and (parse_db_ts(c.get("closed_at")) or datetime.min) >= since)},
        "verdicts": v_count,
        "suppressions": {"active": len(active), "hit_in_week": len(hit)},
        "runs": run_status, "runs_total": len(runs),
        "attack": {"watched": len({t["id"] for t in techs if t["state"] == "active"}),
                   "total": len({t["id"] for t in techs})},
    }


def healthy(d: dict) -> bool:
    """At least one successful run, and fewer failed/skipped runs than good ones."""
    r = d["runs"]
    good = r["ok"] + r["partial"]
    return good > 0 and (r["error"] + r["skipped"]) < good


def server_name(settings: Settings) -> str:
    try:
        return settings.get_server(settings.security.server or None).name
    except ValueError:
        return settings.security.server or "-"


async def send_digest(settings: Settings, db: ArchiveDB) -> dict:
    """Build and send the summary; returns what was sent."""
    from glogarch.notify.sender import notify_security_digest
    d = build_digest(settings, db)
    await notify_security_digest(d, server_name(settings))
    return d
