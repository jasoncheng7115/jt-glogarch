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
| 8 | `test_notify_test_endpoint.py` | 8 | Discord/Slack/Teams/Telegram/Nextcloud Talk/Zulip/Email 送出函式參數、共用的管道清單正確呼叫每個管道 |
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
- [ ] **巢狀 URI 要以巢狀資源命名，而非其上層**
      （`tests/test_audit_operation_labels.py`）——建立 API token 是
      `user.token_create` 而非 `user.modify`；刪除串流規則是 `stream_rule.delete`
      而非 `stream.delete`。白名單由細到粗排序，操作名稱由它決定，而不是由寬鬆的
      敏感樣式清單決定
- [ ] **每一條敏感樣式都要有一個能寫進資料庫的範例請求**——白名單沒有保留的樣式，
      只會示警而不留任何紀錄
- [ ] token 的項目名稱要指出是哪一把（`local:admin / token 'backup-tool'`），以 token
      值刪除時不得顯示祕密的任何片段
- [ ] Graylog 正常運作但超過 10 分鐘未收到 syslog → 心跳警報
- [ ] 篩選下拉選單顯示正確語言標籤（Method/Status 對 方法/狀態碼）

### 客戶安裝 / 升級模擬

- [ ] 複製 `github/` 到暫存目錄 → `pip install` 成功
- [ ] `deploy/install.sh` 路徑正確、systemd 預設 = Yes
- [ ] `deploy/upgrade.sh` 可正常執行（db-backup → git pull → install → restart → verify）
- [ ] **上游歷史被改寫時不能擋住升級** —— 已發布的歷史一旦被強制推送，既有的 clone
      都會與遠端分岔，`git pull --ff-only` 必定失敗。`upgrade.sh` 要能判斷「同時領先又
      落後」並說明原因，把安裝重設到 `origin`；若失敗原因不是歷史分岔，仍必須明確中止
      升級（`tests/test_upgrade_divergence.py` 會把出貨指令碼裡的復原區塊，對一組真正
      分岔的儲存庫實際執行）
- [ ] **DB 備份確實產出檔案** —— 升級後 `/var/backups/jt-glogarch/` 會多一個新的
      `jt-glogarch-*.db` 快照。偵測指令曾在 root 的工作目錄下執行、對 `./config.yaml`
      拋 `PermissionError`，於是**無聲略過備份**卻印出看似正常的「not available」
      （v1.13.82）。`test_upgrade_script.py` 已釘住偵測必須在 `$INSTALL_DIR` 下執行。

**離線（air-gapped）安裝／升級（v1.14.5）** —— 靜態檢查在
`test_static_sweeps.py::test_offline_bundle_can_do_a_first_install` 與
`::test_report_engine_install_is_verified_not_assumed`；人工驗證必須在真的把網路
封掉的 VM 上做（不是「我們沒有用到網路」而已）。

- [ ] **離線套件能安裝到從未連過網的主機** —— `bash scripts/build-offline-bundle.sh`
      建置後把 tarball 搬到一台沒有 jt-glogarch、也連不到 PyPI 的主機，執行
      `sudo bash install-offline.sh`，接著 `systemctl enable --now jt-glogarch`
      並開啟 `/setup`。*v1.14.5 之前這件事做不到：離線套件只能升級曾經連過網的
      主機。*
- [ ] **兩支離線指令碼不會互相越權** —— 在全新主機上執行 `upgrade-offline.sh` 會
      指向 `install-offline.sh` 而不是就此中止；在已安裝的主機上執行
      `install-offline.sh` 會拒絕並導向升級指令碼（只有升級指令碼會先備份資料庫）。
- [ ] **pip 真的完全不碰網路** —— 移除預設路由後再安裝一次。`--no-index` 是明確
      指定的；一旦退回 PyPI，會卡上好幾分鐘才失敗。
- [ ] **Python 次版本不符會在動任何檔案之前就擋下** —— 把 `cp310` 套件放到
      Python 3.12 主機上，必須明確指出版本不符而中止，而不是安裝到一半才丟出
      編譯 wheel 的 ImportError。
- [ ] **算繪引擎是驗證過的，不是假設的** —— 每支安裝指令碼都會執行
      `verify_report_engine`，以 `jt-glogarch` 身分實際啟動 Chromium 並產出 PDF。
      在缺少作業系統函式庫的主機上，必須印出（由 `ldd` 取得的）缺少的 `lib*.so`
      名稱，結尾摘要必須說明 PDF 報表無法運作，同時說明封存與還原不受影響。
      *tarball 帶不動那些函式庫，離線模式又跳過 `playwright install-deps`，
      「裝好了」與「能用」是兩回事；過去升級會回報成功，幾小時後的排程報表才失敗。*
