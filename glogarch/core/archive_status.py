# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Archive status: what jt-glogarch has archived, what is missing, and how the
archiving itself is doing. Read-only over jt-glogarch's own database (and the
free space of the archive disk); never asks Graylog.

Used by the AI tool `archive_status` (chat and /mcp). The owner asked
(2026-11-23) whether the AI could answer "how is archiving doing"; the old
tool only gave totals per server.

Archive times (`time_from`/`time_to`) are stored as UTC (measured on .36: the
03:00 Asia/Taipei export writes archives ending at 19:00Z, file names carry Z).
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from glogarch.core.retention_estimate import estimate_archive_retention
from glogarch.utils.logging import get_logger

log = get_logger("archive_status")

GAP_MIN_SECONDS = 3600      # a gap shorter than an hour is not reported
GAP_LIST_MAX = 20
NOTE_MAX = 300
JOB_TYPES = ("export", "verify", "cleanup")


def job_eta_seconds(d: dict) -> float | None:
    """Seconds of work left at the rate this job has averaged so far.

    A first full backlog can be billions of records. One site sat at
    "4% · 58h26m" with no way to tell whether that meant another day or
    another two months — it was 53 days. Elapsed time alone cannot answer the
    only question the operator has, so derive the remainder from the job's own
    measured rate. Deliberately naive (a flat average): the point is to tell
    hours from months, and a throttled export's rate already reflects its
    pauses. Returns None until there is enough signal to be worth showing.
    """
    if d.get("status") != "running" or d.get("completed_at"):
        return None
    if d.get("source") == "manual:ai-summary":
        # its last steps are the model writing and the PDF: their length has nothing to do
        # with how fast the charts went ("about 25 s left" sat there for minutes, 1.37)
        return None
    done = int(d.get("messages_done") or 0)
    total = int(d.get("messages_total") or 0)
    started = d.get("started_at")
    if not (done > 0 and total > done and started):
        return None
    try:
        st = datetime.fromisoformat(str(started).replace("Z", "+00:00"))
        if st.tzinfo is None:
            st = st.replace(tzinfo=timezone.utc)
        elapsed = (datetime.now(timezone.utc) - st).total_seconds()
    except Exception:
        return None
    # Under a minute of history, or a rate of zero, says nothing useful yet.
    if elapsed < 60:
        return None
    rate = done / elapsed
    if rate <= 0:
        return None
    return (total - done) / rate

def _ts(v) -> datetime | None:
    """A DB time (ISO, maybe with Z, naive = UTC) as an aware UTC datetime."""
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        d = v
    else:
        try:
            d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        except ValueError:
            return None
    return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d.astimezone(timezone.utc)


def _iso(d: datetime | None) -> str | None:
    return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if d else None


def coverage_gaps(spans, min_seconds: int = GAP_MIN_SECONDS) -> list[tuple[datetime, datetime]]:
    """Holes between archived spans, oldest first. `spans` = (from, to) pairs in
    any order; overlapping and touching spans merge. Only holes of at least
    `min_seconds` count. Before the first and after the last span is not a hole."""
    gaps = []
    end = None
    for a, b in sorted((a, b) for a, b in spans if a and b and b > a):
        if end is not None and (a - end).total_seconds() >= min_seconds:
            gaps.append((end, a))
        end = b if end is None or b > end else end
    return gaps


def _short(text) -> str | None:
    if not text:
        return None
    t = " ".join(str(text).split())
    return t if len(t) <= NOTE_MAX else t[:NOTE_MAX - 1] + "…"


def _server_of(config_json, schedules: dict, source: str) -> str | None:
    try:
        cfg = json.loads(config_json) if config_json else {}
    except ValueError:
        cfg = {}
    srv = cfg.get("server") or cfg.get("server_name")
    if not srv and source:
        sched = schedules.get(source.split(":")[-1])
        srv = sched.get("server") if sched else None
    return srv or None


def _job(r: dict, now: datetime) -> dict:
    started, done = _ts(r["started_at"]), _ts(r["completed_at"])
    out = {"id": r["id"], "type": r["job_type"], "status": r["status"], "source": r["source"] or None,
           "started": _iso(started), "finished": _iso(done),
           "records": r["messages_done"] or 0, "note": _short(r["error_message"])}
    if started:
        out["duration_min"] = round(((done or now) - started).total_seconds() / 60, 1)
    if r["status"] == "running":
        out["progress_pct"] = round(r["progress_pct"] or 0, 1)
        if r["messages_total"]:
            out["records_total"] = r["messages_total"]
        eta = job_eta_seconds({"status": "running", "messages_done": r["messages_done"],
                               "messages_total": r["messages_total"], "started_at": r["started_at"]})
        if eta is not None:
            out["eta_hours"] = round(eta / 3600, 1)
    return out


