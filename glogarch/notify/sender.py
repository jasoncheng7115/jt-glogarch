# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Notification sender — Telegram, Discord, Slack, Teams, Nextcloud Talk."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

import httpx

from glogarch.core.config import NotifyConfig, get_settings
from glogarch.utils.logging import get_logger

log = get_logger("notify")

TIMEOUT = httpx.Timeout(15.0, connect=5.0)


class NotifyEvent(str, Enum):
    EXPORT_COMPLETE = "export_complete"
    IMPORT_COMPLETE = "import_complete"
    CLEANUP_COMPLETE = "cleanup_complete"
    VERIFY_FAILED = "verify_failed"
    ERROR = "error"
    SENSITIVE_API_OPERATION = "sensitive_api_operation"
    AUDIT_ALERT = "audit_alert"


def _should_send(config: NotifyConfig, event: NotifyEvent) -> bool:
    mapping = {
        NotifyEvent.EXPORT_COMPLETE: config.on_export_complete,
        NotifyEvent.IMPORT_COMPLETE: config.on_import_complete,
        NotifyEvent.CLEANUP_COMPLETE: config.on_cleanup_complete,
        NotifyEvent.VERIFY_FAILED: config.on_verify_failed,
        NotifyEvent.ERROR: config.on_error,
        NotifyEvent.SENSITIVE_API_OPERATION: config.on_sensitive_operation,
        NotifyEvent.AUDIT_ALERT: config.on_audit_alert,
    }
    return mapping.get(event, False)


def _has_any_channel(config: NotifyConfig) -> bool:
    return any([
        config.telegram.enabled,
        config.discord.enabled,
        config.slack.enabled,
        config.teams.enabled,
        config.nextcloud_talk.enabled,
        config.email.enabled,
    ])


async def send_notification(
    event: NotifyEvent,
    title: str,
    message: str,
    config: NotifyConfig | None = None,
) -> list[dict]:
    """Send notification to all enabled channels.

    Returns list of {channel, success, error} dicts.
    """
    if config is None:
        config = get_settings().notify

    if not _should_send(config, event):
        return []

    if not _has_any_channel(config):
        return []

    results = []
    timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    # Blank line before the footer. Without it the send time is glued to the
    # last body line, and when that line is an indented bullet — the overflow
    # timestamps, the error list — the footer reads as one more list item.
    full_msg = f"[jt-glogarch] {title}\n{message}\n\n{timestamp}"

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        if config.telegram.enabled:
            results.append(await _send_telegram(client, config.telegram, full_msg))

        if config.discord.enabled:
            results.append(await _send_discord(client, config.discord, title, message, timestamp))

        if config.slack.enabled:
            results.append(await _send_slack(client, config.slack, title, message, timestamp))

        if config.teams.enabled:
            results.append(await _send_teams(client, config.teams, title, message, timestamp))

        if config.nextcloud_talk.enabled:
            results.append(await _send_nextcloud_talk(client, config.nextcloud_talk, full_msg))

    if config.email.enabled:
        results.append(await _send_email(config.email, title, message, timestamp))

    for r in results:
        if r["success"]:
            log.info("Notification sent", channel=r["channel"], notify_event=event.value)
        else:
            log.error("Notification failed", channel=r["channel"], error=r.get("error"))

    return results


# --- Telegram ---

def _telegram_text(message: str) -> str:
    """Build the Telegram body for parse_mode=HTML.

    Two things this must get right:
    - ESCAPE. The text is parsed as HTML, and error lines substitute long URLs
      with a literal "<url>" — Telegram rejects that as an unsupported tag with
      HTTP 400, so the notification never arrives and the failure is swallowed
      by the caller's except. Any '<' in a log line or error message does the
      same thing.
    - MONOSPACE. The stat labels are padded to a common width so the values
      line up; that only shows in a fixed-width block, so wrap it in <pre>.
    """
    import html as _html
    return f"<pre>{_html.escape(message)}</pre>"


