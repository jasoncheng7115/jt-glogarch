"""REST API routes for glogarch web interface."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Query, Request
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from glogarch.archive.storage import ArchiveStorage
from glogarch.cleanup.cleaner import Cleaner
from glogarch.core.config import Settings
from glogarch.core.database import ArchiveDB
from glogarch.core.models import ArchiveStatus, JobStatus
from glogarch.export.exporter import Exporter
from glogarch.gelf.sender import GelfSender
from glogarch.import_.importer import Importer
from glogarch.verify.verifier import Verifier
from glogarch.utils.logging import get_logger

log = get_logger("web.api")
router = APIRouter()

# Cancellation registry — shared between API and background tasks
_cancel_flags: dict[str, bool] = {}


def _audit(request: Request, action: str, detail: str = ""):
    try:
        db = request.app.state.db
        username = request.session.get("username", "")
        ip = request.client.host if request.client else ""
        db.audit(action, detail, username, ip)
    except Exception:
        pass

# In-memory progress store for SSE
_job_progress: dict[str, list[dict]] = {}


def _db(request: Request) -> ArchiveDB:
    return request.app.state.db


def _settings(request: Request) -> Settings:
    return request.app.state.settings


def _config_path(request: Request) -> Path:
    """Get path to config.yaml from settings, with fallback."""
    settings = _settings(request)
    if settings.config_path:
        return Path(settings.config_path)
    return Path("/opt/jt-glogarch/config.yaml")


# --- Archives ---

@router.get("/archives")
def list_archives(
    request: Request,
    server: str | None = None,
    stream: str | None = None,
    time_from: str | None = None,
    time_to: str | None = None,
    status: str | None = None,
    sort: str = "time_from",
    order: str = "desc",
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
):
    db = _db(request)
    dt_from = _parse_dt(time_from) if time_from else None
    dt_to = _parse_dt(time_to) if time_to else None
    try:
        arch_status = ArchiveStatus(status) if status else None
    except ValueError:
        return JSONResponse({"error": f"Invalid status: {status}"}, status_code=400)

    archives = db.list_archives(
        server=server, stream=stream,
        time_from=dt_from, time_to=dt_to, status=arch_status,
        sort=sort, order=order,
    )

    total = len(archives)
    start = (page - 1) * page_size
    page_items = archives[start:start + page_size]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_archive_to_dict(a) for a in page_items],
    }


@router.get("/archives/timeline")
def get_archive_timeline(request: Request):
    """Get archive distribution by day for timeline visualization."""
    db = _db(request)
    rows = db.conn.execute(
        """SELECT date(time_from) as day,
                  COUNT(*) as count,
                  COALESCE(SUM(message_count), 0) as messages,
                  COALESCE(SUM(file_size_bytes), 0) as bytes
           FROM archives
           WHERE status = 'completed'
           GROUP BY date(time_from)
           ORDER BY day"""
    ).fetchall()
    return {
        "items": [
            {"day": r[0], "count": r[1], "messages": r[2], "bytes": r[3]}
            for r in rows
        ]
    }


@router.get("/archives/{archive_id}")
def get_archive(request: Request, archive_id: int):
    db = _db(request)
    archive = db.get_archive(archive_id)
    if not archive:
        return JSONResponse({"error": "Archive not found"}, status_code=404)
    return _archive_to_dict(archive)


@router.delete("/archives/{archive_id}")
def delete_archive(request: Request, archive_id: int):
    """Delete an archive — removes file from disk and marks as deleted in DB."""
    db = _db(request)
    settings = _settings(request)
    archive = db.get_archive(archive_id)
    if not archive:
        return JSONResponse({"error": "Archive not found"}, status_code=404)

    from glogarch.archive.storage import ArchiveStorage
    from glogarch.core.models import ArchiveStatus
    storage = ArchiveStorage(settings.export)
    try:
        storage.delete_archive_file(archive.file_path)
    except PermissionError:
        return JSONResponse({"error": f"Permission denied: cannot delete {archive.file_path}"}, status_code=403)
    except Exception as e:
        return JSONResponse({"error": f"Delete failed: {e}"}, status_code=500)
    db.update_archive_status(archive_id, ArchiveStatus.DELETED)
    _audit(request, "archive_deleted", f"ID={archive_id} path={archive.file_path}")
    return {"status": "deleted", "id": archive_id}


# --- Export ---

@router.post("/export")
async def trigger_export(request: Request, background_tasks: BackgroundTasks):
    body = await request.json()
    settings = _settings(request)
    db = _db(request)

    mode = body.get("mode") or settings.export_mode
    server_name = body.get("server")
    server_config = settings.get_server(server_name)
    days = body.get("days")
    resume = body.get("resume", True)
    streams = body.get("streams") or None
    index_set = body.get("index_set") or None
    keep_indices = body.get("keep_indices") or None

    time_to = _parse_dt(body.get("time_to")) if body.get("time_to") else datetime.utcnow()
    if days:
        from datetime import timedelta
        time_from = time_to - timedelta(days=int(days))
    elif body.get("time_from"):
        time_from = _parse_dt(body["time_from"])
    else:
        return JSONResponse({"error": "Must specify time_from or days"}, status_code=400)

    # Clean up old progress entries (keep last 50)
    if len(_job_progress) > 50:
        oldest_keys = sorted(_job_progress.keys())[:len(_job_progress) - 50]
        for k in oldest_keys:
            _job_progress.pop(k, None)

    job_id = str(uuid.uuid4())
    _job_progress[job_id] = []

    def _cb(info):
        # Check if cancelled
        if _cancel_flags.get(job_id):
            raise RuntimeError("Job cancelled by user")
        info["job_id"] = job_id
        events = _job_progress.setdefault(job_id, [])
        # Keep only last 100 progress events per job to limit memory
        if len(events) > 100:
            _job_progress[job_id] = events[-50:]
        events.append(info)

    if mode == "opensearch":
        from glogarch.opensearch.exporter import OpenSearchExporter
        from glogarch.export.exporter import _ensure_naive

        if not settings.opensearch.hosts:
            return JSONResponse({"error": "OpenSearch not configured"}, status_code=400)

        os_exporter = OpenSearchExporter(
            server_config, settings.opensearch, settings.export,
            settings.rate_limit, db,
        )
        # OpenSearch: no resume point — rely on per-chunk dedup to avoid gaps

        def _run_in_thread():
            try:
                result = asyncio.run(os_exporter.export(
                    time_from=time_from, time_to=time_to,
                    index_set_ids=[index_set] if index_set else None,
                    progress_callback=_cb, source="manual:opensearch",
                    job_id=job_id, keep_indices=int(keep_indices) if keep_indices else None,
                ))
                _job_progress.setdefault(job_id, []).append(
                    {"phase": "done", "pct": 100, "messages_done": result.messages_total, "messages_total": result.messages_total, "source": "manual"}
                )
            except Exception as e:
                _job_progress.setdefault(job_id, []).append(
                    {"phase": "error", "error": str(e), "pct": 100}
                )
    else:
        from glogarch.export.exporter import _ensure_naive
        exporter = Exporter(server_config, settings.export, settings.rate_limit, db)

        if resume:
            rp = exporter.get_resume_point(streams[0] if streams else None)
            if rp:
                rp = _ensure_naive(rp)
                time_from_naive = _ensure_naive(time_from)
                if rp > time_from_naive:
                    time_from = rp

        def _run_in_thread():
            try:
                result = asyncio.run(exporter.export(
                    time_from=time_from, time_to=time_to,
                    streams=streams, progress_callback=_cb, source="manual:api",
                    job_id=job_id,
                ))
                _job_progress.setdefault(job_id, []).append(
                    {"phase": "done", "pct": 100, "messages_done": result.messages_total, "messages_total": result.messages_total}
                )
            except Exception as e:
                _job_progress.setdefault(job_id, []).append(
                    {"phase": "error", "error": str(e), "pct": 100}
                )

    asyncio.get_event_loop().run_in_executor(None, _run_in_thread)
    _audit(request, "export_started", f"mode={mode} job={job_id}")
    return {"job_id": job_id, "status": "started", "mode": mode}


# --- Import ---

@router.post("/import")
async def trigger_import(request: Request, background_tasks: BackgroundTasks):
    body = await request.json()
    settings = _settings(request)
    db = _db(request)

    # --- Compliance: Graylog API credentials are MANDATORY ---
    # Pre-flight check + post-import reconciliation both need API access.
    # No more "monitor_mode = none" / SSH path — those can't fix mapping conflicts.
    target_api_url = (body.get("target_api_url") or "").strip()
    target_api_token = (body.get("target_api_token") or "").strip()
    target_api_username = (body.get("target_api_username") or "").strip()
    target_api_password = body.get("target_api_password") or ""

    if not target_api_url:
        return JSONResponse(
            {"error": "target_api_url is required (compliance: zero indexer failures)"},
            status_code=400,
        )
    if not target_api_token and not (target_api_username and target_api_password):
        return JSONResponse(
            {"error": "Provide either target_api_token or target_api_username + target_api_password"},
            status_code=400,
        )

    # Override GELF settings from request
    import_cfg = settings.import_config.model_copy()
    if body.get("gelf_host"):
        import_cfg.gelf_host = body["gelf_host"]
    if body.get("gelf_port"):
        import_cfg.gelf_port = int(body["gelf_port"])
    if body.get("gelf_protocol"):
        import_cfg.gelf_protocol = body["gelf_protocol"]

    from glogarch.import_.journal_monitor import JournalMonitor
    from glogarch.import_.importer import ImportFlowControl
    from glogarch.import_.preflight import PreflightChecker
    from glogarch.import_.bulk import BulkImporter

    # Mode selection: "gelf" (default) or "bulk"
    import_mode = (body.get("mode") or "gelf").lower()
    if import_mode not in ("gelf", "bulk"):
        return JSONResponse(
            {"error": f"Invalid mode '{import_mode}'. Must be 'gelf' or 'bulk'."},
            status_code=400,
        )

    # Bulk-mode-specific validation + setup
    bulk_importer = None
    if import_mode == "bulk":
        # Resolve OpenSearch URL: explicit > auto-detect from Graylog URL
        os_url = (body.get("target_os_url") or "").strip()
        os_username = (body.get("target_os_username") or "").strip()
        os_password = body.get("target_os_password") or ""
        target_index_pattern = (body.get("target_index_pattern") or "jt_restored").strip()
        dedup_strategy = (body.get("dedup_strategy") or "id").lower()

        if dedup_strategy not in ("id", "none", "fail"):
            return JSONResponse(
                {"error": "dedup_strategy must be 'id', 'none', or 'fail'"},
                status_code=400,
            )

        # Auto-detect OpenSearch URL if not provided
        if not os_url:
            preflight_tmp = PreflightChecker(
                api_url=target_api_url,
                api_token=target_api_token,
                api_username=target_api_username,
                api_password=target_api_password,
            )
            os_url = await preflight_tmp.auto_detect_opensearch_url()
            if not os_url:
                return JSONResponse(
                    {"error": "Could not auto-detect OpenSearch URL. Provide target_os_url explicitly."},
                    status_code=400,
                )
            # Inherit Graylog credentials for OpenSearch if none provided
            if not os_username and not os_password:
                os_username = target_api_username
                os_password = target_api_password

        bulk_importer = BulkImporter(
            opensearch_url=os_url,
            os_username=os_username,
            os_password=os_password,
            target_index_pattern=target_index_pattern,
            dedup_strategy=dedup_strategy,
            batch_docs=int(body.get("batch_docs", 5000)),
        )
        # Verify reachability before starting
        ok, err = await bulk_importer.verify_opensearch()
        if not ok:
            return JSONResponse(
                {"error": f"OpenSearch verification failed: {err}"},
                status_code=400,
            )

    # Journal monitoring uses the same Graylog API credentials.
    journal_monitor = JournalMonitor(
        mode="api",
        api_url=target_api_url,
        api_token=target_api_token,
        api_username=target_api_username,
        api_password=target_api_password,
    )

    # Pre-flight checker (mapping conflict resolver + post-import reconciliation)
    preflight = PreflightChecker(
        api_url=target_api_url,
        api_token=target_api_token,
        api_username=target_api_username,
        api_password=target_api_password,
        gelf_port=import_cfg.gelf_port,
    )

    importer = Importer(
        import_cfg, settings.export, db,
        journal_monitor=journal_monitor,
        preflight=preflight,
        mode=import_mode,
        bulk_importer=bulk_importer,
    )

    archive_ids = body.get("archive_ids")
    target = body.get("target_server")

    job_id = str(uuid.uuid4())
    _job_progress[job_id] = []

    # Create flow control with user-specified rate
    fc = ImportFlowControl()
    fc.rate_ms = int(body.get("rate_ms", import_cfg.delay_between_batches_ms))
    fc.batch_size = int(body.get("batch_size", import_cfg.batch_size))
    fc._base_rate_ms = fc.rate_ms

    def _run_in_thread():
        """Run import in a worker thread with its own asyncio loop so the main
        FastAPI event loop is not blocked by CPU-bound work (gzip decode, JSON
        parse, GELF formatting)."""
        def _cb(info):
            if fc.cancelled:
                raise RuntimeError("Job cancelled by user")
            info["job_id"] = job_id
            _job_progress.setdefault(job_id, []).append(info)

        try:
            asyncio.run(importer.import_archives(
                archive_ids=archive_ids,
                target_server=target,
                progress_callback=_cb,
                job_id=job_id,
                flow_control=fc,
            ))
            _job_progress.setdefault(job_id, []).append(
                {"phase": "done", "pct": 100}
            )
        except Exception as e:
            _job_progress.setdefault(job_id, []).append(
                {"phase": "error", "error": str(e), "pct": 100}
            )

    asyncio.get_event_loop().run_in_executor(None, _run_in_thread)
    _audit(request, "import_started", f"job={job_id} mode={import_mode} api={target_api_url}")
    return {"job_id": job_id, "status": "started", "mode": import_mode}


@router.post("/import/{job_id}/pause")
async def pause_import(request: Request, job_id: str):
    """Pause a running import job."""
    from glogarch.import_.importer import get_import_control
    fc = get_import_control(job_id)
    if not fc:
        return JSONResponse({"error": "Import job not found or not running"}, status_code=404)
    fc.pause()
    return {"status": "paused", "job_id": job_id}


@router.post("/import/{job_id}/resume")
async def resume_import(request: Request, job_id: str):
    """Resume a paused import job."""
    from glogarch.import_.importer import get_import_control
    fc = get_import_control(job_id)
    if not fc:
        return JSONResponse({"error": "Import job not found or not running"}, status_code=404)
    fc.resume()
    return {"status": "resumed", "job_id": job_id}


@router.post("/import/{job_id}/rate")
async def set_import_rate(request: Request, job_id: str):
    """Adjust import speed in real-time."""
    body = await request.json()
    from glogarch.import_.importer import get_import_control
    fc = get_import_control(job_id)
    if not fc:
        return JSONResponse({"error": "Import job not found or not running"}, status_code=404)
    rate_ms = int(body.get("rate_ms", fc.rate_ms))
    batch_size = int(body.get("batch_size", fc.batch_size)) if body.get("batch_size") else None
    fc.set_rate(rate_ms, batch_size)
    return {"status": "ok", "rate_ms": fc.rate_ms, "batch_size": fc.batch_size}


@router.get("/import/{job_id}/status")
async def get_import_status(request: Request, job_id: str):
    """Get detailed import status including flow control and journal info."""
    from glogarch.import_.importer import get_import_control
    fc = get_import_control(job_id)
    if not fc:
        return JSONResponse({"error": "Import job not found or not running"}, status_code=404)
    js = fc.journal_status
    return {
        "paused": fc.paused,
        "cancelled": fc.cancelled,
        "rate_ms": fc.rate_ms,
        "effective_delay_ms": fc.get_effective_delay(),
        "batch_size": fc.batch_size,
        "auto_rate": fc.auto_rate,
        "journal_action": fc.journal_action,
        "journal": {
            "uncommitted": js.uncommitted if js else None,
            "size_bytes": js.size_bytes if js else None,
            "disk_free_bytes": js.disk_free_bytes if js else None,
            "available": js.available if js else False,
            "error": js.error if js else "",
        } if js else None,
    }


# --- Cleanup ---

@router.post("/cleanup")
def trigger_cleanup(request: Request, days: int | None = None, dry_run: bool = False):
    settings = _settings(request)
    db = _db(request)
    cleaner = Cleaner(settings.retention, settings.export, db)
    result = cleaner.cleanup(retention_days=days, dry_run=dry_run)
    return {
        "files_deleted": result.files_deleted,
        "bytes_freed": result.bytes_freed,
        "errors": result.errors,
    }


# --- Verify ---

@router.post("/verify")
def trigger_verify(request: Request, server: str | None = None):
    settings = _settings(request)
    db = _db(request)
    verifier = Verifier(settings.export, db)
    result = verifier.verify_all(server=server)
    return {
        "total_checked": result.total_checked,
        "valid": result.valid,
        "corrupted": result.corrupted,
        "missing_files": result.missing_files,
        "orphan_files": result.orphan_files,
    }


# --- Jobs ---

@router.get("/jobs")
def list_jobs(request: Request, limit: int = 50):
    db = _db(request)
    jobs = db.list_jobs(limit=limit)
    return {"items": [_job_to_dict(j) for j in jobs]}


@router.get("/jobs/{job_id}")
def get_job(request: Request, job_id: str):
    # Check in-memory progress first (for Web UI triggered jobs)
    if job_id in _job_progress:
        events = _job_progress[job_id]
        if events:
            last = events[-1]
            is_done = last.get("phase") in ("error", "done") or last.get("pct", 0) >= 100
            return {
                "id": job_id,
                "job_type": "export",
                "status": "completed" if (is_done and last.get("phase") != "error") else ("failed" if last.get("phase") == "error" else "running"),
                "progress_pct": last.get("pct", 0),
                "messages_done": last.get("messages_done", 0),
                "messages_total": last.get("messages_total"),
                "error_message": last.get("error"),
                "started_at": None,
                "completed_at": None,
            }
        # Job started but no progress yet — still running
        return {"id": job_id, "job_type": "export", "status": "running", "progress_pct": 0, "messages_done": 0, "messages_total": None, "error_message": None, "started_at": None, "completed_at": None}

    # Fallback to DB
    db = _db(request)
    job = db.get_job(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)
    return _job_to_dict(job)


@router.post("/jobs/{job_id}/cancel")
def cancel_job(request: Request, job_id: str):
    """Cancel a running job."""
    # Set cancellation flag for background task (works for both in-memory and DB jobs)
    _cancel_flags[job_id] = True

    # Check in-memory jobs first (Web UI triggered)
    if job_id in _job_progress:
        _job_progress.setdefault(job_id, []).append(
            {"phase": "error", "error": "Job cancelled by user", "pct": 100}
        )
        _audit(request, "job_cancelled", f"job={job_id}")
        return {"status": "cancelled", "id": job_id}

    # Fallback to DB jobs
    db = _db(request)
    job = db.get_job(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)
    if job.status.value not in ("running", "pending"):
        return JSONResponse({"error": "Job is not running"}, status_code=400)
    from glogarch.core.models import JobStatus
    db.update_job(job_id, status=JobStatus.CANCELLED, completed_at=datetime.utcnow())
    _audit(request, "job_cancelled", f"job={job_id}")
    return {"status": "cancelled", "id": job_id}


@router.get("/jobs/{job_id}/stream")
async def job_stream(request: Request, job_id: str):
    """SSE endpoint for real-time job progress."""
    async def event_generator():
        import json as _json
        last_idx = 0
        max_wait = 600  # 10 minutes max
        waited = 0
        while waited < max_wait:
            events = _job_progress.get(job_id, [])
            while last_idx < len(events):
                evt = events[last_idx]
                last_idx += 1
                yield {"event": "progress", "data": _json.dumps(evt)}
                if evt.get("pct", 0) >= 100 or evt.get("phase") in ("error", "done"):
                    yield {"event": "done", "data": _json.dumps(evt)}
                    return
                waited = 0  # Reset timeout on activity
            await asyncio.sleep(0.5)
            waited += 0.5
        # Timeout
        yield {"event": "done", "data": _json.dumps({"phase": "error", "error": "SSE timeout", "pct": 0})}

    return EventSourceResponse(event_generator())


# --- Schedules ---

@router.get("/schedules")
def list_schedules(request: Request):
    db = _db(request)
    schedules = db.list_schedules()
    return {"items": [_schedule_to_dict(s) for s in schedules]}


@router.post("/schedules")
async def save_schedule(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    if not body.get("name") or not body.get("cron_expr"):
        return JSONResponse({"error": "name and cron_expr are required"}, status_code=400)
    db = _db(request)
    from glogarch.core.models import ScheduleRecord
    import json as _json
    config_data = {}
    if body.get("job_type", "export") == "export":
        config_data = {
            "mode": body.get("mode", "api"),
            "days": body.get("days", 180),
            "index_set": body.get("index_set", ""),
            "streams": body.get("streams", []),
            "auto_resume": True,
        }
        if body.get("keep_indices"):
            config_data["keep_indices"] = int(body["keep_indices"])
    elif body.get("job_type") == "cleanup":
        config_data = {
            "retention_days": body.get("retention_days", _settings(request).retention.retention_days),
        }
    sched = ScheduleRecord(
        name=body["name"],
        job_type=body.get("job_type", "export"),
        cron_expr=body["cron_expr"],
        config_json=_json.dumps(config_data) if config_data else None,
        enabled=body.get("enabled", True),
    )
    db.save_schedule(sched)
    _audit(request, "schedule_saved", f"name={sched.name} cron={sched.cron_expr}")
    return {"status": "saved", "name": sched.name}


@router.post("/schedules/{name}/toggle")
async def toggle_schedule(request: Request, name: str):
    """Enable or disable a schedule."""
    body = await request.json()
    enabled = body.get("enabled", True)
    db = _db(request)
    schedules = db.list_schedules()
    found = [s for s in schedules if s.name == name]
    if not found:
        return JSONResponse({"error": "Schedule not found"}, status_code=404)
    s = found[0]
    s.enabled = enabled
    db.save_schedule(s)

    # For auto-* schedules, also update config.yaml
    if name.startswith("auto-"):
        import yaml
        config_path = _config_path(request)
        if config_path.exists():
            try:
                with open(config_path) as f:
                    cfg = yaml.safe_load(f) or {}
                if "schedule" not in cfg:
                    cfg["schedule"] = {}
                if name == "auto-export":
                    cfg["schedule"]["export_cron"] = s.cron_expr if enabled else None
                elif name == "auto-cleanup":
                    cfg["schedule"]["cleanup_cron"] = s.cron_expr if enabled else None
                with open(config_path, "w") as f:
                    yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True)
            except Exception:
                pass

    _audit(request, "schedule_toggled", f"{name} enabled={enabled}")
    return {"status": "ok", "name": name, "enabled": enabled}


@router.post("/schedules/{name}/run")
async def run_schedule_now(request: Request, name: str, background_tasks: BackgroundTasks):
    """Immediately run a schedule's export using its saved config."""
    import json as _json
    from datetime import timedelta
    from glogarch.export.exporter import _ensure_naive

    db = _db(request)
    settings = _settings(request)
    schedules = db.list_schedules()
    found = [s for s in schedules if s.name == name]
    if not found:
        return JSONResponse({"error": "Schedule not found"}, status_code=404)
    sched = found[0]
    if sched.job_type not in ("export", "cleanup", "verify"):
        return JSONResponse({"error": "This schedule type cannot be run manually"}, status_code=400)

    # Cleanup: run synchronously (fast)
    if sched.job_type == "cleanup":
        try:
            cfg = _json.loads(sched.config_json) if sched.config_json else {}
        except Exception:
            cfg = {}
        from glogarch.cleanup.cleaner import Cleaner
        cleaner = Cleaner(settings.retention, settings.export, db)
        result = cleaner.cleanup()
        _audit(request, "schedule_run_now", f"{name} cleanup deleted={result.files_deleted}")
        return {"status": "completed", "files_deleted": result.files_deleted, "bytes_freed": result.bytes_freed}

    # Verify: run synchronously
    if sched.job_type == "verify":
        from glogarch.verify.verifier import Verifier
        verifier = Verifier(settings.export, db)
        result = verifier.verify_all()
        _audit(request, "schedule_run_now", f"{name} verify total={result.total_checked} corrupted={len(result.corrupted)}")
        return {"status": "completed", "total_checked": result.total_checked, "valid": result.valid,
                "corrupted": len(result.corrupted), "missing": len(result.missing_files)}

    cfg = {}
    if sched.config_json:
        try:
            cfg = _json.loads(sched.config_json)
        except Exception:
            pass

    export_mode = cfg.get("mode", settings.export_mode)
    export_days = cfg.get("days", settings.schedule.export_days)
    server_config = settings.get_server(cfg.get("server"))
    stream_ids = cfg.get("streams") or None
    index_set = cfg.get("index_set") or None
    keep_indices = cfg.get("keep_indices") or None

    time_to = datetime.utcnow()
    time_from = time_to - timedelta(days=export_days)

    job_id = str(uuid.uuid4())
    _job_progress[job_id] = []

    def _cb(info):
        if _cancel_flags.get(job_id):
            raise RuntimeError("Job cancelled by user")
        info["job_id"] = job_id
        events = _job_progress.setdefault(job_id, [])
        if len(events) > 100:
            _job_progress[job_id] = events[-50:]
        events.append(info)

    if export_mode == "opensearch" and settings.opensearch.hosts:
        from glogarch.opensearch.exporter import OpenSearchExporter
        os_exporter = OpenSearchExporter(
            server_config, settings.opensearch, settings.export,
            settings.rate_limit, db,
        )
        # OpenSearch mode: do NOT use resume point to skip indices.
        # Rely on per-chunk dedup instead, to avoid missing gaps.

        def _run_in_thread():
            try:
                result = asyncio.run(os_exporter.export(
                    time_from=time_from, time_to=time_to,
                    index_set_ids=[index_set] if index_set else None,
                    progress_callback=_cb, source="manual:opensearch",
                    job_id=job_id, keep_indices=int(keep_indices) if keep_indices else None,
                ))
                _job_progress.setdefault(job_id, []).append(
                    {"phase": "done", "pct": 100, "messages_done": result.messages_total, "messages_total": result.messages_total}
                )
            except Exception as e:
                _job_progress.setdefault(job_id, []).append(
                    {"phase": "error", "error": str(e), "pct": 100}
                )
    else:
        exporter = Exporter(server_config, settings.export, settings.rate_limit, db)
        first_stream = stream_ids[0] if stream_ids else None
        rp = exporter.get_resume_point(stream_id=first_stream)
        if rp:
            rp = _ensure_naive(rp)
            if rp > _ensure_naive(time_from):
                time_from = rp

        def _run_in_thread():
            try:
                result = asyncio.run(exporter.export(
                    time_from=time_from, time_to=time_to,
                    streams=stream_ids, progress_callback=_cb, source="manual:api",
                    job_id=job_id,
                ))
                _job_progress.setdefault(job_id, []).append(
                    {"phase": "done", "pct": 100, "messages_done": result.messages_total, "messages_total": result.messages_total}
                )
            except Exception as e:
                _job_progress.setdefault(job_id, []).append(
                    {"phase": "error", "error": str(e), "pct": 100}
                )

    asyncio.get_event_loop().run_in_executor(None, _run_in_thread)
    _audit(request, "schedule_run_now", f"{name} mode={export_mode} job={job_id}")
    return {"job_id": job_id, "status": "started", "mode": export_mode}