def archive_status(db, settings, now: datetime | None = None, gap_list_max: int = GAP_LIST_MAX) -> dict:
    """Everything the AI needs to answer "how is archiving doing". Reads only."""
    from glogarch.scheduler.scheduler import next_fire_time   # heavy module, loaded by the service anyway
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    c = db.conn

    servers = []
    for r in c.execute(
            """SELECT server_name, COUNT(*) AS archives, MIN(time_from) AS earliest, MAX(time_to) AS latest,
                      COALESCE(SUM(message_count), 0) AS records, COALESCE(SUM(file_size_bytes), 0) AS bytes,
                      COALESCE(SUM(original_size_bytes), 0) AS original_bytes
               FROM archives WHERE status = 'completed' GROUP BY server_name ORDER BY server_name"""):
        name = r["server_name"]
        spans = [(_ts(a), _ts(b)) for a, b in c.execute(
            "SELECT time_from, time_to FROM archives WHERE status = 'completed' AND server_name IS ?", (name,))]
        gaps = coverage_gaps(spans)
        latest = _ts(r["latest"])
        servers.append({
            "server": name, "archives": r["archives"], "earliest": _iso(_ts(r["earliest"])), "latest": _iso(latest),
            "hours_since_latest": round((now - latest).total_seconds() / 3600, 1) if latest else None,
            "records": r["records"], "bytes": r["bytes"], "original_bytes": r["original_bytes"],
            "gaps_total": len(gaps),
            "gap_hours_total": round(sum((b - a).total_seconds() for a, b in gaps) / 3600, 1),
            # newest first: the recent ones are the ones that still matter
            "gaps": [{"from": _iso(a), "to": _iso(b), "hours": round((b - a).total_seconds() / 3600, 1)}
                     for a, b in reversed(gaps[-gap_list_max:])],
        })

    problems = {r[0]: r[1] for r in c.execute(
        "SELECT status, COUNT(*) FROM archives WHERE status IN ('corrupted', 'missing', 'tampered', 'failed') GROUP BY status")}
    deleted = c.execute("SELECT COUNT(*) FROM archives WHERE status = 'deleted'").fetchone()[0]

    schedules, by_name = [], {}
    for s in db.list_schedules():
        try:
            cfg = json.loads(s.config_json) if s.config_json else {}
        except ValueError:
            cfg = {}
        nxt = next_fire_time(s.cron_expr) if s.enabled and s.cron_expr else None
        d = {"name": s.name, "type": s.job_type, "enabled": bool(s.enabled), "cron": s.cron_expr,
             "last_run": _iso(_ts(s.last_run_at)), "next_run": _iso(_ts(nxt)) if nxt else None}
        for k in ("mode", "server", "retention_days", "days"):
            if cfg.get(k) not in (None, ""):
                d[k] = cfg[k]
        schedules.append(d)
        by_name[s.name] = d

    jobs = {}
    since = _iso(now - timedelta(days=7))
    # report cleanup is also job_type cleanup; it runs daily and would push the archive
    # cleanup (monthly) out of the list
    for jt in JOB_TYPES:
        rows = [dict(r) for r in c.execute(
            """SELECT id, job_type, status, source, started_at, completed_at, messages_done, messages_total,
                      progress_pct, error_message, config_json FROM jobs
               WHERE job_type = ? AND COALESCE(source, '') NOT LIKE '%report-cleanup%'
               ORDER BY COALESCE(started_at, created_at) DESC LIMIT 5""", (jt,))]
        last = [_job(r, now) for r in rows]
        for r, j in zip(rows, last):
            srv = _server_of(r["config_json"], by_name, r["source"] or "")
            if srv:
                j["server"] = srv
        counts = {r[0]: r[1] for r in c.execute(
            "SELECT status, COUNT(*) FROM jobs WHERE job_type = ? AND COALESCE(started_at, created_at) >= ? "
            "AND COALESCE(source, '') NOT LIKE '%report-cleanup%' GROUP BY status", (jt, since))}
        jobs[jt] = {"recent": last, "last_7_days": counts}
    running = [_job(dict(r), now) for r in c.execute(
        """SELECT id, job_type, status, source, started_at, completed_at, messages_done, messages_total,
                  progress_pct, error_message FROM jobs WHERE status = 'running' ORDER BY started_at""")]

    disk = None
    base = Path(getattr(getattr(settings, "export", None), "base_path", "") or "")
    if str(base) and base.exists():
        try:
            u = shutil.disk_usage(base)
            tot = c.execute("""SELECT COALESCE(SUM(file_size_bytes), 0), MIN(time_from), MAX(time_to)
                               FROM archives WHERE status = 'completed'""").fetchone()
            est = estimate_archive_retention(total_compressed_bytes=tot[0], earliest=tot[1], latest=tot[2],
                                             available_bytes=u.free)
            disk = {"path": str(base), "free_bytes": u.free, "total_bytes": u.total,
                    "months_left_at_current_rate": round(est["remaining_months"], 1) if est.get("available") else None,
                    "alert_below_months": getattr(getattr(settings, "retention", None), "disk_alert_months", None)}
        except OSError as e:
            log.warning("Archive disk could not be read for the archive status", error=str(e))

    return {
        "now": _iso(now),
        "servers": servers,
        "archive_problems": problems,
        "archives_deleted_by_retention": deleted,
        "running_jobs": running,
        "jobs": jobs,
        "schedules": schedules,
        "disk": disk,
        "notes": [
            "All times are UTC.",
            "A gap is time between the earliest and latest archive that no completed archive covers. "
            "It can mean the export did not run or failed for that time, that Graylog had no logs then, "
            "or that an archive there was deleted; check jobs and schedules before calling it data loss. "
            "A scheduled API export re-exports gaps of the last export.gap_refill_hours (default 168) "
            "on its next run; its note then says \"Refilled N gap(s)\".",
            "A completed export's note often carries its summary (chunks, records, size, overflow windows).",
            "archive_problems counts archives found corrupted, missing or tampered by a verify, or left failed by an export.",
        ],
    }
