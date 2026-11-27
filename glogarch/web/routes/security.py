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
from glogarch.security.detectors import DETECTORS, SEVERITIES
from glogarch.security.risk import CRITICALITY, match_asset, normalize_asset, score_entities
from glogarch.security.threat_intel import FEEDS, describe, matcher_for
from glogarch.security.runner import parse_db_ts
from glogarch.security.coverage import detector_rows as _detector_rows, recent_coverage
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


_SINCE_DAYS = {"1": 1, "7": 7, "30": 30, "90": 90}


def _since(days: str) -> str | None:
    """'1' / '7' / '30' / '90' days back as a stored timestamp; '' = all time."""
    from glogarch.core.database import _dt_to_str
    n = _SINCE_DAYS.get(str(days or ""))
    return _dt_to_str(datetime.utcnow() - timedelta(days=n)) if n else None


@router.get("/security/incidents/detectors")
def incident_detectors(request: Request):
    """The detections that have incidents (with their titles), for the list's filter."""
    out = []
    for d in _db(request).security_incident_detectors():
        out.append({**d, "title": ("Sigma: " + d["title"]) if d["title"] else ""})
    return {"detectors": out}


@router.get("/security/incidents")
def list_incidents(request: Request, status: str = "", severity: str = "", detector: str = "",
                   limit: int = 100, offset: int = 0, q: str = "", days: str = ""):
    if status and status not in _STATUSES:
        return JSONResponse({"error": "Unknown status"}, status_code=400)
    if severity and severity not in SEVERITIES:
        return JSONResponse({"error": "Unknown severity"}, status_code=400)
    db = _db(request)
    rows, total = db.list_security_incidents(
        status=status or None, severity=severity or None, detector=detector or None,
        limit=max(1, min(int(limit), 500)), offset=max(0, int(offset)), q=q, since=_since(days))
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


EXPORT_FORMATS = ("csv", "xlsx", "ods", "json", "md")
_EXPORT_COLS = ["id", "severity", "detection", "entity", "entity_field", "external", "first_seen_utc",
                "last_seen_utc", "runs", "peak_count", "status", "status_by", "attack", "ai_verdict", "cases", "query"]


def _export_rows(request: Request, status: str, severity: str, detector: str, q: str, days: str) -> list[list]:
    db = _db(request)
    rows, _ = db.list_security_incidents(status=status or None, severity=severity or None,
                                         detector=detector or None, limit=10000, q=q, since=_since(days))
    verdicts = db.latest_security_verdicts([r["id"] for r in rows])
    cases = db.cases_for_incidents([r["id"] for r in rows])
    out = []
    for r in rows:
        m = r.get("metrics") or {}
        title = ("Sigma: " + str(m.get("sigma_title"))) if str(r["detector"]).startswith("sigma:") else r["detector"]
        out.append([r["id"], r["severity"], title, r["entity"], r["entity_field"],
                    {1: "yes", 0: "no"}.get(r.get("external"), ""), r["first_seen"], r["last_seen"], r["runs"],
                    r["peak_count"], r["status"], r.get("status_by") or "",
                    " ".join(t["id"] for t in techniques_for(r["detector"], r["entity"], m.get("sigma_tags"))),
                    (verdicts.get(r["id"]) or {}).get("verdict") or "",
                    " ".join(f"#{c['id']}" for c in cases.get(r["id"], [])), r["query"]])
    return out