- [ ] **吞掉什麼就記錄什麼** —— 任何新增 `except` 的變更之後，執行
      `test_silent_except_count_only_goes_down`（預算 15，只能往下降）與
      `test_remaining_silent_excepts_are_narrow`（任何位置都不得再出現什麼都不做的
      廣泛 `except`）。*記錄裡看不到的降級，就是沒有人能診斷的降級。*

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
- [ ] **httpx 信任的憑證包是最新的**（`tests/test_tls_trust.py`）：兩份 `pyproject.toml` 都保留
      `certifi >= 2026.10.19`，且已安裝的憑證包不含「emSign ECC Root CA - G3」（GHSA-6q48-6c7w-9gw2）。
      httpx 讀的是 certifi，不是作業系統的憑證庫——只更新系統的 `ca-certificates`，通知管道仍然暴露。
      升級路徑：在裝有舊版 certifi 的主機上，`upgrade.sh` 跑完後必須是 2026.10.19 以上
      （由它的 `[report]` 相依套件步驟套用下限）
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
- [ ] **OpenSearch 直連掃描若讀到的筆數少於索引宣稱的，該索引必須失敗** —— 不可
      回報成功。`iter_index_docs` 會以掃描前的 `_count` 對帳，短少即拋出
      `IncompleteIndexScan`。*游標是 `(timestamp, _doc)`，而 `_doc` 只在 shard
      內唯一，所以多 shard 索引的分頁邊界可能排除一筆從未被回傳的記錄——而已寫出
      的區塊又被記錄為涵蓋該時段，缺口會被重複資料刪除邏輯在之後每次執行都藏起來。
      正式環境的索引是 4 個 shard，e2e 叢集只有 1 個，這就是為什麼任何資料路徑
      測試都不可能抓到它。*
- [ ] **取消匯出絕不可記錄不完整的小時** —— `test_export_cancel_paths.py`（執行期
      測試，兩個真實匯出器搭配假後端）：只靠旗標在索引中途取消，只會記錄**完整**的小時
      （`..._never_records_a_partial_hour`），而下一次執行會把被丟棄的小時完整補回
      （`..._resumes_from_the_discarded_hour`）。*`break` 跳出後落到「關閉最後一個
      writer」，把掃到一半的小時蓋成完整；重複資料刪除從此把它的尾段藏起來。排程執行
      必走這條路。*
- [ ] **每一條取消路徑都以 CANCELLED 結束，絕不是 COMPLETED 或 FAILED** —— 同一個
      檔案：旗標路徑（排程）、回呼路徑（Web UI）、Phase A 重複資料刪除迴圈、API chunk 中途、
      反壓暫停（`test_backpressure_pause_honours_cancel`）。任何一條都不送錯誤通知。
      人工：在作業顯示「已暫停——來源負載過高」時按取消，確認一個暫停 tick 內就停，而
      不是 30 分鐘。
- [ ] **取消的作業列要誠實** —— `messages_done` = 磁碟上的實際數、`messages_total`
      保留計畫分母、`progress_pct` 停在中斷處（不是 100）、沒有「Covered all N index
      set(s)」也沒有綠色涵蓋徽章、備註說明進行中的小時已丟棄。匯出頁面顯示「已由使用者
      取消（N 筆）」而不是「已完成！」。發版指令碼：`scripts/ui-cancel-test.py` 現在會
      真的取消一個 OpenSearch 直連**匯出**（不只匯入）並斷言以上全部。
- [ ] **取消與反壓絕不可被回報成資料遺失** —— 中途跳出掃描會關閉產生器，對帳
      因此不可執行。使用者按下取消，不該被告知歸檔掉了資料。
- [ ] **在繁忙叢集上要限制時窗** —— `E2E_WINDOW_HOURS=2 bash
      scripts/e2e-archive-test.sh` 會把 `--days 1/3` 的匯出換成固定時窗。
      *每小時吞吐約 950 萬筆的正式 Graylog，`--days 3` 等於數千萬筆與數小時的負載。*
- [ ] **不要對正式 Graylog 執行步驟 [3]（GELF 回匯）** —— 它會把封存匯回**線上**
      索引集合，在繁忙叢集上等於數十萬筆重複的正式訊息。完整往返屬於測試叢集；
      正式機只跑唯讀與使用獨立索引的步驟。
