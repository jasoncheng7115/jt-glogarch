# 變更紀錄

jt-glogarch 所有重要變更皆記錄於此檔案。

## [1.3.0] - 2026-04-09

### 新增 — OpenSearch Bulk 匯入模式

新的高速匯入模式,完全跳過 Graylog 直接寫入 OpenSearch 的 `_bulk` API。
已用 CLI 端對端驗證通過。

- **`glogarch/import_/bulk.py`** — `BulkImporter` 類別
  - 讀歸檔、組 NDJSON bulk 請求、解析每筆文件的成功/失敗結果
  - 每日 index 命名:`<pattern>_YYYY_MM_DD`,依每筆文件的 timestamp 決定
  - 預先建立目標 index(Graylog 環境的 OpenSearch 通常設
    `action.auto_create_index = false`,bulk write 必須先建)
  - 三種去重策略:`id`(用 `gl2_message_id` 當 `_id`,重複匯入會
    overwrite)、`none`、`fail`
  - 遇到 OpenSearch 429(限流)指數退讓
  - 注入 marker 欄位 `_jt_glogarch_imported_at` 方便追蹤
- **Preflight 擴充**支援 bulk 模式:
  - `auto_detect_opensearch_url()` — 從 Graylog API URL 推導 OpenSearch URL
    (port 9000 → 9200)並偵測連線
  - `find_or_create_index_set()` — 自動在 Graylog 上建立對應 prefix 的
    Index Set,讓還原資料立刻可在 Graylog UI 上搜尋
  - `apply_bulk_template()` — 寫一個 OpenSearch index template,設
    `total_fields.limit: 10000` 並把所有有字串值的欄位 pin 為 `keyword`
  - `PreflightChecker.run(mode='bulk', ...)` 分支:跳過 Graylog deflector
    cycle(無意義),改為寫 bulk template + 建立 Graylog index set
- **`Importer`** 接受 `mode='bulk'` + `bulk_importer` 參數,在 GELF send
  迴圈前分支
- **Web UI Modal 重構**含模式選擇器:
  - 兩張 radio 卡:`GELF (Graylog Pipeline)`(預設)與
    `OpenSearch Bulk (~5-10x)`
  - Bulk mode 顯示橘色警告區塊,清楚說明跳過了什麼
  - Bulk-mode 專屬欄位:目標 index pattern、去重策略、批次大小、
    OpenSearch 自動偵測 checkbox + 手動 URL/帳密
  - 切換模式時欄位群組 hide/show,內容保留;Graylog API 帳密兩 mode 共用
  - 新增 23 個 i18n 字串(中英)
  - 新 CSS:`.mode-selector`、`.mode-option`、`.bulk-warning`
- **CLI `import` 命令**新增選項:
  - `--mode [gelf|bulk]`
  - `--target-os-url`、`--target-os-username`、`--target-os-password`
  - `--target-index-pattern`(預設 `jt_restored`)
  - `--dedup-strategy [id|none|fail]`
  - `--batch-docs`(預設 5000)
- **權衡點清楚記錄** — bulk mode 跳過所有 Graylog 處理(Pipeline、
  Extractors、Stream routing、Alerts)。只適合「歷史資料原樣還原」場景。

### 新增 — 匯出時保留 gl2_message_id(歸檔格式 v1.1)

為了讓 bulk 匯入能做精準去重,兩個 exporter 都改為**保留** `gl2_message_id`
欄位,而不是跟其他 `gl2_*` 一起被剝除。其他 `gl2_*` 欄位
(`gl2_source_input`、`gl2_processing_timestamp` 等)仍會被剝除,因為它們
指向來源 cluster 的節點/輸入,在目標 cluster 不存在。

- **`opensearch/client.py`** — `iter_index_docs` 保留 `gl2_message_id`
- **`graylog/search.py`** — `_extract_messages` 保留 `gl2_message_id`
- **`ArchiveMetadata.version`** 從 `"1.0"` 升到 `"1.1"` 標記格式變更。
  舊版(v1.0)歸檔仍可正常透過 GELF 匯入;v1.0 歸檔做 bulk 匯入時退化
  為「不去重」(自動生成 `_id`)。
