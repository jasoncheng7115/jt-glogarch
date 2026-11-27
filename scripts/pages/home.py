"""index.html: what jt-glogarch is, laid out like jt-waf-mgr's project page."""
from lib import (D, GH, card, card_list, code, header, footer, dialogs, page, reg, section, shot, steps, t, ticks, tk,
                 PREFIX)


def nav():
    items = [("#features", "nav_features", ("Features", "功能", "機能")),
             ("#flow", "nav_flow", ("Archive flow", "歸檔流程", "アーカイブの流れ")),
             ("#modes", "nav_modes", ("Deployment", "部署方式", "構成")),
             ("#security", "nav_sec", ("Security", "資安中心", "セキュリティ")),
             ("#ai", "nav_ai", ("AI chat", "智慧問答", "AI チャット")),
             ("#audit", "nav_audit", ("Audit", "行為稽核", "操作監査")),
             ("#reports", "nav_reports", ("Reports", "統計報表", "レポート")),
             ("#packs", "nav_packs", ("Content packs", "內容套件", "コンテンツパック")),
             ("#screens", "nav_screens", ("Screens", "畫面", "画面")),
             ("#install", "nav_install", ("Install", "安裝", "インストール")),
             ("#specs", "nav_specs", ("Specs", "規格", "仕様"))]
    opt = {"nav_reports", "nav_screens", "nav_specs"}
    out = []
    for href, k, (en, zh, ja) in items:
        reg(k, en, zh, ja)
        c = ' class="opt"' if k in opt else ""
        out.append(f'<a href="{href}"{c} data-t="{k}">{en}</a>')
    out.append(f'<a href="how.html" id="how-link" data-t="nav_how">How it works</a>')
    return "".join(out)


def hero():
    lead = t("Archive and restore for Graylog Open: logs leave Graylog as compressed files with SHA256 checksums, "
             "and go back into any Graylog when you need them. The same web interface adds an independent audit trail, "
             "PDF reports, content packs, security incidents and AI chat.",
             "Graylog Open 的記錄歸檔與還原工具：把 Graylog 裡的記錄壓縮成附 SHA256 校驗的檔案長期保存，需要時再匯回任何一台 Graylog。"
             "同一個網頁介面還有獨立的行為稽核、PDF 統計報表、內容套件、資安事件與智慧問答。",
             "Graylog Open のためのアーカイブとリストア：ログを SHA256 チェックサム付きの圧縮ファイルとして Graylog から取り出し、"
             "必要なときにどの Graylog にも戻せます。同じ Web 画面に、独立した操作監査、PDF レポート、コンテンツパック、"
             "セキュリティインシデント、AI チャットもあります。", tag="p", cls="lead", key="lead")
    car = [("1_dashboard", ("Dashboard", "儀表板", "ダッシュボード")),
           ("2_archives", ("Archives", "歸檔清單", "アーカイブ一覧")),
           ("11_ai_chat", ("AI chat", "智慧問答", "AI チャット"))]
    slides, dots = [], []
    for i, (name, cap) in enumerate(car):
        k = reg(f"car_{i}", *cap)
        on = " on" if i == 0 else ""
        hid = "" if i == 0 else ' aria-hidden="true" tabindex="-1"'
        slides.append(f'<a class="shotlink car-slide{on}" href="screenshots/{name}_en.png" data-shot="{name}" data-cap="{k}"{hid}>'
                      f'<img class="shot" src="screenshots/{name}_en.png" alt=""></a>')
        cur = ' aria-current="true"' if i == 0 else ""
        dots.append(f'<button type="button" data-i="{i}" data-ta="{k}"{cur}></button>')
    reg("car_prev", "Previous", "上一張", "前へ")
    reg("car_next", "Next", "下一張", "次へ")
    btns = (f'<a class="btn primary" href="{GH}">GitHub</a>'
            f'<a class="btn" href="#install">{t("Get started", "開始使用", "はじめる", key="get_started")}</a>'
            f'<a class="btn cl-link" href="{GH}/blob/main/CHANGELOG.md">{tk("changelog")}</a>'
            f'<a class="btn" href="how.html" id="how-btn">{tk("nav_how")}</a>')
    chips = "".join(f'<span class="chip">{c}</span>' for c in
                    ("Graylog 6 / 7", "OpenSearch 2 / 3", "Graylog Data Node", "Python 3.10+", "FastAPI · SQLite", "AGPL-3.0"))
    return f'''<div class="hero"><div class="wrap">
  <div>
    <h1>jt-glogarch <span class="ver" id="ver" hidden></span></h1>
    {lead}
    <div class="btns">{btns}</div>
    <div class="chips">{chips}</div>
  </div>
  <div class="car" id="car">
    <div class="car-track">{"".join(slides)}
      <button type="button" class="car-btn prev" id="car-prev" data-ta="car_prev">&#8249;</button>
      <button type="button" class="car-btn next" id="car-next" data-ta="car_next">&#8250;</button>
    </div>
    <div class="car-foot"><span class="car-cap" id="car-cap">{car[0][1][0]}</span><span class="car-dots">{"".join(dots)}</span></div>
  </div>
</div></div>
'''


def modes():
    L = lambda *a: a  # noqa: E731
    figs = []
    # 1. one VM
    d = D(360, 340, L("Deployment 1: everything on one VM", "部署方式一：全部在同一台主機", "構成 1：すべて 1 台の VM"), "flowsvg")
    d.box(110, 8, 140, 46, "ext", L("Administrator", "管理者", "管理者"), L("browser, port 8990", "瀏覽器，8990 port", "ブラウザ、8990 番"))
    d.group(10, 76, 340, 256, L("one VM (the common case)", "同一台主機（最常見）", "1 台の VM（よくある構成）"))
    d.box(26, 96, 150, 58, "core", L("jt-glogarch", "jt-glogarch", "jt-glogarch"), L("web UI · scheduler", "網頁介面・排程", "Web 画面・スケジューラ"))
    d.box(26, 246, 150, 58, "file", L("Archive disk", "歸檔磁碟", "アーカイブ用ディスク"), mono="/data/graylog-archives")
    d.box(206, 96, 130, 44, "svc", L("Graylog", "Graylog", "Graylog"))
    d.box(206, 162, 130, 44, "svc", L("OpenSearch", "OpenSearch", "OpenSearch"))
    d.box(206, 228, 130, 44, "svc", L("MongoDB", "MongoDB", "MongoDB"))
    d.edge("M180,54 L180,72 L101,72 L101,96", "main")
    d.edge("M176,118 L206,118", label=L("API", "API", "API"), lx=191, ly=111)
    d.edge("M176,140 L190,140 L190,184 L206,184")
    d.edge("M101,154 L101,246", label=L("streamed write", "邊讀邊寫入", "逐次書き込み"), lx=107, ly=206, anchor="start", w=90)
    figs.append(d.render("fig-m1", zoom=False))
    # 2. separate archive host
    d = D(360, 340, L("Deployment 2: a separate archive host", "部署方式二：獨立的歸檔主機", "構成 2：アーカイブ専用ホスト"), "flowsvg")
    d.group(10, 8, 340, 112, L("Graylog cluster", "Graylog 叢集", "Graylog クラスタ"), ly=112)
    d.box(26, 24, 140, 50, "svc", L("Graylog", "Graylog", "Graylog"), L("one or more nodes", "一或多個節點", "1 台以上のノード"))
    d.box(194, 24, 140, 50, "svc", L("OpenSearch", "OpenSearch", "OpenSearch"), L("cluster", "叢集", "クラスタ"))
    d.group(10, 196, 340, 136, L("archive host", "歸檔主機", "アーカイブ用ホスト"))
    d.box(26, 214, 140, 58, "core", L("jt-glogarch", "jt-glogarch", "jt-glogarch"), L("its own VM", "獨立的 VM", "専用の VM"))
    d.box(194, 214, 140, 58, "file", L("NAS / NFS", "NAS／NFS", "NAS／NFS"), L("mounted archive path", "掛載的歸檔路徑", "マウントしたアーカイブ先"))
    d.edge("M70,214 L70,74", label=L("REST API", "REST API", "REST API"), lx=76, ly=150, anchor="start")
    d.edge("M130,214 L130,160 L264,160 L264,74", label=L("OpenSearch Direct", "OpenSearch Direct", "OpenSearch Direct"), lx=197, ly=154, w=150)
    d.edge("M166,243 L194,243")
    figs.append(d.render("fig-m2", zoom=False))
    # 3. Data Node
    d = D(360, 340, L("Deployment 3: Graylog 7 with a Data Node", "部署方式三：Graylog 7 搭配 Data Node", "構成 3：Graylog 7 と Data Node"), "flowsvg")
    d.group(10, 8, 340, 124, L("Graylog 7", "Graylog 7", "Graylog 7"), ly=124)
    d.box(26, 24, 140, 62, "svc", L("Graylog server", "Graylog 伺服器", "Graylog サーバー"), L("its CA issues certificates", "以自己的 CA 簽發憑證", "自身の CA が証明書を発行"))
    d.box(194, 24, 140, 62, "svc", L("Data Node", "Data Node", "Data Node"), L("OpenSearch, client certificates only", "OpenSearch，只接受用戶端憑證", "OpenSearch、クライアント証明書のみ"))
    d.box(26, 230, 140, 58, "core", L("jt-glogarch", "jt-glogarch", "jt-glogarch"), L("renews its certificate", "自動更新憑證", "証明書を自動更新"))
    d.box(194, 230, 140, 58, "file", L("Archive disk", "歸檔磁碟", "アーカイブ用ディスク"))
    d.edge("M70,230 L70,86", label=L("asks for a certificate", "申請用戶端憑證", "証明書を申請"), lx=76, ly=170, anchor="start", w=110)
    d.edge("M130,230 L130,196 L264,196 L264,86", "main", label=L("mTLS", "mTLS", "mTLS"), lx=197, ly=190)
    d.edge("M166,259 L194,259")
    figs.append(d.render("fig-m3", zoom=False))
    cards = [
        ("1", t("Next to Graylog", "與 Graylog 同一台", "Graylog と同じホスト"),
         t("Most sites run jt-glogarch on the Graylog VM. Exports and imports watch Graylog's heap, journal and buffers and "
           "this host's free memory, and slow down or pause before the box runs short; the dashboard says what size the VM should be.",
           "多數站台把 jt-glogarch 裝在 Graylog 那台主機上。匯出與匯入會留意 Graylog 的 heap、journal、buffer 與本機剩餘記憶體，"
           "在資源吃緊前先放慢或暫停；儀表板會依實測建議主機規格。",
           "多くのサイトは Graylog の VM に jt-glogarch を置きます。エクスポートとインポートは Graylog のヒープ・ジャーナル・バッファと"
           "このホストの空きメモリを見て、足りなくなる前に速度を落とすか一時停止します。ダッシュボードが VM の推奨サイズを示します。")),
        ("2", t("On its own host", "獨立的歸檔主機", "専用ホスト"),
         t("Run it on a separate VM and point the archive path at NAS or NFS storage. It reads Graylog through the REST API, "
           "or OpenSearch directly (about five times faster), over the network.",
           "裝在另一台 VM，把歸檔路徑指向 NAS 或 NFS。透過網路以 Graylog REST API 讀取，或直接讀 OpenSearch（約快五倍）。",
           "別の VM で動かし、アーカイブ先を NAS や NFS にします。ネットワーク越しに Graylog の REST API、"
           "または OpenSearch を直接（約 5 倍速）読みます。")),
        ("3", t("Graylog 7 Data Node (beta)", "Graylog 7 Data Node（beta）", "Graylog 7 Data Node（ベータ）"),
         t("A Data Node accepts only client certificates. <i>Connect Data Node</i> asks Graylog's own CA for one; jt-glogarch "
           "renews it before it expires, so OpenSearch Direct export and Bulk import work as on a plain OpenSearch.",
           "Data Node 只接受用戶端憑證。按下「連接 Data Node」會向 Graylog 自己的 CA 申請一張，jt-glogarch 會在到期前自動更新，"
           "OpenSearch Direct 匯出與 Bulk 匯入就和一般 OpenSearch 一樣可用。",
           "Data Node はクライアント証明書しか受け付けません。「Data Node に接続」で Graylog 自身の CA から発行を受け、"
           "jt-glogarch が期限前に更新するので、OpenSearch Direct エクスポートと Bulk インポートが通常の OpenSearch と同じように使えます。")),
    ]
    cg = "".join(f'<div class="card"><h3><span class="ic">{n}</span>{h}</h3><p>{b}</p></div>' for n, h, b in cards)
    body = f'<div class="grid three modes-figs">{"".join(figs)}</div>\n<div class="grid modes-grid">{cg}</div>'
    return section("modes", t("Three ways to deploy", "三種部署方式", "3 つの構成"),
                   t("One Python service with its own web interface, scheduler and SQLite database. It needs to reach Graylog, "
                     "and OpenSearch for the fast paths; nothing is installed on the Graylog nodes.",
                     "一個 Python 服務，自帶網頁介面、排程與 SQLite 資料庫。只要連得到 Graylog（快速路徑另需連得到 OpenSearch），"
                     "不必在 Graylog 節點上安裝任何東西。",
                     "Web 画面・スケジューラ・SQLite データベースを持つ 1 つの Python サービスです。Graylog（高速経路では OpenSearch も）に"
                     "届けばよく、Graylog のノードには何もインストールしません。"), body, alt=True)


