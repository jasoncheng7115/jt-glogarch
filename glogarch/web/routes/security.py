# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Security incidents API (added 1.20)."""
from __future__ import annotations

import asyncio
import threading
from datetime import datetime, timedelta
from urllib.parse import urlencode

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from glogarch.core.config import SecurityConfig
from glogarch.security.detectors import DETECTORS, PROBES, SEVERITIES
from glogarch.security.runner import parse_db_ts
from glogarch.utils.logging import get_logger
from glogarch.web.routes.api import _audit, _config_path, _db, _settings

log = get_logger("web.security")
router = APIRouter()

_run_lock = threading.Lock()
_STATUSES = ("open", "acknowledged", "closed")
_LANGS = ("en", "zh-TW", "ja")
# incident ids with an AI analysis in progress (one at a time per incident)
_analysing: set[int] = set()
_analysing_lock = threading.Lock()


def _graylog_search_url(settings, server_name: str, query: str, first: str, last: str) -> str:
    """Link to Graylog's own search for an incident's events (absolute range,
    UTC). The API URL and the web UI share the base on every supported
    version."""
    try:
        srv = settings.get_server(server_name)
    except ValueError:
        return ""
    base = srv.url.rstrip("/")
    if base.endswith("/api"):
        base = base[:-4]
    f, t = parse_db_ts(first), parse_db_ts(last)
    if f is None or t is None:
        return ""
    f, t = f - timedelta(minutes=5), t + timedelta(minutes=5)
    q = urlencode({"q": query, "rangetype": "absolute",
                   "from": f.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                   "to": t.strftime("%Y-%m-%dT%H:%M:%S.000Z")})
    return f"{base}/search?{q}"


def _with_link(request: Request, inc: dict) -> dict:
    inc["graylog_url"] = _graylog_search_url(_settings(request), inc.get("server", ""),
                                             inc.get("query", ""), inc.get("first_seen"),
                                             inc.get("last_seen"))
    return inc


@router.get("/security/incidents")
def list_incidents(request: Request, status: str = "", severity: str = "", detector: str = "",
                   limit: int = 100, offset: int = 0):
    if status and status not in _STATUSES:
        return JSONResponse({"error": "Unknown status"}, status_code=400)
    if severity and severity not in SEVERITIES:
        return JSONResponse({"error": "Unknown severity"}, status_code=400)
    db = _db(request)
    rows, total = db.list_security_incidents(
        status=status or None, severity=severity or None, detector=detector or None,
        limit=max(1, min(int(limit), 500)), offset=max(0, int(offset)))
    verdicts = db.latest_security_verdicts([r["id"] for r in rows])
    for r in rows:
        r["ai"] = verdicts.get(r["id"])
        r["ai_running"] = r["id"] in _analysing
    return {"incidents": [_with_link(request, r) for r in rows], "total": total}


@router.get("/security/incidents/{incident_id}")
def get_incident(request: Request, incident_id: int):
    inc = _db(request).get_security_incident(incident_id)
    if not inc:
        return JSONResponse({"error": "Incident not found"}, status_code=404)
    return _with_link(request, inc)


@router.post("/security/incidents/{incident_id}/status")
async def set_incident_status(request: Request, incident_id: int):
    body = await request.json()
    status = (body or {}).get("status", "")
    if status not in _STATUSES:
        return JSONResponse({"error": "Unknown status"}, status_code=400)
    user = request.session.get("username", "")
    if not _db(request).set_security_status(incident_id, status, user):
        return JSONResponse({"error": "Incident not found"}, status_code=404)
    _audit(request, "security_incident_status", f"incident={incident_id} status={status}")
    return {"status": status}


def _ai_ready(settings) -> str | None:
    """Why AI analysis cannot run, or None."""
    ai = settings.ai
    if not ai.analysis_enabled:
        return "AI analysis of incidents is turned off"
    if not ai.url:
        return "Set the LLM URL first"
    return None


@router.get("/security/incidents/{incident_id}/analyses")
def get_analyses(request: Request, incident_id: int):
    db = _db(request)
    if not db.get_security_incident(incident_id):
        return JSONResponse({"error": "Incident not found"}, status_code=404)
    return {"analyses": db.list_security_analyses(incident_id),
            "running": incident_id in _analysing,
            "unavailable": _ai_ready(_settings(request))}


@router.post("/security/incidents/{incident_id}/analyze")
async def analyze(request: Request, incident_id: int):
    settings = _settings(request)
    why = _ai_ready(settings)
    if why:
        return JSONResponse({"error": why}, status_code=400)
    db = _db(request)
    if not db.get_security_incident(incident_id):
        return JSONResponse({"error": "Incident not found"}, status_code=404)
    from glogarch.ai import llm
    why = llm.budget_left(settings.ai, db.ai_usage())
    if why:
        return JSONResponse({"error": why}, status_code=429)
    body = {}
    try:
        body = await request.json() or {}
    except ValueError:
        body = {}
    lang = body.get("lang") if body.get("lang") in _LANGS else "en"
    with _analysing_lock:
        if incident_id in _analysing:
            return JSONResponse({"error": "An AI analysis of this incident is already running"}, status_code=409)
        _analysing.add(incident_id)
    user = request.session.get("username", "")
    _audit(request, "security_ai_analysis", f"incident={incident_id} trigger=manual lang={lang}")

    def _work():
        from glogarch.security.ai_analysis import analyze_incident
        try:
            asyncio.run(analyze_incident(settings, db, incident_id, lang=lang, trigger="manual", username=user))
        except Exception as e:
            log.warning("Incident AI analysis crashed", incident=incident_id, error=str(e))
        finally:
            with _analysing_lock:
                _analysing.discard(incident_id)

    asyncio.get_running_loop().run_in_executor(None, _work)
    return JSONResponse({"status": "running"}, status_code=202)