async def _send_telegram(client: httpx.AsyncClient, cfg, message: str) -> dict:
    try:
        resp = await client.post(
            f"https://api.telegram.org/bot{cfg.bot_token}/sendMessage",
            json={"chat_id": cfg.chat_id, "text": _telegram_text(message),
                  "parse_mode": "HTML"},
        )
        resp.raise_for_status()
        return {"channel": "telegram", "success": True}
    except Exception as e:
        return {"channel": "telegram", "success": False, "error": str(e)}


# --- Discord ---

async def _send_discord(client: httpx.AsyncClient, cfg, title: str, message: str, ts: str) -> dict:
    try:
        resp = await client.post(cfg.webhook_url, json={
            "embeds": [{
                "title": f"jt-glogarch: {title}",
                "description": message,
                "footer": {"text": ts},
                "color": 0x6c63ff,
            }]
        })
        resp.raise_for_status()
        return {"channel": "discord", "success": True}
    except Exception as e:
        return {"channel": "discord", "success": False, "error": str(e)}


# --- Slack ---

async def _send_slack(client: httpx.AsyncClient, cfg, title: str, message: str, ts: str) -> dict:
    try:
        resp = await client.post(cfg.webhook_url, json={
            "blocks": [
                {"type": "header", "text": {"type": "plain_text", "text": f"jt-glogarch: {title}"}},
                {"type": "section", "text": {"type": "mrkdwn", "text": message}},
                {"type": "context", "elements": [{"type": "mrkdwn", "text": ts}]},
            ]
        })
        resp.raise_for_status()
        return {"channel": "slack", "success": True}
    except Exception as e:
        return {"channel": "slack", "success": False, "error": str(e)}


# --- Microsoft Teams ---

async def _send_teams(client: httpx.AsyncClient, cfg, title: str, message: str, ts: str) -> dict:
    try:
        # Adaptive Card format for Teams Workflows webhook
        resp = await client.post(cfg.webhook_url, json={
            "type": "message",
            "attachments": [{
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": [
                        {"type": "TextBlock", "text": f"jt-glogarch: {title}", "weight": "Bolder", "size": "Medium"},
                        {"type": "TextBlock", "text": message, "wrap": True},
                        {"type": "TextBlock", "text": ts, "size": "Small", "isSubtle": True},
                    ],
                }
            }]
        })
        resp.raise_for_status()
        return {"channel": "teams", "success": True}
    except Exception as e:
        return {"channel": "teams", "success": False, "error": str(e)}


# --- Nextcloud Talk ---

async def _send_nextcloud_talk(client: httpx.AsyncClient, cfg, message: str) -> dict:
    try:
        url = f"{cfg.server_url.rstrip('/')}/ocs/v2.php/apps/spreed/api/v1/chat/{cfg.token}"
        resp = await client.post(
            url,
            json={"message": message},
            auth=httpx.BasicAuth(cfg.username, cfg.password),
            headers={
                "OCS-APIRequest": "true",
                "Accept": "application/json",
            },
        )
        resp.raise_for_status()
        return {"channel": "nextcloud_talk", "success": True}
    except Exception as e:
        return {"channel": "nextcloud_talk", "success": False, "error": str(e)}


# --- Email (SMTP) ---

async def _send_email(cfg, title: str, message: str, ts: str) -> dict:
    import asyncio
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    def _do_send():
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"{cfg.subject_prefix} {title}"
        msg["From"] = cfg.from_addr
        msg["To"] = ", ".join(cfg.to_addrs)

        text_body = f"{title}\n\n{message}\n\n{ts}"
        html_body = f"""<div style="font-family:sans-serif;max-width:600px">
<h2 style="color:#6c63ff">{cfg.subject_prefix} {title}</h2>
<pre style="background:#f5f5f5;padding:12px;border-radius:6px;white-space:pre-wrap">{message}</pre>
<p style="color:#888;font-size:12px">{ts}</p>
</div>"""

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        if cfg.smtp_tls:
            server = smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=15)
            server.ehlo()
            server.starttls()
            server.ehlo()
        else:
            if cfg.smtp_port == 465:
                server = smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_port, timeout=15)
            else:
                server = smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=15)
            server.ehlo()

        try:
            if cfg.smtp_user and cfg.smtp_password:
                server.login(cfg.smtp_user, cfg.smtp_password)
            server.sendmail(cfg.from_addr, cfg.to_addrs, msg.as_string())
        finally:
            server.quit()

    try:
        await asyncio.to_thread(_do_send)
        return {"channel": "email", "success": True}
    except Exception as e:
        return {"channel": "email", "success": False, "error": str(e)}