def fit():
    yes = [t("Graylog Open 6.x or 7.x that must keep logs longer than its hot indices do (regulation, forensics, contracts)",
             "Graylog Open 6.x／7.x，記錄必須保留得比熱索引更久（法規、鑑識、合約）",
             "Graylog Open 6.x／7.x で、ホットインデックスより長くログを保管する必要がある（法令、フォレンジック、契約）"),
           t("Old logs must go back into a Graylog to be searched again, with Graylog's own processing or exactly as they were",
             "舊記錄要能匯回 Graylog 再查，可以重新經過 Graylog 處理，也可以原樣寫回",
             "古いログを Graylog に戻して再検索したい（Graylog の処理を通すか、元のまま書き戻す）"),
           t("Administrators' actions in Graylog must be recorded where Graylog admins cannot delete them",
             "Graylog 管理者的操作必須記在 Graylog 管理者刪不到的地方",
             "Graylog 管理者の操作を、Graylog 管理者が削除できない場所に記録したい"),
           t("You want security incidents, Sigma rules and AI chat on top of Graylog Open, with your own LLM",
             "想在 Graylog Open 上加資安事件、Sigma 規則與智慧問答，並使用自己的 LLM",
             "Graylog Open の上でセキュリティインシデント、Sigma ルール、AI チャットを自前の LLM で使いたい")]
    no = [t("Graylog Enterprise's Archiving already covers what you need: use it",
            "Graylog Enterprise 內建的 Archiving 已能滿足需求：直接使用它",
            "Graylog Enterprise の Archiving で足りる場合：そちらを使ってください"),
          t("Analysing archives in place: archives have no index. Record search scans files for a keyword; real analysis means importing the period back",
            "直接在歸檔上做分析：歸檔沒有索引。記錄搜尋只是逐檔比對關鍵字，要分析就把那段時間匯回 Graylog",
            "アーカイブ上での分析：アーカイブにはインデックスがありません。記録検索はファイルを順に照合するだけで、分析にはその期間を Graylog に戻します"),
          t("Graylog 5 or older: measured on Graylog 6.3 to 7.2 only",
            "Graylog 5 或更舊版本：只在 Graylog 6.3～7.2 實測過",
            "Graylog 5 以前：実測は Graylog 6.3〜7.2 のみ"),
          t("A complete commercial SIEM: detections are Graylog aggregations, and what they see depends on how your logs are parsed",
            "完整的商用 SIEM：偵測是以 Graylog 聚合查詢為基礎，看得到什麼取決於記錄的欄位解析",
            "完全な商用 SIEM：検知は Graylog の集計クエリに基づき、何が見えるかはログのフィールド解析次第です")]
    body = (f'<div class="grid fit-grid"><div class="card fit-yes"><h3><span class="ic">✓</span>'
            f'{t("A good fit", "適合", "向いている")}</h3>{ticks(yes, "plain")}</div>'
            f'<div class="card fit-no"><h3><span class="ic">✕</span>{t("Not a fit (today)", "目前不適合", "向いていない（現時点）")}</h3>'
            f'{ticks(no, "plain")}</div></div>')
    return section("fit", t("Where it fits", "適用場景", "向いている場面"),
                   t("jt-glogarch sits beside Graylog and talks to it through its API and OpenSearch; it never changes how Graylog ingests logs.",
                     "jt-glogarch 放在 Graylog 旁邊，透過 API 與 OpenSearch 和它溝通，不會改變 Graylog 收記錄的方式。",
                     "jt-glogarch は Graylog の横に置き、API と OpenSearch を通して連携します。Graylog のログ受信方法は変えません。"), body)


def uses():
    U = [("⚖", ("Keep logs for compliance", "法規遵循記錄保留", "コンプライアンスのための保管"),
          ("A policy asks for a year of authentication logs while Graylog keeps 90 days hot: a daily schedule archives the streams that matter to cheap storage.",
           "資安政策要求保留一年的認證記錄，但 Graylog 熱索引只保留 90 天：每日排程把需要的串流歸檔到便宜的儲存。",
           "ポリシーは認証ログを 1 年求めるのに Graylog のホットは 90 日：毎日のスケジュールで必要なストリームを安価なストレージへ。")),
         ("⌕", ("Forensics", "鑑識調查", "フォレンジック"),
          ("An incident from six months ago needs a look, long after OpenSearch dropped it: find the hours in the archive list, import, search again.",
           "六個月前的事件需要調查，但記錄早已超過 OpenSearch 保留期：在歸檔清單找到那幾個小時、匯入，就能重新搜尋。",
           "半年前のインシデントを調べたいが OpenSearch からは消えている：アーカイブ一覧でその時間を探してインポートし、再検索します。")),
         ("⇆", ("Cluster migration", "叢集遷移", "クラスタ移行"),
          ("Move from an old Graylog to a new one: OpenSearch Direct exports the old cluster fast, GELF or Bulk loads the new one. No cloud in between.",
           "從舊 Graylog 搬到新 Graylog：OpenSearch Direct 快速匯出舊叢集，再以 GELF 或 Bulk 匯入新叢集，中間不經過雲端。",
           "古い Graylog から新しい Graylog へ：OpenSearch Direct で旧クラスタを素早く取り出し、GELF か Bulk で新クラスタへ。間にクラウドはありません。")),
         ("⛁", ("Off-site copy", "異地備援", "遠隔地コピー"),
          ("Mount remote storage as the archive path and schedule a daily export: searchable history survives the loss of the main cluster.",
           "把遠端儲存掛載成歸檔路徑並排程每日匯出：主叢集故障時，可搜尋的歷史記錄仍然保留。",
           "遠隔地のストレージをアーカイブ先にマウントして毎日エクスポート：メインのクラスタを失っても検索できる履歴が残ります。")),
         ("↧", ("Smaller hot tier", "降低儲存成本", "ホット層を小さく"),
          ("Archives are about ten times smaller than indexed data, so the live cluster keeps only recent days and older data is minutes away.",
           "歸檔大約只有索引資料的十分之一，現役叢集只需保留近期資料，舊資料幾分鐘內就能還原。",
           "アーカイブはインデックス済みデータの約 1/10 なので、稼働中のクラスタは直近だけを持ち、古いデータは数分で戻せます。")),
         ("⚇", ("Independent audit", "獨立稽核", "独立した監査"),
          ("The operation audit records what administrators really did in Graylog, in a database Graylog admins cannot touch.",
           "行為稽核記下管理者在 Graylog 實際做了什麼，存在 Graylog 管理者碰不到的資料庫。",
           "操作監査は管理者が Graylog で実際に行ったことを、Graylog 管理者が触れられない DB に記録します。"))]
    return section("uses", t("Six uses for one archive", "一份歸檔，六種用法", "1 つのアーカイブ、6 つの使い道"),
                   t("Once logs are compressed files with checksums, they serve every one of these.",
                     "記錄一旦成為附校驗值的壓縮檔，就能用在以下每一種情境。",
                     "ログがチェックサム付きの圧縮ファイルになれば、次のどの用途にも使えます。"),
                   f'<div class="grid three">{"".join(card(ic, t(*h), t(*b)) for ic, h, b in U)}</div>', alt=True)


