# 變更紀錄

jt-glogarch 所有重要變更皆記錄於此檔案。

## [1.7.12] - 2026-05-04

### 修正 — 匯入完成通知一律顯示「耗時：0s」

- Telegram / Discord / Slack / Teams / Nextcloud Talk / Email 各通道的「匯入完成」通知，不論實際跑多久，永遠都顯示 `耗時: 0s` / `Duration: 0s`。在 192.168.1.83 的實機批次測試中，連續匯入五筆規模 502 / 26,221 / 31,769 / 131,944 / 373,258 的歸檔，實際耗時 12 / 14 / 18 / 32 / 102 秒，但每一筆通知都印 `0s`。
- 成因：`notify_import_complete(...)` 函式有 `duration_seconds: float = 0` 參數，但 `glogarch/import_/importer.py` 內兩個呼叫點（Bulk 路徑與 GELF 路徑）都沒有計算、也沒有傳。`Importer.run()` 完全沒有起始時間紀錄。匯出端早就有此計時（`ExportResult.duration_seconds` 在呼叫 `notify_export_complete(...)` 前正確被設定），匯入端漏做。
- 修法：在 `Importer.run()` 開頭記 `_start_time = time.time()`，於 `ImportResult` 加 `duration_seconds: float`，於兩個 `notify_import_complete(...)` 呼叫點前計算 `result.duration_seconds = time.time() - _start_time` 並一併傳入。完全比照匯出端的既有模式。通知文案模板未改 — `{duration}` 預留位置一直都對，只是過去每次都吃到 `0`。

### 修正 — 每次成功發送通知後，journal 都寫一筆「Notification send failed」警告

- `journalctl -u jt-glogarch` 每次發完通知都會多一行 `Notification send failed   error="_make_filtering_bound_logger.<locals>.make_method.<locals>.meth() got multiple values for argument 'event'"`。實際通知有送達，只是這個假錯誤一直噪訊干擾監控。
- 成因：`glogarch/notify/sender.py::send_notification` 中 `log.info("Notification sent", channel=..., event=event.value)`。structlog 的 bound logger 把第一個位置引數 / `event` 關鍵字保留給訊息字串，因此同時傳「Notification sent」和 `event=` 會觸發重複關鍵字錯誤。例外往上拋給 importer，被 importer 的 `try/except` 攔下，當作「通知失敗」記錄到 journal — 但實際訊息其實早送出了。
- 修法：把結構化記錄欄位 `event=` 改名為 `notify_event=`。通知本身從未失敗，只是發送後的 info log 那一行寫不出來而錯印了警告。

## [1.7.11] - 2026-05-03

### 修正 — 行為稽核頁卡片數字看似「不對」，實則沒標清楚時間窗

- `/op-audit` 上方四張卡（`行為數`、`使用者`、`登入失敗`、`敏感行為`）由 `/api/audit/stats?hours=24` 計算，是**最近 24 小時**的統計。下方清單則是分頁的全部歷史。當清單中出現 24 小時前的敏感事件（每筆都帶 `!` 標誌）、但「敏感行為」卡顯示 `0` 時，使用者很合理會誤以為頁面壞掉 — 24h 時間窗的事實原本只寫在卡片的 hover tooltip 裡，多數使用者並不會去 hover。
- 修法：在四張卡上方加一行小字標題「最近 24 小時統計 / Statistics for the last 24 hours」，並把敏感行為卡的 tooltip 也補上「最近 24 小時內」字樣，使四張卡 tooltip 一致。**純標籤調整，無任何程式邏輯或資料變動**。

## [1.7.10] - 2026-05-03

### 修正 — 作業歷程「記錄數」欄位對 verify 與 cleanup 易誤導

- 作業歷程的欄位表頭原本是「記錄數 / Records」，但對 verify 而言該欄顯示的是「歸檔份數」、對 cleanup 而言則是「刪除檔案數」。讀者很容易把「verify 完成 3,454」誤解為「只驗證了 3,454 筆訊息」，而實際上是驗證了 3,454 份歸檔（內含數百萬筆訊息）。
- 修法：表頭改為中性的「處理量 / Processed」，每列依 `job_type` 加上明確單位 — export/import 標「筆 / records」、verify 標「份 / archives」、cleanup 標「個檔 / files」。`formatRecords()` 三個呼叫點都帶入 `j.job_type`。
- 同時把另外 4 處（歸檔時間軸 tooltip、匯出完成提示、行為稽核總筆數）原本借用 `th_messages` 表頭翻譯來顯示「筆」單位的地方，改用獨立的 `unit_records` i18n key，這些地方就不會因為表頭再次更名而連帶受影響。

## [1.7.9] - 2026-05-02

### 修正 — 含星期欄位的排程都差一天觸發（嚴重正確性問題）

- 客戶回報 auto-verify 設為 UI 預設選項「每個月第一個週六 03:00」（cron `0 3 1-7 * 6`），結果 2026-05-02 週六當天並未觸發，下次觸發顯示為 2026-05-03 週日。
- 根因：APScheduler 的 `CronTrigger.from_crontab` 把星期欄位編號為 `0=週一, 6=週日`，但本專案 UI 預設值、README、所有使用者心智模型都依 POSIX cron 慣例 `0=週日, 6=週六`。差一天結果是 `* * * * 6` 跑成週日、`* * * * 0` 跑成週一。受影響的兩個 UI 內建預設值：
  - `0 0 * * 0` 標籤「Weekly (Sunday 00:00)」實際在週一觸發。
  - `0 3 1-7 * 6` 標籤「Monthly (1st Saturday 03:00)」實際在第一個週日觸發。
- 修法：在 `glogarch/scheduler/scheduler.py` 新增 `posix_cron_to_apscheduler()`，把 cron 字串的 dow 欄位先依 POSIX→APScheduler 慣例轉換，再交給 APScheduler。支援單一數字、範圍、列表、萬用字元、步進表達式、星期名稱；轉換後跨週的範圍（例如 POSIX 週五到週一 `5-1` → APS `4-6,0`）會自動在週末邊界拆開。`apply_schedule()`（runtime 註冊）與 `_schedule_to_dict()`（UI 顯示的「下次執行」也是用 cron 算的）統一走這個 helper，所以畫面顯示與實際觸發日從此一致。資料庫中已存的 cron 都依 POSIX 解讀，下次服務啟動就會正確套用。新增 17 條單元測試 `tests/test_posix_cron.py`。
- **對既有排程的影響**：任何有用到星期數字的排程，從今以後會在使用者真正期望的那一天觸發。沒有星期數字的排程（`0 3 * * *`、`0 0 * * *` 等）完全不受影響。先前因為這個 bug 而不知不覺把錯位當作預設行為的客戶，本次更新後實際觸發日會對齊到 cron 字串字面上的意思，沒有資料損失或副作用。

## [1.7.8] - 2026-04-30

### 修正 — 排程頁面把同一筆執行進度顯示在所有匯出排程列

- 只要任一匯出排程正在執行，排程頁所有匯出類型的列都會顯示同一個進度條 / 百分比 / 記錄數。客戶回報情境：一個 `api-export` 排程（mode=API、手動觸發）和一個 `auto-export` 排程（mode=OpenSearch、cron 觸發），啟動其中一個時兩列同時跑同樣的進度。
- 根因：`web/static/js/app.js` 的 `loadSchedules()` 用 `(jobsData.items || []).find(j => j.status === 'running' && j.job_type === 'export' ...)` 找「正在跑的匯出 job」，然後把進度條套到**每一個** `job_type === 'export'` 的列。原因是 `source` 欄位只記到 `"manual:api"` / `"scheduled:opensearch"` 兩段，沒有排程名稱可比對。
- 修法：將 `source` 欄位擴充為三段格式 `"{manual|scheduled}:{api|opensearch}:{schedule_name}"`。
  - `scheduler.py::_run_export_once` 與 `web/routes/api.py::run_schedule_now` 現在都會寫入第三段。
  - `/api/export`（從「立即匯出」頁面執行，不屬於任何排程）保留兩段格式，因此不會把進度沾染到任何排程列。
- 前端：`loadSchedules()` 改為以第三段建立 `runningBySchedule[name]` 字典，只在排程名稱對得上的列顯示進度條。原本另外兩處解析 source 的地方（作業歷程頁的徽章、儀表板最近作業徽章）只看前兩段，第三段被自動忽略，沿用不變。
- 「立即執行」按鈕的可見性維持原本精神：只要有任何匯出在跑，所有列都隱藏（伺服器層級匯出鎖本來就會拒絕並行執行）。

### 修正 — 手動「立即執行」的 verify / cleanup 不會出現在作業歷程

