# jt-glogarch 測試清單

**語言**： [English](TESTING.md) | **繁體中文**

每次發版前必須全數通過。在專案根目錄執行：

```bash
./scripts/run-tests.sh
```

---

## 規則 0——測試清單必須跟著產品長大（強制）

**每個新功能或行為異動，必須在同一版更新本清單**：加入能抓到它壞掉的檢查項、
擴充對應的指令碼（UI 流程→`ui-sim-test.py`、資料路徑→`e2e-archive-test.sh`、
新失效類別→`test_static_sweeps.py`），並註明**為什麼**（防的是哪一類 bug）。
沒有清單項目的功能等同未測——bulk 匯入的 OOM 正是這樣潛伏了許多版。
審查者：任何未動到本檔的功能變更一律退回。

## 一條指令的發版總檢

```bash
UI_URL=https://<staging>:8990 UI_USER=localadmin UI_PASS=... \
GL_HOST=<graylog-ip> GL_USER=admin GL_PASS=... \
GL_SSH=root@<graylog-ip> REPO=<git-clone> \
bash scripts/release-check.sh        # ALL PASS 即可出貨
```

執行的層次，以及每層對應的實際出貨過的 bug 類別：

| # | 層次 | 指令 | 防範 |
|---|------|------|------|
| 1 | 靜態＋單元閘門 | `./scripts/run-tests.sh` | JS 語法（壞掉的 i18n.js 出貨了兩版）；未定義識別字（死掉的取消鍵）；pytest 含靜態掃描（未匯入名稱、import 遮蔽、i18n 缺漏、錯誤字串未跳脫、無聲 except 棘輪）與效能回歸（每輪 45 秒的重複資料刪除、永久 7% 核心的輪詢） |
| 2 | 瀏覽器模擬 | `scripts/ui-sim-test.py` | 每頁＋中英切換零 JS 錯誤；匯入對話框自動帶入；自訂下拉**有畫出來**（`<option>` 存在但使用者看到空白）；危險區摺疊；設定頁建議值契約 |
| 3 | 實際點擊操作 | `scripts/ui-cancel-test.py` | 低一層的檢查騙過我們三次：類別 vs 路由、`<option>` vs 皮膚、語法 vs 執行期。斷言確認視窗開啟、作業停止、狀態＝`cancelled` |
| 4 | 線上報表機制 | `scripts/report-bigrange-test.py` | 單元測試看不見的線上 schema 不符（粗化與切片無聲失效而所有單元測試全綠） |
| 5 | 歸檔往返 | 在 Graylog 主機上跑 `scripts/e2e-archive-test.sh` | 七個資料路徑步驟，含 bulk（整檔 OOM 潛伏多版未測）、重複資料刪除／補缺、自癒、清除後匯入 |
| 6 | 升級相容 | `REPO=... scripts/upgrade-compat-test.sh` | 三大升級原則；任何 schema／設定預設值／排程器變更**必跑** |

無法指令碼化的手動項目在下方各節（較大版本的 ZAP 掃描、UI 變更目視、閱讀實際
通知內容、對客戶文件）。六層全部 `ALL PASS` 加上下方手動節次完成＝可出貨。

## 自動化測試（約 485 筆）

### 單元測試

| # | 測試檔 | 筆數 | 覆蓋範圍 |
|---|---|---|---|
| 1 | `test_audit.py` | 28 | 稽核解析器（帳號解碼、分類、敏感判定、噪音過濾、syslog/JSON 解析、process_raw_entry）、設定預設/自訂/YAML/缺欄位/無區段、DB 寫入/列表/統計、token 解析、獨立稽核保留期限清理、清理 fallback、通知事件 |
| 2 | `test_sanitize.py` | 10 | 密碼/Token/URL/JSON/Basic Auth/Bearer 脫敏、截斷、無誤殺 |
| 3 | `test_local_admin.py` | 9 | SHA256 hash、帳號必須 `localadmin`、Graylog 拒絕不 fallback、Graylog 離線有/無 hash、向下相容 |
| 4 | `test_upgrade_script.py` | 9 | upgrade.sh 存在 + 5 步驟、root 檢查、版本顯示、README 引用、systemd 預設=Yes、git clone sudo、retention_days 遷移、op_audit retention_days 預設值 |
| 5 | `test_repo_structure.py` | 8 | pyproject.toml 在根目錄、無 src/ 目錄、deploy 檔案、README/CHANGELOG/CONFIG 存在、版號同步、github/glogarch 與 source 一致 |
| 6 | `test_bulk_import.py` | 7 | 保留欄位剝除、deflector alias、stream 改寫、marker 欄位、dedup id/none |
| 7 | `test_notify_format.py` | 23 | 狀態 emoji（✅/⚠️/❌）、每行一項、URL 縮短、en/zh-TW key 一致、依顯示寬度對齊、全形冒號、Telegram HTML 跳脫、溢出時間本地化 |
| 8 | `test_notify_test_endpoint.py` | 7 | Discord/Slack/Teams/Telegram/Nextcloud Talk/Email 送出函式參數、測試端點簽名匹配 |
| 9 | `test_field_schema.py` | 6 | 純 JSON 通過、zlib 壓縮 round-trip、None/損毀處理、DB 儲存+讀取 |
| 10 | `test_multi_server.py` | 6 | 多伺服器設定、依名稱取得伺服器、排程器讀取伺服器、UI 伺服器選擇器、JS 儲存/載入伺服器 |
| 11 | `test_database_datetime.py` | 5 | naive/UTC/+08:00 round-trip、None 通過、offset 字串解析 |
| 12 | `test_import_lock.py` | 5 | 取得/衝突/釋放/錯誤 owner/重複取得 |
| 13 | `test_db_rebuild.py` | 5 | dry-run、實際重建、跳過已存在、備份、清理舊備份 |
| 14 | `test_preflight_conflicts.py` | 4 | intra-archive conflict、cross-conflict 實際 mapping、string-only 不 pin、混合場景 |
| 15 | `test_config.py` | 4 | 預設值、搜尋路徑 `/etc/jt-glogarch/`、檔案載入、WebConfig localadmin |
| 16 | `test_upgrade.py` | 4 | 舊 DB 自動升級、舊 config 向下相容、歸檔升級後保留、DB 備份有效性 |
| 17 | `test_api_error_handling.py` | 4 | Graylog API 401/502/連線失敗的錯誤處理（/api/index-sets 與 /api/streams） |
| 18 | `test_cli_commands.py` | 3 | 16 個指令全註冊、hash-password help、root 警告邏輯 |
| 19 | `test_cleanup_race.py` | 3 | 寬限常數 = 600 秒、新檔跳過、舊檔不跳過 |
| 20 | `test_storage_ownership.py` | 3 | root chown 修復、非 root 報錯、限定 base_path 以下 |
| 21 | `test_health_endpoint.py` | 2 | 回應結構（status/version/checks/issues）、公開路徑（免認證） |
| 22 | `test_recent_fixes.py` | 11 | 通知時間戳本地時區、測試端點時區、保留預設 3 年、Data Node 偵測/警告 i18n/匯入 modal/匯出模式、排程 OpenSearch 顯示、設定範例保留天數、Discord/測試端點正確參數 |
| 23 | `test_opensearch_client.py` | 1 | `_doc` 排序 tiebreaker（非 `_id` — circuit breaker 修正） |