- [ ] **4 分片索引必須被完整掃描** —— e2e 步驟 [8] 會刻意建立一個 4 分片索引，
      每個時間戳放 30 筆文件讓排序鍵在分片之間相撞，並要求全部文件依時間順序
      回傳。*`tests/test_os_shard_scan.py` 會穩定重現該筆數遺失；e2e 這一步存在
      的理由是正式環境有 4 個分片、這座測試叢集只有 1 個，而那正是一個真實的
      掉資料錯誤能藏一輩子的原因。任何新的掃描／游標改動，兩者都必須保留。*
- [ ] **每個分片請求都要釘住主副本**（`_shards:N|_primary`）—— 只寫 `_shards:N`
      可能在主副本之間輪替，而兩者的 `_doc` 順序不同，等於把要修的錯誤再引回來。
- [ ] **合流後仍維持時間戳遞增** —— 匯出端一旦跨過小時邊界就會關閉並寫入該分塊的
      封存記錄，若掃描對每個分片都從頭走一次時間軸，就會去敲已經寫過的分塊。
- [ ] **峰值記憶體不得增加** —— 每個分片同時持有一頁、預抓一頁，因此位元組預算要
      除以 2N。請用寬文件（約 9 KB）驗證：
      `test_bytes_in_flight_stay_within_the_single_page_budget`。
      *那個 500 筆的頁面下限是為「單一游標」設計的，套到每個分片上就無聲地變成
      36 MB 的記憶體下限——而那台機器正是會被 OOM killer 砍掉的那台。*
- [ ] **單分片索引的掃描方式必須與過去完全相同** —— 不發出任何分片請求、沒有新
      行為，小型部署與這座測試叢集都不必為這個修正付出代價。
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
      *醒目提示是用記錄內容組 HTML：先各自跳脫、再插入標記，順序反過來就是 XSS。*
- [ ] **搜尋要讓路給歸檔** —— 匯出或匯入持有鎖時，每份歸檔之間會暫停，並在畫面
      上說明
- [ ] **介面要說明適用範圍** —— 這是掃描而非查詢引擎，需要完整分析請匯回 Graylog
      單元測試：`tests/test_search_engine.py`、`tests/test_search_api.py`

- [ ] **儀表板的統計數值絕不能被裁切** —— UI smoke 會以真實瀏覽器，將算繪後的
      文字寬度與卡片寬度比對，涵蓋數千到 10^18 的量級。*`.stat-card` 為折線圖設了
      overflow:hidden，因此 1,060,702,960 筆被顯示成 `1,060,702,96`（v1.13.93）。
      算繪後的字體寬度，沒有任何 Python 測試量得到——這一項必須用瀏覽器。*
- [ ] **「歸檔涵蓋天數」算的是有歸檔的日數，不是起訖跨度** —— 一筆很舊的零星歸檔
      不能把它拉長，已刪除的歸檔不計入，結束在本地午夜的那一小時算在開始那天，
      中間沒有歸檔的日期要列出。單元測試：`tests/test_archive_day_coverage.py`。
      在 .36 目視：卡片的數值、日期範圍、「其中 N 天沒有歸檔」與滑鼠移上去的日期，
      淺色與深色主題都看。*.36 在 01-01 有一筆歸檔，之後到 02-11 才再有：
      跨度是 307 天，實際有歸檔的是 266 天。*
- [ ] **只有具備允許角色的 Graylog 帳號能登入** —— Reader 帳號（密碼或權杖）被拒並回
      `role_not_allowed`，也拿不到 API 權限；Admin、`*` 權限，以及加進
      `web.allowed_graylog_roles` 的角色可以登入；讀不到角色時拒絕登入；1.18.2 以前的
      session 視為已登出。單元測試：`tests/test_login_roles.py`。實機：拋棄式 Graylog
      6.3 與 7.x，建立 Reader 帳號與權杖（1.18.2 兩個版本都跑過）。
- [ ] **在排程頁儲存的清理保存天數，重新啟動後仍保留** —— 存一個比
      `retention.retention_days` 短的值，重新啟動後頁面仍顯示它。單元測試：
      `tests/test_cleanup_schedule_retention.py`
      （`test_retention_saved_through_the_api_survives_the_startup_reconciliation`）。
      *1.13.57 的升級保護每次啟動都跑，2026-11-03 部署時把 .36 的 150 天改回 1095。*
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
- [ ] **通知要寫出數字**（`test_overflow_notice_states_how_many_were_not_read`、
      `tests/test_overflow_holes.py::test_truncation_record_carries_the_count`）：
      每個時間點那行寫「該毫秒共 N 筆：已保留 10,000，未讀取 M」。Graylog 的 `to` 不含端點——
      計數必須查 `[ms, ms + 1)`；`from == to` 會計得 0，數字就無聲地消失。測試中的假 Graylog
      也必須不含端點（包含端點的版本讓這個問題一直通過）。實機：收到溢出通知時，未讀取的數字
      等於 OpenSearch 對該毫秒的計數減 10,000。標題不得寫「少數」。
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

