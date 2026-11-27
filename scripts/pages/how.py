"""how.html: how jt-glogarch works inside (like jt-waf-mgr's how.html)."""
from lib import D, GH, card, card_list, dialogs, footer, header, page, reg, section, steps, t, ticks, tk, PREFIX


def nav():
    items = [("#arch", "hn_arch", ("Architecture", "架構", "構成")), ("#export", "hn_export", ("Export", "匯出", "エクスポート")),
             ("#guard", "hn_guard", ("Backpressure", "背壓保護", "負荷制御")), ("#import", "hn_import", ("Import", "匯入", "インポート")),
             ("#integrity", "hn_integrity", ("Integrity", "完整性", "完全性")), ("#datanode", "hn_dn", ("Data Node", "Data Node", "Data Node")),
             ("#security", "hn_sec", ("Security", "資安分析", "セキュリティ")), ("#ai", "hn_ai", ("AI chat", "智慧問答", "AI チャット")),
             ("#upgrade", "hn_up", ("Upgrades", "升級", "アップグレード")), ("#bounds", "hn_bounds", ("Boundaries", "邊界", "境界"))]
    out = []
    for href, k, (en, zh, ja) in items:
        reg(k, en, zh, ja)
        out.append(f'<a href="{href}" data-t="{k}">{en}</a>')
    return "".join(out)


def hero():
    chips = []
    for sid, k in (("arch", "hn_arch"), ("export", "hn_export"), ("guard", "hn_guard"), ("import", "hn_import"), ("integrity", "hn_integrity"),
                   ("datanode", "hn_dn"), ("security", "hn_sec"), ("ai", "hn_ai"), ("bounds", "hn_bounds")):
        chips.append(f'<a class="chip" href="#{sid}">{tk(k)}</a>')
    return f'''<div class="hero small"><div class="wrap one">
  <div>
    <h1>{t("How jt-glogarch works", "jt-glogarch 運作架構", "jt-glogarch の仕組み")}</h1>
    {t("Which parts it is made of, where each one runs, what it reads and writes, and the exact path a record takes out of Graylog and back. Everything here describes what the code actually does.",
       "由哪些部分組成、各自在哪裡執行、讀寫哪些資料，以及一筆記錄離開 Graylog 再回去的完整路徑。這裡寫的都是程式實際的行為。",
       "どんな部品でできているか、それぞれどこで動き、何を読み書きするか、そして 1 件のレコードが Graylog から出て戻るまでの正確な経路。ここに書くのはコードが実際に行うことです。", tag="p", cls="lead")}
    <div class="btns"><a class="btn primary" href="index.html" id="home-btn">← {tk("nav_home")}</a><a class="btn" href="{GH}">GitHub</a></div>
    <div class="chips">{"".join(chips)}</div>
  </div>
</div></div>
'''