### 整合測試

| # | 測試檔 | 筆數 | 覆蓋範圍 |
|---|---|---|---|
| 24 | `test_integration.py` | 6 | 真實 OpenSearch cross-conflict 偵測、zlib schema 完整 preflight 流程、timezone dedup/retention/coverage-ratio 正確性、歸檔寫入→SHA256→讀回完整性 |

---

## 發版前手動檢查清單

自動化測試全數通過後執行：

### 版本一致性

- [ ] `glogarch/__init__.py` 已更新版號
- [ ] `scripts/check-version.sh` 通過
- [ ] README 標題：`# jt-glogarch vX.Y.Z`（EN + zh_TW 兩份）
- [ ] README badge：`version-X.Y.Z-green`（兩份）
- [ ] CHANGELOG 有新版本 entry（EN + zh_TW 兩份）
- [ ] `CLAUDE.md` 版號已更新

### GitHub Repo 結構

- [ ] `github/pyproject.toml` 在根目錄（不在 `src/` 裡）
- [ ] `github/glogarch/` 在根目錄（不在 `src/` 裡）
- [ ] `github/glogarch/__init__.py` 版號與 source 一致
- [ ] 沒有 `github/src/` 目錄

### 文件

- [ ] 新功能已寫入 README（EN + zh_TW 兩份）
- [ ] CONFIG.md / CONFIG-zh_TW.md 已更新（若有新增設定欄位）
- [ ] AUDIT-OPERATIONS.md / AUDIT-OPERATIONS-zh_TW.md 已更新（若有新增操作類型）
- [ ] zh_TW 無半形逗號（CJK 語境內）
- [ ] zh_TW 無半形冒號/分號（CJK 語境內）
- [ ] zh_TW 使用台灣繁體中文用語
- [ ] README 升級說明是最新的
- [ ] **授權標示一致** —— `LICENSE` 為 GNU AGPL v3 官方逐字原文（標題＋第 13 條
      「Remote Network Interaction」＋版權宣告），且所有引用一致：`pyproject.toml`
      （`license = "AGPL-3.0-or-later"`）、兩份 README 的徽章／標頭／頁尾、以及兩個
      文件頁面（en／zh-TW）。`THIRD-PARTY-LICENSES.md` 中相依套件的授權維持原條款（v1.13.84）

### 部署驗證

- [ ] `pip install --force-reinstall --no-deps /opt/jt-glogarch` 成功
- [ ] `systemctl restart jt-glogarch` — 服務啟動
- [ ] `curl -sk https://localhost:8990/api/health` 回傳新版號 + healthy
- [ ] 登入頁面顯示正確版號
- [ ] `/openapi.json` 顯示正確版號
- [ ] 部署到 .36 staging — health 回傳新版號

### 歸檔往返 — 每次發布必跑

對真實的 Graylog + OpenSearch 跑完整的端對端歸檔流程（需要 `GELF_PORT` 上有 GELF TCP
input；使用 `/tmp` 下的暫時設定／資料庫，不影響正式服務）：

```bash
GL_PASS='<graylog-admin-密碼>' bash scripts/e2e-archive-test.sh
```

- [ ] **[1] Graylog log 歸檔（API 模式）** — 匯出產生歸檔檔案
- [ ] **[2] OpenSearch 歸檔（OpenSearch 直連模式）** — 匯出產生歸檔檔案（指令碼會先
      cycle deflector 讓寫入中的索引封存；OpenSearch 直連匯出一律略過使用中的寫入索引）
- [ ] **[3] 從歸檔以 GELF 匯回 Graylog TCP input** — 匯入回報 `Messages sent: N`
      （N>0）且 **0 indexer failures**（合規通過）
- [ ] **[4] OpenSearch Bulk 匯入** — 文件確實寫入 OpenSearch。Bulk 完全繞過 Graylog，
      因此 [3] 並未涵蓋。指令碼**不可**預先建立索引：建立索引是產品本身的職責，
      而錯誤正是藏在那裡（DEFECTS #4、#24）
- [ ] **[5] 重新匯出的重複資料刪除** — 對已歸檔時間重新匯出會新增 **0** 筆，但被刻意
      挖掉的缺口會**剛好補回一次**（DEFECTS #1～#3）
- [ ] **[6] 歸檔檔案被刪除** — `verify` 會回報檔案遺失，下一次匯出會剛好重新歸檔該區間
- [ ] **[7] 清除目標索引集合後再匯入** — 清除後只剩**一個空的**索引，內建的 `gl-*` 索引集合
      永遠不會被列出，且之後的匯入仍能成功（會讓目標無法寫入的清除，比不清除更糟）
- [ ] 指令碼印出 `RESULT: ALL PASS`

> **必須在 Graylog 主機上執行。** `GL_URL`／`OS_URL` 預設為 `localhost`，GELF 種子資料
> 也是連到 `127.0.0.1`；從其他機器執行會立刻失敗並出現 `ConnectionRefusedError` ／
> `FAIL: seed not indexed`。只有在同時具備通往 GELF 連接埠的路由時，才可覆寫
> `GL_URL`／`OS_URL`。

> 註：在 Asia/Taipei 系統上，重新匯入的訊息會比執行當下早約 8 小時（naive-Taipei 對 UTC
> 的時間戳位移——見 CLAUDE.md「Restore / Re-import」）；指令碼以 24 小時範圍計數，並以
> 匯入器自身的 0 indexer failures 對帳為準，而非最近 1 小時的計數。