### 溢出的洞（v1.14.8）

- [ ] **對溢出的那個小時執行 OpenSearch Direct，只會抓回缺少的那一毫秒** —— e2e 步驟
      [9]：在同一毫秒灌入 10,500 筆、API 匯出記下溢出、OS Direct 重跑恰好補回 500 筆。
      `tests/test_overflow_holes.py` 釘住 `covered_ranges()` 的洞，以及**兩條**重複資料刪除規則
      都看得到它。*通知給的補救方法過去會被該小時自己的 API 封存重複資料刪除掉。*
- [ ] **溢出通知寫出未讀取的筆數** —— 「（該毫秒共 N 筆：已保留 10,000，未讀取 K）」。
      `test_truncation_record_carries_the_count`。
- [ ] **升級會新增 `archives.overflow_ms`** —— `upgrade-compat-test.sh`（自動遷移；
      可為空、只增不改）。

### 統計報表——一次性起迄時間（v1.14.9）

- [ ] **「產製」會先開啟一次性範圍對話框**（`ui-sim-test.py`）：兩個 datetime-local
      輸入框、說明文字寫明只用於這一次、取消可關閉。兩欄留空就用報表設定的範圍。
- [ ] **範圍只用於這一次、絕不寫回**（`tests/test_report_adhoc_range.py`）：
      `effective_window()` 覆蓋小工具各自的範圍與對齊午夜，並把**相同**的起迄餵給兩種
      儀表板模式；API 對只填一欄／顛倒／無法解析／超過 400 天的範圍在執行前就回 400；
      事後儲存的 `config_json` 逐位元組相同；作業備註記下該範圍。
- [ ] 人工：以過去某一週為範圍產製一份報表，確認封面期間顯示那一週，再確認報表設定頁
      仍是原本的範圍。

### 日文介面與通知（v1.15.0）

- [ ] **日文翻譯完整且未破壞格式**（`tests/test_i18n_ja.py`）：key 與英文相同、
      保留每個 `{placeholder}` 與 HTML 標籤、沒有繁體中文專用字形、日文旁沒有半形
      `,;!?`；每個頁面的 `#lang-select` 都提供 `i18n.js` 定義的所有語言；排程說明直接
      執行 `cronHuman()` 驗證。
- [ ] **繁中規則只套用在繁中區塊**（`test_static_sweeps.py` 的 `_i18n_spans`）：在
      zh-TW 後面新增語言時，不能被台灣用語／全形標點檢查掃到。
- [ ] **切換後確實顯示日文**（`ui-smoke.py`、`ui-sim-test.py`）：登入頁與側邊欄出現
      假名；每一頁依序切換 zh-TW／ja／en 且沒有 console 錯誤。
- [ ] **日文通知**（`tests/test_notify_ja.py`）：範本 key 與 placeholder 與英文一致；
      實際產生的匯入完成通知為日文。人工：把通知語言設為日本語並送出測試通知。
- [ ] 人工：在 staging 以日文開啟初始設定精靈、登入頁與設定頁——介面框架沒有殘留英文，
      側邊欄沒有文字溢出。
- [ ] **日文 PDF 報表**（`tests/test_report_ja.py`）：每個報表字串表的每個英文 key 都有日文；
      各輔助函式（時間範圍、筆數、資料不完整警告、時間間隔調整說明）實際回傳日文；
      **`glogarch/report/` 裡任何以 `== "zh-TW"` 分支的函式都必須處理 `"ja"`**（防止新字串
      無聲地退回英文）；日文報表使用日文字形；報表表單提供日本語，新報表跟隨介面語言。
- [ ] 人工：在 log4 產生一份日文報表（封存摘要＋一個重建的儀表板），將頁面轉成 PNG，
      逐一檢查封面、目錄、表格註記、頁首頁尾與浮水印——沒有退回中文、沒有缺字方塊。

### 作業列表保持最新、取消以即時狀態確認（v1.15.1）

- [ ] **已結束的作業不能取消**（`tests/test_job_cancel_stale_view.py`）：完成／失敗／已取消
      → 409 並附上實際狀態，狀態不變、不留取消旗標；執行中的作業仍可取消；不存在的 ID → 404，
      不留旗標。
