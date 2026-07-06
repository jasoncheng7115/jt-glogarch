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
        "logo_height_px": int(cfg.get("logo_height_px", 72) or 72),
        "header_logo_data_uri": cfg.get("header_logo_data_uri", ""),
        "period": cfg.get("period", ""),
        "generated_at": now.strftime("%Y-%m-%d %H:%M %z"),
        "server": cfg.get("server", ""),
        "summary": cfg.get("summary", ""),
        "app_version": __import__("glogarch").__version__,
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
        # "Use each widget's own time range" — each widget (and each tab) can have
        # a DIFFERENT saved range in Graylog (e.g. one widget "last 5 days", another
        # "last 1 day"), and this captures each exactly as configured. It is
        # mutually exclusive with a report-wide window: when on, NO global time
        # override is applied, so a report-wide range / snap-to-midnight is ignored.
        use_dash_time = bool(cfg.get("use_dashboard_time", True))
        want_midnight = bool(cfg.get("align_midnight"))
        # Report-WIDE snap-to-midnight: only when NOT using per-widget times, and
        # only for a whole-day report window.
        align_midnight_eff = want_midnight and trs % 86400 == 0 and not use_dash_time
        # PER-WIDGET snap-to-midnight: when using each widget's own time range AND
        # snap is on, keep every widget's own duration but end its window at today
        # 00:00. Whether a given widget actually snaps is decided per widget in
        # rebuild (only whole-day durations snap; e.g. a "last 2 hours" widget is
        # left as-is).
        snap_per_widget = want_midnight and use_dash_time
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
                    # Time window for the capture. When the report uses each
                    # widget's OWN time range, apply NO override — let the live
                    # dashboard render every widget/tab at its own configured range
                    # (so a "last 5 days" widget stays 5 days). Only when a report-
                    # wide range is chosen do we override: snap-to-midnight ends at
                    # today 00:00, otherwise it ends now.
                    from datetime import timedelta
                    cap_from = cap_to = None
                    if not use_dash_time:
                        cap_to = (now.replace(hour=0, minute=0, second=0, microsecond=0)
                                  if align_midnight_eff else now)
                        cap_from = cap_to - timedelta(seconds=trs)
                    png, reason = await graylog_data.capture_dashboard_png(
                        server, did, web_username=web_user, web_password=web_pass,
                        time_range_seconds=trs, abs_from=cap_from, abs_to=cap_to)
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
                if align_midnight_eff:
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
                        use_dashboard_time=use_dash_time,
                        abs_from=abs_from, abs_to=abs_to,
                        snap_midnight=snap_per_widget)
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
        # Lay the items out over at most TWO BALANCED lines (each ~half the total
        # width) so the whole rotated watermark chip fits on the page at a
        # readable size — a single wide line spans the diagonal and every tile
        # shows only a fragment. CJK glyphs count double toward width.
        items = [p for p in parts if p]

        def _w(s):
            return sum(2 if ord(c) > 0x2E80 else 1 for c in s)

        if len(items) <= 1:
            text = items[0] if items else ""
        else:
            half = sum(_w(x) for x in items) / 2
            line1, line2, acc = [], [], 0
            for it in items:
                if not line1 or (acc < half and len(line1) < len(items) - 1):
                    line1.append(it); acc += _w(it)
                else:
                    line2.append(it)
            text = "   ".join(line1) + ("\n" + "   ".join(line2) if line2 else "")
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

    # "Data volume" for the job row = widgets rebuilt (+ captured dashboard pages).
    units = sum(len(s.get("widgets") or []) for s in sections if s.get("type") == "charts")
    units += sum(len(s.get("img_slices") or ([s["img_data_uri"]] if s.get("img_data_uri") else []))
                 for s in sections if s.get("type") == "image")
    result = {"ok": True, "file_path": str(path), "filename": filename, "bytes": len(pdf),
              "sha256": sha256, "units": units, "emailed": False}

    # Email BEFORE recording history, so a delivery failure is not swallowed —
    # it lands in the report-history row (and the caller surfaces it) instead of
    # the PDF silently showing green while no mail ever arrives.
    recipients = cfg.get("recipients") or []
    hist_error = None
    if recipients:
        try:
            _email_pdf(settings, recipients, report["title"], pdf, filename, lang)
            result["emailed"] = True
        except Exception as e:
            result["email_error"] = sanitize(str(e))
            hist_error = f"Email delivery failed: {result['email_error']}"
            log.warning("Report email failed", error=result["email_error"])

    db.record_report_history(name, str(path), filename, len(pdf), "completed",
                             error=hist_error, triggered_by=triggered_by, sha256=sha256)
    db.update_report_last_run(name)
    log.info("Report generated", report=name, bytes=len(pdf), by=triggered_by,
             emailed=result["emailed"])
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
    import html as _html
    from datetime import datetime
    msg = EmailMessage()
    prefix = e.subject_prefix or "[jt-glogarch]"
    msg["Subject"] = f"{prefix} {subject_title}"
    msg["From"] = e.from_addr or e.smtp_user
    msg["To"] = ", ".join(recipients)
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %z")
    mb = len(pdf) / (1024 * 1024)
    size = f"{mb:.2f} MB" if mb >= 1 else f"{len(pdf) / 1024:.0f} KB"
    L = ({"intro": "jt-glogarch 已為您產生下列報表，PDF 檔案已附於本信。",
          "report": "報表", "generated": "產製時間", "file": "檔案",
          "footer": "本信由 jt-glogarch 自動寄送"}
         if lang == "zh-TW" else
         {"intro": "jt-glogarch has generated the following report. The PDF is attached.",
          "report": "Report", "generated": "Generated", "file": "File",
          "footer": "Sent automatically by jt-glogarch"})
    # Plain-text fallback + a polished HTML body (mirrors the notification email).
    msg.set_content(f"{subject_title}\n\n{L['intro']}\n\n"
                    f"{L['report']}: {subject_title}\n{L['generated']}: {now}\n"
                    f"{L['file']}: {filename} ({size})\n\n{L['footer']}")
    st, fn = _html.escape(subject_title), _html.escape(filename)
    row = ('<tr><td style="padding:5px 16px 5px 0;color:#9aa">{k}</td>'
           '<td style="padding:5px 0">{v}</td></tr>')
    msg.add_alternative(f"""<div style="font-family:'Segoe UI',Helvetica,Arial,sans-serif;max-width:640px;color:#333">
  <h2 style="color:#6c63ff;margin:0 0 8px">{_html.escape(prefix)} {st}</h2>
  <p style="color:#555;margin:0 0 14px">{_html.escape(L['intro'])}</p>
  <table style="border-collapse:collapse;font-size:14px;margin:0 0 16px">
    {row.format(k=L['report'], v=f'<b>{st}</b>')}
    {row.format(k=L['generated'], v=now)}
    {row.format(k=L['file'], v=f'{fn} <span style="color:#9aa">({size})</span>')}
  </table>
  <p style="color:#aab;font-size:12px;border-top:1px solid #eee;padding-top:12px;margin:0">{_html.escape(L['footer'])} · Graylog Open Archive</p>
</div>""", subtype="html")
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
