# jt-glogarch 測試清單

**語言**： [English](TESTING.md) | **繁體中文**

每次發版前必須全數通過。在專案根目錄執行：

```bash
./scripts/run-tests.sh
```

---

## 自動化測試（157 筆）

### 單元測試

| # | 測試檔 | 筆數 | 覆蓋範圍 |
|---|---|---|---|
| 1 | `test_audit.py` | 28 | 稽核解析器（帳號解碼、分類、敏感判定、噪音過濾、syslog/JSON 解析、process_raw_entry）、設定預設/自訂/YAML/缺欄位/無區段、DB 寫入/列表/統計、token 解析、獨立稽核保留期限清理、清理 fallback、通知事件 |
| 2 | `test_sanitize.py` | 10 | 密碼/Token/URL/JSON/Basic Auth/Bearer 脫敏、截斷、無誤殺 |
| 3 | `test_local_admin.py` | 9 | SHA256 hash、帳號必須 `localadmin`、Graylog 拒絕不 fallback、Graylog 離線有/無 hash、向下相容 |
| 4 | `test_upgrade_script.py` | 9 | upgrade.sh 存在 + 5 步驟、root 檢查、版本顯示、README 引用、systemd 預設=Yes、git clone sudo、retention_days 遷移、op_audit retention_days 預設值 |
| 5 | `test_repo_structure.py` | 8 | pyproject.toml 在根目錄、無 src/ 目錄、deploy 檔案、README/CHANGELOG/CONFIG 存在、版號同步、github/glogarch 與 source 一致 |
| 6 | `test_bulk_import.py` | 7 | 保留欄位剝除、deflector alias、stream 改寫、marker 欄位、dedup id/none |
| 7 | `test_notify_format.py` | 7 | 狀態 emoji（✅/⚠️/❌）、每行一項、URL 縮短、en/zh-TW key 一致 |
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
- [ ] 指令碼印出 `RESULT: ALL PASS`

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

### 測試結果

- [ ] `./scripts/run-tests.sh` 通過 — `TEST-RESULTS.md` 已產生
- [ ] `TEST-RESULTS.md` 已 commit 到這個版本

---

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
  *`retention_days` 之所以維持 1095,正是為此——調低它會讓所有未明確設定的站台無聲縮短保留期，而下一次清理就會刪掉這些站台仍預期存在的資料（v1.13.57）。*

- [ ] 全新安裝、尚未設定、零筆歸檔：不可當機，也不可出現誤報。
  *硬體規格建議在讀不到 `/proc/meminfo` 時回報「ok」——這是無法支持的宣稱（v1.13.50）。*
- [ ] 對新目標／新資源的**第一次**使用，而不只是穩定狀態。
  *對新索引名稱的首次 Bulk 匯入**必定失敗**：建立 Graylog 索引集只會寫入 MongoDB 中繼資料，索引與 deflector 別名要等 deflector 被循環才會建立（v1.13.53）。*
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
  *`batch_docs=10000` 在 9 KB 的 Windows 事件記錄下會產生約 93 MB 的 `_bulk` 請求；OpenSearch 預設 `http.max_content_length` 為 100 MB,且整個請求會先放在協調節點的 heap（v1.13.49）。*
- [ ] **讀取端**也要問同樣的問題。
  *一頁 10,000 筆的搜尋結果，在寬欄位文件下約 90 MB——這是 fetch 階段的 heap 尖峰，加上我方同等規模的解析（v1.13.49）。*
- [ ] 看**尖峰**記憶體而非穩定值——OOM killer 看的是尖峰。
- [ ] 磁碟：目前**設定的保留期間**真的放得下嗎？
  *`retention_days` 預設 1095 天（3 年）；以實測每月約 557 GB 計算需要約 19.6 TB,因此在 2.8 TB 的磁碟上，清理作業其實約 5 個月就開始刪資料（v1.13.52）。*

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