- 在排程頁按 `auto-verify` 或 `auto-cleanup` 的「立即執行」按鈕後，只會寫入 `audit_log` 並更新 `schedules.last_run_at`，完全沒有寫入 `jobs` 表。所以該次執行在作業歷程、儀表板最近作業、以及 `/api/jobs` API 都看不到。
- 修法：`web/routes/api.py::run_schedule_now` 在呼叫 `Cleaner`/`Verifier` 之前先建立 `RUNNING` 狀態的 `JobRecord`，呼叫完成後再依結果轉為 `COMPLETED`（備註欄帶摘要）或 `FAILED`（帶清理過的錯誤訊息）。Source 採用 v1.7.8 統一格式：`manual:cleanup:<name>` / `manual:verify:<name>`。順帶把 cron 觸發的 scheduler.py 的 verify/cleanup source 也升級為 `scheduled:verify:<name>` / `scheduled:cleanup:<name>`，與 export 一致。

## [1.7.7] - 2026-04-30

### 修正 — 切換語言時動態內容未即時更新

- `web/static/js/app.js` 的 `langchange` 事件監聽只重新渲染 `/logs` 與 `/op-audit` 兩個頁面。其他頁面（`/`、`/archives`、`/jobs`、`/schedules`、`/notify-settings`）由 JS 動態 innerHTML 渲染的狀態徽章、表格欄位、Modal 標籤、通知測試結果等都會卡在切換前的語言，使用者必須手動重新整理瀏覽器才會全部更新。
- 修法：擴充監聽器，所有頁面在切換語言時都重新呼叫對應的載入函式，並保留分頁狀態（例如 `archivePage`、`_auditPage`）。
- 同時把四處先前硬寫英文的片段補上 i18n：OpenSearch 連線測試結果（`Connected!` / `Failed:` / `Error:` / `Unknown error` / `Status:` / `Nodes:`）、通知管道測試結果（`OK` / `Failed`）、GELF Port 欄位標籤、排程類型下拉選項（`Export` / `Cleanup` / `Verify`）、以及純資訊提示視窗的 OK 按鈕。新增 i18n key：`btn_ok`、`test_connected`、`test_failed`、`test_error`、`unknown_error`、`result_ok`、`result_failed`、`os_status`、`os_nodes`、`import_gelf_port`、`sched_type_export/cleanup/verify`。

## [1.7.6] - 2026-04-29

### 修正 — 排程的 verify 與 cleanup 不會出現在作業歷程

- `glogarch/scheduler/scheduler.py` 的 `_run_verify` 與 `_run_cleanup` 從未寫入 `jobs` 資料表，只有 export 有紀錄。所以使用者執行 auto-verify 或 auto-cleanup 時，雖然看得到排程「上次執行」更新，但 `/jobs`（作業歷程）卻完全沒有那筆紀錄。
- `_run_export` 的失敗路徑也用了過時的 `db.create_job(job_id, "export", source="scheduled")` 寫法（`create_job()` 改為接受 `JobRecord` 物件之後就已經失效），但因為包在 `try/except` 裡，每次失敗都被靜默吞掉，從未真正寫進歷程。
- 修法：在 `ArchiveScheduler` 新增 `_create_run_job()` / `_finish_run_job()` 兩個 helper，三個排程處理函式統一改走這條路徑。每次排程觸發時先建立 `RUNNING` 紀錄，結束時再轉為 `COMPLETED`（備註欄帶摘要）或 `FAILED`（含清理過的錯誤訊息）。verify 偵測到 corrupted/missing 檔案時會標為 `FAILED`，方便在 UI 上一眼看出。

## [1.7.5] - 2026-04-29

### 修正 — Email 通知設定中非機密欄位被誤設為密碼遮蔽

- 通知設定畫面的 **SMTP 主機**、**SMTP 帳號**、**寄件人** 三個欄位先前都以 `_secret()`（`<input type="password">`）渲染，導致值被點點遮蔽且多了無意義的眼睛切換按鈕。其實只有 SMTP 密碼需要遮蔽。
- 修法：`web/static/js/app.js` — 將上述三個欄位改為一般 `<input type="text">`（仍以 `esc()` 防 XSS）；SMTP 密碼維持遮蔽。

## [1.7.4] - 2026-04-27

### 修正 — Web UI 變更排程須重啟服務才生效（重大）

- **Web UI 新建的 `auto-verify`（或任何自訂排程）永遠不會觸發**，已存在排程的 cron 表達式編輯也會被忽略，直到服務重啟為止。`POST /api/schedules`、`POST /api/schedules/{name}/toggle`、`DELETE /api/schedules/{name}` 三個端點只寫入 SQLite `schedules` 資料表，從未通知正在運行中的 APScheduler。
- Web UI 上的「下次執行」欄位是 `api.py::_schedule_to_dict` 在每次載入時用 cron 表達式即時算出來顯示的，所以 UI 看起來正常，但 APScheduler 內部其實沒註冊任何 job——這個現象掩蓋了問題。
- `ArchiveScheduler.setup()` 只在啟動時被 FastAPI lifespan 呼叫一次，因此唯一能讓 DB 中的新排程被 APScheduler 認識的方法就是 `systemctl restart jt-glogarch`。
- 修法：在 `ArchiveScheduler` 新增 `apply_schedule(sched)` 與 `remove_schedule(name)` 兩個方法，三個排程 API 端點在寫 DB 後立即呼叫，讓變更即刻生效。`setup()` 也一併簡化，所有 DB 記錄統一交由 `apply_schedule()` 處理（DRY），且僅在首次啟動且 DB 無對應記錄時才從 `config.yaml` 建立 `auto-export` / `auto-cleanup` 預設值。

### 修正 — 自訂名稱排程更新錯誤的 `last_run_at`

- `_run_export`、`_run_cleanup`、`_run_verify` 將排程名稱硬編碼為 `"auto-export"` / `"auto-cleanup"` / `"auto-verify"`，導致使用者自訂名稱（例如 `daily-stream-A`）的排程要不就跳過時間戳寫入，要不就覆蓋到錯誤的列。`_run_export_once` 也是從硬編碼的 `"auto-export"` 列讀取 config，使得自訂的匯出排程實際上沿用了 `auto-export` 的模式、天數、串流設定，而非自身的設定。
- 修法：三個處理函式都接受 `schedule_name` 參數；`apply_schedule()` 透過 APScheduler 的 `args=[sched.name]` 機制把實際排程名稱傳入，確保讀取 config 與更新 `last_run_at` 都對應到正確的列。

## [1.7.3] - 2026-04-19

### 修正 — 匯出鎖在早期失敗時未釋放（重大）

- **排程匯出可能永久卡住**。若 `create_job()` 或 `_export_lock[key] = True` 與 `try:` 之間的任何操作拋出例外（如 SQLite 衝突造成的「database is locked」），lock 被設定後就再也無法釋放。所有後續重試以及隔日的排程都會失敗並回報「Export already running」。
- 記錄中可觀察到的模式：第 1 次嘗試「database is locked」，第 2、3 次及後續排程皆「Export already running for 'X'」。
- 同時影響 `glogarch.export.exporter`（API 模式）與 `glogarch.opensearch.exporter`（OpenSearch 模式）。
- 修法：將 job 建立移入 `try:` 區塊內，讓原有的 `finally: _export_lock.pop(...)` 不論例外從何處拋出都能執行。

### 改善 — 行為稽核 server_name fallback 到 syslog hostname

- 當 nginx `server {}` 沒設定 `server_name` 指令時，`$server_name` 為空字串，所有稽核記錄的「伺服器」欄位都會空白。現在會 fallback 使用 syslog envelope 中的 hostname（例如從 `<190>Apr 19 00:07:15 log3 graylog_audit: {...}` 取出 `log3`）。
- nginx 已設 `server_name` 的環境不受影響；fallback 只在 JSON 欄位為空時啟用。

## [1.7.2] - 2026-04-17

### 改善 — JVM 記憶體保護：暫停等待而非直接停止

- API 匯出在 Graylog JVM heap 超過閾值（預設 85%）時**自動暫停**，每 30 秒重新檢查，GC 回收後**自動繼續**。等待 5 分鐘仍未降低才停止。先前是一碰到閾值就直接停止整個匯出。
- 暫停期間進度顯示「JVM heap 87%, paused (waiting for GC)...」。

### 改善 — 心跳監控：主動探測取代被動逾時