- GELF 匯入路徑不受影響 — Graylog 收到訊息後會自己重新生成所有
  `gl2_*` 欄位,包含全新的 `gl2_message_id`。

### 新增 — IMPORTING 狀態 startup recovery

`ArchiveDB.connect()` 啟動時會自動把卡在 `importing` 狀態的歸檔回復到
`completed`,並 log 警告。原因:當匯入 process 被砍(`-9`、OOM、crash)時,
importer 的 `finally` block 沒跑完,歸檔被永久標記為 `importing`,在 Web UI
歸檔清單上看不到。現在會在每次 service 重啟或 DB connect 時自動修復。

### 新增 — UI polish(延續 v1.2.0)

- **GELF 主機 → Graylog API URL 自動帶入** — 在 GELF 主機輸入 IP 時,
  若 API URL 欄位沒被使用者改過,會自動填入 `http://<ip>:9000`。跟 GELF
  port 自動切換是同一套 `data-user-edited` 旗標機制。
- **重新打開正在跑的匯入對話框** — 如果使用者在匯入過程中不小心點外面
  把 modal 關掉,點側邊欄的執行中作業指示燈會把 modal 重新叫回進度模式
  (form 隱藏、進度條 + 控制按鈕顯示)。SSE + 輪詢的監聽器在 modal 關閉
  期間會繼續在背景跑。
  - `closeImportModal()` 在 `_activeImportJobId` 還在時 early-return,
    完全不 reset state
  - 新函式 `reopenActiveImportModal()`
  - 側邊欄 `checkRunningJobs()` 加上 `cursor: pointer` + `onclick`
- **匯入對話框 i18n 補完** — `Pause`/`Resume` 按鈕、`Speed:` 標籤、
  `sending`/`paused` phase 文字、`Journal: X (slow)` badge、以及「匯入
  工作已啟動」訊息中的 `(N archives)` 都改為依語言切換。
- **`completed_with_failures` job badge** — 作業歷程表格上,當 `completed`
  作業有 `error_message` 且包含「Compliance violation」時,改顯示橘色
  shield-checkmark 圖示。hover 顯示完整 violation 訊息。純前端邏輯,
  不需要 DB schema 變更。

### 修正 — v1.3.0 CLI 測試時發現的 bug

- **`def list(...)` shadow Python builtin** in `cli/main.py` — `list` CLI
  命令原本定義為 `def list(...)`,這會把一個 click Command 物件放到 module
  level 的 `list` 名稱上,**蓋掉 builtin**。在 `import_cmd` 內,這行
  `ids = list(archive_id) if archive_id else None` 實際變成在呼叫 click
  Command,觸發詭異的 `TypeError: object of type 'int' has no len()`
  錯誤(來自 click 的 argument parser)。修法:rename 為
  `def list_cmd(...)` 用 `@cli.command("list")` 保留 CLI 命令名。
- **Bulk path 撞到 `index_not_found_exception`** — Graylog 環境的
  OpenSearch 通常設 `action.auto_create_index = false`,所以 `_bulk` API
  無法自動建立每日目標 index。`BulkImporter` 現在會在 pre-flight 階段
  掃所有歸檔的 timestamp,把每個需要的每日 index 名稱列出來,逐個 PUT
  建立(idempotent:遇到 400 `resource_already_exists_exception` 視為
  成功)。
- **`pip install` 在版本未變時是 no-op** — 如果改完程式但 `pyproject.toml`
  的版本沒變,`pip install` 會誤判為「已安裝」而跳過,執行的還是舊程式
  碼。改完程式後一律要用 `--force-reinstall --no-deps`。

## [1.2.0] - 2026-04-09

### 新增 — 合規匯入流程（零遺失保證）

本次重大更新導入「零訊息遺失 + 零 indexer failures」的匯入合規流程。已透過
67 份歸檔、828 萬筆訊息端對端驗證通過。

- **歸檔時記錄欄位 schema** — `archives.field_schema` 欄位（JSON）儲存
  `{欄位名稱: [出現過的型別]}`。OpenSearch 與 API 兩個 exporter 都會在
  `StreamingArchiveWriter` 寫入訊息時順便累積（每筆 ~10 µs，可忽略）。
  匯入 preflight 直接讀 DB，不需要重新掃檔