def features():
    F = [
        ("⇩", ("Two ways out", "兩種匯出", "2 つのエクスポート"),
         ("Graylog REST API (works on any Graylog, stream filters) or OpenSearch Direct (about 5× faster, no 10,000-result window).",
          "Graylog REST API（任何 Graylog 都能用、可篩選串流）或 OpenSearch Direct（約快 5 倍、不受 10,000 筆視窗限制）。",
          "Graylog REST API（どの Graylog でも使え、ストリームで絞り込み可）か OpenSearch Direct（約 5 倍速、10,000 件の窓の制限なし）。")),
        ("⇧", ("Two ways back", "兩種匯入", "2 つのインポート"),
         ("GELF replays every message through Graylog's inputs, pipelines and streams; OpenSearch Bulk writes them as they were, 5–10× faster.",
          "GELF 讓每筆訊息重新經過 Graylog 的 input、管線與串流；OpenSearch Bulk 原樣寫回，快 5～10 倍。",
          "GELF は各メッセージを Graylog の入力・パイプライン・ストリームに通し直し、OpenSearch Bulk は元のまま 5〜10 倍速で書き戻します。")),
        ("≋", ("Streamed to disk", "邊讀邊寫入", "逐次ディスクへ"),
         ("Records go to <code>.json.gz</code> as they arrive and never pile up in memory; files roll over at 50 MB.",
          "記錄邊讀邊寫入 <code>.json.gz</code>，不在記憶體堆積；每 50 MB 換一個檔案。",
          "レコードは届いた順に <code>.json.gz</code> へ書かれ、メモリに溜まりません。50 MB ごとにファイルを切り替えます。")),
        ("⧉", ("No duplicates, no gaps", "不重複、不遺漏", "重複なし、欠けなし"),
         ("Time already archived is never fetched again, whichever mode archived it; a scheduled run first refills holes left by earlier runs.",
          "已歸檔的時間不再抓取，不論當初用哪種模式；排程執行時會先補回先前留下的空缺。",
          "アーカイブ済みの時間は、どのモードで取ったものでも再取得しません。スケジュール実行は、まず以前の実行で残った欠けを埋めます。")),
        ("↺", ("Resumes where it stopped", "中斷後接續", "中断した所から再開"),
         ("A restart or a cancel keeps every finished hour and discards only the hour in progress; the next run continues from there.",
          "服務重啟或取消時，保留已完成的每個小時，只丟棄做到一半的那一小時，下次從那裡接續。",
          "再起動やキャンセルでも完了した各時間は残り、途中の 1 時間だけを破棄します。次回はそこから続けます。")),
        ("⛨", ("SHA256 and HMAC", "SHA256 與 HMAC", "SHA256 と HMAC"),
         ("Every archive has a SHA256 checksum, re-verified on a schedule; an optional keyed HMAC and an off-box ledger catch a forged file-and-database pair.",
          "每個歸檔都附 SHA256 並依排程重新驗證；可選用帶金鑰的 HMAC 與機外清單，連檔案與資料庫一起被改也能發現。",
          "各アーカイブに SHA256 を付け、スケジュールで再検証します。鍵付き HMAC と別ホストの台帳（任意）で、ファイルと DB を両方改ざんされても検出できます。")),
        ("◷", ("Cron schedules", "Cron 排程", "cron スケジュール"),
         ("Export, cleanup and verify on standard POSIX cron. Changes in the web UI apply at once and every run shows in the job history.",
          "匯出、清理、驗證都用標準 POSIX cron；在網頁修改立即生效，每次執行都記在作業歷程。",
          "エクスポート・クリーンアップ・検証を標準の POSIX cron で。Web 画面での変更は即時に反映され、実行はすべてジョブ履歴に残ります。")),
        ("⚖", ("Backs off when Graylog is busy", "Graylog 忙碌時自動放慢", "Graylog が忙しいと減速"),
         ("Heap after garbage collection, journal and buffers are read every 15 seconds; exports slow down, pause, and stop once rather than wedge Graylog.",
          "每 15 秒讀取 GC 後的 heap、journal 與 buffer；匯出會放慢、暫停，必要時停止一次，不讓 Graylog 卡住。",
          "GC 後のヒープ・ジャーナル・バッファを 15 秒ごとに読み、エクスポートは減速・一時停止し、必要なら 1 回だけ停止して Graylog を詰まらせません。")),
        ("✓", ("Preflight before import", "匯入前預檢", "インポート前の事前チェック"),
         ("Target capacity, retention and field-type conflicts are checked and fixed before the first message; afterwards indexer failures are reconciled.",
          "送出第一筆前先檢查目標容量、保留期與欄位型別衝突並修正；送完再核對 indexer 失敗數。",
          "最初のメッセージの前に、送り先の容量・保持期間・フィールド型の衝突を確認して修正し、送信後に indexer の失敗数を照合します。")),
        ("⌫", ("Retention and disk outlook", "保留期與磁碟預估", "保持期間とディスク見通し"),
         ("Cleanup keeps what the retention says and never deletes a file still being written; the dashboard estimates how many months the disk still holds.",
          "清理依保留期刪除，不會刪到正在寫入的檔案；儀表板依實際資料預估磁碟還能放幾個月。",
          "クリーンアップは保持期間に従い、書き込み中のファイルは消しません。ダッシュボードはディスクがあと何か月持つかを実データから見積もります。")),
        ("⌕", ("Record search", "記錄搜尋", "記録検索"),
         ("Find records inside archives without restoring them: keyword and field conditions, hits highlighted, CSV or JSON Lines download.",
          "不必還原，直接在歸檔裡找記錄：關鍵字與欄位條件、命中處醒目提示、可下載 CSV 或 JSON Lines。",
          "リストアせずにアーカイブ内のレコードを探せます。キーワードとフィールド条件、一致箇所の強調、CSV／JSON Lines でダウンロード。")),
        ("⚑", ("Alerting in bulk", "告警批次管理", "アラートの一括管理"),
         ("Attach or detach notifications on many Graylog event definitions at once, as the signed-in user, with a preview and undo.",
          "一次替多個 Graylog 事件定義加上或移除通知，以登入者身分執行，先預覽、可復原。",
          "多数の Graylog イベント定義に通知をまとめて付け外しします。サインインしたユーザーとして実行し、プレビューと取り消しがあります。")),
        ("✉", ("Seven notification channels", "七種通知管道", "7 つの通知チャネル"),
         ("Telegram, Discord, Slack, Microsoft Teams, Nextcloud Talk, Zulip and e-mail, in English, Traditional Chinese or Japanese.",
          "Telegram、Discord、Slack、Microsoft Teams、Nextcloud Talk、Zulip 與 Email，可用英文、繁體中文或日文。",
          "Telegram、Discord、Slack、Microsoft Teams、Nextcloud Talk、Zulip、メールに、英語・繁体字中国語・日本語で。")),
        ("▣", ("Web UI and CLI", "網頁介面與 CLI", "Web 画面と CLI"),
         ("Light and dark themes in three languages, plus the <code>glogarch</code> command for scripts; both use the same database.",
          "三種語言、淺色與深色主題，另有 <code>glogarch</code> 指令可寫指令碼；兩者共用同一個資料庫。",
          "3 言語・ライト／ダークテーマ、スクリプト用の <code>glogarch</code> コマンド。どちらも同じデータベースを使います。")),
        ("◎", ("Sized from this host", "依本機實測給規格建議", "このホストから推奨サイズ"),
         ("Reads the Graylog and OpenSearch JVMs running here, their heaps and swap in use, and says how much RAM and how many cores the VM needs.",
          "讀取本機上 Graylog 與 OpenSearch 的 JVM、heap 與正在使用的 swap，建議主機需要多少記憶體與核心。",
          "ここで動く Graylog と OpenSearch の JVM・ヒープ・使用中のスワップを読み、VM に必要なメモリとコア数を示します。")),
        ("⟲", ("Safe upgrades", "安全升級", "安全なアップグレード"),
         ("An upgrade backs up the database first, keeps every schedule running, never shortens a retention, and has an offline bundle for closed networks.",
          "升級前先備份資料庫，所有排程照常執行、不會縮短保留期；封閉網路另有離線安裝包。",
          "アップグレードは先に DB をバックアップし、スケジュールを止めず、保持期間を短くしません。閉域網用のオフラインバンドルもあります。")),
    ]
    cards = "".join(card(ic, t(*h), t(*b)) for ic, h, b in F)
    return section("features", t("Built to run quietly for years", "為長期穩定運作而設計", "何年も静かに動き続けるために"),
                   t("Designed to sit beside a busy Graylog cluster: bounded memory, careful with Graylog's heap, and honest about what it did.",
                     "設計目標是在繁忙的 Graylog 叢集旁安靜運作：記憶體用量有上限、顧及 Graylog 的 heap，做了什麼就如實回報。",
                     "忙しい Graylog クラスタの横で動くことを前提に、メモリ使用量に上限を設け、Graylog のヒープに配慮し、行ったことを正直に報告します。"),
                   f'<div class="grid">{cards}</div>')


