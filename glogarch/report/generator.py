"""Generate a report PDF from a stored report definition, save it, record
history, and optionally email it. Beta."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from glogarch.report import builder, graylog_data
from glogarch.utils.logging import get_logger
from glogarch.utils.sanitize import sanitize

log = get_logger("report.generator")


def _reports_dir(settings) -> Path:
    d = Path(settings.export.base_path) / "reports"
    d.mkdir(parents=True, exist_ok=True)
    return d


async def generate_report(db, settings, cfg: dict, *, triggered_by: str = "manual") -> dict:
    """cfg is the parsed report definition. Returns {ok, file_path, filename, error}."""
    name = cfg.get("name", "report")
    lang = cfg.get("lang", "zh-TW")
    now = datetime.now().astimezone()

    report = {
        "title": cfg.get("title") or name,
        "subtitle": cfg.get("subtitle", ""),
        "author": cfg.get("author", ""),
        "kicker": cfg.get("kicker", "Graylog Open Archive"),
        "brand_color": cfg.get("brand_color", "#6c63ff"),
        "brand_dark": cfg.get("brand_dark", "#4b43c4"),
        "lang": lang, "beta": True,
        "header_text": cfg.get("header_text", ""),
        "logo_data_uri": cfg.get("logo_data_uri", ""),
        "header_logo_data_uri": cfg.get("header_logo_data_uri", ""),
        "period": cfg.get("period", ""),
        "generated_at": now.strftime("%Y-%m-%d %H:%M %z"),
        "server": cfg.get("server", ""),
        "summary": cfg.get("summary", ""),
    }

    # Append the Graylog version to the server line, e.g. "log4 (Graylog 7.1.2)".
    _srv_name = cfg.get("server", "")
    if _srv_name:
        try:
            _srv = _resolve_server(settings, _srv_name)
            if _srv:
                _ver = await graylog_data.get_graylog_version(_srv)
                if _ver:
                    report["server"] = f"{_srv_name}（Graylog {_ver}）" if lang == "zh-TW" else f"{_srv_name} (Graylog {_ver})"
        except Exception:
            pass

    sections: list[dict] = []

    # Phase 2 — branded data from jt-glogarch's own DB (always reliable).
    if cfg.get("include_archive_summary", False):
        header_extra, data_sections = graylog_data.archive_summary_sections(db, lang)
        report["kpis"] = header_extra.get("kpis")
        if not report["summary"]:
            report["summary"] = _default_summary(lang, report.get("kpis"))
        sections.extend(data_sections)

    # Graylog dashboards — two modes the user chooses per report:
    #   "rebuild"    (default) — reconstruct widgets from live data as our charts
    #   "screenshot"           — native headless-Chromium capture (needs web creds)
    dashboards = cfg.get("dashboards") or []
    if dashboards:
        server = _resolve_server(settings, cfg.get("server"))
        mode = cfg.get("dashboard_mode", "rebuild")
        trs = int(cfg.get("time_range_seconds", 86400))
        maxw = int(cfg.get("max_widgets", 16))
        web_user = cfg.get("graylog_web_username", "")
        web_pass = cfg.get("graylog_web_password", "")
        for dash in dashboards:
            did = dash.get("id") if isinstance(dash, dict) else dash
            dtitle = dash.get("title") if isinstance(dash, dict) else did
            dtabs = None
            if isinstance(dash, dict):
                dtabs = dash.get("tabs")
                if not dtabs and dash.get("tab"):
                    dtabs = [dash.get("tab")]   # legacy single-tab config
            if mode == "screenshot":
                sec = {"type": "image", "title": dtitle or did,
                       "description": _t(lang, "native"), "img_data_uri": None}
                if not (server and web_user and web_pass):
                    sec["capture_error"] = _t(lang, "no_capture")
                else:
                    png, reason = await graylog_data.capture_dashboard_png(
                        server, did, web_username=web_user, web_password=web_pass,
                        time_range_seconds=trs)
                    if png:
                        # A full dashboard capture is tall — slice it across pages.
                        sec["img_slices"] = graylog_data.slice_tall_png(png)
                    else:
                        sec["capture_error"] = reason or _t(lang, "no_capture")
                sections.append(sec)
            else:  # rebuild
                built = []
                # Snap-to-midnight: end the window at today's local 00:00 and go
                # back `trs` seconds — so a Mon-05:00 run of a 1-day dashboard
                # covers Sun 00:00 → Mon 00:00 instead of Sun 05:00 → Mon 05:00.
                abs_from = abs_to = None
                if cfg.get("align_midnight"):
                    from datetime import timedelta
                    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
                    abs_to = midnight.isoformat(timespec="milliseconds")
                    abs_from = (midnight - timedelta(seconds=trs)).isoformat(timespec="milliseconds")
                if server:
                    built = await graylog_data.rebuild_dashboard_sections(
                        server, did, time_range_seconds=trs, max_widgets=maxw, lang=lang,
                        tabs=(dtabs or None),
                        message_rows=int(cfg.get("message_rows", 20) or 0),
                        message_max_cols=int(cfg.get("message_max_cols", 0) or 0),
                        bar_horizontal=bool(cfg.get("bar_horizontal", False)),
                        heatmap_values=bool(cfg.get("heatmap_values", False)),
                        use_dashboard_time=bool(cfg.get("use_dashboard_time", True)),
                        abs_from=abs_from, abs_to=abs_to)
                if built:
                    sections.extend(built)
                else:
                    sections.append({"type": "charts", "title": dtitle or did,
                                     "description": _t(lang, "rebuild_empty"), "widgets": []})

    if not sections:
        sections.append({"type": "charts", "title": _t(lang, "no_content"),
                         "widgets": [{"kind": "text"}]})

    # Watermark (flattened, tiled) — text + any auto-appended context fields.
    watermark = None
    if cfg.get("watermark_enabled"):
        # Blank text defaults to 機密 / CONFIDENTIAL.
        base_text = (cfg.get("watermark_text") or "").strip() or ("機密" if lang == "zh-TW" else "CONFIDENTIAL")
        parts = [base_text]
        ap = cfg.get("watermark_append") or []
        if "server" in ap and cfg.get("server"):
            parts.append(str(cfg.get("server")))
        if "ip" in ap:
            try:
                from urllib.parse import urlparse
                _srv2 = _resolve_server(settings, cfg.get("server"))
                host = urlparse(_srv2.url).hostname if _srv2 else ""
                if host:
                    parts.append(host)
            except Exception:
                pass
        if "time" in ap:
            parts.append(now.strftime("%Y-%m-%d %H:%M"))
        if "dashboard" in ap and dashboards:
            names = [(d.get("title") or d.get("id")) if isinstance(d, dict) else str(d)
                     for d in dashboards]
            parts.append(" / ".join(n for n in names if n))
        if "recipients" in ap and cfg.get("recipients"):
            parts.append(", ".join(cfg.get("recipients")))
        # At most TWO lines: the base text on line 1, and ALL appended fields
        # combined on line 2 (a single wide line clips some text off the tile).
        base_line = parts[0]
        extra = "   ".join(p for p in parts[1:] if p)
        text = base_line + ("\n" + extra if extra else "")
        watermark = {"text": text, "size": cfg.get("watermark_size", "large"),
                     "direction": cfg.get("watermark_direction", "diagonal"),
                     "opacity": float(cfg.get("watermark_opacity", 0.10) or 0.10)}

    # Render
    from glogarch.report import renderer
    html = builder.build_html(report, sections)
    pdf = await renderer.html_to_pdf(
        html, report_title=report["title"], header_text=report["header_text"],
        header_logo=report.get("header_logo_data_uri", ""),
        brand_color=report.get("brand_color", "#6c63ff"),
        watermark=watermark,
        toc_titles=[s.get("title") for s in sections if s.get("title")],
        generated_at=report["generated_at"])

    # Save
    ts = now.strftime("%Y%m%dT%H%M%S")
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)[:60]
    filename = f"{safe}_{ts}.pdf"
    path = _reports_dir(settings) / filename
    path.write_bytes(pdf)

    # Tamper-evident fingerprint: SHA-256 of the exact PDF bytes. Stored in the
    # DB + shown in the Web UI, and written as a .sha256 sidecar so anyone can
    # `sha256sum report.pdf` and compare against the access-controlled record.
    import hashlib
    sha256 = hashlib.sha256(pdf).hexdigest()
    sidecar = path.with_name(path.name + ".sha256")
    try:
        sidecar.write_text(f"{sha256}  {filename}\n", encoding="utf-8")
    except Exception:
        pass
    try:
        _chown_if_root(path)
        _chown_if_root(sidecar)
    except Exception:
        pass

    db.record_report_history(name, str(path), filename, len(pdf), "completed",
                             triggered_by=triggered_by, sha256=sha256)
    db.update_report_last_run(name)
    log.info("Report generated", report=name, bytes=len(pdf), by=triggered_by)

    # Email
    # "Data volume" for the job row = widgets rebuilt (+ captured dashboard pages).
    units = sum(len(s.get("widgets") or []) for s in sections if s.get("type") == "charts")
    units += sum(len(s.get("img_slices") or ([s["img_data_uri"]] if s.get("img_data_uri") else []))
                 for s in sections if s.get("type") == "image")
    result = {"ok": True, "file_path": str(path), "filename": filename, "bytes": len(pdf),
              "sha256": sha256, "units": units, "emailed": False}
    recipients = cfg.get("recipients") or []
    if recipients:
        try:
            _email_pdf(settings, recipients, report["title"], pdf, filename, lang)
            result["emailed"] = True
        except Exception as e:
            log.warning("Report email failed", error=sanitize(str(e)))
            result["email_error"] = sanitize(str(e))
    return result


def _resolve_server(settings, name):
    try:
        return settings.get_server(name)
    except Exception:
        return None


def _chown_if_root(path: Path):
    if os.geteuid() == 0:
        import pwd
        try:
            u = pwd.getpwnam("jt-glogarch")
            os.chown(path, u.pw_uid, u.pw_gid)
        except Exception:
            pass


def _email_pdf(settings, recipients, subject_title, pdf: bytes, filename: str, lang: str):
    """Send the PDF as an email attachment via the configured SMTP settings."""
    import smtplib
    from email.message import EmailMessage
    e = settings.notify.email
    if not e.smtp_host:
        raise RuntimeError("SMTP not configured (notify.email)")
    msg = EmailMessage()
    prefix = e.subject_prefix or "[jt-glogarch]"
    msg["Subject"] = f"{prefix} {subject_title}"
    msg["From"] = e.from_addr or e.smtp_user
    msg["To"] = ", ".join(recipients)
    body = ("附件為 jt-glogarch 產生的報表：%s" if lang == "zh-TW"
            else "Attached is the jt-glogarch report: %s") % subject_title
    msg.set_content(body)
    msg.add_attachment(pdf, maintype="application", subtype="pdf", filename=filename)
    if e.smtp_tls:
        with smtplib.SMTP(e.smtp_host, e.smtp_port, timeout=30) as s:
            s.starttls()
            if e.smtp_user:
                s.login(e.smtp_user, e.smtp_password)
            s.send_message(msg)
    else:
        with smtplib.SMTP(e.smtp_host, e.smtp_port, timeout=30) as s:
            if e.smtp_user:
                s.login(e.smtp_user, e.smtp_password)
            s.send_message(msg)


def _default_summary(lang, kpis):
    if lang == "zh-TW":
        return "本報表由 jt-glogarch 自動產生，涵蓋日誌封存、作業與操作稽核之概況統計。"
    return "This report is generated automatically by jt-glogarch, summarising log archiving, jobs, and operation audit activity."


_TXT = {
    "zh-TW": {"native": "Graylog 儀表板原生擷取畫面。", "no_content": "無報表內容",
              "no_capture": "（無法擷取儀表板畫面，請確認報表已設定 Graylog 網頁登入帳密）",
              "rebuild_empty": "（無法重現此儀表板的 widget，可能是查詢逾時或無資料）"},
    "en": {"native": "Native capture of the Graylog dashboard.", "no_content": "No content",
           "no_capture": "(dashboard capture unavailable — set Graylog web credentials in the report)",
           "rebuild_empty": "(could not rebuild widgets from this dashboard — search timed out or returned no data)"},
}


def _t(lang, key):
    return _TXT.get(lang, _TXT["zh-TW"]).get(key, "")