- [ ] **列表會自己更新**（`ui-sim-test.py` 第 7 步，導向模擬的 `/api/jobs`）：作業狀態改變時，
      作業歷程會自行更新。
- [ ] **過時的取消會被說明、不會送出**（同一步）：在仍顯示執行中、但伺服器已結束的列上按取消，
      會顯示「已經結束」，而且不會送出取消請求。
- [ ] 人工：用兩個不同帳號、兩個瀏覽器開啟作業歷程，在其中一邊取消一個測試用匯出——另一邊
      不必重新整理，約 5 秒內就顯示已取消。
- [ ] **多管理員防護**（`tests/test_multi_admin_guards.py`）：編輯排程保留 `enabled` 與 `server`；
      該伺服器匯出中時立即執行（匯出）回 409、不留紀錄、不更新上次執行；立即執行（清理／驗證）在
      長期存在的事件迴圈上立即回應、使用「排程」的保存天數、第二次執行回 409；過時的稽核切換回 409
      且不變；被排程／報表使用的伺服器不能刪除；正在匯入的歸檔不能刪除；正有匯入寫入的索引集不能
      清除；排程匯出會發布即時進度。
- [ ] **透過真正的對話框編輯排程**（`ui-sim-test.py` 第 8 步）：停用的測試用排程維持停用並保留
      伺服器。

### Graylog 7 的匯出 heap 保護：GC 指標、控速、暫存的搜尋結果（v1.16.0）

- [ ] **GC 判斷**（`tests/test_health_guard_gc.py`）：健康的 80%～94% 使用率鋸齒、沒有 Full GC
      時，用 GC 指標不會暫停（設為 `health_heap_signal: used` 時會暫停）；發生 Full GC、GC 剛結束
      heap 仍 `>=` 硬上限，或連續兩次 GC 時間 `>=` `health_gc_overhead_pct` 時會暫停；Graylog
      重啟（計數歸零）不會誤觸；沒有 GC 指標時退回使用率判斷；journal 與 buffer 照樣監看。
- [ ] **控速**（同一個檔案）：GC 後 heap 在 `health_pace_start_pct` 以下時每頁不等待，之後線性增加，
      到 `jvm_memory_hard_pct` 時為 `health_pace_max_delay_sec`；OpenSearch 直連或沒有 GC 指標時
      一律不控速；API 匯出每一頁都會呼叫 `guard.pace()`。
- [ ] **因 heap 暫停時會讓 Graylog 釋放過期的搜尋結果**：超過 `health_search_cache_flush_sec` 才送，
      每分鐘最多一次，heap 降下來就恢復；因 journal／buffer 暫停時不送。
- [ ] **對真的 Graylog 測試（.83，絕不用正式環境）**：調低門檻做一次 API 匯出，記錄出現
      `export pacing adjusted`，延遲隨 Graylog 的 GC 後 heap 上升而增加；強制一次因 heap 暫停，
      記錄出現 `asked Graylog to release expired search results searches=8`。
- [ ] **在 staging 實跑一晚**，同時對來源 Graylog 做唯讀 GC 取樣：總耗時和前幾晚比較、各原因的
      暫停次數、沒有因「did not drain」停止、執行期間的 Full GC 次數。

### 熱點加速、GELF 重新連線、反壓停止（v1.16.1）

- [ ] **快速路徑結果完全相同**（`tests/test_fast_paths_equivalence.py`）：固定格式的時間解析和它前面
      的 strptime 迴圈從不產生不同結果（邊界案例加 4,000 筆模糊字串，兩組格式都測）；GELF 與
      OpenSearch 直連的解析結果和舊函式一樣（結尾的 `Z` 照舊當成本機時間、丟出一樣的例外）；欄位型別
      追蹤和 isinstance 判斷鏈相同（含子類別與 2^63）；重複使用的 encoder 輸出和 `json.dumps` 位元組
      完全相同。封存 JSON 的空白格式刻意不改，因為記錄搜尋的預先篩選是比對原始位元組。
- [ ] **GELF 送出每一筆都有交代**：沒有異常時全部送達；接收端（獨立 thread）中途重置時，會被偵測到並
      計入 `reconnects`，只會遺失當下還在傳送中的資料；連線已關閉時會丟出錯誤，不會無聲地丟掉寫入。
      對真的 Graylog（.83）：新舊版都送出 30,000 筆、收到 30,000 筆。