- 心跳不再只因「10 分鐘沒收到 syslog」就報警（沒人用 Graylog 時會誤報）。改為每 5 分鐘透過 nginx（HTTPS :443）主動送出探測請求，只有在 HTTP 探測成功但沒收到對應 syslog 時才報警 — 代表 nginx 轉送被關閉。
- nginx URL 自動從 `servers[].url` 推導（相同 host，HTTPS port 443）。

### 改善 — 匯出作業 UX：準確數字與跳過資訊

- OpenSearch 匯出改用 `_count` API 取得準確文件數，不再用 `_cat/indices`（含已刪除/合併的文件，數字偏高）。
- 完成的匯出作業在備註欄顯示跳過資訊：「Skipped 75 indices (already archived)」或「Skipped 4200/4320 chunks (already archived)」。
- 中斷的作業顯示上下文：「Interrupted by service restart (502,202 / 1,397,360 processed, partial files cleaned up)」。
- 排程頁面和側邊欄進度詳情分行顯示。

### 修正 — 排程「立即執行」匯出未更新上次執行時間

### 修正 — 升級腳本：git safe.directory

- `upgrade.sh` 在 `git pull` 前執行 `git config --global --add safe.directory`，避免 `/opt/jt-glogarch` 為 jt-glogarch 使用者所有時出現「dubious ownership」錯誤。

## [1.7.1] - 2026-04-16

### 改善 — 匯出進度 UX

- **掃描/去重階段顯示詳細文字** — OpenSearch 匯出現在會顯示「Scanning 45/88 indices...」、「skipped 75/88 indices (archived)」、「querying graylog_515 (4,651,029 docs)...」，而非空白的 0% 進度。API 匯出在去重跳過階段顯示「skipped 43/4320 (archived)」。
- **Polling fallback 顯示詳情** — SSE 不可用時，polling 進度顯示 `current_detail` 而非「0/?」。

### 改善 — 敏感操作通知去重

- **重複項目合併** — 同一批次中相同的操作（同帳號、同操作、同項目、同狀態碼）合併為一筆並加上「×N」後綴。例如：12 筆相同的 logout-401 合併為一行加上「×12」。

### 修正 — 排程「立即執行」匯出未更新上次執行時間

- 匯出排程按「立即執行」後，完成時更新「上次執行」時間戳。先前只有清理和驗證排程會更新此欄位。

### 修正 — 排程匯出暫態錯誤重試

- 排程匯出遇到暫態錯誤（如「database is locked」）時自動重試最多 3 次（間隔 30 秒）。最終失敗會建立失敗的作業記錄，使其出現在作業歷程中（先前為無聲失敗，僅在系統記錄中可見）。

### 修正 — 無歸檔時稽核清理被跳過

- `Cleaner.cleanup()` 有 early return 導致沒有歸檔檔案符合保留條件時稽核記錄清理也不執行。已重構為稽核清理一律執行。

### 修正 — 稽核保留期限獨立於歸檔

- `op_audit.retention_days`（預設 180）獨立控制稽核記錄清理，與歸檔保留（預設 1095）分開。`upgrade.sh` 為既有安裝自動補上此欄位。

### 修正 — alert.enable / alert.disable 分類

- 事件定義的啟用/停用排程現在分類為 `alert.enable` / `alert.disable`，而非通用的 `alert.modify`，讓使用者在稽核記錄和通知中可區分啟用與停用。

## [1.7.0] - 2026-04-15

### 新增 — 行為稽核（Graylog 合規稽核）

記錄誰在 Graylog 上做了什麼操作，用於合規稽核。記錄完整 request body
（可精確查看變更內容），且記錄獨立於 Graylog（管理員無法刪除稽核記錄）。

**架構：**
- 每台 Graylog 的 nginx 透過 UDP syslog 送出 access log
- jt-glogarch 在 port 8991 接收、解析、分類、存入 SQLite
- IP 白名單自動從 Graylog Cluster API 建立（零設定）
- 白名單式篩選：僅記錄有意義的操作（60+ 種操作類型）
- 背景輪詢、靜態資源、metrics 自動篩除

**帳號解析：**
- Basic Auth → 從 Authorization header 擷取帳號
- Token 認證 → 透過 Graylog 逐使用者 token API 解析
- Session 認證 → Session ID 透過 Graylog Sessions API 解析
- Cookie Session（`$cookie_authentication`）→ 從 nginx log 擷取 session ID，透過 API 解析
- 登入 POST body → 擷取帳號 → 以來源 IP 快取
- 單一使用者環境 → 自動歸屬
- 定期回填無帳號的記錄

**項目名稱解析：**
- Input/Stream/Index Set/Dashboard/Pipeline/Lookup Table ID → 人類可讀名稱
- 從 Graylog API 快取，每 6 分鐘更新

**心跳監控：**
- 偵測稽核無聲失效（Graylog 正常但沒收到 syslog）
- 超過 10 分鐘未收到資料時發送通知

**Web UI「行為稽核」頁面：**
- Dashboard 風格統計卡片 + sparkline 趨勢圖（24h）
- 可篩選表格（時間範圍、帳號、方法、狀態碼、僅敏感操作）
- 詳情 modal（JSON 語法高亮 + 複製按鈕）
- nginx 前置設定說明（語法高亮設定範例）
- 預設啟用；upgrade.sh 自動為舊版新增設定

**通知：**
- `on_sensitive_operation` — 偵測到敏感操作時通知
- `on_audit_alert` — 稽核管道異常時通知
- 各自獨立開關，可在通知設定頁面配置

**安全強化：**
- Session cookie `https_only=True`
- 安全標頭：X-Frame-Options、X-Content-Type-Options、HSTS、Referrer-Policy
- 通知設定密碼遮罩（API 回傳時脫敏）
- 登入錯誤參數白名單驗證
- UDP listener DoS 防護（佇列上限、封包大小限制）
- SSH 指令注入防護（`shlex.quote`）

**設定：**
```yaml
op_audit:
  enabled: true          # 預設啟用
  listen_port: 8991
  max_body_size: 65536
  alert_sensitive: true
  retention_days: 180
```

**文件：**
- `AUDIT-OPERATIONS.md` / `AUDIT-OPERATIONS-zh_TW.md` — 完整 60+ 種追蹤操作清單
- `CONFIG.md` 新增 `op_audit` 區段
- `README.md` — nginx 設定指南 + port 9000 防火牆說明

**測試：** 新增 17 筆測試（parser、帳號解碼、session 認證、敏感分類、DB 操作、通知事件）。

### 修正 — 行為稽核精進

- **移除冗餘的 `search.execute` 記錄** — Graylog 搜尋會產生兩個 API 呼叫：建立/更新搜尋定義（包含查詢語句）+ 執行（僅含 `global_override`）。現在只記錄 `search.create`/`search.update`，後續的 `/execute` 呼叫自動篩除，避免重複。
- **Token 認證帳號解析** — `GET /api/users` 不會回傳實際 token 值。新增 fallback 查詢各使用者的 `GET /api/users/{username}/tokens` 端點（會回傳真實 token 值）。同時新增非同步解析（`_resolve_token_via_api`）處理快取未命中的情況。
- **Cookie Session 解析** — 瀏覽器 session 使用 cookie 而非 Authorization header。nginx log format 新增 `$cookie_authentication` 欄位擷取 Graylog session cookie，listener 從中擷取 session ID 並透過 Graylog Sessions API 解析帳號。無 cookie 時 fallback 至 IP 快取。
- **外部帳號被排除** — `_get_human_users()` 錯誤地排除 LDAP/SSO 帳號（`external=true`），導致單一使用者預設歸屬到錯誤帳號。外部帳號現已納入。
- **搜尋項目欄位顯示原始 URI** — `search.execute` 的 target_name 為空時，UI 會顯示完整的 API URI 路徑。透過移除冗餘的 execute pattern 修正（查詢語句已記錄在 `search.create`/`search.update`）。
- **稽核表格缺少伺服器欄位** — 行為稽核表格新增「伺服器」欄位（位於帳號前面）。
- **認證服務操作未追蹤** — `_KEEP_PATTERNS` 新增 `/api/system/authentication/services/backends`（建立/修改/刪除/啟用/停用）。同時標記為敏感操作。
- **Content Pack 名稱未解析** — `_refresh_resource_cache` 新增從 Graylog API 快取 content pack。`_resolve_target_name` 新增含連字號的 UUID URI 比對。
- **Dashboard 名稱無法透過 /api/dashboards 解析** — 統一 `_resolve_target_name`，讓 `/api/views/` 和 `/api/dashboards/` 路徑共用同一個 view 快取。
- **Lookup adapter/cache 名稱未解析** — `_refresh_resource_cache` 原本只快取 lookup table。新增快取 data adapter（`/api/system/lookup/adapters`）和 cache（`/api/system/lookup/caches`）。
- **稽核保留期限獨立於歸檔保留期限** — `op_audit.retention_days`（預設 180）現在獨立控制稽核記錄清理，與歸檔保留期限（預設 1095 天）分開。先前稽核清理使用歸檔保留設定，且在沒有歸檔時會提前返回。
- **無歸檔可清理時稽核清理被跳過** — `Cleaner.cleanup()` 有一個提前返回，導致沒有歸檔檔案符合保留條件時，稽核記錄清理也不會執行。已重構為稽核清理一律執行。
- **upgrade.sh 自動新增 `retention_days`** — 已有 `op_audit` 設定但缺少 `retention_days` 的舊版安裝，升級時自動補上。