def flow():
    L = lambda *a: a  # noqa: E731
    d = D(1040, 400, L("Archive and restore: how records move", "歸檔與還原：記錄怎麼流動", "アーカイブとリストア：レコードの流れ"))
    d.box(20, 40, 190, 70, "ext", L("Source Graylog", "來源 Graylog", "取り出し元の Graylog"), L("REST API · OpenSearch · Data Node", "REST API・OpenSearch・Data Node", "REST API・OpenSearch・Data Node"))
    d.box(290, 40, 200, 70, "core", L("Export", "匯出", "エクスポート"), L("hourly chunks, streamed to disk", "以小時為單位，邊讀邊寫入", "1 時間単位、逐次書き込み"))
    d.box(570, 40, 200, 70, "file", L("Archive files", "歸檔檔案", "アーカイブファイル"), mono=".json.gz · SHA256 · HMAC")
    d.box(830, 40, 190, 70, "svc", L("Verify and retention", "驗證與保留期", "検証と保持期間"), L("scheduled re-check, cleanup", "定期重新驗證、清理", "定期再検証、クリーンアップ"))
    d.box(570, 160, 200, 60, "file", L("Archive index", "歸檔索引", "アーカイブ索引"), L("SQLite: time ranges, field types", "SQLite：時間範圍、欄位型別", "SQLite：時間範囲、フィールド型"))
    d.box(570, 290, 200, 70, "core", L("Preflight", "匯入預檢", "事前チェック"), L("capacity, retention, mapping conflicts", "容量、保留期、mapping 衝突", "容量、保持期間、マッピング衝突"))
    d.box(290, 268, 200, 48, "svc", L("GELF input", "GELF input", "GELF 入力"), L("full Graylog processing", "完整經過 Graylog 處理", "Graylog の処理をすべて通す"))
    d.box(290, 332, 200, 48, "svc", L("OpenSearch Bulk", "OpenSearch Bulk", "OpenSearch Bulk"), L("exactly as archived, 5–10× faster", "原樣寫回，快 5～10 倍", "元のまま、5〜10 倍速"))
    d.box(20, 290, 190, 70, "ext", L("Target Graylog", "目標 Graylog", "戻し先の Graylog"), L("any Graylog 6 / 7", "任何 Graylog 6／7", "任意の Graylog 6／7"))
    d.edge("M210,75 L290,75", "main", L("records", "記錄", "レコード"), 250, 67)
    d.edge("M490,75 L570,75", "main", L("write", "寫入", "書き込み"), 530, 67)
    d.edge("M770,75 L830,75", label=L("check", "檢查", "確認"), lx=800, ly=67)
    d.edge("M440,110 L440,190 L570,190", label=L("record coverage", "記下涵蓋範圍", "範囲を記録"), lx=505, ly=182, w=120)
    d.edge("M570,205 L390,205 L390,110", "dash", L("skip covered time", "跳過已歸檔的時間", "取得済みの時間は飛ばす"), 480, 222, w=150)
    d.edge("M770,75 L800,75 L800,325 L770,325", "main", L("import", "匯入", "インポート"), 806, 210, anchor="start")
    d.edge("M670,220 L670,290", label=L("field types", "欄位型別", "フィールド型"), lx=676, ly=262, anchor="start")
    d.edge("M570,312 L490,292", "main")
    d.edge("M570,338 L490,356", "main")
    d.edge("M290,292 L210,315", "main")
    d.edge("M290,356 L210,340", "main")
    d.edge("M115,290 L115,250 L530,250 L530,290 L570,300", "dash", L("reconcile: indexer failures, documents written", "核對：indexer 失敗數、實際寫入筆數", "照合：indexer の失敗数、書き込み件数"), 320, 243, w=320)
    legend = [("l main", t("records", "記錄", "レコード")), ("l dash", t("checks and coverage", "檢查與涵蓋範圍", "確認と範囲")),
              ("k-core", t("jt-glogarch", "jt-glogarch", "jt-glogarch")), ("k-file", t("files and database", "檔案與資料庫", "ファイルと DB")),
              ("k-ext", t("Graylog", "Graylog", "Graylog"))]
    fig = d.render("fig-flow", legend)
    exp = steps([
        (t("Pick", "選擇", "選ぶ"), t("A schedule or a manual run picks the server, the time window and the streams or index sets.",
                                        "排程或手動執行指定伺服器、時間範圍與串流或索引集。", "スケジュールか手動実行で、サーバー・時間範囲・ストリームまたはインデックスセットを選びます。")),
        (t("Plan", "規劃", "計画"), t("Covered time is subtracted; holes left by earlier runs are queued first.",
                                       "扣掉已歸檔的時間，先排入先前留下的空缺。", "取得済みの時間を除き、以前の実行で残った欠けを先に並べます。")),
        (t("Read", "讀取", "読む"), t("Page by page from the API or index by index from OpenSearch, pausing whenever Graylog is under load.",
                                       "從 API 逐頁、或從 OpenSearch 逐索引讀取，Graylog 吃緊時自動暫停。", "API からページごと、または OpenSearch からインデックスごとに読み、Graylog に負荷がかかれば一時停止します。")),
        (t("Write", "寫入", "書く"), t("One <code>.json.gz</code> per hour (rolled at 50 MB), with the field types seen.",
                                        "每小時一個 <code>.json.gz</code>（滿 50 MB 換檔），同時記下看到的欄位型別。", "1 時間ごとに <code>.json.gz</code>（50 MB で切り替え）、見えたフィールド型も記録します。")),
        (t("Seal", "封存", "封印"), t("SHA256 (and HMAC when enabled) is computed and the hour is recorded as covered.",
                                       "計算 SHA256（啟用時加上 HMAC），並把這一小時記為已涵蓋。", "SHA256（有効なら HMAC も）を計算し、その 1 時間を取得済みとして記録します。")),
        (t("Report", "回報", "報告"), t("The job history and a notification say what was archived, refilled, or left for OpenSearch Direct.",
                                         "作業歷程與通知會說明歸檔了什麼、補了哪些空缺、哪些要改用 OpenSearch Direct。", "ジョブ履歴と通知が、アーカイブした内容・埋めた欠け・OpenSearch Direct に回すべき箇所を伝えます。")),
    ])
    body = (fig + f'<h3 class="flow-h">{t("One export", "一次匯出", "1 回のエクスポート")}</h3>' + exp)
    return section("flow", t("From Graylog to a file, and back", "從 Graylog 到檔案，再回到 Graylog", "Graylog からファイルへ、そして Graylog へ"),
                   t("Two ways out and two ways back, freely combined; a switch between modes never stores the same records twice.",
                     "兩種匯出、兩種匯入可自由搭配；切換模式也不會把同一批記錄存兩次。",
                     "2 つのエクスポートと 2 つのインポートを自由に組み合わせられます。モードを切り替えても同じレコードを二重に保存しません。"),
                   body, alt=True)


def security():
    st = steps([
        (t("Count", "統計", "集計"), t("Fixed aggregations in Graylog: failed and successful logins, IDS alerts, WAF records. Counts only, never message text.",
                                        "在 Graylog 跑固定的聚合查詢：登入失敗與成功、IDS 告警、WAF 記錄。只讀筆數，不讀訊息內容。",
                                        "Graylog で固定の集計：ログインの失敗と成功、IDS アラート、WAF 記録。件数だけで、本文は読みません。")),
        (t("Detect", "偵測", "検知"), t("Brute force, password spraying, web scans, silent sources, unusual volume, new login sources and your Sigma rules.",
                                         "暴力破解、密碼噴灑、網站掃描、來源停止傳送、記錄量異常、帳號從新來源登入，以及您的 Sigma 規則。",
                                         "総当たり、パスワードスプレー、Web スキャン、送信停止、ログ量の異常、新しい送信元からのログイン、そしてお手持ちの Sigma ルール。")),
        (t("Filter", "排除", "除外"), t("Suppressions for known sources or networks; what a WAF blocked stays quiet unless it is a flood.",
                                         "已知來源或網段可設定排除；WAF 已擋下的請求不會通知，除非數量很大。",
                                         "既知の送信元やネットワークは抑制できます。WAF が遮断したものは、大量でない限り通知しません。")),
        (t("Enrich", "補充", "補足"), t("Who reported it, MITRE ATT&amp;CK techniques, threat intelligence lists, asset criticality and a risk score.",
                                         "回報來源、MITRE ATT&amp;CK 技術、威脅情資清單、資產重要性與風險分數。",
                                         "報告元、MITRE ATT&amp;CK のテクニック、脅威インテリジェンス、資産の重要度とリスクスコア。")),
        (t("Notify", "通知", "通知"), t("New or escalated incidents go to your channels, with a link back to the incident.",
                                         "新的或升級的事件送到通知管道，並附上回到該事件的連結。",
                                         "新規または深刻度の上がったインシデントを、インシデントへのリンク付きで通知します。")),
        (t("Investigate", "調查", "調査"), t("An AI verdict from fixed evidence queries, cases with a timeline, and a weekly summary.",
                                              "以固定的證據查詢產生 AI 判斷、附時間軸的調查案件，以及每週摘要。",
                                              "固定の証拠クエリに基づく AI 判定、タイムライン付きの調査ケース、週次サマリー。")),
    ])
    left = ticks([
        t("Off by default: an upgrade never starts querying a site's Graylog", "預設關閉：升級不會自己開始查詢站台的 Graylog",
          "既定は無効：アップグレードで勝手に Graylog への問い合わせを始めません"),
        t("A coverage table shows which fields are missing, so a quiet network is not mistaken for a safe one",
          "「涵蓋狀況」表列出缺少的欄位，避免把收不到資料誤認為安全",
          "カバレッジ表が欠けているフィールドを示し、データが来ないことを安全と取り違えません"),
        t("Field names follow your parsing: a field map, with a button that finds the fields in your data",
          "欄位名稱依您的解析而定：可設定欄位對照，並有按鈕從實際資料找出欄位",
          "フィールド名は解析に合わせます。フィールド対応表と、実データからフィールドを探すボタンがあります"),
        t("Sigma rules are converted to Graylog queries; a rule that cannot be converted exactly is refused, never approximated",
          "Sigma 規則轉成 Graylog 查詢；無法精確轉換的規則會被拒絕，絕不近似",
          "Sigma ルールは Graylog クエリに変換し、正確に変換できないルールは近似せず拒否します"),
        t("The SigmaHQ rule library can be downloaded and kept up to date, with the fields each rule needs checked against your Graylog",
          "可下載並自動更新 SigmaHQ 規則庫，並對照您的 Graylog 檢查每條規則需要的欄位",
          "SigmaHQ のルールライブラリをダウンロード・自動更新でき、各ルールに必要なフィールドを Graylog と照合します"),
    ])
    body = st + f'<div class="two top"><div><h3>{t("What it does and does not do", "它會做與不會做的事", "すること・しないこと")}</h3>{left}</div>' \
                f'<div class="reccard"><h3>{t("Where the evidence comes from", "證據從哪裡來", "証拠の出どころ")}</h3>' \
                f'<p>{t("The AI analysis of an incident does not let the model choose queries: jt-glogarch runs fixed queries scoped to the incident (counts, top values, successful logins of the same source, a few sample messages) and asks for one JSON verdict. Addresses in the answer that are not in the evidence are flagged.", "資安事件的 AI 分析不讓模型自己決定查詢：jt-glogarch 只執行限定在該事件範圍內的固定查詢（筆數、前幾名的值、同一來源的成功登入、少量範例訊息），並要求模型回覆一份 JSON 判斷。回覆中出現證據裡沒有的位址會被標示出來。", "インシデントの AI 分析では、モデルにクエリを選ばせません。jt-glogarch がインシデントの範囲に限った固定クエリ（件数、上位の値、同じ送信元の成功ログイン、少数のサンプル）を実行し、JSON の判定を 1 つ求めます。証拠にないアドレスが回答に出ると印を付けます。")}</p></div></div>'
    return section("security", t("A security center for Graylog Open", "Graylog Open 的資安中心", "Graylog Open のセキュリティセンター"),
                   t("Turns what Graylog already collects into incidents you can work through, without sending logs anywhere.",
                     "把 Graylog 已經收到的記錄整理成可以逐一處理的資安事件，記錄不會送往任何地方。",
                     "Graylog がすでに集めているログを、順に対処できるインシデントにまとめます。ログをどこにも送りません。"), body)