@router.delete("/schedules/{name}")
def delete_schedule(request: Request, name: str):
    db = _db(request)
    db.delete_schedule(name)
    return {"status": "deleted", "name": name}


# --- Status ---

@router.get("/status")
def get_status(request: Request):
    settings = _settings(request)
    db = _db(request)
    storage = ArchiveStorage(settings.export)

    stats = db.get_archive_stats()
    storage_stats = storage.get_storage_stats()

    # Sparkline data: daily aggregates for last 30 days
    sparkline = _get_sparkline_data(db)

    return {
        "archive_stats": stats,
        "storage_stats": storage_stats,
        "sparkline": sparkline,
        "servers": [
            {"name": s.name, "url": s.url}
            for s in settings.servers
        ],
        "retention_days": settings.retention.retention_days,
        "export_path": settings.export.base_path,
    }


def _get_sparkline_data(db: ArchiveDB) -> dict:
    """Get daily aggregates for sparkline charts (last 30 days)."""
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(days=30)
    cutoff_str = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = db.conn.execute(
        """SELECT date(created_at) as day,
                  COUNT(*) as count,
                  COALESCE(SUM(message_count), 0) as messages,
                  COALESCE(SUM(file_size_bytes), 0) as bytes,
                  COALESCE(SUM(original_size_bytes), 0) as original_bytes
           FROM archives
           WHERE status = 'completed' AND created_at >= ?
           GROUP BY date(created_at)
           ORDER BY day""",
        (cutoff_str,),
    ).fetchall()
    return {
        "archives": [{"day": r[0], "count": r[1]} for r in rows],
        "messages": [{"day": r[0], "count": r[2]} for r in rows],
        "original_bytes": [{"day": r[0], "count": r[4]} for r in rows],
        "bytes": [{"day": r[0], "count": r[3]} for r in rows],
    }


