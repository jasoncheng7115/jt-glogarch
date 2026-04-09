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
from glogarch.core.models import ScheduleRecord
from glogarch.export.exporter import Exporter
from glogarch.utils.logging import get_logger

log = get_logger("scheduler")


class ArchiveScheduler:
    """Manages periodic export and cleanup jobs."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.scheduler = AsyncIOScheduler()
        self.db = ArchiveDB(self.settings.database_path)
        self.db.connect()
        self._running_jobs: dict[str, bool] = {}

    def _run_export_in_thread(self) -> None:
        """Sync wrapper that runs the async export in its own asyncio loop in a
        worker thread, so the main FastAPI event loop is not blocked by CPU-bound
        work (gzip, JSON parsing, GELF formatting)."""
        import threading
        threading.Thread(
            target=lambda: asyncio.run(self._run_export()),
            daemon=True,
            name="scheduled-export",
        ).start()

    async def _run_export(self) -> None:
        """Scheduled export job — reads config from DB (supports Web UI edits)."""
        if self._running_jobs.get("export"):
            log.warning("Export already running, skipping scheduled run")
            return

        self._running_jobs["export"] = True
        try:
            import json as _json
            from datetime import timedelta
            from glogarch.export.exporter import _ensure_naive

            # Read config from DB (may have been edited via Web UI)
            sched_list = self.db.list_schedules()
            sched_rec = next((s for s in sched_list if s.name == "auto-export"), None)
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

            if export_mode == "opensearch" and self.settings.opensearch.hosts:
                from glogarch.opensearch.exporter import OpenSearchExporter
                exporter = OpenSearchExporter(
                    server_config, self.settings.opensearch, self.settings.export,
                    self.settings.rate_limit, self.db,
                )
                # OpenSearch: no resume point — rely on per-chunk dedup to avoid gaps
                log.info("OpenSearch mode: using full range with per-chunk dedup")
                log.info("Scheduled export starting (OpenSearch)", time_from=str(time_from), time_to=str(time_to), keep_indices=keep_indices)
                result = await exporter.export(time_from=time_from, time_to=time_to, index_set_ids=index_set_ids, source="scheduled:opensearch", keep_indices=int(keep_indices) if keep_indices else None)
            else:
                exporter = Exporter(
                    server_config, self.settings.export,
                    self.settings.rate_limit, self.db,
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
                result = await exporter.export(time_from=time_from, time_to=time_to, streams=stream_ids, source="scheduled:api")
            log.info("Scheduled export completed",
                     chunks=result.chunks_exported,
                     skipped=result.chunks_skipped,
                     messages=result.messages_total)

        except Exception as e:
            log.error("Scheduled export failed", error=str(e))
        finally:
            self._running_jobs["export"] = False
            self._update_schedule_last_run("auto-export")

    def _run_cleanup(self) -> None:
        """Scheduled cleanup job."""
        if self._running_jobs.get("cleanup"):
            log.warning("Cleanup already running, skipping scheduled run")
            return

        self._running_jobs["cleanup"] = True
        try:
            cleaner = Cleaner(self.settings.retention, self.settings.export, self.db)
            result = cleaner.cleanup()
            log.info("Scheduled cleanup completed",
                     files_deleted=result.files_deleted,
                     bytes_freed=result.bytes_freed)
        except Exception as e:
            log.error("Scheduled cleanup failed", error=str(e))
        finally:
            self._running_jobs["cleanup"] = False
            self._update_schedule_last_run("auto-cleanup")

    def _run_verify(self) -> None:
        """Scheduled archive verification — checks SHA256 hash of all completed archives."""
        if self._running_jobs.get("verify"):
            log.warning("Verify already running, skipping scheduled run")
            return

        self._running_jobs["verify"] = True
        try:
            from glogarch.verify.verifier import Verifier
            verifier = Verifier(self.settings.export, self.db)
            result = verifier.verify_all()
            log.info("Scheduled verify completed",
                     total=result.total_checked,
                     valid=result.valid,
                     corrupted=len(result.corrupted),
                     missing=len(result.missing_files))
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
            log.error("Scheduled verify failed", error=str(e))
        finally:
            self._running_jobs["verify"] = False
            self._update_schedule_last_run("auto-verify")

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

    def setup(self) -> None:
        """Configure scheduled jobs from settings.

        Only creates DB records if they don't exist yet.
        Existing records (possibly edited via Web UI) are preserved.
        """
        import json
        sched_config = self.settings.schedule
        existing = {s.name: s for s in self.db.list_schedules()}

        if sched_config.export_cron:
            # Use DB config if exists, otherwise create from config.yaml
            ex = existing.get("auto-export")
            if ex:
                # Use cron and config from DB (user may have edited)
                cron = ex.cron_expr
                if not ex.enabled:
                    log.info("auto-export is disabled, skipping")
                else:
                    self.scheduler.add_job(
                        self._run_export_in_thread,
                        trigger=CronTrigger.from_crontab(cron),
                        id="auto-export",
                        name="Automatic Export",
                        replace_existing=True,
                    )
                    log.info("Export schedule configured (from DB)", cron=cron)
            else:
                # First time — create from config.yaml
                self.scheduler.add_job(
                    self._run_export_in_thread,
                    trigger=CronTrigger.from_crontab(sched_config.export_cron),
                    id="auto-export",
                    name="Automatic Export",
                    replace_existing=True,
                )
                export_config = json.dumps({
                    "mode": self.settings.export_mode,
                    "days": sched_config.export_days,
                    "server": self.settings.default_server or (self.settings.servers[0].name if self.settings.servers else ""),
                    "index_set": "",
                    "batch_size": self.settings.export.batch_size,
                    "auto_resume": True,
                })
                self.db.save_schedule(ScheduleRecord(
                    name="auto-export",
                    job_type="export",
                    cron_expr=sched_config.export_cron,
                    config_json=export_config,
                    enabled=True,
                ))
                log.info("Export schedule configured (new)", cron=sched_config.export_cron)

        if sched_config.cleanup_cron and self.settings.retention.enabled:
            ex = existing.get("auto-cleanup")
            if ex:
                cron = ex.cron_expr
                if not ex.enabled:
                    log.info("auto-cleanup is disabled, skipping")
                else:
                    self.scheduler.add_job(
                        self._run_cleanup,
                        trigger=CronTrigger.from_crontab(cron),
                        id="auto-cleanup",
                        name="Automatic Cleanup",
                        replace_existing=True,
                    )
                    log.info("Cleanup schedule configured (from DB)", cron=cron)
            else:
                self.scheduler.add_job(
                    self._run_cleanup,
                    trigger=CronTrigger.from_crontab(sched_config.cleanup_cron),
                    id="auto-cleanup",
                    name="Automatic Cleanup",
                    replace_existing=True,
                )
                cleanup_config = json.dumps({
                    "retention_days": self.settings.retention.retention_days,
                })
                self.db.save_schedule(ScheduleRecord(
                    name="auto-cleanup",
                    job_type="cleanup",
                    cron_expr=sched_config.cleanup_cron,
                    config_json=cleanup_config,
                    enabled=True,
                ))
                log.info("Cleanup schedule configured (new)", cron=sched_config.cleanup_cron)

        # Verify schedule — load from DB if exists
        ex_verify = existing.get("auto-verify")
        if ex_verify:
            if ex_verify.enabled:
                self.scheduler.add_job(
                    self._run_verify,
                    trigger=CronTrigger.from_crontab(ex_verify.cron_expr),
                    id="auto-verify",
                    name="Automatic Verify",
                    replace_existing=True,
                )
                log.info("Verify schedule configured (from DB)", cron=ex_verify.cron_expr)
            else:
                log.info("auto-verify is disabled, skipping")

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