- [ ] **重新連線過的 GELF 匯入不會標示為「已驗證」**：0 個索引失敗但有重新連線時，結果與作業紀錄
      都出現「NOT verified」警告；沒有重新連線時仍顯示「Verified at target」。
- [ ] **反壓停止只結束一次**（`tests/test_backpressure_stop.py`）：保護機制丟出 `BackpressureStop`、
      自己不發通知；API 匯出在區段中途停止，不出現「Chunk N failed」，只保留完整的小時；OpenSearch 直連
      停止時不出現「Index X failed」，也不會碰下一個 index；手動執行只通知一次，排程執行交給排程處理；
      排程在 `health_stop_retry_min` 後只重試一次（不是 3 次快速重試）、只通知一次、不多出空的失敗紀錄，
      其他錯誤仍維持快速重試。對真的 Graylog（.83）：強制停止時只暫停一次就結束，並附上「stay archived」
      摘要。

### 伺服器訊息以介面語言顯示（v1.16.2）

- [ ] **經過翻譯，不是原樣顯示**（`tests/test_srv_messages.py`）：每個 `srv_*` 英文句型都存在於後端
      程式碼；繁中／日文保留所有佔位；每個句型都能透過真正的 `i18n.js` 翻成兩種語言；真實的組合備註
      都能翻譯；認不得的文字與英文介面維持不變；`fetchJSON()`、作業備註與初始設定精靈都經過翻譯。
- [ ] **在瀏覽器中**（`ui-sim-test.py` 第 7b 步）：英文的作業備註依介面語言顯示為中文／日文／英文。
- [ ] 新增會顯示給使用者的後端訊息時，在同一次修改中把它的 `srv_*` key 加進三個語言區塊（否則會顯示英文）。
- [ ] **升級會安裝已安裝 Playwright 所需的 Chromium 版本**（`tests/test_report_deps_browser_build.py`）；
      在 Playwright 版本有變的升級之後，staging 上的 `verify_report_engine` 會通過。

### jt-glogarch 底下的作業系統大版本升級（v1.16.3）：修改升級流程時必跑

- [ ] `bash scripts/os-upgrade-sim.sh` 印出 `RESULT: ALL PASS`（docker、ubuntu:24.04，模擬 22.04 → 24.04
      之後執行真正的 `upgrade.sh`：出現 Python 變更說明、資料庫已備份、已為 3.12 重新安裝、服務健康、
      每個排程都已註冊）。
- [ ] `tests/test_os_upgrade_paths.py` 通過；完整測試在目前支援的最新 Ubuntu 的 Python 上也通過（在該容器中執行）。
- [ ] `upgrade.sh` 中任何在重新安裝「之前」執行的新步驟，在已安裝的套件無法載入時（不同的 Python）也要能運作。

### 從作業歷程重試失敗的匯入（v1.16.4）

- [ ] **實際點擊，不是直接呼叫函式**（`ui-sim-test.py` 第 7c 步）：作業歷程 → 重試 → 按下真正的「確定」，
      會在「歸檔清單」頁開啟匯入對話框，並帶入該作業的歸檔、目標與模式。這個對話框只在「歸檔清單」頁的區塊中，
      所以從 v1.13.35 到 v1.16.3，在作業歷程按「確定」都會出錯而沒有反應。
- [ ] **模式依實際送到目標的情況決定**：完全沒匯入 → 用相同模式，並說明不會重複；Bulk 作業 → Bulk（依訊息 id 進行
      重複資料刪除）；已送出訊息的 GELF 作業 → GELF，並警告會重複（GELF 不會帶 `gl2_message_id`，所以任何模式都無法略過已建立索引的訊息）。
- [ ] 任何會開啟「另一頁」範本區塊中對話框的按鈕，都改成先切換到那一頁（`tests/test_retry_import_ui.py`）。

### OS 直連匯出的涵蓋說明與 Graylog 內建 index set（v1.16.5）

- [ ] 排程只選取放記錄的 index set：作業備註沒有 ⚠，並寫明「未包含 Graylog 內建事件索引集合：……」；作業歷程的標籤為綠色（`tests/test_index_set_coverage.py`）。
- [ ] 漏選放記錄的 index set 時，仍顯示「⚠ ……未涵蓋」與黃色標籤。

### 密碼自動完成（v1.16.5）

- [ ] `login.html`／`index.html` 中每個 `type="password"` 欄位與登入表單都有 `autocomplete="off"`（`tests/test_password_autocomplete.py`）。
      可用 `curl -sk https://<host>:8990/login | grep -E '<form|type="password"'` 確認。

### 外觀與樣式（v1.18.0）