@router.get("/servers")
async def list_servers(request: Request):
    """List servers with connectivity status."""
    settings = _settings(request)
    results = []
    for srv in settings.servers:
        from glogarch.graylog.client import GraylogClient
        from glogarch.ratelimit.limiter import RateLimiter
        rl = RateLimiter(settings.rate_limit)
        async with GraylogClient(srv, rl) as client:
            info = await client.check_connectivity()
            info["name"] = srv.name
            info["url"] = srv.url
            results.append(info)
    return {"items": results}


# --- Settings ---

@router.get("/settings/archive-path")
def get_archive_path(request: Request):
    settings = _settings(request)
    return {"base_path": settings.export.base_path}


@router.post("/settings/archive-path")
async def set_archive_path(request: Request):
    """Update archive base path with validation. Does NOT move files."""
    body = await request.json()
    new_path = body.get("base_path", "").strip()
    if not new_path:
        return JSONResponse({"error": "base_path is required"}, status_code=400)

    import os
    import shutil
    import yaml
    _Path = Path

    target = _Path(new_path)
    errors = []

    # 1. Check if path exists, try to create if not
    if not target.exists():
        try:
            target.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            errors.append(f"Cannot create directory: {new_path} (permission denied)")
        except Exception as e:
            errors.append(f"Cannot create directory: {new_path} ({e})")

    # 2. Check write permission
    if target.exists():
        test_file = target / ".jt-glogarch-write-test"
        try:
            test_file.write_text("test")
            test_file.unlink()
        except PermissionError:
            errors.append(f"No write permission on: {new_path}")
        except Exception as e:
            errors.append(f"Write test failed: {e}")

    # 3. Check disk space
    if target.exists():
        try:
            usage = shutil.disk_usage(target)
            avail_mb = usage.free / (1024 * 1024)
            if avail_mb < 500:
                errors.append(f"Insufficient disk space: {avail_mb:.0f} MB available (minimum 500 MB)")
        except Exception as e:
            errors.append(f"Cannot check disk space: {e}")

    # 4. Check it's not the same path
    settings = _settings(request)
    old_path = settings.export.base_path
    if os.path.realpath(new_path) == os.path.realpath(old_path):
        errors.append("New path is the same as current path")

    if errors:
        return JSONResponse({"error": "; ".join(errors)}, status_code=400)

    # All checks passed — update config
    settings.export.base_path = new_path

    config_path = _config_path(request)
    if config_path.exists():
        with open(config_path) as f:
            cfg = yaml.safe_load(f) or {}
        if "export" not in cfg:
            cfg["export"] = {}
        cfg["export"]["base_path"] = new_path
        with open(config_path, "w") as f:
            yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True)

    # Return with disk info
    usage = shutil.disk_usage(target)
    avail_mb = usage.free / (1024 * 1024)

    _audit(request, "archive_path_changed", f"{old_path} → {new_path}")

    return {
        "old_path": old_path,
        "new_path": new_path,
        "available_mb": round(avail_mb, 0),
    }


