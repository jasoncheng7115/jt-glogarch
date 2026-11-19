# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Notification sender — Telegram, Discord, Slack, Teams, Nextcloud Talk, Zulip, Email."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

import html as _html
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
    SECURITY_INCIDENT = "security_incident"


def _should_send(config: NotifyConfig, event: NotifyEvent) -> bool:
    mapping = {
        NotifyEvent.EXPORT_COMPLETE: config.on_export_complete,
        NotifyEvent.IMPORT_COMPLETE: config.on_import_complete,
        NotifyEvent.CLEANUP_COMPLETE: config.on_cleanup_complete,
        NotifyEvent.VERIFY_FAILED: config.on_verify_failed,
        NotifyEvent.ERROR: config.on_error,
        NotifyEvent.SENSITIVE_API_OPERATION: config.on_sensitive_operation,
        NotifyEvent.AUDIT_ALERT: config.on_audit_alert,
        NotifyEvent.SECURITY_INCIDENT: config.on_security_incident,
    }
    return mapping.get(event, False)


def _has_any_channel(config: NotifyConfig) -> bool:
    return any([
        config.telegram.enabled,
        config.discord.enabled,
        config.slack.enabled,
        config.teams.enabled,
        config.nextcloud_talk.enabled,
        config.zulip.enabled,
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

    timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    results = await deliver_to_channels(config, title, message, timestamp)

    for r in results:
        if r["success"]:
            log.info("Notification sent", channel=r["channel"], notify_event=event.value)
        else:
            log.error("Notification failed", channel=r["channel"], error=r.get("error"))

    return results


async def deliver_to_channels(config: NotifyConfig, title: str, message: str,
                              timestamp: str) -> list[dict]:
    """Send one message to every enabled channel; one result dict per channel.

    The ONLY place the channel list is walked. The test endpoint used to repeat
    it, so every new channel had to be added twice and a missed copy meant "Send
    test" silently skipped a channel that real notifications used (or the other
    way round)."""
    results = []
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

        if config.zulip.enabled:
            results.append(await _send_zulip(client, config.zulip, title, message, timestamp))

    if config.email.enabled:
        results.append(await _send_email(config.email, title, message, timestamp))
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

def _slack_escape(text: str) -> str:
    """Slack's documented escaping for mrkdwn text: & < > only."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


async def _send_slack(client: httpx.AsyncClient, cfg, title: str, message: str, ts: str) -> dict:
    try:
        resp = await client.post(cfg.webhook_url, json={
            "blocks": [
                {"type": "header", "text": {"type": "plain_text", "text": f"jt-glogarch: {title}"}},
                {"type": "section", "text": {"type": "mrkdwn", "text": _slack_escape(message)}},
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


# --- Zulip ---

def _zulip_content(title: str, message: str, ts: str) -> str:
    """Zulip renders Markdown. The body goes in a code block so the padded stat
    labels line up (the same reason Telegram uses <pre>) and so a log line full of
    `*`, `_` or `#` is shown as written. The fence is longer than any backtick run
    in the message, so a message containing ``` cannot close the block early."""
    import re
    longest = max((len(m) for m in re.findall(r"`+", message)), default=0)
    fence = "`" * max(3, longest + 1)
    return f"**[jt-glogarch] {title}**\n{fence}text\n{message}\n{fence}\n{ts}"


async def _send_zulip(client: httpx.AsyncClient, cfg, title: str, message: str, ts: str) -> dict:
    try:
        if not (cfg.server_url and cfg.bot_email and cfg.api_key and cfg.stream):
            raise RuntimeError("Zulip server URL / bot email / API key / stream not set")
        resp = await client.post(
            f"{cfg.server_url.rstrip('/')}/api/v1/messages",
            auth=httpx.BasicAuth(cfg.bot_email, cfg.api_key),
            data={"type": "stream", "to": cfg.stream,
                  "topic": cfg.topic or "jt-glogarch",
                  "content": _zulip_content(title, message, ts)},
        )
        if resp.status_code >= 400:
            # Zulip says what is wrong ("Invalid API key", "Stream 'x' does not
            # exist") — a bare "401" would leave the operator guessing.
            try:
                detail = str(resp.json().get("msg") or "")[:200]
            except ValueError:
                detail = resp.text[:200]
            raise RuntimeError(f"HTTP {resp.status_code}: {detail}" if detail
                               else f"HTTP {resp.status_code}")
        return {"channel": "zulip", "success": True}
    except Exception as e:
        return {"channel": "zulip", "success": False, "error": str(e)}


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
        # Escaped: messages carry text from logs (an account name tried in a
        # brute force, an IDS signature), and `<url>` placeholders vanished as
        # unknown tags before this.
        html_body = f"""<div style="font-family:sans-serif;max-width:600px">
<h2 style="color:#6c63ff">{_html.escape(cfg.subject_prefix)} {_html.escape(title)}</h2>
<pre style="background:#f5f5f5;padding:12px;border-radius:6px;white-space:pre-wrap">{_html.escape(message)}</pre>
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
        "export_overflow": "⚠️ Export Complete (some records exceeded the API per-query limit)",
        "overflow_counts": "({total} in that millisecond: {kept} kept, {unread} unread)",
        "overflow_note": ("What this means: one single millisecond held more than 10,000 messages, "
                          "and 10,000 is the most Graylog's API can return for one query. At the {n} "
                          "timestamp(s) below, the messages past that limit could not be read.\n"
                          "Everything else in those chunks WAS archived — this run did not fail, and "
                          "these windows will NOT be retried.\n"
                          "To collect the remainder, run an OpenSearch Direct export over the hour "
                          "containing each timestamp below. What is already archived is kept and "
                          "skipped; the missing millisecond is fetched (along with anything else in "
                          "that index not yet archived):"),
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
        "sec_title": "⚠️ Security incidents: {n}",
        "sec_new": "NEW",
        "sec_escalated": "escalated",
        "sec_ongoing": "still ongoing",
        "sec_line": "[{sev}] {det} — {entity}{ext}{flag}\n    {stats}",
        "sec_external": " (external)",
        "sec_footer": "Window: last {minutes} min · Server: {server}\nOpen Security Incidents in jt-glogarch for details.",
        "sec_failing_title": "❌ Security analysis is not running",
        "sec_failing_body": ("The last {n} runs on server {server} failed, so no incidents are being detected.\n"
                             "Last error: {error}"),
        "sec_sev_high": "HIGH", "sec_sev_medium": "MEDIUM", "sec_sev_low": "LOW",
        "sec_m_count": "events", "sec_m_card_user_name": "accounts", "sec_m_card_source": "hosts",
        "sec_m_card_source_ip": "sources", "sec_m_card_uri": "paths", "sec_m_card_vhost": "sites",
        "sec_m_success": "successful logins", "sec_m_min_alert_severity": "IDS severity",
        "sec_det_auth_bruteforce": "Brute force (many failed logins from one source)",
        "sec_det_auth_spray": "Password spraying (one source, many accounts)",
        "sec_det_auth_multi_host": "One source failing logins on many hosts",
        "sec_det_account_multi_host": "One account failing logins on many hosts",
        "sec_det_auth_success_after_fail": "Successful login after many failures",
        "sec_det_ids_alert_passed": "IDS alert not blocked",
        "sec_det_waf_scanner": "Web scanner (many paths through the WAF)",
        "datanode_fallback_title": "⚠️ Data Node certificate unusable — archived via Graylog API",
        "datanode_fallback_body": ("Schedule: {schedule}\nServer: {server}\n"
                                   "The Graylog Data Node client certificate could not be used: {problem}\n"
                                   "This run archived through the Graylog API instead, so nothing was skipped.\n"
                                   "Reconnect Data Node access in Settings → Graylog servers."),
        "datanode_renew_failed_title": "⚠️ Data Node certificate renewal failed",
        "datanode_renew_failed_body": ("Server: {server}\nThe certificate expires {expires} ({days} day(s) left).\n"
                                       "Error: {problem}\n"
                                       "jt-glogarch retries daily; if it keeps failing, reconnect "
                                       "Data Node access in Settings → Graylog servers."),
    },
    "zh-TW": {
        "export_ok": "✅ 匯出成功",
        "export_err": "⚠️ 匯出完成（有錯誤）",
        "export_overflow": "⚠️ 匯出完成（部分記錄超出 API 單次上限）",
        "overflow_counts": "（該毫秒共 {total} 筆：已保留 {kept}，未讀取 {unread}）",
        "overflow_note": ("這是什麼意思：同一毫秒內出現超過 10000 筆記錄，而 Graylog API 單次查詢"
                          "最多只能回傳 10000 筆。以下 {n} 個時間點，超出上限的那些記錄無法讀取。\n"
                          "這些區段的其餘記錄都已完整歸檔——本次匯出並未失敗，這些時段也不會重試。\n"
                          "若要補回未讀取的部分，請以 OpenSearch Direct 模式匯出包含以下時間點的那個小時。"
                          "已封存的部分會保留並自動略過，缺少的那一毫秒會被補抓"
                          "（該索引內其他尚未封存的資料也會一併封存）："),
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
        "sec_title": "⚠️ 資安事件：{n} 件",
        "sec_new": "首次出現",
        "sec_escalated": "等級升高",
        "sec_ongoing": "仍在持續",
        "sec_line": "[{sev}] {det} — {entity}{ext}{flag}\n    {stats}",
        "sec_external": "（外部）",
        "sec_footer": "時間範圍：最近 {minutes} 分鐘 · 伺服器：{server}\n詳情請到 jt-glogarch 的「資安事件」頁面查看。",
        "sec_failing_title": "❌ 資安事件分析沒有在運作",
        "sec_failing_body": ("伺服器 {server} 最近 {n} 次分析都失敗，目前沒有在偵測資安事件。\n"
                             "最後的錯誤：{error}"),
        "sec_sev_high": "高", "sec_sev_medium": "中", "sec_sev_low": "低",
        "sec_m_count": "筆", "sec_m_card_user_name": "個帳號", "sec_m_card_source": "台主機",
        "sec_m_card_source_ip": "個來源", "sec_m_card_uri": "個路徑", "sec_m_card_vhost": "個網站",
        "sec_m_success": "次登入成功", "sec_m_min_alert_severity": "IDS 嚴重度",
        "sec_det_auth_bruteforce": "暴力破解（同一來源大量登入失敗）",
        "sec_det_auth_spray": "密碼噴灑（同一來源嘗試多個帳號）",
        "sec_det_auth_multi_host": "同一來源在多台主機登入失敗",
        "sec_det_account_multi_host": "同一帳號在多台主機登入失敗",
        "sec_det_auth_success_after_fail": "多次失敗後登入成功",
        "sec_det_ids_alert_passed": "IDS 告警未被阻擋",
        "sec_det_waf_scanner": "網站掃描（經 WAF 嘗試大量路徑）",
        "datanode_fallback_title": "⚠️ Data Node 憑證無法使用，已改用 Graylog API 歸檔",
        "datanode_fallback_body": ("排程：{schedule}\n伺服器：{server}\n"
                                   "無法使用 Graylog Data Node 用戶端憑證：{problem}\n"
                                   "本次已改用 Graylog API 歸檔，沒有略過任何資料。\n"
                                   "請到「設定 → Graylog 伺服器」重新連接 Data Node。"),
        "datanode_renew_failed_title": "⚠️ Data Node 憑證更新失敗",
        "datanode_renew_failed_body": ("伺服器：{server}\n憑證到期：{expires}（剩 {days} 天）。\n"
                                       "錯誤：{problem}\n"
                                       "jt-glogarch 每天會再試一次；若持續失敗，請到「設定 → Graylog 伺服器」重新連接 Data Node。"),
    },
    "ja": {
        "export_ok": "✅ エクスポート完了",
        "export_err": "⚠️ エクスポート完了（エラーあり）",
        "export_overflow": "⚠️ エクスポート完了（一部のレコードが API の 1 回あたりの上限を超えました）",
        "overflow_counts": "（このミリ秒の合計 {total} 件：保存 {kept} 件、未読 {unread} 件）",
        "overflow_note": ("これは何を意味するか：1 ミリ秒の中に 10,000 件を超えるメッセージがありましたが、"
                          "Graylog API が 1 回のクエリで返せるのは最大 10,000 件です。以下の {n} 件の"
                          "タイムスタンプでは、上限を超えた分のメッセージを読み取れませんでした。\n"
                          "それらの区間のその他のレコードはすべてアーカイブ済みです。今回の実行は失敗ではなく、"
                          "これらの時間帯は再試行されません。\n"
                          "残りを取得するには、以下の各タイムスタンプを含む 1 時間を対象に、OpenSearch 直接モードで"
                          "エクスポートしてください。アーカイブ済みの部分は保持されてスキップされ、欠けている"
                          "ミリ秒が取得されます（そのインデックス内でまだアーカイブされていない他のデータも"
                          "あわせてアーカイブされます）："),
        "export_body": ("エクスポート区間：{chunks}\n"
                        "スキップ区間　　：{skipped}\n"
                        "レコード数　　　：{records}\n"
                        "書き込みファイル：{files}\n"
                        "元のサイズ　　　：{original}\n"
                        "圧縮後　　　　　：{compressed}\n"
                        "所要時間　　　　：{duration}\n"
                        "モード　　　　　：{mode}"),
        "import_ok": "✅ インポート完了",
        "import_cancelled": "⏹️ インポートはユーザーによりキャンセルされました",
        "import_err": "⚠️ インポート完了（エラーあり）",
        "import_body": ("アーカイブ数：{archives}\n"
                        "レコード数　：{records}\n"
                        "所要時間　　：{duration}"),
        "cleanup_ok": "✅ クリーンアップ完了",
        "cleanup_body": ("削除ファイル数：{deleted}\n"
                         "解放容量　　　：{freed}"),
        "verify_ok": "✅ 検証完了",
        "verify_body": ("正常　　：{valid}\n"
                        "検査総数：{total}"),
        "verify_fail": "❌ 検証失敗",
        "corrupted": "破損：{n}",
        "tampered": "🚨 改ざん検出（HMAC 不一致）：{n}",
        "missing": "欠落：{n}",
        "error_title": "❌ {op} エラー",
        "errors": "エラー：{n}",
        "sensitive_title": "⚠️ 重要操作を {n} 件検出しました",
        "audit_alert_title": "⚠️ 操作監査アラート",
        "audit_alert_body": ("監査 syslog を {minutes} 分間受信していません。\n"
                             "Graylog には接続できますが、nginx の転送が停止している可能性があります。\n"
                             "最終受信：{last}\n"
                             "すべての Graylog ノードの nginx 設定と syslog を確認してください。"),
        "disk_low_title": "⚠️ アーカイブディスクの残り保存期間が少なくなっています",
        "disk_low_body": ("現在のペースでは、アーカイブ容量は残り約 {months} か月分です。\n"
                          "空き容量：{avail} · 毎月約 {rate} 増加。\n"
                          "容量が尽きる前に、アーカイブディスクを拡張するか保持期間を短くしてください。"),
        "sec_title": "⚠️ セキュリティインシデント：{n} 件",
        "sec_new": "初検出",
        "sec_escalated": "重大度上昇",
        "sec_ongoing": "継続中",
        "sec_line": "[{sev}] {det} — {entity}{ext}{flag}\n    {stats}",
        "sec_external": "（外部）",
        "sec_footer": "対象期間：直近 {minutes} 分 · サーバー：{server}\n詳細は jt-glogarch の「セキュリティインシデント」ページを確認してください。",
        "sec_failing_title": "❌ セキュリティ分析が動作していません",
        "sec_failing_body": ("サーバー {server} の直近 {n} 回の分析がすべて失敗したため、インシデントを検出できていません。\n"
                             "最後のエラー：{error}"),
        "sec_sev_high": "高", "sec_sev_medium": "中", "sec_sev_low": "低",
        "sec_m_count": "件", "sec_m_card_user_name": "アカウント", "sec_m_card_source": "ホスト",
        "sec_m_card_source_ip": "送信元", "sec_m_card_uri": "パス", "sec_m_card_vhost": "サイト",
        "sec_m_success": "回ログイン成功", "sec_m_min_alert_severity": "IDS 重大度",
        "sec_det_auth_bruteforce": "ブルートフォース（同一送信元からの大量のログイン失敗）",
        "sec_det_auth_spray": "パスワードスプレー（同一送信元が多数のアカウントを試行）",
        "sec_det_auth_multi_host": "同一送信元が多数のホストでログイン失敗",
        "sec_det_account_multi_host": "同一アカウントが多数のホストでログイン失敗",
        "sec_det_auth_success_after_fail": "多数の失敗の後のログイン成功",
        "sec_det_ids_alert_passed": "ブロックされなかった IDS アラート",
        "sec_det_waf_scanner": "Web スキャン（WAF 経由で多数のパスを試行）",
        "datanode_fallback_title": "⚠️ Data Node 証明書が使用できないため、Graylog API でアーカイブしました",
        "datanode_fallback_body": ("スケジュール：{schedule}\nサーバー：{server}\n"
                                   "Graylog Data Node のクライアント証明書を使用できません：{problem}\n"
                                   "今回は Graylog API でアーカイブしたため、スキップされたデータはありません。\n"
                                   "「設定 → Graylog サーバー」で Data Node に再接続してください。"),
        "datanode_renew_failed_title": "⚠️ Data Node 証明書の更新に失敗しました",
        "datanode_renew_failed_body": ("サーバー：{server}\n証明書の有効期限：{expires}（残り {days} 日）。\n"
                                       "エラー：{problem}\n"
                                       "jt-glogarch は毎日再試行します。失敗が続く場合は「設定 → Graylog サーバー」で Data Node に再接続してください。"),
    },
}


def _t(key: str, **kwargs) -> str:
    lang = "en"
    try:
        lang = get_settings().notify.language or "en"
    except Exception as e:
        log.debug("Could not read the notification language setting; defaulting to English", error=str(e))
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
    overflows: list[dict] | None = None,
):
    truncations = truncations or []
    overflows = overflows or []
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
        if overflows:
            for ow in overflows[:5]:
                line = f"  - {_fmt_overflow_ts(ow.get('timestamp', ''))}"
                if isinstance(ow.get("unread"), int):
                    # The one number that decides whether it is worth re-running.
                    line += "  " + _t("overflow_counts", total=f"{ow['total']:,}",
                                      kept=f"{ow['kept']:,}", unread=f"{ow['unread']:,}")
                lines.append(line)
        else:
            for tr in truncations[:5]:
                # Just the timestamp — the full remedy is in the header note.
                ts = tr.split(" had ")[0].split(" held ")[0].replace("Timestamp ", "")
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


async def notify_datanode_fallback(schedule: str, server: str, problem: str):
    """A scheduled OpenSearch-direct run could not use the Data Node
    certificate and archived through the Graylog API instead."""
    await send_notification(
        NotifyEvent.ERROR,
        _t("datanode_fallback_title"),
        _t("datanode_fallback_body", schedule=schedule, server=server, problem=problem[:300]),
    )


async def notify_datanode_renew_failed(server: str, expires: str, days, problem: str):
    await send_notification(
        NotifyEvent.ERROR,
        _t("datanode_renew_failed_title"),
        _t("datanode_renew_failed_body", server=server, expires=expires, days=days,
           problem=problem[:300]),
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


# --- Security incidents ----------------------------------------------------

def _plain(value: str, limit: int = 120) -> str:
    """Log-derived text for a notification: no control characters or line
    breaks, clipped, backticks neutralised, then put in a code span so Discord/
    Slack/Teams/Zulip markdown cannot turn it into a link or heading."""
    s = "".join(" " if (ord(c) < 32 or ord(c) == 127) else c for c in str(value))
    s = " ".join(s.split()).replace("`", "'")
    if len(s) > limit:
        s = s[:limit - 1] + "…"
    return f"`{s}`"


def _sec_stats(metrics: dict) -> str:
    parts = []
    for k, v in metrics.items():
        if v is None:
            continue
        key = "sec_m_" + k.replace(":", "_")
        label = _t(key)
        if label == key:
            continue
        if isinstance(v, float) and v.is_integer():
            v = int(v)
        parts.append(f"{v:,} {label}" if isinstance(v, int) and k != "min:alert_severity"
                     else f"{label} {v}")
    return " · ".join(parts)


async def notify_security_incidents(items: list[dict], server: str, window_minutes: int):
    """items: {detector, entity, severity, external, change, metrics}."""
    if not items:
        return []
    lines = []
    for it in items:
        flag = {"new": "", "escalated": f" · {_t('sec_escalated')}",
                "ongoing": f" · {_t('sec_ongoing')}"}.get(it.get("change"), "")
        if it.get("is_new"):
            flag = f" · {_t('sec_new')}" + flag
        lines.append(_t("sec_line", sev=_t("sec_sev_" + it["severity"]),
                        det=_t("sec_det_" + it["detector"]), entity=_plain(it["entity"]),
                        ext=_t("sec_external") if it.get("external") else "",
                        flag=flag, stats=_sec_stats(it.get("metrics") or {})))
    body = "\n".join(lines) + "\n\n" + _t("sec_footer", minutes=window_minutes, server=server)
    return await send_notification(NotifyEvent.SECURITY_INCIDENT, _t("sec_title", n=len(items)), body)


async def notify_security_failing(server: str, runs: int, error: str):
    from glogarch.utils.sanitize import sanitize
    return await send_notification(
        NotifyEvent.ERROR, _t("sec_failing_title"),
        _t("sec_failing_body", server=server, n=runs, error=sanitize(error)[:300]))
