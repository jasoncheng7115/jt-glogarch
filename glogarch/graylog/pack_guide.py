# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""The usage guide that travels with a downloaded pack, in the language of the page.

Everything specific in it is read from the pack that is leaving, after the sensitive-value
decision and any version conversion, so the guide cannot describe a different pack. The steps
are what was measured (graylog/packs.py): a stream comes out of an install paused, a pipeline
runs only for the streams it is connected to, a title clash fails the whole install.

HTML because a customer's admin can open it with a double click; a table in a .md file is
noise in Notepad. Graylog's own menu names stay in English in all three languages: its UI is
English, and a translated name would not be found on screen.
"""

from __future__ import annotations

import html
import io
import json
import re
import zipfile
from typing import Any

from glogarch.graylog import pack_compat
from glogarch.graylog.packs import _title, analyze, val

LANGS = ("en", "zh-TW", "ja")
_GEO = re.compile(r"_(?:geolocation|country_code|city_name)\b")
_HOST_FIELDS = {"source", "gl2_source_input", "gl2_remote_ip"}
_TYPE_ORDER = ("dashboard", "stream", "pipeline", "pipeline_rule", "event_definition", "notification",
               "input", "lookup_table", "lookup_adapter", "lookup_cache", "grok_pattern")

_T: dict[str, dict[str, str]] = {
    "en": {
        "file": "User-Guide.html",
        "rev": "Revision {rev}",
        "converted": "Converted for Graylog {v}.",
        "h_about": "What this pack does",
        "own_desc": "The description in the pack, as its author wrote it:",
        "collect": "How the logs get in: {v}",
        "h_inside": "What gets installed",
        "col_item": "Item", "col_count": "Count",
        "t_dashboard": "Dashboards", "t_stream": "Streams", "t_pipeline": "Pipelines", "t_pipeline_rule": "Pipeline rules",
        "t_event_definition": "Alerts (event definitions)", "t_notification": "Notifications", "t_input": "Inputs",
        "t_lookup_table": "Lookup tables", "t_lookup_adapter": "Lookup adapters", "t_lookup_cache": "Lookup caches",
        "t_grok_pattern": "Grok patterns",
        "tabs": "{n} tabs",
        "h_before": "Before you install",
        "need_version": "Graylog {v} or newer.",
        "need_older": "On an older Graylog, download this pack again and choose that version in the download dialog.",
        "need_plugin": "Needs: {v}",
        "need_input": "This pack creates no input. Create one for your logs under System → Inputs and point the source at it.",
        "has_input": "This pack creates these inputs: {v}. Check that their ports are free.",
        "need_geo": "Maps and country columns need the Geo-Location Processor: System → Configurations → Geo-Location Processor, with a GeoLite2-City database.",
        "need_lookup": "These lookup tables are used but not included: {v}. Without them the columns they fill stay empty and everything else works. Create tables with these exact names if you want those columns.",
        "h_install": "Install",
        "s_unzip": "Unzip this file. Graylog takes the .json file, not the ZIP.",
        "s_upload": "In Graylog go to System → Content Packs, click Upload and choose {file}.",
        "s_install": "Open “{name}” in the list and click Install.",
        "s_params": "Fill in the parameters Graylog asks for: {v}.",
        "h_upgrade": "Already have an earlier version?",
        "upgrade": "Uninstall it first. Graylog refuses a second pipeline or rule with the same title and the whole install fails with a bare error, leaving nothing behind.",
        "upgrade_warn": "Uninstalling also deletes anything you changed in what it installed, such as stream rules, thresholds and notifications. Write them down first and set them again afterwards.",
        "h_after": "After installing",
        "a_start": "Start the stream under Streams → Start Stream: {v}. Graylog creates every installed stream paused, and until it runs its pipelines do nothing and the dashboards stay empty.",
        "a_host": "Change this stream rule to match your own hosts: “{s}”, field {f}, value {v}. It still holds the values of the site this pack was built on, so nothing of yours would match.",
        "a_default": "These pipelines are connected to the default stream, so they already run: {v}. They look at every message; for less load, connect them to a stream holding only these sources under System → Pipelines → Manage connections.",
        "a_removed": "If you route these logs into your own stream with “Remove matches from Default Stream”, the default stream no longer sees them and the pipelines do not run. Connect all of the pipelines above to your stream under System → Pipelines → Manage connections.",
        "a_connect": "Connect these pipelines to the stream that holds these logs, under System → Pipelines → Manage connections: {v}. A pipeline with no stream processes nothing.",
        "a_alerts_quiet": "The {n} alerts have no notification: events are only written to Graylog. To be told, add one under Alerts → Event Definitions.",
        "a_alerts_notify": "This pack brings notifications. Check who they go to before relying on them: {v}.",
        "a_dash": "Open the dashboards under Dashboards: {v}.",
        "a_new": "Only messages received after this point are parsed. Graylog does not go back over what is already stored.",
        "h_verify": "Check that it works",
        "v_query": "In Search, over the last hour, run this query. Any result means the pipelines are working:",
        "v_generic": "Send a log from the device, wait a minute and open the dashboard with the time range widened.",
        "h_notes": "Notes for this pack",
        "h_trouble": "Troubleshooting",
        "col_symptom": "What you see", "col_check": "What to check",
        "tr_all": "Every widget is 0 or empty",
        "tr_all_fix": "In this order: the stream is started; messages are arriving (Search for them with no query); the pipelines are connected to a stream those messages are in; the time range covers them. If a message has none of the expected fields, the pipelines did not run on it.",
        "tr_some": "Only some widgets are empty",
        "tr_some_fix": "Usually there are no such events in the time range. A field added by a newer rule only appears on new messages.",
        "tr_500": "Install fails with an error and nothing changes",
        "tr_500_fix": "A pipeline or rule with the same title already exists; see “Already have an earlier version?”. Also check the Graylog version above.",
        "h_remove": "Removing it",
        "remove": "System → Content Packs → open the pack → Uninstall. Messages already stored stay.",
    },
    "zh-TW": {
        "file": "使用說明.html",
        "rev": "修訂版 {rev}",
        "converted": "已轉換為 Graylog {v} 可用的版本。",
        "h_about": "這個套件做什麼",
        "own_desc": "套件內附的說明，內容為作者原文：",
        "collect": "記錄如何送入：{v}",
        "h_inside": "會安裝哪些項目",
        "col_item": "項目", "col_count": "數量",
        "t_dashboard": "看板", "t_stream": "串流", "t_pipeline": "管線", "t_pipeline_rule": "管線規則",
        "t_event_definition": "告警（event definition）", "t_notification": "通知", "t_input": "Input",
        "t_lookup_table": "Lookup table", "t_lookup_adapter": "Lookup adapter", "t_lookup_cache": "Lookup cache",
        "t_grok_pattern": "Grok pattern",
        "tabs": "{n} 個分頁",
        "h_before": "安裝前",
        "need_version": "需要 Graylog {v} 以上。",
        "need_older": "Graylog 版本較舊時，請重新下載，並在下載視窗選擇該版本。",
        "need_plugin": "需要：{v}",
        "need_input": "這個套件不會建立 Input。請到 System → Inputs 自行建立，並把記錄來源指向它。",
        "has_input": "這個套件會建立這些 Input：{v}。請先確認連接埠沒有被占用。",
        "need_geo": "地圖與國別欄位需要 Geo-Location Processor：到 System → Configurations → Geo-Location Processor 啟用，並準備 GeoLite2-City 資料庫。",
        "need_lookup": "這些 lookup table 有用到但沒有包含在套件內：{v}。沒有它們時，由它們填入的欄位會是空的，其他功能不受影響。需要這些欄位時，請用完全相同的名稱自行建立。",
        "h_install": "安裝",
        "s_unzip": "先解壓縮這個檔案。Graylog 要上傳的是 .json 檔，不是 ZIP。",
        "s_upload": "到 Graylog 的 System → Content Packs，按 Upload，選擇 {file}。",
        "s_install": "在清單開啟「{name}」，按 Install。",
        "s_params": "填入 Graylog 要求的參數：{v}。",
        "h_upgrade": "已經裝過舊版？",
        "upgrade": "請先移除舊版。Graylog 不接受標題相同的管線或規則，安裝會整包失敗並只顯示一般錯誤，不會留下任何項目。",
        "upgrade_warn": "移除時，您改過的設定也會一起刪掉，例如串流規則、告警門檻和通知。請先記下來，裝好後再設定一次。",
        "h_after": "安裝後要做的事",
        "a_start": "到 Streams 按 Start Stream 啟動串流：{v}。Graylog 建立的串流都是暫停狀態，啟動前管線不會運作，看板也沒有資料。",
        "a_host": "把這條串流規則改成您自己的主機：「{s}」，欄位 {f}，值 {v}。這裡還是打包環境的值，不修改就比對不到您的記錄。",
        "a_default": "這些管線已接到預設串流，所以裝好就會運作：{v}。它們會檢查每一筆記錄；想減輕負擔，可到 System → Pipelines → Manage connections 改接到只含這類來源的串流。",
        "a_removed": "如果您把這些記錄導到自建串流，並勾選「Remove matches from Default Stream」，預設串流就收不到這些記錄，管線也不會運作。請到 System → Pipelines → Manage connections，把上面所有管線都接到您的串流。",
        "a_connect": "到 System → Pipelines → Manage connections，把這些管線接到存放這類記錄的串流：{v}。沒有接串流的管線不會處理任何記錄。",
        "a_alerts_quiet": "這 {n} 條告警沒有設定通知，事件只會寫進 Graylog。需要收到通知時，請到 Alerts → Event Definitions 加上。",
        "a_alerts_notify": "這個套件帶有通知。使用前請確認收件對象：{v}。",
        "a_dash": "到 Dashboards 開啟看板：{v}。",
        "a_new": "只有從現在起收到的記錄才會被解析，已存入的記錄不會回溯。",
        "h_verify": "確認是否正常",
        "v_query": "到 Search，時間範圍選最近一小時，輸入下面的查詢。有結果就表示管線正常運作：",
        "v_generic": "從設備送一筆記錄，等一分鐘，把看板的時間範圍拉大後查看。",
        "h_notes": "這個套件的注意事項",
        "h_trouble": "疑難排解",
        "col_symptom": "看到的狀況", "col_check": "要檢查什麼",
        "tr_all": "所有 widget 都是 0 或無資料",
        "tr_all_fix": "請依序確認：串流已啟動；記錄確實有進來（到 Search 不輸入條件查詢）；管線有接到這些記錄所在的串流；時間範圍有涵蓋這些記錄。如果記錄上完全沒有預期的欄位，就是管線沒有處理到它。",
        "tr_some": "只有部分 widget 沒有資料",
        "tr_some_fix": "通常是該時段沒有這類事件。新版規則才產生的欄位，只會出現在之後收到的記錄上。",
        "tr_500": "安裝時出現錯誤，什麼都沒有建立",
        "tr_500_fix": "已存在標題相同的管線或規則，請看「已經裝過舊版？」。也請確認上面寫的 Graylog 版本。",
        "h_remove": "移除",
        "remove": "到 System → Content Packs 開啟套件，按 Uninstall。已存入的記錄會保留。",
    },
    "ja": {
        "file": "使用ガイド.html",
        "rev": "リビジョン {rev}",
        "converted": "Graylog {v} 向けに変換済みです。",
        "h_about": "このパックの内容",
        "own_desc": "パックに含まれる説明です（作者の原文のままです）：",
        "collect": "ログの送信方法：{v}",
        "h_inside": "インストールされるもの",
        "col_item": "項目", "col_count": "数",
        "t_dashboard": "ダッシュボード", "t_stream": "ストリーム", "t_pipeline": "パイプライン", "t_pipeline_rule": "パイプラインルール",
        "t_event_definition": "アラート（event definition）", "t_notification": "通知", "t_input": "Input",
        "t_lookup_table": "Lookup table", "t_lookup_adapter": "Lookup adapter", "t_lookup_cache": "Lookup cache",
        "t_grok_pattern": "Grok pattern",
        "tabs": "{n} タブ",
        "h_before": "インストールの前に",
        "need_version": "Graylog {v} 以降が必要です。",
        "need_older": "Graylog が古い場合は、ダウンロード画面でそのバージョンを選んでダウンロードし直してください。",
        "need_plugin": "必要なもの：{v}",
        "need_input": "このパックは Input を作成しません。System → Inputs で作成し、ログの送信先に指定してください。",
        "has_input": "このパックは次の Input を作成します：{v}。ポートが空いていることを確認してください。",
        "need_geo": "地図と国の列には Geo-Location Processor が必要です。System → Configurations → Geo-Location Processor で有効にし、GeoLite2-City データベースを用意してください。",
        "need_lookup": "次の Lookup table は使われていますが、パックには含まれていません：{v}。ない場合、それらが埋める列は空のままですが、他の機能には影響しません。必要な場合は同じ名前で作成してください。",
        "h_install": "インストール",
        "s_unzip": "このファイルを解凍してください。Graylog にアップロードするのは ZIP ではなく .json ファイルです。",
        "s_upload": "Graylog の System → Content Packs で Upload をクリックし、{file} を選びます。",
        "s_install": "一覧で「{name}」を開き、Install をクリックします。",
        "s_params": "Graylog が求めるパラメーターを入力します：{v}。",
        "h_upgrade": "以前のバージョンがインストール済みの場合",
        "upgrade": "先にアンインストールしてください。Graylog は同じタイトルのパイプラインやルールを受け付けず、インストール全体が一般的なエラーで失敗します。何も作成されません。",
        "upgrade_warn": "アンインストールすると、変更した設定（ストリームルール、しきい値、通知など）も削除されます。先に控えておき、インストール後に設定し直してください。",
        "h_after": "インストール後の作業",
        "a_start": "Streams で Start Stream をクリックしてストリームを開始します：{v}。作成されたストリームはすべて一時停止の状態で、開始するまでパイプラインは動作せず、ダッシュボードも空のままです。",
        "a_host": "このストリームルールをお使いのホストに合わせて変更してください：「{s}」、フィールド {f}、値 {v}。パックを作成した環境の値のままなので、変更しないとログに一致しません。",
        "a_default": "次のパイプラインはデフォルトストリームに接続済みのため、すぐに動作します：{v}。すべてのメッセージを確認するので、負荷を減らすには System → Pipelines → Manage connections で、このソースのみを含むストリームに接続し直してください。",
        "a_removed": "これらのログを「Remove matches from Default Stream」を有効にした独自のストリームに振り分けると、デフォルトストリームに届かなくなり、パイプラインは動作しません。System → Pipelines → Manage connections で、上記のパイプラインをすべてそのストリームに接続してください。",
        "a_connect": "System → Pipelines → Manage connections で、次のパイプラインをこのログが入るストリームに接続してください：{v}。ストリームに接続していないパイプラインは何も処理しません。",
        "a_alerts_quiet": "この {n} 件のアラートには通知が設定されていません。イベントは Graylog に記録されるだけです。通知が必要な場合は Alerts → Event Definitions で追加してください。",
        "a_alerts_notify": "このパックには通知が含まれています。使用前に送信先を確認してください：{v}。",
        "a_dash": "Dashboards でダッシュボードを開きます：{v}。",
        "a_new": "解析されるのは、これ以降に受信したメッセージのみです。保存済みのメッセージはさかのぼって解析されません。",
        "h_verify": "動作の確認",
        "v_query": "Search で時間範囲を直近 1 時間にして、次のクエリを実行します。結果が出ればパイプラインは動作しています：",
        "v_generic": "機器からログを送信し、1 分ほど待ってから、時間範囲を広げてダッシュボードを確認してください。",
        "h_notes": "このパックの注意事項",
        "h_trouble": "トラブルシューティング",
        "col_symptom": "症状", "col_check": "確認すること",
        "tr_all": "すべてのウィジェットが 0 または空です",
        "tr_all_fix": "次の順に確認してください：ストリームが開始されていること、メッセージが届いていること（Search を条件なしで実行）、そのメッセージが入るストリームにパイプラインが接続されていること、時間範囲に含まれていること。メッセージに想定のフィールドがまったくない場合は、パイプラインが処理していません。",
        "tr_some": "一部のウィジェットだけが空です",
        "tr_some_fix": "多くの場合、その時間範囲に該当するイベントがありません。新しいルールで追加されたフィールドは、以降に受信したメッセージにのみ付きます。",
        "tr_500": "インストールがエラーになり、何も作成されません",
        "tr_500_fix": "同じタイトルのパイプラインまたはルールがすでに存在します。「以前のバージョンがインストール済みの場合」をご覧ください。上記の Graylog のバージョンも確認してください。",
        "h_remove": "削除",
        "remove": "System → Content Packs でパックを開き、Uninstall をクリックします。保存済みのメッセージは残ります。",
    },
}

_CSS = """
:root{--bg:#fff;--fg:#1f2430;--mut:#5d6575;--line:#d9dde5;--box:#f4f6f9;--warn:#fff6e5;--warnline:#e0a100;--ac:#2f5fb3}
@media (prefers-color-scheme:dark){:root{--bg:#171a21;--fg:#e6e9ef;--mut:#a3abba;--line:#343a46;--box:#20242d;--warn:#33290f;--warnline:#b98500;--ac:#8db2f2}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.65 -apple-system,"Segoe UI","Noto Sans TC","Noto Sans JP","Microsoft JhengHei","Yu Gothic",sans-serif}
main{max-width:860px;margin:0 auto;padding:32px 20px 56px}h1{font-size:28px;line-height:1.3;margin:0 0 4px}
h2{font-size:20px;margin:32px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--line)}h3{font-size:16px;margin:18px 0 6px}
.sub{color:var(--mut);margin:0 0 16px}ol,ul{padding-left:24px}li{margin:6px 0}
table{border-collapse:collapse;width:100%;margin:10px 0}th,td{border:1px solid var(--line);padding:7px 10px;text-align:left;vertical-align:top}th{background:var(--box)}
td.n{text-align:right;width:90px}code{background:var(--box);padding:1px 5px;border-radius:4px;overflow-wrap:anywhere;font:14px ui-monospace,Menlo,Consolas,monospace}
pre{background:var(--box);padding:10px 12px;border-radius:6px;white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.5 ui-monospace,Menlo,Consolas,monospace}
.warn{background:var(--warn);border-left:4px solid var(--warnline);padding:10px 14px;border-radius:4px;margin:12px 0}
.desc{white-space:pre-wrap;background:var(--box);padding:10px 14px;border-radius:6px;overflow-wrap:anywhere}
@media print{main{max-width:none;padding:0}}
"""


def normalize_lang(lang: Any) -> str:
    return lang if lang in LANGS else "en"


def pack_filename(pack: dict) -> str:
    name = re.sub(r"[^\w.-]+", "_", str(pack.get("name") or "pack"))
    return f"{name}-r{pack.get('rev')}.json"


def facts(pack: dict) -> dict:
    """What the steps depend on, read from this pack."""
    a = analyze(pack)
    ents = pack.get("entities") or []
    of = lambda t: [e for e in ents if (e.get("type") or {}).get("name") == t]  # noqa: E731
    host_rules = []
    for e in of("stream"):
        for r in (e.get("data") or {}).get("stream_rules") or []:
            if str(val(r.get("field"))) in _HOST_FIELDS:
                host_rules.append({"stream": _title(e), "field": str(val(r.get("field"))), "value": str(val(r.get("value")))})
    versions, plugins = [], set()
    for e in ents:
        for c in e.get("constraints") or []:
            if c.get("type") == "server-version":
                m = re.search(r"\d+(?:\.\d+)*", str(c.get("version") or ""))
                if m:
                    versions.append(m.group(0))
            elif c.get("type"):
                plugins.add(f"{c.get('plugin') or c.get('type')} {c.get('version') or ''}".strip())
    dashboards = []
    for e in of("dashboard"):
        dashboards.append({"title": _title(e), "tabs": len((e.get("data") or {}).get("state") or {})})
    alerts = of("event_definition")
    version_key = lambda v: tuple(int(x) for x in v.split("."))  # noqa: E731
    needed = pack_compat.needs_version(ents)
    return {
        "counts": a["counts"], "streams": a["streams"], "host_rules": host_rules,
        "default_pipelines": a["default_stream_pipelines"], "unconnected": a["unconnected_pipelines"],
        "lookups": a["lookup_tables_used"], "dashboards": dashboards,
        "version": max(versions + ([needed] if needed else []), key=version_key, default=""),
        "plugins": sorted(plugins), "inputs": [_title(e) for e in of("input")],
        "notifications": [_title(e) for e in of("notification")], "alert_count": len(alerts),
        "alerts_notify": sum(1 for e in alerts if (e.get("data") or {}).get("notifications")),
        "parameters": [str(p.get("name")) for p in pack.get("parameters") or []],
        "geo": any(_GEO.search(json.dumps(e.get("data") or {}, ensure_ascii=False)) for e in of("dashboard")),
    }


def render(pack: dict, lang: str, notes: dict | None = None, target_version: str = "") -> str:
    """notes: this pack's entry from the library's translated notes, when it has one."""
    lang = normalize_lang(lang)
    t, f, notes = _T[lang], facts(pack), notes or {}
    e = html.escape
    name = str(pack.get("name") or "")

    def tx(key: str, **kw) -> str:
        """A template with its values escaped; the templates themselves are ours."""
        out = e(t[key], quote=False)
        for k, v in kw.items():
            out = out.replace("{" + k + "}", v)
        return out

    def code_list(items) -> str:
        return ", ".join(f"<code>{e(str(i))}</code>" for i in items)

    def localized(key: str) -> Any:
        return (notes.get(key) or {}).get(lang)

    b = [f'<!doctype html>\n<html lang="{e(lang)}"><head><meta charset="utf-8">'
         f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(name)}</title>'
         f"<style>{_CSS}</style></head><body><main><h1>{e(name)}</h1>"]
    sub = [tx("rev", rev=e(str(pack.get("rev"))))]
    if pack.get("vendor"):
        sub.append(e(str(pack["vendor"])))
    b.append(f'<p class="sub">{" · ".join(sub)}</p>')
    if target_version:
        b.append(f'<p class="sub">{tx("converted", v=e(target_version))}</p>')

    b.append(f'<h2>{tx("h_about")}</h2>')
    # An untranslated description is labelled as such; it is never passed off as this language.
    summary = localized("summary") or (str(pack.get("summary") or "") if lang == "zh-TW" and notes else "")
    if summary:
        b.append(f"<p>{e(summary)}</p>")
    if localized("collect"):
        b.append(f'<p>{tx("collect", v=e(localized("collect")))}</p>')
    if not notes:
        if pack.get("summary"):
            b.append(f'<p>{e(str(pack["summary"]))}</p>')
        if pack.get("description"):
            b.append(f'<p>{tx("own_desc")}</p><div class="desc">{e(str(pack["description"]))}</div>')

    b.append(f'<h2>{tx("h_inside")}</h2><table><tr><th>{tx("col_item")}</th><th>{tx("col_count")}</th></tr>')
    others = sorted(k for k in f["counts"] if k not in _TYPE_ORDER)
    for k in list(_TYPE_ORDER) + others:
        if f["counts"].get(k):
            label = tx("t_" + k) if "t_" + k in t else e(k)
            b.append(f'<tr><td>{label}</td><td class="n">{f["counts"][k]}</td></tr>')
    b.append("</table>")
    if f["dashboards"]:
        left, right = ("(", ")") if lang == "en" else ("（", "）")
        b.append("<ul>" + "".join(f'<li>{e(d["title"])} {left}{tx("tabs", n=str(d["tabs"]))}{right}</li>'
                                  for d in f["dashboards"]) + "</ul>")

    before = []
    # A converted file was only tried on its own version, so it does not promise "or newer".
    if f["version"] and not target_version:
        before.append(tx("need_version", v=e(f["version"])) + ("" if lang != "en" else " ") + tx("need_older"))
    if f["plugins"]:
        before.append(tx("need_plugin", v=code_list(f["plugins"])))
    if f["inputs"]:
        before.append(tx("has_input", v=code_list(f["inputs"])))
    elif not notes.get("no_input"):
        before.append(tx("need_input"))
    if f["geo"]:
        before.append(tx("need_geo"))
    if f["lookups"]:
        before.append(tx("need_lookup", v=code_list(f["lookups"])))
    b.append(f'<h2>{tx("h_before")}</h2><ul>' + "".join(f"<li>{x}</li>" for x in before) + "</ul>")

    steps = [tx("s_unzip"), tx("s_upload", file=f"<code>{e(pack_filename(pack))}</code>"), tx("s_install", name=e(name))]
    if f["parameters"]:
        steps.append(tx("s_params", v=code_list(f["parameters"])))
    b.append(f'<h2>{tx("h_install")}</h2><ol>' + "".join(f"<li>{x}</li>" for x in steps) + "</ol>")
    b.append(f'<h3>{tx("h_upgrade")}</h3><p>{tx("upgrade")}</p><div class="warn">{tx("upgrade_warn")}</div>')

    after = []
    if f["streams"]:
        after.append(tx("a_start", v=code_list(f["streams"])))
    for r in f["host_rules"]:
        after.append(tx("a_host", s=e(r["stream"]), f=f'<code>{e(r["field"])}</code>', v=f'<code>{e(r["value"])}</code>'))
    if f["default_pipelines"]:
        after.append(tx("a_default", v=code_list(f["default_pipelines"])))
        after.append(tx("a_removed"))
    if f["unconnected"]:
        after.append(tx("a_connect", v=code_list(f["unconnected"])))
    if f["notifications"]:
        after.append(tx("a_alerts_notify", v=code_list(f["notifications"])))
    if f["alert_count"] and not f["alerts_notify"]:
        after.append(tx("a_alerts_quiet", n=str(f["alert_count"])))
    if f["dashboards"]:
        after.append(tx("a_dash", v=code_list(d["title"] for d in f["dashboards"])))
    if f["counts"].get("pipeline"):
        after.append(tx("a_new"))
    if after:
        b.append(f'<h2>{tx("h_after")}</h2><ol>' + "".join(f"<li>{x}</li>" for x in after) + "</ol>")

    b.append(f'<h2>{tx("h_verify")}</h2>')
    if notes.get("verify"):
        b.append(f'<p>{tx("v_query")}</p><pre>{e(str(notes["verify"]))}</pre>')
    else:
        b.append(f'<p>{tx("v_generic")}</p>')

    note_list = localized("notes") or []
    if note_list:
        b.append(f'<h2>{tx("h_notes")}</h2><ul>' + "".join(f"<li>{e(str(x))}</li>" for x in note_list) + "</ul>")

    b.append(f'<h2>{tx("h_trouble")}</h2><table><tr><th>{tx("col_symptom")}</th><th>{tx("col_check")}</th></tr>')
    for sym, fix in (("tr_all", "tr_all_fix"), ("tr_some", "tr_some_fix"), ("tr_500", "tr_500_fix")):
        b.append(f"<tr><td>{tx(sym)}</td><td>{tx(fix)}</td></tr>")
    b.append(f'</table><h2>{tx("h_remove")}</h2><p>{tx("remove")}</p></main></body></html>\n')
    return "".join(b)


def bundle(pack: dict, lang: str, notes: dict | None = None, target_version: str = "") -> tuple[bytes, str]:
    """(ZIP bytes, its file name): the pack as it would be uploaded, and the guide beside it."""
    lang = normalize_lang(lang)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(pack_filename(pack), json.dumps(pack, ensure_ascii=False, indent=2))
        z.writestr(_T[lang]["file"], render(pack, lang, notes, target_version))
    stem = pack_filename(pack)[:-len(".json")]
    if target_version:
        stem += f"-graylog{target_version}"
    return buf.getvalue(), f"{stem}-{lang}.zip"