@router.post("/settings/rescan")
def rescan_archive_path(request: Request):
    """Scan the archive directory for .json.gz files not in DB and register them."""
    import gzip as _gzip
    settings = _settings(request)
    db = _db(request)
    base = Path(settings.export.base_path)

    if not base.exists():
        return JSONResponse({"error": f"Path does not exist: {base}"}, status_code=400)

    from glogarch.archive.integrity import compute_sha256
    from glogarch.core.models import ArchiveMetadata, ArchiveRecord, ArchiveStatus

    # Get all known file paths from DB
    known = {a.file_path for a in db.list_archives()}

    registered = 0
    errors = []

    for gz_file in sorted(base.rglob("*.json.gz")):
        file_str = str(gz_file)
        if file_str in known:
            continue

        try:
            with _gzip.open(gz_file, "rt", encoding="utf-8") as f:
                import json as _json
                data = _json.load(f)
            meta = data.get("metadata", {})
            msgs = data.get("messages", [])

            from datetime import datetime
            def _parse(s):
                for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S"):
                    try: return datetime.strptime(s, fmt)
                    except: continue
                return datetime.utcnow()

            checksum = compute_sha256(gz_file)
            record = ArchiveRecord(
                server_name=meta.get("server", "unknown"),
                stream_id=meta.get("stream_id"),
                stream_name=meta.get("stream_name"),
                time_from=_parse(meta.get("time_from", "")),
                time_to=_parse(meta.get("time_to", "")),
                file_path=file_str,
                file_size_bytes=gz_file.stat().st_size,
                message_count=len(msgs),
                part_number=meta.get("part", 1),
                total_parts=meta.get("total_parts", 1),
                checksum_sha256=checksum,
                status=ArchiveStatus.COMPLETED,
            )
            db.record_archive(record)
            registered += 1
        except Exception as e:
            errors.append(f"{gz_file.name}: {e}")

    # Reverse check: DB records whose files no longer exist → mark as deleted
    removed = 0
    all_archives = db.list_archives(status=ArchiveStatus.COMPLETED)
    for archive in all_archives:
        if not Path(archive.file_path).exists():
            db.update_archive_status(archive.id, ArchiveStatus.DELETED)
            removed += 1

    return {"registered": registered, "removed": removed, "errors": errors}


