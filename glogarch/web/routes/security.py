# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Security incidents API (added 1.20)."""
from __future__ import annotations

import asyncio
import re
import threading
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from glogarch.core.config import SecurityConfig
from glogarch.security.attack import ATTACK_VERSION, coverage_matrix, techniques_for
from glogarch.security.detectors import DETECTORS, PROBES, SEVERITIES
from glogarch.security.risk import CRITICALITY, match_asset, normalize_asset, score_entities
from glogarch.security.threat_intel import DEFAULT_FEEDS, FEEDS, describe, matcher_for
from glogarch.security.runner import parse_db_ts
from glogarch.utils.logging import get_logger
from glogarch.web.routes.api import _audit, _config_path, _db, _settings

log = get_logger("web.security")
router = APIRouter()

from glogarch.security.runner import RUN_LOCK as _run_lock   # shared with the scheduled run
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
    m = inc.get("metrics") or {}
    inc["attack"] = techniques_for(inc.get("detector", ""), inc.get("entity", ""), m.get("sigma_tags"))
    if str(inc.get("detector", "")).startswith("sigma:"):
        inc["detector_title"] = "Sigma: " + str(m.get("sigma_title") or inc["detector"])
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
    cases = db.cases_for_incidents([r["id"] for r in rows])
    assets = db.list_security_assets()
    ti = matcher_for(_settings(request), db)
    for r in rows:
        r["threat_intel"] = describe(ti.match(r["entity"])) if ti else []
        a = match_asset(r["entity"], assets)
        r["asset"] = {k: a[k] for k in ("id", "name", "criticality", "value", "kind")} if a else None
        r["ai"] = verdicts.get(r["id"])
        r["cases"] = cases.get(r["id"], [])
        r["ai_running"] = r["id"] in _analysing
    return {"incidents": [_with_link(request, r) for r in rows], "total": total}


def csv_cell(v) -> str:
    """A spreadsheet runs a cell starting with = + - @ (or tab / CR) as a formula:
    log-derived text (an account name, a signature) must never do that."""
    s = "" if v is None else str(v)
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s