### 修正 — zh_TW 用語

- 損壞 → 損毀（台灣用語）
- 過濾 → 篩選/篩除
- 對象 → 項目
- README cleanup 範例保留天數：60 天 → 1095 天

## [1.6.2] - 2026-04-15

### 新增 — 排程支援多伺服器

匯出排程可指定歸檔來源的 Graylog 伺服器。排程表單新增「Graylog 伺服器」
下拉選單。排程表格在「伺服器 / 模式」欄顯示伺服器名稱。

### 新增 — 終端機風格系統記錄

系統記錄「即時記錄」改為深色終端機背景，依 log level 著色
（ERROR=紅、WARN=橘、info=綠、INFO=白灰、DEBUG=灰、systemd=藍）。

### 修正 — 系統記錄在部分主機顯示「無記錄資料」

`jt-glogarch` 使用者缺少 `systemd-journal` 群組，`journalctl` 回傳空白。
已在 `install.sh` 和 `upgrade.sh` 修正。

### 修正 — OpenSearch 模式說明缺少 Data Node 警告

匯出模式說明文字加上 Data Node 環境不支援此模式的提示。

### 修正 — Modal 拖曳到外面會關閉

所有 modal 只能透過儲存/取消按鈕關閉。

### 修正 — 缺少 pause/close 圖示

ICONS map 加上 `pause` 和 `close` SVG。排程啟用/停用按鈕加 play/pause
圖示。取消按鈕加 close 圖示。

### 修正 — Cleanup/verify 手動執行沒更新「上次執行」

手動觸發的 cleanup 和 verify 排程現在會更新 `last_run_at`。

### 修正 — TEST-RESULTS.md 有 ANSI 亂碼

`run-tests.sh` 加上 `NO_COLOR=1 TERM=dumb` + sed 篩除。

## [1.6.1] - 2026-04-14

### 新增 — 排程支援多伺服器

匯出排程現在可以指定歸檔來源的 Graylog 伺服器，不再只用預設伺服器。
排程表單新增「Graylog 伺服器」下拉選單，列出所有已設定的伺服器。
排程表格在匯出模式旁顯示伺服器名稱。

這讓一台 jt-glogarch 可以歸檔多個 Graylog 叢集 — 每個伺服器建一個排程即可。

### 修正 — Modal 拖曳到外面會關閉

所有 modal（匯入、排程編輯、確認）不再因為滑鼠從 modal 內拖到外面而關閉。
只能透過儲存/取消按鈕關閉。

### 修正 — 啟用/停用按鈕缺少圖示

排程表格的啟用/停用按鈕加上 play/pause 圖示。

## [1.6.0] - 2026-04-14

### 修正 — Code review 發現的問題

- **安全：OpenSearch 測試的 XSS** — `testOpenSearch()` 把 OS 叢集名稱/版本/狀態直接插入 innerHTML 沒有用 `esc()`。已修正。
- **Bug：通知狀態漏掉 Email 管道** — `GET /api/notify/status` 沒有包含 email 管道。只啟用 email 時儀表板顯示「未啟用任何管道」。
- **一致性：`batch_docs` 預設值不一致** — CLI help 寫 5000 但程式用 10000。修正 help 文字 + JS fallback + CLAUDE.md。
- **i18n：statusBadge 硬寫中文** — `corrupted` 和 `missing` 標籤硬寫中文。改用 `t('status_corrupted')` / `t('status_missing')`。
- **記憶體：`_cancel_flags` 沒有清理** — 在 export 和 import 路徑都加上跟 `_job_progress` 一起的清理邏輯（保留最近 50 筆）。

### 新增 — 11 筆回歸測試（`test_recent_fixes.py`）

涵蓋：通知時區、Data Node 偵測、retention 預設值、batch_docs 一致性、Discord 參數、排程顯示、i18n key。

## [1.5.9] - 2026-04-14

### 修正 — 排程表格 OpenSearch 模式沒設 Index 份數時顯示不清

OpenSearch 模式匯出排程若沒設 `keep_indices`（如 auto-export），
設定欄顯示「180 天」容易誤解。改為顯示「180 天（所有 Index）」
以表明匯出該時間範圍內的所有 Index。

## [1.5.8] - 2026-04-14

### 變更 — 預設保留天數從 180 天改為 3 年（1095 天）

180 天對大多數合規場景太短。`retention_days` 預設值從 180 改為
1095（3 年）。變更範圍：config 預設、CLI 範例、JS fallback、
CONFIG 文件、config.yaml.example。

## [1.5.7] - 2026-04-14

### 修正 — 通知時間戳顯示 UTC 而非本地時區

通知（Telegram、Discord 等）的時間戳顯示 UTC
（`2026-04-13 19:23:35 UTC`）。改為使用系統本地時區
（`2026-04-14 03:23:35 CST`）。排程任務通知與測試通知都適用。

### 變更 — Data Node 警告文字調整

匯入/匯出對話框的 Data Node 警告從「不建議使用 Data Node」改為
中性的事實描述：「Data Node 不支援 OpenSearch 直連，請改用
API/GELF 模式」。

## [1.5.6] - 2026-04-14

### 新增 — Graylog 7 Data Node 相容性文件

在 Graylog 7.0.6 + Data Node 7.0.6（管理的 OpenSearch 2.19.3）上
測試 jt-glogarch。主要發現：

- **OpenSearch Direct 匯出：Data Node 環境不支援。** Data Node 使用
  Graylog 自動管理的 TLS 憑證認證，不對外暴露帳密，外部工具無法
  存取 OS port 9200。
- **OpenSearch Bulk 匯入：同樣不支援。**
- **Graylog API 匯出：正常運作。**
- **GELF 匯入：正常運作。**
- Graylog API proxy 只支援有限的唯讀端點（health、indices info），
  不支援 `_search` 或 `_bulk` passthrough。
- 兩份 README 都更新了匯出模式比較表的 Data Node 相容性欄位 +
  使用者注意事項。
- `GET /api/servers` 新增 `has_datanode` 旗標供 UI 偵測並警告使用者。

## [1.5.5] - 2026-04-13

### 修正 — Discord/Slack/Teams/Email 測試通知壞掉

`/notify/test` endpoint 呼叫 `_send_discord(client, cfg, full_msg)` 傳了
3 個參數，但函式簽名要 5 個：`(client, cfg, title, message, ts)`。
Slack、Teams、Email 也有同樣的參數不符。呼叫直接 crash，前端顯示
「尚未啟用任何管道」而非實際錯誤。

- 修正 4 個函式呼叫傳入正確參數
- 新增 `test_notify_test_endpoint.py`（7 筆測試）驗證每個 send 函式的
  參數數量及每個呼叫端的參數清單

## [1.5.4] - 2026-04-13

### 修正 — Graylog API 401 造成下拉選單永遠「載入中...」

`/api/index-sets` 和 `/api/streams` 沒有 catch `HTTPStatusError`。
Graylog 回 401（token 錯誤）時前端下拉選單永遠停在「載入中...」。

- 後端 catch 401 → 回傳 `{"error": "...authentication failed...", "items": []}`
- 後端 catch 連線錯誤 → 回傳 `{"error": "Cannot reach Graylog: ...", "items": []}`
- 前端讀取 `data.error` 顯示在下拉選單裡，不再無限轉圈

### 新增 — 一行指令升級（`deploy/upgrade.sh`）

```bash
cd /opt/jt-glogarch && sudo bash deploy/upgrade.sh
```

自動：DB 備份 → git pull → pip install → 重啟 → 確認 health。
顯示升級前後版本。health 失敗時回傳非零 exit code。
README 升級段落已更新為使用此指令碼。

### 修正 — install.sh systemd 預設是 No

`[y/N]` → `[Y/n]`。按 Enter 現在會安裝 systemd 服務
（之前會跳過，與「5 分鐘安裝」不符）。

### 修正 — `git clone /opt/` 需要 sudo