# --- Streams & Index Sets ---

@router.get("/streams")
async def list_streams(request: Request):
    settings = _settings(request)
    server_config = settings.get_server()
    from glogarch.graylog.client import GraylogClient
    from glogarch.ratelimit.limiter import RateLimiter
    rl = RateLimiter(settings.rate_limit)
    async with GraylogClient(server_config, rl) as client:
        streams = await client.get_streams()
    return {"items": [{"id": s["id"], "title": s.get("title", ""), "index_set_id": s.get("index_set_id", "")} for s in streams]}


@router.get("/index-sets")
async def list_index_sets(request: Request):
    settings = _settings(request)
    server_config = settings.get_server()
    from glogarch.graylog.client import GraylogClient
    from glogarch.ratelimit.limiter import RateLimiter
    rl = RateLimiter(settings.rate_limit)
    async with GraylogClient(server_config, rl) as client:
        index_sets = await client.get_index_sets()
    return {"items": [{"id": s["id"], "title": s.get("title", ""), "index_prefix": s.get("index_prefix", ""), "default": s.get("default", False)} for s in index_sets]}


# --- OpenSearch ---

@router.get("/opensearch/status")
async def opensearch_status(request: Request):
    """Get OpenSearch connection status and config."""
    settings = _settings(request)
    has_config = bool(settings.opensearch.hosts)
    return {
        "configured": has_config,
        "hosts": settings.opensearch.hosts,
        "export_mode": settings.export_mode,
    }