def arch():
    L = lambda *a: a  # noqa: E731
    d = D(1200, 720, L("System architecture", "系統架構", "システム構成"))
    d.group(20, 118, 870, 440, L("jt-glogarch.service: one process, user jt-glogarch", "jt-glogarch.service：單一程序，以 jt-glogarch 使用者執行", "jt-glogarch.service：1 つのプロセス、jt-glogarch ユーザー"))
    # callers
    d.box(40, 20, 180, 60, "ext", L("Administrators", "管理者", "管理者"), L("browser, Graylog account", "瀏覽器，Graylog 帳號", "ブラウザ、Graylog アカウント"))
    d.box(680, 20, 190, 60, "ext", L("External AI", "外部 AI", "外部の AI"), L("MCP client", "MCP 用戶端", "MCP クライアント"))
    # row A: entry points
    d.box(40, 150, 180, 62, "core", L("Web UI and API", "網頁介面與 API", "Web 画面と API"), mono="FastAPI · HTTPS 8990")
    d.box(250, 150, 180, 62, "core", L("Scheduler", "排程器", "スケジューラ"), mono="APScheduler · cron")
    d.box(460, 150, 180, 62, "core", L("Audit listener", "稽核接收器", "監査リスナー"), mono="syslog · UDP 8991")
    d.box(680, 150, 190, 62, "core", L("MCP endpoint", "MCP 端點", "MCP エンドポイント"), mono="/mcp")
    # row B: workers (threads)
    for i, (title, sub) in enumerate([
        (L("Verify and cleanup", "驗證與清理", "検証とクリーンアップ"), L("parallel SHA256, retention", "平行 SHA256、保留期", "並列 SHA256、保持期間")),
        (L("Security runner", "資安分析", "セキュリティ分析"), L("detectors · Sigma", "偵測項目・Sigma", "検知・Sigma")),
        (L("AI chat", "智慧問答", "AI チャット"), L("model rounds · tools", "模型回合・工具", "モデルの往復・ツール")),
        (L("Importer", "匯入", "インポート"), L("preflight · GELF · Bulk", "預檢・GELF・Bulk", "事前チェック・GELF・Bulk")),
        (L("Exporter", "匯出", "エクスポート"), L("API · OpenSearch Direct", "API・OpenSearch Direct", "API・OpenSearch Direct"))]):
        d.box(40 + i * 170, 270, 150, 62, "svc", title, sub)
    # row C: helpers
    for i, (title, sub) in enumerate([
        (L("Health guard", "健康防護", "ヘルスガード"), L("pace, pause, stop once", "放慢、暫停、停止一次", "減速・一時停止・1 回停止")),
        (L("PDF reports", "PDF 報表", "PDF レポート"), L("headless Chromium", "無頭 Chromium", "ヘッドレス Chromium")),
        (L("Data Node certificate", "Data Node 憑證", "Data Node 証明書"), L("issue, renew, probe", "申請、更新、探測", "発行・更新・確認")),
        (L("Threat intel and SigmaHQ", "威脅情資與 SigmaHQ", "脅威情報と SigmaHQ"), L("opt-in downloads", "選用下載", "任意のダウンロード")),
        (L("Notifier", "通知", "通知"), L("7 channels, 3 languages", "7 種管道、3 種語言", "7 チャネル・3 言語"))]):
        d.box(40 + i * 170, 400, 150, 58, "svc", title, sub)
    # files
    d.box(40, 618, 260, 60, "file", L("SQLite database", "SQLite 資料庫", "SQLite データベース"), mono="jt-glogarch.db (WAL)")
    d.box(330, 618, 260, 60, "file", L("Archive files", "歸檔檔案", "アーカイブファイル"), mono="/data/graylog-archives/*.json.gz")
    d.box(620, 618, 260, 60, "file", L("Settings and certificates", "設定與憑證", "設定と証明書"), mono="config.yaml · certs/")
    # outside
    d.box(940, 20, 240, 58, "ext", L("Graylog users", "Graylog 使用者", "Graylog ユーザー"), L("browser · API tokens", "瀏覽器・API token", "ブラウザ・API トークン"))
    d.box(940, 122, 240, 58, "ext", L("nginx", "nginx", "nginx"), L("in front of Graylog", "擋在 Graylog 前面", "Graylog の前段"))
    d.box(940, 224, 240, 58, "ext", L("Graylog", "Graylog", "Graylog"), L("REST API · GELF TCP input", "REST API・GELF TCP input", "REST API・GELF TCP 入力"))
    d.box(940, 326, 240, 58, "ext", L("OpenSearch or Data Node", "OpenSearch 或 Data Node", "OpenSearch または Data Node"), L("scan per shard · _bulk", "逐分片掃描・_bulk", "シャードごとの走査・_bulk"))
    d.box(940, 428, 240, 58, "ext", L("LLM servers", "LLM 伺服器", "LLM サーバー"), L("OpenAI-compatible · Claude API", "OpenAI 相容・Claude API", "OpenAI 互換・Claude API"))
    d.box(940, 530, 240, 58, "ext", L("Notification channels", "通知管道", "通知チャネル"), L("Telegram · Slack · e-mail …", "Telegram・Slack・Email…", "Telegram・Slack・メール…"))
    d.box(940, 632, 240, 58, "ext", L("Public feeds", "公開來源", "公開フィード"), L("SigmaHQ · Spamhaus · Tor · abuse.ch", "SigmaHQ・Spamhaus・Tor・abuse.ch", "SigmaHQ・Spamhaus・Tor・abuse.ch"), dash=True)
    # edges
    d.edge("M130,80 L130,150", "main", L("HTTPS 8990", "HTTPS 8990", "HTTPS 8990"), 136, 120, anchor="start")
    d.edge("M775,80 L775,150", "", L("Graylog token", "Graylog token", "Graylog トークン"), 781, 120, anchor="start")
    d.edge("M1060,78 L1060,122", "main")
    d.edge("M1060,180 L1060,224", "main", L("proxied", "轉送", "転送"), 1066, 207, anchor="start")
    d.edge("M940,151 L910,151 L910,134 L550,134 L550,150", "", L("access log by syslog", "以 syslog 送出存取記錄", "syslog でアクセスログ"), 640, 128, w=170)
    for x in (285, 455, 625):
        d.edge(f"M{x},270 L{x},250 L{x + 170},250", "nohead")
    d.edge("M795,270 L795,250 L940,250", "main")
    d.text(905, 244, L("REST API · GELF", "REST API・GELF", "REST API・GELF"), "el", anchor="end", w=120, into=d.labels)
    d.edge("M625,332 L625,352 L940,352", "main")
    d.edge("M795,332 L795,352", "main nohead")
    d.text(905, 346, L("scan · _bulk", "掃描・_bulk", "走査・_bulk"), "el", anchor="end", w=100, into=d.labels)
    d.edge("M455,332 L455,376 L920,376 L920,456 L940,456", "", L("chat completions", "對話請求", "チャット要求"), 700, 370, w=150)
    d.edge("M870,428 L906,428 L906,558 L940,558", "", L("send", "送出", "送信"), 900, 530, anchor="end")
    d.edge("M625,458 L625,500 L924,500 L924,660 L940,660", "dash", L("download, when enabled", "下載（啟用時）", "ダウンロード（有効時）"), 760, 494, w=160)
    for x in (170, 460, 750):
        d.edge(f"M{x},558 L{x},618", "data", both=True)
    d.text(466, 594, L("read / write", "讀取/寫入", "読み書き"), "el", anchor="start", into=d.labels)
    legend = [("l main", t("records and requests", "記錄與請求", "レコードと要求")), ("l data", t("control and files", "控制與檔案", "制御とファイル")),
              ("l dash", t("optional", "選用", "任意")), ("k-core", t("entry points", "進入點", "入口")), ("k-svc", t("workers (threads)", "工作執行緒", "ワーカー（スレッド）")),
              ("k-file", t("on disk", "磁碟上", "ディスク上")), ("k-ext", t("outside jt-glogarch", "jt-glogarch 以外", "jt-glogarch の外"))]
    fig = d.render("fig-arch", legend)
    cards = [
        card_list("◉", t("One service", "單一服務", "1 つのサービス"), "<code>jt-glogarch.service</code>",
                  [t("Web UI, API, scheduler, audit listener and MCP share one process", "網頁介面、API、排程器、稽核接收器與 MCP 在同一個程序",
                     "Web 画面・API・スケジューラ・監査リスナー・MCP は 1 つのプロセス"),
                   t("Exports, imports and verifies run in worker threads so the web UI stays responsive", "匯出、匯入與驗證在工作執行緒中執行，網頁介面不會卡住",
                     "エクスポート・インポート・検証はワーカースレッドで動き、Web 画面は止まりません"),
                   t("Only one export per Graylog server at a time; a second request waits or is refused", "每台 Graylog 同一時間只跑一個匯出；第二個請求會等待或被拒絕",
                     "Graylog サーバーごとにエクスポートは同時に 1 つ。2 つ目は待つか拒否されます")]),
        card_list("⚿", t("User and files", "使用者與檔案", "ユーザーとファイル"), "<code>jt-glogarch</code>",
                  [t("Runs as its own system user, in the <code>systemd-journal</code> group so the System Logs page can read the journal",
                     "以專屬系統使用者執行，並加入 <code>systemd-journal</code> 群組以便「系統記錄」頁讀取 journal",
                     "専用のシステムユーザーで動き、「システムログ」画面が journal を読めるよう <code>systemd-journal</code> グループに属します"),
                   t("Owns <code>/opt/jt-glogarch</code> (settings, database, certificates) and the archive path", "擁有 <code>/opt/jt-glogarch</code>（設定、資料庫、憑證）與歸檔路徑",
                     "<code>/opt/jt-glogarch</code>（設定・DB・証明書）とアーカイブ先を所有します"),
                   t("Data Node keys: 0600 files in a 0700 folder, never returned by the API", "Data Node 金鑰：0700 資料夾內的 0600 檔案，API 不會回傳",
                     "Data Node の鍵：0700 のフォルダ内の 0600 ファイル。API は返しません")]),
        card_list("◷", t("Internal jobs", "內部排程", "内部ジョブ"), t("besides your own schedules", "您自己的排程以外", "ご自身のスケジュール以外"),
                  [t("Daily disk outlook check; Data Node certificate renewal at 04:45", "每日磁碟預估檢查；每日 04:45 更新 Data Node 憑證",
                     "毎日のディスク見通し確認、04:45 の Data Node 証明書更新"),
                   t("Security analysis, weekly summary, threat intelligence and SigmaHQ refresh, only when enabled", "資安分析、每週摘要、威脅情資與 SigmaHQ 更新（僅在啟用時）",
                     "セキュリティ分析・週次サマリー・脅威情報と SigmaHQ の更新（有効時のみ）"),
                   t("Registered at start and again whenever their settings are saved", "服務啟動時註冊，設定儲存後也會重新註冊",
                     "起動時と、設定を保存するたびに登録し直します")]),
    ]
    return section("arch", t("System architecture", "系統架構", "システム構成"),
                   t("One Python service next to Graylog. It reads Graylog through its API and OpenSearch, keeps its own SQLite database and archive files, and writes to Graylog only when you ask it to.",
                     "Graylog 旁邊的一個 Python 服務：透過 API 與 OpenSearch 讀取 Graylog，自己保存 SQLite 資料庫與歸檔檔案，只有在您要求時才會寫入 Graylog。",
                     "Graylog の横で動く 1 つの Python サービスです。API と OpenSearch で Graylog を読み、独自の SQLite DB とアーカイブファイルを持ち、頼まれたときだけ Graylog に書き込みます。"),
                   fig + f'<h3>{t("Process, user and files", "程序、使用者與檔案", "プロセス・ユーザー・ファイル")}</h3><div class="grid three">{"".join(cards)}</div>')