README 安裝指令加上 `sudo git clone`。

### 修正 — 作者 email 和網站 URL

- Email：`jason@jasontools.com` → `jason@jason.tools`
- Jason Tools URL：`https://jasontools.com` → `https://github.com/jasoncheng7115`

### 新增 — API 錯誤處理 + 升級流程測試

- `test_api_error_handling.py`（4 筆）：index-sets 和 streams 的 401/502/連線失敗
- `test_upgrade_script.py`（7 筆）：指令碼存在、5 步驟、root 檢查、systemd 預設、README 引用

## [1.5.3] - 2026-04-13

### 修正 — 客戶安裝失敗：找不到 pyproject.toml

`git clone` + `pip install /opt/jt-glogarch` 會失敗，因為 GitHub repo
把 `pyproject.toml` 和 `glogarch/` 放在 `src/` 子目錄裡。`pip` 要求它們
在 repo 根目錄。

- `github/src/glogarch/` → 搬到 `github/glogarch/`
- `github/src/pyproject.toml` → 搬到 `github/pyproject.toml`
- 刪除 `github/src/` 目錄
- 更新 `check-version.sh` 和 `CLAUDE.md` 的參照路徑
- 新增 `test_repo_structure.py`（7 筆測試）防止回歸

### 新增 — README 加入升級說明

兩份 README 都加入升級步驟：
`db-backup` → `git pull` → `pip install --force-reinstall` →
`systemctl restart` → 確認 `/api/health`。

### 新增 — 升級模擬測試（`test_upgrade.py`）

4 筆測試：舊 DB 自動升級、舊 config 向下相容、既有歸檔升級後完整保留、
DB 備份有效性。

## [1.5.2] - 2026-04-12

### 新增 — 緊急本機管理員登入

Graylog 離線時 Web UI 完全無法登入（認證委派給 Graylog REST API）。
這在災難復原場景是致命缺陷。

- **`web.localadmin_password_hash`** 設定選項 — 儲存 SHA256 hash。
  Graylog API 連不上且此欄位有設定時，登入頁面接受本機密碼作為
  fallback。帳號必須輸入 `localadmin`。
- **登入頁面回饋** — 三種錯誤狀態：
  - Graylog 拒絕帳密 →「登入失敗」
  - Graylog 離線 + 有設 hash → 橘色警告，提示使用 `localadmin` 帳號
  - Graylog 離線 + 沒設 hash → 紅色錯誤，提示設定 config
- **`glogarch hash-password`** CLI 指令 — 互動式產生 SHA256 hash，
  直接貼入 `config.yaml`。
- **向下相容** — 欄位預設空字串（停用）。舊版設定檔沒有此欄位時
  行為完全不變。
- 登入邏輯：永遠先嘗試 Graylog API。本機 fallback 只在 Graylog
  連不上（連線錯誤/逾時）時啟用，Graylog 拒絕密碼（帳密錯誤）時
  **不會** fallback。

## [1.5.1] - 2026-04-12

### 修正 — 歸檔目錄權限自動修復

以 root 身份執行 `glogarch export`（沒用 `sudo -u jt-glogarch`）會建出
root 擁有的子目錄。之後排程以 `jt-glogarch` 服務帳號執行時就會因為
`PermissionError` 失敗。

- **`ArchiveStorage._fix_dir_ownership()`** — `mkdir` 遇到
  PermissionError 且當前是 root 時，自動把 `base_path` 底下非
  `jt-glogarch` 擁有的目錄 chown 為 `jt-glogarch`。限定只修歸檔目錄，
  不會動到 `base_path` 以上的系統目錄。
- **CLI root 警告** — 以 root 執行任何 `glogarch` 指令時會顯示警告，
  建議使用 `sudo -u jt-glogarch`。

## [1.5.0] - 2026-04-11

### 修正 — OpenSearch `_id` fielddata circuit breaker（嚴重）

排程 OpenSearch 匯出在大 index（650K+ docs）上持續失敗：
`circuit_breaking_exception: [fielddata] Data too large, data for [_id] would be [1.6gb], which is larger than the limit of [1.5gb]`。三個
index（graylog_489、490、492）每晚都失敗。

根因：`search_after` 分頁用 `{"_id": "asc"}` 做 tiebreaker sort。
以 `_id` 排序會強迫 OpenSearch 把整個欄位載入 heap-resident
fielddata — 680K 筆文件 ID 佔了 1.6 GB，超過 circuit breaker 預設
限制。

修法：tiebreaker 從 `_id` 改成 `_doc`（index 寫入順序），零成本，
不需要 fielddata。驗證：graylog_495（680K docs）現在 3m53s 匯出
完成，零錯誤。

### 修正 — OpenSearch 暫態錯誤 retry

`OpenSearchClient._request()` 之前只在連線錯誤（ConnectError /
ConnectTimeout）時重試。HTTP 500、502、503、429 回應直接 raise，
不會重試也不會 failover 到下一台 host。

修法：暫態 HTTP 錯誤會做 exponential backoff retry（最多 3 次，
間隔 1s/2s/4s），耗盡後才 failover 到下一台。非暫態錯誤（4xx）
仍然直接 raise。

### 變更 — 通知格式全面改版

- 內文行拿掉 emoji — 只在標題行放一個狀態 emoji
  （✅ 成功、⚠️ 部分錯誤、❌ 失敗）
- 每個統計值獨立一行，乾淨的 `標籤: 值` 格式
- 錯誤訊息中的長 URL 自動縮為 `<url>`，避免在聊天軟體中斷行
- 匯入通知加上耗時
- 標題範例：`✅ 匯出成功`、`⚠️ 匯出完成（有錯誤）`、`❌ 驗證失敗`

### 修正 — Preflight `collect_field_schema` 無法處理壓縮 schema（code review）

`json.loads()` 直接解析 `field_schema` 欄位，但 `ArchiveDB.record_archive()`
會把大型 schema 壓成 `zlib:…`。導致 preflight 對大型歸檔無聲地 fallback 成
`{}`，mixed-type field conflict 偵測失效。改為使用
`ArchiveDB.decompress_schema()` 解壓，解析失敗時 `log.warning` 而非無聲地
吞掉。backfill 路徑也改用 `_maybe_compress_schema()` 確保儲存一致。

### 修正 — `_dt_to_str()` / `_str_to_dt()` timezone 處理（code review）

`replace(tzinfo=None)` 只拔掉 tzinfo 卻沒先轉 UTC。`+08:00` 的 datetime
會被當成 UTC 存進去，絕對時間偏移 8 小時。改為先
`astimezone(timezone.utc)` 再 strip。內部全用 `datetime.utcnow()`（naive
UTC），既有 DB 資料不受影響。

### 修正 — Cross-conflict 偵測漏掉自動建立的 numeric mapping（code review）

`get_current_custom_mapping()` 之前只讀 Graylog custom field mappings API。
OpenSearch 自動建立的 numeric mapping 看不到，preflight 會漏掉
cross-conflict（target=long，archive=string）。改為先查 active write index
的實際 OpenSearch mapping（`GET /<deflector>/_mapping`），custom mappings
作為補充。

### 新增 — 55 筆單元測試（pytest）

首個公開測試套件。涵蓋：密碼脫敏（10）、DB datetime round-trip（5）、
field_schema 壓縮（6）、DB 重建/備份（5）、清理競態（3）、bulk 匯入
機制（7）、並發匯入鎖（5）、通知格式（7）、OpenSearch `_doc` 排序（1）、
`/api/health` 結構（2）、preflight conflict 計算（4）。

### 修正 — 文件與實作一致性（reviewer 回報）

- **FastAPI `version` 硬寫 `"1.3.1"`**（`web/app.py`）而非讀
  `glogarch.__version__`。改為讀取唯一版本來源。
- **匯出 metadata 的 `glogarch_version` 硬寫 `"1.3.1"`**（`export/exporter.py`
  與 `opensearch/exporter.py`）。改為讀 `__version__`，讓歸檔檔案
  永遠帶正確版號。
- **Config 搜尋路徑 `/etc/glogarch/`** 與安裝指令碼的
  `CONFIG_DIR="/etc/jt-glogarch"` 不一致。改為 `/etc/jt-glogarch/`
  （home 目錄 fallback 也改為 `~/.jt-glogarch/`）。

## [1.4.4] - 2026-04-10

### 變更 — 作業歷程「錯誤」欄改為「備註」

- 欄位標題從「Error / 錯誤」改為「Note / 備註」（en + zh-TW i18n），
  因為這欄現在同時存放資訊提示（如「去哪查看匯入的資料」）與真正的
  錯誤訊息。