def xlsx_bytes(header: list[str], rows: list[list]) -> bytes:
    """A minimal .xlsx (one sheet, bold header, frozen first row) written with the standard
    library. Every cell is an inline string or a number: log text can never be a formula."""
    import io
    import zipfile
    from html import escape   # text into XML: & < > (bandit B406 is about parsing, not this)

    def col(i):
        s_ = ""
        i += 1
        while i:
            i, r = divmod(i - 1, 26)
            s_ = chr(65 + r) + s_
        return s_

    def cell(ref, v, style=0):
        st = f' s="{style}"' if style else ""
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return f'<c r="{ref}"{st}><v>{v}</v></c>'
        txt = escape("" if v is None else str(v))
        txt = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", txt)[:32000]
        return f'<c r="{ref}" t="inlineStr"{st}><is><t xml:space="preserve">{txt}</t></is></c>'
    sheet_rows = ['<row r="1">' + "".join(cell(f"{col(i)}1", h, 1) for i, h in enumerate(header)) + "</row>"]
    for n, r in enumerate(rows, 2):
        sheet_rows.append(f'<row r="{n}">' + "".join(cell(f"{col(i)}{n}", v) for i, v in enumerate(r)) + "</row>")
    sheet = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
             '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" '
             'state="frozen"/></sheetView></sheetViews><sheetData>' + "".join(sheet_rows) + '</sheetData></worksheet>')
    files = {
        "[Content_Types].xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>',
        "_rels/.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        "xl/workbook.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="incidents" sheetId="1" r:id="rId1"/></sheets></workbook>',
        "xl/_rels/workbook.xml.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>',
        "xl/styles.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
            '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>'
            '<borders count="1"><border/></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            '<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
            '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs>'
            '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>',
        "xl/worksheets/sheet1.xml": sheet,
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, body in files.items():
            z.writestr(name, body)
    return buf.getvalue()


def ods_bytes(header: list[str], rows: list[list]) -> bytes:
    """A minimal OpenDocument spreadsheet (LibreOffice's own format), standard library only:
    the uncompressed mimetype first, a bold header row, numbers as floats, the rest as text
    (log text can never become a formula)."""
    import io
    import zipfile
    from html import escape   # text into XML: & < > (bandit B406 is about parsing, not this)

    def cell(v, head=False):
        st = ' table:style-name="hd"' if head else ""
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return f'<table:table-cell{st} office:value-type="float" office:value="{v}"><text:p>{v}</text:p></table:table-cell>'
        txt = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", escape("" if v is None else str(v)))
        return f'<table:table-cell{st} office:value-type="string"><text:p>{txt}</text:p></table:table-cell>'
    body = ['<table:table-row>' + "".join(cell(h, True) for h in header) + '</table:table-row>']
    body += ['<table:table-row>' + "".join(cell(v) for v in r) + '</table:table-row>' for r in rows]
    content = ('<?xml version="1.0" encoding="UTF-8"?><office:document-content '
               'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
               'xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" '
               'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
               'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
               'xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" office:version="1.2">'
               '<office:automatic-styles><style:style style:name="hd" style:family="table-cell">'
               '<style:text-properties fo:font-weight="bold"/></style:style></office:automatic-styles>'
               '<office:body><office:spreadsheet><table:table table:name="incidents">'
               f'<table:table-column table:number-columns-repeated="{len(header)}"/>'
               + "".join(body) + '</table:table></office:spreadsheet></office:body></office:document-content>')
    manifest = ('<?xml version="1.0" encoding="UTF-8"?><manifest:manifest '
                'xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.2">'
                '<manifest:file-entry manifest:full-path="/" manifest:version="1.2" '
                'manifest:media-type="application/vnd.oasis.opendocument.spreadsheet"/>'
                '<manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/></manifest:manifest>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(zipfile.ZipInfo("mimetype"), "application/vnd.oasis.opendocument.spreadsheet",
                   compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/manifest.xml", manifest, compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("content.xml", content, compress_type=zipfile.ZIP_DEFLATED)
    return buf.getvalue()


def _md_cell(v) -> str:
    return ("" if v is None else str(v)).replace("|", "\\|").replace("\n", " ").replace("`", "'")


@router.get("/security/incidents.csv")
def incidents_csv(request: Request, status: str = "", severity: str = "", detector: str = "", q: str = "",
                  days: str = ""):
    return incidents_export(request, "csv", status, severity, detector, q, days)


@router.get("/security/incidents/export")
def incidents_export(request: Request, format: str = "csv", status: str = "", severity: str = "",
                     detector: str = "", q: str = "", days: str = ""):
    """The incidents the list shows (its filters), as CSV, Excel, OpenDocument, JSON or Markdown (owner 2026-11-27:
    "多支援幾種匯出格式"). Log-derived text is never a formula: CSV cells are prefixed, the Excel
    cells are inline strings."""
    import csv
    import io
    import json as _json
    from fastapi.responses import Response
    if format not in EXPORT_FORMATS:
        return JSONResponse({"error": "Unknown export format"}, status_code=400)
    if status and status not in _STATUSES:
        return JSONResponse({"error": "Unknown status"}, status_code=400)
    if severity and severity not in SEVERITIES:
        return JSONResponse({"error": "Unknown severity"}, status_code=400)
    rows = _export_rows(request, status, severity, detector, q, days)
    _audit(request, "security_incidents_exported",
           f"rows={len(rows)} format={format} status={status or '*'} severity={severity or '*'}"
           f"{' detector=' + detector if detector else ''}{' q=' + q[:60] if q else ''}{' days=' + days if days else ''}")
    stem = f"jt-glogarch-incidents-{datetime.now().strftime('%Y%m%d-%H%M')}"
    if format == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(_EXPORT_COLS)
        for r in rows:
            w.writerow([csv_cell(x) for x in r])
        body, mt = "\ufeff" + buf.getvalue(), "text/csv; charset=utf-8"
    elif format == "xlsx":
        body, mt = xlsx_bytes(_EXPORT_COLS, rows), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif format == "ods":
        body, mt = ods_bytes(_EXPORT_COLS, rows), "application/vnd.oasis.opendocument.spreadsheet"
    elif format == "json":
        body = _json.dumps([dict(zip(_EXPORT_COLS, r)) for r in rows], ensure_ascii=False, indent=1)
        mt = "application/json; charset=utf-8"
    else:
        lines = ["| " + " | ".join(_EXPORT_COLS[:12]) + " |", "|" + "---|" * 12]
        lines += ["| " + " | ".join(_md_cell(x) for x in r[:12]) + " |" for r in rows]
        body, mt = "\n".join(lines) + "\n", "text/markdown; charset=utf-8"
    return Response(body, media_type=mt, headers={"Content-Disposition": f'attachment; filename="{stem}.{format}"'})


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
    if ai.llm() is None:
        return "Set up an LLM server first"
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
    why = llm.limits_left(settings.ai, settings.ai.llm(), db, request.session.get("username", ""))
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
        "settings": cfg.model_dump(exclude={"detectors", "field_map"}),
        "detectors": _detector_rows(cfg),
        "field_map": _field_map_view(cfg),
        "counts_24h": db.security_counts(now - timedelta(hours=24)),
        "counts_7d": db.security_counts(now - timedelta(days=7)),
        "runs": runs,
        "coverage": (last_done or {}).get("coverage", []),
        "coverage_at": (last_done or {}).get("finished_at"),
        "next_run": next_run,
        "running": _run_lock.locked(),
        "ai": {"analysis_enabled": settings.ai.analysis_enabled, "configured": settings.ai.llm() is not None,
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
    db = _db(request)
    rules = db.list_sigma_rules()
    # a rule taken from the SigmaHQ library links back to its source (DRL 1.1 credit)
    from glogarch.security.sigma_library import SOURCE_URL
    paths = {e["sigma_id"]: e["path"] for e in db.list_sigma_library()} if any(r.get("origin") == "library" for r in rules) else {}
    for r in rules:
        r["attack"] = techniques_for(f"sigma:{r['id']}", "", r["tags"])
        r.pop("yaml", None)
        p = paths.get(r.get("sigma_id")) if r.get("origin") == "library" else None
        r["source_url"] = SOURCE_URL.format(path=p) if p else None
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


@router.post("/security/sigma-bulk")
async def bulk_sigma(request: Request):
    """Enable or disable many rules at once (owner 2026-11-27, with select-all). Enabling stops at
    `sigma_max_rules`: the rest are reported, never silently left off."""
    body = await request.json() or {}
    if not isinstance(body.get("enabled"), bool):
        return JSONResponse({"error": "enabled: true or false"}, status_code=400)
    want = body["enabled"]
    ids = [int(x) for x in (body.get("ids") or [])[:5000] if str(x).isdigit()]
    db = _db(request)
    cap = int(_settings(request).security.sigma_max_rules)
    on = len(db.list_sigma_rules(enabled_only=True))
    changed, skipped = [], []
    for rid in ids:
        cur = db.get_sigma_rule(rid)
        if not cur:
            skipped.append({"id": rid, "reason": "not_found"})
            continue
        if bool(cur["enabled"]) == want:
            continue
        if want and not cur["query"]:
            skipped.append({"id": rid, "reason": "not_convertible"})
            continue
        if want and on >= cap:
            skipped.append({"id": rid, "reason": "cap"})
            continue
        db.update_sigma_rule(rid, {"enabled": want})
        on += 1 if want else -1
        changed.append(rid)
    if changed:
        _audit(request, "security_sigma_updated",
               f"bulk enabled={want} rules={','.join(map(str, changed[:200]))}{' ...' if len(changed) > 200 else ''}")
    return {"changed": changed, "skipped": skipped, "max_rules": cap, "enabled": on}


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
    # and the library, so its "converts" / "fields" columns follow the map too
    import json as _json

    from glogarch.security.sigma_library import convert_entry

    def _reconvert_library():
        rows = []
        for e in db.list_sigma_library(with_yaml=True):
            c = convert_entry(e["yaml"], fmap)
            rows.append((c["query"], c["error"], _json.dumps(c["fields"]), e["sigma_id"]))
        db.update_sigma_library_conversions(rows)
    await asyncio.to_thread(_reconvert_library)
    _audit(request, "security_sigma_fieldmap", f"fields={len(fmap)} rules_reconverted={changed}")
    return {"fields": len(fmap), "reconverted": changed}


# --- Sigma rule library (added 1.33) ------------------------------------------------

_LIB_STATES = ("all", "convertible", "fields_ok", "not_added", "added")


def _library_view(e: dict, gl_fields: set | None, added: dict) -> dict:
    from glogarch.security.sigma_library import SOURCE_URL
    missing = None if gl_fields is None else [f for f in e.get("fields") or [] if f not in gl_fields]
    return {k: e.get(k) for k in ("sigma_id", "title", "level", "status", "product", "category", "service",
                                   "author", "modified", "path", "query", "error", "fields")} | {
        "attack": techniques_for("sigma:0", "", e.get("tags") or []),
        "source_url": SOURCE_URL.format(path=e.get("path") or ""),
        "missing_fields": missing, "added_rule_id": added.get(e["sigma_id"])}


@router.get("/security/sigma-library")
def sigma_library(request: Request, q: str = "", product: str = "", level: str = "", state: str = "all",
                  offset: int = 0, limit: int = 50, ids_only: int = 0):
    import json as _json

    from glogarch.security.sigma_library import LICENSE, LICENSE_URL, PACKAGES
    cfg = _settings(request).security
    db = _db(request)
    meta = db.sigma_library_meta()
    try:
        gl_fields = set(_json.loads(meta["graylog_fields"])) if meta.get("graylog_fields") else None
    except ValueError:
        gl_fields = None
    added = {r["sigma_id"]: r["id"] for r in db.list_sigma_rules() if r.get("sigma_id")}
    entries = db.list_sigma_library()
    products: dict[str, int] = {}
    for e in entries:
        k = e.get("product") or e.get("category") or e.get("service") or "-"
        products[k] = products.get(k, 0) + 1
    ql = q.strip().lower()[:200]
    state = state if state in _LIB_STATES else "all"

    def keep(e):
        if product and product not in (e.get("product"), e.get("category"), e.get("service")) \
                and not (product == "-" and not (e.get("product") or e.get("category") or e.get("service"))):
            return False
        if level and e.get("level") != level:
            return False
        if ql and ql not in (e.get("title") or "").lower() and ql not in e["sigma_id"] \
                and not any(ql in t for t in e.get("tags") or []):
            return False
        if state == "convertible" and not e.get("query"):
            return False
        if state == "fields_ok" and (not e.get("query") or gl_fields is None
                                     or any(f not in gl_fields for f in e.get("fields") or [])):
            return False
        if state == "not_added" and e["sigma_id"] in added:
            return False
        if state == "added" and e["sigma_id"] not in added:
            return False
        return True

    hits = [e for e in entries if keep(e)]
    if ids_only:
        # "select every rule this filter matches" (owner 2026-11-27): the ids that can still be added
        return {"ids": [e["sigma_id"] for e in hits if e.get("query") and e["sigma_id"] not in added],
                "total": len(hits)}
    offset, limit = max(0, int(offset)), max(1, min(int(limit), 200))
    pub = {k: v for k, v in meta.items() if k != "graylog_fields"}
    pub["graylog_field_count"] = len(gl_fields) if gl_fields is not None else None
    return {"meta": pub,
            "settings": {"enabled": cfg.sigma_library_enabled, "package": cfg.sigma_library_package,
                         "auto_update": cfg.sigma_library_auto_update},
            "packages": [{"id": k, "about": v["about"]} for k, v in PACKAGES.items()],
            "license": LICENSE, "license_url": LICENSE_URL,
            "products": sorted(products.items(), key=lambda x: (-x[1], x[0])),
            "total": len(hits), "offset": offset,
            "items": [_library_view(e, gl_fields, added) for e in hits[offset:offset + limit]]}


@router.get("/security/sigma-library/{sigma_id}")
def sigma_library_entry(request: Request, sigma_id: str):
    e = _db(request).get_sigma_library_entry(sigma_id[:64])
    if not e:
        return JSONResponse({"error": "Not in the Sigma library"}, status_code=404)
    return {"sigma_id": e["sigma_id"], "title": e["title"], "yaml": e["yaml"], "query": e["query"], "error": e["error"]}


@router.post("/security/sigma-library/settings")
async def sigma_library_settings(request: Request):
    from glogarch.security.sigma_library import PACKAGES
    body = await request.json() or {}
    settings = _settings(request)
    cur = settings.security
    package = str(body.get("package") or cur.sigma_library_package)
    if package not in PACKAGES:
        return JSONResponse({"error": "Unknown Sigma package"}, status_code=400)
    new = cur.model_copy(update={
        "sigma_library_enabled": bool(body.get("enabled", cur.sigma_library_enabled)),
        "sigma_library_package": package,
        "sigma_library_auto_update": bool(body.get("auto_update", cur.sigma_library_auto_update))})
    from glogarch.core.config_writer import update_config

    def _mut(cfg):
        cfg["security"] = new.model_dump()
    update_config(_config_path(request), _mut)
    settings.security = new
    sched = getattr(request.app.state, "scheduler", None)
    if sched is not None:
        sched.apply_security_schedule()
    _audit(request, "security_sigma_library_settings",
           f"enabled={new.sigma_library_enabled} package={package} auto_update={new.sigma_library_auto_update}")
    return {"status": "saved"}


@router.post("/security/sigma-library/refresh")
async def sigma_library_refresh(request: Request):
    settings = _settings(request)
    if not settings.security.sigma_library_enabled:
        return JSONResponse({"error": "The Sigma library download is turned off"}, status_code=400)
    body = await request.json() or {}
    from glogarch.security.sigma_library import refresh
    res = await refresh(settings, _db(request), force=bool(body.get("force")))
    _audit(request, "security_sigma_library_refresh",
           f"status={res.get('status')} tag={res.get('tag', '')} count={res.get('count', '')} "
           f"updated_rules={len(res.get('updated_rules') or [])}")
    if res.get("status") == "error":
        return JSONResponse({"error": f"Sigma library download failed: {res['error']}"}, status_code=502)
    return res


@router.post("/security/sigma-library/add")
async def sigma_library_add(request: Request):
    """Adds library rules to this site's Sigma rules, DISABLED (the operator enables each)."""
    body = await request.json() or {}
    ids = [str(x)[:64] for x in (body.get("ids") or [])][:100]
    group_by = str(body.get("group_by") or "source").strip()
    if not _GROUP_FIELD.match(group_by):
        return JSONResponse({"error": "Group by: a Graylog field name"}, status_code=400)
    threshold = max(1, min(int(body.get("threshold") or 1), 1000000))
    db = _db(request)
    fmap = _settings(request).security.sigma_field_map
    have = {r["sigma_id"] for r in db.list_sigma_rules() if r.get("sigma_id")}
    added, skipped = [], []
    for sid in ids:
        e = db.get_sigma_library_entry(sid)
        if not e:
            skipped.append({"sigma_id": sid, "reason": "not_found"})
            continue
        if sid in have:
            skipped.append({"sigma_id": sid, "reason": "already_added"})
            continue
        conv, err = _sigma_convert(e["yaml"], fmap)
        if err:
            skipped.append({"sigma_id": sid, "reason": "not_convertible"})
            continue
        rid = db.add_sigma_rule({**conv, "yaml": e["yaml"], "group_by": group_by, "threshold": threshold,
                                 "origin": "library"}, request.session.get("username", ""))
        have.add(sid)
        added.append(rid)
    if added:
        _audit(request, "security_sigma_library_added", f"rules={','.join(map(str, added))}")
    return {"added": added, "skipped": skipped}


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
    enabled = body.get("enabled", settings.security.ti_enabled)
    if not isinstance(enabled, bool):   # "false" (a string) must not switch the downloads on
        return JSONResponse({"error": "enabled must be true or false"}, status_code=400)
    try:
        hours = int(body.get("refresh_hours") or settings.security.ti_refresh_hours)
    except (TypeError, ValueError):
        return JSONResponse({"error": "refresh_hours must be a number"}, status_code=400)
    new = settings.security.model_copy(update={
        "ti_enabled": enabled, "ti_feeds": feeds, "ti_refresh_hours": max(1, min(hours, 168))})
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
    # the field map has its own endpoint (validated there)
    merged = {**cur, **{k: v for k, v in body.items() if k in cur and k not in ("detectors", "field_map")}}
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
            if v.get("blocked_min_count") not in (None, "") and next(
                    (d.blocked_min_count for d in DETECTORS if d.id == k), 0):
                entry["blocked_min_count"] = max(1, int(v["blocked_min_count"]))
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
    new.digest_cron = (new.digest_cron or "").strip() or old.digest_cron
    from glogarch.security.digest import digest_cron_problem
    if digest_cron_problem(new.digest_cron):
        return JSONResponse({"error": f"Invalid summary schedule (cron): {new.digest_cron}"}, status_code=400)

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
           f"ai_auto={new.ai_auto}/{new.ai_auto_min_severity}/{new.ai_auto_max_per_run} "
           f"digest={new.digest_enabled}/{new.digest_cron}")
    return {"status": "saved", "registered": registered}


# --- field map (1.35) ----------------------------------------------------------------

def _field_map_view(cfg) -> dict:
    from glogarch.security.fieldmap import FieldMap, GROUPS, SPEC
    return {"values": FieldMap.from_config(cfg.field_map).values(), "stored": dict(cfg.field_map),
            "defaults": {k: v[1] for k, v in SPEC.items()},
            "kinds": {k: v[0] for k, v in SPEC.items()}, "groups": GROUPS}


@router.post("/security/fieldmap")
async def save_field_map(request: Request):
    """Where this site keeps what the built-in detectors read. Empty / default
    values are not stored (= the GIM default)."""
    from glogarch.security.fieldmap import validate
    body = await request.json() or {}
    fmap, errors = validate(body.get("field_map"))
    if errors:
        return JSONResponse({"error": "; ".join(errors[:5])}, status_code=400)
    settings = _settings(request)
    new = settings.security.model_copy(update={"field_map": fmap})
    from glogarch.core.config_writer import update_config

    def _mut(cfg):
        cfg["security"] = new.model_dump()
    update_config(_config_path(request), _mut)
    settings.security = new
    _audit(request, "security_fieldmap_saved",
           " ".join(f"{k}={v}" for k, v in sorted(fmap.items()))[:900] or "defaults")
    return {"status": "saved", "field_map": _field_map_view(new)}


@router.post("/security/fieldmap/detect")
async def detect_field_map(request: Request):
    """Fields of a sample of one group's events that could hold each thing, with
    the exact share of events that have them. Reads only; the page picks."""
    from glogarch.security.ai_analysis import server_ctx
    from glogarch.security.fieldmap import FieldMap, detect, validate
    body = await request.json() or {}
    settings = _settings(request)
    cfg = settings.security
    try:
        server = settings.get_server(cfg.server or None)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    # the form's values, unsaved: what the administrator is trying out
    trial, errors = validate(body.get("field_map") or {})
    if errors:
        return JSONResponse({"error": "; ".join(errors[:5])}, status_code=400)
    fm = FieldMap.from_config(trial if isinstance(body.get("field_map"), dict) else cfg.field_map)
    try:
        out = await detect(server_ctx(settings, _db(request), server), str(body.get("group") or ""), fm)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        log.warning("Field detection failed", error=str(e))
        return JSONResponse({"error": f"Graylog query failed: {str(e)[:300]}"}, status_code=502)
    return {**out, "server": server.name}


# --- weekly summary (1.32) ------------------------------------------------------------

@router.get("/security/digest")
def digest_preview(request: Request):
    from glogarch.notify.sender import format_security_digest
    from glogarch.security.digest import build_digest, healthy, server_name
    settings = _settings(request)
    d = build_digest(settings, _db(request))
    title, body = format_security_digest(d, server_name(settings))
    return {**d, "healthy": healthy(d), "title": title, "body": body}


@router.post("/security/digest/send")
async def digest_send(request: Request):
    from glogarch.security.digest import send_digest
    try:
        d = await send_digest(_settings(request), _db(request))
    except Exception as e:
        return JSONResponse({"error": f"The summary could not be sent: {e}"}, status_code=502)
    _audit(request, "security_digest_sent", f"new={d['new_total']} runs={d['runs_total']}")
    return {"status": "sent"}


# --- suppressions (1.31) ------------------------------------------------------------

_SUPPRESS_DAYS = (0, 1, 7, 30, 90, 365)


def _suppression_row(r: dict, now: datetime, db) -> dict:
    exp = parse_db_ts(r.get("expires_at"))
    title = None
    if r["detector"].startswith("sigma:"):
        rule = db.get_sigma_rule(int(r["detector"].split(":", 1)[1]))
        title = f"Sigma: {rule['title']}" if rule else None   # a deleted rule shows its id
    return {**r, "active": exp is None or exp > now, "detector_title": title}


@router.get("/security/suppressions")
def list_suppressions(request: Request):
    db = _db(request)
    now = datetime.utcnow()
    return {"suppressions": [_suppression_row(r, now, db) for r in db.list_suppressions()],
            "days": list(_SUPPRESS_DAYS)}


@router.post("/security/suppressions")
async def add_suppression(request: Request):
    from glogarch.security.suppress import DAYS_MAX, MAX_REASON, SuppressionError, normalize_entity
    body = await request.json() or {}
    db = _db(request)
    settings = _settings(request)
    detector = str(body.get("detector") or "").strip()
    if detector != "*" and detector not in {d.id for d in DETECTORS} and not re.fullmatch(r"sigma:\d+", detector):
        return JSONResponse({"error": "Unknown detection"}, status_code=400)
    server = str(body.get("server") or "").strip()
    if server and server not in {s.name for s in settings.servers}:
        return JSONResponse({"error": "Unknown server"}, status_code=400)
    try:
        entity = normalize_entity(str(body.get("entity") or ""))
    except SuppressionError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    reason = str(body.get("reason") or "").strip()
    if not reason:
        return JSONResponse({"error": "A reason is required"}, status_code=400)
    if len(reason) > MAX_REASON:
        return JSONResponse({"error": f"The reason is longer than {MAX_REASON} characters"}, status_code=400)
    try:
        days = int(body.get("days", 30))
    except (TypeError, ValueError):
        return JSONResponse({"error": "Days must be a number"}, status_code=400)
    if days < 0 or days > DAYS_MAX:
        return JSONResponse({"error": f"Days must be between 0 and {DAYS_MAX}"}, status_code=400)
    user = request.session.get("username", "")
    expires = datetime.utcnow() + timedelta(days=days) if days else None
    sid, created = db.add_suppression(server=server, detector=detector, entity=entity, reason=reason,
                                      username=user, expires_at=expires)
    _audit(request, "security_suppression_added",
           f"id={sid} server={server or '*'} detector={detector} entity={entity} days={days or 'never'} "
           f"reason={reason[:120]}")
    closed = None
    iid = body.get("incident_id")
    if body.get("close_incident") is True and isinstance(iid, int) and not isinstance(iid, bool):
        # only an incident this suppression covers (its server, detection and entity):
        # the id comes from the page and could name any incident
        from glogarch.security.suppress import Suppressor
        inc = db.get_security_incident(iid)
        covers = inc and Suppressor([{"id": sid, "server": server, "detector": detector, "entity": entity,
                                      "expires_at": None}], "").match(
            inc.get("server", ""), inc.get("detector", ""), str(inc.get("entity", ""))) == sid
        if covers and db.set_security_status(iid, "closed", user):
            closed = iid
            _audit(request, "security_incident_status", f"incident={iid} status=closed (suppressed)")
    return {"id": sid, "created": created, "entity": entity, "closed_incident": closed}


@router.delete("/security/suppressions/{sid}")
def delete_suppression(request: Request, sid: int):
    row = _db(request).delete_suppression(sid)
    if not row:
        return JSONResponse({"error": "Suppression not found"}, status_code=404)
    _audit(request, "security_suppression_removed",
           f"id={sid} server={row['server'] or '*'} detector={row['detector']} entity={row['entity']}")
    return {"deleted": sid}
