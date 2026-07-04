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
        "period": cfg.get("period", ""),
        "generated_at": now.strftime("%Y-%m-%d %H:%M %z"),
        "server": cfg.get("server", ""),
        "summary": cfg.get("summary", ""),
    }

    sections: list[dict] = []

    # Phase 2 — branded data from jt-glogarch's own DB (always reliable).
    if cfg.get("include_archive_summary", True):
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
            dtab = dash.get("tab") if isinstance(dash, dict) else None
            if mode == "screenshot":
                sec = {"type": "image", "title": dtitle or did,
                       "description": _t(lang, "native"), "img_data_uri": None}
                if server and web_user and web_pass:
                    png = await graylog_data.capture_dashboard_png(
                        server, did, web_username=web_user, web_password=web_pass,
                        time_range_seconds=trs)
                    if png:
                        sec["img_data_uri"] = graylog_data.png_to_data_uri(png)
                sections.append(sec)
            else:  # rebuild
                built = []
                if server:
                    built = await graylog_data.rebuild_dashboard_sections(
                        server, did, time_range_seconds=trs, max_widgets=maxw, lang=lang,
                        tab=(dtab or None))
                if built:
                    sections.extend(built)
                else:
                    sections.append({"type": "charts", "title": dtitle or did,
                                     "description": _t(lang, "rebuild_empty"), "widgets": []})

    if not sections:
        sections.append({"type": "charts", "title": _t(lang, "no_content"),
                         "widgets": [{"kind": "text"}]})

    # Render
    from glogarch.report import renderer
    html = builder.build_html(report, sections)
    pdf = await renderer.html_to_pdf(
        html, report_title=report["title"], header_text=report["header_text"],
        generated_at=report["generated_at"])

    # Save
    ts = now.strftime("%Y%m%dT%H%M%S")
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)[:60]
    filename = f"{safe}_{ts}.pdf"
    path = _reports_dir(settings) / filename
    path.write_bytes(pdf)
    try:
        _chown_if_root(path)
    except Exception:
        pass

    db.record_report_history(name, str(path), filename, len(pdf), "completed")
    db.update_report_last_run(name)
    log.info("Report generated", report=name, bytes=len(pdf), by=triggered_by)

    # Email
    result = {"ok": True, "file_path": str(path), "filename": filename, "bytes": len(pdf), "emailed": False}
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
              "rebuild_empty": "（無法從此儀表板重建 widget，可能是查詢逾時或無資料）"},
    "en": {"native": "Native capture of the Graylog dashboard.", "no_content": "No content",
           "no_capture": "(dashboard capture unavailable — set Graylog web credentials in the report)",
           "rebuild_empty": "(could not rebuild widgets from this dashboard — search timed out or returned no data)"},
}


def _t(lang, key):
    return _TXT.get(lang, _TXT["zh-TW"]).get(key, "")