def ai():
    L = lambda *a: a  # noqa: E731
    d = D(1000, 330, L("AI chat: who asks what", "智慧問答：誰向誰問了什麼", "AI チャット：誰が何を問い合わせるか"))
    d.box(20, 130, 160, 64, "ext", L("You", "您", "あなた"), L("a question in any language", "用任何語言發問", "どの言語でも質問"))
    d.box(260, 126, 200, 72, "core", L("AI chat", "智慧問答", "AI チャット"), L("budgets · loop guard · paging", "用量控制・防止重複・分頁", "予算・ループ防止・ページング"))
    d.box(540, 30, 210, 64, "svc", L("LLM server", "LLM 伺服器", "LLM サーバー"), L("OpenAI-compatible or Claude API", "OpenAI 相容或 Claude API", "OpenAI 互換または Claude API"))
    d.box(540, 230, 210, 64, "core", L("Read-only tools", "唯讀工具", "読み取り専用ツール"), L("as your own Graylog account", "以您自己的 Graylog 帳號", "あなた自身の Graylog アカウントで"))
    d.box(820, 230, 160, 64, "ext", L("Graylog", "Graylog", "Graylog"), L("aggregations, counts, messages", "聚合、計數、訊息", "集計・件数・メッセージ"))
    d.box(820, 126, 160, 72, "ext", L("External AI", "外部 AI", "外部の AI"), L("MCP client, Graylog token", "MCP 用戶端、Graylog token", "MCP クライアント、Graylog トークン"))
    d.box(260, 250, 200, 56, "file", L("Answer and its queries", "答案與它用的查詢", "回答と使ったクエリ"), L("dashboard · PDF · case", "看板・PDF・調查案件", "ダッシュボード・PDF・ケース"))
    d.edge("M180,162 L260,162", "main", L("question", "問題", "質問"), 220, 154)
    d.edge("M460,140 L500,140 L500,62 L540,62", "main", L("prompt", "提示", "プロンプト"), 506, 100, anchor="start")
    d.edge("M540,80 L430,80 L430,126", "", L("tool calls", "工具呼叫", "ツール呼び出し"), 424, 74, anchor="end")
    d.edge("M460,184 L500,184 L500,262 L540,262", label=L("audited", "記入稽核", "監査に記録"), lx=506, ly=230, anchor="start")
    d.edge("M750,262 L820,262", "main", L("read only", "唯讀", "読み取りのみ"), 785, 254)
    d.edge("M900,198 L900,215 L700,215 L700,230", label=L("/mcp", "/mcp", "/mcp"), lx=800, ly=209)
    d.edge("M360,198 L360,250")
    fig = d.render("fig-ai")
    left = ticks([
        t("Counts, breakdowns, time buckets and message patterns are computed by Graylog first; a result too big for the model is kept and read page by page, never cut",
          "計數、分組、時間分布與訊息樣式由 Graylog 先算好；放不下的結果保留下來分頁讀取，絕不截斷",
          "件数・内訳・時間分布・メッセージの型は先に Graylog が計算し、大きすぎる結果は保持してページごとに読み、切り捨てません"),
        t("Under every answer: each query, its time range, how many records and how long it took, with a link that opens it in Graylog",
          "每則答案下方列出每次查詢、時間範圍、筆數與花費時間，並可在 Graylog 以同樣條件開啟",
          "各回答の下に、クエリ・時間範囲・件数・所要時間と、同じ条件で Graylog を開くリンクを表示します"),
        t("From an answer: a real Graylog dashboard, a summary PDF with its charts re-queried from Graylog, or an investigation case",
          "可從答案建立真正的 Graylog 看板、圖表重新向 Graylog 查詢的摘要 PDF，或轉存為調查案件",
          "回答から、本物の Graylog ダッシュボード、グラフを Graylog に問い直した要約 PDF、調査ケースを作れます"),
        t("HTML dashboards and Mermaid diagrams the model writes open in a sandbox that cannot reach the network or jt-glogarch",
          "模型寫的 HTML 看板與 Mermaid 圖在沙箱中預覽，無法連網、也無法讀取 jt-glogarch",
          "モデルが書いた HTML ダッシュボードや Mermaid 図は、ネットワークにも jt-glogarch にも届かないサンドボックスで表示します"),
        t("Internal LLM servers only by default; an external service must be allowed explicitly and is audited",
          "預設只允許內網的 LLM；要用外部服務必須明確開啟並記入稽核",
          "既定では社内の LLM のみ。外部サービスは明示的に許可が必要で、監査に記録します"),
    ])
    shots = f'<div class="shots two-shots">{shot("11_ai_chat", t("Breakdowns computed by Graylog, with the query under the answer", "分組統計由 Graylog 計算，答案下方附上查詢", "内訳は Graylog が計算し、回答の下にクエリ"))}' \
            f'{shot("12_ai_preview", t("A dashboard the model wrote, previewed beside the chat", "模型寫的看板在旁邊預覽", "モデルが書いたダッシュボードを横でプレビュー"))}</div>'
    body = fig + f'<div class="two top"><div>{left}</div><div>{shots}</div></div>'
    return section("ai", t("Ask Graylog in plain language", "用自然語言問 Graylog", "Graylog に自然な言葉で聞く"),
                   t("The model queries Graylog through read-only tools as the signed-in user; every tool call is audited. Off by default.",
                     "模型以登入者自己的 Graylog 帳號、透過唯讀工具查詢，每次工具呼叫都記入稽核。預設關閉。",
                     "モデルはサインインしたユーザー自身の Graylog アカウントで、読み取り専用ツールを通して問い合わせ、各呼び出しを監査に記録します。既定は無効です。"),
                   body, alt=True)


def audit():
    L = lambda *a: a  # noqa: E731
    d = D(960, 250, L("Operation audit: an independent trail", "行為稽核：獨立的操作軌跡", "操作監査：独立した記録"))
    d.box(20, 96, 170, 60, "ext", L("Graylog users", "Graylog 使用者", "Graylog ユーザー"), L("browser · API token", "瀏覽器・API token", "ブラウザ・API トークン"))
    d.box(270, 96, 170, 60, "svc", L("nginx", "nginx", "nginx"), L("in front of Graylog", "擋在 Graylog 前面", "Graylog の前段"))
    d.box(520, 20, 180, 60, "ext", L("Graylog", "Graylog", "Graylog"))
    d.box(520, 170, 180, 60, "core", L("Audit listener", "稽核接收器", "監査リスナー"), mono="UDP 8991")
    d.box(780, 170, 160, 60, "file", L("Audit records", "稽核紀錄", "監査記録"), L("own retention (180 days)", "獨立保留期（180 天）", "独自の保持期間（180 日）"))
    d.box(780, 20, 160, 60, "svc", L("Alerts", "即時告警", "即時アラート"), L("sensitive operations", "敏感操作", "重要操作"))
    d.edge("M190,126 L270,126", "main", L("every request", "每個請求", "すべての要求"), 230, 118)
    d.edge("M440,110 L480,110 L480,50 L520,50", "main", L("proxied", "轉送", "転送"), 486, 80, anchor="start")
    d.edge("M440,142 L480,142 L480,200 L520,200", label=L("access log via syslog", "以 syslog 送出存取記錄", "syslog でアクセスログ"), lx=486, ly=176, anchor="start", w=120)
    d.edge("M700,200 L780,200", label=L("classified", "分類後寫入", "分類して保存"), lx=740, ly=192)
    d.edge("M700,186 L740,186 L740,50 L780,50", label=L("notify", "通知", "通知"), lx=746, ly=120, anchor="start")
    d.edge("M610,170 L610,80", "dash", L("user and resource names", "解析使用者與資源名稱", "ユーザー名・リソース名を解決"), 616, 130, anchor="start", w=150)
    fig = d.render("fig-audit")
    left = ticks([
        t("Basic auth, API tokens, browser sessions and cookies are all resolved back to the real Graylog user name",
          "Basic Auth、API token、瀏覽器 session 與 Cookie 全部解析回真正的 Graylog 使用者名稱",
          "Basic 認証・API トークン・ブラウザのセッション・Cookie を、すべて実際の Graylog ユーザー名に解決します"),
        t("More than 60 kinds of operations classified: streams, pipelines, users, searches, dashboards, content packs, lookup tables…",
          "60 種以上的操作分類：串流、管線、使用者、搜尋、看板、內容套件、查找表……",
          "60 種類以上の操作を分類：ストリーム、パイプライン、ユーザー、検索、ダッシュボード、コンテンツパック、ルックアップテーブル…"),
        t("Sensitive operations notify at once; a silent syslog path while Graylog is up raises an alert",
          "敏感操作即時通知；Graylog 正常但收不到 syslog 時也會告警",
          "重要操作は即時に通知し、Graylog が動いているのに syslog が届かなければアラートを出します"),
        t("Kept in jt-glogarch's database, which Graylog administrators cannot reach",
          "存在 jt-glogarch 的資料庫，Graylog 管理者無法存取",
          "Graylog 管理者が触れない jt-glogarch のデータベースに保存します"),
    ])
    body = fig + f'<div class="two top"><div>{left}</div><div>{shot("5_op_audit", t("Filter by user, method, path, status, time or sensitive only", "可依使用者、方法、路徑、狀態碼、時間或只看敏感操作篩選", "ユーザー・メソッド・パス・ステータス・時間・重要操作のみで絞り込み"))}</div></div>'
    return section("audit", t("Who did what in Graylog", "誰在 Graylog 做了什麼", "誰が Graylog で何をしたか"),
                   t("Regulations ask for an administrators' trail. Graylog admins can delete Graylog's own; they cannot delete this one.",
                     "法規要求保留管理者操作軌跡。Graylog 管理者刪得掉 Graylog 自己的稽核紀錄，但刪不到這一份。",
                     "法令は管理者操作の記録を求めます。Graylog 管理者は Graylog 自身の記録を消せますが、この記録は消せません。"), body)