@router.get("/opensearch/indices")
async def list_opensearch_indices(request: Request, prefix: str | None = None):
    """Get available OpenSearch indices with time ranges for coverage visualization."""
    settings = _settings(request)
    if not settings.opensearch.hosts:
        return {"indices": [], "active_index": None}

    from glogarch.opensearch.client import OpenSearchClient

    # Resolve prefix
    if not prefix:
        try:
            from glogarch.graylog.client import GraylogClient
            from glogarch.ratelimit.limiter import RateLimiter
            rl = RateLimiter(settings.rate_limit)
            async with GraylogClient(settings.get_server(), rl) as gl:
                index_sets = await gl.get_index_sets()
                prefix = "graylog"
                for iset in index_sets:
                    if iset.get("default"):
                        prefix = iset.get("index_prefix", "graylog")
                        break
        except Exception:
            prefix = "graylog"

    async with OpenSearchClient(settings.opensearch) as client:
        indices = await client.list_indices(prefix)
        active = await client.get_active_write_index(prefix)

        # Get time ranges for each index
        result = []
        for idx in indices:
            min_ts, max_ts = await client.get_index_time_range(idx["index"])
            result.append({
                "index": idx["index"],
                "docs_count": idx["docs_count"],
                "store_size": idx.get("store_size", ""),
                "min_ts": min_ts,
                "max_ts": max_ts,
            })

        return {"indices": result, "active_index": active, "prefix": prefix,
                "max_indices": settings.export.batch_size}  # placeholder


