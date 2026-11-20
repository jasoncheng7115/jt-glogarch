# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""One security-analysis run: health check -> detectors -> incidents -> notify.

Called by the scheduler's internal job `internal-security-analysis` (only while
`security.enabled`) and by "Run now" in the UI.
"""
from __future__ import annotations

import threading
from dataclasses import asdict
from datetime import datetime, timedelta, timezone

from glogarch.core.config import Settings
from glogarch.core.database import ArchiveDB
from glogarch.graylog.client import GraylogClient
from glogarch.graylog.system import SystemMonitor
from glogarch.ratelimit.limiter import RateLimiter
from glogarch.security.detectors import (
    ANOMALY_FACTOR, ANOMALY_HISTORY_DAYS, ANOMALY_LEARN_DAYS, ANOMALY_MEDIUM_FACTOR, ANOMALY_MIN_DAYS,
    ANOMALY_Z, AUTH_OK, NEW_SOURCE_LEARN_DAYS, NEW_SOURCE_MEMORY_DAYS, sev_rank,
)
from glogarch.security.engine import run_detectors
from glogarch.security.graylog_fetch import make_fetch, make_pair_fetch
from glogarch.security.suppress import apply_suppressions
from glogarch.utils.logging import get_logger

log = get_logger("security")

# One run at a time, scheduled or Run now: two overlapping runs could both see a new
# incident as un-notified and notify (and analyse) it twice (review 2026-11-20).
RUN_LOCK = threading.Lock()

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
                                source: str = "scheduled", ai_inline: bool = True) -> dict:
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
            rules = db.list_sigma_rules(enabled_only=True)[:max(0, int(cfg.sigma_max_rules))]
            res = await run_detectors(
                make_fetch(client),
                t_from.replace(tzinfo=timezone.utc), now.replace(tzinfo=timezone.utc),
                settings=cfg.detectors, global_exclude=cfg.exclude_query, sigma_rules=rules,
                fetch_pairs=make_pair_fetch(client))
    except Exception as e:
        db.finish_security_run(run_id, status="error", errors=[str(e)])
        log.warning("Security analysis failed", server=server.name, error=str(e))
        await _maybe_alert_failing(db, server.name, str(e))
        return {**summary, "error": str(e)}

    for rid, out in res.sigma.items():
        try:
            db.record_sigma_result(rid, out["count"], out["error"])
        except Exception as e:
            log.warning("Sigma rule result not recorded", rule=rid, error=str(e))
    first = parse_db_ts(db.first_security_run_at())
    learning = first is not None and first > now - timedelta(hours=LEARNING_HOURS)
    findings = [asdict(f) for f in res.findings]
    if res.pairs:
        findings += new_source_findings(db, server.name, res.pairs, now, cfg.exclude_query)
        db.record_pairs(server.name, [(a, b) for a, b, _ in res.pairs], now)
    if res.volume_settings is not None:
        findings += volume_findings(db, server.name, res.volumes, now, int(cfg.window_minutes),
                                    min_count=res.volume_settings["min_count"],
                                    exclude=res.volume_settings["exclude"], global_exclude=cfg.exclude_query)
        rate = 60.0 / max(1, int(cfg.window_minutes))
        db.record_volumes(server.name, [(f, k, n * rate) for f, k, n in res.volumes], now.replace(minute=0, second=0))
    suppressed = 0
    try:
        findings, hits = apply_suppressions(findings, server.name, db.list_suppressions(), now)
        db.record_suppression_hits(hits, now)
        suppressed = sum(hits.values())
    except Exception as e:   # a broken suppression list must not stop the analysis
        log.warning("Suppressions not applied", error=str(e))
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
             queries=res.queries, findings=len(findings), suppressed=suppressed, notified=len(to_notify))
    extra = {}
    if ai_inline:
        extra["ai_analysed"] = await _auto_ai_analysis(settings, db, changes)
    else:
        extra["_changes"] = changes          # the caller runs the AI after answering
    return {**summary, "status": status, "queries": res.queries, "findings": len(findings),
            "notified": len(to_notify), "suppressed": suppressed, "errors": res.errors, **extra}


def new_source_findings(db: ArchiveDB, server: str, pairs: list[tuple[str, str, int]], now: datetime,
                        global_exclude: str = "") -> list[dict]:
    """One finding per account that logged in from a source it has not used for
    NEW_SOURCE_MEMORY_DAYS, once its history is at least NEW_SOURCE_LEARN_DAYS old.
    Called BEFORE the pairs of this run are recorded."""
    from glogarch.security.engine import build_query, is_external, lucene_quote
    accounts = sorted({a for a, _, _ in pairs})
    known, first = db.pair_history(server, accounts)
    memory = now - timedelta(days=NEW_SOURCE_MEMORY_DAYS)
    learned = now - timedelta(days=NEW_SOURCE_LEARN_DAYS)
    by_acct: dict[str, list[tuple[str, int]]] = {}
    for a, b, n in pairs:
        f = parse_db_ts(first.get(a))
        if f is None or f > learned:
            continue                      # still learning this account
        last = parse_db_ts(known.get((a, b)))
        if last is not None and last >= memory:
            continue                      # a source it uses
        by_acct.setdefault(a, []).append((b, n))
    out = []
    for a, srcs in by_acct.items():
        srcs.sort(key=lambda x: -x[1])
        ext = any(is_external(b) for b, _ in srcs)
        ors = " OR ".join(lucene_quote(b) for b, _ in srcs[:20])
        out.append({"detector": "account_new_source", "entity": a, "entity_field": "user_name",
                    "severity": "medium" if ext else "low",
                    "metrics": {"count": sum(n for _, n in srcs), "new_sources": [b for b, _ in srcs[:5]]},
                    "external": True if ext else (False if all(is_external(b) is False for b, _ in srcs) else None),
                    "query": build_query(f"{AUTH_OK} AND user_name:{lucene_quote(a)} AND source_ip:({ors})", global_exclude)})
    return out


def _median(vals: list[float]) -> float:
    v = sorted(vals)
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2


def usual_rate(samples: dict[str, float], observed: set[str], now: datetime) -> tuple[float, float, int] | None:
    """(median, robust sigma, days) of the rate at this time of day: for each of the
    last ANOMALY_HISTORY_DAYS days, the mean of the hours now-24h*k -1h..+1h. An hour
    in which the analysis ran (`observed`) but this key had no row counts as 0; a day
    on which the analysis did not run at that time is left out. None when fewer than
    ANOMALY_MIN_DAYS days remain."""
    from glogarch.core.database import _dt_to_str
    base = now.replace(minute=0, second=0, microsecond=0)
    days = []
    for k in range(1, ANOMALY_HISTORY_DAYS + 1):
        hours = [_dt_to_str(base - timedelta(days=k) + timedelta(hours=d)) for d in (-1, 0, 1)]
        seen = [h for h in hours if h in observed]
        if not seen:
            continue
        days.append(sum(samples.get(h, 0.0) for h in seen) / len(seen))
    if len(days) < ANOMALY_MIN_DAYS:
        return None
    med = _median(days)
    mad = _median([abs(x - med) for x in days]) * 1.4826
    return med, max(mad, 0.1 * med, 1.0), len(days)


def volume_findings(db: ArchiveDB, server: str, volumes: list[tuple[str, str, int]], now: datetime,
                    window_minutes: int, *, min_count: int, exclude: str = "", global_exclude: str = "") -> list[dict]:
    """A host or event category sending far more than usual at this time of day
    (see detectors.ANOMALY_*). Called BEFORE this run's volumes are recorded."""
    from glogarch.security.engine import build_query, is_external, lucene_quote
    per_hour = 60.0 / max(1, window_minutes)
    since = now - timedelta(days=ANOMALY_HISTORY_DAYS + 1)
    learned = now - timedelta(days=ANOMALY_LEARN_DAYS)
    out = []
    for fld in sorted({f for f, _, _ in volumes}):
        rows = [(k, n) for f, k, n in volumes if f == fld and n * per_hour >= min_count]
        if not rows:
            continue
        samples, observed, first = db.volume_history(server, fld, [k for k, _ in rows], since)
        for key, n in rows:
            f = parse_db_ts(first.get(key))
            if f is None or f > learned:
                continue                       # history too young: still learning
            usual = usual_rate(samples.get(key, {}), observed, now)
            if usual is None:
                continue
            med, sigma, days = usual
            rate = n * per_hour
            if rate < ANOMALY_FACTOR * max(med, 1.0) or (rate - med) / sigma < ANOMALY_Z:
                continue
            ratio = rate / max(med, 1.0)
            out.append({"detector": "volume_anomaly", "entity": key, "entity_field": fld,
                        "severity": "medium" if ratio >= ANOMALY_MEDIUM_FACTOR else "low",
                        "metrics": {"count": n, "rate": round(rate), "usual": round(med),
                                    "ratio": round(ratio, 1), "days": days},
                        "external": is_external(key) if fld == "source" else None,
                        "query": build_query(f"{fld}:{lucene_quote(key)}", exclude, global_exclude)})
    return out