def export():
    api = steps([
        (t("Plan", "規劃", "計画"), t("From the resume point, minus covered time; holes from earlier runs (last 7 days) first.", "從接續點開始，扣掉已涵蓋的時間；先處理先前留下的空缺（最近 7 天）。", "再開点から、取得済みの時間を除く。以前の欠け（直近 7 日）を先に。")),
        (t("Chunk", "分段", "分割"), t("One hour per chunk, so a failure costs at most one hour and archives line up.", "每段一小時，失敗最多損失一小時，歸檔也能對齊。", "1 時間ごとに分け、失敗しても失うのは最大 1 時間、アーカイブも揃います。")),
        (t("Page", "分頁", "ページ"), t("1,000 messages per page; past 10,000 the time window moves forward instead of the offset.", "每頁 1,000 筆；超過 10,000 筆時改為推進時間視窗，而不是加大 offset。", "1 ページ 1,000 件。10,000 件を超えたら offset ではなく時間窓を進めます。")),
        (t("Pace", "調速", "ペース"), t("Graylog keeps every search result for 5 minutes; requests slow down as heap after GC rises.", "Graylog 會把每次搜尋結果保留 5 分鐘；GC 後的 heap 越高，請求越慢。", "Graylog は検索結果を 5 分保持するので、GC 後のヒープが上がるほど要求を遅くします。")),
        (t("Overflow", "溢出", "あふれ"), t("More than 10,000 messages in one millisecond: what was read is kept, the millisecond recorded for OpenSearch Direct.", "同一毫秒超過 10,000 筆：已讀到的保留，該毫秒記下來交給 OpenSearch Direct。", "1 ミリ秒に 10,000 件超：読めた分は残し、そのミリ秒を OpenSearch Direct 用に記録します。")),
        (t("Record", "登錄", "記録"), t("The hour is sealed and recorded; a cancel discards only the unfinished hour.", "封存並登錄這一小時；取消只丟棄未完成的那一小時。", "その 1 時間を封印して記録。キャンセルは未完了の 1 時間だけを捨てます。")),
    ])
    os_ = steps([
        (t("Indices", "索引", "インデックス"), t("Indices whose time range meets the window; the active write index is skipped until it rotates.", "時間範圍與視窗重疊的索引；正在寫入的索引等它輪替後再處理。", "時間範囲が窓と重なるインデックス。書き込み中のものはローテーション後に。")),
        (t("Exclude", "排除", "除外"), t("Covered time goes into the query as <code>must_not</code>, so archived records are never fetched.", "已涵蓋的時間以 <code>must_not</code> 放進查詢，已歸檔的記錄不會再抓。", "取得済みの時間をクエリの <code>must_not</code> に入れ、アーカイブ済みを取得しません。")),
        (t("Count", "計數", "件数"), t("<code>_count</code> first, so the scan can prove it returned every document.", "先 <code>_count</code>，掃描結束時能證明每一筆都拿到了。", "先に <code>_count</code> を取り、走査がすべての文書を返したことを証明します。")),
        (t("Scan", "掃描", "走査"), t("One <code>search_after</code> cursor per shard, pinned to the primary, merged back into time order.", "每個分片一個 <code>search_after</code> 游標，固定讀主分片，再合併回時間順序。", "シャードごとに <code>search_after</code> カーソル（プライマリ固定）を持ち、時間順に統合します。")),
        (t("Write", "寫入", "書き込み"), t("An hour closes the moment a timestamp crosses it, and is recorded at once.", "時間戳一跨過整點，這一小時立即結束並登錄。", "タイムスタンプが時を越えた瞬間にその 1 時間を閉じ、すぐ記録します。")),
        (t("Refill", "補齊", "補完"), t("API overflow milliseconds are fetched, minus the IDs the API archive already holds.", "API 模式記下的溢出毫秒在這裡補抓，並排除 API 歸檔已有的 ID。", "API で記録したあふれのミリ秒を、API アーカイブにある ID を除いて取得します。")),
    ])
    rules = ticks([
        t("One rule decides what is covered, used both in the query and in the per-hour skip: only archives that hold all data for their range count",
          "「是否已涵蓋」只有一條規則，同時用在查詢與逐小時略過：只有包含該範圍全部資料的歸檔才算數",
          "「取得済みか」の規則は 1 つで、クエリと時間ごとのスキップの両方に使います。範囲のデータをすべて持つアーカイブだけが数えられます"),
        t("A stream-filtered API archive or a sister index holding a slice of the hour never hides missing data",
          "篩選了串流的 API 歸檔、或只含該小時一部分的同系列索引，都不會遮住缺少的資料",
          "ストリームで絞った API アーカイブや、その時間の一部しか持たない兄弟インデックスが、欠けを隠すことはありません"),
        t("Progress counts written records, so a scan that fetches and discards would show as stuck — the rule above is why it never does",
          "進度只算寫入的筆數，抓了又丟掉的掃描看起來會像卡住——上面那條規則就是讓它不會發生",
          "進捗は書き込んだ件数で数えるため、取得して捨てる走査は止まって見えます。上の規則がそれを防ぎます"),
    ])
    body = (f'<div class="two top steps-pair"><div><h3>{t("Graylog API mode", "Graylog API 模式", "Graylog API モード")}</h3>{api}</div>'
            f'<div><h3>{t("OpenSearch Direct mode", "OpenSearch Direct 模式", "OpenSearch Direct モード")}</h3>{os_}</div></div>'
            f'<div class="reccard"><h3>{t("Deduplication: one rule", "重複資料刪除：只有一條規則", "重複排除：規則は 1 つ")}</h3>{rules}</div>')
    return section("export", t("Export", "匯出", "エクスポート"),
                   t("Two readers, one writer: both modes stream into hourly <code>.json.gz</code> files and share the same coverage rule, so they can be switched at any time.",
                     "兩種讀取、同一個寫入：兩種模式都串流寫成每小時的 <code>.json.gz</code>，並共用同一條涵蓋規則，可以隨時切換。",
                     "読み手は 2 つ、書き手は 1 つ。どちらのモードも 1 時間ごとの <code>.json.gz</code> に逐次書き、同じ範囲の規則を共有するので、いつでも切り替えられます。"),
                   body, alt=True)