全站共用的尺度在 `glogarch/web/static/css/refine.css`，顏色在 `style.css` 開頭的變數。`test_no_select_uses_the_browsers_own_dropdown` 防止原生下拉再次出現。

**人工，每次改樣式後**
- [ ] 每一頁的亮色與暗色，在約 1440 與 1180 像素寬：內容不超過頁面右側內距，數字不被裁切。
- [ ] 分別打開表單、對話框和側邊欄的下拉：清單沒有被切掉。
- [ ] 由程式設定值的下拉（系統設定的匯出模式）顯示正確的值。

### 內容套件頁面（v1.18.0）

**自動**：`tests/test_packs.py`（4 個真實套件、安裝檢查、套件庫、以仿照實測行為的假 Graylog 測試路由，以及發布邊界）。

**下載內容**：`tests/test_pack_guide.py` 涵蓋三種語言的說明文字、從套件讀出的內容、跳脫處理與 ZIP。`tests/live_packs_check.py` 以真瀏覽器下載，確認 ZIP 內有套件與使用說明。

**實機，真瀏覽器**：`tests/live_packs_check.py` 在真實 Graylog 上傳、修改、安裝、啟動、解除安裝並刪除一個暫時的 `ZZTEST` 套件，最後確認沒有殘留。它的串流只比對不存在的主機名，規則是 `when false`。要對正式環境執行前先詢問。

**敏感資料與版本**：`tests/test_packs.py` 涵蓋掃描、清除，以及每條離開路徑的拒絕。`tests/live_packs_check.py` 上傳通知裡含 email 的套件，確認到達 Graylog 的內容沒有 email，也確認 6.3 版下載確實經過轉換。

**人工**
- [ ] 沒有地端套件的站台，Jason Tools 頁只列出已公開的套件（Windows Active Directory、Linux 登入與 SSH、Apache HTTP Server、QNAP NAS），每一包都標示為公開，下載內容附有翻譯好的使用說明。`glogarch/jt_library/` 只要出現作者沒同意公開的套件，`tests/test_packs.py` 就會失敗。
- [ ] 開啟含多個看板的套件，逐一對照 Graylog 上每個分頁的版面。
- [ ] 看板預覽：滑鼠停在 widget 上不會出現瀏覽器提示；點一下會開啟本程式的提示框，列出 widget 查詢條件、分頁查詢條件和欄位；查詢文字可以選取，按「複製」會放進剪貼簿；按 Esc、點其他地方、捲動、切換分頁或關閉預覽都會收起。兩種主題、約 1436 px 寬都要看。
- [ ] 把有串流的公開套件分別裝到全新的 Graylog 7（預設 Message Processors 順序）和 Stream Rule Processor 在前的 Graylog：兩種都會解析，其他來源的記錄不會被加上它的欄位。
- [ ] 看板預覽：分頁選擇在滑鼠停住和選取時，兩種主題都看得清楚；圓餅圖和環圈圖的圖例在圖的下方。
- [ ] 以權限較少的帳號登入：安裝預覽會把無權讀取的項目列為未檢查。
- [ ] 規則標題已存在於目標的套件無法安裝，且原因會列出這些標題。

### 告警管理：批次管理 Graylog 事件定義與通知方式（v1.17.0）

寫入會直接改到真實的 Graylog，所以兩個實機層級都只能對「測試用」Graylog（.83）執行，絕不能對正式環境。
UI 測試用的 jt-glogarch 也必須指向那台測試 Graylog（在任何主機上用一份暫時的設定檔即可；`.36` 指向的是正式的 log4）。

**自動化**

- [ ] `tests/test_alerting.py`（32 項）：
      - 規劃：加入／移除／替換時，其他通知項目與它們的 `notification_parameters` 保持不變；
      - `schedule` 參數等於定義目前的狀態；
      - 預覽後被修改的定義會略過，期間被改的其他欄位會保留；
      - 單筆失敗不影響其他筆；登入過期會停止整個批次；可以取消；
      - Graylog 存成不同狀態時視為失敗；
      - 復原，包括「已送出但未確認」的變更也能復原；
      - 真正的 HTTP 用戶端：查詢參數、整份內容、`X-Requested-By`、401／403 對應、超過 200 筆的分頁；
      - 身分存放：機密不進 cookie、會過期、登出會清除；登入時保留的是 Graylog 工作階段而不是密碼；
      - API：一律回 403＋`need_signin`，從不回 401；一份預覽只能套用一次，且只限產生它的瀏覽器工作階段；拒絕不存在的通知方式；復原；
      - 以 node 執行真正的 `alerting.js` 篩選邏輯：同時符合、`-` 排除、詞組、`notif:`／`notif:none`／`tag:`／`prio:`／`state:`、快速篩選、Shift 範圍選取，且快速篩選的數字與健檢的數字一致。