def _detector_rows(cfg: SecurityConfig) -> list[dict]:
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


@router.get("/security/overview")
def overview(request: Request):
    settings = _settings(request)
    cfg = settings.security
    db = _db(request)
    now = datetime.utcnow()
    runs = db.list_security_runs(limit=10)
    last_done = next((r for r in runs if r["status"] in ("ok", "partial")), None)
    next_run = None
    sched = getattr(request.app.state, "scheduler", None)
    if sched is not None:
        try:
            job = sched.scheduler.get_job(sched.SECURITY_JOB_ID)
            if job and job.next_run_time:
                next_run = job.next_run_time.isoformat()
        except Exception as e:
            log.debug("Could not read the security job", error=str(e))
    return {
        "enabled": cfg.enabled,
        "server": cfg.server or settings.default_server,
        "servers": [s.name for s in settings.servers],
        "settings": cfg.model_dump(exclude={"detectors"}),
        "detectors": _detector_rows(cfg),
        "counts_24h": db.security_counts(now - timedelta(hours=24)),
        "counts_7d": db.security_counts(now - timedelta(days=7)),
        "runs": runs,
        "coverage": (last_done or {}).get("coverage", []),
        "coverage_at": (last_done or {}).get("finished_at"),
        "next_run": next_run,
        "running": _run_lock.locked(),
        "ai": {"analysis_enabled": settings.ai.analysis_enabled, "configured": bool(settings.ai.url),
               "chat_enabled": settings.ai.enabled},
    }


@router.post("/security/run")
async def run_now(request: Request):
    settings = _settings(request)
    if not settings.servers:
        return JSONResponse({"error": "No Graylog server configured"}, status_code=400)
    if not _run_lock.acquire(blocking=False):
        return JSONResponse({"error": "A security analysis is already running"}, status_code=409)
    db = _db(request)
    _audit(request, "security_run_now", f"server={settings.security.server or settings.default_server}")

    def _work():
        from glogarch.security.runner import run_security_analysis
        try:
            return asyncio.run(run_security_analysis(settings, db, source="manual"))
        finally:
            _run_lock.release()

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _work)


@router.post("/security/settings")
async def save_settings(request: Request):
    body = await request.json() or {}
    settings = _settings(request)
    cur = settings.security.model_dump()
    merged = {**cur, **{k: v for k, v in body.items() if k in cur and k != "detectors"}}
    if "detectors" in body:
        known = {d.id for d in DETECTORS}
        dets = {}
        for k, v in (body.get("detectors") or {}).items():
            if k not in known or not isinstance(v, dict):
                continue
            entry = {}
            if "enabled" in v:
                entry["enabled"] = bool(v["enabled"])
            if v.get("min_count") not in (None, ""):
                entry["min_count"] = max(1, int(v["min_count"]))
            if "exclude" in v:
                entry["exclude"] = str(v["exclude"] or "")[:500]
            dets[k] = entry
        merged["detectors"] = dets
    try:
        new = SecurityConfig(**merged)
    except Exception as e:
        return JSONResponse({"error": f"Invalid settings: {e}"}, status_code=400)
    if new.server and not settings.has_server(new.server):
        return JSONResponse({"error": "Unknown server"}, status_code=400)
    if new.notify_min_severity not in (*SEVERITIES, "off") or new.ai_auto_min_severity not in SEVERITIES:
        return JSONResponse({"error": "Unknown severity"}, status_code=400)
    new.ai_auto_max_per_run = max(1, min(int(new.ai_auto_max_per_run), 10))
    new.interval_minutes = max(5, min(int(new.interval_minutes), 1440))
    new.window_minutes = max(5, min(int(new.window_minutes), 1440))

    from glogarch.core.config_writer import update_config

    def _mut(cfg):
        cfg["security"] = new.model_dump()
    update_config(_config_path(request), _mut)
    settings.security = new
    registered = False
    sched = getattr(request.app.state, "scheduler", None)
    if sched is not None:
        registered = sched.apply_security_schedule()
    _audit(request, "security_settings_saved",
           f"enabled={new.enabled} server={new.server or '(default)'} "
           f"interval={new.interval_minutes}m window={new.window_minutes}m "
           f"ai_auto={new.ai_auto}/{new.ai_auto_min_severity}/{new.ai_auto_max_per_run}")
    return {"status": "saved", "registered": registered}