def guard():
    st = steps([
        (t("Sample", "取樣", "取得"), t("Graylog's metrics about every 15 seconds, on a fixed cadence independent of chunk size.", "約每 15 秒讀一次 Graylog 指標，固定節奏，與分段大小無關。", "約 15 秒ごとに Graylog の指標を読みます（チャンクの大きさに関係なく一定）。")),
        (t("Heap", "Heap", "ヒープ"), t("Heap after garbage collection, full GCs and GC time — not the raw used/max, which counts garbage.", "看 GC 後的 heap、Full GC 與 GC 耗時，而不是包含垃圾物件的瞬間使用率。", "GC 後のヒープ・フル GC・GC 時間を見ます。ゴミを含む使用率そのものではありません。")),
        (t("Journal", "Journal", "ジャーナル"), t("Uncommitted journal entries and the input, process and output buffers, on a sustained rise.", "未提交的 journal 筆數與 input/process/output buffer 持續上升時。", "未コミットのジャーナル件数と入力・処理・出力バッファが上がり続けるとき。")),
        (t("Pace", "放慢", "減速"), t("API exports wait between pages, from 0 at 70 % up to 5 seconds at 90 %.", "API 匯出在頁與頁之間等待，70 % 時為 0，90 % 時最多 5 秒。", "API エクスポートはページ間で待ちます（70 % で 0 秒〜90 % で最大 5 秒）。")),
        (t("Pause", "暫停", "一時停止"), t("Until the signal drains; the job shows “Paused — source under load”. Unreadable metrics count as pressure.", "直到指標回落；作業顯示「已暫停：來源負載過高」。讀不到指標也視為有壓力。", "指標が下がるまで。ジョブに「一時停止：送信元が高負荷」と出ます。読めない指標も負荷とみなします。")),
        (t("Stop once", "停止一次", "1 回停止"), t("If it never drains, the run stops once, keeps what it archived, and retries after 60 minutes.", "若一直沒有回落，這次執行停止一次，保留已歸檔的部分，60 分鐘後再試。", "下がらなければ実行を 1 回だけ止め、アーカイブ済みは残し、60 分後に再試行します。")),
    ])
    body = st + f'<p class="note">{t("Why: on busy or HDD-backed storage a heavy export loads the same OpenSearch cluster Graylog indexes into, and can wedge Graylog until it is restarted. Every fast path — OpenSearch Direct export and Bulk import included — is throttled the same way; Bulk watches OpenSearch heap and this host’s free memory.", "原因：在忙碌或使用 HDD 的儲存上，大量匯出會壓到 Graylog 正在寫入的同一個 OpenSearch 叢集，可能讓 Graylog 卡到必須重啟。所有快速路徑（含 OpenSearch Direct 匯出與 Bulk 匯入）都一樣會調速；Bulk 會留意 OpenSearch heap 與本機剩餘記憶體。", "理由：忙しい、または HDD のストレージでは、大量のエクスポートが Graylog の書き込み先と同じ OpenSearch に負荷をかけ、再起動まで Graylog を詰まらせることがあります。OpenSearch Direct エクスポートと Bulk インポートを含むすべての高速経路を同じように制御し、Bulk は OpenSearch のヒープとこのホストの空きメモリを見ます。")}</p>'
    return section("guard", t("Backpressure: keep Graylog responsive", "背壓保護：不讓 Graylog 卡住", "負荷制御：Graylog を詰まらせない"),
                   t("An export is a guest on Graylog's cluster. It watches the host and gives way.", "匯出是 Graylog 叢集的客人：留意主人的狀況，必要時讓路。",
                     "エクスポートは Graylog クラスタの客です。様子を見て、道を譲ります。"), body)