def reports():
    left = ticks([
        t("<b>Rebuild</b>: each widget becomes a native chart (world map, donut, trends, heatmaps), long windows sliced and merged exactly",
          "<b>重現版</b>：每個小工具重建為原生圖表（世界地圖、甜甜圈、趨勢、熱度圖），長時間範圍分段查詢後精確合併",
          "<b>再構成</b>：各ウィジェットをネイティブなグラフ（世界地図、ドーナツ、推移、ヒートマップ）にし、長い期間は分割して正確に結合"),
        t("<b>Screenshot</b>: a real browser captures every dashboard tab, cut between widget rows",
          "<b>截圖版</b>：以真正的瀏覽器擷取每個看板分頁，在小工具列之間分頁",
          "<b>スクリーンショット</b>：本物のブラウザで各タブを撮影し、ウィジェットの行の間で改ページ"),
        t("Cron schedules, e-mail delivery, your logo, a tiled watermark and a SHA-256 fingerprint on every PDF",
          "Cron 排程、Email 寄送、自訂 logo、平鋪浮水印，每份 PDF 都有 SHA-256 指紋",
          "cron スケジュール、メール送信、ロゴ、タイル状の透かし、各 PDF に SHA-256 の指紋"),
        t("Long reports show their progress while they run", "產製較久的報表會即時顯示進度", "時間のかかるレポートは進捗を表示します"),
    ])
    shots = (f'<div class="shots two-shots">{shot("7_reports", t("Reports from Graylog dashboards", "從 Graylog 看板產生報表", "Graylog ダッシュボードからレポート"))}'
             f'<figure><a class="shotlink" href="reports/wazuh_rebuild_en.png" data-shot-fixed="1" data-report="rebuild">'
             f'<img class="shot" src="reports/wazuh_rebuild_en.png" alt="" loading="lazy"></a>'
             f'<figcaption>{t("A rebuilt report (click to page through it)", "重現版報表（點一下可翻頁）", "再構成レポート（クリックでページ送り）")}</figcaption></figure></div>')
    body = f'<div class="two top"><div>{left}</div><div>{shots}</div></div>'
    return section("reports", t("PDF reports from Graylog dashboards", "從 Graylog 看板產製 PDF 報表", "Graylog ダッシュボードから PDF レポート"),
                   t("Branded multi-page reports, rebuilt from the data or captured from the screen.",
                     "品牌化的多頁報表，可依資料重建，也可直接截取畫面。",
                     "ブランド付きの複数ページのレポートを、データから再構成するか画面から撮影します。"), body, alt=True)


PACKS = [("Apache HTTP Server", "Apache HTTP Server", "Apache HTTP Server"), ("FortiADC", "FortiADC", "FortiADC"),
         ("FortiWAN", "FortiWAN", "FortiWAN"), ("Linux SSH and sudo logins", "Linux 登入與 SSH", "Linux の SSH と sudo ログイン"),
         ("Microsoft DNS Server", "Microsoft DNS Server", "Microsoft DNS Server"), ("NetFlow", "NetFlow", "NetFlow"),
         ("PCAP packet analysis", "PCAP 封包分析", "PCAP パケット分析"), ("Proxmox VE", "Proxmox VE", "Proxmox VE"),
         ("QNAP NAS", "QNAP NAS", "QNAP NAS"), ("SQL Server", "SQL Server", "SQL Server"), ("Synology NAS", "Synology NAS", "Synology NAS"),
         ("Windows Active Directory", "Windows Active Directory", "Windows Active Directory"),
         ("Windows logon events", "Windows 登入事件", "Windows ログオンイベント")]


def packs():
    chips = "".join(f'<li>{t(*p)}</li>' for p in PACKS)
    left = ticks([
        t("See, edit, install, uninstall, download and upload the content packs of each Graylog, and what an install would change before it runs",
          "檢視、修改、安裝、解除安裝、下載與上傳每台 Graylog 的內容套件，安裝前先看會改變什麼",
          "各 Graylog のコンテンツパックを表示・編集・インストール・アンインストール・ダウンロード・アップロードし、実行前に変更内容を確認できます"),
        t("A download is a ZIP with the pack and a guide for a new install, an upgrade and an uninstall, in the page's language",
          "下載為 ZIP，內含套件與新安裝、升級、解除安裝說明，語言依頁面而定",
          "ダウンロードは ZIP で、パックと新規インストール・アップグレード・アンインストールの手順書（画面の言語）が入っています"),
        t("Nothing leaves with an e-mail address, URL or credential inside until you decide to strip or keep it",
          "內含 email、網址或帳密的套件，必須先決定移除或保留才能匯出",
          "メールアドレス・URL・認証情報を含むパックは、削除か保持かを決めるまで出せません"),
        t("Packs converted for older Graylog versions where an export would not install as is",
          "匯出的套件無法直接裝到較舊版本時，會先轉換",
          "エクスポートがそのまま入らない古い Graylog 向けに変換します"),
    ])
    lib = (f'<div class="pack-list"><div class="pack-list-head"><strong>{t("13 Jason Tools packs ship with jt-glogarch", "jt-glogarch 隨附 13 個 Jason Tools 套件", "jt-glogarch に付属する Jason Tools のパック（13 個）")}</strong></div>'
           f'<ul class="pack-chips">{chips}</ul><p class="pack-list-note">{t("Pipelines into GIM fields, dashboards and alerts; no pack touches another pack’s records. Other packs are provided by Jason Tools separately and are not part of this repository.", "管線解析成 GIM 欄位，附看板與告警，套件之間互不影響。其他套件由 Jason Tools 另行提供，不隨本專案原始碼發布。", "パイプラインで GIM フィールドに解析し、ダッシュボードとアラート付き。パック同士は互いのレコードに触れません。その他のパックは Jason Tools が別途提供し、このリポジトリには含まれません。")}</p></div>')
    shots = (f'<div class="shots two-shots">{shot("9_packs", t("The library: dashboards, pipelines and rules per pack", "套件庫：每個套件的看板、管線與規則數", "ライブラリ：パックごとのダッシュボード・パイプライン・ルール数"))}'
             f'{shot("10_pack_dashboard", t("Dashboard preview before installing (illustrative shapes, no query runs)", "安裝前預覽看板（圖形只是示意，不執行查詢）", "インストール前にダッシュボードをプレビュー（図は例示、クエリは実行しません）"))}</div>')
    body = f'<div class="two top"><div>{left}</div><div>{shots}</div></div>{lib}'
    return section("packs", t("Content packs", "內容套件", "コンテンツパック"),
                   t("Know what a pack contains before it reaches Graylog.", "套件裝進 Graylog 之前，先知道裡面有什麼。",
                     "パックが Graylog に入る前に、中身を確認できます。"), body)