- 顏色邏輯：紅色（`--danger`）只用於 failed 狀態或訊息含
  「Compliance violation」/「Interrupted」的情況。其他備註用灰色
  (`--text-muted`）低調顯示。作業歷程頁面與儀表板最近任務表格都有改。

### 修正 — 架構圖對齊

`README.md` 與 `README-zh_TW.md` 裡的 ASCII art 架構圖右邊框 `|`
沒對齊。用 Python 驗證每行寬度後重畫為固定 70 字元寬。

## [1.4.3] - 2026-04-10

### 修正 — 即時控制條跑進 bulk 模式

匯入 modal 的「即時控制條」（暫停 + 速率 slider）在 GELF 與 bulk 模式
都會顯示，但 bulk 模式兩個都不認帳。使用者截圖回報 50 份歸檔正在做
preflight 時 slider 還顯示「100ms」。

- 把暫停 + 速率 slider 包進 `#import-gelf-controls`，bulk 模式時整個
  hide 掉（`doImportSingle` → `gelfControls.style.display='none'`)
- 新增一個常駐的 `#import-cancel-btn`，讓 bulk 匯入也能從 modal 中途
  取消

### 修正 — `/jobs/{id}/cancel` 取消不掉 bulk 匯入

cancel endpoint 之前只 set `_cancel_flags[job_id]`，但 bulk loop 的
取消檢查點是讀 `ImportFlowControl.cancelled`（要透過
`get_import_control(job_id).cancel()` 觸發）。兩條不同的 cancel 機制 —
按取消對 bulk 完全沒效果。現在 endpoint 也會呼叫
`get_import_control(job_id).cancel()`，bulk loop 在 batch 之間就會
真的停下來。

### 新增 — 取消匯入確認的 i18n

en + zh-TW 都加上 `confirm_cancel_import` 字串（供新的
`cancelActiveImport()` modal 流程使用）。

## [1.4.2] - 2026-04-10

v1.4.0 強化版發行後在 Graylog 7 目標 (.83) 端對端測試時又抓到兩個
潛在的架構 bug 與幾個 UX 問題，本版本一次處理。

### 修正 — Bulk 模式匯入後 Graylog Search 看不到資料

症狀：bulk 匯入回報「已完成，159,286 筆訊息」，OpenSearch 也確實有
資料（`jt_restored_2026_04_09` 索引，166 MB），但在 Graylog 上搜尋
`jt-glogarch Restored (jt_restored)` stream 顯示 0 筆結果。發現 32
萬筆訊息都成了 UI 看不到的殘留索引。

根因：`BulkImporter._index_name_for_doc()` 之前是用每筆文件的
`timestamp` 推算目標索引名稱（`jt_restored_YYYY_MM_DD`）。Graylog
是用 MongoDB 追蹤 index set 的索引清單（`jt_restored_0`、
`jt_restored_1`...），**不是用 `<prefix>_*` wildcard**。Graylog 不認得
不是它自己建的索引，即使名稱開頭對得上也不會列入 stream 搜尋範圍。
Stream → index_set → MongoDB 清單查詢永遠不會回傳那些日期分區索引。