def importer():
    pre = steps([
        (t("Connect", "連線", "接続"), t("Credentials, cluster health (RED aborts) and a running GELF input.", "帳密、叢集狀態（RED 即中止）與運作中的 GELF input。", "認証情報、クラスタの状態（RED なら中止）、動作中の GELF 入力。")),
        (t("Baseline", "基準值", "基準値"), t("Indexer failure count before the import, to compare afterwards.", "匯入前的 indexer 失敗數，事後比對用。", "インポート前の indexer 失敗数（後で比較）。")),
        (t("Field types", "欄位型別", "フィールド型"), t("Recorded at export, so no archive has to be scanned again.", "匯出時已記下，不必重新掃描歸檔。", "エクスポート時に記録済みなので、アーカイブを再走査しません。")),
        (t("Capacity", "容量", "容量"), t("Rotation and retention of the target set: aborts if retention would delete the imported data.", "目標索引集的輪替與保留期：若保留期會刪掉匯入的資料就中止。", "送り先のローテーションと保持期間。取り込んだデータが消える設定なら中止します。")),
        (t("Mappings", "Mapping", "マッピング"), t("Fields seen both as numbers and text are pinned to text, and the field limit raised to 10,000.", "同時出現數字與文字的欄位固定為文字，欄位上限提高到 10,000。", "数値と文字列の両方で現れたフィールドを文字列に固定し、フィールド上限を 10,000 に。")),
        (t("Cycle", "輪替", "ローテーション"), t("One deflector cycle so the new mappings apply, then wait until the new index is ready.", "輪替一次 deflector 讓新 mapping 生效，並等到新索引就緒。", "deflector を 1 回切り替えて新しいマッピングを有効にし、新インデックスの準備を待ちます。")),
    ])
    modes = (f'<div class="grid two-cards">'
             + card("⇄", t("GELF (TCP 32202)", "GELF（TCP 32202）", "GELF（TCP 32202）"),
                    t("Every message goes through Graylog's input, pipelines, extractors and stream routing again. TCP gives backpressure, so nothing is dropped silently; a reconnect during the send means the result is not called “verified”.",
                      "每筆訊息重新經過 Graylog 的 input、管線、extractor 與串流路由。TCP 有背壓，不會無聲丟失；傳送中若曾重新連線，結果不會標成「已驗證」。",
                      "各メッセージが Graylog の入力・パイプライン・extractor・ストリームの振り分けを再び通ります。TCP には背圧があり黙って落ちません。送信中に再接続があれば「検証済み」とはしません。"))
             + card("⇶", t("OpenSearch Bulk", "OpenSearch Bulk", "OpenSearch Bulk"),
                    t("Writes through the index set's deflector alias so Graylog finds the data at once, with <code>gl2_message_id</code> as the document ID (no duplicates) and a marker field. The response is checked document by document.",
                      "透過索引集的 deflector 別名寫入，Graylog 立即找得到；以 <code>gl2_message_id</code> 作為文件 ID（不重複），並加上標記欄位。逐筆檢查回應。",
                      "インデックスセットの deflector エイリアスに書くので Graylog がすぐ見つけられます。<code>gl2_message_id</code> を文書 ID にし（重複なし）、目印のフィールドを付け、応答を 1 件ずつ確認します。"))
             + "</div>")
    body = f'<h3>{t("Preflight, before the first message", "第一筆送出前的預檢", "最初のメッセージの前の事前チェック")}</h3>{pre}' \
           f'<h3>{t("Two ways in", "兩種寫入方式", "2 つの書き込み方法")}</h3>{modes}' \
           f'<p class="note">{t("Compliance goal: zero lost messages and zero indexer failures. Archives are read in batches, never loaded whole — customer archives reach 1.2 GB compressed. Import slows down and shrinks its batch when the target’s journal, buffers or heap, or this host’s memory, are under pressure.", "合規目標：零遺失、零 indexer 失敗。歸檔以批次讀取，不會整檔載入（實際客戶的歸檔壓縮後可達 1.2 GB）。目標的 journal、buffer、heap 或本機記憶體吃緊時，匯入會放慢並縮小批次。", "コンプライアンスの目標は、欠落ゼロ・indexer 失敗ゼロ。アーカイブは一括で読み込まずバッチで読みます（実際の顧客のアーカイブは圧縮で 1.2 GB に達します）。送り先のジャーナル・バッファ・ヒープ、またはこのホストのメモリが逼迫すると、速度を落としバッチを小さくします。")}</p>'
    return section("import", t("Import", "匯入", "インポート"),
                   t("Before anything is sent, the target is checked and prepared; afterwards the result is reconciled.", "送出任何資料前先檢查並準備目標；送完再核對結果。",
                     "何かを送る前に送り先を確認して準備し、送った後に結果を照合します。"), body, alt=True)


def integrity():
    st = steps([
        (t("Write", "寫入", "書き込み"), t("The writer computes SHA256 while it streams the file.", "寫入時邊串流邊計算 SHA256。", "書き込みながら SHA256 を計算します。")),
        (t("Seal", "封存", "封印"), t("With integrity enabled, a keyed HMAC-SHA256 too; the key comes from <code>JT_HMAC_KEY</code> or a 0600 key file.", "啟用完整性時再加上帶金鑰的 HMAC-SHA256；金鑰來自 <code>JT_HMAC_KEY</code> 或權限 0600 的金鑰檔。", "完全性を有効にすると鍵付き HMAC-SHA256 も。鍵は <code>JT_HMAC_KEY</code> か 0600 の鍵ファイルから。")),
        (t("Ledger", "清單", "台帳"), t("An independent ledger table, and a manifest you can copy off the box.", "獨立的清單資料表，以及可複製到其他主機的清單檔。", "独立した台帳テーブルと、別ホストにコピーできるマニフェスト。")),
        (t("Verify", "驗證", "検証"), t("Scheduled re-verification with several workers in parallel.", "依排程以多個工作程序平行重新驗證。", "スケジュールで複数ワーカーが並列に再検証します。")),
        (t("Status", "狀態", "状態"), t("Ok, corrupted (SHA256 differs), tampered (HMAC differs) or missing.", "正常、損毀（SHA256 不符）、遭竄改（HMAC 不符）或遺失。", "正常、破損（SHA256 不一致）、改ざん（HMAC 不一致）、欠落。")),
        (t("Self-heal", "自我修復", "自己修復"), t("A deleted archive frees its time range, and the next export fetches it again while Graylog still has it.", "被刪除的歸檔會釋出它的時間範圍，下次匯出會在 Graylog 仍保有資料時重新抓取。", "削除されたアーカイブは時間範囲を空け、Graylog にまだあれば次のエクスポートで取り直します。")),
    ])
    lim = ticks([
        t("A plain checksum only shows a change against the stored value: whoever edits the file and the database together forges a consistent pair. The keyed HMAC cannot be forged without the key.",
          "單純的校驗值只能看出與儲存值不同：同時改檔案與資料庫就能偽造一致的組合。帶金鑰的 HMAC 沒有金鑰就無法偽造。",
          "単なるチェックサムは保存値との違いしか示せず、ファイルと DB を両方書き換えれば整合した組を偽造できます。鍵付き HMAC は鍵なしには偽造できません。"),
        t("Honest limit: a key kept on the same box does not stop root. For that, supply the key by environment only and keep the ledger copy elsewhere.",
          "實際限制：金鑰放在同一台主機擋不住 root。若要防範，金鑰只用環境變數提供，並把清單複本存到別處。",
          "正直な限界：同じホストに置いた鍵では root を防げません。そのためには鍵を環境変数だけで渡し、台帳のコピーを別の場所に置きます。"),
        t("Cleanup never deletes a file changed in the last 10 minutes, so a file still being written is safe.",
          "清理不會刪除最近 10 分鐘內有變動的檔案，正在寫入的檔案不會被刪。",
          "クリーンアップは直近 10 分以内に変更されたファイルを消さないので、書き込み中のファイルは安全です。"),
    ])
    return section("integrity", t("Integrity and retention", "完整性與保留期", "完全性と保持期間"),
                   t("Every archive can prove it is the file that was written.", "每個歸檔都能證明自己就是當初寫入的那個檔案。",
                     "各アーカイブは、書き込まれたときのファイルであることを証明できます。"), st + f'<div class="reccard">{lim}</div>')