def notify_integrate():
    chips = "".join(f'<span class="chip">{c}</span>' for c in ("Telegram", "Discord", "Slack", "Microsoft Teams", "Nextcloud Talk", "Zulip", "E-mail"))
    n = ticks([
        t("Each event can be switched on or off: export, import, cleanup, verify, errors, disk outlook, security incidents, the weekly summary",
          "每種事件可個別開關：匯出、匯入、清理、驗證、錯誤、磁碟預估、資安事件、每週摘要",
          "イベントごとにオン／オフ：エクスポート、インポート、クリーンアップ、検証、エラー、ディスク見通し、セキュリティインシデント、週次サマリー"),
        t("Messages in English, Traditional Chinese or Japanese; security notifications are laid out for phones",
          "訊息可用英文、繁體中文或日文；資安通知針對手機排版",
          "メッセージは英語・繁体字中国語・日本語。セキュリティ通知はスマートフォン向けにレイアウト"),
        t("Log text quoted in a notification is always plain text: it can never become a link or markup",
          "通知裡引用的記錄內容一律是純文字，不會變成連結或格式",
          "通知に引用するログの文字列は常にプレーンテキストで、リンクや書式にはなりません"),
    ])
    left = f'<div><h2>{t("Notified where you already are", "在您常用的地方收到通知", "いつもの場所で通知を受け取る")}</h2><p class="sub">{t("One list of channels for every kind of message.", "所有訊息共用一份通知管道清單。", "すべての通知で 1 つのチャネル一覧を使います。")}</p><div class="chips">{chips}</div>{n}</div>'
    notif = f'<section id="notify"><div class="wrap two">{shot("6_notify", "", "")}{left}</div></section>\n'
    I = [("◈", ("Graylog", "Graylog", "Graylog"),
          ("REST API for export, alerting, packs and dashboards; GELF TCP input for import; logins with Graylog accounts (Admin role by default).",
           "以 REST API 匯出、管理告警、套件與看板；以 GELF TCP input 匯入；用 Graylog 帳號登入（預設需 Admin 角色）。",
           "エクスポート・アラート・パック・ダッシュボードは REST API、インポートは GELF TCP 入力。Graylog アカウントでログイン（既定は Admin ロール）。")),
         ("⇄", ("OpenSearch and Data Node", "OpenSearch 與 Data Node", "OpenSearch と Data Node"),
          ("OpenSearch 2.x and 3.x directly for fast export and Bulk import, with host failover; Graylog 7 Data Node through a certificate from Graylog.",
           "直接連 OpenSearch 2.x、3.x 做快速匯出與 Bulk 匯入，可多主機容錯；Graylog 7 Data Node 透過 Graylog 簽發的憑證連線。",
           "高速エクスポートと Bulk インポートでは OpenSearch 2.x／3.x に直接接続（ホストのフェイルオーバーあり）。Graylog 7 Data Node は Graylog 発行の証明書で接続。")),
         ("≣", ("nginx", "nginx", "nginx"),
          ("The reverse proxy in front of Graylog sends its access log by syslog; the web UI gives you the exact log format to paste.",
           "Graylog 前面的反向代理以 syslog 送出存取記錄；網頁介面提供可直接貼上的記錄格式設定。",
           "Graylog の前段のリバースプロキシが syslog でアクセスログを送ります。貼り付けるだけのログ形式を Web 画面が提示します。")),
         ("✦", ("LLM servers", "LLM 伺服器", "LLM サーバー"),
          ("llama.cpp, vLLM, LM Studio, Ollama or any OpenAI-compatible server, and the Claude API; several at once, picked per question.",
           "llama.cpp、vLLM、LM Studio、Ollama 或任何 OpenAI 相容伺服器，以及 Claude API；可同時設定多台、逐題選用。",
           "llama.cpp、vLLM、LM Studio、Ollama などの OpenAI 互換サーバーと Claude API。複数を設定し、質問ごとに選べます。")),
         ("⌘", ("MCP clients", "MCP 用戶端", "MCP クライアント"),
          ("External AI tools use the same read-only Graylog tools at <code>/mcp</code> with a Graylog token, rate-limited and audited.",
           "外部 AI 工具可用 Graylog token 透過 <code>/mcp</code> 使用同一組唯讀工具，有頻率限制並記入稽核。",
           "外部の AI ツールは Graylog トークンで <code>/mcp</code> から同じ読み取り専用ツールを使えます（レート制限・監査あり）。")),
         ("⊕", ("Public feeds (optional)", "公開情資（選用）", "公開フィード（任意）"),
          ("Spamhaus DROP, Tor exit nodes and abuse.ch Feodo for threat intelligence, and the SigmaHQ rule library. All off until you enable them.",
           "威脅情資使用 Spamhaus DROP、Tor 出口節點、abuse.ch Feodo，另有 SigmaHQ 規則庫；全部預設關閉，需自行啟用。",
           "脅威インテリジェンスに Spamhaus DROP、Tor 出口ノード、abuse.ch Feodo、さらに SigmaHQ ルールライブラリ。すべて有効にするまでオフです。"))]
    integ = section("integrate", t("Works with what you already run", "和現有系統一起運作", "今ある仕組みと一緒に動く"),
                    t("Everything it talks to is listed here; nothing else is contacted.", "會連線的對象都列在這裡，不會連到其他地方。",
                      "接続先はここに挙げたものだけで、それ以外には接続しません。"),
                    f'<div class="grid three">{"".join(card(ic, t(*h), t(*b)) for ic, h, b in I)}</div>', alt=True)
    return notif + integ


def secdesign():
    S = [("⚿", ("Least privilege", "最小權限", "最小権限"),
          ("Runs as its own <code>jt-glogarch</code> user under systemd; the web UI is HTTPS on 8990 with a self-signed certificate you can replace.",
           "以專屬的 <code>jt-glogarch</code> 使用者在 systemd 下執行；網頁介面為 8990 port 的 HTTPS，自簽憑證可替換。",
           "専用の <code>jt-glogarch</code> ユーザーで systemd の下で動き、Web 画面は 8990 番の HTTPS（自己署名証明書は差し替え可）。")),
         ("⚇", ("Logins with Graylog roles", "以 Graylog 角色登入", "Graylog のロールでログイン"),
          ("Valid Graylog credentials are not enough: the account needs an allowed role (Admin by default). A local backup account works when Graylog is down.",
           "Graylog 帳密正確還不夠，帳號必須有允許的角色（預設 Admin）；Graylog 無法連線時可用本機備用帳號。",
           "Graylog の認証情報が正しいだけでは不十分で、許可されたロール（既定は Admin）が必要です。Graylog 停止時はローカルの予備アカウントを使えます。")),
         ("⛨", ("Secrets stay secret", "機密不外洩", "秘密は秘密のまま")),
         ("✓", ("Scanned every release", "每次發版都掃描", "リリースごとにスキャン"),
          ("Static analysis (Bandit), an OWASP ZAP scan of the web UI, whole-tree checks for known failure classes, and a CycloneDX SBOM.",
           "靜態分析（Bandit）、對網頁介面的 OWASP ZAP 掃描、針對已知錯誤類型的全專案檢查，以及 CycloneDX SBOM。",
           "静的解析（Bandit）、Web 画面への OWASP ZAP スキャン、既知の不具合パターンの全体チェック、CycloneDX の SBOM。")),
         ("◌", ("Off until you turn it on", "預設關閉", "有効にするまでオフ"),
          ("Security analysis, AI chat, MCP, threat intelligence and the Sigma library are all off by default: an upgrade never starts them.",
           "資安分析、智慧問答、MCP、威脅情資與 Sigma 規則庫都預設關閉，升級也不會自動開啟。",
           "セキュリティ分析、AI チャット、MCP、脅威インテリジェンス、Sigma ライブラリはすべて既定でオフで、アップグレードでも有効になりません。")),
         ("⌂", ("Data stays inside", "資料留在內部", "データは内部に"),
          ("Logs are never sent to a third party. LLM servers are internal by default; previews run sandboxed without network access.",
           "記錄不會送給第三方。LLM 伺服器預設限內網；預覽在無法連網的沙箱中執行。",
           "ログを第三者に送りません。LLM サーバーは既定で社内のみ、プレビューはネットワークに出られないサンドボックスで動きます。"))]
    S[2] = ("⛨", ("Secrets stay secret", "機密不外洩", "秘密は秘密のまま"),
            ("Passwords and tokens are stripped from job notes, audit details and errors before they are stored, and never sent back to the browser.",
             "密碼與 token 在寫入作業紀錄、稽核細節與錯誤訊息前會先遮蔽，也不會回傳給瀏覽器。",
             "パスワードやトークンは、ジョブの記録・監査の詳細・エラーに保存する前に取り除き、ブラウザにも返しません。"))
    return section("secdesign", t("Secure by design", "安全設計", "セキュリティ設計"),
                   t("The tool holds credentials to your logging platform, so it is built and checked accordingly.",
                     "這個工具持有記錄平台的帳密，因此依此標準設計與檢查。",
                     "ログ基盤の認証情報を持つツールなので、それにふさわしく作り、検査しています。"),
                   f'<div class="grid">{"".join(card(ic, t(*h), t(*b)) for ic, h, b in S)}</div>')


def screens():
    S = [("1_dashboard", ("Dashboard: sparklines, servers, recent jobs, disk outlook", "儀表板：迷你趨勢、伺服器、最近作業、磁碟預估", "ダッシュボード：推移、サーバー、最近のジョブ、ディスク見通し")),
         ("2_archives", ("Archives: filter, batch import, timeline", "歸檔清單：篩選、批次匯入、時間軸", "アーカイブ一覧：絞り込み、一括インポート、タイムライン")),
         ("3_jobs", ("Job history: live progress, elapsed time, cancel", "作業歷程：即時進度、耗時、取消", "ジョブ履歴：進捗、経過時間、キャンセル")),
         ("4_schedules", ("Schedules: cron editor, run now", "排程作業：Cron 編輯、立即執行", "スケジュール：cron 編集、今すぐ実行")),
         ("8_search", ("Record search inside archives", "在歸檔中搜尋記錄", "アーカイブ内の記録検索")),
         ("8_search_expanded", ("One record, every field, where it came from", "單筆記錄的所有欄位與來源檔案", "1 件のレコードの全フィールドと出どころ"))]
    figs = "".join(shot(n, t(*c)) for n, c in S)
    return section("screens", t("Screens", "畫面", "画面"),
                   t("Light and dark themes, English, Traditional Chinese and Japanese. Click to enlarge.",
                     "淺色與深色主題，英文、繁體中文、日文介面。點一下可放大。",
                     "ライト／ダークテーマ、英語・繁体字中国語・日本語。クリックで拡大します。"),
                   f'<div class="shots">{figs}</div>', alt=True)