- **`glogarch/import_/preflight.py`** 新模組，匯入前**先**做完所有防範：
  1. 驗證目標 Graylog API 帳密
  2. **Cluster health check** — 對方 OpenSearch RED 直接 abort
  3. **GELF input 檢查** — 必須存在於指定 port 且為 RUNNING 狀態。同時警告
     `override_source`（會蓋掉原始 source）、`decompress_size_limit`、
     `max_message_size` 等設定問題
  4. **Journal 壓力檢查** — 對方 journal 已有 >10 萬未處理就警告
  5. **Capacity 檢查** — 讀對方 index set 的 rotation/retention strategy，
     估算這次匯入會用到幾份 index；如果**刪除型 retention 會把剛匯入的資料
     刪掉**就直接 abort
  6. **欄位 schema 收集** — 從 DB `field_schema` 欄位讀（毫秒）。1.2.0 之前
     的舊歸檔自動 fallback 解壓掃檔，並 backfill 進 DB
  7. **衝突偵測** — 只 pin 兩種情況的欄位為 keyword：（a）歸檔內同時有
     numeric 與 string 值（內部矛盾，必衝突），或（b）對方目前的 mapping
     是 numeric 而歸檔有字串值。避免過度 pin 撞到 1000 欄位上限
  8. **OpenSearch 欄位上限突破** — 自動 PUT 一個名為 `jt-glogarch-field-limit`
     的 OpenSearch index template，把 `index.mapping.total_fields.limit`
     拉到 10000，徹底解決「Limit of total fields [1000] has been exceeded」
     導致 index rotation 失敗的問題
  9. **套用 custom mappings + cycle** — 透過 Graylog
     `PUT /api/system/indices/mappings`（每個欄位一次 PUT、`rotate: false`），
     套完所有衝突欄位後再 cycle 一次 deflector，新 index 才會吃到新 mappings
  10. **等待新 index 啟用** — poll 直到對方準備好接資料
- **匯入後自動對帳** — GELF 送完後自動撈 Graylog `indexer failures` 數字並
  跟匯入前的 baseline 比對。差異 > 0 就把 compliance violation 訊息寫進
  `jobs.error_message`，讓使用者能立即發現
- **強制目標 Graylog API 帳密** — 匯入對話框必填
  `target_api_url` + (`target_api_token` 或 `target_api_username` + `target_api_password`)。
  前後端都會驗證，缺欄位不執行。同一組帳密用於 preflight、journal 監控、對帳
- **通知欄位敏感資料遮罩** — 所有憑證欄位（Bot Token、Chat ID、Webhook URL、SMTP 密碼、Nextcloud token/帳密等）預設以遮罩顯示，欄位右側有眼睛按鈕可切換顯示/隱藏
- **側邊欄 logo 連結** — 點擊側邊欄左上的 `jt-glogarch` 標題會在新分頁開啟專案 GitHub 頁面
- **歸檔時間軸視覺化**（歸檔清單頁面）
  - 每日分布長條圖，高度依記錄數量比例
  - 拖曳選取時間範圍（小時等級精度），自動填入篩選並套用
  - 滑鼠 hover 時有垂直虛線跟隨，整個欄位區都可選取
  - Hover 提示顯示日期、歸檔數、記錄數、檔案大小
  - 清除選取按鈕（永遠保留位置避免版面跳動）
  - 圖表有邊框，accent 色長條，紅色標記無資料日
- **表格載入動畫** — 篩選或重新載入完成時表格會閃爍 accent 色光暈
- **匯入流量控制系統**
  - Web UI 即時暫停/繼續
  - 即時速率調整（批次延遲滑桿）
  - **三種監控模式** 防止目標 Graylog Buffer/Journal 爆掉：
    - 無（手動控制）
    - Graylog API 監控（`/api/system/journal`）
    - SSH 監控（遠端 `du` 檢查 journal 目錄）
  - 依 `uncommitted_journal_entries` 動態調整速率：
    - >10萬 → 延遲加 3 倍
    - >50萬 → 自動暫停 30 秒
    - >100萬 → 停止匯入並通知管理員