def datanode():
    st = steps([
        (t("Issue", "申請", "発行"), t("<code>POST /api/ca/clientcert</code> as a Graylog admin: Graylog's CA signs a 90-day certificate and maps it to <code>all_access</code>.", "以 Graylog 管理者呼叫 <code>POST /api/ca/clientcert</code>：Graylog 的 CA 簽發 90 天憑證並對應到 <code>all_access</code>。", "Graylog 管理者として <code>POST /api/ca/clientcert</code>：Graylog の CA が 90 日の証明書に署名し <code>all_access</code> に割り当てます。")),
        (t("Store", "保存", "保存"), t("Key, certificate and CA under <code>certs/datanode/&lt;server&gt;/</code>, replaced atomically.", "金鑰、憑證與 CA 存在 <code>certs/datanode/&lt;server&gt;/</code>，以原子方式替換。", "鍵・証明書・CA を <code>certs/datanode/&lt;server&gt;/</code> に保存し、アトミックに置き換えます。")),
        (t("Connect", "連線", "接続"), t("Every OpenSearch connection presents it; the chain is always checked against Graylog's CA.", "每次連 OpenSearch 都出示憑證；憑證鏈一律以 Graylog 的 CA 驗證。", "OpenSearch への接続ごとに提示し、チェーンは常に Graylog の CA で検証します。")),
        (t("Renew", "更新", "更新"), t("When a third of its lifetime is left, and by a daily job at 04:45.", "剩下三分之一效期時更新，另有每日 04:45 的排程。", "残り期間が 3 分の 1 になったときと、毎日 04:45 のジョブで更新します。")),
        (t("Probe", "探測", "確認"), t("Before each OpenSearch export and Bulk import: refused means re-issue once; unreachable means wait and try again (1, 2, 5 minutes).", "每次 OpenSearch 匯出與 Bulk 匯入前探測：被拒就重新申請一次；連不上就等待後重試（1、2、5 分鐘）。", "各 OpenSearch エクスポートと Bulk インポートの前に確認。拒否なら 1 回再発行、届かなければ待って再試行（1・2・5 分）。")),
        (t("Fall back", "改用 API", "API に切替"), t("A scheduled run whose certificate still fails runs in API mode and notifies, so archiving never stops.", "排程執行若憑證仍失敗，改用 API 模式並通知，歸檔不會中斷。", "証明書がまだ失敗するスケジュール実行は API モードで動き、通知します。アーカイブは止まりません。")),
    ])
    return section("datanode", t("Graylog 7 Data Node (beta)", "Graylog 7 Data Node（beta）", "Graylog 7 Data Node（ベータ）"),
                   t("A Data Node is Graylog-managed OpenSearch that accepts client certificates only. Measured on Graylog 6.3, 7.0, 7.1 and 7.2.",
                     "Data Node 是由 Graylog 管理、只接受用戶端憑證的 OpenSearch。已在 Graylog 6.3、7.0、7.1、7.2 實測。",
                     "Data Node は Graylog が管理する、クライアント証明書のみを受け付ける OpenSearch です。Graylog 6.3・7.0・7.1・7.2 で実測しました。"),
                   st + f'<p class="note">{t("Each jt-glogarch server gets its own certificate name, so two servers on one cluster never revoke each other. A server with a connected Data Node cannot be deleted before Disconnect.", "每台 jt-glogarch 伺服器有自己的憑證名稱，同一叢集上的兩台不會互相撤銷。已連接 Data Node 的伺服器必須先中斷連線才能刪除。", "jt-glogarch のサーバーごとに証明書名が異なるので、同じクラスタの 2 台が互いを取り消すことはありません。Data Node に接続中のサーバーは、切断するまで削除できません。")}</p>', alt=True)


def security():
    st = steps([
        (t("Aggregate", "聚合", "集計"), t("<code>POST /api/search/aggregate</code> per probe: grouped counts, never message text.", "每個探測執行 <code>POST /api/search/aggregate</code>：分組計數，不讀訊息內容。", "プローブごとに <code>POST /api/search/aggregate</code>：グループ化した件数のみで本文は読みません。")),
        (t("Detect", "偵測", "検知"), t("Thresholds per detection; Sigma rules run as converted queries.", "每個偵測項目有門檻；Sigma 規則以轉換後的查詢執行。", "検知ごとのしきい値。Sigma ルールは変換したクエリで実行します。")),
        (t("Learn", "學習", "学習"), t("New login sources and unusual volume compare with 7–14 days of history kept in the database.", "帳號新來源與記錄量異常會與資料庫中 7～14 天的歷史比對。", "新しいログイン元とログ量の異常は、DB に保持した 7〜14 日の履歴と比べます。")),
        (t("Suppress", "排除", "抑制"), t("Suppressions are applied; they never change what Graylog counts.", "套用排除規則；排除不會改變 Graylog 的計數。", "抑制を適用します。抑制は Graylog の件数を変えません。")),
        (t("Context", "補充", "補足"), t("Top values per finding: which source reported it, which site, which paths.", "每個發現補上前幾名的值：哪個來源回報、哪個站台、哪些路徑。", "各検出に上位の値を補足：どの送信元が報告し、どのサイトで、どのパスか。")),
        (t("Store and notify", "儲存與通知", "保存と通知"), t("Incidents are opened or updated; new or escalated ones notify; an AI verdict may follow, after the notification.", "建立或更新事件；新的或升級的事件會通知；之後才可能接著產生 AI 判斷。", "インシデントを作成・更新し、新規や深刻化したものを通知。その後に AI 判定が続くことがあります。")),
    ])
    lim = ticks([
        t("Every probe tries several field names and the coverage table reports what is missing: field names are not uniform even on one site",
          "每個探測會嘗試多種欄位名稱，「涵蓋狀況」表會列出缺少的部分：即使同一站台，欄位名稱也不一致",
          "各プローブは複数のフィールド名を試し、カバレッジ表が欠けを示します。同じサイトでもフィールド名は揃っていません"),
        t("Events without the grouping field come back as one “(Empty Value)” row: that is the coverage measure, never an incident",
          "缺少分組欄位的事件會集中成一列「(Empty Value)」：那是涵蓋程度的量測，不會當成事件",
          "グループ化フィールドのないイベントは「(Empty Value)」1 行にまとまります。これはカバレッジの指標で、インシデントにはしません"),
        t("Thresholds were calibrated on real data: machine accounts failing all day and constant scanner noise do not open incidents",
          "門檻以實際資料校正：整天登入失敗的機器帳號與持續的掃描雜訊不會開成事件",
          "しきい値は実データで調整済み。一日中失敗するマシンアカウントや絶え間ないスキャンのノイズではインシデントを作りません"),
    ])
    return section("security", t("Security analysis", "資安分析", "セキュリティ分析"),
                   t("A scheduled run, off by default, that reads counts from Graylog with the detector's own server connection.", "預設關閉的排程工作，以偵測用的伺服器連線向 Graylog 讀取計數。",
                     "既定ではオフのスケジュール実行で、検知用のサーバー接続を使って Graylog から件数を読みます。"), st + f'<div class="reccard">{lim}</div>')