### 行為稽核

- [ ] `op_audit.enabled: true` — listener 在 port 8991 啟動，稽核頁面顯示「監聽中」
- [ ] `op_audit.enabled: false` — listener 不啟動，稽核頁面顯示停用
- [ ] config 沒有 `op_audit` 區段 — 使用所有預設值（啟用、port 8991、保留 180 天）
- [ ] config 有 `op_audit` 但缺 `retention_days` — fallback 到預設 180 天
- [ ] `op_audit.retention_days` 獨立控制稽核記錄清理，與歸檔保留期限分開
- [ ] 即使無歸檔可清理，cleanup 仍執行稽核記錄清理
- [ ] `upgrade.sh` 在 config.yaml 缺少 `op_audit` 時自動加入完整區塊
- [ ] `upgrade.sh` 在已有 `op_audit` 但缺 `retention_days` 時自動補上
- [ ] nginx syslog 收到 → 稽核記錄出現在 Web UI
- [ ] 來自非允許 IP 的 syslog → 拒絕並產生 warning log
- [ ] 帳號正確解析（Basic Auth、Token、Session、Cookie）
- [ ] 項目名稱顯示人類可讀的資源名稱（非原始 ID）
- [ ] 敏感操作觸發通知警報
- [ ] Graylog 正常運作但超過 10 分鐘未收到 syslog → 心跳警報
- [ ] 篩選下拉選單顯示正確語言標籤（Method/Status 對 方法/狀態碼）

### 客戶安裝 / 升級模擬

- [ ] 複製 `github/` 到暫存目錄 → `pip install` 成功
- [ ] `deploy/install.sh` 路徑正確、systemd 預設 = Yes
- [ ] `deploy/upgrade.sh` 可正常執行（db-backup → git pull → install → restart → verify）
- [ ] **DB 備份確實產出檔案** —— 升級後 `/var/backups/jt-glogarch/` 會多一個新的
      `jt-glogarch-*.db` 快照。偵測指令曾在 root 的工作目錄下執行、對 `./config.yaml`
      拋 `PermissionError`，於是**靜默略過備份**卻印出看似正常的「not available」
      （v1.13.82）。`test_upgrade_script.py` 已釘住偵測必須在 `$INSTALL_DIR` 下執行。

### 安全性——Bandit 原始碼掃描（每次發版，自動執行）

由 `run-tests.sh` 執行；ZAP 是動態掃描，本質上看不到下列任何一項。

- [ ] `bash scripts/bandit-scan.sh` 印出 `Bandit: OK` —— **HIGH 與 MEDIUM 必須為零**。
      修掉，或在該行標注 `# nosec <IDs> - <為何安全>`；絕不整條規則關掉，否則
      下一個真的問題就看不見了
- [ ] LOW 棘輪（預算 8）沒有變大。它**刻意排除** B110/B112：`try/except/pass`
      由 `tests/test_static_sweeps.py` 及其自身預算負責——同一個決定有兩套規則，
      正是關卡之間開始互相矛盾的起點
- [ ] **沒有任何呼叫寫死 `verify=False`**（`tests/test_tls_verify.py`，以 AST 檢查）。
      *曾有 7 處這樣寫，導致開啟 `verify_ssl` 的操作者在大部分路徑有驗證、在這幾處
      卻無聲地沒有——其中好幾條會傳送憑證（v1.13.91）。*
- [ ] 若調高預算或新增 `# nosec`，必須在 commit 訊息中說明理由

### 破壞性操作——清除目標索引集合（v1.13.66）

任何會**刪除客戶資料**的功能，每次發版都必須重新驗證；這裡的回歸是客戶無法自行復原的。

- [ ] 匯入對話框 →「匯入前清除目標索引」預設為**摺疊**狀態
- [ ] 「載入索引集合」會列出目標的索引集合，且索引數與容量**不為 0**（若為 0 代表回應
      結構已變更，見 DEFECTS #27；此時清除操作看起來會像是無害的空動作）
- [ ] 預設已選取目標的**預設索引集合**
- [ ] Graylog 內建索引集合（`gl-events`、`gl-system-events`）**不會列出**，即使直接
      以其 ID 呼叫 API 也會被拒絕
- [ ] 輸入錯誤的前置碼時，前端與後端（`confirm`）都會拒絕
- [ ] 清除後：該索引集合只剩**一個**索引，且是**全新的空白寫入索引**——目標仍可寫入
- [ ] 之後對已清除的索引集合進行匯入會成功（這正是此功能的目的：舊資料留下的錯誤
      欄位型別對應已經消失）
- [ ] 操作稽核中出現 `graylog_index_set_cleared`，並記錄前置碼、索引數與釋出容量
- [ ] jt-glogarch 自身的歸檔未受影響（歸檔列表不變）

- [ ] **標題絕不低報查詢範圍** —— 當 widget 的資料範圍小於查詢範圍時，兩者都要
      顯示（例如「最近 6 天（…）⚠ 查詢範圍為最近 90 天，此區間內僅有以上時段有
      資料」）。90 天的報表若只標「最近 6 天」，等於讓查詢範圍本身從頁面上消失
      （v1.13.86）
- [ ] **每個表格都標示總筆數** —— 未截斷顯示「共 12 筆」，截斷顯示「顯示前 40 筆，
      共 128 筆」。讀者不該自己一筆一筆數，且截斷的表格必須說明它是什麼的子集
- [ ] **長區間報表執行中要看得到進度** —— 產生最近 90 天的報表，觀察作業歷程與
      側邊欄：每完成一段切片，進度條就要往前（`3 / 13`），不可以在 PDF 產出前
      一直停在 0%。也不可以在檔案還沒產生前就顯示 100%（算繪發生在最後一段之後）。
      十幾段查詢要跑好幾分鐘，凍結的 0% 會被當成當機，客戶就把正常執行中的作業
      取消掉了（v1.13.88）。單元測試：`tests/test_report_progress.py`

### 大範圍報表——影響報表的變更必測

對線上 Graylog 執行 `GL_PASS=<pw> python3 scripts/report-bigrange-test.py [GL_URL]`
——必須印出 `RESULT: ALL PASS`。指令碼會建立（並刪除）一個拋棄式儀表板，內含
此機制必須處理的兩種 widget 形態。

