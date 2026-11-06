# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""The SOP that travels with a downloaded pack, in the language of the page.

One Markdown file with the three procedures a customer needs: a new install, an upgrade from
an earlier version, and an uninstall (owner, 2026-11-06). Everything specific in it is read
from the pack that is leaving, after the sensitive-value decision and any version conversion,
so it cannot describe a different pack. The steps are what was measured (graylog/packs.py): a
stream comes out of an install paused, a pipeline runs only for the streams it is connected to,
a title clash fails the whole install, an uninstall deletes what the customer changed too.

Graylog's own menu names stay in English in all three languages: its UI is English, and a
translated name would not be found on screen. Values from the pack go in code spans or are
escaped, so a title cannot turn into markup in a Markdown viewer.
"""

from __future__ import annotations

import io
import json
import os
import re
import zipfile
from typing import Any

from glogarch.graylog import pack_compat
from glogarch.graylog.packs import DEFAULT_STREAM_ID, _title, analyze, val

LANGS = ("en", "zh-TW", "ja")
_GEO = re.compile(r"_(?:geolocation|country_code|city_name)\b")
_HOST_FIELDS = {"source", "gl2_source_input", "gl2_remote_ip"}
_TYPE_ORDER = ("dashboard", "stream", "pipeline", "pipeline_rule", "event_definition", "notification",
               "input", "lookup_table", "lookup_adapter", "lookup_cache", "grok_pattern")

_T: dict[str, dict[str, str]] = {
    "en": {
        "file": "SOP-install-upgrade-uninstall.md",
        "rev": "Revision {rev}",
        "converted": "Converted for Graylog {v}.",
        "which": "Follow the part that fits:",
        "w_new": "Never installed it: **1. New install**",
        "w_up": "An earlier version is installed: **2. Upgrade from an earlier version**",
        "w_rm": "Removing it: **3. Uninstall**",
        "h_about": "What this pack does",
        "own_desc": "The description in the pack, as its author wrote it:",
        "collect": "How the logs get in: {v}",
        "h_inside": "What gets installed",
        "t_dashboard": "Dashboards", "t_stream": "Streams", "t_pipeline": "Pipelines", "t_pipeline_rule": "Pipeline rules",
        "t_event_definition": "Alerts (event definitions)", "t_notification": "Notifications", "t_input": "Inputs",
        "t_lookup_table": "Lookup tables", "t_lookup_adapter": "Lookup adapters", "t_lookup_cache": "Lookup caches",
        "t_grok_pattern": "Grok patterns",
        "tabs": "{n} tabs",
        "h_new": "1. New install",
        "h_before": "Before you install",
        "need_version": "Graylog {v} or newer.",
        "need_older": "On an older Graylog, download this pack again and choose that version in the download dialog.",
        "need_plugin": "Needs: {v}",
        "need_input": "This pack creates no input. Create one for your logs under System → Inputs and point the source at it.",
        "has_input": "This pack creates these inputs: {v}. Check that their ports are free.",
        "need_geo": "Maps and country columns need the Geo-Location Processor: System → Configurations → Geo-Location Processor, with a GeoLite2-City database.",
        "need_lookup": "These lookup tables are used but not included: {v}. Without them the columns they fill stay empty and everything else works. Create tables with these exact names if you want those columns.",
        "h_steps": "Steps",
        "s_unzip": "Unzip the downloaded file. Graylog takes the .json file, not the ZIP.",
        "s_upload": "In Graylog go to System → Content Packs, click Upload and choose {file}.",
        "s_install": "Open “{name}” in the list and click Install.",
        "s_params": "Fill in the parameters Graylog asks for: {v}.",
        "h_after": "After installing",
        "a_start": "Start the stream under Streams → Start Stream: {v}. Graylog creates every installed stream paused, and until it runs no message lands in it, so a pipeline or alert tied only to that stream does nothing.",
        "a_host": "Change this stream rule to match your own hosts: “{s}”, field {f}, value {v}. It still holds the values of the site this pack was built on, so nothing of yours would match.",
        "a_default": "These pipelines are connected to the default stream, where every message starts, so they run whatever order your message processors are in: {v}.",
        "a_removed": "If System → Configurations → Message Processors runs the Stream Rule Processor before the Pipeline Processor, and a stream with “Remove matches from Default Stream” takes these logs, the default stream no longer holds them when the pipelines run. Then connect the pipelines above to that stream as well, under System → Pipelines → Manage connections.",
        "a_order": "These pipelines are connected only to their own stream: {v}. A fresh Graylog 7 runs the Pipeline Processor before the Stream Rule Processor, and then such a pipeline never sees a message. Under System → Configurations → Message Processors, move the Stream Rule Processor above the Pipeline Processor.",
        "a_connect": "Connect these pipelines to the stream that holds these logs, under System → Pipelines → Manage connections: {v}. A pipeline with no stream processes nothing. A fresh Graylog 7 runs the Pipeline Processor before the Stream Rule Processor, and then a pipeline on your own stream never sees a message: under System → Configurations → Message Processors, move the Stream Rule Processor above the Pipeline Processor.",
        "a_alerts_quiet": "The {n} alerts have no notification: events are only written to Graylog. To be told, add one under Alerts → Event Definitions.",
        "a_alerts_notify": "This pack brings notifications. Check who they go to before relying on them: {v}.",
        "a_dash": "Open the dashboards under Dashboards: {v}.",
        "a_new": "Only messages received after this point are parsed. Graylog does not go back over what is already stored.",
        "h_verify": "Check that it works",
        "v_query": "In Search, over the last hour, run this query. Any result means the pipelines are working:",
        "v_generic": "Send a log from the device, wait a minute and open the dashboard with the time range widened.",
        "h_up": "2. Upgrade from an earlier version",
        "up_why": "Graylog cannot update an installed pack in place, and it refuses a second pipeline or rule with the same title: the whole install then fails with a bare error and creates nothing. So the earlier version comes off first, then this one goes on.",
        "up_record": "Write down what you changed in the earlier version. Uninstalling deletes everything the pack installed, changed or not: stream rules, alert thresholds and notifications, rules you edited, and the streams the pipelines are connected to (System → Pipelines → Manage connections).",
        "up_uninstall": "Under System → Content Packs, open the earlier version and click Uninstall. If it is listed more than once, uninstall each one.",
        "uninstall_list": "Before it deletes anything, Graylog lists what it will remove. If an Input you receive logs on is in that list, cancel: that Input would be deleted too. Delete the other items by hand instead, using the check below.",
        "up_check": "Check that nothing is left, and delete by hand whatever is. A pipeline or rule left behind makes the new install fail; a dashboard left behind ends up twice:",
        "up_extra": "For this pack, also:",
        "up_extractors": "If the earlier version parsed these logs with extractors (System → Inputs → Manage extractors, on the Input that receives them), delete those extractors. Otherwise every message is parsed twice.",
        "up_install": "Install this version as in “1. New install”, including what to do after installing.",
        "up_restore": "Set again what you wrote down in step 1. If the pipelines were connected to other streams, connect them again under System → Pipelines → Manage connections.",
        "up_gap": "Messages already stored are not touched. Messages received between the uninstall and the new install are stored but not parsed, so do the steps in one go.",
        "c_pipelines": "System → Pipelines → Manage pipelines: {v}",
        "c_rules_prefix": "System → Pipelines → Manage rules, search for {v}: no rule should start with it.",
        "c_rules_list": "System → Pipelines → Manage rules: {v}",
        "c_dashboards": "Dashboards: {v}",
        "c_streams": "Streams: {v}",
        "c_alerts": "Alerts → Event Definitions: {v}",
        "c_notifications": "Alerts → Notifications: {v}",
        "prefix_n": "the {n} whose names start with {p}",
        "h_rm": "3. Uninstall",
        "rm_open": "Under System → Content Packs, open the pack and click Uninstall.",
        "rm_check": "Check that nothing is left, and delete by hand whatever is:",
        "rm_delete": "To take the pack off the list too, click Delete on it. Graylog allows that only once no revision of it is installed.",
        "rm_parse": "From then on new messages are not parsed.",
        "rm_keep": "Messages already stored stay, with the fields they already have.",
        "h_notes": "Notes for this pack",
        "h_trouble": "Troubleshooting",
        "tr_all": "Every widget is 0 or empty",
        "tr_all_fix": "In this order: the stream is started; messages are arriving (Search for them with no query); the pipelines are connected to a stream those messages are in; the time range covers them. If a message has none of the expected fields, the pipelines did not run on it.",
        "tr_some": "Only some widgets are empty",
        "tr_some_fix": "Usually there are no such events in the time range. A field added by a newer rule only appears on new messages.",
        "tr_500": "Install fails with an error and nothing changes",
        "tr_500_fix": "A pipeline or rule with the same title already exists: do “2. Upgrade from an earlier version” from step 2. Also check the Graylog version above.",
    },
    "zh-TW": {
        "file": "SOP-安裝-升級-解除安裝.md",
        "rev": "修訂版 {rev}",
        "converted": "已轉換為 Graylog {v} 可用的版本。",
        "which": "請依您的情況做對應的段落：",
        "w_new": "從沒裝過：做「**1. 新安裝**」",
        "w_up": "已經裝過舊版：做「**2. 舊版升級**」",
        "w_rm": "不再使用：做「**3. 解除安裝**」",
        "h_about": "這個套件做什麼",
        "own_desc": "套件內附的說明，內容為作者原文：",
        "collect": "記錄如何送入：{v}",
        "h_inside": "會安裝哪些項目",
        "t_dashboard": "看板", "t_stream": "串流", "t_pipeline": "管線", "t_pipeline_rule": "管線規則",
        "t_event_definition": "告警（event definition）", "t_notification": "通知", "t_input": "Input",
        "t_lookup_table": "Lookup table", "t_lookup_adapter": "Lookup adapter", "t_lookup_cache": "Lookup cache",
        "t_grok_pattern": "Grok pattern",
        "tabs": "{n} 個分頁",
        "h_new": "1. 新安裝",
        "h_before": "安裝前",
        "need_version": "需要 Graylog {v} 以上。",
        "need_older": "Graylog 版本較舊時，請重新下載，並在下載視窗選擇該版本。",
        "need_plugin": "需要：{v}",
        "need_input": "這個套件不會建立 Input。請到 System → Inputs 自行建立，並把記錄來源指向它。",
        "has_input": "這個套件會建立這些 Input：{v}。請先確認連接埠沒有被占用。",
        "need_geo": "地圖與國別欄位需要 Geo-Location Processor：到 System → Configurations → Geo-Location Processor 啟用，並準備 GeoLite2-City 資料庫。",
        "need_lookup": "這些 lookup table 有用到但沒有包含在套件內：{v}。沒有它們時，由它們填入的欄位會是空的，其他功能不受影響。需要這些欄位時，請用完全相同的名稱自行建立。",
        "h_steps": "步驟",
        "s_unzip": "先解壓縮下載的檔案。Graylog 要上傳的是 .json 檔，不是 ZIP。",
        "s_upload": "到 Graylog 的 System → Content Packs，按 Upload，選擇 {file}。",
        "s_install": "在清單開啟「{name}」，按 Install。",
        "s_params": "填入 Graylog 要求的參數：{v}。",
        "h_after": "安裝後要做的事",
        "a_start": "到 Streams 按 Start Stream 啟動串流：{v}。Graylog 建立的串流都是暫停狀態，啟動前不會有記錄進入這個串流，只綁在這個串流上的管線和告警都不會運作。",
        "a_host": "把這條串流規則改成您自己的主機：「{s}」，欄位 {f}，值 {v}。這裡還是打包環境的值，不修改就比對不到您的記錄。",
        "a_default": "這些管線已接到預設串流，每筆記錄一開始都在預設串流，所以不論訊息處理順序如何，裝好就會運作：{v}。",
        "a_removed": "如果 System → Configurations → Message Processors 把 Stream Rule Processor 排在 Pipeline Processor 前面，而且有勾選「Remove matches from Default Stream」的串流收走了這些記錄，管線執行時預設串流裡已經沒有它們。這時請到 System → Pipelines → Manage connections，把上面的管線也接到那個串流。",
        "a_order": "這些管線只接在自己的串流上：{v}。全新安裝的 Graylog 7 預設先執行 Pipeline Processor、後執行 Stream Rule Processor，這樣的管線永遠收不到記錄。請到 System → Configurations → Message Processors，把 Stream Rule Processor 移到 Pipeline Processor 前面。",
        "a_connect": "到 System → Pipelines → Manage connections，把這些管線接到存放這類記錄的串流：{v}。沒有接串流的管線不會處理任何記錄。全新安裝的 Graylog 7 預設先執行 Pipeline Processor、後執行 Stream Rule Processor，這時接在自建串流上的管線收不到記錄：請到 System → Configurations → Message Processors，把 Stream Rule Processor 移到 Pipeline Processor 前面。",
        "a_alerts_quiet": "這 {n} 條告警沒有設定通知，事件只會寫進 Graylog。需要收到通知時，請到 Alerts → Event Definitions 加上。",
        "a_alerts_notify": "這個套件帶有通知。使用前請確認收件對象：{v}。",
        "a_dash": "到 Dashboards 開啟看板：{v}。",
        "a_new": "只有從現在起收到的記錄才會被解析，已存入的記錄不會回溯。",
        "h_verify": "確認是否正常",
        "v_query": "到 Search，時間範圍選最近一小時，輸入下面的查詢。有結果就表示管線正常運作：",
        "v_generic": "從設備送一筆記錄，等一分鐘，把看板的時間範圍拉大後查看。",
        "h_up": "2. 舊版升級",
        "up_why": "Graylog 無法直接更新已安裝的套件，也不接受標題相同的管線或規則：撞名時整包安裝失敗，只顯示一般錯誤，什麼都不會建立。所以要先移除舊版，再安裝這一版。",
        "up_record": "先記下您在舊版改過的設定。解除安裝會刪掉套件裝的所有項目，不管有沒有改過：串流規則、告警門檻和通知、改過的管線規則，以及管線接在哪些串流（System → Pipelines → Manage connections）。",
        "up_uninstall": "到 System → Content Packs 開啟舊版，按 Uninstall。清單裡有多筆時，每一筆都要 Uninstall。",
        "uninstall_list": "Graylog 刪除前會先列出要移除的項目。清單裡如果有您正在收記錄的 Input，請取消，否則那個 Input 也會被刪掉；改用下面的檢查清單，手動刪除其他項目。",
        "up_check": "確認沒有殘留，有就手動刪除。留下管線或規則，新版會裝不起來；留下看板，會變成兩份：",
        "up_extra": "這個套件另外要注意：",
        "up_extractors": "如果舊版是用 Extractor 解析這類記錄（在收這類記錄的 Input 上，System → Inputs → Manage extractors），請刪掉那些 Extractor，否則每筆記錄都會被解析兩次。",
        "up_install": "照「1. 新安裝」安裝這一版，包括安裝後要做的事。",
        "up_restore": "把第 1 步記下的設定改回去。原本管線接在其他串流的，到 System → Pipelines → Manage connections 重新連接。",
        "up_gap": "已存入的記錄不受影響。從解除安裝到裝好新版之間收到的記錄會存入，但不會被解析，所以請一次做完。",
        "c_pipelines": "System → Pipelines → Manage pipelines：{v}",
        "c_rules_prefix": "System → Pipelines → Manage rules，搜尋 {v}：不該有任何以它開頭的規則。",
        "c_rules_list": "System → Pipelines → Manage rules：{v}",
        "c_dashboards": "Dashboards：{v}",
        "c_streams": "Streams：{v}",
        "c_alerts": "Alerts → Event Definitions：{v}",
        "c_notifications": "Alerts → Notifications：{v}",
        "prefix_n": "名稱以 {p} 開頭的 {n} 項",
        "h_rm": "3. 解除安裝",
        "rm_open": "到 System → Content Packs 開啟套件，按 Uninstall。",
        "rm_check": "確認沒有殘留，有就手動刪除：",
        "rm_delete": "要把套件也從清單移除，對它按 Delete。要等所有修訂版都解除安裝後，Graylog 才允許刪除。",
        "rm_parse": "之後收到的記錄不再被解析。",
        "rm_keep": "已存入的記錄會保留，已有的欄位也還在。",
        "h_notes": "這個套件的注意事項",
        "h_trouble": "疑難排解",
        "tr_all": "所有 widget 都是 0 或無資料",
        "tr_all_fix": "請依序確認：串流已啟動；記錄確實有進來（到 Search 不輸入條件查詢）；管線有接到這些記錄所在的串流；時間範圍有涵蓋這些記錄。如果記錄上完全沒有預期的欄位，就是管線沒有處理到它。",
        "tr_some": "只有部分 widget 沒有資料",
        "tr_some_fix": "通常是該時段沒有這類事件。新版規則才產生的欄位，只會出現在之後收到的記錄上。",
        "tr_500": "安裝時出現錯誤，什麼都沒有建立",
        "tr_500_fix": "已存在標題相同的管線或規則：請從第 2 步開始做「2. 舊版升級」。也請確認上面寫的 Graylog 版本。",
    },
    "ja": {
        "file": "SOP-インストール-アップグレード-アンインストール.md",
        "rev": "リビジョン {rev}",
        "converted": "Graylog {v} 向けに変換済みです。",
        "which": "該当する手順を行ってください：",
        "w_new": "初めてインストールする：「**1. 新規インストール**」",
        "w_up": "以前のバージョンがインストール済み：「**2. 以前のバージョンからのアップグレード**」",
        "w_rm": "使用をやめる：「**3. アンインストール**」",
        "h_about": "このパックの内容",
        "own_desc": "パックに含まれる説明です（作者の原文のままです）：",
        "collect": "ログの送信方法：{v}",
        "h_inside": "インストールされるもの",
        "t_dashboard": "ダッシュボード", "t_stream": "ストリーム", "t_pipeline": "パイプライン", "t_pipeline_rule": "パイプラインルール",
        "t_event_definition": "アラート（event definition）", "t_notification": "通知", "t_input": "Input",
        "t_lookup_table": "Lookup table", "t_lookup_adapter": "Lookup adapter", "t_lookup_cache": "Lookup cache",
        "t_grok_pattern": "Grok pattern",
        "tabs": "{n} タブ",
        "h_new": "1. 新規インストール",
        "h_before": "インストールの前に",
        "need_version": "Graylog {v} 以降が必要です。",
        "need_older": "Graylog が古い場合は、ダウンロード画面でそのバージョンを選んでダウンロードし直してください。",
        "need_plugin": "必要なもの：{v}",
        "need_input": "このパックは Input を作成しません。System → Inputs で作成し、ログの送信先に指定してください。",
        "has_input": "このパックは次の Input を作成します：{v}。ポートが空いていることを確認してください。",
        "need_geo": "地図と国の列には Geo-Location Processor が必要です。System → Configurations → Geo-Location Processor で有効にし、GeoLite2-City データベースを用意してください。",
        "need_lookup": "次の Lookup table は使われていますが、パックには含まれていません：{v}。ない場合、それらが埋める列は空のままですが、他の機能には影響しません。必要な場合は同じ名前で作成してください。",
        "h_steps": "手順",
        "s_unzip": "ダウンロードしたファイルを解凍してください。Graylog にアップロードするのは ZIP ではなく .json ファイルです。",
        "s_upload": "Graylog の System → Content Packs で Upload をクリックし、{file} を選びます。",
        "s_install": "一覧で「{name}」を開き、Install をクリックします。",
        "s_params": "Graylog が求めるパラメーターを入力します：{v}。",
        "h_after": "インストール後の作業",
        "a_start": "Streams で Start Stream をクリックしてストリームを開始します：{v}。作成されたストリームはすべて一時停止の状態で、開始するまでメッセージは入らず、このストリームだけに結び付いたパイプラインやアラートは動作しません。",
        "a_host": "このストリームルールをお使いのホストに合わせて変更してください：「{s}」、フィールド {f}、値 {v}。パックを作成した環境の値のままなので、変更しないとログに一致しません。",
        "a_default": "次のパイプラインはデフォルトストリームに接続済みです。すべてのメッセージは最初にデフォルトストリームに入るため、メッセージプロセッサーの順序に関係なく動作します：{v}。",
        "a_removed": "System → Configurations → Message Processors で Stream Rule Processor が Pipeline Processor より前にあり、「Remove matches from Default Stream」を有効にしたストリームがこのログを受け取る場合、パイプラインの実行時にはデフォルトストリームにログが残っていません。その場合は System → Pipelines → Manage connections で、上記のパイプラインをそのストリームにも接続してください。",
        "a_order": "次のパイプラインは独自のストリームにのみ接続されています：{v}。新規インストールの Graylog 7 は Pipeline Processor を Stream Rule Processor より先に実行するため、このようなパイプラインにはメッセージが届きません。System → Configurations → Message Processors で、Stream Rule Processor を Pipeline Processor より前に移動してください。",
        "a_connect": "System → Pipelines → Manage connections で、次のパイプラインをこのログが入るストリームに接続してください：{v}。ストリームに接続していないパイプラインは何も処理しません。新規インストールの Graylog 7 は Pipeline Processor を Stream Rule Processor より先に実行するため、独自のストリームに接続したパイプラインにはメッセージが届きません。System → Configurations → Message Processors で、Stream Rule Processor を Pipeline Processor より前に移動してください。",
        "a_alerts_quiet": "この {n} 件のアラートには通知が設定されていません。イベントは Graylog に記録されるだけです。通知が必要な場合は Alerts → Event Definitions で追加してください。",
        "a_alerts_notify": "このパックには通知が含まれています。使用前に送信先を確認してください：{v}。",
        "a_dash": "Dashboards でダッシュボードを開きます：{v}。",
        "a_new": "解析されるのは、これ以降に受信したメッセージのみです。保存済みのメッセージはさかのぼって解析されません。",
        "h_verify": "動作の確認",
        "v_query": "Search で時間範囲を直近 1 時間にして、次のクエリを実行します。結果が出ればパイプラインは動作しています：",
        "v_generic": "機器からログを送信し、1 分ほど待ってから、時間範囲を広げてダッシュボードを確認してください。",
        "h_up": "2. 以前のバージョンからのアップグレード",
        "up_why": "Graylog はインストール済みのパックをそのまま更新できず、同じタイトルのパイプラインやルールも受け付けません。重複するとインストール全体が一般的なエラーで失敗し、何も作成されません。そのため、以前のバージョンを先に削除してから、このバージョンをインストールします。",
        "up_record": "以前のバージョンで変更した設定を控えておきます。アンインストールすると、変更の有無にかかわらず、パックがインストールしたものはすべて削除されます：ストリームルール、アラートのしきい値と通知、編集したパイプラインルール、パイプラインの接続先ストリーム（System → Pipelines → Manage connections）。",
        "up_uninstall": "System → Content Packs で以前のバージョンを開き、Uninstall をクリックします。一覧に複数ある場合は、それぞれアンインストールしてください。",
        "uninstall_list": "Graylog は削除の前に、削除する項目を一覧で示します。ログを受信している Input が含まれている場合はキャンセルしてください。その Input も削除されてしまいます。代わりに、下のチェックリストに沿って他の項目を手動で削除してください。",
        "up_check": "何も残っていないことを確認し、残っているものは手動で削除します。パイプラインやルールが残っていると新しいバージョンのインストールが失敗し、ダッシュボードが残っていると 2 つになります：",
        "up_extra": "このパックでは、さらに次の点に注意してください：",
        "up_extractors": "以前のバージョンがこのログを Extractor で解析していた場合（ログを受信する Input の System → Inputs → Manage extractors）、その Extractor を削除してください。削除しないと、すべてのメッセージが 2 回解析されます。",
        "up_install": "「1. 新規インストール」のとおりにこのバージョンをインストールします。インストール後の作業も含みます。",
        "up_restore": "手順 1 で控えた設定を元に戻します。パイプラインを他のストリームに接続していた場合は、System → Pipelines → Manage connections で接続し直してください。",
        "up_gap": "保存済みのメッセージには影響しません。アンインストールから新しいバージョンのインストールまでに受信したメッセージは保存されますが、解析されません。手順は続けて行ってください。",
        "c_pipelines": "System → Pipelines → Manage pipelines：{v}",
        "c_rules_prefix": "System → Pipelines → Manage rules で {v} を検索し、これで始まるルールがないこと。",
        "c_rules_list": "System → Pipelines → Manage rules：{v}",
        "c_dashboards": "Dashboards：{v}",
        "c_streams": "Streams：{v}",
        "c_alerts": "Alerts → Event Definitions：{v}",
        "c_notifications": "Alerts → Notifications：{v}",
        "prefix_n": "名前が {p} で始まる {n} 件",
        "h_rm": "3. アンインストール",
        "rm_open": "System → Content Packs でパックを開き、Uninstall をクリックします。",
        "rm_check": "何も残っていないことを確認し、残っているものは手動で削除します：",
        "rm_delete": "パックを一覧からも削除するには、Delete をクリックします。Graylog では、どのリビジョンもインストールされていない場合にのみ削除できます。",
        "rm_parse": "これ以降に受信したメッセージは解析されません。",
        "rm_keep": "保存済みのメッセージは、既に付いているフィールドとともに残ります。",
        "h_notes": "このパックの注意事項",
        "h_trouble": "トラブルシューティング",
        "tr_all": "すべてのウィジェットが 0 または空です",
        "tr_all_fix": "次の順に確認してください：ストリームが開始されていること、メッセージが届いていること（Search を条件なしで実行）、そのメッセージが入るストリームにパイプラインが接続されていること、時間範囲に含まれていること。メッセージに想定のフィールドがまったくない場合は、パイプラインが処理していません。",
        "tr_some": "一部のウィジェットだけが空です",
        "tr_some_fix": "多くの場合、その時間範囲に該当するイベントがありません。新しいルールで追加されたフィールドは、以降に受信したメッセージにのみ付きます。",
        "tr_500": "インストールがエラーになり、何も作成されません",
        "tr_500_fix": "同じタイトルのパイプラインまたはルールがすでに存在します。「2. 以前のバージョンからのアップグレード」を手順 2 から行ってください。上記の Graylog のバージョンも確認してください。",
    },
}

_LIST_MAX = 5
_MD_SPECIAL = re.compile(r"([\\`*_\[\]<>#|~!])")


def normalize_lang(lang: Any) -> str:
    return lang if lang in LANGS else "en"


def pack_filename(pack: dict) -> str:
    name = re.sub(r"[^\w.-]+", "_", str(pack.get("name") or "pack"))
    return f"{name}-r{pack.get('rev')}.json"


def md(s: Any) -> str:
    """Pack text as plain Markdown text: one line, every markup character escaped."""
    return _MD_SPECIAL.sub(r"\\\1", " ".join(str(s).split()))


def ours(s: Any) -> str:
    """Text from the library's notes, written by us: only what could open raw HTML is escaped,
    so it stays readable in a plain text editor. A lone `*` or an `_` inside a word is no markup."""
    return re.sub(r"([<>])", r"\\\1", " ".join(str(s).split()))


def code(s: Any) -> str:
    """Pack text as a code span; a span shows its content literally, markup included."""
    s = " ".join(str(s).split())
    fence = "`" * (max((len(r) for r in re.findall(r"`+", s)), default=0) + 1)
    pad = " " if s.startswith("`") or s.endswith("`") else ""
    return f"{fence}{pad}{s}{pad}{fence}"


def block(s: Any) -> str:
    """Pack text kept as written, in a fence longer than any it contains."""
    s = str(s)
    fence = "`" * max(3, max((len(r) for r in re.findall(r"`{3,}", s)), default=0) + 1)
    return f"{fence}text\n{s}\n{fence}"


def rule_prefix(titles: list[str]) -> str:
    """What every rule title starts with, cut back to a separator, so one search finds them all."""
    if len(titles) < 2:
        return ""
    pre = os.path.commonprefix(titles)
    cut = max(pre.rfind(c) for c in "-_ ")
    pre = pre[:cut + 1] if cut >= 0 else ""
    return pre if len(pre.strip("-_ ")) >= 2 else ""


def _own_stream_only(pipelines: list) -> list[str]:
    """Pipelines connected to streams but not to the default one. Measured on a fresh Graylog
    7.1.9: its default order runs the Pipeline Processor before the Stream Rule Processor, so
    these never see a message until that order is changed."""
    out = []
    for e in pipelines:
        conn = [str(val(x)) for x in (e.get("data") or {}).get("connected_streams") or []]
        if conn and DEFAULT_STREAM_ID not in conn:
            out.append(_title(e))
    return out


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
        "own_stream_only": _own_stream_only(of("pipeline")),
        "lookups": a["lookup_tables_used"], "dashboards": dashboards,
        "version": max(versions + ([needed] if needed else []), key=version_key, default=""),
        "plugins": sorted(plugins), "inputs": [_title(e) for e in of("input")],
        "notifications": [_title(e) for e in of("notification")], "alert_count": len(alerts),
        "alerts_notify": sum(1 for e in alerts if (e.get("data") or {}).get("notifications")),
        "alerts": [_title(e) for e in alerts],
        "pipelines": [_title(e) for e in of("pipeline")],
        "rules": sorted(_title(e) for e in of("pipeline_rule")),
        "parameters": [str(p.get("name")) for p in pack.get("parameters") or []],
        "geo": any(_GEO.search(json.dumps(e.get("data") or {}, ensure_ascii=False)) for e in of("dashboard")),
    }


def render(pack: dict, lang: str, notes: dict | None = None, target_version: str = "") -> str:
    """notes: this pack's entry from the library's translated notes, when it has one."""
    lang = normalize_lang(lang)
    t, f, notes = _T[lang], facts(pack), notes or {}
    name = str(pack.get("name") or "")
    sep = "" if lang != "en" else " "

    def tx(key: str, **kw) -> str:
        """A template of ours with its values already made safe by the caller."""
        out = t[key]
        for k, v in kw.items():
            out = out.replace("{" + k + "}", v)
        return out

    def codes(items) -> str:
        return ("、" if lang != "en" else ", ").join(code(i) for i in items)

    def localized(key: str) -> Any:
        return (notes.get(key) or {}).get(lang)

    def ol(items, indent="") -> list[str]:
        return [f"{indent}{i}. {x}" for i, x in enumerate(items, 1)]

    def ul(items, indent="") -> list[str]:
        return [f"{indent}- {x}" for x in items]

    out = [f"# {md(name)}", ""]
    sub = [tx("rev", rev=md(pack.get("rev")))]
    if pack.get("vendor"):
        sub.append(md(pack["vendor"]))
    out += [" · ".join(sub), ""]
    if target_version:
        out += [tx("converted", v=md(target_version)), ""]
    out += [tx("which"), ""] + ul([tx("w_new"), tx("w_up"), tx("w_rm")]) + [""]

    out += [f"## {tx('h_about')}", ""]
    # An untranslated description is labelled as such; it is never passed off as this language.
    summary = localized("summary") or (str(pack.get("summary") or "") if lang == "zh-TW" and notes else "")
    if summary:
        out += [ours(summary) if localized("summary") else md(summary), ""]
    if localized("collect"):
        out += [tx("collect", v=ours(localized("collect"))), ""]
    if not notes:
        if pack.get("summary"):
            out += [md(pack["summary"]), ""]
        if pack.get("description"):
            out += [tx("own_desc"), "", block(pack["description"]), ""]

    out += [f"## {tx('h_inside')}", ""]
    others = sorted(k for k in f["counts"] if k not in _TYPE_ORDER)
    colon = "：" if lang != "en" else ": "
    left, right = (" (", ")") if lang == "en" else ("（", "）")
    for k in list(_TYPE_ORDER) + others:
        if f["counts"].get(k):
            label = tx("t_" + k) if "t_" + k in t else md(k)
            out.append(f"- {label}{colon}{f['counts'][k]}")
            if k == "dashboard":
                out += [f"   - {code(d['title'])}{left}{tx('tabs', n=str(d['tabs']))}{right}" for d in f["dashboards"]]
    out.append("")

    # ---- 1. New install
    out += [f"## {tx('h_new')}", "", f"### {tx('h_before')}", ""]
    before = []
    # A converted file was only tried on its own version, so it does not promise "or newer".
    if f["version"] and not target_version:
        before.append(tx("need_version", v=md(f["version"])) + sep + tx("need_older"))
    if f["plugins"]:
        before.append(tx("need_plugin", v=codes(f["plugins"])))
    if f["inputs"]:
        before.append(tx("has_input", v=codes(f["inputs"])))
    elif not notes.get("no_input"):
        before.append(tx("need_input"))
    if f["geo"]:
        before.append(tx("need_geo"))
    if f["lookups"]:
        before.append(tx("need_lookup", v=codes(f["lookups"])))
    out += ul(before) + [""]

    steps = [tx("s_unzip"), tx("s_upload", file=code(pack_filename(pack))), tx("s_install", name=md(name))]
    if f["parameters"]:
        steps.append(tx("s_params", v=codes(f["parameters"])))
    out += [f"### {tx('h_steps')}", ""] + ol(steps) + [""]

    after = []
    if f["streams"]:
        after.append(tx("a_start", v=codes(f["streams"])))
    for r in f["host_rules"]:
        after.append(tx("a_host", s=md(r["stream"]), f=code(r["field"]), v=code(r["value"])))
    if f["default_pipelines"]:
        after.append(tx("a_default", v=codes(f["default_pipelines"])))
        after.append(tx("a_removed"))
    if f["own_stream_only"]:
        after.append(tx("a_order", v=codes(f["own_stream_only"])))
    if f["unconnected"]:
        after.append(tx("a_connect", v=codes(f["unconnected"])))
    if f["notifications"]:
        after.append(tx("a_alerts_notify", v=codes(f["notifications"])))
    if f["alert_count"] and not f["alerts_notify"]:
        after.append(tx("a_alerts_quiet", n=str(f["alert_count"])))
    if f["dashboards"]:
        after.append(tx("a_dash", v=codes(d["title"] for d in f["dashboards"])))
    if f["pipelines"]:
        after.append(tx("a_new"))
    if after:
        out += [f"### {tx('h_after')}", ""] + ol(after) + [""]

    out += [f"### {tx('h_verify')}", ""]
    if notes.get("verify"):
        out += [tx("v_query"), "", block(notes["verify"]), ""]
    else:
        out += [tx("v_generic"), ""]

    # ---- What an upgrade and an uninstall must find: everything this pack installs by title.
    def names(titles: list[str]) -> str:
        """A short list in full; a long one by what its names start with, when they share that."""
        pre = rule_prefix(sorted(titles)) if len(titles) > _LIST_MAX else ""
        return tx("prefix_n", p=code(pre), n=str(len(titles))) if pre else codes(titles)

    leftovers = []
    if f["pipelines"]:
        leftovers.append(tx("c_pipelines", v=names(f["pipelines"])))
    if f["rules"]:
        pre = rule_prefix(f["rules"])
        leftovers.append(tx("c_rules_prefix", v=code(pre)) if pre else tx("c_rules_list", v=codes(f["rules"])))
    if f["dashboards"]:
        leftovers.append(tx("c_dashboards", v=names([d["title"] for d in f["dashboards"]])))
    if f["streams"]:
        leftovers.append(tx("c_streams", v=names(f["streams"])))
    if f["alerts"]:
        leftovers.append(tx("c_alerts", v=names(f["alerts"])))
    if f["notifications"]:
        leftovers.append(tx("c_notifications", v=names(f["notifications"])))

    # ---- 2. Upgrade
    extra = localized("upgrade") or []
    out += [f"## {tx('h_up')}", "", tx("up_why"), ""]
    if extra:
        out += [tx("up_extra"), ""] + ul([ours(x) for x in extra]) + [""]
    out += [f"1. {tx('up_record')}",
            f"2. {tx('up_uninstall')}{sep}{tx('uninstall_list')}",
            f"3. {tx('up_check')}"] + ul(leftovers, "   ")
    n = 4
    if f["pipelines"]:
        out.append(f"{n}. {tx('up_extractors')}")
        n += 1
    out += [f"{n}. {tx('up_install')}", f"{n + 1}. {tx('up_restore')}", "", tx("up_gap"), ""]

    # ---- 3. Uninstall
    out += [f"## {tx('h_rm')}", "", f"1. {tx('rm_open')}{sep}{tx('uninstall_list')}",
            f"2. {tx('rm_check')}"] + ul(leftovers, "   ") + [f"3. {tx('rm_delete')}", ""]
    result = ([tx("rm_parse")] if f["pipelines"] else []) + [tx("rm_keep")]
    out += [sep.join(result), ""]

    note_list = localized("notes") or []
    if note_list:
        out += [f"## {tx('h_notes')}", ""] + ul([ours(x) for x in note_list]) + [""]

    out += [f"## {tx('h_trouble')}", ""]
    for sym, fix in (("tr_all", "tr_all_fix"), ("tr_some", "tr_some_fix"), ("tr_500", "tr_500_fix")):
        out.append(f"- **{tx(sym)}**{colon}{tx(fix)}")
    return "\n".join(out) + "\n"


def bundle(pack: dict, lang: str, notes: dict | None = None, target_version: str = "") -> tuple[bytes, str]:
    """(ZIP bytes, its file name): the pack as it would be uploaded, and the SOP beside it."""
    lang = normalize_lang(lang)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(pack_filename(pack), json.dumps(pack, ensure_ascii=False, indent=2))
        z.writestr(_T[lang]["file"], render(pack, lang, notes, target_version))
    stem = pack_filename(pack)[:-len(".json")]
    if target_version:
        stem += f"-graylog{target_version}"
    return buf.getvalue(), f"{stem}-{lang}.zip"