- **OpenSearch keep_indices 模式**
  - 排程依「保留最近 N 份 index」而非天數
  - 允許 N 超過目前 index 數量（預留成長空間）
  - UI 顯示 `60 份 Index` 而非 `180 天`
- **儀表板新增第 5 個統計卡片**：歸檔前大小（含 sparkline）
- **Sparkline tooltip**：滑鼠移到長條顯示日期和數值
- **時間軸 tooltip 等寬數字**：數字位數變化時版面不跳動

### 變更 — 合規流程連帶調整
- **匯入對話框重構**：移除 Journal 監控下拉（無/API/SSH）與整個 SSH 監控的程式碼。目標 Graylog API 帳密改為一律必填，一組帳密同時用於 preflight、journal 監控、對帳。
- **GELF 預設改為 TCP / port 32202**（之前是 UDP / 12201）。UDP 仍可選，但 README 明確警告大量匯入時會靜默丟封包。
- **TCP backpressure + Journal 監控** 永遠啟用。匯入時偵測對方 `uncommitted_journal_entries` 超過 50 萬就自動暫停 30 秒，避免擠爆對方 buffer。
- **`POST /api/import`、`POST /api/export`、`POST /api/schedules/{name}/run`** 改為在背景執行緒（`asyncio.run(...)` 包在 `loop.run_in_executor`）跑，主 FastAPI event loop 不再被 gzip / JSON / GELF 的 CPU 工作卡死。Web UI 在百萬筆等級的匯入/匯出期間仍可正常切頁。
- **`ArchiveScheduler._run_export`** 改用 sync wrapper（`_run_export_in_thread`）註冊到 APScheduler，原因同上。
- 壓縮後大小卡片名稱改為「壓縮後」（對比新增的「歸檔前大小」）
- 記錄數顯示格式：`9,458,948 of 9,458,948`（粗體+灰色總數）
- 側邊欄收摺按鈕與 logo 垂直對齊
- 深色主題數字顏色加亮以提升可讀性
- 通知設定：未啟用的管道自動收摺設定欄位
- 通知測試端點繞過事件類型檢查（只要管道啟用就發送）
- 「操作」→「動作」（台灣用語，全 UI 統一）

### 修正 — 合規流程驗證時發現的 bug
- **OpenSearch exporter 跨 index 邊界資料遺失** — `is_time_range_covered()` 會把同一次 OpenSearch run 內的姊妹 index 互相擋住，導致跨越 index rotation 邊界的小時內訊息只寫入其中一個 index 的部分。症狀：某些小時的歸檔筆數明顯偏低。修法：加上 `exclude_stream_id_prefix` 參數，讓跨模式 dedup 只擋跨模式不擋同模式內的姊妹。**這個 bug 造成受影響小時 ~17% 資料遺失**。
- **Web UI 匯入對話框狀態殘留** — `_batchImportIds` 在 POST 後立刻被清空（不論成功失敗），導致匯入失敗後重試時靜悄悄什麼都沒做。修法：清空時機延後到 `closeImportModal()`。
- **Web UI 匯入對話框進度殘影** — 失敗匯入的進度條與錯誤文字會留到下次嘗試。修法：在 `watchJob()` 開頭清空 bar/text。
- **Web UI 匯入對話框重試時 host 還是舊值** — 跟上一條相關，新版會在每次重試時重新讀表單值。
- **OpenSearch 欄位上限被撐爆** — 套用大量 custom field mappings 時，Graylog 自動產生的 index template 超過 OpenSearch 預設的 1000 欄位上限，導致 `Limit of total fields [1000] has been exceeded`，graylog index rotation 失敗。Preflight 現在會自動 PUT 一個 override template `jt-glogarch-field-limit` 把上限拉到 10000。
- **目標端殘留舊 custom field mappings** — preflight 中途失敗會在 Graylog MongoDB 留下半套狀態，影響後續 index rotation。README 補上清理流程。
- FastAPI 路由順序：`/archives/timeline` 須在 `/archives/{archive_id}` 之前（422 錯誤）
- pip install 快取問題：`build/` 目錄導致安裝舊版（改為強制重裝）
- 排程編輯 modal：`keep_indices` 值未在 coverage widget 載入後還原
- 時間軸單擊不再殘留舊選區（會把高亮移到點擊位置 1 小時寬的範圍）
- 時間軸長條高度改用記錄數而非檔案數
- 通知測試被 `_should_send` 事件類型檢查擋住
- 移除 OpenSearch resume point（改為依靠 per-chunk dedup 避免缺口）
- 排程編輯時暫停自動刷新輪詢
- 編輯時模式選擇器被重設的 bug（`initCustomSelects` 競態）
- 匯入對話框：GELF Port 輸入框與 Protocol 下拉選單高度（38px）與位置統一對齊
- 匯入對話框：Graylog API URL / API Token / 帳號 / 密碼 / SSH 主機 / SSH Port / SSH 使用者 / Journal 路徑 等欄位 label 與 placeholder 改為依介面語言切換
- Journal 監控下拉選單：選項標籤（`無（手動控制）` / `Graylog API` / `SSH`）原本永遠顯示英文 — 已在 `i18n.js` 加上 `data-i18n-opt` handler 讓它跟著翻譯
- 通知欄位密碼類欄位改為 `type="password"` 並關閉 autocomplete，避免在共用螢幕上意外曝光
- 所有顯示版本號的位置統一為 v1.2.0（登入頁、側邊欄、套件 metadata、exporter 的 `glogarch_version`）