@router.post("/opensearch/reorder")
async def reorder_opensearch(request: Request):
    """Reorder OpenSearch hosts — first host is primary."""
    body = await request.json()
    from_idx = body.get("from_index", 0)
    to_idx = body.get("to_index", 0)
    settings = _settings(request)

    hosts = list(settings.opensearch.hosts)
    if from_idx < 0 or from_idx >= len(hosts) or to_idx < 0 or to_idx >= len(hosts):
        return JSONResponse({"error": "Invalid index"}, status_code=400)

    # Move host from from_idx to to_idx
    host = hosts.pop(from_idx)
    hosts.insert(to_idx, host)
    settings.opensearch.hosts = hosts

    # Save to config.yaml
    import yaml
    config_path = _config_path(request)
    if config_path.exists():
        with open(config_path) as f:
            cfg = yaml.safe_load(f) or {}
        if "opensearch" not in cfg:
            cfg["opensearch"] = {}
        cfg["opensearch"]["hosts"] = hosts
        with open(config_path, "w") as f:
            yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True)

    return {"hosts": hosts, "primary": hosts[0]}


@router.post("/opensearch/test")
async def test_opensearch(request: Request):
    """Test OpenSearch connection."""
    settings = _settings(request)

    # Allow testing with ad-hoc connection info from request body
    try:
        body = await request.json()
    except Exception:
        body = {}
    hosts = body.get("hosts") or settings.opensearch.hosts
    username = body.get("username") or settings.opensearch.username
    password = body.get("password") or settings.opensearch.password

    if not hosts:
        return JSONResponse({"connected": False, "error": "No OpenSearch hosts configured"}, status_code=400)

    from glogarch.core.config import OpenSearchConfig
    from glogarch.opensearch.client import OpenSearchClient

    test_config = OpenSearchConfig(
        hosts=hosts if isinstance(hosts, list) else [hosts],
        username=username,
        password=password,
        verify_ssl=settings.opensearch.verify_ssl,
    )

    async with OpenSearchClient(test_config) as client:
        result = await client.test_connection()
    return result


# --- Notifications ---

@router.get("/notify/status")
def notify_status(request: Request):
    """Get notification channel status."""
    settings = _settings(request)
    n = settings.notify
    channels = []
    if n.telegram.enabled:
        channels.append({"name": "telegram", "enabled": True})
    if n.discord.enabled:
        channels.append({"name": "discord", "enabled": True})
    if n.slack.enabled:
        channels.append({"name": "slack", "enabled": True})
    if n.teams.enabled:
        channels.append({"name": "teams", "enabled": True})
    if n.nextcloud_talk.enabled:
        channels.append({"name": "nextcloud_talk", "enabled": True})
    return {
        "channels": channels,
        "on_export_complete": n.on_export_complete,
        "on_import_complete": n.on_import_complete,
        "on_cleanup_complete": n.on_cleanup_complete,
        "on_error": n.on_error,
        "on_verify_failed": n.on_verify_failed,
    }


@router.post("/notify/test")
async def test_notify(request: Request):
    """Send a test notification to all enabled channels (skips event type check)."""
    from glogarch.notify.sender import _has_any_channel, _send_telegram, _send_discord, _send_slack, _send_teams, _send_nextcloud_talk, _send_email
    import httpx
    settings = _settings(request)
    config = settings.notify

    if not _has_any_channel(config):
        return {"results": [], "message": "No notification channels enabled"}

    results = []
    from datetime import timezone, timedelta as _td
    local_tz = timezone(_td(hours=8))  # Asia/Taipei
    timestamp = datetime.now(local_tz).strftime("%Y-%m-%d %H:%M:%S %z")
    # Use notification language from config
    if config.language == "zh-TW":
        title = "測試通知"
        body = "這是一則來自 jt-glogarch 的測試通知。"
    else:
        title = "Test Notification"
        body = "This is a test notification from jt-glogarch."
    full_msg = f"[jt-glogarch] {title}\n{body}\n{timestamp}"

    async with httpx.AsyncClient(timeout=15) as client:
        if config.telegram.enabled:
            results.append(await _send_telegram(client, config.telegram, full_msg))
        if config.discord.enabled:
            results.append(await _send_discord(client, config.discord, full_msg))
        if config.slack.enabled:
            results.append(await _send_slack(client, config.slack, full_msg))
        if config.teams.enabled:
            results.append(await _send_teams(client, config.teams, full_msg))
        if config.nextcloud_talk.enabled:
            results.append(await _send_nextcloud_talk(client, config.nextcloud_talk, full_msg))
    if config.email.enabled:
        results.append(await _send_email(config.email, full_msg))

    return {"results": results}


# --- Logs ---

