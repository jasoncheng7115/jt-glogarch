# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Alerting: Graylog event definitions + notifications, managed in bulk.

Every Graylog call here is made AS the logged-in user (web/gl_identity.py), never
with the service account in config.yaml. A change is always two steps: preview
(the server computes and keeps the plan) then apply (runs that exact plan as a
job, one definition at a time). See graylog/alerting.py for why each write
re-reads the definition and passes its current state.
"""

from __future__ import annotations

import asyncio
import re
import secrets
import threading
import time
import uuid
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from glogarch.core.models import JobRecord, JobStatus, JobType
from glogarch.graylog import alerting as gla
from glogarch.utils.logging import get_logger
from glogarch.utils.sanitize import sanitize
from glogarch.web import gl_identity

log = get_logger("web.alerting")
router = APIRouter()

_PLAN_TTL = 15 * 60
_plans: dict[str, dict] = {}
_plans_lock = threading.Lock()
_running: dict[str, str] = {}          # server name -> job id of the running batch


def _settings(request: Request):
    return request.app.state.settings


def _db(request: Request):
    return request.app.state.db


def _audit(request: Request, action: str, detail: str = "") -> None:
    try:
        ip = request.client.host if request.client else ""
        _db(request).audit(action, detail, request.session.get("username", ""), ip)
    except Exception as e:
        log.warning("Audit record could not be written - this operation is NOT in the audit log",
                    error=str(e))


def _server(request: Request, name: str | None):
    settings = _settings(request)
    name = (name or "").strip() or request.session.get("gl_server") or ""
    srv = next((s for s in settings.servers if s.name == name), None)
    if srv is None:
        try:
            srv = settings.get_server()
        except ValueError:
            srv = None
    return srv


def _need_signin(srv, why: str = "Sign in to Graylog to continue") -> JSONResponse:
    # 403, not 401: the page's fetch helper treats 401 as "jt-glogarch session
    # gone" and redirects to /login, which is not what happened here.
    return JSONResponse({"error": why, "need_signin": True,
                         "server": srv.name if srv else ""}, status_code=403)


def _ident(request: Request, srv):
    return gl_identity.get(request.session, srv.name) if srv else None


async def _call(request: Request, srv, fn, client_cls=None):
    """Run `fn(client)` as the signed-in user, mapping Graylog's auth errors."""
    ident = _ident(request, srv)
    if ident is None:
        return None, _need_signin(srv)
    try:
        async with (client_cls or gla.AlertingClient)(srv.url, ident.auth, srv.verify_ssl) as c:
            return await fn(c), None
    except gla.GraylogAuthError:
        gl_identity.drop(request.session, srv.name)
        return None, _need_signin(srv, "Graylog sign-in expired - sign in again")
    except gla.GraylogPermissionError as e:
        return None, JSONResponse({"error": str(e)}, status_code=403)
    except Exception as e:
        return None, JSONResponse({"error": sanitize(str(e))}, status_code=502)


def _save_plan(request: Request, plan: dict) -> str:
    pid = secrets.token_urlsafe(16)
    now = time.time()
    with _plans_lock:
        for k in [k for k, v in _plans.items() if now - v["at"] > _PLAN_TTL]:
            del _plans[k]
        plan.update(at=now, owner=request.session.get("gl_handle"))
        _plans[pid] = plan
    return pid


def _take_plan(request: Request, pid: str) -> dict | None:
    with _plans_lock:
        p = _plans.get(pid or "")
        if not p or time.time() - p["at"] > _PLAN_TTL or p["owner"] != request.session.get("gl_handle"):
            return None
        return _plans.pop(pid)


# --------------------------------------------------------------------------- #

@router.get("/alerting/servers")
def alerting_servers(request: Request):
    signed = gl_identity.signed_in_servers(request.session)
    default = _server(request, None)
    return {
        "items": [{"name": s.name, "url": s.url, "signed_in": s.name in signed,
                   "graylog_user": signed.get(s.name, "")} for s in _settings(request).servers],
        "default": default.name if default else "",
        "login_user": request.session.get("username", ""),
    }


@router.post("/alerting/signin")
async def alerting_signin(request: Request):
    body = await request.json()
    srv = _server(request, body.get("server"))
    if srv is None:
        return JSONResponse({"error": "Unknown server"}, status_code=404)
    user = (body.get("username") or "").strip()
    pw = body.get("password") or ""
    if not user or not pw:
        return JSONResponse({"error": "Username and password are required"}, status_code=400)
    host = request.client.host if request.client else ""
    try:
        d = await gla.create_session(srv.url, user, pw, srv.verify_ssl, host)
    except gla.GraylogAuthError as e:
        _audit(request, "alerting_signin_failed", f"Graylog user {user} @ {srv.name}")
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": sanitize(str(e))}, status_code=502)
    gl_identity.put(request.session, srv.name, gl_identity.Identity(
        kind="session", secret=d["session_id"], username=d.get("username") or user,
        server_url=srv.url, verify_ssl=srv.verify_ssl,
        expires_at=gl_identity.parse_valid_until(d.get("valid_until"))))
    _audit(request, "alerting_signin", f"Graylog user {user} @ {srv.name}")
    return {"status": "ok", "graylog_user": d.get("username") or user}