修法：bulk 寫入現在**永遠走 Graylog 管理的 deflector alias**
(`<prefix>_deflector`）。OpenSearch 會把 bulk request 自動路由到 Graylog
標記為 `is_write_index=true` 的底層索引，所以：
- Graylog Search 立刻就看得到我們的文件（寫進 Graylog 自己追蹤的
  寫入索引裡）
- Graylog 自己的 SizeBased / TimeBased rotation 還是繼續適用
- 不會再有殘留索引

`_ensure_index()` 學會偵測 deflector alias 結尾，改用 HEAD 驗證而不是
PUT（否則會 fail with `invalid_index_name_exception`）。舊版預先掃描
全部文件以建立日期索引的邏輯也整個拿掉了。

### 修正 — Bulk 匯入完成「去哪查看」提示被吞掉

症狀：bulk 匯入成功，Graylog stream 也正確建好，但 Web UI 匯入完成
modal 只顯示「已完成！ (N 記錄數）」，沒提示要去 Graylog 哪裡找資料。
後端確實有把 notice 寫進 `jobs.error_message`（直接查 DB 確認過），
但前端就是不顯示。

根因 (`web/routes/api.py::get_job`)：從 Web UI 觸發的 job 會把 SSE
事件累積到 `_job_progress[job_id]`。`/api/jobs/{id}` endpoint 一律
**優先回 in-memory 版本而完全不查 DB**。in-memory 的 `error_message`
是 `last.get("error")` — 成功時是 None，**根本不會去讀 DB 的真正
error_message column**。所以 where_msg 寫了卻永遠回 null。

修法：in-memory 顯示 job 已完成（`phase=done` 或 `pct>=100`）時，改
讀 DB 裡的 row。這樣會回正確的 `error_message`、正確的 `job_type`、
正確的 status。in-memory cache 還是用於正在進行中的 polling。

### 修正 — `/api/jobs/{id}` 把 import 誤回成 export

`_job_progress` 捷徑的另一個副作用：之前硬寫 `"job_type": "export"`
不管實際是什麼 job。從 Web UI 觸發的 import 在這個 endpoint 都被
誤標成 export（列表 endpoint 與 Job History 是用另一條程式路徑所以
通常看不出來）。現在改從 DB row 讀真正的 type。

### 新增 — Verify 排程「立即執行」按鈕

排程頁面之前只有 export 與 cleanup 排程有「立即執行」按鈕，verify
排程被遺漏 — 純粹是 JS render 條件少寫了 verify。後端
`POST /api/schedules/{name}/run` 三種類型本來就支援。`app.js` 一行
修改解決。

### 變更 — Bulk batch_docs 預設 5000 → 10000

v1.4.1 在 .83 (Graylog 7) 測試驗證 — 每個 `_bulk` request 10k 筆跑
得很順，沒有遇到 429 backpressure。對多數 target 可以直接讓吞吐量
翻倍。共改 4 處：`BulkImporter.DEFAULT_BATCH_DOCS`、`web/routes/api.py`
body 預設、`index.html` modal `value`、`cli/main.py --batch-docs` 預設。

### 文件 — Bulk 模式速率 slider 沒有作用

匯入 modal 的「Batch Delay (ms）」slider **只**對 GELF 模式有用。
`BulkImporter.import_archives()` 的 hot loop 沒有任何 inter-batch
sleep — 只有 OpenSearch 回 429 時的 retry backoff。這條 slider
原本就在 `#gelf-mode-fields` 內，選 bulk 模式時整個 div 會 hide，
所以使用者不會在 bulk 模式看到它。Bulk 真正能調的旋鈕是
`batch_docs`。

## [1.4.1] - 2026-04-10

內部 point release，內容已併入 1.4.2 — 請見上方。Deflector alias 寫入
修法是這版先落地的。

## [1.4.0] - 2026-04-09

強化版本。v1.3.1 端對端測試後盤點出 20 項風險，涵蓋災難復原、密碼洩漏、
保留策略、競態條件、保留欄位處理、並行控制與運維面向。本版本一次處理完。

### 新增 — 災難復原

- **`glogarch db-backup`** — 透過 SQLite 線上 `.backup` API 製作快照
  （執行中也可安全備份）。自動清掉舊快照（`--keep`，預設 14）。建議
  cron 設定：`0 4 * * * /usr/bin/python3 -m glogarch db-backup`。
- **`glogarch db-rebuild`** — 掃描歸檔目錄重建 SQLite metadata DB。讀取
  每個 `.json.gz` 內的 metadata 區塊與 `.sha256` 副檔案，逐筆寫回
  資料表。已存在的 row 不會重複寫入。SQLite DB 遺失或損毀時用。

### 新增 — 維運端點

- **`GET /api/health`** — liveness/readiness 探針，可給 Prometheus blackbox、
  Kubernetes、Uptime Kuma 等監控工具使用。DB 可連、歸檔磁碟可寫且
  剩餘空間高於設定值、排程器執行中時回傳 200(`healthy`)；否則回傳
  503 並附 `issues[]` 陣列。

### 新增 — 維護工具

- **`glogarch streams-cleanup`** — 列出/刪除 jt-glogarch 在 bulk 模式
  匯入時自動建立的 Streams 與 Index Sets。會同時刪除 Graylog Stream
  與底層 Index Set(Graylog 也會把 OpenSearch 索引刪掉）。測試後或
  封存某批歸檔後使用。

### 新增 — Bulk 匯入改進

- **取消檢查點** — `BulkImporter` 在 batch 之間檢查 cancel 旗標。在
  Web UI 中按取消可即時停止匯入，不會跑完整批。
- **保留欄位篩除** — bulk body builder 會把 `_id`、`_index`、`_source`、
  `_type`、`_routing`、`_parent`、`_version`、`_op_type` 從每筆文件
  剔除，避免歸檔中極少數含這類欄位的文件導致 bulk 整批被拒絕。

### 變更 — `jt_restored_*` 保留策略

- 舊版：`NoopRetentionStrategy`，`max_number_of_indices = 2³¹-1`，
  → 重複 bulk 匯入後索引會無限累積。
- 新版：`DeletionRetentionStrategy`，`max_number_of_indices = 30`，
  可透過 `find_or_create_index_set()` 新增的 `max_indices` 參數調整。
  避免叢集磁碟用量失控。

### 安全

- **`jobs.error_message` 密碼/Token 脫敏** — 新增
  `glogarch/utils/sanitize.py`，任何要寫入 `jobs.error_message`、
  `audit_log.detail` 或經由 `update_job` / `create_job` / `audit` 的字串
  都會先脫敏。涵蓋 `Authorization: Basic|Bearer …`、
  `http(s)://user:pass@host`、`password=…`、`token=…`、`api_key=…` 與
  JSON 風格的 `"password": "…"`。輸出長度也有上限（預設 2000 字）。
- **TLS verification** 串接到 `PreflightChecker`(`verify_ssl` 建構參數，
  預設 False）。preflight HTTP client 不再硬寫 `verify=False`。
- **Token 過期偵測** — 匯出/匯入若因 Graylog 401 失敗，錯誤訊息現在會
  顯示「Graylog API authentication failed (401). Check that the API
  token is still valid: …」並觸發通知。

### 修正 — 競態條件與並行

- **清理 vs 匯出競態** — 清理會跳過最近 10 分鐘內被修改的檔案
  (`RECENT_FILE_GRACE_SECONDS`），避免保留期掃描刪掉還在被匯出寫入
  的歸檔檔。
- **同時匯入鎖** — 在 importer 層加上 per-archive 鎖。同一個歸檔不會
  被兩個 job 同時匯入（兩個瀏覽器分頁、排程 + 手動點按、CLI + Web UI）。
  衝突會立即失敗並顯示明確訊息；鎖會在 importer 的 `finally` 區塊
  自動釋放。
- **通知失敗不再被吞掉** — `notify_*` 例外現在會記錄為 warning 並寫進
  job 的 `errors[]`，不再被 `try / except: pass` 默默吞掉。

### 效能

- **`glogarch verify --workers N`** — 平行 SHA256 驗證，N 個 worker
  thread。磁碟 I/O bound，thread 模式即可。`--workers 1`（預設）維持
  原本的循序行為。
- **`field_schema` 欄位自動壓縮** — 單一歸檔的 field schema JSON 超過
  4 KiB 時改以 `zlib:` + base64 儲存，讀取時透過
  `ArchiveDB.decompress_schema()` 自動解壓。讓欄位數很多的歸檔不會把
  metadata DB 撐肥。

### 文件

- **DST 與 APScheduler**:APScheduler 依系統時區運作；像 `0 3 * * *`
  這種 cron 在日光節約時間切換日可能會跑兩次或被跳過。需要絕對時間
  保證的使用者請改用 UTC cron。
- **bulk 匯入後的 `gl2_processing_timestamp` / `gl2_remote_ip`**:bulk
  模式跳過 Graylog 的處理鏈路，所以這些欄位反映的是「來源叢集」原本
  的處理時間，不會在匯入時被改寫。這是設計決策 — bulk 模式就是要
  保留來源叢集的歷程。
- **單租戶**:jt-glogarch 為單租戶設計。metadata DB 與 Web UI 都沒有
  per-user 的資料隔離。
- **Web UI 會覆寫手動修改的 config**：從 Web UI 儲存任何設定都會以
  記憶體中的 `Settings` 物件重寫 `config.yaml`，在頁面載入後到儲存
  之間做的手動編輯會被覆蓋。需要批次/自動化變更請直接編輯
  `config.yaml` 並重啟服務。
- **IndexSet 名稱衝突**:`find_or_create_index_set` 是以 `index_prefix`
  查詢而非 title。兩個呼叫端搶建同一個 prefix 時，後到者會直接重用
  前者建立的 index set(API 在伺服器端會強制 prefix 唯一）。

## [1.3.1] - 2026-04-10

### 修正 — Bulk 模式匯入後在 Graylog UI 上看不到資料

v1.3.0 bulk 模式端對端測試發現，匯入的訊息確實有寫進 OpenSearch 但
**在 Graylog UI 上搜尋不到**。原因：Graylog 搜尋會以 `streams` → index sets
做篩選，而我們的訊息 `streams` 欄位是來源 cluster 的舊 stream UUIDs，
目標 cluster 不認得。沒有目標 stream 綁到 bulk index set，Graylog 完全
不會去 query `jt_restored_*` indices。

- **`PreflightChecker.find_or_create_stream()`** — 新方法，透過
  `POST /api/streams` 建立綁到 bulk index set 的 Graylog stream（並 resume）。
  Bulk preflight 會在建完 index set 後立刻建這個 stream。
- **Graylog 6 + 7 雙 API 支援** — Stream 建立 API schema 在 Graylog 6 跟 7
  之間有差異：
  - Graylog 7: `CreateEntityRequest_CreateStreamRequest`
    → `{"entity": {<config>}, "share_request": null}`
  - Graylog 6: `UnwrappedCreateEntityRequest_CreateStreamRequest`
    → `{<config>, "share_request": null}`（平級 sibling)

  程式先試 wrapped 版本，4xx 就退一步試 flat 版本。兩個版本都端對端
  驗證通過。
- **`BulkImporter.target_stream_id`** — 新屬性，由 importer 從 preflight
  result 設定。每筆 doc 在 bulk write 之前會把 `streams` 欄位 rewrite 成
  `[target_stream_id]`，蓋掉來源 cluster 的舊 UUIDs。Graylog 搜尋現在
  會正確路由到新 stream → 新 index set → `jt_restored_*` indices。
- **完成後通知** — bulk 匯入成功會在 `jobs.error_message` 寫一行
  「去哪找你的資料」訊息。CLI 用青色 ⓘ 印出；Web UI 在作業歷程顯示
  tooltip；進行中的匯入對話框也會在完成時用 info box 顯示。
- **`ImportResult.notices`** — 新欄位，放非錯誤的資訊類訊息。
- **SSE `done` 事件原本沒帶 `error_message`** — `watchJob` 在 done 事件
  收到時會額外 fetch 一次完整 job record，讓完成後的 notice 能在 UI 上
  顯示。

### 修正 — Modal 顯示問題

- **Modal 太高超出視窗** — `.modal-card` 加上 `max-height: 90vh` +
  `overflow-y: auto`，匯入對話框內容過高時會在 modal 內部 scroll，
  不會超出視窗上下緣。
- **模式選擇卡文字字字換行** — radio 卡片寬度不夠塞原本的標籤。
  縮短 label(`GELF (Graylog Pipeline)` → `GELF`、
  `OpenSearch Bulk (~5-10x)` → `OpenSearch Bulk`），內 div 加
  `min-width: 0` + `overflow-wrap: break-word`，modal 寬度從 420 調到 460px。
- **匯入完成後 form 還在顯示** — `watchJob` 完成 callback 原本把
  `import-modal-form` display 改回 `block`，讓表單欄位跟完成的進度條疊
  在一起。現在完成後 form 保持隱藏，使用者點 modal 外面 dismiss。

### 修正 — 修改 static 檔案後 `pip install` 沒生效

修改 `web/static/js/*.js` 或 `web/static/css/*.css` 時，FastAPI 的
StaticFiles mount 是從**安裝後的 package** 路徑
`/usr/local/lib/python3.10/dist-packages/glogarch/web/static/` 服務，
不是 `/opt/jt-glogarch/glogarch/web/static/`。只 rsync static 檔案到 /opt
是不夠的 — 必須再跑一次 `pip install --force-reinstall` 才會更新。
已記錄在 CLAUDE.md。

### 變更 — 台灣用語清理

- `推薦` → `建議`(i18n bulk_dedup_id、README-zh_TW)
- `殘留檔案` → `殘留檔案`(README-zh_TW)
- 移除所有「v1.1+ 歸檔」/「v1.0 歸檔」的版本歷史措辭（從使用者文件
  與程式註解），因為 v1.3.0 是第一次公開發行。
- 從 README 移除過時的 SSH journal 監控引用 — 只剩 Graylog API journal
  監控。

### 新增 — README 語言切換連結

`README.md` 跟 `README-zh_TW.md` 兩個檔案頂部都加上語言切換列：
`**Language**: **English** | [繁體中文](README-zh_TW.md)`（中文版鏡像同樣）。
GitHub 渲染時會用相對連結讓兩份 README 互相切換。

### 新增 — 匯出時保留 `gl2_message_id`

兩個 exporter 都保留 `gl2_message_id`（用於 bulk 匯入重複資料刪除）；其他
`gl2_*` 欄位仍會被剝除。GELF 匯入路徑不受影響，因為 Graylog 收到時會
重新生成所有 `gl2_*`。

## [1.3.0] - 2026-04-09

### 新增 — OpenSearch Bulk 匯入模式

新的高速匯入模式，完全跳過 Graylog 直接寫入 OpenSearch 的 `_bulk` API。
已用 CLI 端對端驗證通過。

- **`glogarch/import_/bulk.py`** — `BulkImporter` 類別
  - 讀歸檔、組 NDJSON bulk 請求、解析每筆文件的成功/失敗結果
  - 每日 index 命名：`<pattern>_YYYY_MM_DD`，依每筆文件的 timestamp 決定
  - 預先建立目標 index(Graylog 環境的 OpenSearch 通常設
    `action.auto_create_index = false`，bulk write 必須先建）
  - 三種重複資料刪除策略：`id`（用 `gl2_message_id` 當 `_id`，重複匯入會
    overwrite)、`none`、`fail`
  - 遇到 OpenSearch 429（限流）指數退讓
  - 注入 marker 欄位 `_jt_glogarch_imported_at` 方便追蹤
- **Preflight 擴充**支援 bulk 模式：
  - `auto_detect_opensearch_url()` — 從 Graylog API URL 推導 OpenSearch URL
    (port 9000 → 9200）並偵測連線
  - `find_or_create_index_set()` — 自動在 Graylog 上建立對應 prefix 的
    Index Set，讓還原資料立刻可在 Graylog UI 上搜尋
  - `apply_bulk_template()` — 寫一個 OpenSearch index template，設
    `total_fields.limit: 10000` 並把所有有字串值的欄位 pin 為 `keyword`
  - `PreflightChecker.run(mode='bulk', ...)` 分支：跳過 Graylog deflector
    cycle（無意義），改為寫 bulk template + 建立 Graylog index set
- **`Importer`** 接受 `mode='bulk'` + `bulk_importer` 參數，在 GELF send
  迴圈前分支
- **Web UI Modal 重構**含模式選擇器：
  - 兩張 radio 卡：`GELF (Graylog Pipeline)`（預設）與
    `OpenSearch Bulk (~5-10x)`
  - Bulk mode 顯示橘色警告區塊，清楚說明跳過了什麼
  - Bulk-mode 專屬欄位：目標 index pattern、重複資料刪除策略、批次大小、
    OpenSearch 自動偵測 checkbox + 手動 URL/帳密
  - 切換模式時欄位群組 hide/show，內容保留；Graylog API 帳密兩 mode 共用
  - 新增 23 個 i18n 字串（中英）
  - 新 CSS:`.mode-selector`、`.mode-option`、`.bulk-warning`
- **CLI `import` 命令**新增選項：
  - `--mode [gelf|bulk]`
  - `--target-os-url`、`--target-os-username`、`--target-os-password`
  - `--target-index-pattern`（預設 `jt_restored`)
  - `--dedup-strategy [id|none|fail]`
  - `--batch-docs`（預設 5000)
- **權衡點清楚記錄** — bulk mode 跳過所有 Graylog 處理（Pipeline、
  Extractors、Stream routing、Alerts）。只適合「歷史資料原樣還原」場景。

### 新增 — 匯出時保留 gl2_message_id

為了讓 bulk 匯入能做精準重複資料刪除，兩個 exporter 都會**保留** `gl2_message_id`
欄位。其他 `gl2_*` 欄位（`gl2_source_input`、`gl2_processing_timestamp` 等）
仍會被剝除，因為它們指向來源 cluster 的節點/輸入，在目標 cluster 不存在。

- **`opensearch/client.py`** — `iter_index_docs` 保留 `gl2_message_id`
- **`graylog/search.py`** — `_extract_messages` 保留 `gl2_message_id`
- GELF 匯入路徑不受影響 — Graylog 收到訊息後會自己重新生成所有
  `gl2_*` 欄位，包含全新的 `gl2_message_id`。

### 新增 — IMPORTING 狀態 startup recovery

`ArchiveDB.connect()` 啟動時會自動把卡在 `importing` 狀態的歸檔回復到
`completed`，並 log 警告。原因：當匯入 process 被砍（`-9`、OOM、crash）時，
importer 的 `finally` block 沒跑完，歸檔被永久標記為 `importing`，在 Web UI
歸檔清單上看不到。現在會在每次 service 重啟或 DB connect 時自動修復。

### 新增 — UI polish(延續 v1.2.0)

- **GELF 主機 → Graylog API URL 自動帶入** — 在 GELF 主機輸入 IP 時，
  若 API URL 欄位沒被使用者改過，會自動填入 `http://<ip>:9000`。跟 GELF
  port 自動切換是同一套 `data-user-edited` 旗標機制。
- **重新打開正在跑的匯入對話框** — 如果使用者在匯入過程中不小心點外面
  把 modal 關掉，點側邊欄的執行中作業指示燈會把 modal 重新叫回進度模式
  (form 隱藏、進度條 + 控制按鈕顯示）。SSE + 輪詢的監聽器在 modal 關閉
  期間會繼續在背景跑。
  - `closeImportModal()` 在 `_activeImportJobId` 還在時 early-return，
    完全不 reset state
  - 新函式 `reopenActiveImportModal()`
  - 側邊欄 `checkRunningJobs()` 加上 `cursor: pointer` + `onclick`
- **匯入對話框 i18n 補完** — `Pause`/`Resume` 按鈕、`Speed:` 標籤、
  `sending`/`paused` phase 文字、`Journal: X (slow)` badge、以及「匯入
  工作已啟動」訊息中的 `(N archives)` 都改為依語言切換。
- **`completed_with_failures` job badge** — 作業歷程表格上，當 `completed`
  作業有 `error_message` 且包含「Compliance violation」時，改顯示橘色
  shield-checkmark 圖示。hover 顯示完整 violation 訊息。純前端邏輯，
  不需要 DB schema 變更。

### 修正 — v1.3.0 CLI 測試時發現的 bug

- **`def list(...)` shadow Python builtin** in `cli/main.py` — `list` CLI
  命令原本定義為 `def list(...)`，這會把一個 click Command 物件放到 module
  level 的 `list` 名稱上，**蓋掉 builtin**。在 `import_cmd` 內，這行
  `ids = list(archive_id) if archive_id else None` 實際變成在呼叫 click
  Command，觸發詭異的 `TypeError: object of type 'int' has no len()`
  錯誤（來自 click 的 argument parser）。修法：rename 為
  `def list_cmd(...)` 用 `@cli.command("list")` 保留 CLI 命令名。
- **Bulk path 撞到 `index_not_found_exception`** — Graylog 環境的
  OpenSearch 通常設 `action.auto_create_index = false`，所以 `_bulk` API
  無法自動建立每日目標 index。`BulkImporter` 現在會在 pre-flight 階段
  掃所有歸檔的 timestamp，把每個需要的每日 index 名稱列出來，逐個 PUT
  建立（idempotent：遇到 400 `resource_already_exists_exception` 視為
  成功）。
- **`pip install` 在版本未變時是 no-op** — 如果改完程式但 `pyproject.toml`
  的版本沒變，`pip install` 會誤判為「已安裝」而跳過，執行的還是舊程式
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
  `target_api_url` + (`target_api_token` 或 `target_api_username` + `target_api_password`）。
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
- **GELF 預設改為 TCP / port 32202**（之前是 UDP / 12201）。UDP 仍可選，但 README 明確警告大量匯入時會無聲地丟封包。
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
- README/CHANGELOG/`jt-glogarch.service` 內的 repo 網址統一更正為 `https://github.com/jasoncheng7115/jt-glogarch`
- 新增 FAQ 條目：排程未在預期時間執行 → 請確認系統時區與你寫 cron expression 的時區一致（APScheduler 繼承系統時區）

## [1.0.0] - 2026-04-06

### 新增
- **雙模式匯出**：Graylog API + OpenSearch Direct
- **OpenSearch 單次掃描匯出**：整個 index 一次掃描，依小時切分歸檔檔案（速度提升 5 倍）
- **跨模式重複資料刪除**：切換 API/OpenSearch 模式不會重複匯出
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
