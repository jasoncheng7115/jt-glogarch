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
from glogarch.export.exporter import Exporter, normalize_index_set_ids
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


def _apply_to_runtime(request: Request, sched) -> None:
    """Push a saved/toggled schedule into the running APScheduler so it takes
    effect without a service restart."""
    arch_sched = getattr(request.app.state, "scheduler", None)
    if arch_sched is None:
        return
    try:
        arch_sched.apply_schedule(sched)
    except Exception as e:
        log.warning("Failed to apply schedule to runtime",
                    name=sched.name, error=str(e))

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


@router.get("/archives/ids")
def list_archive_ids(
    request: Request,
    server: str | None = None,
    stream: str | None = None,
    time_from: str | None = None,
    time_to: str | None = None,
    status: str | None = None,
):
    """Return just the IDs of every archive matching the filter — for the
    cross-page "select all matching" action, so the UI can select thousands of
    archives across pages in ONE request instead of walking every page. Uses the
    exact same filter as GET /archives (server / stream / time range)."""
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
    )
    ids = [a.id for a in archives if a.id is not None]
    return {"ids": ids, "total": len(ids)}


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

    # Validate provided timestamps (OWASP A10): a malformed date must yield a
    # clean 400, not silently become None and start a broken job.
    time_to = datetime.utcnow()
    if body.get("time_to"):
        time_to = _parse_dt(body["time_to"])
        if time_to is None:
            return JSONResponse({"error": "Invalid time_to format"}, status_code=400)
    if days:
        from datetime import timedelta
        try:
            time_from = time_to - timedelta(days=int(days))
        except (TypeError, ValueError):
            return JSONResponse({"error": "Invalid days value"}, status_code=400)
    elif body.get("time_from"):
        time_from = _parse_dt(body["time_from"])
        if time_from is None:
            return JSONResponse({"error": "Invalid time_from format"}, status_code=400)
    else:
        return JSONResponse({"error": "Must specify time_from or days"}, status_code=400)

    # Clean up old progress entries + cancel flags (keep last 50)
    if len(_job_progress) > 50:
        oldest_keys = sorted(_job_progress.keys())[:len(_job_progress) - 50]
        for k in oldest_keys:
            _job_progress.pop(k, None)
            _cancel_flags.pop(k, None)

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

        os_config = settings.get_opensearch(server_name)
        if not os_config.hosts:
            return JSONResponse({"error": "OpenSearch not configured"}, status_code=400)

        os_exporter = OpenSearchExporter(
            server_config, os_config, settings.export,
            settings.rate_limit, db, integrity=settings.integrity,
        )
        # OpenSearch: no resume point — rely on per-chunk dedup to avoid gaps

        def _run_in_thread():
            try:
                result = asyncio.run(os_exporter.export(
                    time_from=time_from, time_to=time_to,
                    index_set_ids=normalize_index_set_ids(index_set, settings.export.index_sets),
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
        exporter = Exporter(server_config, settings.export, settings.rate_limit, db, integrity=settings.integrity)

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

    # Fall back to the pre-configured restore-target defaults when a field is
    # empty or still holds the masked placeholder ("***") that the settings
    # auto-fill puts in the secret inputs. This lets the operator save the
    # target once (in 系統設定) and not retype the URL/token every import.
    _ic = settings.import_config
    if not target_api_url:
        target_api_url = (_ic.target_api_url or "").strip()
    if (not target_api_token) or ("***" in target_api_token):
        target_api_token = (_ic.target_api_token or "").strip()
    if (not target_api_password) or ("***" in target_api_password):
        target_api_password = _ic.target_api_password or ""
    if not target_api_username:
        target_api_username = (_ic.target_api_username or "").strip()

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
            batch_docs=int(body.get("batch_docs", 10000)),
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

    # Retry params persisted on the job (NEVER secrets) so a failed import can be
    # re-run with one click. Secrets are re-read from the stored import defaults.
    retry_config = {
        "archive_ids": archive_ids,
        "mode": import_mode,
        "target_api_url": target_api_url,
        "gelf_host": body.get("gelf_host") or "",
        "gelf_port": body.get("gelf_port") or "",
        "gelf_protocol": body.get("gelf_protocol") or "",
        "target_server": target,
    }

    job_id = str(uuid.uuid4())
    _job_progress[job_id] = []

    # Clean up old progress entries + cancel flags (keep last 50)
    if len(_job_progress) > 50:
        oldest_keys = sorted(_job_progress.keys())[:len(_job_progress) - 50]
        for k in oldest_keys:
            _job_progress.pop(k, None)
            _cancel_flags.pop(k, None)

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
            # Keep only the last ~100 progress events (like the export path) — a
            # multi-million-record import fires per batch and this list would grow
            # unbounded in memory otherwise.
            events = _job_progress.setdefault(job_id, [])
            if len(events) > 100:
                events = _job_progress[job_id] = events[-50:]
            events.append(info)

        try:
            asyncio.run(importer.import_archives(
                archive_ids=archive_ids,
                target_server=target,
                progress_callback=_cb,
                job_id=job_id,
                flow_control=fc,
                job_config=retry_config,
                ignore_capacity=bool(body.get("ignore_capacity")),
                estimated_indices=int(body.get("estimated_indices") or 0),
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


@router.post("/import/capacity-estimate")
async def import_capacity_estimate(request: Request):
    """Estimate — BEFORE the import starts — whether the target index set's
    rotation + retention can hold this batch, so the operator can raise
    max_number_of_indices first instead of discovering mid-import that retention
    will delete the freshly-imported data."""
    from glogarch.import_.preflight import PreflightChecker
    from glogarch.utils.netguard import ssrf_block_reason
    from glogarch.core.config_writer import reconcile_secret
    from glogarch.utils.sanitize import sanitize

    body = await request.json()
    settings = _settings(request)
    db = _db(request)
    ids = body.get("archive_ids") or []
    if not ids:
        return JSONResponse({"error": "archive_ids required"}, status_code=400)

    total_messages = 0
    total_bytes = 0
    for aid in ids:
        rec = db.get_archive(aid)
        if rec:
            total_messages += rec.message_count or 0
            # index size tracks the ORIGINAL (uncompressed) volume, not the gz file
            total_bytes += (rec.original_size_bytes or rec.file_size_bytes or 0)

    ic = settings.import_config
    url = (body.get("target_api_url") or "").strip() or (ic.target_api_url or "")
    if not url:
        return JSONResponse({"error": "target_api_url required"}, status_code=400)
    reason = ssrf_block_reason(url)
    if reason:
        return JSONResponse({"error": reason}, status_code=400)
    token = reconcile_secret(body.get("target_api_token"), ic.target_api_token) or ""
    user = (body.get("target_api_username") or "").strip() or (ic.target_api_username or "")
    pw = reconcile_secret(body.get("target_api_password"), ic.target_api_password) or ""
    if not token and not (user and pw):
        return JSONResponse({"error": "Provide a token or username + password"}, status_code=400)

    pf = PreflightChecker(api_url=url, api_token=token, api_username=user,
                          api_password=pw, verify_ssl=False)
    try:
        idx_id, idx_title = await pf.find_target_index_set()
        async with pf._client() as c:
            r = await c.get(f"{pf.api_url}/api/system/indices/index_sets/{idx_id}")
            iset = r.json() if r.status_code == 200 else {}
        estimated, warnings = await pf.check_capacity(idx_id, total_messages, total_bytes)
    except Exception as e:
        return JSONResponse({"error": sanitize(str(e))}, status_code=500)

    def _short(c: str) -> str:
        return c.rsplit(".", 1)[-1].replace("Strategy", "").replace("Config", "") if c else "?"

    ret = iset.get("retention_strategy", {}) or {}
    rot = iset.get("rotation_strategy", {}) or {}
    ret_class = iset.get("retention_strategy_class", "") or ""
    rot_class = iset.get("rotation_strategy_class", "") or ""
    max_indices = int(ret.get("max_number_of_indices", 0)) if "Deletion" in ret_class else 0
    insufficient = any("Retention will delete" in w for w in warnings)

    # --- Read the ACTUAL OpenSearch data-path disk and compute the max index
    # retention that fits within 80% of it. The disk may be plenty while
    # max_number_of_indices is set too low — so recommend the safe number. ---
    per_index_bytes = int(rot.get("max_size", 0)) if "SizeBased" in rot_class else 0
    if per_index_bytes == 0 and estimated > 0:
        per_index_bytes = total_bytes // estimated  # MessageCount/time: derive avg
    replicas = int(iset.get("replicas", 0) or 0)
    # Resolve the OpenSearch to measure. CRITICAL: prefer the IMPORT TARGET's own
    # OpenSearch (the disk the imported data will actually land on) — NOT
    # jt-glogarch's globally-configured OS, which is often a DIFFERENT cluster
    # (e.g. production). Order: explicit target_os_url → auto-detect from the
    # target Graylog host → the app's global OS (last resort).
    os_cfg = settings.get_opensearch()
    body_os = (body.get("target_os_url") or "").strip()
    if body_os:
        os_hosts = [body_os]
    else:
        auto = await pf.auto_detect_opensearch_url()
        os_hosts = [auto] if auto else list(os_cfg.hosts or [])
    # Try the app's OS creds first, then the target Graylog creds (co-located
    # setups often share admin creds; OS may also be open).
    disk = await _query_os_data_disk(os_hosts, os_cfg.username, os_cfg.password, os_cfg.verify_ssl)
    if not disk:
        disk = await _query_os_data_disk(os_hosts, user, pw, False)
    disk_total = disk[0] if disk else 0
    disk_avail = disk[1] if disk else 0
    disk_host = (disk[2] if disk else "")
    disk_paths = (disk[3] if disk else [])

    # Measure REAL indexed size/doc from the target's existing indices so the
    # estimate reflects OpenSearch on-disk size, not raw JSON size (they differ:
    # _source is compressed but the inverted index + doc_values add overhead;
    # the ratio is data-dependent, so measure it from the customer's own data).
    prefix = iset.get("index_prefix", "") or ""
    bytes_per_doc = 0.0
    measure_scope = ""
    if os_hosts:
        bpd = await _measure_bytes_per_doc(os_hosts, os_cfg.username, os_cfg.password,
                                           os_cfg.verify_ssl, prefix)
        if bpd:
            bytes_per_doc, measure_scope = bpd
    indexed_bytes_est = int(total_messages * bytes_per_doc) if bytes_per_doc else 0
    json_to_index_ratio = (indexed_bytes_est / total_bytes) if (indexed_bytes_est and total_bytes) else None
    # For SizeBased rotation, recompute the index count from the ACTUAL indexed
    # size (max_size is an on-disk primary threshold, so raw JSON ÷ max_size was
    # comparing different units).
    if indexed_bytes_est and "SizeBased" in rot_class and per_index_bytes:
        estimated = max(1, -(-indexed_bytes_est // per_index_bytes))  # ceil

    per_index_on_disk = per_index_bytes * (1 + replicas)
    rec_max_indices = 0
    if disk_total > 0 and per_index_on_disk > 0:
        rec_max_indices = int((disk_total * 0.8) // per_index_on_disk)

    return {
        "total_messages": total_messages,
        "total_bytes": total_bytes,
        "index_set_id": idx_id,
        "index_set_title": idx_title,
        "rotation": _short(rot_class),
        "retention": _short(ret_class),
        "max_indices": max_indices,
        "estimated_indices": estimated,
        "sufficient": not insufficient,
        "warnings": warnings,
        # disk-aware sizing
        "os_disk_reachable": bool(disk),
        "os_disk_total_bytes": disk_total,
        "os_disk_avail_bytes": disk_avail,
        "os_disk_host": disk_host,
        "os_disk_paths": disk_paths,
        "per_index_bytes": per_index_bytes,
        "replicas": replicas,
        "recommended_max_indices": rec_max_indices,
        # what to set: enough for this import, but no more than 80%-disk allows
        "suggested_setting": (min(estimated, rec_max_indices) if rec_max_indices else estimated),
        "disk_fits": (rec_max_indices >= estimated) if rec_max_indices else None,
        # measured JSON→index sizing
        "bytes_per_doc": round(bytes_per_doc, 1),
        "measure_scope": measure_scope,
        "indexed_bytes_est": indexed_bytes_est,
        "json_to_index_ratio": round(json_to_index_ratio, 3) if json_to_index_ratio else None,
    }


async def _measure_bytes_per_doc(hosts, user, pw, verify, prefix):
    """Measure REAL indexed bytes-per-document (primary store size ÷ doc count) —
    the accurate proxy for OpenSearch on-disk size vs the raw archive JSON.

    Prefers the TARGET index set's own indices (most representative). If that set
    is empty (a fresh restore target — "currently has 0 indices"), falls back to
    the WHOLE cluster's existing data so the estimate is still measured, not a raw
    JSON guess. Returns (bytes_per_doc, scope) or None."""
    import httpx as _httpx
    auth = _httpx.BasicAuth(user, pw) if user else None
    # 1) the target index set's own indices (most representative)
    if prefix:
        for h in (hosts or []):
            try:
                async with _httpx.AsyncClient(verify=verify, timeout=10.0) as c:
                    r = await c.get(f"{h.rstrip('/')}/{prefix}*/_stats/store,docs",
                                    auth=auth, headers={"Accept": "application/json"})
                    if r.status_code == 200:
                        pri = ((r.json().get("_all") or {}).get("primaries") or {})
                        store = int((pri.get("store") or {}).get("size_in_bytes") or 0)
                        docs = int((pri.get("docs") or {}).get("count") or 0)
                        if store > 0 and docs > 0:
                            return store / docs, "index-set"
            except Exception:
                pass
    # 2) fallback: the DOMINANT log data across the cluster. Use _cat/indices and
    # EXCLUDE system/plugin indices (dot-prefixed, or top_queries/gl-events/…) —
    # those have few docs but large ones and badly skew a cluster-wide _all ratio.
    _SYS = ("top_queries", "gl-events", "gl-system-events", "gl_system_events")
    for h in (hosts or []):
        try:
            async with _httpx.AsyncClient(verify=verify, timeout=10.0) as c:
                r = await c.get(f"{h.rstrip('/')}/_cat/indices",
                                params={"h": "index,docs.count,pri.store.size", "bytes": "b",
                                        "format": "json"},
                                auth=auth, headers={"Accept": "application/json"})
                if r.status_code != 200:
                    continue
                store = docs = 0
                for row in r.json():
                    name = row.get("index", "")
                    if name.startswith(".") or any(name.startswith(s) for s in _SYS):
                        continue
                    dc = int(row.get("docs.count") or 0)
                    sz = int(row.get("pri.store.size") or 0)
                    if dc > 0:
                        docs += dc
                        store += sz
                if store > 0 and docs > 0:
                    return store / docs, "log-data"
        except Exception:
            continue
    return None


async def _query_os_data_disk(hosts, user, pw, verify):
    """Return (total_bytes, available_bytes, host, data_paths) of the OpenSearch
    DATA path across data nodes via _nodes/stats/fs, or None if unreachable. The
    host + data paths are returned so the UI can show WHICH disk was measured
    (avoids silently reading the wrong cluster)."""
    import httpx as _httpx
    auth = _httpx.BasicAuth(user, pw) if user else None
    for h in (hosts or []):
        try:
            async with _httpx.AsyncClient(verify=verify, timeout=8.0) as c:
                r = await c.get(f"{h.rstrip('/')}/_nodes/stats/fs", auth=auth,
                                headers={"Accept": "application/json"})
                if r.status_code != 200:
                    continue
                data = r.json()
                total = avail = 0
                paths = set()
                for _nid, n in (data.get("nodes") or {}).items():
                    fs = n.get("fs") or {}
                    fs_total = fs.get("total") or {}
                    total += int(fs_total.get("total_in_bytes") or 0)
                    avail += int(fs_total.get("available_in_bytes") or 0)
                    for d in (fs.get("data") or []):
                        p = d.get("path") or d.get("mount")
                        if p:
                            paths.add(p)
                if total > 0:
                    return total, avail, h, sorted(paths)
        except Exception:
            continue
    return None


@router.post("/import/set-retention")
async def import_set_retention(request: Request):
    """One-click SOP action: raise the target index set's
    max_number_of_indices (Deletion retention) to the given value, so retention
    won't delete freshly-imported data. NEVER lowers below the current value."""
    from glogarch.import_.preflight import PreflightChecker
    from glogarch.utils.netguard import ssrf_block_reason
    from glogarch.core.config_writer import reconcile_secret
    from glogarch.utils.sanitize import sanitize
    import httpx as _httpx
    import json

    body = await request.json()
    settings = _settings(request)
    ic = settings.import_config
    idx_id = (body.get("index_set_id") or "").strip()
    new_max = int(body.get("max_number_of_indices") or 0)
    if not idx_id or new_max <= 0:
        return JSONResponse({"error": "index_set_id and max_number_of_indices required"}, status_code=400)
    url = (body.get("target_api_url") or "").strip() or (ic.target_api_url or "")
    reason = ssrf_block_reason(url) if url else "target_api_url required"
    if reason:
        return JSONResponse({"error": reason}, status_code=400)
    token = reconcile_secret(body.get("target_api_token"), ic.target_api_token) or ""
    user = (body.get("target_api_username") or "").strip() or (ic.target_api_username or "")
    pw = reconcile_secret(body.get("target_api_password"), ic.target_api_password) or ""
    auth = _httpx.BasicAuth(token, "token") if token else _httpx.BasicAuth(user, pw)
    try:
        async with _httpx.AsyncClient(verify=False, timeout=20,
                headers={"X-Requested-By": "jt-glogarch", "Content-Type": "application/json"}) as c:
            r = await c.get(f"{url.rstrip('/')}/api/system/indices/index_sets/{idx_id}", auth=auth)
            if r.status_code != 200:
                return JSONResponse({"error": f"Cannot read index set: HTTP {r.status_code}"}, status_code=400)
            iset = r.json()
            ret = iset.get("retention_strategy", {}) or {}
            cur = int(ret.get("max_number_of_indices", 0))
            if new_max <= cur:
                return {"ok": True, "unchanged": True, "current": cur,
                        "message": f"max_number_of_indices already {cur} (>= {new_max})"}
            ret["max_number_of_indices"] = new_max
            iset["retention_strategy"] = ret
            r2 = await c.put(f"{url.rstrip('/')}/api/system/indices/index_sets/{idx_id}",
                             content=json.dumps(iset))
            if r2.status_code not in (200, 201):
                return JSONResponse({"error": f"Update failed: HTTP {r2.status_code}: {r2.text[:200]}"},
                                    status_code=400)
    except Exception as e:
        return JSONResponse({"error": sanitize(str(e))}, status_code=500)
    _audit(request, "index_set_retention_changed", f"idx={idx_id} max_indices {cur}->{new_max}")
    return {"ok": True, "previous": cur, "new": new_max}


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
        "heap_percent": js.heap_percent if js else None,
        "buffer_output_pct": js.buffer_output_pct if js else None,
        "buffer_process_pct": js.buffer_process_pct if js else None,
        "mem_available_mb": round(fc.mem_available_mb) if fc.mem_available_mb is not None else None,
        "journal": {
            "uncommitted": js.uncommitted if js else None,
            "size_bytes": js.size_bytes if js else None,
            "disk_free_bytes": js.disk_free_bytes if js else None,
            "available": js.available if js else False,
            "error": js.error if js else "",
            "heap_percent": js.heap_percent if js else None,
        } if js else None,
    }


# --- Cleanup ---

@router.post("/cleanup")
def trigger_cleanup(request: Request, days: int | None = None, dry_run: bool = False):
    settings = _settings(request)
    db = _db(request)
    cleaner = Cleaner(settings.retention, settings.export, db, settings.op_audit)
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
    verifier = Verifier(settings.export, db, integrity=settings.integrity)
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
    db = _db(request)

    # In-memory progress is the right answer ONLY while the job is still
    # actively producing events. Once it has finished (phase=done/error or
    # pct>=100), we MUST read from the DB so the caller sees the real
    # error_message column (which carries informational notices like the
    # bulk-mode "where to find your data" hint, not just errors). The old
    # behaviour returned `last.get("error")` — null on success — which
    # silently swallowed the where_msg notice.
    if job_id in _job_progress:
        events = _job_progress[job_id]
        if events:
            last = events[-1]
            is_done = last.get("phase") in ("error", "done") or last.get("pct", 0) >= 100
            if is_done:
                db_job = db.get_job(job_id)
                if db_job:
                    return _job_to_dict(db_job)
                # DB row not yet flushed → fall through to in-memory
            # Look up real job_type from DB if possible — in-memory progress
            # events don't carry it, so the old code hardcoded "export"
            # which mislabelled imports in the UI.
            db_job = db.get_job(job_id)
            jt = db_job.job_type.value if db_job else "export"
            return {
                "id": job_id,
                "job_type": jt,
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
    job = db.get_job(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)
    return _job_to_dict(job)


@router.post("/jobs/{job_id}/cancel")
def cancel_job(request: Request, job_id: str):
    """Cancel a running job."""
    # Set cancellation flag for background task (works for both in-memory and DB jobs)
    _cancel_flags[job_id] = True

    # Active import jobs use ImportFlowControl.cancelled (NOT _cancel_flags)
    # for their cancel checkpoint — the bulk loop reads fc.cancelled between
    # batches. Trigger it here so cancel actually stops bulk imports mid-flight.
    try:
        from glogarch.import_.importer import get_import_control
        ifc = get_import_control(job_id)
        if ifc:
            ifc.cancel()
    except Exception:
        pass

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
    """SSE endpoint for real-time job progress.

    A backpressure pause (target Graylog output buffer full / journal climbing)
    can legitimately stall message progress for many minutes while the importer
    waits for the buffer to drain — during that window NO new progress event is
    appended. The old code declared a fake ``SSE timeout`` after 10 min of that,
    surfacing a *running* import as a red error. Instead we now emit a periodic
    heartbeat so the stream never idles into a false failure, and only END the
    stream with the job's REAL status (from the in-memory final event, or the DB
    once the job has left memory) — never a synthetic error.
    """
    async def event_generator():
        import json as _json
        last_idx = 0
        idle = 0.0
        HEARTBEAT = 10.0  # keepalive cadence while progress is stalled (paused)
        while True:
            if await request.is_disconnected():
                return
            events = _job_progress.get(job_id, [])
            new = False
            while last_idx < len(events):
                evt = events[last_idx]
                last_idx += 1
                new = True
                yield {"event": "progress", "data": _json.dumps(evt)}
                if evt.get("pct", 0) >= 100 or evt.get("phase") in ("error", "done"):
                    yield {"event": "done", "data": _json.dumps(evt)}
                    return
            if new:
                idle = 0.0
                continue
            await asyncio.sleep(0.5)
            idle += 0.5
            if idle >= HEARTBEAT:
                idle = 0.0
                # If the job has left the in-memory buffer, the run is over — emit
                # the DB's terminal status and stop. Otherwise it's still running
                # (possibly paused on backpressure): send a heartbeat and wait.
                if job_id not in _job_progress:
                    try:
                        job = _db(request).get_job(job_id)
                    except Exception:
                        job = None
                    if job and job.status.value in ("completed", "failed", "cancelled"):
                        yield {"event": "done", "data": _json.dumps(
                            {"phase": job.status.value, "pct": 100})}
                        return
                yield {"event": "heartbeat", "data": _json.dumps({"phase": "heartbeat"})}

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
    elif body.get("job_type") == "report_cleanup":
        config_data = {"days": int(body.get("days", 720) or 720)}
    sched = ScheduleRecord(
        name=body["name"],
        job_type=body.get("job_type", "export"),
        cron_expr=body["cron_expr"],
        config_json=_json.dumps(config_data) if config_data else None,
        enabled=body.get("enabled", True),
    )
    db.save_schedule(sched)
    _apply_to_runtime(request, sched)
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
    _apply_to_runtime(request, s)

    # For auto-* schedules, also update config.yaml
    if name.startswith("auto-"):
        from glogarch.core.config_writer import update_config
        config_path = _config_path(request)
        if config_path.exists():
            try:
                def _mut(cfg):
                    sch = cfg.setdefault("schedule", {})
                    if name == "auto-export":
                        sch["export_cron"] = s.cron_expr if enabled else None
                    elif name == "auto-cleanup":
                        sch["cleanup_cron"] = s.cron_expr if enabled else None
                update_config(config_path, _mut)
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
        from glogarch.core.models import JobRecord, JobStatus, JobType
        from glogarch.utils.sanitize import sanitize as _sanitize
        job_id = str(uuid.uuid4())
        try:
            db.create_job(JobRecord(id=job_id, job_type=JobType.CLEANUP,
                                     status=JobStatus.RUNNING,
                                     source=f"manual:cleanup:{name}",
                                     started_at=datetime.utcnow()))
        except Exception:
            job_id = ""
        cleaner = Cleaner(settings.retention, settings.export, db, settings.op_audit)
        try:
            result = cleaner.cleanup()
            mb = result.bytes_freed / (1024 * 1024)
            if job_id:
                try:
                    db.update_job(job_id, status=JobStatus.COMPLETED,
                                  messages_done=result.files_deleted,
                                  messages_total=result.files_deleted,
                                  progress_pct=100.0,
                                  completed_at=datetime.utcnow(),
                                  error_message=f"Deleted {result.files_deleted} files ({mb:.1f} MB)")
                except Exception:
                    pass
        except Exception as e:
            if job_id:
                try:
                    db.update_job(job_id, status=JobStatus.FAILED,
                                  error_message=_sanitize(str(e)),
                                  completed_at=datetime.utcnow())
                except Exception:
                    pass
            raise
        db.update_schedule_last_run(name)
        _audit(request, "schedule_run_now", f"{name} cleanup deleted={result.files_deleted}")
        return {"status": "completed", "files_deleted": result.files_deleted, "bytes_freed": result.bytes_freed}

    # Verify: run synchronously
    if sched.job_type == "verify":
        from glogarch.verify.verifier import Verifier
        from glogarch.core.models import JobRecord, JobStatus, JobType
        from glogarch.utils.sanitize import sanitize as _sanitize
        job_id = str(uuid.uuid4())
        try:
            db.create_job(JobRecord(id=job_id, job_type=JobType.VERIFY,
                                     status=JobStatus.RUNNING,
                                     source=f"manual:verify:{name}",
                                     started_at=datetime.utcnow()))
        except Exception:
            job_id = ""
        verifier = Verifier(settings.export, db, integrity=settings.integrity)
        try:
            result = verifier.verify_all()
            note = (f"{result.valid} valid, {len(result.corrupted)} corrupted, "
                    f"{len(result.missing_files)} missing of {result.total_checked} total")
            status = (JobStatus.FAILED
                      if result.corrupted or result.missing_files
                      else JobStatus.COMPLETED)
            if job_id:
                try:
                    db.update_job(job_id, status=status,
                                  messages_done=result.total_checked,
                                  messages_total=result.total_checked,
                                  progress_pct=100.0,
                                  completed_at=datetime.utcnow(),
                                  error_message=note)
                except Exception:
                    pass
        except Exception as e:
            if job_id:
                try:
                    db.update_job(job_id, status=JobStatus.FAILED,
                                  error_message=_sanitize(str(e)),
                                  completed_at=datetime.utcnow())
                except Exception:
                    pass
            raise
        db.update_schedule_last_run(name)
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

    os_config = settings.get_opensearch(cfg.get("server"))
    if export_mode == "opensearch" and os_config.hosts:
        from glogarch.opensearch.exporter import OpenSearchExporter
        os_exporter = OpenSearchExporter(
            server_config, os_config, settings.export,
            settings.rate_limit, db, integrity=settings.integrity,
        )
        # OpenSearch mode: do NOT use resume point to skip indices.
        # Rely on per-chunk dedup instead, to avoid missing gaps.

        def _run_in_thread():
            try:
                result = asyncio.run(os_exporter.export(
                    time_from=time_from, time_to=time_to,
                    index_set_ids=normalize_index_set_ids(index_set, settings.export.index_sets),
                    progress_callback=_cb, source=f"manual:opensearch:{name}",
                    job_id=job_id, keep_indices=int(keep_indices) if keep_indices else None,
                ))
                _job_progress.setdefault(job_id, []).append(
                    {"phase": "done", "pct": 100, "messages_done": result.messages_total, "messages_total": result.messages_total}
                )
            except Exception as e:
                _job_progress.setdefault(job_id, []).append(
                    {"phase": "error", "error": str(e), "pct": 100}
                )
            finally:
                try:
                    db.update_schedule_last_run(name)
                except Exception:
                    pass
    else:
        exporter = Exporter(server_config, settings.export, settings.rate_limit, db, integrity=settings.integrity)
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
                    streams=stream_ids, progress_callback=_cb, source=f"manual:api:{name}",
                    job_id=job_id,
                ))
                _job_progress.setdefault(job_id, []).append(
                    {"phase": "done", "pct": 100, "messages_done": result.messages_total, "messages_total": result.messages_total}
                )
            except Exception as e:
                _job_progress.setdefault(job_id, []).append(
                    {"phase": "error", "error": str(e), "pct": 100}
                )
            finally:
                try:
                    db.update_schedule_last_run(name)
                except Exception:
                    pass

    asyncio.get_event_loop().run_in_executor(None, _run_in_thread)
    _audit(request, "schedule_run_now", f"{name} mode={export_mode} job={job_id}")
    return {"job_id": job_id, "status": "started", "mode": export_mode}


@router.delete("/schedules/{name}")
def delete_schedule(request: Request, name: str):
    db = _db(request)
    db.delete_schedule(name)
    arch_sched = getattr(request.app.state, "scheduler", None)
    if arch_sched is not None:
        try:
            arch_sched.remove_schedule(name)
        except Exception as e:
            log.warning("Failed to remove schedule from runtime",
                        name=name, error=str(e))
    return {"status": "deleted", "name": name}


# --- Status ---

@router.get("/health")
def get_health(request: Request):
    """Lightweight liveness/readiness probe for monitoring tools.

    Returns 200 + JSON when DB is reachable, archive disk is writable, and
    free space is above the configured min. Returns 503 otherwise. Designed
    to be polled by external healthchecks (Prometheus blackbox, k8s probes,
    Uptime Kuma, etc.).
    """
    import shutil as _sh
    from pathlib import Path as _P
    settings = _settings(request)
    db = _db(request)
    issues: list[str] = []

    # DB ping
    try:
        db.conn.execute("SELECT 1").fetchone()
        db_ok = True
    except Exception as e:
        db_ok = False
        issues.append(f"db: {e}")

    # Disk free
    disk_free_mb = 0
    disk_ok = True
    try:
        base = _P(settings.export.base_path)
        if base.exists():
            disk_free_mb = _sh.disk_usage(str(base)).free // (1024 * 1024)
            min_mb = settings.export.min_disk_space_mb or 0
            if disk_free_mb < min_mb:
                disk_ok = False
                issues.append(f"disk: free={disk_free_mb}MB < min={min_mb}MB")
        else:
            disk_ok = False
            issues.append(f"disk: archive path not found: {base}")
    except Exception as e:
        disk_ok = False
        issues.append(f"disk: {e}")

    # Scheduler (best-effort — may not be present in pure-CLI deployments)
    sched_ok = True
    try:
        sched = getattr(request.app.state, "scheduler", None)
        if sched and hasattr(sched, "running") and not sched.running:
            sched_ok = False
            issues.append("scheduler: not running")
    except Exception:
        pass

    healthy = db_ok and disk_ok and sched_ok

    try:
        from glogarch import __version__  # type: ignore
    except Exception:
        __version__ = "unknown"  # type: ignore[assignment]

    body = {
        "status": "healthy" if healthy else "unhealthy",
        "version": __version__,
        "checks": {
            "db": db_ok,
            "disk": disk_ok,
            "scheduler": sched_ok,
        },
        "disk_free_mb": disk_free_mb,
        "issues": issues,
    }
    return JSONResponse(body, status_code=200 if healthy else 503)


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
    """List servers with connectivity status, including Data Node detection."""
    settings = _settings(request)
    from glogarch.graylog.client import GraylogClient
    from glogarch.ratelimit.limiter import RateLimiter
    import asyncio as _asyncio

    import httpx as _httpx

    async def _probe(srv):
        rl = RateLimiter(settings.rate_limit)
        async with GraylogClient(srv, rl) as client:
            info = await client.check_connectivity()
            info["name"] = srv.name
            info["url"] = srv.url
            info["has_datanode"] = False
            # Detect Data Node via a DIRECT, single-shot call (5s, NO retry).
            # On Graylog without data nodes /api/datanodes returns 404 — routing
            # it through client.get() would trip the retry decorator's 2+4+8s
            # backoff (~14s) and stall the dashboard's Servers table. Skip the
            # probe entirely if the server is unreachable.
            if info.get("connected"):
                try:
                    if srv.auth_token:
                        auth = _httpx.BasicAuth(srv.auth_token, "token")
                    else:
                        auth = _httpx.BasicAuth(srv.username or "", srv.password or "")
                    async with _httpx.AsyncClient(verify=srv.verify_ssl, timeout=5.0) as hc:
                        r = await hc.get(f"{srv.url.rstrip('/')}/api/datanodes",
                                         auth=auth, headers={"Accept": "application/json"})
                        if r.status_code == 200:
                            d = r.json()
                            if isinstance(d, list) and len(d) > 0:
                                info["has_datanode"] = True
                                info["datanode_count"] = len(d)
                except Exception:
                    pass
            return info

    # Probe all servers concurrently so N unreachable servers don't add up
    # serially. Each probe already returns {"connected": False} on failure.
    results = await _asyncio.gather(*[_probe(srv) for srv in settings.servers])
    return {"items": list(results)}


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
        from glogarch.core.config_writer import update_config
        update_config(config_path,
                      lambda cfg: cfg.setdefault("export", {}).update({"base_path": new_path}))

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
    import httpx as _httpx
    rl = RateLimiter(settings.rate_limit)
    try:
        async with GraylogClient(server_config, rl) as client:
            streams = await client.get_streams()
    except _httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            return JSONResponse({"error": "Graylog API authentication failed (401). Check API token.", "items": []}, status_code=401)
        return JSONResponse({"error": f"Graylog API error: HTTP {e.response.status_code}", "items": []}, status_code=502)
    except Exception as e:
        return JSONResponse({"error": f"Cannot reach Graylog: {e}", "items": []}, status_code=502)
    return {"items": [{"id": s["id"], "title": s.get("title", ""), "index_set_id": s.get("index_set_id", "")} for s in streams]}


@router.get("/index-sets")
async def list_index_sets(request: Request):
    settings = _settings(request)
    server_config = settings.get_server()
    from glogarch.graylog.client import GraylogClient
    from glogarch.ratelimit.limiter import RateLimiter
    import httpx as _httpx
    rl = RateLimiter(settings.rate_limit)
    try:
        async with GraylogClient(server_config, rl) as client:
            index_sets = await client.get_index_sets()
    except _httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            return JSONResponse({"error": "Graylog API authentication failed (401). Check API token.", "items": []}, status_code=401)
        return JSONResponse({"error": f"Graylog API error: HTTP {e.response.status_code}", "items": []}, status_code=502)
    except Exception as e:
        return JSONResponse({"error": f"Cannot reach Graylog: {e}", "items": []}, status_code=502)
    return {"items": [{"id": s["id"], "title": s.get("title", ""), "index_prefix": s.get("index_prefix", ""), "default": s.get("default", False)} for s in index_sets]}


# --- OpenSearch ---

@router.get("/opensearch/status")
async def opensearch_status(request: Request, server: str | None = None):
    """Get OpenSearch connection status and config.

    When `server` is given, reports that Graylog server's resolved cluster
    (per-server block if set, else the global fallback)."""
    settings = _settings(request)
    os_config = settings.get_opensearch(server)
    has_config = bool(os_config.hosts)
    # Tell the UI whether this cluster came from the server's OWN opensearch block
    # or the global fallback, so a multi-cluster dashboard can label each server
    # correctly (and users don't misread a per-server cluster as "API mode").
    source = "none"
    if has_config:
        source = "global"
        if server:
            try:
                srv = settings.get_server(server)
                if srv.opensearch is not None and srv.opensearch.hosts:
                    source = "per-server"
            except Exception:
                pass
    return {
        "configured": has_config,
        "hosts": os_config.hosts,
        "export_mode": settings.export_mode,
        "server": server,
        "source": source,
    }


@router.get("/opensearch/indices")
async def list_opensearch_indices(request: Request, prefix: str | None = None, server: str | None = None):
    """Get available OpenSearch indices with time ranges for coverage visualization."""
    settings = _settings(request)
    os_config = settings.get_opensearch(server)
    if not os_config.hosts:
        return {"indices": [], "active_index": None}

    from glogarch.opensearch.client import OpenSearchClient

    # Resolve prefix
    if not prefix:
        try:
            from glogarch.graylog.client import GraylogClient
            from glogarch.ratelimit.limiter import RateLimiter
            rl = RateLimiter(settings.rate_limit)
            async with GraylogClient(settings.get_server(server), rl) as gl:
                index_sets = await gl.get_index_sets()
                prefix = "graylog"
                for iset in index_sets:
                    if iset.get("default"):
                        prefix = iset.get("index_prefix", "graylog")
                        break
        except Exception:
            prefix = "graylog"

    async with OpenSearchClient(os_config) as client:
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
    server = body.get("server") or None
    settings = _settings(request)

    # Reorder the correct cluster: the server's OWN opensearch block when it has
    # one (multi-cluster), otherwise the global block. Reordering the global list
    # when the user clicked a per-server node used to be a silent mistake.
    target_server = None
    if server:
        try:
            srv = settings.get_server(server)
            if srv.opensearch is not None and srv.opensearch.hosts:
                target_server = srv
        except Exception:
            target_server = None

    hosts = list(target_server.opensearch.hosts if target_server else settings.opensearch.hosts)
    if from_idx < 0 or from_idx >= len(hosts) or to_idx < 0 or to_idx >= len(hosts):
        return JSONResponse({"error": "Invalid index"}, status_code=400)

    # Move host from from_idx to to_idx
    host = hosts.pop(from_idx)
    hosts.insert(to_idx, host)

    from glogarch.core.config_writer import update_config
    config_path = _config_path(request)
    if target_server is not None:
        target_server.opensearch.hosts = hosts
        _sname = target_server.name

        def _mutate(cfg):
            for s in cfg.get("servers", []) or []:
                if s.get("name") == _sname:
                    s.setdefault("opensearch", {})["hosts"] = hosts
        if config_path.exists():
            update_config(config_path, _mutate)
    else:
        settings.opensearch.hosts = hosts
        if config_path.exists():
            update_config(config_path,
                          lambda cfg: cfg.setdefault("opensearch", {}).update({"hosts": hosts}))

    return {"hosts": hosts, "primary": hosts[0], "server": server}


@router.post("/opensearch/test")
async def test_opensearch(request: Request):
    """Test OpenSearch connection."""
    settings = _settings(request)

    # Allow testing with ad-hoc connection info from request body
    try:
        body = await request.json()
    except Exception:
        body = {}
    os_config = settings.get_opensearch(body.get("server"))
    hosts = body.get("hosts") or os_config.hosts
    username = body.get("username") or os_config.username
    password = body.get("password") or os_config.password

    if not hosts:
        return JSONResponse({"connected": False, "error": "No OpenSearch hosts configured"}, status_code=400)

    # SSRF guard (OWASP A01): refuse link-local / cloud-metadata targets.
    from glogarch.utils.netguard import ssrf_block_reason
    for h in (hosts if isinstance(hosts, list) else [hosts]):
        reason = ssrf_block_reason(h)
        if reason:
            return JSONResponse({"connected": False, "error": reason}, status_code=400)

    from glogarch.core.config import OpenSearchConfig
    from glogarch.opensearch.client import OpenSearchClient

    test_config = OpenSearchConfig(
        hosts=hosts if isinstance(hosts, list) else [hosts],
        username=username,
        password=password,
        verify_ssl=os_config.verify_ssl,
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
    if n.email.enabled:
        channels.append({"name": "email", "enabled": True})
    return {
        "channels": channels,
        "on_export_complete": n.on_export_complete,
        "on_import_complete": n.on_import_complete,
        "on_cleanup_complete": n.on_cleanup_complete,
        "on_error": n.on_error,
        "on_verify_failed": n.on_verify_failed,
        "on_sensitive_operation": n.on_sensitive_operation,
        "on_audit_alert": n.on_audit_alert,
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
    timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
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
            results.append(await _send_discord(client, config.discord, title, body, timestamp))
        if config.slack.enabled:
            results.append(await _send_slack(client, config.slack, title, body, timestamp))
        if config.teams.enabled:
            results.append(await _send_teams(client, config.teams, title, body, timestamp))
        if config.nextcloud_talk.enabled:
            results.append(await _send_nextcloud_talk(client, config.nextcloud_talk, full_msg))
    if config.email.enabled:
        results.append(await _send_email(config.email, title, body, timestamp))

    return {"results": results}


# --- Logs ---

# --- Operation Audit ---

@router.get("/audit/stats")
def get_audit_stats(request: Request, hours: int = 24):
    db = _db(request)
    return db.get_api_audit_stats(hours=hours)


@router.get("/audit/status")
def get_audit_status(request: Request):
    listener = getattr(request.app.state, "audit_listener", None)
    if not listener:
        return {"enabled": False}
    status = listener.get_status()
    status["retention_days"] = _settings(request).op_audit.retention_days
    return status


@router.post("/audit/toggle")
async def toggle_audit(request: Request):
    """Toggle op_audit.enabled and save to config.yaml. Requires restart."""
    settings = _settings(request)
    new_val = not settings.op_audit.enabled
    settings.op_audit.enabled = new_val

    # Save to config.yaml
    from glogarch.core.config_writer import update_config
    config_path = _config_path(request)
    if config_path.exists():
        def _mut(cfg):
            cfg.setdefault("op_audit", {})["enabled"] = new_val
            cfg.pop("api_audit", None)  # remove old key if present
        update_config(config_path, _mut)

    _audit(request, "audit_toggle", f"op_audit.enabled={new_val}")

    # Restart listener if toggling on (best effort — full restart recommended)
    listener = getattr(request.app.state, "audit_listener", None)
    if listener:
        if new_val and not listener.transport:
            listener.config.enabled = True
            import asyncio
            asyncio.ensure_future(listener.start())
        elif not new_val and listener.transport:
            listener.config.enabled = False
            await listener.stop()

    return {"enabled": new_val, "restart_required": False}


@router.get("/audit/nginx-config")
def get_audit_nginx_config(request: Request):
    """Return the nginx config snippet for users to copy."""
    settings = _settings(request)
    port = settings.op_audit.listen_port
    # nginx convention: 8-space indent
    I = "        "  # 8 spaces (inside block)
    II = "                "  # 16 spaces (continuation)
    log_format = (
        f"{I}log_format graylog_audit escape=json\n"
        f"{II}'{{'\n"
        f"{II}'\"time\":\"$time_iso8601\",'\n"
        f"{II}'\"remote_addr\":\"$remote_addr\",'\n"
        f"{II}'\"method\":\"$request_method\",'\n"
        f"{II}'\"uri\":\"$uri\",'\n"
        f"{II}'\"args\":\"$args\",'\n"
        f"{II}'\"status\":$status,'\n"
        f"{II}'\"body_bytes_sent\":$body_bytes_sent,'\n"
        f"{II}'\"request_body\":\"$request_body\",'\n"
        f"{II}'\"http_authorization\":\"$http_authorization\",'\n"
        f"{II}'\"http_cookie\":\"$cookie_authentication\",'\n"
        f"{II}'\"user_agent\":\"$http_user_agent\",'\n"
        f"{II}'\"request_time\":$request_time,'\n"
        f"{II}'\"server_name\":\"$server_name\"'\n"
        f"{II}'}}';",
    )
    server_block = (
        f"{I}access_log syslog:server=JT_GLOGARCH_IP:{port},facility=local7,tag=graylog_audit graylog_audit;\n"
        f"{I}client_body_buffer_size 64k;"
    )
    return {"log_format": log_format, "server_block": server_block}


@router.get("/audit")
def list_audit(request: Request, page: int = 1, page_size: int = 50,
               username: str = "", method: str = "", uri: str = "",
               status_code: str = "", sensitive_only: bool = False,
               time_from: str = "", time_to: str = ""):
    db = _db(request)
    offset = (page - 1) * page_size
    items, total = db.list_api_audit(
        limit=page_size, offset=offset,
        username=username, method=method, uri=uri,
        status_code=status_code, sensitive_only=sensitive_only,
        time_from=time_from, time_to=time_to,
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/audit/{entry_id}")
def get_audit_detail(request: Request, entry_id: int):
    db = _db(request)
    entry = db.get_api_audit_entry(entry_id)
    if not entry:
        return JSONResponse({"error": "Not found"}, status_code=404)
    return entry


@router.get("/logs/realtime")
def get_realtime_log(request: Request, lines: int = 100):
    """Get recent journalctl log lines."""
    import subprocess
    try:
        result = subprocess.run(
            ["journalctl", "-u", "jt-glogarch", "-n", str(min(lines, 1000)), "--no-pager"],
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

def _mask(val: str) -> str:
    """Mask sensitive strings for API responses. Show first/last 3 chars."""
    if not val or len(val) <= 6:
        return "***" if val else ""
    # Always embed at least THREE asterisks so reconcile_secret() (which treats
    # any value containing "***" as an unchanged mask) reliably recognises the
    # masked value on save. A 7- or 8-char secret would otherwise mask to only
    # 1-2 asterisks, slip past reconcile, and get persisted literally — silently
    # replacing e.g. an 8-char admin password with "abc**xyz". (real-world bug)
    return val[:3] + "*" * max(3, len(val) - 6) + val[-3:]


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
        "on_sensitive_operation": n.on_sensitive_operation,
        "on_audit_alert": n.on_audit_alert,
        "telegram": {"enabled": n.telegram.enabled, "bot_token": _mask(n.telegram.bot_token), "chat_id": n.telegram.chat_id},
        "discord": {"enabled": n.discord.enabled, "webhook_url": _mask(n.discord.webhook_url)},
        "slack": {"enabled": n.slack.enabled, "webhook_url": _mask(n.slack.webhook_url)},
        "teams": {"enabled": n.teams.enabled, "webhook_url": _mask(n.teams.webhook_url)},
        "nextcloud_talk": {"enabled": n.nextcloud_talk.enabled, "server_url": n.nextcloud_talk.server_url,
                           "token": _mask(n.nextcloud_talk.token), "username": n.nextcloud_talk.username,
                           "password": _mask(n.nextcloud_talk.password)},
        "email": {"enabled": n.email.enabled, "smtp_host": n.email.smtp_host, "smtp_port": n.email.smtp_port,
                  "smtp_tls": n.email.smtp_tls, "smtp_user": n.email.smtp_user,
                  "smtp_password": _mask(n.email.smtp_password),
                  "from_addr": n.email.from_addr, "to_addrs": n.email.to_addrs, "subject_prefix": n.email.subject_prefix},
    }


@router.post("/notify/config")
async def save_notify_config(request: Request):
    """Save notification config to config.yaml."""
    body = await request.json()
    settings = _settings(request)

    # Update in-memory
    n = settings.notify
    for key in ("on_export_complete", "on_import_complete", "on_cleanup_complete", "on_error", "on_verify_failed", "on_sensitive_operation", "on_audit_alert"):
        if key in body:
            setattr(n, key, body[key])

    channel_map = {
        "telegram": n.telegram, "discord": n.discord, "slack": n.slack,
        "teams": n.teams, "nextcloud_talk": n.nextcloud_talk, "email": n.email,
    }
    # Secret fields that are masked in GET responses — skip if unchanged
    _SECRET_FIELDS = {"bot_token", "webhook_url", "token", "password", "smtp_password"}
    for ch_name, ch_obj in channel_map.items():
        if ch_name in body:
            ch_data = body[ch_name]
            for k, v in ch_data.items():
                if hasattr(ch_obj, k):
                    # Don't overwrite with masked value
                    if k in _SECRET_FIELDS and isinstance(v, str) and "***" in v:
                        continue
                    setattr(ch_obj, k, v)

    # Save to config.yaml — persist the RECONCILED model (with real secrets),
    # never the raw request body, which may carry masked "***" placeholders for
    # unchanged secrets. Writing the body verbatim used to overwrite real
    # secrets with their masked form, breaking notifications after restart.
    from glogarch.core.config_writer import update_config
    config_path = _config_path(request)
    if config_path.exists():
        update_config(config_path, lambda cfg: cfg.update({"notify": n.model_dump()}))

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
    # Structured post-completion result (e.g. OpenSearch index-set coverage), parsed
    # so the UI can render a badge without re-parsing free text.
    _rj = getattr(j, "result_json", None)
    if _rj:
        try:
            import json as _json
            d["result"] = _json.loads(_rj)
        except Exception:
            d["result"] = None
    # Parsed retry config (archives + target, no secrets) for the one-click retry.
    _cj = getattr(j, "config_json", None)
    if _cj:
        try:
            import json as _json2
            d["retry_config"] = _json2.loads(_cj)
        except Exception:
            d["retry_config"] = None
    # Enrich with live progress info from in-memory store
    if j.id in _job_progress and _job_progress[j.id]:
        events = _job_progress[j.id]
        last = events[-1]
        d["phase"] = last.get("phase", "")
        idx_name = last.get("index", "")
        chunk = last.get("chunk_index")
        total = last.get("total_chunks")
        # Find detail from the most recent event that has it
        detail_str = ""
        for evt in reversed(events[-10:]):
            if evt.get("detail"):
                detail_str = evt["detail"]
                break
        if detail_str:
            d["current_detail"] = detail_str
        elif idx_name:
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
    # Compute next fire time from cron expression if enabled
    next_run = None
    if s.enabled and s.cron_expr:
        try:
            from apscheduler.triggers.cron import CronTrigger
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            from datetime import datetime
            from glogarch.scheduler.scheduler import posix_cron_to_apscheduler
            # Use the scheduler's local timezone for display
            tz = AsyncIOScheduler().timezone
            # POSIX cron numbers dow as 0/7=Sun, 6=Sat; APScheduler numbers
            # 0=Mon, 6=Sun. Convert so the displayed next-fire matches what
            # apply_schedule() actually registers with APScheduler.
            cron_for_aps = posix_cron_to_apscheduler(s.cron_expr)
            trigger = CronTrigger.from_crontab(cron_for_aps, timezone=tz)
            next_fire = trigger.get_next_fire_time(None, datetime.now(tz))
            if next_fire:
                next_run = next_fire.isoformat()
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
        "next_run_at": next_run,
    }


# ============================================================
# Connection settings — Graylog servers + OpenSearch (Web UI editable)
# and first-run setup wizard. All writes go through the atomic config_writer.
# ============================================================


def _is_unconfigured(settings: Settings) -> bool:
    """Fresh install with no Graylog server yet — triggers the setup wizard."""
    return len(settings.servers) == 0


def _server_to_dict(s) -> dict:
    """Serialize a GraylogServerConfig with secrets masked for GET responses."""
    d = {
        "name": s.name,
        "url": s.url,
        "auth_token": _mask(s.auth_token or ""),
        "username": s.username or "",
        "password": _mask(s.password or ""),
        "verify_ssl": s.verify_ssl,
        "has_opensearch": bool(s.opensearch and s.opensearch.hosts),
    }
    if s.opensearch:
        d["opensearch"] = {
            "hosts": list(s.opensearch.hosts),
            "username": s.opensearch.username or "",
            "password": _mask(s.opensearch.password or ""),
            "verify_ssl": s.opensearch.verify_ssl,
        }
    return d


@router.get("/config/servers")
def get_config_servers(request: Request):
    """List Graylog servers (secrets masked), plus default_server + export_mode."""
    settings = _settings(request)
    return {
        "items": [_server_to_dict(s) for s in settings.servers],
        "default_server": settings.default_server,
        "export_mode": settings.export_mode,
    }


@router.post("/config/servers")
async def save_config_server(request: Request):
    """Create or update ONE Graylog server (keyed by name).

    Partial-update friendly: masked/empty secrets are reconciled against the
    stored value, and an omitted per-server ``opensearch`` block is preserved —
    so editing a server never wipes fields the UI didn't surface (important for
    upgraded customers whose config may carry username+password AND a token)."""
    body = await request.json()
    settings = _settings(request)
    name = (body.get("name") or "").strip()
    url = (body.get("url") or "").strip()
    if not name or not url:
        return JSONResponse({"error": "name and url are required"}, status_code=400)

    from glogarch.core.config import GraylogServerConfig, OpenSearchConfig
    from glogarch.core.config_writer import update_config, reconcile_secret

    existing = next((s for s in settings.servers if s.name == name), None)

    auth_token = reconcile_secret(body.get("auth_token"),
                                  existing.auth_token if existing else None)
    password = reconcile_secret(body.get("password"),
                                existing.password if existing else None)
    username = body.get("username")
    if username is None and existing:
        username = existing.username
    verify_ssl = bool(body.get("verify_ssl", existing.verify_ssl if existing else True))

    # Per-server OpenSearch: present with hosts → rebuild; key omitted → keep
    # existing; present but empty hosts → drop it.
    os_block = None
    os_in = body.get("opensearch")
    if os_in and os_in.get("hosts"):
        existing_os = existing.opensearch if (existing and existing.opensearch) else None
        os_block = OpenSearchConfig(
            hosts=[h.strip() for h in os_in.get("hosts", []) if isinstance(h, str) and h.strip()],
            username=(os_in.get("username") or None),
            password=reconcile_secret(os_in.get("password"),
                                      existing_os.password if existing_os else None),
            verify_ssl=bool(os_in.get("verify_ssl", existing_os.verify_ssl if existing_os else False)),
        )
    elif os_in is None and existing and existing.opensearch:
        os_block = existing.opensearch

    new_server = GraylogServerConfig(
        name=name, url=url, auth_token=(auth_token or None),
        username=(username or None), password=(password or None),
        verify_ssl=verify_ssl, opensearch=os_block,
    )

    # In-memory: replace by name or append (applies live to new operations)
    settings.servers = [s for s in settings.servers if s.name != name] + [new_server]
    if not settings.default_server:
        settings.default_server = name
    new_default = settings.default_server

    def _mut(cfg):
        srv_list = cfg.setdefault("servers", [])
        entry = new_server.model_dump(exclude_none=True)
        for i, e in enumerate(srv_list):
            if isinstance(e, dict) and e.get("name") == name:
                srv_list[i] = entry
                break
        else:
            srv_list.append(entry)
        if not cfg.get("default_server"):
            cfg["default_server"] = new_default
    update_config(_config_path(request), _mut)

    _audit(request, "config_server_saved", f"server={name} url={url}")
    return {"status": "saved", "name": name}


@router.delete("/config/servers/{name}")
def delete_config_server(request: Request, name: str):
    """Delete a Graylog server; reassign default_server if it pointed here."""
    settings = _settings(request)
    if not any(s.name == name for s in settings.servers):
        return JSONResponse({"error": "Server not found"}, status_code=404)
    settings.servers = [s for s in settings.servers if s.name != name]
    if settings.default_server == name:
        settings.default_server = settings.servers[0].name if settings.servers else ""
    new_default = settings.default_server

    from glogarch.core.config_writer import update_config

    def _mut(cfg):
        cfg["servers"] = [e for e in cfg.get("servers", [])
                          if not (isinstance(e, dict) and e.get("name") == name)]
        if cfg.get("default_server") == name:
            cfg["default_server"] = new_default
    update_config(_config_path(request), _mut)

    _audit(request, "config_server_deleted", f"server={name}")
    return {"status": "deleted", "name": name}


async def _fetch_heap_advice(client, base_url: str, auth):
    """After a successful Graylog connection, read its JVM heap and return sizing
    advice for the UI (current -Xmx + a recommended minimum). Best-effort."""
    from glogarch.graylog.system import heap_advice
    try:
        r = await client.get(f"{base_url.rstrip('/')}/api/system/jvm", auth=auth,
                             headers={"Accept": "application/json"})
        if r.status_code == 200:
            j = r.json()
            mx = (j.get("max_memory") or {}).get("bytes", 0)
            used = (j.get("used_memory") or {}).get("bytes", 0)
            pct = (used / mx * 100.0) if mx else None
            return heap_advice(mx, pct)
    except Exception:
        pass
    return None


@router.post("/config/servers/test")
async def test_config_server(request: Request):
    """Test a Graylog server connection from ad-hoc form values (no save).

    Uses a direct 10s httpx call (no retry) for fast feedback, mirroring the
    login flow's auth (token as username / "token" as password)."""
    import httpx
    from glogarch.utils.sanitize import sanitize
    from glogarch.core.config_writer import reconcile_secret
    body = await request.json()
    settings = _settings(request)
    name = (body.get("name") or "").strip()
    url = (body.get("url") or "").strip()
    if not url:
        return JSONResponse({"error": "url is required"}, status_code=400)
    # SSRF guard (OWASP A01): refuse link-local / cloud-metadata targets.
    from glogarch.utils.netguard import ssrf_block_reason
    _reason = ssrf_block_reason(url)
    if _reason:
        return JSONResponse({"connected": False, "error": _reason}, status_code=400)
    existing = next((s for s in settings.servers if s.name == name), None)
    auth_token = reconcile_secret(body.get("auth_token"),
                                  existing.auth_token if existing else None)
    username = body.get("username") or (existing.username if existing else None)
    password = reconcile_secret(body.get("password"),
                                existing.password if existing else None)
    verify_ssl = bool(body.get("verify_ssl", False))
    if auth_token:
        auth = httpx.BasicAuth(auth_token, "token")
    else:
        auth = httpx.BasicAuth(username or "", password or "")
    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=10.0) as client:
            resp = await client.get(f"{url.rstrip('/')}/api/system", auth=auth,
                                    headers={"Accept": "application/json"})
            if resp.status_code == 200:
                data = resp.json()
                heap = await _fetch_heap_advice(client, url, auth)
                return {"connected": True, "version": data.get("version"),
                        "hostname": data.get("hostname"), "heap": heap}
            if resp.status_code in (401, 403):
                return {"connected": False, "error": "Authentication failed (check token / credentials)"}
            return {"connected": False, "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"connected": False, "error": sanitize(str(e))}


@router.post("/config/servers/{name}/test")
async def test_saved_server(request: Request, name: str):
    """Test connectivity to an already-saved Graylog server (uses stored creds)."""
    import httpx
    from glogarch.utils.sanitize import sanitize
    settings = _settings(request)
    srv = next((s for s in settings.servers if s.name == name), None)
    if not srv:
        return JSONResponse({"error": "Server not found"}, status_code=404)
    if srv.auth_token:
        auth = httpx.BasicAuth(srv.auth_token, "token")
    else:
        auth = httpx.BasicAuth(srv.username or "", srv.password or "")
    try:
        async with httpx.AsyncClient(verify=srv.verify_ssl, timeout=10.0) as client:
            resp = await client.get(f"{srv.url.rstrip('/')}/api/system", auth=auth,
                                    headers={"Accept": "application/json"})
            if resp.status_code == 200:
                data = resp.json()
                heap = await _fetch_heap_advice(client, srv.url, auth)
                return {"connected": True, "version": data.get("version"),
                        "hostname": data.get("hostname"), "heap": heap}
            if resp.status_code in (401, 403):
                return {"connected": False, "error": "Authentication failed (check token / credentials)"}
            return {"connected": False, "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"connected": False, "error": sanitize(str(e))}


@router.get("/config/opensearch")
def get_config_opensearch(request: Request):
    """Global OpenSearch config (password masked)."""
    os_cfg = _settings(request).opensearch
    return {
        "hosts": list(os_cfg.hosts),
        "username": os_cfg.username or "",
        "password": _mask(os_cfg.password or ""),
        "verify_ssl": os_cfg.verify_ssl,
    }


@router.post("/config/opensearch")
async def save_config_opensearch(request: Request):
    """Save the global OpenSearch config (password reconciled if masked)."""
    body = await request.json()
    settings = _settings(request)
    from glogarch.core.config import OpenSearchConfig
    from glogarch.core.config_writer import update_config, reconcile_secret
    hosts = [h.strip() for h in body.get("hosts", []) if isinstance(h, str) and h.strip()]
    password = reconcile_secret(body.get("password"), settings.opensearch.password)
    username = body.get("username")
    if username is None:
        username = settings.opensearch.username
    verify_ssl = bool(body.get("verify_ssl", settings.opensearch.verify_ssl))
    new_os = OpenSearchConfig(hosts=hosts, username=(username or None),
                              password=(password or None), verify_ssl=verify_ssl)
    settings.opensearch = new_os
    update_config(_config_path(request),
                  lambda cfg: cfg.update({"opensearch": new_os.model_dump(exclude_none=True)}))
    _audit(request, "config_opensearch_saved", f"hosts={len(hosts)}")
    return {"status": "saved"}


@router.post("/config/general")
async def save_config_general(request: Request):
    """Save export_mode and/or default_server."""
    body = await request.json()
    settings = _settings(request)
    from glogarch.core.config_writer import update_config
    updates: dict = {}
    if "export_mode" in body:
        mode = body["export_mode"]
        if mode not in ("api", "opensearch"):
            return JSONResponse({"error": "export_mode must be 'api' or 'opensearch'"}, status_code=400)
        settings.export_mode = mode
        updates["export_mode"] = mode
    if "default_server" in body:
        ds = (body["default_server"] or "")
        if ds and not any(s.name == ds for s in settings.servers):
            return JSONResponse({"error": "default_server not found"}, status_code=400)
        settings.default_server = ds
        updates["default_server"] = ds
    if updates:
        update_config(_config_path(request), lambda cfg: cfg.update(updates))
    _audit(request, "config_general_saved", str(updates))
    return {"status": "saved", **updates}


@router.get("/config/import-defaults")
def get_config_import_defaults(request: Request):
    """Default restore target for the import dialog (secrets masked).

    The import modal reads this on open and pre-fills the target fields so the
    operator doesn't retype the Graylog host/API URL/token every time.
    """
    ic = _settings(request).import_config
    return {
        "gelf_host": ic.gelf_host or "",
        "gelf_port": ic.gelf_port,
        "gelf_protocol": ic.gelf_protocol or "tcp",
        "target_api_url": ic.target_api_url or "",
        "target_api_token": _mask(ic.target_api_token or ""),
        "target_api_username": ic.target_api_username or "",
        "target_api_password": _mask(ic.target_api_password or ""),
        # Flags so the modal knows a secret default exists even though it's
        # masked (used to decide whether to show the masked placeholder).
        "has_token": bool(ic.target_api_token),
        "has_password": bool(ic.target_api_password),
    }


@router.post("/config/import-defaults")
async def save_config_import_defaults(request: Request):
    """Save the default restore target (secrets reconciled if masked)."""
    body = await request.json()
    settings = _settings(request)
    from glogarch.core.config_writer import update_config, reconcile_secret
    ic = settings.import_config
    # Non-secret fields: take provided value, else keep current.
    if "gelf_host" in body:
        ic.gelf_host = (body.get("gelf_host") or "").strip() or "localhost"
    if body.get("gelf_port"):
        try:
            ic.gelf_port = int(body["gelf_port"])
        except (TypeError, ValueError):
            return JSONResponse({"error": "gelf_port must be an integer"}, status_code=400)
    if body.get("gelf_protocol") in ("tcp", "udp"):
        ic.gelf_protocol = body["gelf_protocol"]
    if "target_api_url" in body:
        ic.target_api_url = (body.get("target_api_url") or "").strip()
    if "target_api_username" in body:
        ic.target_api_username = (body.get("target_api_username") or "").strip()
    # Secrets: reconcile so a masked/empty value keeps the stored secret.
    ic.target_api_token = reconcile_secret(body.get("target_api_token"), ic.target_api_token) or ""
    ic.target_api_password = reconcile_secret(body.get("target_api_password"), ic.target_api_password) or ""

    # Persist the whole 'import' section (alias of import_config) atomically.
    section = ic.model_dump()
    update_config(_config_path(request),
                  lambda cfg: cfg.update({"import": section}))
    _audit(request, "config_import_defaults_saved",
           f"api_url={ic.target_api_url} host={ic.gelf_host}")
    return {"status": "saved"}


@router.post("/config/import-defaults/test")
async def test_config_import_defaults(request: Request):
    """Test the restore-target Graylog API from form values (secrets reconciled
    against the stored defaults so a masked field still tests)."""
    import httpx
    from glogarch.utils.sanitize import sanitize
    from glogarch.utils.netguard import ssrf_block_reason
    from glogarch.core.config_writer import reconcile_secret
    body = await request.json()
    ic = _settings(request).import_config
    url = (body.get("target_api_url") or "").strip() or (ic.target_api_url or "")
    if not url:
        return JSONResponse({"error": "target_api_url is required"}, status_code=400)
    _reason = ssrf_block_reason(url)
    if _reason:
        return JSONResponse({"connected": False, "error": _reason}, status_code=400)
    token = reconcile_secret(body.get("target_api_token"), ic.target_api_token) or ""
    username = (body.get("target_api_username") or "").strip() or (ic.target_api_username or "")
    password = reconcile_secret(body.get("target_api_password"), ic.target_api_password) or ""
    if token:
        auth = httpx.BasicAuth(token, "token")
    elif username and password:
        auth = httpx.BasicAuth(username, password)
    else:
        return JSONResponse({"connected": False, "error": "Provide a token or username + password"}, status_code=400)
    try:
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            resp = await client.get(f"{url.rstrip('/')}/api/system", auth=auth,
                                    headers={"Accept": "application/json"})
            if resp.status_code == 200:
                data = resp.json()
                return {"connected": True, "version": data.get("version"),
                        "hostname": data.get("hostname")}
            if resp.status_code in (401, 403):
                return {"connected": False, "error": "Authentication failed (check token / credentials)"}
            return {"connected": False, "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"connected": False, "error": sanitize(str(e))}


@router.post("/graylog/flush")
async def flush_target_graylog(request: Request):
    """Non-destructive 'relieve / flush' a wedged target Graylog. NEVER deletes
    data — cycles the write index (deflector) and/or rebuilds index ranges, with
    before/after backpressure snapshots.

    Two contexts, both supported:
      * ``{"server": "<name>"}`` — a configured server (Settings server list).
      * ``{"target_api_url": ..., "target_api_token"/"username"/"password": ...}``
        — an import target (import progress screen); secrets reconciled against
        the stored import defaults so a masked field still works.
    """
    from glogarch.graylog.maintenance import GraylogFlusher
    from glogarch.utils.netguard import ssrf_block_reason
    from glogarch.core.config_writer import reconcile_secret
    from glogarch.utils.sanitize import sanitize

    body = await request.json()
    settings = _settings(request)
    index_set_id = (body.get("index_set_id") or "").strip() or None
    do_cycle = body.get("do_cycle", True)
    do_rebuild = body.get("do_rebuild", True)

    server_name = (body.get("server") or "").strip()
    if server_name:
        # get_server() falls back to servers[0] for an unknown name, which would
        # silently flush the WRONG server — validate the name matches exactly.
        srv = next((s for s in settings.servers if s.name == server_name), None)
        if srv is None:
            return JSONResponse({"error": f"Unknown server: {server_name}"}, status_code=404)
        url, token = srv.url, (srv.auth_token or "")
        username, password, verify_ssl = (srv.username or ""), (srv.password or ""), srv.verify_ssl
    else:
        ic = settings.import_config
        url = (body.get("target_api_url") or "").strip() or (ic.target_api_url or "")
        token = reconcile_secret(body.get("target_api_token"), ic.target_api_token) or ""
        username = (body.get("target_api_username") or "").strip() or (ic.target_api_username or "")
        password = reconcile_secret(body.get("target_api_password"), ic.target_api_password) or ""
        verify_ssl = False

    if not url:
        return JSONResponse({"error": "target_api_url or server is required"}, status_code=400)
    _reason = ssrf_block_reason(url)
    if _reason:
        return JSONResponse({"ok": False, "error": _reason}, status_code=400)
    if not token and not (username and password):
        return JSONResponse({"ok": False, "error": "Provide a token or username + password"},
                            status_code=400)

    flusher = GraylogFlusher(
        api_url=url, api_token=token, api_username=username,
        api_password=password, verify_ssl=verify_ssl,
    )
    try:
        report = await flusher.flush(index_set_id=index_set_id,
                                     do_cycle=bool(do_cycle), do_rebuild=bool(do_rebuild))
    except Exception as e:
        return JSONResponse({"ok": False, "error": sanitize(str(e))}, status_code=500)

    acts = ",".join(a["name"] + ":" + a["status"] for a in report.get("actions", []))
    _audit(request, "graylog_flush",
           f"target={url} index_set={report.get('index_set_id')} actions=[{acts}]")
    return report


@router.post("/config/admin-password")
async def save_admin_password(request: Request):
    """Set or clear the emergency local admin password (authenticated).

    For already-configured (e.g. upgraded) installs to opt into a break-glass
    localadmin. Empty password clears/disables it."""
    body = await request.json()
    pw = body.get("password", "") or ""
    if pw and len(pw) < 8:
        return JSONResponse({"error": "Password must be at least 8 characters"}, status_code=400)
    settings = _settings(request)
    import hashlib
    h = hashlib.sha256(pw.encode()).hexdigest() if pw else ""
    settings.web.localadmin_password_hash = h
    from glogarch.core.config_writer import update_config
    update_config(_config_path(request),
                  lambda cfg: cfg.setdefault("web", {}).update({"localadmin_password_hash": h}))
    _audit(request, "admin_password_changed", "localadmin " + ("set" if pw else "cleared"))
    return {"status": "saved", "enabled": bool(pw)}


@router.get("/setup/status")
def setup_status(request: Request):
    """First-run wizard state. Public (read-only booleans)."""
    settings = _settings(request)
    return {
        "configured": not _is_unconfigured(settings),
        "has_admin_password": bool(settings.web.localadmin_password_hash),
    }


@router.post("/setup/admin-password")
async def setup_admin_password(request: Request):
    """First-run ONLY: set the localadmin password and open an authenticated
    session so the rest of the wizard can use the normal /api/config/* endpoints.

    Gated on the pre-auth setup session (`session.setup_mode`), granted only by
    GET /setup on a still-unconfigured box — so on a configured box (no
    setup_mode obtainable) this returns 403. The local admin password is the
    LAST wizard step, so by the time it runs a Graylog server already exists;
    gating on _is_unconfigured (servers empty) would wrongly reject it, hence the
    setup_mode gate. On success we authenticate the session AND clear setup_mode,
    closing the pre-auth window."""
    if not request.session.get("setup_mode"):
        return JSONResponse({"error": "Setup already completed"}, status_code=403)
    body = await request.json()
    pw = body.get("password", "") or ""
    if len(pw) < 8:
        return JSONResponse({"error": "Password must be at least 8 characters"}, status_code=400)
    settings = _settings(request)
    import hashlib
    h = hashlib.sha256(pw.encode()).hexdigest()
    settings.web.localadmin_password_hash = h
    from glogarch.core.config_writer import update_config
    update_config(_config_path(request),
                  lambda cfg: cfg.setdefault("web", {}).update({"localadmin_password_hash": h}))
    # Password set (the wizard's last input) → authenticate as the local admin
    # and close the pre-auth setup window.
    request.session["authenticated"] = True
    request.session["username"] = "localadmin"
    request.session["emergency_mode"] = True
    request.session.pop("setup_mode", None)
    _audit(request, "setup_admin_password", "First-run admin password set")
    return {"status": "ok"}


# ============================================================
# Reports (beta) — Graylog dashboard → PDF, branded, scheduled, emailed
# ============================================================

_REPORT_SECRET_KEYS = {"graylog_web_password"}
_reports_running: set = set()  # report names currently generating (concurrency guard)


def _report_public(rec: dict) -> dict:
    import json as _json
    cfg = {}
    try:
        cfg = _json.loads(rec.get("config_json") or "{}")
    except Exception:
        cfg = {}
    for k in _REPORT_SECRET_KEYS:
        if cfg.get(k):
            cfg[k] = _mask(cfg[k])
    return {
        "id": rec["id"], "name": rec["name"], "enabled": bool(rec["enabled"]),
        "last_run_at": rec.get("last_run_at"), "config": cfg,
    }


@router.get("/reports")
def list_reports(request: Request):
    db = _db(request)
    return {"items": [_report_public(r) for r in db.list_reports()]}


@router.post("/reports")
async def save_report(request: Request):
    import json as _json
    import sqlite3
    from glogarch.core.config_writer import reconcile_secret
    body = await request.json()
    name = (body.get("name") or "").strip()
    if not name:
        return JSONResponse({"error": "name is required"}, status_code=400)
    db = _db(request)
    # Identity is the stable numeric id, so the NAME can be edited freely. When
    # editing, `id` is present → update that row (rename-capable). When creating,
    # the name must be free.
    report_id = body.get("id")
    old_rec = db.get_report_by_id(int(report_id)) if report_id else None
    old_cfg = {}
    if old_rec:
        try:
            old_cfg = _json.loads(old_rec.get("config_json") or "{}")
        except Exception:
            old_cfg = {}
    else:
        # Creating (or the id vanished): the target name must not already exist.
        if db.get_report(name):
            return JSONResponse({"error": f"A report named '{name}' already exists."},
                                status_code=409)
    cfg = dict(body.get("config") or {})
    # reconcile masked secrets against stored values
    for k in _REPORT_SECRET_KEYS:
        cfg[k] = reconcile_secret(cfg.get(k), old_cfg.get(k))
    cfg_json = _json.dumps(cfg, ensure_ascii=False)
    enabled = bool(body.get("enabled", True))
    old_name = old_rec["name"] if old_rec else None
    try:
        if old_rec:
            db.update_report(int(report_id), name, cfg_json, enabled)
        else:
            db.save_report(name, cfg_json, enabled)
    except sqlite3.IntegrityError:
        return JSONResponse({"error": f"A report named '{name}' already exists."},
                            status_code=409)
    sched = getattr(request.app.state, "scheduler", None)
    if sched:
        try:
            # On rename, drop the old cron job before (re)registering the new name.
            if old_name and old_name != name:
                sched.remove_report(old_name)
            sched.apply_report(name)
        except Exception:
            pass
    _audit(request, "report_saved", f"report={name}")
    return {"status": "saved", "name": name}


@router.delete("/reports/{name}")
def delete_report(request: Request, name: str):
    db = _db(request)
    if not db.get_report(name):
        return JSONResponse({"error": "Report not found"}, status_code=404)
    db.delete_report(name)
    sched = getattr(request.app.state, "scheduler", None)
    if sched:
        try:
            sched.remove_report(name)
        except Exception:
            pass
    _audit(request, "report_deleted", f"report={name}")
    return {"status": "deleted", "name": name}


@router.get("/reports/dashboards")
async def report_dashboards(request: Request, server: str = Query(default="")):
    """List Graylog dashboards for the report content picker."""
    settings = _settings(request)
    try:
        srv = settings.get_server(server or None)
    except Exception:
        return {"items": []}
    from glogarch.report import graylog_data
    items = await graylog_data.list_dashboards(srv)
    return {"items": items}


@router.get("/reports/dashboard-tabs")
async def report_dashboard_tabs(request: Request, server: str = Query(default=""),
                                id: str = Query(default="")):
    """List a dashboard's tabs for the report tab picker."""
    settings = _settings(request)
    try:
        srv = settings.get_server(server or None)
    except Exception:
        return {"items": []}
    if not id:
        return {"items": []}
    from glogarch.report import graylog_data
    items = await graylog_data.list_dashboard_tabs(srv, id)
    return {"items": items}


@router.get("/reports/status")
def report_status(request: Request):
    """Beta capability check — is the PDF render engine available?"""
    ok = True
    detail = ""
    try:
        import playwright  # noqa: F401
    except Exception as e:
        ok = False
        detail = f"playwright not installed: {e}"
    return {"beta": True, "render_engine": ok, "detail": detail}


@router.post("/reports/{name}/generate")
async def generate_report_now(request: Request, name: str):
    import json as _json
    db = _db(request)
    settings = _settings(request)
    rec = db.get_report(name)
    if not rec:
        return JSONResponse({"error": "Report not found"}, status_code=404)
    cfg = {}
    try:
        cfg = _json.loads(rec.get("config_json") or "{}")
    except Exception:
        pass
    cfg["name"] = name

    # Guard against duplicate concurrent generations of the same report (double
    # clicks / overlapping runs) each spawning a heavy Chromium process.
    if name in _reports_running:
        return JSONResponse({"error": "already running"}, status_code=409)
    _reports_running.add(name)

    def _run():
        from glogarch.report import generator
        from glogarch.utils.sanitize import sanitize
        from glogarch.core.models import JobRecord, JobType, JobStatus
        import uuid as _uuid
        from datetime import datetime as _dt
        job_id = str(_uuid.uuid4())
        try:
            db.create_job(JobRecord(id=job_id, job_type=JobType.REPORT, status=JobStatus.RUNNING,
                                    source="manual:report", started_at=_dt.utcnow()))
        except Exception:
            job_id = None
        try:
            _res = asyncio.run(generator.generate_report(db, settings, cfg, triggered_by="manual"))
            _units = int((_res or {}).get("units", 0) or 0)
            _note = f"report={name}"
            if (_res or {}).get("email_error"):
                _note += f" | ⚠ Email failed: {_res['email_error']}"
            elif (_res or {}).get("emailed"):
                _note += " | Email sent"
            if job_id:
                db.update_job(job_id, status=JobStatus.COMPLETED, completed_at=_dt.utcnow(),
                              progress_pct=100.0, messages_done=_units, messages_total=_units,
                              error_message=_note)
        except Exception as e:
            if job_id:
                try:
                    db.update_job(job_id, status=JobStatus.FAILED, completed_at=_dt.utcnow(),
                                  error_message=sanitize(str(e)))
                except Exception:
                    pass
            try:
                db.record_report_history(name, "", "", 0, "failed", sanitize(str(e)),
                                         triggered_by="manual")
            except Exception:
                pass
        finally:
            _reports_running.discard(name)

    asyncio.get_event_loop().run_in_executor(None, _run)
    _audit(request, "report_generate", f"report={name}")
    return {"status": "started"}


@router.get("/reports/history")
def report_history(request: Request, limit: int = Query(default=50)):
    db = _db(request)
    return {"items": db.list_report_history(limit=limit)}


@router.get("/reports/history/{hist_id}/download")
def report_download(request: Request, hist_id: int):
    from fastapi.responses import FileResponse
    db = _db(request)
    rec = db.get_report_history_entry(hist_id)
    if not rec or not rec.get("file_path"):
        return JSONResponse({"error": "Not found"}, status_code=404)
    # A01 (Broken Access Control) defense-in-depth: only ever serve files that
    # resolve to inside the reports directory — never an arbitrary path, even if
    # a DB row were tampered with.
    reports_dir = (Path(_settings(request).export.base_path) / "reports").resolve()
    try:
        p = Path(rec["file_path"]).resolve()
        p.relative_to(reports_dir)
    except (ValueError, OSError):
        return JSONResponse({"error": "Not found"}, status_code=404)
    if not p.is_file():
        return JSONResponse({"error": "File missing"}, status_code=404)
    # Force download (no inline rendering).
    return FileResponse(str(p), media_type="application/pdf",
                        filename=rec.get("filename") or p.name,
                        content_disposition_type="attachment")