@router.get("/alerting/data")
async def alerting_data(request: Request, server: str = ""):
    srv = _server(request, server)
    if srv is None:
        return JSONResponse({"error": "No Graylog server configured"}, status_code=404)

    async def fn(c):
        defs, notifs = await asyncio.gather(c.list_definitions(), c.list_notifications())
        return defs, notifs

    out, err = await _call(request, srv, fn)
    if err:
        return err
    defs, notifs = out
    used: dict[str, int] = {}
    for d in defs:
        for nid in gla.notif_ids(d):
            used[nid] = used.get(nid, 0) + 1
    ident = _ident(request, srv)
    return {
        "server": srv.name,
        "graylog_user": ident.username if ident else "",
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "definitions": [gla.summarize(d) for d in defs],
        "notifications": [{"id": n.get("id"), "title": n.get("title") or "",
                           "description": n.get("description") or "",
                           "type": (n.get("config") or {}).get("type") or "",
                           "used_by": used.get(n.get("id"), 0)} for n in notifs],
        "running_job": _running.get(srv.name),
    }


_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _web_url(api_url: str) -> str:
    """Graylog's web UI base from the configured API URL (".../api" or bare)."""
    u = (api_url or "").rstrip("/")
    return u[:-4] if u.endswith("/api") else u


@router.get("/alerting/definition")
async def alerting_definition(request: Request, server: str = "", id: str = ""):
    """One definition, read live as the signed-in user, for the detail dialog."""
    srv = _server(request, server)
    if srv is None:
        return JSONResponse({"error": "Unknown server"}, status_code=404)
    if not _ID_RE.match(id or ""):
        return JSONResponse({"error": "Invalid event definition id"}, status_code=400)

    async def fn(c):
        return await asyncio.gather(c.get_definition(id), c.stream_titles())

    out, err = await _call(request, srv, fn)
    if err:
        return err
    defn, streams = out
    return {"definition": defn, "streams": streams, "graylog_url": _web_url(srv.url)}


@router.post("/alerting/preview")
async def alerting_preview(request: Request):
    body = await request.json()
    srv = _server(request, body.get("server"))
    if srv is None:
        return JSONResponse({"error": "Unknown server"}, status_code=404)
    try:
        action = gla.Action.from_dict(body.get("action") or {})
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    ids = [str(i) for i in (body.get("definition_ids") or []) if i]
    if not ids:
        return JSONResponse({"error": "Select at least one event definition"}, status_code=400)

    async def fn(c):
        return await asyncio.gather(c.list_definitions(), c.list_notifications())

    out, err = await _call(request, srv, fn)
    if err:
        return err
    defs, notifs = out
    titles = {n.get("id"): n.get("title") or "" for n in notifs}
    wanted = set(action.ids) | ({action.src, action.dst} - {""})
    unknown = sorted(wanted - set(titles))
    if unknown:
        return JSONResponse({"error": "Notification not found in Graylog: " + ", ".join(unknown)},
                            status_code=400)
    p = gla.plan(defs, ids, action)
    pid = _save_plan(request, {"kind": "change", "server": srv.name, "action": action,
                               "items": p["change"], "describe": action.describe(titles)})
    return {"plan_id": pid, "describe": action.describe(titles), **p}


@router.get("/alerting/batches")
def alerting_batches(request: Request, server: str = ""):
    srv = _server(request, server)
    if srv is None:
        return {"items": []}
    return {"items": _db(request).list_alerting_batches(srv.name)}


@router.get("/alerting/batches/{batch_id}")
def alerting_batch_detail(request: Request, batch_id: str):
    return {"items": _db(request).list_alerting_changes(batch_id)}


@router.post("/alerting/undo-preview")
async def alerting_undo_preview(request: Request):
    body = await request.json()
    batch_id = (body.get("batch_id") or "").strip()
    rows = _db(request).list_alerting_changes(batch_id)
    if not rows:
        return JSONResponse({"error": "Batch not found"}, status_code=404)
    srv = _server(request, rows[0]["server"])
    if srv is None or srv.name != rows[0]["server"]:
        return JSONResponse({"error": "That batch's Graylog server is no longer configured"},
                            status_code=404)
    items = gla.restore_items(rows)
    if not items:
        return JSONResponse({"error": "Nothing in this batch can be undone"}, status_code=400)

    async def fn(c):
        return await c.list_definitions()

    defs, err = await _call(request, srv, fn)
    if err:
        return err
    by_id = {d.get("id"): d for d in defs}
    change, skipped = [], []
    for it in items:
        d = by_id.get(it["id"])
        if d is None:
            skipped.append({"id": it["id"], "title": it["title"], "reason": "Not found in Graylog"})
        elif gla.notif_ids(d) != it["expect"]:
            skipped.append({"id": it["id"], "title": it["title"],
                            "reason": "Notifications changed since that batch"})
        else:
            change.append({**it, "state": str(d.get("state") or "").upper(),
                           "before": it["expect"],
                           "after": [x.get("notification_id") for x in it["target"]]})
    pid = _save_plan(request, {"kind": "undo", "server": srv.name,
                               "action": gla.Action(type="restore"), "items": change,
                               "undoes": batch_id, "describe": f"undo batch {batch_id[:8]}"})
    return {"plan_id": pid, "describe": f"undo batch {batch_id[:8]}", "change": change,
            "unchanged": [], "skipped": skipped}