為什麼單元測試不夠：這支指令碼能攔到的兩個 bug 都是**線上 schema 不符**——搜尋
定義的間隔寫成 `{"timeunit":"5m"}`、序列寫成 `{"type":"count"}`（而非 widget 設定
的 `{"value":5,"unit":"minutes"}`／`{"function":"count()"}`），因此粗化與切片各自
無聲地從未觸發，所有單元測試卻都是綠的；而天真的「切片＝未切片」比對也會通過，
因為兩次其實都沒切片。

- [ ] 粗化有觸發——固定 5 分鐘的時間圖說明標註「時間間隔已由 5 分鐘調整為 6 小時」
- [ ] avg widget 帶有「無法分段合併」說明（平均值／不重複計數／百分位數**絕不**拼接）
- [ ] 切片 90 天的筆數總計與未切片對照組完全相等
- [ ] 章節能渲染成真實 PDF（需渲染引擎）
- [ ] 記錄中同時出現 `coarsened wide-range intervals` 與 `wide-window slicing done`
      ——若兩個機制都沒啟動，數字相等本身不能證明任何事

### UI 操作——實際點擊驗證（本版有變更的 UI 操作必測）

同一個功能連續三個 bug，都通過了比使用者體驗低一層的檢查：端點回 500 但單元測試
直接呼叫類別；下拉畫面空白但 `<option>` 元素存在；取消按鈕死掉（`customConfirm`
未定義——語法合法、無處定義）但 API、旗標與所有單元測試都正常。規則：
**在使用者看到的那一層，驗證使用者實際的操作。**

- [ ] 本版**有變更**的每個 UI 操作，都在真實瀏覽器對線上實例實際點擊過——
      不能只斷言標記／`<option>`／路由
- [ ] `UI_URL=... UI_USER=... UI_PASS=... GL_HOST=... GL_PASS=...
      python3 scripts/ui-cancel-test.py` 必須印出 `RESULT: ALL PASS`
      （確認視窗開啟、作業停止、狀態記為 `cancelled` 而非 `completed`）。
      凡動到匯入／取消／作業狀態路徑皆必跑
- [ ] 動到任何通知路徑：閱讀**實際產生的訊息**——使用者主動取消必須以「已取消」
      通知，絕不能是「完成（有錯誤）」

- [ ] **排程匯出可被取消，且取消會釋放鎖** —— `tests/test_export_cancel_registry.py`
      通過。取消原本只靠 `progress_callback` 拋例外實作，而排程從不提供該回呼：
      該次執行會繼續跑並持續持有 per-server 鎖，之後每晚的執行都以「Previous
      export still holds lock」被跳過——歸檔停擺約 4 週，卻只有 info 等級的記錄
      （v1.13.87）
- [ ] **對忙碌中的伺服器手動匯出，必須被明確拒絕** —— `POST /api/export` 回 409
      並帶 `export_already_running`，而不是 200「已開始」。*作業列是在 exporter
      內部、鎖之後才寫的，因此被拒絕的執行完全沒留下任何一列，失敗只存在於作業
      歷程從不讀取的記憶體清單裡——有客戶按下立即執行、被告知已開始，然後到處都
      找不到它（v1.13.92）。*
- [ ] **任何在 exporter 寫下自己那一列之前發生的失敗，仍要出現在作業歷程** ——
      失敗列、已清洗的原因、正確的 `source`。涵蓋鎖被佔用、磁碟滿、伺服器連不上。
      單元測試：`tests/test_export_busy_visibility.py`
### 稽核覆蓋率（每次發版）

- [ ] **每一條會改變狀態的路由都要留下稽核記錄** —— `tests/test_audit_coverage.py`
      會走過所有路由；真正不改變任何東西的 POST／DELETE 必須列入 READ_ONLY_POSTS
      **並寫明理由**。*盤點發現 43 條中有 18 條沒有稽核，包含會**刪除歸檔檔案**的
      `POST /cleanup` —— 單筆刪除有稽核，依保留期整批刪除反而沒有（v1.14.0）。*
- [ ] **特別確認破壞性的那幾條**：清理、刪除歸檔、清除索引集合、刪除伺服器／排程／報表
- [ ] **本系統自身的記錄要能在介面上看到** —— 行為稽核 →「jt-glogarch 操作」，
      可篩選、可分頁。*這些記錄從第一版就在寫，卻沒有任何介面；唯一的讀取方式是
      直接開 SQLite 檔案。*
- [ ] 該分頁要隱藏 Graylog 的統計卡片 —— 那是 Graylog 的操作次數，留著會被讀成
      本系統的操作次數

### 搜尋的資安

- [ ] **XSS：歸檔內容本身就是攻擊者可控的。** 任何人只要能送一筆 log 進客戶的
      Graylog，那段文字就會進入我們的歸檔並被算繪到這個頁面。測試載荷須包含
      `<script>`、`<img onerror>`、`<svg onload>`、`</td></tr>` 跳脫表格，
      以及把載荷放在**欄位名稱**與**歸檔檔名**上：全部必須以純文字呈現，不得執行。
- [ ] 欄位／伺服器／串流的值皆為綁定 SQL 參數；沒有任何使用者提供的路徑會到達
      檔案系統（歸檔路徑一律來自資料庫列）
- [ ] 所有 `/api/search*` 端點在未登入時皆回 401
- [ ] 每頁筆數有上下限、保留命中數有上限、同時存活的搜尋會被清理

### 記錄搜尋（歸檔清單頁）

- [ ] **沒有時間範圍就不能搜尋，而且要在兩層都擋** —— 按鈕是真的 `disabled`
      （不是只有寫著），且 `POST /api/search` 對缺範圍、只有半邊、或無法解析的
      範圍一律回 400。*範圍是唯一的索引；沒有它就是掃描整個語料庫——在真實機器上
      是 173 GB、10.6 億筆。* 提示文字要指名該用哪個控制項（「在上方的歸檔時間軸
      拖曳」）。
- [ ] **搜尋前就要說出代價** —— `/api/search/plan` 顯示歸檔數、記錄數與預估時間，
      而且為此不開啟任何歸檔檔案