# --- Notification language ---

_MSG = {
    "en": {
        "export_ok": "✅ Export Complete",
        "export_err": "⚠️ Export Completed with Errors",
        "export_overflow": "⚠️ Export Complete (a few records exceeded the API per-query limit)",
        "overflow_note": ("What this means: one single millisecond held more than 10,000 messages, "
                          "and 10,000 is the most Graylog's API can return for one query. At the {n} "
                          "timestamp(s) below, the messages past that limit could not be read.\n"
                          "Everything else in those chunks WAS archived — this run did not fail, and "
                          "these windows will NOT be retried.\n"
                          "To collect the remainder, re-run just these windows in OpenSearch Direct "
                          "mode, which has no such limit:"),
        "export_body": ("Exported:   {chunks} chunks\n"
                        "Skipped:    {skipped}\n"
                        "Records:    {records}\n"
                        "Files:      {files}\n"
                        "Original:   {original}\n"
                        "Compressed: {compressed}\n"
                        "Duration:   {duration}\n"
                        "Mode:       {mode}"),
        "import_ok": "✅ Import Complete",
        "import_cancelled": "⏹️ Import Cancelled by User",
        "import_err": "⚠️ Import Completed with Errors",
        "import_body": ("Archives: {archives}\n"
                        "Records:  {records}\n"
                        "Duration: {duration}"),
        "cleanup_ok": "✅ Cleanup Complete",
        "cleanup_body": ("Deleted: {deleted} files\n"
                         "Freed:   {freed}"),
        "verify_ok": "✅ Verification Complete",
        "verify_body": ("Valid:   {valid}\n"
                        "Checked: {total}"),
        "verify_fail": "❌ Verification Failed",
        "corrupted": "Corrupted: {n}",
        "tampered": "🚨 TAMPERED (HMAC mismatch): {n}",
        "missing": "Missing:   {n}",
        "error_title": "❌ {op} Error",
        "errors": "Errors: {n}",
        "sensitive_title": "⚠️ {n} Sensitive Operation(s) Detected",
        "audit_alert_title": "⚠️ Operation Audit Alert",
        "audit_alert_body": ("No audit syslog received for {minutes} minutes.\n"
                             "Graylog is reachable but nginx may have stopped forwarding.\n"
                             "Last received: {last}\n"
                             "Check nginx config and syslog on all Graylog nodes."),
        "disk_low_title": "⚠️ Archive disk retention running low",
        "disk_low_body": ("Only ~{months} month(s) of archive capacity left at the current rate.\n"
                          "Free space: {avail} · growing ~{rate}/month.\n"
                          "Expand the archive disk or lower retention before it fills up."),
    },
    "zh-TW": {
        "export_ok": "✅ 匯出成功",
        "export_err": "⚠️ 匯出完成（有錯誤）",
        "export_overflow": "⚠️ 匯出完成（少數記錄超出 API 單次上限）",
        "overflow_note": ("這是什麼意思：同一毫秒內出現超過 10000 筆記錄，而 Graylog API 單次查詢"
                          "最多只能回傳 10000 筆。以下 {n} 個時間點，超出上限的那些記錄無法讀取。\n"
                          "這些區段的其餘記錄都已完整歸檔——本次匯出並未失敗，這些時段也不會重試。\n"
                          "若要補回未讀取的部分，請只針對以下時段改用 OpenSearch Direct 模式重跑"
                          "（該模式沒有這個上限）："),
        "export_body": ("匯出區段：{chunks}\n"
                        "略過區段：{skipped}\n"
                        "記錄數　：{records}\n"
                        "寫入檔案：{files}\n"
                        "原始大小：{original}\n"
                        "壓縮後　：{compressed}\n"
                        "耗時　　：{duration}\n"
                        "模式　　：{mode}"),
        "import_ok": "✅ 匯入成功",
        "import_cancelled": "⏹️ 匯入已由使用者取消",
        "import_err": "⚠️ 匯入完成（有錯誤）",
        "import_body": ("歸檔數：{archives}\n"
                        "記錄數：{records}\n"
                        "耗時　：{duration}"),
        "cleanup_ok": "✅ 清理成功",
        "cleanup_body": ("刪除檔案：{deleted}\n"
                         "釋放空間：{freed}"),
        "verify_ok": "✅ 驗證成功",
        "verify_body": ("通過　：{valid}\n"
                        "總檢查：{total}"),
        "verify_fail": "❌ 驗證失敗",
        "corrupted": "損毀　：{n}",
        "tampered": "🚨 遭竄改（HMAC 不符）：{n}",
        "missing": "遺失　：{n}",
        "error_title": "❌ {op} 失敗",
        "errors": "錯誤：{n}",
        "sensitive_title": "⚠️ 偵測到 {n} 個敏感行為",
        "audit_alert_title": "⚠️ 行為稽核警告",
        "audit_alert_body": ("已超過 {minutes} 分鐘未收到稽核 syslog。\n"
                             "Graylog 可連線但 nginx 可能已停止轉送。\n"
                             "最後收到：{last}\n"
                             "請檢查所有 Graylog 節點的 nginx 設定與 syslog 狀態。"),
        "disk_low_title": "⚠️ 歸檔磁碟可存時間偏低",
        "disk_low_body": ("依目前增長速度，歸檔空間大約只剩 ~{months} 個月。\n"
                          "可用空間：{avail} · 每月約增加 {rate}。\n"
                          "請在空間用盡前擴充歸檔磁碟或調低保留設定。"),
    },
}