### 文件
- README 更新含安裝 SOP 改善
- install.sh 安裝前清除 `build/` 快取
- 已在全新 Ubuntu 22.04 LXC 上完整部署驗證
- README/CHANGELOG/`glogarch.service` 內的 repo 網址統一更正為 `https://github.com/jasoncheng7115/jt-glogarch`
- 新增 FAQ 條目：排程未在預期時間執行 → 請確認系統時區與你寫 cron expression 的時區一致（APScheduler 繼承系統時區）

## [1.0.0] - 2026-04-06

### 新增
- **雙模式匯出**：Graylog API + OpenSearch Direct
- **OpenSearch 單次掃描匯出**：整個 index 一次掃描，依小時切分歸檔檔案（速度提升 5 倍）
- **跨模式去重**：切換 API/OpenSearch 模式不會重複匯出
- **GELF UDP 匯入**：新增 UDP 發送器（預設），Web UI 可選擇通訊協定
- **JVM 記憶體保護**：API 匯出時監控 Graylog heap，超過 85% 自動停止並通知管理員
- **驗證排程**：新增「驗證」作業類型，定期 SHA256 完整性檢查
- **歸檔狀態**：新增「損壞」及「遺失」狀態，歸檔清單有對應視覺標示
- **儀表板迷你圖表**：Grafana 風格的 area graph 背景
- **歸檔前大小**：顯示壓縮前原始大小
- **通知語言**：雙語通知訊息（English / 繁體中文）
- **側邊欄收摺**：可收摺側邊欄，狀態持久化
- **作業詳情**：匯出時顯示目前正在處理的 index/chunk
- **耗時欄位**：作業歷程及儀表板顯示執行時間
- **立即執行**：所有排程類型（匯出、清理、驗證）都支援
- **每月排程**：新增「每月第一個週六 03:00」頻率選項

### 變更
- API batch_size：300 -> 1000，delay：200ms -> 5ms（搭配 JVM 記憶體保護）
- OpenSearch batch_size：10,000，delay：2ms
- 匯出/匯入頁面合併至排程作業及歸檔清單
- 「排程匯出」更名為「排程作業」

### 修正
- 排程匯出 0 筆問題（resume point 跨串流汙染）
- OpenSearch 時間戳格式不符
- Web UI 與 DB 的 Job ID 不一致
- 資料庫執行緒安全、XSS 漏洞、權限問題

## [0.7.1] - 2026-03-29

### 新增
- 初始版本，核心功能完成
- Graylog API 匯出（串流寫入）
- OpenSearch 直連匯出（依 index）
- GELF TCP 匯入
- Web 管理介面（7 個頁面）
- CLI 指令、APScheduler、6 種通知管道
- 深色/淺色主題、English/繁體中文 雙語