async def _auto_ai_analysis(settings: Settings, db: ArchiveDB, changes: list[dict]) -> int:
    """After the run is recorded and notified: the model looks at the new or
    escalated incidents (security.ai_auto). Its time never delays a
    notification, and its failure never fails the run."""
    cfg, ai = settings.security, settings.ai
    if not (cfg.ai_auto and ai.analysis_enabled and ai.url):
        return 0
    from glogarch.security.ai_analysis import analyze_incident, auto_candidates
    done = 0
    notify = []
    for inc_id in auto_candidates(changes, cfg.ai_auto_min_severity, cfg.ai_auto_max_per_run):
        try:
            row = await analyze_incident(settings, db, inc_id, lang=settings.notify.language,
                                         trigger="auto", username="scheduler")
        except Exception as e:
            log.warning("Automatic incident AI analysis failed", incident=inc_id, error=str(e))
            continue
        db.audit("security_ai_analysis", f"incident={inc_id} trigger=auto verdict={row.get('verdict')} "
                                         f"error={(row.get('error') or '')[:120]}", "scheduler", "")
        if row.get("error"):
            break   # the LLM is down or the budget is used up: do not try the rest now
        done += 1
        if row.get("verdict") in (cfg.ai_notify_verdicts or []):
            notify.append({"incident": db.get_security_incident(inc_id) or {"id": inc_id, "detector": "", "entity": ""},
                           "row": row})
    if notify:
        try:
            from glogarch.notify.sender import notify_security_ai
            server = settings.get_server(cfg.server or None).name
            await notify_security_ai(notify, server)
        except Exception as e:  # the analyses are stored either way
            log.warning("AI verdict notification failed", error=str(e))
    return done


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
