"""APScheduler-based scheduler for periodic export and cleanup."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from glogarch.cleanup.cleaner import Cleaner
from glogarch.core.config import Settings, get_settings
from glogarch.core.database import ArchiveDB
from glogarch.core.models import JobRecord, JobStatus, JobType, ScheduleRecord
from glogarch.export.exporter import Exporter
from glogarch.utils.logging import get_logger

log = get_logger("scheduler")


# POSIX cron dow numbering: 0/7 = Sun, 1 = Mon, ..., 6 = Sat
# APScheduler dow numbering: 0 = Mon, 1 = Tue, ..., 6 = Sun
# All cron expressions in this project (UI presets, customer-written, DB-stored)
# follow POSIX. We convert before handing to APScheduler so the day actually
# matches the user's intent.
_POSIX_TO_APS_DOW = {0: 6, 1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6}


def _convert_dow_token(tok: str) -> str:
    tok = tok.strip()
    if not tok or tok == "*":
        return tok
    # Step expressions (e.g. */2) — semantics depend on base, but POSIX and
    # APScheduler both step from 0 over a 7-day cycle; emit untouched.
    if "/" in tok:
        return tok
    # Named days (mon, tue, ..., sun) are interpreted identically by APS — keep.
    if any(c.isalpha() for c in tok):
        return tok
    # Numeric range like "1-5"
    if "-" in tok:
        a_s, b_s = tok.split("-", 1)
        a, b = _POSIX_TO_APS_DOW[int(a_s)], _POSIX_TO_APS_DOW[int(b_s)]
        if a == b:
            return str(a)
        if a < b:
            return f"{a}-{b}"
        # Wrapped after conversion (e.g. POSIX 5-1 Fri-Mon → APS 4-0): split at week edge
        high = f"{a}-6" if a < 6 else "6"
        low = "0" if b == 0 else f"0-{b}"
        return f"{high},{low}"
    # Plain number
    return str(_POSIX_TO_APS_DOW[int(tok)])


def posix_cron_to_apscheduler(cron_expr: str) -> str:
    """Translate a 5-field cron expression so that the day-of-week field is
    interpreted with POSIX semantics (0/7=Sun, 6=Sat) when handed to
    APScheduler's `CronTrigger.from_crontab` (which numbers 0=Mon, 6=Sun).

    Returns the original expression if it does not have exactly 5 fields,
    so non-standard inputs are passed through unchanged."""
    parts = cron_expr.strip().split()
    if len(parts) != 5:
        return cron_expr
    minute, hour, dom, month, dow = parts
    new_dow = ",".join(_convert_dow_token(t) for t in dow.split(","))
    return f"{minute} {hour} {dom} {month} {new_dow}"


class ArchiveScheduler:
    """Manages periodic export and cleanup jobs."""

    def __init__(self, settings: Settings | None = None, db: ArchiveDB | None = None):
        self.settings = settings or get_settings()
        self.scheduler = AsyncIOScheduler()
        # Share the caller's DB instance when provided — avoids creating a
        # second sqlite3 connection on the same file, which causes SQLite
        # "database is locked" errors under concurrent writes (separate
        # connections contend at the file lock level, our threading.Lock
        # only serializes within one connection).
        if db is not None:
            self.db = db
        else:
            self.db = ArchiveDB(self.settings.database_path)
            self.db.connect()
        self._running_jobs: dict[str, bool] = {}

    def _run_export_in_thread(self, schedule_name: str = "auto-export") -> None:
        """Sync wrapper that runs the async export in its own asyncio loop in a
        worker thread, so the main FastAPI event loop is not blocked by CPU-bound
        work (gzip, JSON parsing, GELF formatting)."""
        import threading
        threading.Thread(
            target=lambda: asyncio.run(self._run_export(schedule_name)),
            daemon=True,
            name=f"scheduled-export-{schedule_name}",
        ).start()

    _EXPORT_MAX_RETRIES = 3
    _EXPORT_RETRY_DELAY = 60  # seconds

    async def _run_export(self, schedule_name: str = "auto-export") -> None:
        """Scheduled export job — reads config from DB (supports Web UI edits).

        Retries up to 3 times on transient errors (e.g. database locked).
        If the previous export is still running (lock held), skips silently
        without retry/alert — this is expected when an export takes longer
        than the cron interval.
        Records a failed job on final failure so it appears in Job History.
        """
        if self._running_jobs.get("export"):
            log.info("Previous scheduled export still running, skipping this run")
            return

        self._running_jobs["export"] = True
        last_error = None
        skipped_due_to_running = False
        try:
            for attempt in range(1, self._EXPORT_MAX_RETRIES + 1):
                try:
                    await self._run_export_once(schedule_name)
                    last_error = None
                    break
                except Exception as e:
                    err_str = str(e)
                    # "Export already running" means another export holds the
                    # module-level lock. Don't treat as retryable — skip the run.
                    if "already running" in err_str.lower():
                        log.info("Previous export still holds lock, skipping this scheduled run",
                                 error=err_str)
                        skipped_due_to_running = True
                        last_error = None
                        break
                    last_error = e
                    if attempt < self._EXPORT_MAX_RETRIES:
                        log.warning("Scheduled export failed, retrying",
                                    attempt=attempt, max=self._EXPORT_MAX_RETRIES,
                                    error=err_str, retry_in=self._EXPORT_RETRY_DELAY)
                        await asyncio.sleep(self._EXPORT_RETRY_DELAY)
                    else:
                        log.error("Scheduled export failed after all retries",
                                  attempts=self._EXPORT_MAX_RETRIES, error=err_str)

            if last_error is not None:
                # Record failed job so it appears in Job History
                from glogarch.utils.sanitize import sanitize
                job_id = self._create_run_job(JobType.EXPORT, "scheduled")
                self._finish_run_job(job_id, JobStatus.FAILED,
                                     error_message=sanitize(str(last_error)))
        finally:
            self._running_jobs["export"] = False
            if not skipped_due_to_running:
                self._update_schedule_last_run(schedule_name)

    async def _run_export_once(self, schedule_name: str = "auto-export") -> None:
        """Single export attempt."""
        import json as _json
        from datetime import timedelta
        from glogarch.export.exporter import _ensure_naive

        # Read config from DB (may have been edited via Web UI)
        sched_list = self.db.list_schedules()
        sched_rec = next((s for s in sched_list if s.name == schedule_name), None)
        cfg = {}
        if sched_rec and sched_rec.config_json:
            try:
                cfg = _json.loads(sched_rec.config_json)
            except Exception:
                pass

        export_mode = cfg.get("mode", self.settings.export_mode)
        export_days = cfg.get("days", self.settings.schedule.export_days)
        index_set_ids = [cfg["index_set"]] if cfg.get("index_set") else None
        stream_ids = cfg.get("streams") or None
        keep_indices = cfg.get("keep_indices") or None

        server_config = self.settings.get_server(cfg.get("server"))
        time_to = datetime.utcnow()
        time_from = time_to - timedelta(days=export_days)

        log.info("Scheduled export config",
                 mode=export_mode, days=export_days,
                 streams=stream_ids, index_set=index_set_ids,
                 server=server_config.name,
                 initial_from=str(time_from), to=str(time_to))

        os_config = self.settings.get_opensearch(cfg.get("server"))
        if export_mode == "opensearch" and os_config.hosts:
            from glogarch.opensearch.exporter import OpenSearchExporter
            exporter = OpenSearchExporter(
                server_config, os_config, self.settings.export,
                self.settings.rate_limit, self.db, integrity=self.settings.integrity,
            )
            # OpenSearch: no resume point — rely on per-chunk dedup to avoid gaps
            log.info("OpenSearch mode: using full range with per-chunk dedup")
            log.info("Scheduled export starting (OpenSearch)", time_from=str(time_from), time_to=str(time_to), keep_indices=keep_indices)
            result = await exporter.export(time_from=time_from, time_to=time_to, index_set_ids=index_set_ids, source=f"scheduled:opensearch:{schedule_name}", keep_indices=int(keep_indices) if keep_indices else None)
        else:
            exporter = Exporter(
                server_config, self.settings.export,
                self.settings.rate_limit, self.db, integrity=self.settings.integrity,
            )

            # Pass first stream_id for stream-aware resume point
            first_stream = stream_ids[0] if stream_ids else None
            resume_point = exporter.get_resume_point(stream_id=first_stream)
            if resume_point:
                resume_point = _ensure_naive(resume_point)
                log.info("Resume point (API)", resume=str(resume_point), stream=first_stream)
                if resume_point > time_from:
                    time_from = resume_point
                # Safety: if resume_point >= time_to, nothing to export
                if time_from >= time_to:
                    log.info("Resume point is at or beyond time_to, nothing to export",
                             time_from=str(time_from), time_to=str(time_to))
                    return
            else:
                log.info("No resume point found (API), using full range", stream=first_stream)
            log.info("Scheduled export starting (API)", time_from=str(time_from), time_to=str(time_to), streams=stream_ids)
            result = await exporter.export(time_from=time_from, time_to=time_to, streams=stream_ids, source=f"scheduled:api:{schedule_name}")
        log.info("Scheduled export completed",
                 chunks=result.chunks_exported,
                 skipped=result.chunks_skipped,
                 messages=result.messages_total)

    def _run_cleanup(self, schedule_name: str = "auto-cleanup") -> None:
        """Scheduled cleanup job."""
        if self._running_jobs.get("cleanup"):
            log.warning("Cleanup already running, skipping scheduled run")
            return

        self._running_jobs["cleanup"] = True
        job_id = self._create_run_job(JobType.CLEANUP, f"scheduled:cleanup:{schedule_name}")
        try:
            cleaner = Cleaner(self.settings.retention, self.settings.export, self.db, self.settings.op_audit)
            result = cleaner.cleanup()
            log.info("Scheduled cleanup completed",
                     files_deleted=result.files_deleted,
                     bytes_freed=result.bytes_freed)
            mb = result.bytes_freed / (1024 * 1024)
            self._finish_run_job(
                job_id, JobStatus.COMPLETED,
                messages_done=result.files_deleted,
                messages_total=result.files_deleted,
                progress_pct=100.0,
                error_message=f"Deleted {result.files_deleted} files ({mb:.1f} MB)",
            )
        except Exception as e:
            from glogarch.utils.sanitize import sanitize
            log.error("Scheduled cleanup failed", error=str(e))
            self._finish_run_job(job_id, JobStatus.FAILED,
                                 error_message=sanitize(str(e)))
        finally:
            self._running_jobs["cleanup"] = False
            self._update_schedule_last_run(schedule_name)

    def _run_verify(self, schedule_name: str = "auto-verify") -> None:
        """Scheduled archive verification — checks SHA256 hash of all completed archives."""
        if self._running_jobs.get("verify"):
            log.warning("Verify already running, skipping scheduled run")
            return

        self._running_jobs["verify"] = True
        job_id = self._create_run_job(JobType.VERIFY, f"scheduled:verify:{schedule_name}")
        try:
            from glogarch.verify.verifier import Verifier
            verifier = Verifier(self.settings.export, self.db, integrity=self.settings.integrity)
            result = verifier.verify_all()
            log.info("Scheduled verify completed",
                     total=result.total_checked,
                     valid=result.valid,
                     corrupted=len(result.corrupted),
                     missing=len(result.missing_files))
            note = (f"{result.valid} valid, {len(result.corrupted)} corrupted, "
                    f"{len(result.missing_files)} missing of {result.total_checked} total")
            status = (JobStatus.FAILED
                      if result.corrupted or result.missing_files
                      else JobStatus.COMPLETED)
            self._finish_run_job(
                job_id, status,
                messages_done=result.total_checked,
                messages_total=result.total_checked,
                progress_pct=100.0,
                error_message=note,
            )
            if result.corrupted or result.missing_files:
                try:
                    from glogarch.notify.sender import notify_error
                    import asyncio
                    msg = f"Verify: {len(result.corrupted)} corrupted, {len(result.missing_files)} missing"
                    loop = asyncio.get_event_loop()
                    loop.create_task(notify_error("Verify", msg))
                except Exception:
                    pass
        except Exception as e:
            from glogarch.utils.sanitize import sanitize
            log.error("Scheduled verify failed", error=str(e))
            self._finish_run_job(job_id, JobStatus.FAILED,
                                 error_message=sanitize(str(e)))
        finally:
            self._running_jobs["verify"] = False
            self._update_schedule_last_run(schedule_name)

    def _run_report_cleanup(self, schedule_name: str = "auto-report-cleanup") -> None:
        """Scheduled cleanup of generated report PDFs older than N days."""
        if self._running_jobs.get("report_cleanup"):
            return
        self._running_jobs["report_cleanup"] = True
        job_id = self._create_run_job(JobType.CLEANUP, f"scheduled:report-cleanup:{schedule_name}")
        try:
            import json as _json
            import os as _os
            days = 720
            for s in self.db.list_schedules():
                if s.name == schedule_name and s.config_json:
                    try:
                        days = int(_json.loads(s.config_json).get("days", 720))
                    except Exception:
                        pass
                    break
            paths = self.db.prune_report_history(days=days)
            deleted = 0
            for p in paths:
                for f in (p, (p + ".sha256") if p else None):
                    try:
                        if f and _os.path.exists(f):
                            _os.remove(f)
                    except Exception:
                        pass
                deleted += 1
            log.info("Scheduled report cleanup completed", deleted=deleted, days=days)
            self._finish_run_job(job_id, JobStatus.COMPLETED, messages_done=deleted,
                                 messages_total=deleted, progress_pct=100.0,
                                 error_message=f"Deleted {deleted} reports older than {days} days")
        except Exception as e:
            from glogarch.utils.sanitize import sanitize
            log.error("Scheduled report cleanup failed", error=str(e))
            self._finish_run_job(job_id, JobStatus.FAILED, error_message=sanitize(str(e)))
        finally:
            self._running_jobs["report_cleanup"] = False
            self._update_schedule_last_run(schedule_name)

    def _update_schedule_last_run(self, name: str) -> None:
        try:
            schedules = self.db.list_schedules()
            for s in schedules:
                if s.name == name:
                    s.last_run_at = datetime.utcnow()
                    self.db.save_schedule(s)
                    break
        except Exception:
            pass

    def _create_run_job(self, job_type: JobType, source: str) -> str:
        """Create a Job History row for a scheduled run; returns job_id (uuid)
        on success, "" on failure. Best-effort — never blocks the actual job."""
        import uuid
        job_id = str(uuid.uuid4())
        try:
            self.db.create_job(JobRecord(
                id=job_id,
                job_type=job_type,
                status=JobStatus.RUNNING,
                source=source,
                started_at=datetime.utcnow(),
            ))
            return job_id
        except Exception:
            return ""

    def _finish_run_job(self, job_id: str, status: JobStatus, **fields) -> None:
        """Mark a run job complete/failed. No-op when job_id is empty."""
        if not job_id:
            return
        try:
            self.db.update_job(
                job_id,
                status=status,
                completed_at=datetime.utcnow(),
                **fields,
            )
        except Exception:
            pass

    _JOB_NAMES = {
        "export": "Automatic Export",
        "cleanup": "Automatic Cleanup",
        "verify": "Automatic Verify",
        "report_cleanup": "Automatic Report Cleanup",
    }

    def _job_callable(self, job_type: str):
        if job_type == "export":
            return self._run_export_in_thread
        if job_type == "cleanup":
            return self._run_cleanup
        if job_type == "verify":
            return self._run_verify
        if job_type == "report_cleanup":
            return self._run_report_cleanup
        return None

    def apply_schedule(self, sched: ScheduleRecord) -> None:
        """Add/update or remove a job in the running APScheduler based on the DB record.

        Called by Web UI handlers (save / toggle) so that DB changes take effect
        immediately without a service restart.
        """
        from apscheduler.jobstores.base import JobLookupError

        job_id = sched.name
        if not sched.enabled:
            try:
                self.scheduler.remove_job(job_id)
                log.info("Schedule unregistered (disabled)", name=job_id)
            except JobLookupError:
                pass
            return

        func = self._job_callable(sched.job_type)
        if func is None:
            log.warning("Unknown job_type, not registering",
                        name=job_id, type=sched.job_type)
            return

        cron_for_aps = posix_cron_to_apscheduler(sched.cron_expr)
        self.scheduler.add_job(
            func,
            trigger=CronTrigger.from_crontab(cron_for_aps),
            id=job_id,
            name=self._JOB_NAMES.get(sched.job_type, job_id),
            args=[sched.name],
            replace_existing=True,
        )
        log.info("Schedule registered", name=job_id, type=sched.job_type,
                 cron=sched.cron_expr,
                 cron_aps=(cron_for_aps if cron_for_aps != sched.cron_expr else None))

    def remove_schedule(self, name: str) -> None:
        """Remove a job from the running APScheduler if it exists."""
        from apscheduler.jobstores.base import JobLookupError
        try:
            self.scheduler.remove_job(name)
            log.info("Schedule removed from runtime", name=name)
        except JobLookupError:
            pass

    def setup(self) -> None:
        """Configure scheduled jobs from settings.

        Bootstraps DB records from config.yaml on first run; afterwards, all
        scheduling is driven by DB records (which the Web UI can edit).
        """
        import json
        sched_config = self.settings.schedule
        existing = {s.name: s for s in self.db.list_schedules()}

        # Bootstrap auto-export from config.yaml on first run
        if sched_config.export_cron and "auto-export" not in existing:
            export_config = json.dumps({
                "mode": self.settings.export_mode,
                "days": sched_config.export_days,
                "server": self.settings.default_server or (self.settings.servers[0].name if self.settings.servers else ""),
                "index_set": "",
                "batch_size": self.settings.export.batch_size,
                "auto_resume": True,
            })
            rec = ScheduleRecord(
                name="auto-export",
                job_type="export",
                cron_expr=sched_config.export_cron,
                config_json=export_config,
                enabled=True,
            )
            self.db.save_schedule(rec)
            existing["auto-export"] = rec
            log.info("Bootstrapped auto-export from config.yaml",
                     cron=sched_config.export_cron)

        # Bootstrap auto-cleanup from config.yaml on first run
        if (sched_config.cleanup_cron and self.settings.retention.enabled
                and "auto-cleanup" not in existing):
            cleanup_config = json.dumps({
                "retention_days": self.settings.retention.retention_days,
            })
            rec = ScheduleRecord(
                name="auto-cleanup",
                job_type="cleanup",
                cron_expr=sched_config.cleanup_cron,
                config_json=cleanup_config,
                enabled=True,
            )
            self.db.save_schedule(rec)
            existing["auto-cleanup"] = rec
            log.info("Bootstrapped auto-cleanup from config.yaml",
                     cron=sched_config.cleanup_cron)

        # Auto-add the report-cleanup schedule (720-day retention) if missing.
        # Runs on every startup, so both fresh installs and upgrades from older
        # versions gain it automatically without touching config.yaml.
        if "auto-report-cleanup" not in existing:
            rec = ScheduleRecord(
                name="auto-report-cleanup",
                job_type="report_cleanup",
                cron_expr="0 4 * * *",
                config_json=json.dumps({"days": 720}),
                enabled=True,
            )
            self.db.save_schedule(rec)
            existing["auto-report-cleanup"] = rec
            log.info("Bootstrapped auto-report-cleanup (720-day retention)")

        # Register every DB schedule with APScheduler
        for sched in existing.values():
            self.apply_schedule(sched)

        # Register report schedules (beta)
        try:
            for rep in self.db.list_reports():
                self.apply_report(rep["name"])
        except Exception as e:
            log.warning("Report schedule registration failed", error=str(e))

    # --- Reports (beta) ---

    def apply_report(self, name: str) -> None:
        """(Re)register a report's cron schedule with APScheduler."""
        import json
        job_id = f"report:{name}"
        try:
            self.scheduler.remove_job(job_id)
        except Exception:
            pass
        rep = self.db.get_report(name)
        if not rep or not rep.get("enabled"):
            return
        try:
            cfg = json.loads(rep.get("config_json") or "{}")
        except Exception:
            return
        cron = (cfg.get("schedule_cron") or "").strip()
        if not cron:
            return
        self.scheduler.add_job(
            self._run_report, trigger=CronTrigger.from_crontab(posix_cron_to_apscheduler(cron)),
            args=[name], id=job_id, replace_existing=True, misfire_grace_time=3600)
        log.info("Report scheduled", report=name, cron=cron)

    def remove_report(self, name: str) -> None:
        try:
            self.scheduler.remove_job(f"report:{name}")
        except Exception:
            pass

    def _run_report(self, name: str) -> None:
        """Generate a scheduled report in a worker thread (Chromium is heavy)."""
        import threading

        def _work():
            import asyncio
            import json
            import uuid as _uuid
            from datetime import datetime as _dt
            from glogarch.report import generator
            from glogarch.utils.sanitize import sanitize
            from glogarch.core.models import JobRecord, JobType, JobStatus
            rep = self.db.get_report(name)
            if not rep:
                return
            job_id = str(_uuid.uuid4())
            try:
                self.db.create_job(JobRecord(id=job_id, job_type=JobType.REPORT,
                                             status=JobStatus.RUNNING, source="scheduled:report",
                                             started_at=_dt.utcnow()))
            except Exception:
                job_id = None
            try:
                cfg = json.loads(rep.get("config_json") or "{}")
                cfg["name"] = name
                _res = asyncio.run(generator.generate_report(self.db, self.settings, cfg,
                                                             triggered_by="scheduled"))
                _units = int((_res or {}).get("units", 0) or 0)
                if job_id:
                    self.db.update_job(job_id, status=JobStatus.COMPLETED, completed_at=_dt.utcnow(),
                                       progress_pct=100.0, messages_done=_units, messages_total=_units,
                                       error_message=f"report={name}")
            except Exception as e:
                log.error("Scheduled report failed", report=name, error=str(e))
                if job_id:
                    try:
                        self.db.update_job(job_id, status=JobStatus.FAILED, completed_at=_dt.utcnow(),
                                           error_message=sanitize(str(e)))
                    except Exception:
                        pass
                try:
                    self.db.record_report_history(name, "", "", 0, "failed", sanitize(str(e)),
                                                  triggered_by="scheduled")
                except Exception:
                    pass

        threading.Thread(target=_work, daemon=True).start()

    def start(self) -> None:
        """Start the scheduler."""
        self.setup()
        self.scheduler.start()
        log.info("Scheduler started")

    def stop(self) -> None:
        """Stop the scheduler."""
        self.scheduler.shutdown(wait=False)
        self.db.close()
        log.info("Scheduler stopped")