- [ ] **預篩絕不可少選** —— 含 JSON 跳脫字元（`"` `\`）的關鍵字要跳過位元組掃描，
      讀不到的歸檔要當成候選。*被跳過的歸檔就是無聲遺漏的結果，與「本來就沒有」
      無法分辨。*
- [ ] **「載入更多」是接續，不是重跑** —— 跨頁時每一筆命中恰好出現一次、不遺漏，
      且已掃過的歸檔不會重開。`has_more: false` 代表這個範圍真的掃完了。
- [ ] **每頁 50／100／200／500／1000 要真的生效** —— 選 50 就回 50 筆
- [ ] **過長的記錄要明確截斷，不能被裁切** —— 4,000 字的 syslog 顯示約 320 字
      加上「…」，絕不能出現中間無聲少掉一段的行
- [ ] **結果表格的版面不能跑掉**（`ui-sim-test.py`）—— 展開某一筆時，表格寬度與
      記錄欄寬度都不變；展開列的 `colspan` 等於**可見**欄位數；表頭與資料列對
      「有哪些欄位」的認定一致，且可見欄位填滿整個表格寬度。*隱藏欄位是表格的
      屬性，不是每個儲存格的屬性：寫死的 colspan 會讓瀏覽器補出幽靈欄位，逐格
      隱藏則會漏掉之後才新增的每一列。兩者都會把記錄內容擠成 96 px，而且後端
      測試完全看不到。*
- [ ] **展開就顯示全部欄位** —— 不需要再點一次「… 另外 N 個欄位」；欄位極多的
      記錄（1,100 個以上）在自己的區塊內捲動，不會把下方的結果整個推走
- [ ] **下載涵蓋所有分頁，不是只有畫面上那頁** —— CSV 與 JSON Lines 都要回傳該
      時間範圍內全部符合的記錄，且兩者筆數一致。*`limit` 只限制畫面；若匯出也照著
      它走，交出去的只有四分之一的證據，看起來卻像是完整的。*
- [ ] **下載是串流，且每份歸檔只讀一次** —— 最後一筆還沒找到之前，第一筆就已經
      可以取得（不會先把整個檔案做出來）；完整匯出對每份歸檔恰好開啟一次。
      *畫面上的「載入更多」是靠重新解析停住的那份歸檔來接續——點幾次沒問題，
      整份下載就會變成平方級：三次 1,000 筆的分頁分別檢視了 22 萬、53.1 萬、
      46.4 萬筆訊息。改為串流後，一次真實的 4,041 筆匯出從 62 秒降到 35 秒，
      輸出位元組完全相同。*
- [ ] **達到筆數上限要寫在檔案裡** —— CSV 寫入 TRUNCATED 那一列、JSONL 寫入
      `_jt_note` 物件，絕不無聲停止
- [ ] **CSV 在 Excel 開啟要正常** —— 有 UTF-8 BOM，中文不會變亂碼；記錄中的換行
      要留在加引號的欄位內
- [ ] **匯出要有稽核**（`search_exported`）—— 記錄離開歸檔屬於資料輸出，
      資料輸出就要留下記錄
- [ ] **`/search/export` 必須宣告在 `/search/{search_id}` 之前** —— FastAPI 依
      宣告順序比對，帶參數的路由會無聲吃掉字面路由，讓下載收到 404 的 JSON
- [ ] **命中的關鍵字要標示，而且標示要安全** —— 關鍵字要在「記錄」欄與展開的
      完整記錄中標示（「來源」欄不標），欄位條件要連欄位名稱一起標示；內容含有
      `<img src=x onerror=...>` 的記錄必須以**純文字**呈現，且關鍵字仍有標示。
      *高亮是用記錄內容組 HTML：先各自跳脫、再插入標記，順序反過來就是 XSS。*
- [ ] **搜尋要讓路給歸檔** —— 匯出或匯入持有鎖時，每份歸檔之間會暫停，並在畫面
      上說明
- [ ] **介面要說明適用範圍** —— 這是掃描而非查詢引擎，需要完整分析請匯回 Graylog
      單元測試：`tests/test_search_engine.py`、`tests/test_search_api.py`

- [ ] **儀表板的統計數值絕不能被裁切** —— UI smoke 會以真實瀏覽器，將算繪後的
      文字寬度與卡片寬度比對，涵蓋數千到 10^18 的量級。*`.stat-card` 為折線圖設了
      overflow:hidden，因此 1,060,702,960 筆被顯示成 `1,060,702,96`（v1.13.93）。
      算繪後的字體寬度，沒有任何 Python 測試量得到——這一項必須用瀏覽器。*
- [ ] **樣板中不得出現行內 `style="…"`** —— 本應用自己的 `style-src 'self'` CSP
      會拒絕它們（`style-src-attr`），所以它們看起來有套用、實際上毫無作用。曾有
      兩個應該預設隱藏的區塊因此是可見的。靜態掃描：`tests/test_static_sweeps.py`
- [ ] **UI smoke 要帶帳密執行** —— 不帶帳密時，登入後的檢查（設定頁算繪、數值裁切、
      主頁面主控台錯誤）根本不會跑。現在它會印出「登入後檢查未執行」；一個明明略過
      了某一層卻顯示 OK 的關卡，正是上面那個 CSP 錯誤能一直存活的原因。
- [ ] **稽核心跳警告要說出成因** —— 內文帶有每台伺服器的失敗原因，且需連續兩次
      探測失敗才發出。*它原本記在 DEBUG（被 INFO 丟掉），且單次瞬斷就發警告：
      11 分鐘內發出、恢復、再發出，而當下兩台都在 50 毫秒內回應（v1.13.92）。*
      單元測試：`tests/test_audit_heartbeat.py`
- [ ] **讀取設定欄位的輔助函式，必須對「真實模型」測試** —— 絕不用手寫假物件。
      *`verify_for_url` 讀的是 `graylog_servers`（真正的欄位是 `servers`），而假
      物件也用了同一個發明的名字，於是測試跟著錯誤一起通過，功能空轉出貨
      （v1.13.92）。*
- [ ] **只有在工作真的停了才升級告警** —— 連續次數本身不是判斷依據。要看這個鎖
      保護著什麼：完全沒有執行中的匯出 → 鎖殘留，發告警並說明重啟即可清除；
      正在執行且**持續前進** → 正常，記錄進度、絕不告警；正在執行但連續數次都沒有
      前進 → 用專屬訊息說出這件事，並提醒被限流的匯出是刻意暫停、會自行恢復。
      *第一次完整歸檔可能有數十億筆、跑上數週，每天排擠掉排程卻歸檔得好好的。
      只看連續次數就告警，等於告訴這種站台「沒有在歸檔任何資料」，並誘導他們
      取消一個已經跑了 58 小時的作業——說法不實，照做則具破壞性（v1.13.90）。*
      單元測試：`tests/test_schedule_lock_skip.py`
- [ ] **執行中的作業要顯示還要多久** —— 作業歷程與側邊欄依該作業自身平均速率
      顯示剩餘時間推估（`剩餘約 53 天`），訊號不足時不顯示，已完成的作業不顯示。
      *115.8 億筆下的「4% · 58h26m」與當機無從分辨，實際上還要 53 天。*
      單元測試：`tests/test_job_eta.py`

### 大規模下的效能與活性（匯出／匯入／資料庫／輪詢變更適用）

隨**資料總量**（而非工作量）成長的成本，只在客戶規模才會現形：20 萬份歸檔時
`covered_ranges` 每輪 45 秒；5 萬筆作業列時作業歷程輪詢永久占用一顆核心的 7%。
兩者在測試規模下都看不見。

- [ ] `tests/test_perf_covered_ranges.py` 通過（規模模式回歸界限；植入 3 萬份
      合成歸檔）
- [ ] 新增熱路徑查詢：出貨前對 20 萬份合成歸檔的資料庫實測，並把量測數字寫進
      CHANGELOG
- [ ] 任何當作迴圈步長／除數的設定值都必須鉗制
      （`chunk_duration_minutes <= 0` 曾讓匯出永久卡死）
- [ ] 靜態掃描通過（`tests/test_static_sweeps.py`）：未定義名稱、import 遮蔽、
      i18n 雙語＋zh 標點／術語、data-act 處理函式、innerHTML 錯誤字串跳脫、
      無聲 except 棘輪

> 測試機注意：.36 設有**真實**通知管道——在其上跑匯入／匯出測試會寄出真的郵件。
> 請先告知會有測試噪音，或先停用通知管道。

### API 匯出——單一毫秒溢出（v1.13.83／85）

整秒的 syslog 尖峰（`12:23:03.000`，無次秒精度）可讓單一時間戳超過 10000 筆，
超出 Graylog REST 的 offset 上限。此情況必須精確降級：絕不丟失整個 chunk、
也絕不被貼成失敗。

- [ ] `tests/test_export_pagination.py` 通過，含
      `test_overflow_ms_does_not_lose_messages_after_it`（過滿毫秒**之後**的資料仍
      完整匯出——舊程式會刪掉整個 chunk）
- [ ] 單一毫秒溢出被記錄進 `search.truncated_windows`，並落在 `result.truncations`
      而非 `result.errors`
- [ ] `tests/test_notify_format.py` 通過：僅有溢出的執行標題為 `export_overflow`
      （非 `export_err`）、以 `EXPORT_COMPLETE`（非 `ERROR`）送出、內文寫「已歸檔、
      不會重試」——真正的 chunk 失敗仍優先且以錯誤回報
- [ ] 測試任何 `notify_*` 路徑：繞過 conftest 的自動靜音——在 import 時抓真函式
      （`_REAL = S.notify_export_complete`）再 patch `send_notification`；對空殼斷言
      會空過
- [ ] **溢出通知要能自己解釋清楚** —— 必須寫出成因（同一毫秒超過 10000 筆，而
      10000 是 API 單次查詢上限）、影響範圍（其餘記錄都已歸檔、本次未失敗、不會
      重試）與該做的事（只針對這些時段改用 OpenSearch Direct 重跑）。客戶看了舊的
      術語開頭寫法，還得回頭問「這什麼意思」。
- [ ] **溢出時間點要同時顯示本地時間與 UTC** —— Graylog 回傳 UTC，操作者卻在自己
      時區的介面重跑；在 Asia/Taipei 只給 `...Z` 會讓他重跑錯誤的八小時，這則通知
      唯一的目的就落空了
- [ ] **通知統計要對齊為一欄** —— 標籤補齊到相同的**顯示寬度**（中日韓字元算兩欄），
      匯出／匯入／清理／驗證四種、中英文皆需；且 zh 內文使用全形冒號
- [ ] **Telegram 內文必須做 HTML 跳脫** —— `parse_mode=HTML` 會把錯誤訊息裡由網址
      縮短產生的字面 `<url>` 當成不支援的標籤，Telegram 回 400，通知就無聲地送不出去
- [ ] 線上（選用）：對單一秒種入 >10000 筆＋之後幾筆，跑 API 匯出，確認「之後」的
      訊息已歸檔、溢出被回報（而非 chunk 失敗）。事後清除種子。

### 測試結果

- [ ] `./scripts/run-tests.sh` 通過 — `TEST-RESULTS.md` 已產生
- [ ] `TEST-RESULTS.md` 已 commit 到這個版本

---

## 升級相容性測試（必要）

    REPO=/path/to/git-clone bash scripts/upgrade-compat-test.sh [版本 ...]

以**舊版本自己的程式碼**（取自 git 歷史）建立真實狀態——12 份含實體檔案的歸檔、三個排程，以及舊格式的 config.yaml——再把該狀態交給**目前版本**接手，並驗證三條不可妥協的升級原則：

1. **絕不遺失資料** —— 經過 `_migrate()` 後，歸檔紀錄、筆數與檔案完全一致；升級路徑中沒有任何刪除。
2. **絕不讓系統無法正確使用** —— 舊 `config.yaml` 能載入、舊的 `api_audit:` 會轉換為 `op_audit`、之後新增的欄位會取得預設值。
3. **絕不讓排程歸檔停止** —— 既有排程全數保留**並且**確實註冊到 APScheduler；清理排程若儲存了比實際生效值更短的保留期，會被向上對齊，並實際驗證清理執行時採用的是安全值（否則升級後第一次 04:00 就會刪掉 200～1095 天之間的歸檔）。

已驗證來源版本：**1.7.9、1.7.15、1.9.2、1.10.13、1.11.0、1.12.0、1.12.10、1.13.0、1.13.20、1.13.40**——全部 ALL PASS。只要動到 schema 遷移、config 預設值、排程器，或任何會重新解讀既有狀態的程式碼，都必須執行。

## 設計檢視：常見陷阱檢查清單

以下每一項在本專案都**真實發生過**，並附上對應事故版本，讓檢查具體而非流於原則。
凡是改動匯出、匯入、重複判斷、儲存或進度回報，請逐項走過一次——成本遠低於事故本身。

### 1. 規模——成本是隨「資料量」還是隨「工作量」成長？

- [ ] 工作量是隨**新增的工作**成長，還是隨**資料總量**成長？
  *重複判斷原本在每筆文件被取回並解析**之後**才執行，因此重跑匯出會把整個 3 億 4 千萬筆的索引全部拉過網路，只為了發現早已歸檔。多個彼此無關的站台進度停在「0%」達 14 小時（v1.13.53）。*
- [ ] 是否有對整張資料表的 `fetchall()` 或串列生成式？
  *為了顯示一頁，把 7 萬筆歸檔紀錄全部載入記憶體（v1.13.47）。*
- [ ] 是否有整檔 `json.load()` 或整份讀進記憶體？
  *Bulk 匯入會把 1.2 GB 的歸檔整份展開為 Python 物件（v1.13.47）。*
- [ ] 是否在數百萬筆的迴圈內，逐筆發出資料庫查詢或 HTTP 請求？
- [ ] 這個「檢查」會不會隨歷史累積而愈來愈慢？請合併／彙總，讓成本隨**區間數**而非**紀錄數**成長。

### 2. 首次執行、空狀態與升級

- [ ] **這個修正本身，會不會在升級後刪掉資料？** 行為修正會被套用到「舊行為」寫下的既有狀態上，而升級後的第一次排程執行，是在無人看管的情況下動作的。
  *v1.13.56 讓清理排程改為採用它自己的 `retention_days`——單獨看是正確的，但某站台排程頁顯示「200 Days」而 config.yaml 為 1095、實際保留 3 年，下一次 04:00 執行就會刪光 200 至 1095 天之間的所有歸檔。v1.13.57 改為在啟動時對帳：絕不縮短前一版本原本保留的範圍，同時記錄兩個數值，並讓操作者自行選擇是否套用。*
- [ ] 哪一個方向具破壞性？只自動套用**安全方向**，破壞性方向必須由操作者明確執行。
- [ ] 變更某個**預設值**，會不會改變所有「從未設定過它」的站台行為？
  *`retention_days` 之所以維持 1095，正是為此——調低它會讓所有未明確設定的站台無聲縮短保留期，而下一次清理就會刪掉這些站台仍預期存在的資料（v1.13.57）。*

- [ ] 全新安裝、尚未設定、零筆歸檔：不可當機，也不可出現誤報。
  *硬體規格建議在讀不到 `/proc/meminfo` 時回報「ok」——這是無法支持的宣稱（v1.13.50）。*
- [ ] 對新目標／新資源的**第一次**使用，而不只是穩定狀態。
  *對新索引名稱的首次 Bulk 匯入**必定失敗**：建立 Graylog 索引集合只會寫入 MongoDB 中繼資料，索引與 deflector 別名要等 deflector 被循環才會建立（v1.13.53）。*
- [ ] 新建立的遠端資源是否需要時間才能使用？請**輪詢就緒狀態**，不要假設，也不要只固定睡一段時間。
  *在循環後不到 1 秒就寫入，文件會落在隨後被 Graylog 取代的索引中，回報為「已寫入」卻無聲消失（v1.13.54）。*

### 3. 模式與拓撲切換

- [ ] 用**另一種模式**跑同一件事：模式 A 寫下的狀態，模式 B 讀得懂嗎？
  *API 模式歸檔的 `stream_id` 為 `NULL`，而判斷規則 `stream_id NOT LIKE '<前置碼>%'` 永遠比對不到，導致在 API 與 OpenSearch 兩種歸檔間切換時，同一批 log 被存兩次（v1.13.55）。*
- [ ] 兩種模式對**邊界**的認知一致嗎？
  *API 區塊由請求時間切分（10:43:58–11:43:58），OpenSearch 區塊對齊整點（11:00–12:00），因此「單一歸檔完整包含此區塊」跨模式永遠不成立（v1.13.55）。*
- [ ] 共置同一台主機 vs. 分散在不同主機。
  *規格建議曾為「執行在另一台主機上的 OpenSearch」編列約 8 GB 的幽靈需求（v1.13.47）。*
- [ ] 宣稱「繞過」某元件的快速路徑，仍然會操到同一台機器。
  *Bulk 匯入當初刻意設計為「無 back-pressure」，理由是它繞過 Graylog——但它操的是同一個 OpenSearch 與同一份記憶體，而且快 5–10 倍（v1.13.48）。*
- [ ] 是否把**部分性**的資料當成完整？經串流篩選的歸檔或同前置碼的姊妹索引都只有該時段的一部分，若視為已涵蓋，會略過匯出並遺失其餘資料（v1.13.55）。

### 4. NULL、邊界與格式

- [ ] SQL 三值邏輯：`NULL NOT LIKE 'x%'` 的結果是 NULL,**不是成立**。請明確比對 `IS NULL` 或以 `COALESCE` 包裹（v1.13.55）。
- [ ] `0` 是否為合法值，卻被當成「未知」處理？
  *`if remaining:` 把數量 0 當成假值丟棄，導致已完全歸檔的索引仍執行一次必然為空的掃描（v1.13.53）。*
- [ ] 遠端系統所要求的日期／時間**格式**。
  *Graylog 將 `timestamp` 對應為 `uuuu-MM-dd HH:mm:ss.SSS`，傳入 ISO-8601 會回報 `parse_exception`；範圍篩選必須帶明確的 `format`，否則會出錯——更糟的是完全篩不到（v1.13.53）。*
- [ ] 時區：歸檔時間是無時區的本地時間，重新匯入的訊息在 Asia/Taipei 會落在約 8 小時之前。任何時間斷言都必須納入此偏移。
- [ ] 網格對齊的差一錯誤（`k = max(0, floor((first - t_from)/step))`）。

### 5. 中斷與不一致

- [ ] 取消必須在長時間操作**內部**輪詢，而非只在單位之間檢查。
  *在忙碌主機上，一個 500 筆的批次可能耗時數十秒，使「取消」看起來像沒有反應（v1.13.45）。*
- [ ] 長時間等待必須可中斷（固定的 `sleep(5)` 與 30 秒暫停迴圈曾忽略取消與使用者的繼續操作）。
- [ ] 資料庫與磁碟說法不一致：某份歸檔的**檔案**被刪除時，不能永遠略過該時段。
  *`verify` 會標記為 `missing`，而重複判斷只採計 `completed`，因此下次匯出會精準補回該時段——已由 e2e 步驟 [6] 斷言。*
- [ ] 單一毀損或截斷的項目應只讓**該項目**失敗，而非中止整個作業。
- [ ] 鎖、佔用標記與記憶體中的登錄表，都要在 `finally` 釋放。

### 6. 資源上限

- [ ] 限制的是**請求大小**，還是只有筆數？
  *`batch_docs=10000` 在 9 KB 的 Windows 事件記錄下會產生約 93 MB 的 `_bulk` 請求；OpenSearch 預設 `http.max_content_length` 為 100 MB，且整個請求會先放在協調節點的 heap（v1.13.49）。*
- [ ] **讀取端**也要問同樣的問題。
  *一頁 10,000 筆的搜尋結果，在寬欄位文件下約 90 MB——這是 fetch 階段的 heap 尖峰，加上我方同等規模的解析（v1.13.49）。*
- [ ] 看**尖峰**記憶體而非穩定值——OOM killer 看的是尖峰。
- [ ] 磁碟：目前**設定的保留期間**真的放得下嗎？
  *`retention_days` 預設 1095 天（3 年）；以實測每月約 557 GB 計算需要約 19.6 TB，因此在 2.8 TB 的磁碟上，清理作業其實約 5 個月就開始刪資料（v1.13.52）。*

### 7. 無聲失敗

- [ ] 關鍵邏輯外層不可有 `except: pass`——請記錄下來。
  *少了一個 `import json` 就讓分頁大小防護完全失效，而所有測試仍然全過（v1.13.50）。*
- [ ] 失敗是否真的會**呈現**給操作者？
  *排程匯出的失敗路徑呼叫 `create_job`，卻被包在一個總是失敗的 try/except 中，因此匯出壞掉時「作業歷程」空無一物，只有 `last_run` 有更新。*
- [ ] 「成功」是否代表資料真的在？請在**目的端**驗證。
  *Bulk 回報 4,900 筆已寫入，而那些文件隨後被 Graylog 取代（v1.13.54）。*
- [ ] 清理／維運指令，真的刪得掉它自己建立的東西嗎？
  *`streams-cleanup` 以串流**名稱**比對，但 Bulk 建立的串流叫「jt-glogarch Restored (&lt;前置碼&gt;)」——它找到 0 筆，在唯一的用途上無聲失效（v1.13.51）。*

### 8. 進度與感受

- [ ] 進度的**分母**是否等於實際要處理的量，分子是否也會因**被略過**的工作而前進？（「0%」持續 14 小時——v1.13.53。）
- [ ] 不要把介面綁在單一傳輸通道上。
  *進度條只由 SSE 串流更新，串流一卡住進度條就凍結，即使工作仍在前進、輪詢也有最新資料（v1.13.44）。*
- [ ] 暫停或節流狀態有沒有**明講**？靜止的進度條會被讀成「卡死」（v1.13.42）。
- [ ] 顏色要正確傳達嚴重性：資訊性文字不可看起來像警告（橘色資訊行曾讓客戶誤解——v1.13.41）。

### 9. 測試盲點

- [ ] **每一條**匯入／匯出路徑都有對應的 e2e 步驟嗎？
  *Bulk 從未被涵蓋，因此整檔 `json.load()` 的 OOM 風險存活了很多個版本（v1.13.48）。*
- [ ] 測試是否替**產品本身該建立**的狀態代勞？
  *e2e 自行預建 Bulk 的索引與別名，既遮蔽了首次匯入的錯誤，又與 Graylog 的建置產生競爭（v1.13.54）。*
- [ ] 如果該功能被無聲停用，這個測試還會通過嗎？若會，它就沒有在測那個功能。
- [ ] 測試會自行清理嗎？殘留狀態會改變下一次執行的程式路徑——這正是首次匯入錯誤被掩蓋數個版本的原因。

## 執行測試

```bash
# 完整測試 + 產生 TEST-RESULTS.md（每次 push GitHub 前必須執行）
./scripts/run-tests.sh

