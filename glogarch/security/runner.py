# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""One security-analysis run: health check -> detectors -> incidents -> notify.

Called by the scheduler's internal job `internal-security-analysis` (only while
`security.enabled`) and by "Run now" in the UI.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone

from glogarch.core.config import Settings
from glogarch.core.database import ArchiveDB
from glogarch.graylog.client import GraylogClient
from glogarch.graylog.system import SystemMonitor
from glogarch.ratelimit.limiter import RateLimiter
from glogarch.security.detectors import sev_rank
from glogarch.security.engine import run_detectors
from glogarch.security.graylog_fetch import make_fetch
from glogarch.utils.logging import get_logger

log = get_logger("security")

LEARNING_HOURS = 24        # no NEW badge during the first day of runs
FAILING_RUNS_ALERT = 3     # consecutive failed runs before "analysis is not running"


def parse_db_ts(value: str | None) -> datetime | None:
    """sec_* timestamps are stored by `_dt_to_str` as naive UTC with a trailing
    `Z`, which `datetime.fromisoformat` rejects before Python 3.11."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value[:-1] if value.endswith("Z") else value)
    except ValueError:
        return None


def _under_pressure(health: dict | None, hard_pct: float) -> str | None:
    """Same fail-safe as the export guard: unreadable health = pressure."""
    if health is None:
        return "Graylog health could not be read"
    after = health.get("heap_after_gc_pct")
    heap = after if after is not None else health.get("jvm_pct")
    if heap is not None and heap >= hard_pct:
        return f"Graylog heap at {heap:.0f}%"
    return None


def notify_decision(change: dict, min_sev: str, now: datetime, renotify_hours: float) -> bool:
    """Should this incident appear in this run's notification?

    new / escalated at or above `min_sev`: yes. Ongoing: only when it was
    never notified (it rose past `min_sev` earlier without one) or was last
    notified more than `renotify_hours` ago — held otherwise, never dropped
    from the incident list."""
    if min_sev == "off" or sev_rank(change["severity"]) < sev_rank(min_sev):
        return False
    if change["change"] in ("new", "escalated"):
        return True
    last_dt = parse_db_ts(change.get("notified_at"))
    if last_dt is None:
        return True
    return (now - last_dt) >= timedelta(hours=renotify_hours)


async def run_security_analysis(settings: Settings, db: ArchiveDB, *,
                                source: str = "scheduled") -> dict:
    cfg = settings.security
    try:
        server = settings.get_server(cfg.server or None)
    except ValueError as e:
        return {"status": "error", "error": str(e)}
    now = datetime.utcnow().replace(microsecond=0)
    t_from = now - timedelta(minutes=int(cfg.window_minutes))
    run_id = db.start_security_run(server.name, t_from, now)
    summary: dict = {"run_id": run_id, "server": server.name, "status": "error"}
    try:
        async with GraylogClient(server, RateLimiter(settings.rate_limit)) as client:
            health = await SystemMonitor(client).get_health()
            if health is None:
                # Unreachable counts as a FAILED run, not a skipped one, so the
                # failing-streak alert fires: a dead connection must not look
                # like a quiet network.
                raise RuntimeError("Graylog health could not be read")
            reason = _under_pressure(health, settings.export.jvm_memory_hard_pct)
            if reason:
                db.finish_security_run(run_id, status="skipped", note=reason)
                log.warning("Security analysis skipped", server=server.name, reason=reason)
                return {**summary, "status": "skipped", "note": reason}
            res = await run_detectors(
                make_fetch(client),
                t_from.replace(tzinfo=timezone.utc), now.replace(tzinfo=timezone.utc),
                settings=cfg.detectors, global_exclude=cfg.exclude_query)
    except Exception as e:
        db.finish_security_run(run_id, status="error", errors=[str(e)])
        log.warning("Security analysis failed", server=server.name, error=str(e))
        await _maybe_alert_failing(db, server.name, str(e))
        return {**summary, "error": str(e)}

    first = parse_db_ts(db.first_security_run_at())
    learning = first is not None and first > now - timedelta(hours=LEARNING_HOURS)
    findings = [asdict(f) for f in res.findings]
    changes = db.apply_security_findings(
        server.name, findings, now, reopen_hours=cfg.reopen_hours,
        new_days=cfg.new_days, learning=learning)

    to_notify, sev_by_id = [], {}
    for f, ch in zip(findings, changes):
        if notify_decision(ch, cfg.notify_min_severity, now, cfg.renotify_hours):
            inc = db.get_security_incident(ch["id"]) or {}
            to_notify.append({**f, "change": ch["change"], "severity": ch["severity"],
                              "is_new": bool(inc.get("is_new")) and ch["change"] == "new"})
            sev_by_id[ch["id"]] = ch["severity"]
    if to_notify:
        try:
            from glogarch.notify.sender import notify_security_incidents
            await notify_security_incidents(to_notify, server.name, int(cfg.window_minutes))
            db.mark_security_notified(list(sev_by_id), sev_by_id, now)
        except Exception as e:  # the incidents are recorded either way
            log.warning("Security notification failed", error=str(e))

    probes_failed = sum(1 for c in res.coverage if c.error)
    status = "ok" if not probes_failed else ("error" if probes_failed == len(res.coverage) else "partial")
    db.finish_security_run(
        run_id, status=status, queries=res.queries, findings=len(findings),
        opened=sum(1 for c in changes if c["change"] == "new"),
        coverage=[asdict(c) for c in res.coverage], errors=res.errors,
        note="Learning period: no NEW badges during the first 24 hours" if learning else None)
    if status == "error":
        await _maybe_alert_failing(db, server.name, "; ".join(res.errors))
    try:
        db.prune_security(int(cfg.retention_days))
    except Exception as e:
        log.warning("Security retention prune failed", error=str(e))
    log.info("Security analysis finished", server=server.name, source=source, status=status,
             queries=res.queries, findings=len(findings), notified=len(to_notify))
    return {**summary, "status": status, "queries": res.queries, "findings": len(findings),
            "notified": len(to_notify), "errors": res.errors}


async def _maybe_alert_failing(db: ArchiveDB, server: str, error: str) -> None:
    """Exactly once per failing streak: when the streak first reaches
    FAILING_RUNS_ALERT. A silent analysis looks like a quiet network."""
    runs = db.list_security_runs(server, limit=FAILING_RUNS_ALERT + 1)
    statuses = [r["status"] for r in runs]
    streak = 0
    for s in statuses:
        if s != "error":
            break
        streak += 1
    if streak == FAILING_RUNS_ALERT:
        try:
            from glogarch.notify.sender import notify_security_failing
            await notify_security_failing(server, streak, error)
        except Exception as e:
            log.warning("Security failing notification failed", error=str(e))