def ai():
    st = steps([
        (t("Budget", "預算", "予算"), t("The model's context is read from the server; answer, history and tool results each get a share.", "向伺服器讀取模型的上下文長度，答案、歷史與工具結果各分配一部分。", "サーバーからモデルのコンテキスト長を読み、回答・履歴・ツール結果に配分します。")),
        (t("Ask", "詢問", "質問"), t("The question goes to the model with the read-only tools it may call.", "把問題與可呼叫的唯讀工具一起交給模型。", "質問と、呼べる読み取り専用ツールをモデルに渡します。")),
        (t("Query", "查詢", "問い合わせ"), t("Each tool call runs as the signed-in user against Graylog and is audited.", "每次工具呼叫都以登入者身分查詢 Graylog，並記入稽核。", "各ツール呼び出しはサインインしたユーザーとして Graylog に問い合わせ、監査に記録します。")),
        (t("Shape", "整理", "整形"), t("A result too large is kept in memory for 30 minutes and handed over page by page.", "過大的結果在記憶體保留 30 分鐘，分頁交給模型。", "大きすぎる結果はメモリに 30 分保持し、ページごとに渡します。")),
        (t("Guard", "防護", "防止"), t("A model repeating itself is stopped and asked once more; the same call is never run twice.", "模型開始重複時會被中止並重問一次；相同的呼叫不會執行兩次。", "繰り返し始めたモデルは止めて 1 回だけ聞き直し、同じ呼び出しは 2 回実行しません。")),
        (t("Answer", "回答", "回答"), t("Streamed to the page with every query listed; it keeps running if the page is closed.", "串流顯示在頁面上並列出每次查詢；關閉頁面也會繼續完成。", "クエリ一覧付きでページに逐次表示し、ページを閉じても続きます。")),
    ])
    lim = ticks([
        t("No write tools exist: the model can read through the tools, never change Graylog",
          "沒有任何寫入工具：模型只能透過工具讀取，無法變更 Graylog",
          "書き込みツールはありません。モデルはツールで読むだけで、Graylog を変更できません"),
        t("Tool results go back to the model marked as data, so text inside a log cannot pose as an instruction",
          "工具結果以「資料」標記交回給模型，記錄裡的文字無法偽裝成指令",
          "ツールの結果はデータとして印を付けてモデルに戻すので、ログ内の文字が指示を装えません"),
        t("The MCP endpoint checks the Graylog token's role, limits requests per token and refuses repeated bad tokens per address",
          "MCP 端點會檢查 Graylog token 的角色、限制每個 token 的請求數，並拒絕同一位址反覆送來的錯誤 token",
          "MCP エンドポイントは Graylog トークンのロールを確認し、トークンごとに要求数を制限し、同じアドレスからの不正なトークンの繰り返しを拒否します"),
        t("Graylog-side tools come from mcp_graylog, embedded unmodified with its version and checksum pinned",
          "Graylog 端的工具來自 mcp_graylog，原樣內嵌並固定版本與校驗值",
          "Graylog 側のツールは mcp_graylog を改変せずに組み込み、バージョンとチェックサムを固定しています"),
    ])
    return section("ai", t("AI chat", "智慧問答", "AI チャット"),
                   t("A loop between your question, the model and read-only tools, sized to the model you run.", "在您的問題、模型與唯讀工具之間往返，依您使用的模型調整用量。",
                     "質問・モデル・読み取り専用ツールの間の往復で、お使いのモデルに合わせて量を調整します。"), st + f'<div class="reccard">{lim}</div>', alt=True)