# 或手動執行：
python3 -m pytest tests/ -v

# 只跑單元測試（快速，不需外部服務）
python3 -m pytest tests/ -v --ignore=tests/test_integration.py

# 只跑整合測試（需要可連線的 OpenSearch）
python3 -m pytest tests/test_integration.py -v

# 版本 + 結構檢查
./scripts/check-version.sh
```

## 測試結果檔

`TEST-RESULTS.md` 由 `./scripts/run-tests.sh` 自動產生，每次 push GitHub
前必須一起 commit。記錄：通過/失敗狀態、版本、時間、平台、完整 pytest
輸出、版本檢查結果。

最新結果：[TEST-RESULTS.md](TEST-RESULTS.md)

## 安全掃描（較大版本異動）

每次**較大版本異動**（minor／major，例如 `1.11.0`、`2.0.0`——例行 patch 除非動到 Web 介面否則不需）
在視為完成前，都必須通過 **OWASP ZAP** 掃描。**所有 findings 都要修到「高／中／低」風險為零**
（或以文件化理由抑制誤判）。

```bash
# Baseline（被動：spider ＋被動規則，不送攻擊 payload、不會改資料）
docker run --rm -t zaproxy/zaproxy zap-baseline.py -t https://<host>:8990

# Full 主動掃描會送 SQLi/XSS payload、可能透過 API 建立/修改資料——
# 只在乾淨／測試實例、且經明確同意後才執行。
```

應用已透過 `SecurityHeadersMiddleware`（`glogarch/web/app.py`）設好完整的標頭/cookie 基線：
嚴格 CSP、HSTS、`X-Frame-Options: DENY`、`nosniff`、Referrer/Permissions-Policy、COOP/COEP，
以及 `HttpOnly; SameSite=Strict; Secure` cookie——因此 ZAP 最常見的標頭/cookie findings 已先擋掉。

每次掃描報告存到 `zap/<YYYY-MM-DD>/`（JSON ＋摘要）。**不要 commit 到 GitHub**（含掃描目標主機）——`zap/` 已在 gitignore。