- [ ] `GL_URL=http://<測試-graylog>:9000 GL_PASS=... python3 scripts/e2e-alerting-test.py` 顯示 `RESULT: ALL PASS`，內容是 30 個真實定義（其中 12 個停用）：
      - 全部加入通知：狀態不變，其他欄位逐位元組相同；
      - 預覽與套用之間被修改的定義會略過；
      - 替換通知；
      - 復原後完全回到原狀；
      - Graylog 系統內建定義從不被寫入；
      - Reader 角色的使用者改不了任何東西；
      - 結束後清理。
- [ ] `UI_URL=https://<指向測試-graylog 的-jt-glogarch>:8990 GL_URL=... GL_PASS=... RESTART_CMD='...' python3 scripts/ui-alerting-test.py` 顯示 `RESULT: ALL PASS`，全程真實點擊：
      - 用 Graylog 帳號登入；
      - 標籤、搜尋、Shift 點選、全選符合的結果；
      - 加入 → 預覽 → 套用，並「在 Graylog 中」確認結果：15 個都有新通知、另一個標籤的定義沒被動到、沒有狀態被改變；
      - 作業歷程有這筆作業；
      - 載入中狀態：攔住資料請求，確認工具列與表格有 spinner、每個 spinner 真的在轉、轉動的弧線與底圈對比足夠（≥ 2）、動作按鈕不能按；
      - 版面：工具列項目在同一條中線上、篩選標題在同一欄、每個分頁都以卡片承接頁籤、標題與描述的樣式不同；
      - 點選標題會開啟即時讀取的定義內容，並有連到 Graylog 的連結；
      - 從「變更紀錄」復原；
      - 健檢卡片、繁體中文；
      - 服務重新啟動後，頁面會要求重新登入 Graylog，且對話框可正常登入；
      - 沒有 JS 錯誤。

**人工（每次改到告警管理的版本）**

- [ ] 淺色＋深色主題、en／zh-TW／ja、400 px 寬的視窗：外觀與其他頁面一致（工具列卡片、分頁、表格、分頁按鈕）。
- [ ] 以 `localadmin` 登入：頁面要求登入 Graylog；之後的變更以那個 Graylog 使用者執行，稽核記錄兩者都列出。
- [ ] 沒有編輯權限的 Graylog 使用者：預覽可以載入，套用會在第一個定義停下並顯示「Graylog 拒絕你的帳號執行此操作」。
- [ ] 登出會關閉 Graylog 工作階段（`DELETE /api/system/sessions/{id}`）。

### Zulip 通知管道（v1.17.1）

**自動**

- [ ] `tests/test_notify_zulip.py`（8 項）：以真實 httpx client 搭配 MockTransport 檢查實際送出的內容——
      `POST {server}/api/v1/messages`、以 bot 電子郵件＋API 金鑰做 Basic 驗證、表單 `type=stream`、`to`、
      `topic`（預設 `jt-glogarch`）、內文放在程式碼區塊中；4xx 時顯示 Zulip 自己的錯誤文字
      （「HTTP 401: Invalid API key」）；設定不完整時不送出且回報失敗；訊息含 ``` 也不會提早結束程式碼區塊；
      實際通知與「傳送測試通知」走同一份管道清單（`deliver_to_channels`）；設定 API 會遮罩金鑰、表單送回遮罩值時保留原金鑰，
      並拒絕 link-local 的伺服器 URL。
- [ ] `tests/test_notify_test_endpoint.py`：`_send_zulip` 的參數，以及共用的管道清單以正確參數呼叫每個管道。
- [ ] `ui-sim-test.py` 步驟 1b：通知設定頁有 Zulip 卡片，勾選「啟用」後顯示欄位、取消勾選後隱藏（原本停用的管道——這正是先前每個管道都會壞掉的情況），只有 API 金鑰是遮罩欄位
      （只讀取，不會儲存）。

**人工（每次改到通知的版本）**

- [ ] 填入真實的 Zulip bot（伺服器 URL、bot 電子郵件、API 金鑰、串流），儲存後按**傳送測試通知**：
      訊息出現在該串流／主題，標題為粗體、內文對齊；重新整理頁面後金鑰以遮罩顯示，且仍可正常發送。
- [ ] API 金鑰錯誤時，測試結果顯示「HTTP 401: Invalid API key」。

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