def _t(key: str, **kwargs) -> str:
    lang = "en"
    try:
        lang = get_settings().notify.language or "en"
    except Exception:
        pass
    tpl = _MSG.get(lang, _MSG["en"]).get(key, _MSG["en"].get(key, key))
    return tpl.format(**kwargs) if kwargs else tpl



def _fmt_overflow_ts(ts: str) -> str:
    """Render an overflow timestamp in BOTH local and UTC time.

    Graylog's API returns UTC (`...Z`), but the operator re-runs the window in
    a UI that shows THEIR timezone. On Asia/Taipei that is an 8-hour gap — the
    whole point of listing these timestamps is that the window can be re-run,
    and a bare UTC string invites re-running the wrong eight hours.
    """
    from datetime import datetime, timezone
    raw = (ts or "").strip()
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        local = dt.astimezone()
        return f"{local.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} {local.strftime('%z')[:3]}:00  (UTC {raw})"
    except Exception:
        return raw


# --- Convenience functions ---

async def notify_export_complete(
    chunks: int, records: int, skipped: int, errors: list[str],
    files: int = 0, original_bytes: int = 0, compressed_bytes: int = 0,
    duration_seconds: float = 0, mode: str = "api",
    truncations: list[str] | None = None,
):
    truncations = truncations or []
    # Title precedence: a real failure outranks an overflow-only caveat, which
    # outranks a clean success. A run that archived everything except a few
    # over-full seconds is NOT "completed with errors" — that wording made a
    # customer think exports were failing when 9.1M records were being saved
    # every run. Give overflows their own accurate, non-alarming title.
    if errors:
        title = _t("export_err")
    elif truncations:
        title = _t("export_overflow")
    else:
        title = _t("export_ok")
    def _fmt_bytes(b):
        for u in ['B', 'KB', 'MB', 'GB', 'TB']:
            if b < 1024: return f"{b:.1f} {u}"
            b /= 1024
        return f"{b:.1f} PB"
    def _fmt_dur(s):
        if s < 60: return f"{int(s)}s"
        m = int(s // 60)
        if m < 60: return f"{m}m{int(s % 60)}s"
        h = m // 60
        return f"{h}h{m % 60}m"
    lines = [_t("export_body",
                chunks=chunks, skipped=skipped,
                records=f"{records:,}",
                files=files,
                original=_fmt_bytes(original_bytes),
                compressed=_fmt_bytes(compressed_bytes),
                duration=_fmt_dur(duration_seconds),
                mode=mode.upper())]
    if errors:
        lines.append("")          # keep the stats block visually separate
        lines.append(_t("errors", n=len(errors)))
        for e in errors[:3]:
            # Strip long URLs from error strings to keep notifications compact
            import re as _re
            short = _re.sub(r"https?://\S+", "<url>", str(e))
            lines.append(f"  - {short[:80]}")
    if truncations:
        lines.append("")          # keep the stats block visually separate
        lines.append(_t("overflow_note", n=len(truncations)))
        for tr in truncations[:5]:
            # Just the timestamp — the full remedy is in the header note.
            ts = tr.split(" had ")[0].replace("Timestamp ", "")
            lines.append(f"  - {_fmt_overflow_ts(ts)}")
    # An overflow-only run is a warning, not an error event: everything that
    # could be read WAS archived.
    if errors:
        event = NotifyEvent.ERROR
    elif truncations:
        event = NotifyEvent.WARNING if hasattr(NotifyEvent, "WARNING") else NotifyEvent.EXPORT_COMPLETE
    else:
        event = NotifyEvent.EXPORT_COMPLETE
    await send_notification(event, title, "\n".join(lines))


async def notify_import_complete(archives: int, records: int, errors: list[str],
                                 duration_seconds: float = 0,
                                 cancelled: bool = False):
    # A user-initiated cancel is not an error and must not be reported as
    # "completed (with errors)" — a customer read exactly that mail as a
    # failed/partial import. The cancel pseudo-error is dropped from the list;
    # any REAL errors that happened before the cancel are still shown.
    if cancelled:
        errors = [e for e in errors if "cancelled by user" not in e.lower()]
        title = _t("import_cancelled")
    else:
        title = _t("import_err") if errors else _t("import_ok")
    def _fmt_dur(s):
        if s < 60: return f"{int(s)}s"
        m = int(s // 60)
        if m < 60: return f"{m}m{int(s % 60)}s"
        h = m // 60
        return f"{h}h{m % 60}m"
    lines = [_t("import_body", archives=archives, records=f"{records:,}",
                 duration=_fmt_dur(duration_seconds))]
    if errors:
        lines.append(_t("errors", n=len(errors)))
        for e in errors[:3]:
            import re as _re
            short = _re.sub(r"https?://\S+", "<url>", str(e))
            lines.append(f"  - {short[:80]}")
    event = NotifyEvent.ERROR if errors else NotifyEvent.IMPORT_COMPLETE
    await send_notification(event, title, "\n".join(lines))


async def notify_cleanup_complete(deleted: int, freed_bytes: int):
    freed_mb = freed_bytes / 1024 / 1024
    await send_notification(
        NotifyEvent.CLEANUP_COMPLETE,
        _t("cleanup_ok"),
        _t("cleanup_body", deleted=deleted, freed=f"{freed_mb:.1f} MB"),
    )


async def notify_verify_failed(corrupted: list[str], missing: list[str],
                               tampered: list[str] | None = None):
    lines = []
    if tampered:
        lines.append(_t("tampered", n=len(tampered)))   # security event — listed first
    if corrupted:
        lines.append(_t("corrupted", n=len(corrupted)))
    if missing:
        lines.append(_t("missing", n=len(missing)))
    await send_notification(
        NotifyEvent.VERIFY_FAILED,
        _t("verify_fail"),
        "\n".join(lines),
    )


async def notify_error(operation: str, error: str):
    await send_notification(
        NotifyEvent.ERROR,
        _t("error_title", op=operation),
        error[:500],
    )


async def notify_disk_low(remaining_months: float, available_bytes: int,
                          bytes_per_month: float):
    """Warn that the archive disk will fill in ~remaining_months at the current
    compressed-growth rate. Routed through the ERROR event so it reaches any
    enabled channel without new config wiring."""
    def _fmt(b):
        for u in ['B', 'KB', 'MB', 'GB', 'TB']:
            if b < 1024:
                return f"{b:.1f} {u}"
            b /= 1024
        return f"{b:.1f} PB"
    await send_notification(
        NotifyEvent.ERROR,
        _t("disk_low_title"),
        _t("disk_low_body", months=remaining_months,
           avail=_fmt(available_bytes), rate=_fmt(bytes_per_month)),
    )