@router.get("/security/incidents.csv")
def incidents_csv(request: Request, status: str = "", severity: str = "", detector: str = ""):
    import csv
    import io
    from fastapi.responses import Response
    if status and status not in _STATUSES:
        return JSONResponse({"error": "Unknown status"}, status_code=400)
    if severity and severity not in SEVERITIES:
        return JSONResponse({"error": "Unknown severity"}, status_code=400)
    db = _db(request)
    rows, total = db.list_security_incidents(status=status or None, severity=severity or None,
                                             detector=detector or None, limit=10000)
    verdicts = db.latest_security_verdicts([r["id"] for r in rows])
    cases = db.cases_for_incidents([r["id"] for r in rows])
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "severity", "detection", "entity", "entity_field", "external", "first_seen_utc",
                "last_seen_utc", "runs", "peak_count", "status", "status_by", "attack", "ai_verdict", "cases", "query"])
    for r in rows:
        m = r.get("metrics") or {}
        title = ("Sigma: " + str(m.get("sigma_title"))) if str(r["detector"]).startswith("sigma:") else r["detector"]
        w.writerow([csv_cell(x) for x in (
            r["id"], r["severity"], title, r["entity"], r["entity_field"], {1: "yes", 0: "no"}.get(r.get("external"), ""),
            r["first_seen"], r["last_seen"], r["runs"], r["peak_count"], r["status"], r.get("status_by") or "",
            " ".join(t["id"] for t in techniques_for(r["detector"], r["entity"], m.get("sigma_tags"))),
            (verdicts.get(r["id"]) or {}).get("verdict") or "",
            " ".join(f"#{c['id']}" for c in cases.get(r["id"], [])), r["query"])])
    _audit(request, "security_incidents_exported", f"rows={len(rows)} status={status or '*'} severity={severity or '*'}")
    name = f"jt-glogarch-incidents-{datetime.now().strftime('%Y%m%d-%H%M')}.csv"
    return Response("\ufeff" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


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


# --- overview (added 1.29) ---------------------------------------------------

@router.get("/security/summary")
def summary(request: Request, days: int = 14):
    """One read for the Overview tab: incidents opened per local day by severity,
    what is open now, the top detections and techniques, open cases, the riskiest
    entities and detection health. Everything comes from jt-glogarch's own DB."""
    days = max(7, min(int(days), 90))
    settings = _settings(request)
    db = _db(request)
    now_local = datetime.now().astimezone()
    start_local = (now_local - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    since_utc = start_local.astimezone(timezone.utc).replace(tzinfo=None)
    incs = db.security_incidents_since(since_utc - timedelta(days=1), limit=20000)
    labels = [(start_local + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]
    per_day = {d: {"high": 0, "medium": 0, "low": 0} for d in labels}
    det_count: dict[str, dict] = {}
    tech_count: dict[str, dict] = {}
    for i in incs:
        first = parse_db_ts(i.get("first_seen"))
        if first is None:
            continue
        day = first.replace(tzinfo=timezone.utc).astimezone(now_local.tzinfo).strftime("%Y-%m-%d")
        if day in per_day and i.get("severity") in per_day[day]:
            per_day[day][i["severity"]] += 1
        if day not in per_day:
            continue
        m = i.get("metrics") or {}
        key = i["detector"]
        d = det_count.setdefault(key, {"detector": key, "count": 0, "title": None})
        d["count"] += 1
        if key.startswith("sigma:"):
            d["title"] = "Sigma: " + str(m.get("sigma_title") or key)
        for te in techniques_for(key, i.get("entity", ""), m.get("sigma_tags")):
            t = tech_count.setdefault(te["id"], {**te, "count": 0})
            t["count"] += 1
    counts = db.open_security_counts()
    open_by = {s_: int(counts.get(s_, 0)) for s_ in ("high", "medium", "low")}
    cases = db.list_security_cases()
    runs = db.list_security_runs(limit=10)
    cov, ran, _ = recent_coverage(db)
    matrix = coverage_matrix(_detector_rows(settings.security), cov, ran)
    techs = [te for ta in matrix for te in ta["techniques"]]
    week = db.security_incidents_since(datetime.utcnow() - timedelta(days=7))
    risk_top = score_entities(week, db.list_security_assets(), db.latest_security_verdicts([i["id"] for i in week]),
                              limit=5, ti=matcher_for(settings, db))
    return {
        "days": labels, "per_day": [per_day[d] for d in labels],
        "open": open_by, "open_total": sum(open_by.values()),
        "cases": {"open": sum(1 for c in cases if c["status"] == "open"),
                  "in_progress": sum(1 for c in cases if c["status"] == "in_progress")},
        "top_detectors": sorted(det_count.values(), key=lambda x: -x["count"])[:6],
        "top_techniques": sorted(tech_count.values(), key=lambda x: -x["count"])[:6],
        "attack": {"watched": len({t["id"] for t in techs if t["state"] == "active"}),
                   "total": len({t["id"] for t in techs})},
        "risk_top": risk_top,
        "last_run": runs[0] if runs else None,
        "enabled": settings.security.enabled,
    }


# --- Sigma rules (added 1.27) -------------------------------------------------

_GROUP_FIELD = re.compile(r"^[A-Za-z0-9_@][A-Za-z0-9_.@-]{0,99}$")


def _sigma_convert(text: str, field_map: dict) -> tuple[dict | None, str]:
    from glogarch.security.sigma import SigmaError, convert, parse_rule
    try:
        rule = parse_rule(text)
        return {**rule, "query": convert(rule, field_map)}, ""
    except SigmaError as e:
        return None, str(e)


@router.get("/security/sigma")
def list_sigma(request: Request):
    cfg = _settings(request).security
    rules = _db(request).list_sigma_rules()
    for r in rules:
        r["attack"] = techniques_for(f"sigma:{r['id']}", "", r["tags"])
        r.pop("yaml", None)
    return {"rules": rules, "field_map": cfg.sigma_field_map, "max_rules": cfg.sigma_max_rules,
            "enabled": sum(1 for r in rules if r["enabled"])}


@router.get("/security/sigma/{rule_id}")
def get_sigma(request: Request, rule_id: int):
    r = _db(request).get_sigma_rule(rule_id)
    if not r:
        return JSONResponse({"error": "Sigma rule not found"}, status_code=404)
    return r


@router.post("/security/sigma/preview")
async def preview_sigma(request: Request):
    body = await request.json() or {}
    conv, err = _sigma_convert(str(body.get("yaml") or ""), _settings(request).security.sigma_field_map)
    if err:
        return JSONResponse({"error": err}, status_code=400)
    return {"title": conv["title"], "level": conv["level"], "query": conv["query"], "tags": conv["tags"],
            "attack": techniques_for("sigma:0", "", conv["tags"]), "logsource": conv["logsource"]}


@router.post("/security/sigma")
async def add_sigma(request: Request):
    body = await request.json() or {}
    text = str(body.get("yaml") or "")
    conv, err = _sigma_convert(text, _settings(request).security.sigma_field_map)
    if err:
        return JSONResponse({"error": err}, status_code=400)
    group_by = str(body.get("group_by") or "source").strip()
    if not _GROUP_FIELD.match(group_by):
        return JSONResponse({"error": "Group by: a Graylog field name"}, status_code=400)
    rid = _db(request).add_sigma_rule({**conv, "yaml": text, "group_by": group_by,
                                       "threshold": max(1, min(int(body.get("threshold") or 1), 1000000))},
                                      request.session.get("username", ""))
    _audit(request, "security_sigma_added", f"rule={rid} title={conv['title'][:120]}")
    return {"id": rid, "query": conv["query"]}


@router.post("/security/sigma/{rule_id}")
async def update_sigma(request: Request, rule_id: int):
    body = await request.json() or {}
    db = _db(request)
    cur = db.get_sigma_rule(rule_id)
    if not cur:
        return JSONResponse({"error": "Sigma rule not found"}, status_code=404)
    ch = {}
    if "enabled" in body:
        ch["enabled"] = bool(body["enabled"])
        if ch["enabled"] and not cur["query"]:
            return JSONResponse({"error": "This rule does not convert; fix it or the field map first"}, status_code=400)
        cap = int(_settings(request).security.sigma_max_rules)
        if ch["enabled"] and not cur["enabled"] and len(db.list_sigma_rules(enabled_only=True)) >= cap:
            return JSONResponse({"error": f"At most {cap} Sigma rules can be enabled"}, status_code=400)
    if "group_by" in body:
        g = str(body.get("group_by") or "").strip()
        if not _GROUP_FIELD.match(g):
            return JSONResponse({"error": "Group by: a Graylog field name"}, status_code=400)
        ch["group_by"] = g
    if "threshold" in body:
        ch["threshold"] = max(1, min(int(body.get("threshold") or 1), 1000000))
    db.update_sigma_rule(rule_id, ch)
    _audit(request, "security_sigma_updated", f"rule={rule_id} " + " ".join(f"{k}={v}" for k, v in ch.items()))
    return {"changed": sorted(ch)}


@router.delete("/security/sigma/{rule_id}")
def delete_sigma(request: Request, rule_id: int):
    r = _db(request).delete_sigma_rule(rule_id)
    if not r:
        return JSONResponse({"error": "Sigma rule not found"}, status_code=404)
    _audit(request, "security_sigma_deleted", f"rule={rule_id} title={r['title'][:120]}")
    return {"status": "deleted"}


@router.post("/security/sigma/{rule_id}/test")
async def test_sigma(request: Request, rule_id: int):
    """Counts the rule's matches in the last 24 h, per group: nothing is recorded."""
    settings = _settings(request)
    r = _db(request).get_sigma_rule(rule_id)
    if not r:
        return JSONResponse({"error": "Sigma rule not found"}, status_code=404)
    if not r["query"]:
        return JSONResponse({"error": "This rule does not convert; fix it or the field map first"}, status_code=400)
    from glogarch.graylog.client import GraylogClient
    from glogarch.ratelimit.limiter import RateLimiter
    from glogarch.security.engine import build_query
    from glogarch.security.graylog_fetch import make_fetch
    try:
        server = settings.get_server(settings.security.server or None)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    try:
        async with GraylogClient(server, RateLimiter(settings.rate_limit)) as c:
            rows = await make_fetch(c)(build_query(r["query"], settings.security.exclude_query), r["group_by"],
                                       (("count", None),), now - timedelta(hours=24), now, 20)
    except Exception as e:
        return JSONResponse({"error": f"The test query failed: {str(e)[:300]}"}, status_code=502)
    return {"rows": rows, "total": sum(int(x.get("count") or 0) for x in rows), "query": r["query"]}


@router.post("/security/sigma-fieldmap")
async def save_sigma_fieldmap(request: Request):
    body = await request.json() or {}
    from glogarch.security.sigma import parse_field_map
    fmap, errors = parse_field_map(str(body.get("text") or ""))
    if errors:
        return JSONResponse({"error": "; ".join(errors[:5])}, status_code=400)
    settings = _settings(request)
    new = settings.security.model_copy(update={"sigma_field_map": fmap})
    from glogarch.core.config_writer import update_config

    def _mut(cfg):
        cfg["security"] = new.model_dump()
    update_config(_config_path(request), _mut)
    settings.security = new
    # every stored rule is converted again with the new map
    db = _db(request)
    changed = 0
    for r in db.list_sigma_rules():
        full = db.get_sigma_rule(r["id"])
        conv, err = _sigma_convert(full["yaml"], fmap)
        q = conv["query"] if conv else ""
        if q != full["query"] or err != full["error"]:
            db.update_sigma_rule(r["id"], {"query": q, "error": err, **({"enabled": False} if err else {})})
            changed += 1
    _audit(request, "security_sigma_fieldmap", f"fields={len(fmap)} rules_reconverted={changed}")
    return {"fields": len(fmap), "reconverted": changed}


# --- assets and risk (added 1.25) -----------------------------------------------

_ASSET_CAPS = {"name": 200, "owner": 100, "notes": 2000}


def _asset_input(body: dict) -> tuple[dict, str | None]:
    kind = str(body.get("kind") or "")
    value, err = normalize_asset(kind, body.get("value"))
    if err:
        return {}, err
    crit = body.get("criticality") or "medium"
    if crit not in CRITICALITY:
        return {}, "Unknown criticality"
    out = {"kind": kind, "value": value, "criticality": crit}
    for k, cap in _ASSET_CAPS.items():
        out[k] = str(body.get(k) or "").strip()[:cap]
    return out, None


@router.get("/security/assets")
def list_assets(request: Request):
    return {"assets": _db(request).list_security_assets()}


@router.post("/security/assets")
async def save_asset(request: Request):
    body = await request.json() or {}
    data, err = _asset_input(body)
    if err:
        return JSONResponse({"error": err}, status_code=400)
    aid = body.get("id")
    try:
        rid = _db(request).upsert_security_asset(asset_id=int(aid) if aid else None, **data)
    except Exception as e:   # (kind, value) already belongs to another asset
        if "UNIQUE" in str(e):
            return JSONResponse({"error": "That asset already exists"}, status_code=409)
        raise
    if rid is None:
        return JSONResponse({"error": "Asset not found"}, status_code=404)
    _audit(request, "security_asset_saved", f"asset={rid} {data['kind']}={data['value']} criticality={data['criticality']}")
    return {"id": rid}


@router.post("/security/assets/import")
async def import_assets(request: Request):
    """One asset per line: kind,value,name,criticality,owner (name onwards optional)."""
    body = await request.json() or {}
    lines = [ln for ln in str(body.get("text") or "").splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    if len(lines) > 2000:
        return JSONResponse({"error": "At most 2000 lines at a time"}, status_code=400)
    db = _db(request)
    saved, errors = 0, []
    for n, ln in enumerate(lines, 1):
        parts = [x.strip() for x in ln.split(",")]
        keys = ("kind", "value", "name", "criticality", "owner")
        data, err = _asset_input(dict(zip(keys, parts)))
        if err:
            errors.append(f"line {n}: {err}")
            continue
        db.upsert_security_asset(**data)
        saved += 1
    _audit(request, "security_assets_imported", f"saved={saved} errors={len(errors)}")
    return {"saved": saved, "errors": errors[:50]}


@router.delete("/security/assets/{asset_id}")
def delete_asset(request: Request, asset_id: int):
    row = _db(request).delete_security_asset(asset_id)
    if not row:
        return JSONResponse({"error": "Asset not found"}, status_code=404)
    _audit(request, "security_asset_deleted", f"asset={asset_id} {row['kind']}={row['value']}")
    return {"status": "deleted"}


@router.get("/security/risk")
def risk(request: Request, days: int = 7):
    days = max(1, min(int(days), 90))
    db = _db(request)
    incs = db.security_incidents_since(datetime.utcnow() - timedelta(days=days))
    ranked = score_entities(incs, db.list_security_assets(), db.latest_security_verdicts([i["id"] for i in incs]),
                            ti=matcher_for(_settings(request), db))
    return {"days": days, "entities": ranked, "incidents": len(incs)}


# --- threat-intel lists (added 1.28) --------------------------------------------

@router.get("/security/ti")
def ti_status(request: Request):
    cfg = _settings(request).security
    st = _db(request).ti_status()
    return {"enabled": cfg.ti_enabled, "refresh_hours": cfg.ti_refresh_hours,
            "feeds": [{"id": f, "name": d["name"], "about": d["about"], "url": d["url"],
                       "selected": f in cfg.ti_feeds, **{k: (st.get(f) or {}).get(k) for k in
                                                        ("refreshed_at", "count", "error", "tried_at")}}
                      for f, d in FEEDS.items()]}


@router.post("/security/ti/settings")
async def ti_save(request: Request):
    body = await request.json() or {}
    settings = _settings(request)
    feeds = [f for f in (body.get("feeds") or []) if f in FEEDS] if "feeds" in body else list(settings.security.ti_feeds)
    new = settings.security.model_copy(update={
        "ti_enabled": bool(body.get("enabled", settings.security.ti_enabled)), "ti_feeds": feeds,
        "ti_refresh_hours": max(1, min(int(body.get("refresh_hours") or settings.security.ti_refresh_hours), 168))})
    from glogarch.core.config_writer import update_config

    def _mut(cfg):
        cfg["security"] = new.model_dump()
    update_config(_config_path(request), _mut)
    settings.security = new
    sched = getattr(request.app.state, "scheduler", None)
    if sched is not None:
        sched.apply_security_schedule()
    _audit(request, "security_ti_settings", f"enabled={new.ti_enabled} feeds={','.join(feeds)} every={new.ti_refresh_hours}h")
    return {"status": "saved"}


@router.post("/security/ti/refresh")
async def ti_refresh(request: Request):
    settings = _settings(request)
    if not settings.security.ti_enabled:
        return JSONResponse({"error": "Threat intelligence is turned off"}, status_code=400)
    from glogarch.security.threat_intel import refresh
    _audit(request, "security_ti_refresh", f"feeds={','.join(settings.security.ti_feeds)}")
    return {"result": await refresh(_db(request), settings.security.ti_feeds)}


# --- investigations / cases (added 1.24) ---------------------------------------

_CASE_LIMITS = {"title": 200, "assignee": 100, "description": 8000, "resolution": 8000}


def _case_input(body: dict, partial: bool) -> tuple[dict, str | None]:
    out = {}
    for k, cap in _CASE_LIMITS.items():
        if k in body:
            out[k] = str(body.get(k) or "").strip()[:cap]
    if "severity" in body:
        out["severity"] = body.get("severity")
        if out["severity"] not in SEVERITIES:
            return {}, "Unknown severity"
    if "status" in body:
        out["status"] = body.get("status")
        if out["status"] not in ("open", "in_progress", "closed"):
            return {}, "Unknown status"
    if (not partial or "title" in out) and not out.get("title"):
        return {}, "A case needs a title"
    return out, None


def _ids(v) -> list[int]:
    try:
        return [int(x) for x in (v or [])][:500]
    except (TypeError, ValueError):
        return []


@router.get("/security/cases")
def list_cases(request: Request, status: str = ""):
    if status and status not in ("open", "in_progress", "closed"):
        return JSONResponse({"error": "Unknown status"}, status_code=400)
    return {"cases": _db(request).list_security_cases(status or None)}


@router.post("/security/cases")
async def create_case(request: Request):
    body = await request.json() or {}
    data, err = _case_input({"severity": "medium", **body}, partial=False)
    if err:
        return JSONResponse({"error": err}, status_code=400)
    user = request.session.get("username", "")
    ids = _ids(body.get("incident_ids"))
    cid = _db(request).create_security_case(data["title"], data["severity"], data.get("description", ""),
                                            user, ids)
    _audit(request, "security_case_created", f"case={cid} incidents={ids} title={data['title'][:120]}")
    return {"id": cid}


@router.get("/security/cases/{case_id}")
def get_case(request: Request, case_id: int):
    c = _db(request).get_security_case(case_id)
    if not c:
        return JSONResponse({"error": "Case not found"}, status_code=404)
    verdicts = _db(request).latest_security_verdicts([i["id"] for i in c["incidents"]])
    for i in c["incidents"]:
        _with_link(request, i)
        i["ai"] = verdicts.get(i["id"])
    return c


@router.post("/security/cases/{case_id}")
async def update_case(request: Request, case_id: int):
    body = await request.json() or {}
    data, err = _case_input(body, partial=True)
    if err:
        return JSONResponse({"error": err}, status_code=400)
    changed = _db(request).update_security_case(case_id, data, request.session.get("username", ""))
    if changed is None:
        return JSONResponse({"error": "Case not found"}, status_code=404)
    if changed:
        _audit(request, "security_case_updated",
               f"case={case_id} " + " ".join(f"{k}={data[k]}" if k not in ("description", "resolution")
                                             else f"{k}=(changed)" for k in changed))
    return {"changed": changed}


@router.post("/security/cases/{case_id}/notes")
async def add_case_note(request: Request, case_id: int):
    body = await request.json() or {}
    text = str(body.get("body") or "").strip()
    if not text:
        return JSONResponse({"error": "Write a note first"}, status_code=400)
    nid = _db(request).add_security_case_note(case_id, text, request.session.get("username", ""))
    if nid is None:
        return JSONResponse({"error": "Case not found"}, status_code=404)
    _audit(request, "security_case_note", f"case={case_id} note={nid}")
    return {"id": nid}


@router.post("/security/cases/{case_id}/incidents")
async def link_case_incidents(request: Request, case_id: int):
    body = await request.json() or {}
    ids = _ids(body.get("incident_ids"))
    if not ids:
        return JSONResponse({"error": "No incidents given"}, status_code=400)
    remove = bool(body.get("remove"))
    done = _db(request).link_security_case_incidents(case_id, ids, request.session.get("username", ""), remove)
    if done is None:
        return JSONResponse({"error": "Case not found"}, status_code=404)
    _audit(request, "security_case_incidents", f"case={case_id} {'removed' if remove else 'added'}={done}")
    return {"changed": done}


def recent_coverage(db, hours: int = 24) -> tuple[list[dict], bool, str | None]:
    """Coverage merged over the finished runs of the last `hours`: a probe field
    counts its events across them, and is an error only if it failed in all.
    One quiet hour (no WAF traffic at 3 am) must not read as "no data"."""
    since = datetime.utcnow() - timedelta(hours=hours)
    runs = [r for r in db.list_security_runs(limit=500) if r["status"] in ("ok", "partial")
            and (parse_db_ts(r.get("started_at")) or datetime.min) >= since]
    merged: dict[tuple, dict] = {}
    for r in runs:
        for c in r.get("coverage") or []:
            m = merged.setdefault((c.get("probe"), c.get("field")),
                                  {"probe": c.get("probe"), "field": c.get("field"), "events": 0, "missing": 0,
                                   "error": "", "ok_runs": 0, "err_runs": 0})
            if c.get("error"):
                m["err_runs"] += 1
                m["error"] = c["error"]
            else:
                m["ok_runs"] += 1
                m["events"] += int(c.get("events") or 0)
                m["missing"] += int(c.get("missing") or 0)
    out = []
    for m in merged.values():
        if m["ok_runs"]:
            m["error"] = ""
        out.append({k: m[k] for k in ("probe", "field", "events", "missing", "error")})
    return out, bool(runs), (runs[0].get("finished_at") if runs else None)


@router.get("/security/attack")
def attack_coverage(request: Request):
    """MITRE ATT&CK techniques the detections map to, and whether each is
    really watched here (detection on AND this site's logs carried its field
    in the last 24 hours)."""
    settings = _settings(request)
    cov, ran, at = recent_coverage(_db(request))
    return {"version": ATTACK_VERSION, "coverage_at": at,
            "tactics": coverage_matrix(_detector_rows(settings.security), cov, ran)}


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
            return asyncio.run(run_security_analysis(settings, db, source="manual", ai_inline=False))
        finally:
            _run_lock.release()

    loop = asyncio.get_running_loop()
    res = await loop.run_in_executor(None, _work)
    changes = res.pop("_changes", None)
    if changes:
        # the AI may take minutes: never hold the request (or the lock) for it
        def _ai():
            from glogarch.security.runner import _auto_ai_analysis
            try:
                asyncio.run(_auto_ai_analysis(settings, db, changes))
            except Exception as e:
                log.warning("Automatic AI analysis after Run now failed", error=str(e))
        loop.run_in_executor(None, _ai)
    return res


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
    new.ai_notify_verdicts = [v for v in new.ai_notify_verdicts if v in ("malicious", "suspicious", "benign", "unclear")]
    new.interval_minutes = max(5, min(int(new.interval_minutes), 1440))
    new.window_minutes = max(5, min(int(new.window_minutes), 1440))
    # an empty box arrives as 0: retention 0 would delete every incident at the next run.
    # 0/empty keeps what is stored (never shorten retention by accident), then clamp.
    old = settings.security
    new.retention_days = max(7, min(int(new.retention_days or old.retention_days), 3650))
    new.reopen_hours = max(1.0, min(float(new.reopen_hours or old.reopen_hours), 720.0))
    new.renotify_hours = max(1.0, min(float(new.renotify_hours or old.renotify_hours), 720.0))
    new.new_days = max(1, min(int(new.new_days or old.new_days), 365))
    new.sigma_max_rules = max(0, min(int(new.sigma_max_rules), 500))

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