def install():
    q = code([(t("# clone, then let the installer create the user, the service and a certificate", "# 取得原始碼，安裝程式會建立使用者、服務與憑證", "# 取得すると、インストーラがユーザー・サービス・証明書を作ります"),),
              "sudo git clone https://github.com/jasoncheng7115/jt-glogarch.git /opt/jt-glogarch",
              "sudo bash /opt/jt-glogarch/deploy/install.sh"])
    up = code([(t("# backs up the database first, then upgrades and checks the service", "# 先備份資料庫，再升級並檢查服務", "# 先に DB をバックアップし、アップグレードしてサービスを確認"),),
               "sudo bash /opt/jt-glogarch/deploy/upgrade.sh"])
    off = code([(t("# where there is internet (same Python and CPU type as the target)", "# 在可上網處（Python 與 CPU 需與目標相同）", "# インターネットに出られる所で（Python と CPU は対象と同じ）"),),
                "bash scripts/build-offline-bundle.sh",
                (t("# on the closed-network host, after checking the sha256", "# 在封閉網路主機核對 sha256 後", "# 閉域網のホストで sha256 を確認してから"),),
                "sudo bash install-offline.sh      # " + "first install",
                "sudo bash upgrade-offline.sh      # " + "upgrade"])
    blocks = [
        ("c-install", "↓", t("Install", "安裝", "インストール"),
         t("Linux with Python 3.10 or newer, pip and git. The web UI starts on HTTPS port 8990 and a setup wizard asks for the Graylog connection.",
           "Linux，Python 3.10 以上、pip 與 git。網頁介面在 HTTPS 8990 port 啟動，設定精靈會引導連線 Graylog。",
           "Python 3.10 以上・pip・git のある Linux。Web 画面は HTTPS 8990 番で起動し、セットアップウィザードが Graylog への接続を案内します。"),
         q, [t("Program: <code>/opt/jt-glogarch</code>, service <code>jt-glogarch</code>", "程式：<code>/opt/jt-glogarch</code>，服務 <code>jt-glogarch</code>", "プログラム：<code>/opt/jt-glogarch</code>、サービス <code>jt-glogarch</code>"),
             t("Settings: <code>/opt/jt-glogarch/config.yaml</code>", "設定檔：<code>/opt/jt-glogarch/config.yaml</code>", "設定：<code>/opt/jt-glogarch/config.yaml</code>"),
             t("Archives: <code>/data/graylog-archives</code> (any mounted path)", "歸檔：<code>/data/graylog-archives</code>（可為任何掛載路徑）", "アーカイブ：<code>/data/graylog-archives</code>（任意のマウント先）"),
             t("Logs: <code>journalctl -u jt-glogarch -f</code>", "記錄：<code>journalctl -u jt-glogarch -f</code>", "ログ：<code>journalctl -u jt-glogarch -f</code>")]),
        ("c-upgrade", "↻", t("Upgrade", "升級", "アップグレード"),
         t("Upgrades never lose data, never leave the service unusable and never stop scheduled archiving; each release is tested against state written by older ones.",
           "升級絕不遺失資料、絕不讓服務無法使用、絕不中斷排程歸檔；每一版都以舊版寫出的狀態實測。",
           "アップグレードはデータを失わず、サービスを使えなくせず、スケジュールされたアーカイブを止めません。各リリースは旧版が書いた状態で試験しています。"),
         up, [t("An Ubuntu 22.04 → 24.04 upgrade underneath is handled: the steps before the reinstall need only bash and Python's standard library",
                "底下的 Ubuntu 22.04 → 24.04 升級也考慮在內：重新安裝前的步驟只需要 bash 與 Python 標準函式庫",
                "下での Ubuntu 22.04 → 24.04 アップグレードにも対応：再インストール前の手順は bash と Python 標準ライブラリだけで動きます"),
              t("Stopped at <code>Not possible to fast-forward</code>? See the FAQ in the README: one <code>git reset</code> fixes clones made before 2026-09-13",
                "停在 <code>Not possible to fast-forward</code>？請看 README 的常見問題：2026-09-13 之前的 clone 需要一次 <code>git reset</code>",
                "<code>Not possible to fast-forward</code> で止まったら README の FAQ を参照。2026-09-13 より前の clone は一度 <code>git reset</code> が必要です")]),
        ("c-offline", "⇢", t("Closed networks", "封閉網路", "閉域網"),
         t("Build a bundle where there is internet access and carry it in: the program, every dependency wheel and the PDF engine's browser, installed with no network at all.",
           "在可上網處建立安裝包再帶進去：程式、所有相依套件與 PDF 引擎用的瀏覽器，全程不需連網即可安裝。",
           "インターネットに出られる場所でバンドルを作って持ち込みます。プログラム、すべての依存 wheel、PDF エンジンのブラウザを、ネットワークなしでインストールします。"),
         off, [t("The bundle carries its own SBOM with a SHA-256 for every file", "安裝包附有自己的 SBOM，每個檔案都有 SHA-256", "バンドルには各ファイルの SHA-256 を含む専用の SBOM が付きます"),
               t("It cannot carry the operating system libraries Chromium needs (libnss3, libgbm1…); the installer tells you which are missing",
                 "無法附帶 Chromium 需要的作業系統函式庫（libnss3、libgbm1…）；安裝程式會列出缺少的項目",
                 "Chromium が必要とする OS のライブラリ（libnss3、libgbm1…）は含められません。インストーラが不足分を示します")]),
    ]
    out = []
    for cls, ic, h, d_, c, items in blocks:
        out.append(f'<div class="iblock {cls}"><div class="ihead"><span class="ic">{ic}</span><div><h3>{h}</h3><p>{d_}</p></div></div>{c}{ticks(items)}</div>')
    note = (f'<p class="guide-note">{t("Step-by-step setup, every setting and the FAQ are in the README:", "逐步設定、所有設定項目與常見問題請見 README：", "手順・全設定・FAQ は README にあります：")} '
            f'<a class="readme-link" href="{GH}#readme">README</a> · <a href="{GH}/blob/main/CONFIG.md" class="cfg-link">CONFIG</a> · '
            f'<a href="{GH}/blob/main/TESTING.md" class="test-link">TESTING</a></p>')
    return section("install", t("Install, upgrade and closed networks", "安裝、升級與封閉網路", "インストール、アップグレード、閉域網"),
                   t("One installer for online and offline installs; the service runs as soon as it finishes.",
                     "線上與離線共用同一個安裝程式，完成後服務即開始執行。",
                     "オンラインとオフラインで同じインストーラを使い、終わればすぐにサービスが動きます。"),
                   note + f'<div class="inst">{"".join(out)}</div>')


def specs():
    S = [("▣", ("Host", "主機", "ホスト"), ("Linux with systemd", "具 systemd 的 Linux", "systemd のある Linux"),
          [("Ubuntu 22.04 / 24.04, Debian 12", "Ubuntu 22.04／24.04、Debian 12", "Ubuntu 22.04／24.04、Debian 12"),
           ("Python 3.10 or newer", "Python 3.10 以上", "Python 3.10 以上"),
           ("4 cores for archiving alone, 8 when Graylog shares the VM", "只做歸檔 4 核心，與 Graylog 同機 8 核心", "アーカイブのみ 4 コア、Graylog と同居なら 8 コア")]),
         ("☰", ("Graylog", "Graylog", "Graylog"), ("measured on 6.3 to 7.2", "於 6.3～7.2 實測", "6.3〜7.2 で実測"),
          [("Graylog Open 6.x and 7.x", "Graylog Open 6.x 與 7.x", "Graylog Open 6.x と 7.x"),
           ("OpenSearch 2.x and 3.x; Graylog 7 Data Node (beta)", "OpenSearch 2.x 與 3.x；Graylog 7 Data Node（beta）", "OpenSearch 2.x と 3.x、Graylog 7 Data Node（ベータ）"),
           ("A GELF TCP input for imports (port 32202 by default)", "匯入需 GELF TCP input（預設 32202 port）", "インポートには GELF TCP 入力（既定 32202 番）")]),
         ("◉", ("Ports", "連接埠", "ポート"), ("what listens here", "本機監聽的連接埠", "ここで待ち受けるもの"),
          [("8990/tcp: web UI and API (HTTPS)", "8990/tcp：網頁介面與 API（HTTPS）", "8990/tcp：Web 画面と API（HTTPS）"),
           ("8991/udp: nginx syslog for the operation audit", "8991/udp：行為稽核接收 nginx 的 syslog", "8991/udp：操作監査用の nginx syslog"),
           ("Outbound: Graylog, OpenSearch, your LLM and notification channels", "對外：Graylog、OpenSearch、您的 LLM 與通知管道", "外向き：Graylog、OpenSearch、LLM、通知チャネル")]),
         ("✎", ("Storage", "儲存", "ストレージ"), ("about 10× smaller than the indexed data", "約為索引資料的十分之一", "インデックス済みデータの約 1/10"),
          [("gzip-compressed JSON, one file per hour, 50 MB each at most", "gzip 壓縮的 JSON，每小時一個檔案，單檔最多 50 MB", "gzip 圧縮の JSON、1 時間 1 ファイル、最大 50 MB"),
           ("SQLite database with WAL; backups with <code>glogarch db-backup</code>", "SQLite 資料庫（WAL）；以 <code>glogarch db-backup</code> 備份", "SQLite（WAL）、<code>glogarch db-backup</code> でバックアップ"),
           ("The index can be rebuilt from the files: <code>glogarch db-rebuild</code>", "索引可由檔案重建：<code>glogarch db-rebuild</code>", "索引はファイルから再構築可能：<code>glogarch db-rebuild</code>")]),
         ("⧉", ("Languages", "語言", "言語"), ("interface, notifications and reports", "介面、通知與報表", "画面・通知・レポート"),
          [("English, Traditional Chinese, Japanese", "英文、繁體中文、日文", "英語・繁体字中国語・日本語"),
           ("Light and dark themes", "淺色與深色主題", "ライト／ダークテーマ"),
           ("PDF reports with CJK fonts", "PDF 報表支援中日文字型", "CJK フォント対応の PDF レポート")]),
         ("⇲", ("License", "授權", "ライセンス"), ("AGPL-3.0-or-later", "AGPL-3.0-or-later", "AGPL-3.0-or-later"),
          [("Source on GitHub, changelog in three languages", "原始碼在 GitHub，變更紀錄有三種語言", "ソースは GitHub、変更履歴は 3 言語"),
           ("SBOM (CycloneDX 1.5) with every release", "每版附 SBOM（CycloneDX 1.5）", "各リリースに SBOM（CycloneDX 1.5）"),
           ("Bundled assets keep their own licences (Iconoir MIT, Natural Earth public domain)", "隨附資產保留各自授權（Iconoir MIT、Natural Earth 公有領域）", "同梱物はそれぞれのライセンス（Iconoir MIT、Natural Earth パブリックドメイン）")])]
    cards = "".join(card_list(ic, t(*h), t(*by), [t(*x) for x in items]) for ic, h, by, items in S)
    return section("specs", t("Specifications", "規格", "仕様"),
                   t("What it needs and what it opens.", "需要什麼、開放什麼。", "必要なものと、開くもの。"), f'<div class="grid specs">{cards}</div>')


def build():
    PREFIX["p"] = "h"
    title = reg("title_home", "jt-glogarch — Graylog Open Archive", "jt-glogarch — Graylog Open 歸檔工具", "jt-glogarch — Graylog Open アーカイブ")
    desc = reg("desc_home", "Archive and restore for Graylog Open 6.x and 7.x, with an independent audit trail, PDF reports, content packs, security incidents and AI chat.",
               "Graylog Open 6.x／7.x 的歸檔與還原工具，另有獨立行為稽核、PDF 報表、內容套件、資安事件與智慧問答。",
               "Graylog Open 6.x／7.x のアーカイブとリストア。独立した操作監査、PDF レポート、コンテンツパック、セキュリティインシデント、AI チャットも。")
    body = (header(nav()) + hero() + modes() + fit() + uses() + features() + flow() + security() + ai() + audit() + reports() + packs()
            + notify_integrate() + secdesign() + screens() + install() + specs() + dialogs() + footer())
    return page(title, desc, body, "home")