@router.get("/logs/realtime")
def get_realtime_log(request: Request, lines: int = 100):
    """Get recent journalctl log lines."""
    import subprocess
    try:
        result = subprocess.run(
            ["journalctl", "-u", "glogarch", "-n", str(min(lines, 1000)), "--no-pager"],
            capture_output=True, text=True, timeout=5,
        )
        return {"lines": result.stdout}
    except Exception as e:
        return {"lines": f"Error reading log: {e}"}


@router.get("/logs/history")
def get_operation_history(request: Request, limit: int = 100):
    """Get operation history from jobs table."""
    db = _db(request)
    jobs = db.list_jobs(limit=limit)
    return {"items": [_job_to_dict(j) for j in jobs]}


@router.get("/logs/audit")
def get_audit_log(request: Request, limit: int = 200):
    """Get audit log entries."""
    db = _db(request)
    entries = db.list_audit(limit=limit)
    return {"items": entries}


# --- Notification Settings ---

@router.get("/notify/config")
def get_notify_config(request: Request):
    """Get full notification config for the settings form."""
    settings = _settings(request)
    n = settings.notify
    return {
        "language": n.language,
        "on_export_complete": n.on_export_complete,
        "on_import_complete": n.on_import_complete,
        "on_cleanup_complete": n.on_cleanup_complete,
        "on_error": n.on_error,
        "on_verify_failed": n.on_verify_failed,
        "telegram": {"enabled": n.telegram.enabled, "bot_token": n.telegram.bot_token, "chat_id": n.telegram.chat_id},
        "discord": {"enabled": n.discord.enabled, "webhook_url": n.discord.webhook_url},
        "slack": {"enabled": n.slack.enabled, "webhook_url": n.slack.webhook_url},
        "teams": {"enabled": n.teams.enabled, "webhook_url": n.teams.webhook_url},
        "nextcloud_talk": {"enabled": n.nextcloud_talk.enabled, "server_url": n.nextcloud_talk.server_url,
                           "token": n.nextcloud_talk.token, "username": n.nextcloud_talk.username, "password": n.nextcloud_talk.password},
        "email": {"enabled": n.email.enabled, "smtp_host": n.email.smtp_host, "smtp_port": n.email.smtp_port,
                  "smtp_tls": n.email.smtp_tls, "smtp_user": n.email.smtp_user, "smtp_password": n.email.smtp_password,
                  "from_addr": n.email.from_addr, "to_addrs": n.email.to_addrs, "subject_prefix": n.email.subject_prefix},
    }


@router.post("/notify/config")
async def save_notify_config(request: Request):
    """Save notification config to config.yaml."""
    body = await request.json()
    settings = _settings(request)
    import yaml

    # Update in-memory
    n = settings.notify
    for key in ("on_export_complete", "on_import_complete", "on_cleanup_complete", "on_error", "on_verify_failed"):
        if key in body:
            setattr(n, key, body[key])

    channel_map = {
        "telegram": n.telegram, "discord": n.discord, "slack": n.slack,
        "teams": n.teams, "nextcloud_talk": n.nextcloud_talk, "email": n.email,
    }
    for ch_name, ch_obj in channel_map.items():
        if ch_name in body:
            ch_data = body[ch_name]
            for k, v in ch_data.items():
                if hasattr(ch_obj, k):
                    setattr(ch_obj, k, v)

    # Save to config.yaml
    config_path = _config_path(request)
    if config_path.exists():
        with open(config_path) as f:
            cfg = yaml.safe_load(f) or {}
        cfg["notify"] = body
        with open(config_path, "w") as f:
            yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True)

    _audit(request, "notify_config_saved", "Notification settings updated")
    return {"status": "saved"}


# --- Helpers ---

def _parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _archive_to_dict(a) -> dict:
    return {
        "id": a.id,
        "server_name": a.server_name,
        "stream_id": a.stream_id,
        "stream_name": a.stream_name,
        "time_from": a.time_from.isoformat() if a.time_from else None,
        "time_to": a.time_to.isoformat() if a.time_to else None,
        "file_path": a.file_path,
        "file_size_bytes": a.file_size_bytes,
        "original_size_bytes": a.original_size_bytes,
        "message_count": a.message_count,
        "part_number": a.part_number,
        "total_parts": a.total_parts,
        "checksum_sha256": a.checksum_sha256,
        "status": a.status.value,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


def _job_to_dict(j) -> dict:
    d = {
        "id": j.id,
        "job_type": j.job_type.value if hasattr(j.job_type, "value") else j.job_type,
        "status": j.status.value,
        "progress_pct": j.progress_pct,
        "messages_done": j.messages_done,
        "messages_total": j.messages_total,
        "error_message": j.error_message,
        "source": getattr(j, "source", "") or "",
        "started_at": j.started_at.isoformat() if j.started_at else None,
        "completed_at": j.completed_at.isoformat() if j.completed_at else None,
        "phase": "",
        "current_detail": "",
    }
    # Enrich with live progress info from in-memory store
    if j.id in _job_progress and _job_progress[j.id]:
        last = _job_progress[j.id][-1]
        d["phase"] = last.get("phase", "")
        idx_name = last.get("index", "")
        chunk = last.get("chunk_index")
        total = last.get("total_chunks")
        if idx_name:
            d["current_detail"] = f"{idx_name}"
        elif chunk and total:
            d["current_detail"] = f"chunk {chunk}/{total}"
        # Use live progress if more up-to-date
        live_done = last.get("messages_done", 0)
        live_pct = last.get("pct", 0)
        if live_done > d["messages_done"]:
            d["messages_done"] = live_done
            d["progress_pct"] = live_pct
        if last.get("messages_total"):
            d["messages_total"] = last["messages_total"]
    return d


def _schedule_to_dict(s) -> dict:
    import json as _json
    config = {}
    if s.config_json:
        try:
            config = _json.loads(s.config_json)
        except Exception:
            pass
    return {
        "id": s.id,
        "name": s.name,
        "job_type": s.job_type,
        "cron_expr": s.cron_expr,
        "enabled": s.enabled,
        "config": config,
        "last_run_at": s.last_run_at.isoformat() if s.last_run_at else None,
        "next_run_at": s.next_run_at.isoformat() if s.next_run_at else None,
    }