@router.post("/alerting/apply")
async def alerting_apply(request: Request):
    body = await request.json()
    plan = _take_plan(request, body.get("plan_id") or "")
    if plan is None:
        return JSONResponse({"error": "The preview expired or was already applied - preview again"},
                            status_code=409)
    srv = _server(request, plan["server"])
    ident = _ident(request, srv)
    if srv is None or ident is None:
        return _need_signin(srv)
    if not plan["items"]:
        return JSONResponse({"error": "Nothing to change"}, status_code=400)
    if srv.name in _running:
        return JSONResponse({"error": "Another alerting change is running on this server",
                             "job_id": _running[srv.name]}, status_code=409)

    db = _db(request)
    job_id = str(uuid.uuid4())
    login_user = request.session.get("username", "")
    who = f"{login_user} (Graylog: {ident.username})" if ident.username != login_user else login_user
    db.create_job(JobRecord(id=job_id, job_type=JobType.ALERTING, status=JobStatus.RUNNING,
                            source="manual:alerting", started_at=datetime.utcnow(),
                            messages_total=len(plan["items"])))
    _running[srv.name] = job_id
    _audit(request, "alerting_apply",
           f"{plan['describe']} on {len(plan['items'])} event definition(s) @ {srv.name} "
           f"as Graylog user {ident.username} (job {job_id})")

    from glogarch.web.routes.api import _cancel_flags

    def _run():
        import json as _json
        last = [0.0]

        def progress(done, total):
            now = time.time()
            if now - last[0] >= 1.0 or done == total:
                last[0] = now
                db.update_job(job_id, messages_done=done, progress_pct=round(done * 100.0 / total, 1))

        async def go():
            async with gla.AlertingClient(srv.url, ident.auth, srv.verify_ssl) as c:
                return await gla.apply_batch(
                    c, db, batch_id=job_id, server=srv.name, username=who,
                    items=plan["items"], action=plan["action"],
                    cancel_check=lambda: _cancel_flags.get(job_id, False),
                    progress_cb=progress, undoes_batch=plan.get("undoes"))

        try:
            r = asyncio.run(go())
            note = batch_note(plan["describe"], r)
            status = (JobStatus.CANCELLED if r["cancelled"] else
                      JobStatus.FAILED if r["aborted"] or (r["failed"] and not r["changed"]) else
                      JobStatus.COMPLETED)
            db.update_job(job_id, status=status, completed_at=datetime.utcnow(),
                          messages_done=r["changed"], error_message=note,
                          result_json=_json.dumps({"alerting": {
                              "server": srv.name, "describe": plan["describe"],
                              "changed": r["changed"], "unchanged": r["unchanged"],
                              "skipped": r["skipped"][:200], "failed": r["failed"][:200],
                              "undoes": plan.get("undoes")}}))
        except Exception as e:
            log.error("Alerting batch failed", job=job_id, error=str(e))
            db.update_job(job_id, status=JobStatus.FAILED, completed_at=datetime.utcnow(),
                          error_message=sanitize(str(e)))
        finally:
            _running.pop(srv.name, None)
            _cancel_flags.pop(job_id, None)

    asyncio.get_event_loop().run_in_executor(None, _run)
    return {"status": "started", "job_id": job_id}


def batch_note(describe: str, r: dict) -> str:
    """The job note. English, translated in the UI (srv_al_* keys)."""
    parts = [f"Alerting: {describe}",
             f"{r['changed']} event definition(s) changed, {r['unchanged']} already as requested"]
    if r["skipped"]:
        parts.append(f"{len(r['skipped'])} event definition(s) skipped")
    if r["failed"]:
        parts.append(f"⚠ {len(r['failed'])} event definition(s) failed (reasons in the job result)")
    if r["aborted"]:
        parts.append(f"⚠ Stopped: {r['aborted']}")
    if r["cancelled"]:
        parts.append("⚠ Cancelled by user - definitions already changed stay changed and can be undone")
    return ". ".join(parts)


@router.post("/alerting/test-notification")
async def alerting_test_notification(request: Request):
    body = await request.json()
    srv = _server(request, body.get("server"))
    nid = (body.get("notification_id") or "").strip()
    if srv is None or not nid:
        return JSONResponse({"error": "server and notification_id are required"}, status_code=400)

    async def fn(c):
        return await c.test_notification(nid)

    out, err = await _call(request, srv, fn)
    if err:
        return err
    ok, msg = out
    _audit(request, "alerting_test_notification", f"{nid} @ {srv.name}: {'ok' if ok else msg}")
    return {"ok": ok, "message": sanitize(msg)}