def upgrade():
    P = [("1", ("Keep the data", "不遺失資料", "データを失わない"),
          ("A change applied to state written by an older version may only go in the safe direction automatically: a cleanup never starts deleting what the previous version kept.",
           "套用在舊版狀態上的變更，只會自動往安全的方向：清理不會開始刪除舊版原本保留的資料。",
           "旧版の状態に適用する変更は、安全な方向だけ自動で行います。旧版が保持していたものをクリーンアップが消し始めることはありません。")),
         ("2", ("Keep it usable", "系統維持可用", "使える状態を保つ"),
          ("The service must start and serve; <code>/api/health</code> must report the new version before a release counts as done.",
           "服務必須能啟動並提供服務；<code>/api/health</code> 回報新版本後才算完成發版。",
           "サービスは起動して応答しなければならず、<code>/api/health</code> が新しいバージョンを返して初めてリリース完了です。")),
         ("3", ("Keep scheduled archiving running", "排程歸檔不中斷", "スケジュールされたアーカイブを止めない"),
          ("Every schedule must survive and be registered; the first 03:00 run after an unattended upgrade must work.",
           "每個排程都必須保留並重新註冊；無人值守升級後的第一次 03:00 執行必須正常。",
           "すべてのスケジュールが残って登録されなければならず、無人アップグレード後の最初の 03:00 の実行が動く必要があります。")),
         ("4", ("Survive an OS upgrade underneath", "能承受底層作業系統升級", "下の OS アップグレードに耐える"),
          ("When Ubuntu moves Python 3.10 → 3.12 the installed package cannot be imported; every step before the reinstall uses only bash and the standard library.",
           "Ubuntu 從 Python 3.10 升到 3.12 時，已安裝的套件無法匯入；重新安裝前的每個步驟只用 bash 與標準函式庫。",
           "Ubuntu が Python 3.10 → 3.12 に上がるとインストール済みのパッケージを import できません。再インストール前の手順は bash と標準ライブラリだけを使います。"))]
    cards = "".join(f'<div class="card"><h3><span class="ic">{n}</span>{t(*h)}</h3><p>{t(*b)}</p></div>' for n, h, b in P)
    st = steps([
        (t("Back up", "備份", "バックアップ"), t("An online snapshot of the database (stdlib <code>sqlite3</code> if the package cannot load).", "資料庫線上快照（套件無法載入時改用標準函式庫 <code>sqlite3</code>）。", "DB のオンラインスナップショット（パッケージが読めなければ標準の <code>sqlite3</code>）。")),
        (t("Update", "更新", "更新"), t("<code>git pull</code>, or the offline bundle; a clone that diverged from the published history is reset safely.", "<code>git pull</code> 或離線安裝包；與公開歷史分岔的 clone 會安全地重設。", "<code>git pull</code> またはオフラインバンドル。公開履歴と分岐した clone は安全にリセットします。")),
        (t("Reinstall", "重新安裝", "再インストール"), t("<code>pip install --force-reinstall</code>, so the service never runs stale code.", "<code>pip install --force-reinstall</code>，避免服務跑到舊程式。", "<code>pip install --force-reinstall</code> で、古いコードが動き続けないようにします。")),
        (t("Migrate", "遷移", "移行"), t("Missing database columns and settings are added on start; nothing is removed.", "啟動時補上缺少的資料庫欄位與設定，不刪除任何東西。", "起動時に足りない DB 列と設定を追加し、何も削除しません。")),
        (t("Restart", "重啟", "再起動"), t("The service restarts and every schedule is registered again.", "服務重啟，所有排程重新註冊。", "サービスを再起動し、すべてのスケジュールを登録し直します。")),
        (t("Check", "檢查", "確認"), t("<code>/api/health</code> must answer with the new version; the PDF engine is tested by rendering a real page.", "<code>/api/health</code> 必須回報新版本；PDF 引擎以實際產生一頁來測試。", "<code>/api/health</code> が新しいバージョンを返すこと。PDF エンジンは実際に 1 ページ描画して確認します。")),
    ])
    return section("upgrade", t("Upgrade safety", "升級安全", "アップグレードの安全性"),
                   t("Customers upgrade unattended and the first scheduled run fires at night with nobody watching. Four rules override convenience.",
                     "客戶常在無人值守下升級，第一次排程在夜裡執行、沒人看著。四條規則優先於任何方便。",
                     "顧客は無人でアップグレードし、最初のスケジュール実行は誰も見ていない夜に動きます。4 つの規則は利便性より優先します。"),
                   f'<div class="grid">{cards}</div><h3>{t("What upgrade.sh does", "upgrade.sh 做了什麼", "upgrade.sh がすること")}</h3>{st}')


def bounds():
    writes = ticks([
        t("Import: messages, plus the index set, stream, field mappings and one deflector cycle the preflight needs",
          "匯入：訊息本身，以及預檢需要的索引集、串流、欄位 mapping 與一次 deflector 輪替",
          "インポート：メッセージと、事前チェックに必要なインデックスセット・ストリーム・フィールドマッピング・deflector の切り替え 1 回"),
        t("Alerting: the notifications of event definitions you picked, as you, after a preview, with undo",
          "告警：您選定的事件定義的通知，以您的身分、先預覽、可復原",
          "アラート：選んだイベント定義の通知を、あなたとして、プレビュー後に、取り消し可能な形で"),
        t("Content packs you install, upload or uninstall, and Graylog dashboards you create from an AI answer",
          "您安裝、上傳或解除安裝的內容套件，以及您從 AI 答案建立的 Graylog 看板",
          "インストール・アップロード・アンインストールするコンテンツパックと、AI の回答から作る Graylog ダッシュボード"),
        t("Clearing an import target's index set: only when you type its prefix to confirm; aborts if the write index cannot be identified",
          "清空匯入目標的索引集：必須輸入前置碼確認才執行；無法辨識寫入索引時中止",
          "インポート先のインデックスセットの消去：プレフィックスを入力して確認したときだけ。書き込みインデックスを特定できなければ中止"),
        t("A Data Node client certificate, when you click Connect", "按下「連接」時申請的 Data Node 用戶端憑證",
          "「接続」を押したときの Data Node クライアント証明書"),
    ])
    never = ticks([
        t("No telemetry: nothing is sent anywhere except the systems listed on the home page", "沒有遙測：除了首頁列出的系統，不會送資料到任何地方",
          "テレメトリーなし。ホームに挙げたシステム以外にはどこにも送りません"),
        t("Archives are deleted only by the retention you set, or when you delete them", "歸檔只會依您設定的保留期，或由您手動刪除",
          "アーカイブは設定した保持期間か、手動削除でしか消えません"),
        t("The AI cannot write: there are no write tools", "AI 無法寫入：沒有任何寫入工具", "AI は書き込めません。書き込みツールがありません"),
        t("Security analysis reads counts and never message bodies", "資安分析只讀計數，不讀訊息內容", "セキュリティ分析は件数だけを読み、本文は読みません"),
        t("Graylog's internal event index sets are never offered for clearing", "Graylog 內部的事件索引集不會出現在可清空清單中",
          "Graylog 内部のイベント用インデックスセットは消去の候補に出しません"),
    ], "ticks no")
    body = (f'<div class="two top"><div class="reccard"><h3>{t("It writes to Graylog only when you ask", "只有在您要求時才寫入 Graylog", "Graylog に書くのは頼まれたときだけ")}</h3>{writes}</div>'
            f'<div class="reccard"><h3>{t("What it does not do", "不會做的事", "しないこと")}</h3>{never}</div></div>')
    return section("bounds", t("Boundaries", "邊界", "境界"),
                   t("A tool that reads your whole logging platform should be clear about what it touches.", "一個能讀取整個記錄平台的工具，應該清楚交代它會碰到什麼。",
                     "ログ基盤全体を読めるツールは、何に触れるかを明確にすべきです。"), body)


def build():
    PREFIX["p"] = "w"
    title = reg("title_how", "How jt-glogarch works", "jt-glogarch 運作架構", "jt-glogarch の仕組み")
    desc = reg("desc_how", "Architecture, export and import paths, backpressure, integrity, Data Node certificates, security analysis, AI chat, upgrade safety and boundaries.",
               "系統架構、匯出與匯入路徑、背壓保護、完整性、Data Node 憑證、資安分析、智慧問答、升級安全與邊界。",
               "システム構成、エクスポートとインポートの経路、負荷制御、完全性、Data Node 証明書、セキュリティ分析、AI チャット、アップグレードの安全性と境界。")
    body = (header(nav(), home_link=True) + hero() + arch() + export() + guard() + importer() + integrity() + datanode() + security() + ai()
            + upgrade() + bounds() + dialogs() + footer())
    return page(title, desc, body, "how")
