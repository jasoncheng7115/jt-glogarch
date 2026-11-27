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

### 統計報表——啟用開關（v1.36.0）

- [ ] `tests/test_reports_enabled.py`（4 項）：開關可停用報表（排程從 scheduler 移除）與重新啟用（重新註冊）、不存在的報表
      回 404、非布林值拒絕、沒有送 `enabled` 的儲存保留原狀態。手動：清單中的開關、標籤跟著變、停用的報表仍可「立即產生」；
      不再顯示 BETA。

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

- [ ] `tests/test_notify_links.py`（16，v1.34.0）：jt-glogarch 網址只能是 http(s) 的主機位址（不含路徑、查詢字串、
      帳密、空白；不超過 200 字元）；設定後每則資安事件與 AI 判斷通知都附上 `/security?incident=<id>` 連結，未設定則不附；
      電子郵件只讓我們自己的連結可點，記錄中的網址絕不變成連結；設定 API 會儲存通知語言（1.34 之前有送出卻沒存）與網址，
      不合格的網址回 400；分析流程會傳入事件 id；`/security?incident=` 會開啟該事件。
- [ ] `tests/test_reports_poll.py`（1，v1.34.0）：「統計報表」頁面透過 `startJobsPoll` 定期更新兩個清單，
      開著報表編輯視窗時不重繪。
- [ ] `tests/test_form_fields.py`（7，v1.34.0）：設定精靈的歸檔路徑可儲存（`path`／`base_path`）；`auth_type: password`
      會清除伺服器原本的 token（沒帶這個欄位的 API 呼叫維持部分更新的行為）；排程只有帶 `server_default` 才會改回預設伺服器，
      只送空的伺服器則維持原值；匯入時輸入的帳號密碼優先於已儲存的 token，所有連線匯入目標的端點都用同一個
      `target_credentials`；資安通知開關在表單上；手動 OS 匯出只有調低時才送出「最近 N 個」。`tests/test_ai.py`：
      網址改變時遮罩的 LLM 金鑰會被清除。
- [ ] `tests/test_sigma_library.py`（v1.34.0 新增）：`version.txt` 有讀取上限（zip 中 20 MB 的 0）；YAML 別名在任何展開前就從
      事件串流拒絕（九層別名炸彈 2 秒內結束）；tags 不是清單、3,000 層的條件不會讓整個規則包停止；不成對的 `|re` 會被拒絕，
      `[(]`／`[]x]`／`[^]x]` 可以接受；重新導向只到 443 埠；下載的整體時限。
- [ ] 檢視後的修正（v1.34.0）：`tests/test_datanode.py`（同時連接兩次不會停住、名稱衝突會被拒絕、CA 更換會重新核發但主機名稱不符不會、
      已連接時拒絕刪除、區塊消失時改用 API）；`tests/test_threat_intel.py`（略過不合理／過大／私有網段、名單驟減時保留舊名單、
      串流下載與時限、索引比對（1,500 個網段 2,000 次比對在 1 秒內）、依上次更新排程）；`tests/test_security_suppress.py`
      （標準形式與 IPv4 對應位址、拒絕對應網段、含「/」的一般對象、只結案涵蓋的事件）；`tests/test_security_digest.py`
      （固定時間且會執行的排程、不合格的排程不影響資安分析、正常需要分析開啟且一天內有成功執行）。
- [ ] MCP 與告警管理的檢視修正（v1.34.0）：`tests/test_ai.py`（輪換假 token 在打到 Graylog 前就被擋下、批次與內容大小上限、
      逐則錯誤、未知伺服器回 400、數字參數依結構描述限制）；`tests/test_alerting.py`（被翻轉的狀態放回一次、未知狀態在寫入前略過、
      失敗的列可以復原、重複 id 移除）。`scripts/e2e-alerting-test.py` 改對 `datanode-stack/up.sh` 的測試用 Graylog 7.2.2 執行
      （.83 無法連線）：2026-11-21 ALL PASS。
- [ ] **手機寬度（1.34）**：`UI_URL=https://<host>:8990 UI_USER=... UI_PASS=... python3 scripts/ui-phone-width-check.py`
      以 390 px 開啟每一頁，必須顯示 ALL PASS（頁面不能比螢幕寬；寬表格在自己的框內捲動）。
      `tests/test_phone_layout.py` 確保手機規則位於 `refine.css` 最後。1.18.0 到 1.33 手機版面是壞的
      （選單文字變成直排、頁面寬 600–990 px）。

**人工，每次改樣式後**
- [ ] 每一頁的亮色與暗色，在約 1440 與 1180 像素寬：內容不超過頁面右側內距，數字不被裁切。
- [ ] 分別打開表單、對話框和側邊欄的下拉：清單沒有被切掉。
- [ ] 由程式設定值的下拉（系統設定的匯出模式）顯示正確的值。

### 內容套件頁面（v1.18.0）

**自動**：`tests/test_packs.py`（4 個真實套件、安裝檢查、套件庫、以仿照實測行為的假 Graylog 測試路由，以及發布邊界）。

**下載內容**：`tests/test_pack_guide.py` 涵蓋三種語言的 SOP 文字、從套件讀出的內容、每份 SOP 都有新安裝／舊版升級／解除安裝三段、升級與解除安裝的檢查清單列出這個套件會留下的項目、跳脫處理與 ZIP。`tests/live_packs_check.py` 以真瀏覽器下載，確認 ZIP 內有套件與 SOP。

- [ ] 每種語言各下載一個套件庫的套件：ZIP 內有 `.json` 與一個 `.md`；`.md` 用純文字編輯器開也好讀，有三個段落，升級的檢查清單寫出這個套件的管線、規則前置碼與看板。

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

### Graylog Data Node 連線，beta（v1.19.0）

**自動化**

- [ ] `tests/test_datanode.py`（22）：主機位址取自 `transport_address`（略過未運作的節點，6.3 的 `data_node_status` 也讀）；6.3 憑證申請改用單一 `role` 重試；連線測試按鈕與容量估算保留憑證；列表端點是 `/api/system/cluster/datanodes`（儀表板偵測會先試它）；憑證名稱依伺服器而不同；一般 OpenSearch 區塊維持 `verify=bool` 加 Basic 認證，憑證區塊不送 Basic 認證並固定 CA（只有 `verify_ssl` 才檢查主機名稱）；檔案不見時錯誤訊息清楚；以標準函式庫讀取到期日；PEM 檔 0600、目錄 0700、不留暫存檔；更新時機（剩三分之一有效期，至少 7 天，最多一半）；更新失敗時保留可用的憑證；只有 401／403／憑證被拒才重新簽發；匯入目標只採用憑證區塊；Bulk 與 preflight 都經過這個設定；排程 OpenSearch 作業在憑證無法使用時改用 API 歸檔並通知一次；編輯伺服器會保留區塊且永不回傳金鑰路徑；連接時拒絕 `http://`；有 OpenSearch 排程時中斷連線會先詢問。
- [ ] **對真實 Data Node 執行 `scripts/e2e-datanode-test.py`**（凡改動 Data Node／憑證／OpenSearch 用戶端路徑都必須執行）：`bash scripts/datanode-stack/up.sh`（以 docker 啟動 Graylog + Data Node + MongoDB，只聽 loopback、限制記憶體，會印出所需環境變數），再執行它，必須印出 `RESULT: ALL PASS`：連接、送入測試訊息並輪替、以 OpenSearch 直連匯出全部測試訊息、Bulk 匯入全部、強制更新憑證、角色對應被背後移除後復原、排程改用 API 備援、中斷連線。`bash scripts/datanode-stack/down.sh` 會移除測試環境。請在不只一個 Graylog 版本線上執行（`GL_VERSION=6.3.15／7.0.15／7.1.11／7.2.2`）：6.3 的憑證申請只接受單一 `role`，狀態欄位名稱也不同。
      步驟 [6b]（2026-11-27）：停掉 Data Node 容器 → 試 4 次後回報，不申請新憑證；等待期間重新啟動 → 直接使用。
      `tests/test_datanode.py`：連不上的節點在 1、2、5 分鐘後重試，第一次成功就不再等，憑證被拒不等待，手動執行不等待，
      改走 API 的通知寫明試了幾次、等了幾分鐘。
- [ ] 儀表板「硬體規格建議」卡片（2026-11-27）：每種資源一列（本機／建議／足夠或不足），歸檔磁碟附「可存月數 vs 保留
      設定」長條，下方只列需要處理的事項；純歸檔主機與同機部署都要看，兩種主題與 390 px。

**人工（每次改到這部分的版本）**

- [ ] 系統設定 → Graylog 伺服器 → 編輯有 Data Node 的伺服器：方框列出節點，以預設位址（或 IP）連接後顯示「已連線：… green」；個別 OpenSearch 欄位隱藏；測試／更新／中斷連線都能用；英文／繁中／日文、淺色與深色主題在約 1436 px 寬下都正確。
- [ ] 匯出頁：連接後，這台 Data Node 伺服器不再被鎖定為 Graylog API，提示寫著 beta；匯入對話框可選 Bulk。

### 資安事件（v1.20.0）

**自動化**

- [ ] `tests/test_security_incidents.py`（30 項）：各項偵測的門檻與等級（外部來源等級較高；Suricata
      嚴重度 1 為高、2 只在量大時收錄、3 不收錄）；「(Empty Value)」那一列算涵蓋狀況，絕不開成事件；
      每個來源欄位都會嘗試（WAF 用 `client_ip`）；共用同一查詢的偵測只查一次；某次查詢失敗會記錄下來，
      其他查詢照常執行；站台自訂門檻與排除條件、電腦帳號的正規表示式；來源字串在 Graylog 查詢裡有加引號；
      事件生命週期（新增、持續、升級、等級不會降低、超過 `reopen_hours` 再出現為新事件、結案後為新事件、
      「首次出現」標記與學習期）；通知判斷（持續中的事件不重複通知，超過 `renotify_hours` 再提醒）；
      通知文字已中和（控制字元、markdown、反引號），Email／Slack 本文已跳脫；預設關閉，儲存設定會註冊／
      移除排程；API 參數驗證、狀態變更記入稽核、Graylog 連結；Graylog 連不上算失敗，連續三次只通知一次；
      實際跑兩次執行器只通知一次（資料庫時間字串結尾有 `Z`）。
- [ ] **對真實 Graylog 執行 `scripts/e2e-security-test.py`**（凡改動 `glogarch/security/` 都必須執行）：
      先 `bash scripts/datanode-stack/up.sh`，再用它印出的 `GL_URL`／`GL_PASS`／`GELF_PORT` 執行；
      會以 GELF 送入登入記錄，必須印出 `RESULT: ALL PASS`（四項登入偵測、Graylog 算出的帳號數／主機數、
      第二次查詢、沒有來源欄位的記錄算進涵蓋狀況）。不可對正式環境執行：它會寫入記錄。
      2026-11-19：6.3.15 與 7.2.2 皆 ALL PASS。2026-11-21（1.34.0）：7.2.2 ALL PASS（29 項）。

**手動（每個動到此功能的版本）**

- [ ] 在指向真實資料的測試實例上開「資安事件」頁面：「立即執行」完成並顯示查詢次數；事件清單顯示等級、
      「首次出現」，Graylog 連結會開啟對應的搜尋；確認／結案／重新開啟；「涵蓋狀況」把所有記錄都是空的欄位
      標紅、沒用到的替代欄位顯示灰色；儲存設定後出現下次執行時間。英文／繁中／日文、兩種主題、約 1436 px。
      通知管道會送到真人的站台，除非對方預期，否則不要開啟。

### 智慧問答與 MCP 端點（v1.21.0）

**自動化**

- [ ] `tests/test_ai.py`（33 項）：收進來的 mcp_graylog 和清單檔一致，並能在目前的 Python 載入（1.10.2 起 3.10 也可以）；
      無法載入時，狀態會說明原因，內建工具照常可用；匯入時不會動到根記錄器，也不會產生 `~/.mcp_graylog.log`；
      `find_silent_sources` 的回溯時間有上限；`*`／`*:*` 查詢會變成空白查詢，其他以萬用字元開頭的查詢會被拒絕；
      三個會拉取記錄的工具需要勾選才開放；只有在沒有真正的 SDK 時
      才用替代模組；時間範圍的解析與拒絕、拉取記錄的上限與 31 天上限；未知工具／參數會被拒絕；`top_values`
      透過彙總 API 精確計算；結果最多 12,000 字元；LLM 回覆解析（原生工具呼叫、`<tool_call>` 文字、去除
      `<think>`）；內網優先的網址檢查，雲端中繼資料位址一律拒絕；token 額度；對話迴圈（工具輪次、最後一輪後
      強制作答、空白答案再問一次、工具結果裡的 `</data>` 無法提前結束資料區塊、每次工具呼叫都以使用者和 IP
      記入稽核）；MCP 方法、協定版本協商、通知、批次、Bearer／Basic token、流量限制；`/mcp` 預設關閉、沒有 token
      回 401、被拒的 token 回 403、只有通知時回 202；設定保留遮罩的金鑰、換網址時清除金鑰、外部網址除非允許否則
      拒絕（記入稽核）；智慧問答需要先登入 Graylog；別人的對話一律找不到；頁面的 Markdown 轉換器（在 node 執行）
      先跳脫再加格式，只允許 https 連結。
- [ ] `tests/test_ai.py`（v1.33.1 新增）：停在長度上限的回覆會請模型接著回答並接起來，不重複被截斷的那一行；每次請求都用
      `ANSWER_TOKENS`；接續後仍被截斷的回答標示 `truncated`。**用真的 uvicorn 測**（TestClient 會把回應讀到結束，無法模擬
      離開頁面）：關閉串流後回答仍繼續，清單和對話會標示進行中與進度，同一段對話再提問回 409，回答連同時間存下；
      「停止」可中止離開時仍在進行的回答（「Stopped」，記入稽核）；頁面接線（複製、編輯、重新回答、接續進度、按鍵）。
- [ ] `tests/test_ai.py`（v1.34.0 新增）：每次工具呼叫都以查詢、實際查詢的絕對時間範圍和筆數／列數記錄在回答裡，
      不保存查回的資料列或記錄內容（結果在上限處被截斷時仍記錄參數）；讀回的查詢附上在 Graylog 開啟同一搜尋的連結，
      依每次呼叫的伺服器產生，已移除的伺服器不產生連結；對話可依名稱或訊息內容搜尋（`%`／`_` 視為一般字元，
      看不到其他使用者的對話），可重新命名（空白或太長回 400，其他使用者的回 404，記入稽核）；沒有回答的問題可用
      `retry` 回答一次（不重複保存問題，最後一則已是回答時回 409，稽核記錄 `retry=1`）；舊的 `ai_messages` 表會加上
      `calls`；串流：用在擁有者 llama.cpp 實測到的區塊格式組合文字、工具呼叫片段和用量，`<think>` 不會出現在頁面，
      收到 HTTP 400 後改用一般請求並記住，連線中斷轉成 LLM 錯誤，伺服器沒送用量時估算 token；對話迴圈在某一輪變成
      工具呼叫時清掉已顯示的文字，續寫接在已顯示的內容後；**用真的 uvicorn**：離開後回來的頁面讀得到目前已寫好的內容；
      數字欄靠右（node）；Markdown 下載（node）會跳脫 `|`、降低回答標題層級、列出查詢；結果不回報時間範圍的工具
      （mcp_graylog）由參數和預設值推算，失敗的呼叫仍保留查詢；頁面接線（資安事件範例讀取 `incidents`）。
- [ ] `tests/test_login_identity.py`（5 項，v1.33.1）：用 Graylog 帳號登入後，服務重新啟動會登出（代表使用者的
      Graylog 身分已經不在），重新登入即恢復，`localadmin` 不受影響；登入時也會在其他接受此帳號的伺服器登入，
      拒絕的伺服器略過；模型清單（`POST /api/ai/models`）讀取表單裡的網址，已儲存的金鑰只送往已儲存的網址，
      LLM 錯誤回 502；模型是清單，不是文字欄位。
- [ ] `tests/test_ai.py` 思考過程（4 項，v1.35.0）：`chat_stream` 把 `reasoning_content`／`reasoning`／內容裡的 `<think>` 區塊隨增長傳給 `on_reasoning`（有節流），而且在第一段答案文字之前全部送完；`run_chat` 送出 `reasoning` 增量，每次請求重設一次；離開再回來的頁面拿得到 `run.reasoning`；思考內容不儲存。手動：對會推理的模型問一題需要查詢的問題，思考區塊前幾秒就有文字、答案開始時收合、點過後維持你的選擇。
- [ ] `tests/test_ai_query_syntax.py`（51 項，v1.35.0）：在 Graylog Open 7.2.2 實測會算錯筆數或出錯的查詢寫法（正規表示式旗標、小寫運算子、以萬用字元開頭、未加引號的 CIDR、群組內沒寫運算子、`OR NOT`、Enterprise 的 `$name$` 參數），`call_tool` 會在詢問 Graylog 前拒絕並說明寫法；實測正確的寫法都能通過；系統提示含這些規則與 Open／Enterprise 的差異。
- [ ] `tests/test_api_heap_hint.py`（12 項，v1.35.0）：API 匯出的估算為每 GB Graylog heap 約每秒 200 筆，小於 4 GB 視為受 heap 限制；`GET /api/servers/api-heap` 讀取所選（或預設）伺服器的 `/api/system/jvm` 並快取，未知伺服器或讀不到 Graylog 時回 `available: false`，`api_in_use` 依預設匯出模式與該伺服器已啟用的 API 匯出排程判斷；匯出／排程對話框只在 API 模式且 heap 小時顯示提示（以最後一次選擇為準），硬體規格卡片只在使用 API 模式時顯示；三種語言的文字都有完整的佔位符。
- [ ] `tests/test_ai.py` 延伸問題（v1.35.0）：`split_followups` 取出 `[[follow-up]]` 那一行之後的問題（去掉項目符號、編號、引號；最多 3 個、每個 ≤ 200 字、不重複）；回答串流時標記和標記的開頭都不會顯示，串流出來的內容等於保存的內容；被截斷的回答不提供；建議問題會保存（`ai_messages.followups`，舊資料庫會自動加欄位），並出現在完成事件和對話內容裡；頁面只在最後一則回答底下顯示、經過跳脫，點一下就送出問題。
- [ ] `tests/test_ai.py` 模型伺服器等候提示（v1.35.0）：`llm.SILENT_SEC` 內沒有任何串流內容（沒有回應標頭，或有標頭但沒有內容）時呼叫 `on_silent(True)`，收到第一段內容時、在任何文字之前呼叫 `on_silent(False)`；伺服器立刻回應時不提示；提示本身失敗不會讓請求失敗；`run_chat` 先送出 `waiting_model`，再送回原本那一步的進度；頁面三種語言都有翻譯。
- [ ] `tests/test_export_gap_refill.py`（14 項，v1.35.0）：之前排程 API 匯出失敗的區段會被重新匯出。
      `Exporter.find_gaps` 只回傳歸檔之間的空缺（任何串流、只看這台伺服器；第一份歸檔之前不算；不到 60 秒不算；依範圍截斷）；
      `export(refill_windows=)` 在同一個作業裡先匯出空缺，預先計數只算空缺與新範圍，絕不重抓已歸檔的時段，沒有新範圍時也照樣執行；
      `_run_export_once` 會傳入續傳點之前、`gap_refill_hours` 與排程天數範圍內的空缺，沒有空缺（正常站台行為不變）或設 0 時不傳；排程頁的「立即執行」用同一個規劃（`Exporter.plan_scheduled_run`）；
      逾時記為「Chunk N failed: ReadTimeout」，不再是空白原因。
      實測：1.35.0 之後 .36 的 03:00 排程要補回 2026-11-21 03:00–04:00Z（附註出現「Refilled 1 gap(s)」）。
- [ ] `tests/test_archive_status.py`（7 項，v1.35.0）：`archive_status` 工具（智慧問答與 `/mcp`，取代 `archive_coverage`）
      依伺服器列出歸檔數、最早／最晚時間、距最新歸檔幾小時與缺口（重疊或相連的歸檔合併、不到一小時的空檔不列、新的在前、有上限）；
      損毀／遺失／遭竄改／失敗的歸檔；執行中的作業與預估剩餘時間；最近的匯出／驗證／清理作業（不含報表清理），附註截到 300 字並有
      7 天統計；排程的下次執行時間和排程頁用同一個規則（`scheduler.next_fire_time`）；磁碟剩餘空間與還能用幾個月。
      手動：在智慧問答問「歸檔狀況如何、昨晚的匯出有沒有成功」，答案要和作業歷程、儀表板一致。
- [ ] `scripts/check-mcp-graylog.py`（由 `run-tests.sh` 執行）：收進來的檔案和清單檔一致，也是上游最新的發佈版本；
      上游有新版時發版檢查失敗（`--update` 會整份換成新版）。
- [ ] **對真實 Graylog 執行 `scripts/e2e-ai-test.py`**（凡改動 `glogarch/ai/` 或 `web/routes/ai.py` 都必須執行）：
      先 `bash scripts/datanode-stack/up.sh`，再用它印出的環境變數執行（真實 LLM 那一步另需 `AI_URL`／`AI_MODEL`／
      `AI_KEY`）。它會送入 60 筆登入失敗，接著檢查精確計數、用 Graylog 簽發的 token 呼叫 `/mcp`（假 token 會被拒、
      呼叫有記入稽核）、透過 MCP 呼叫 mcp_graylog（`get_log_sample`、`analyze_source_distribution`、`find_silent_sources`
      及其回溯上限、`*:*` 很快回應、預設不開放會拉取記錄的工具）、真實 LLM 的答案與它自己的查詢結果一致（模型的查詢條件是否正確會以 WARN 列出），以及（第 5 步）
      真實的偵測會開出密碼噴灑事件、AI 分析的證據與 Graylog 一致、真實模型回傳有效的判斷，且沒有提到證據以外的位址。
      2026-11-19：Graylog 7.2.2 上以 Python 3.10 與（docker 中的）3.12 皆 ALL PASS；
      2026-11-20（1.33.1）：7.2.2、Python 3.10 ALL PASS。2026-11-21（1.34.0）：7.2.2 ALL PASS（28 項，包含串流文字
      與儲存的回答一致、每個查詢都記錄了時間範圍）。

**手動（每個動到此功能的版本）**

- [ ] 對測試用 Graylog 開「智慧問答」頁面：在頁面上登入 Graylog、提問、看進度列（輪次、工具），答案附上查詢、
      模型、耗時、token 與工具；「停止」有效；對話清單、重新開啟、刪除；設定：測試連線、儲存、MCP 設定範例、
      mcp_graylog 狀態。提問後切到其他頁面再回來：清單顯示「回答中…」，點開會接續顯示進度，回答完整出現；
      滑過提問、回答、表格（複製、編輯、重新回答、複製表格）；訊息時間；模型從清單選擇。（1.34）回答邊寫邊出現並有游標，
      已執行時間持續增加；回答到一半離開再回來，已寫好的內容還在且繼續增加；「N 次查詢」展開每個查詢的時間範圍和筆數，
      「在 Graylog 開啟」顯示同樣的搜尋和筆數；搜尋清單（名稱與訊息內容）、今天／昨天分組；在標題列重新命名（Enter／Esc）；
      下載為 Markdown；按停止後「回答這個問題」只回答一次（重新整理後也一樣）；數字欄靠右。
      英文／繁中／日文、兩種主題、約 1436 px。
- [ ] **`scripts/ui-ai-chat-test.py`（1.34）**：對已開啟智慧問答的 jt-glogarch 執行 `UI_URL=... UI_USER=<Graylog 帳號或 token>
      UI_PASS=... python3 scripts/ui-ai-chat-test.py`，必須顯示 ALL PASS（串流與游標、計時、回答到一半離開再回來、查詢面板的
      Graylog 連結與複製、重新命名／搜尋／下載 Markdown、立刻停止後「回答這個問題」只回答一次、刪除正在追蹤的對話後頁面不會卡住；
      結束時刪除自己建立的對話）。2026-11-21 在 .36 用擁有者的 LLM：ALL PASS（17 項）。

### mcp_graylog 1.12.0 事件工具與 Zulip 格式（v1.35.0）

**自動**

- [ ] `tests/test_ai.py::test_event_tools_are_offered_and_search_events_gets_the_long_range`：5 個事件工具預設提供，
      除錯工具一律不提供；`search_events` 可查 31 天，拉取記錄的工具 24 小時。
- [ ] `scripts/e2e-ai-test.py` 的 `events_step`（真實 Graylog）：URL 含 token、說明含 email、URL 與 IP 的 HTTP 通知，
      綁在一個 event definition 上；經由 /mcp，`list_event_definitions` 兩者都列出，`list_event_notifications` 與
      `get_event_definition` 不回傳 URL、token、密碼或位址，`search_events` 查 2 天找得到觸發的事件，
      `get_event_source_messages` 取得其記錄。2026-11-22：7.2.2（含真實 LLM）與 6.3.15 皆 ALL PASS。
- [ ] `tests/test_notify_zulip.py`：每個數字一行、標籤加粗，沒有程式碼區塊，錯誤為清單項目，保留資安通知的程式碼標記，
      記錄文字以 HTML 實體送出（不會變成格式、提及、串流連結、表情符號、KaTeX 或連結）；`rich` 從通道清單傳到 Zulip。

**手動**

- [ ] 在手機與電腦上看 Zulip 通知：不需橫向捲動，數字一行一個。

### 資安通知版面、事件細節與 WAF 擋下（v1.35.0）

**自動**

- [ ] `tests/test_security_incidents.py`：WAF 擋下的掃描（放行筆數低於 min_count）記成「低」；部分放行保留原本的
      嚴重程度並帶 blocked／passed；達到 1,000 筆（或該偵測項目的 `blocked_min_count`）保留原本的嚴重程度；擋下筆數
      查詢失敗時事件照舊；擋下條件來自欄位對應；執行流程會保存 `metrics.context` 並用在通知裡。
- [ ] `tests/test_security_context.py`：事件細節＝對事件自己的搜尋條件取每個欄位前 3 名、使用本站欄位名稱、略過
      事件本身的欄位、停止送記錄的主機不查、單一欄位失敗就略過、每次最多 12 件（嚴重的優先）。
- [ ] `tests/test_notify_rich.py`：一行標題加上每個項目一行標籤（標籤不重複），含偵測來源／網站／路徑／回應碼／
      WAF；只有我們的標題與標籤是粗體（Telegram、Zulip、Slack 用 `*`），連結那一行與含冒號的值不會被當成標籤。
- [ ] `scripts/e2e-security-test.py` `waf_step`（真實 Graylog）：30 筆全擋 -> 低；擋 10 筆、放行 20 筆 -> 中，帶
      blocked／passed；事件細節列出回報主機、網站、回應碼（對應到 `http_status`）與 3 個路徑。

**手動**

- [ ] 在 Zulip／Telegram 的手機與電腦上看資安通知：標題與標籤為粗體、不需要橫向捲動；「資安事件」頁面每件事件的
      數字下方有事件細節與 WAF 結果。

### 內建偵測的欄位對應（v1.35.0）

**自動**

- [ ] `tests/test_security_fieldmap.py`（13）：沒有對應時查詢與舊版完全相同（升級後送出同樣的搜尋）；
      驗證（不認得的項目、單一欄位、最多 4 個、`gl2_*` 與不合法名稱、條件長度、預設值與空欄不儲存）；
      儲存的對應損毀時逐項退回預設；引擎查詢對應後的欄位，指標仍以 GIM 名稱儲存（`card:user_name`），
      事件查詢使用對應的欄位，排除機器帳號的條件跟著帳號欄位；IDS／WAF／停止送記錄／訊息量／失敗後成功／
      新來源的條件都用對應；偵測列表與 AI 證據使用對應；`candidates()` 依值的樣子與名稱挑選（排除
      `useragent`、`request_id`、GeoIP 衍生欄位；像目的端的排最後）；`detect()` 在 log4 形狀的模擬資料上：
      精確比例、沒有任何欄位的事件依輸入列出、條件無符合事件時不抽樣；API：儲存（錯誤回 400、只存非預設值、
      記入稽核）、一般設定的儲存不會寫入對應、找欄位以表單送出的內容查詢。
- [ ] `scripts/e2e-security-test.py` 的 `fieldmap_step`（真實 Graylog）：非 GIM 的登入事件在預設下看不到，
      設定對應後找得到（經 `IpAddress` 的暴力破解、密碼噴灑、失敗後成功，指標以 GIM 名稱儲存，覆蓋率 65／5），
      `detect()` 以 Graylog 精確的 `count(field)` 找出 `IpAddress`／`TargetUserName`（有值＋都沒有＝全部）。
      2026-11-22：7.2.2 與 6.3.15 皆 ALL PASS。

**手動**

- [ ] 資安事件 → 設定 → 欄位對應：每個群組按「找欄位」顯示筆數與範例；「使用」填入欄位（多欄位的放第一個）；
      儲存、匯出、匯入、恢復預設；淺色與深色主題，約 1436 px 寬。

### 資安通知格式化（v1.32.1）

**自動化**

- [ ] `tests/test_notify_rich.py`（4 項）：Telegram 的格式化 HTML 會跳脫標題與內文、把程式碼片段轉成 `<code>`、只用 b／i／code 標籤，
      沒有 `<pre>` 也沒有反引號；工作類通知維持 `<pre>`；事件與 AI 通知以格式化模式送出，沒有縮排的行，每件事件一段且對象獨立一行；
      Email 的 HTML 是一般段落，程式碼有跳脫。

**手動**

- [ ] 真實的事件通知在 Telegram（手機）與 Email 中顯示為格式化文字，而不是程式碼區塊。

### 每週資安摘要（v1.32.0）

**自動化**

- [ ] `tests/test_security_digest.py`（6 項）：7 天內的內容（依嚴重程度的新增事件與較舊的事件、最常見的偵測、未處理、案件、執行次數、
      有符合的抑制規則、風險）；健康判斷（沒有任何執行就是警告，不論事件多少；失敗多於成功也是警告）；文字（沒有執行的一週用警告標題、
      寫明分析已關閉、數字、我們自己的偵測名稱不加程式碼格式、記錄內容無法自成一行）；API（cron 檢查、空白保留原排程、預覽給出實際文字、
      寄送、寄送失敗回 502 並附原因、稽核）；排程預設關閉、POSIX 星期換算、儲存的 cron 錯誤時改用預設；三種語言的字串與參數。

**手動**

- [ ] 資安 → 設定：「預覽」以通知語言顯示文字；「立即寄送」會先確認，真實通知管道收得到；開啟並儲存後，`internal-security-digest` 排程存在。

### 抑制規則（v1.31.0）

**自動化**

- [ ] `tests/test_security_suppress.py`（7 項）：對象正規化（網段轉成標準格式、太寬的網段與錯誤的值會被拒絕）；比對（完全相同、所有偵測、
      所有伺服器與單一伺服器、IPv4／IPv6 網段、名稱不會落在網段內、到期的不算、記錄值不做修剪）；符合次數；API（驗證訊息、網段標準化、
      關閉事件、同一條會更新原因與到期日、Sigma 偵測、刪除、稽核）；runner 在開出事件前略過被抑制的結果並記下次數；清理保留生效中與剛到期的規則；
      介面連結、確認框有跳脫、三種語言字串。

**手動**

- [ ] 事件：抑制按鈕開啟對話框（這項偵測或所有偵測、可修改對象、必填原因、到期、關閉事件）；儲存後事件已關閉，表格下方的「抑制規則」出現這一條；
      對象仍在發生時按「立即執行」，符合次數會增加；移除前會先確認。英文／繁中／日文、兩種主題、約 1436 px。

### 記錄量異常（v1.30.0）

**自動化**

- [ ] `tests/test_security_anomaly.py`（10 項）：預設關閉（沒開啟就不會彙總所有記錄）；兩個欄位都會收集，其中一個失敗不影響另一個；
      平常的量把沒有記錄的時段算 0、排除分析沒有執行的日子、至少要 5 天；對已學習的紀錄找出暴增（數值、含排除條件的查詢、20 倍以上為中）；
      門檻（5 倍、每小時下限、30 分鐘的範圍換算成每小時、波動大的紀錄在範圍內不算暴增）；學習期（紀錄不滿 7 天、從沒看過的主機）；
      每小時一筆、同一小時以最後一次為準、清理；runner 先判斷再記錄這次的量；不對應 ATT&CK；三種語言字串；AI 證據會說明數值。
- [ ] `scripts/e2e-security-test.py`（真實 Graylog）：600 筆的暴增由兩次真實彙總依主機與類別算出，對 10 天每小時 20 筆的紀錄判斷出兩者（30 倍、中），
      事件的查詢也找得到這批記錄。2026-11-20：7.2.2 上 ALL PASS。

**手動**

- [ ] 資安 → 設定：這項偵測那一列說明最少筆數是每小時，而且要先累積 7 天的紀錄。

### 帳號從新的來源登入（v1.29.0）

**自動化**

- [ ] `tests/test_security_new_source.py`（4 項）：預設關閉；從兩個分組收集配對（空值算涵蓋率，排除電腦帳號）；學習期（帳號紀錄不滿 7 天）、
      記憶期間（30 天沒用過的來源會再次算新）、每個帳號一件事件並列出新來源、依外部來源決定等級、這次看到的配對下次就算已知；清理會忘記舊配對；
      T1078 與三種語言字串。
- [ ] `scripts/e2e-security-test.py`（真實 Graylog）：兩個分組的彙總查詢回傳送入的（帳號、來源、3），歷史判斷也會標示該帳號。
      2026-11-20：7.2.2 上 ALL PASS。

### 資安總覽（v1.29.0）

**自動化**

- [ ] `tests/test_security_overview.py`（5 項；另含 CSV 匯出：篩選、公式內容中和、技術欄位、稽核）：總覽資料（14 個本地日、各嚴重程度的筆數、依嚴重程度的未處理事件、案件、最常見的偵測與技術、
      風險排名前幾名、天數上限 90）；圖表是沒有行內樣式的 SVG（CSP），每個非零的嚴重程度各一段、每天都有標題、有圖例；ATT&CK「監看中」
      合併最近 24 小時的分析（安靜的一次分析不會讓偵測變成沒有資料）；三種語言字串。

**手動（每個動到此功能的版本）**

- [ ] 「資安事件」頁先開啟總覽：資訊磚（事件與調查會開啟對應分頁）、圖表的滑鼠提示數字與表格檢視、三個清單。英文／繁中／日文、兩種主題、約 1436 px。

### 威脅情資（v1.28.0）

**自動化**

- [ ] `tests/test_threat_intel.py`（10 項）：清單解析（註解、無效內容、網段正規化）；比對（位址與網段、多份清單、非位址）；更新會取代
      清單內容，下載失敗則保留先前內容並記錄錯誤；空的或過大的清單會被拒絕，且只會下載固定的 https 網址；預設關閉，只使用勾選的清單；
      風險分數乘 2；API（設定會限制數值並過濾清單、關閉時拒絕下載、事件與排名會標示、稽核）；AI 分析的證據會說明清單；排程工作跟著
      開關與間隔變動；三種語言字串。
- [ ] `scripts/upgrade-compat-test.sh`：會建立 `sec_ti_entries` 與 `sec_ti_feeds`。

**手動（每個動到此功能的版本）**

- [ ] 「資產與風險」分頁：開啟清單、立即下載（三份清單的筆數與時間）、來源在清單上的事件會顯示清單標記與乘 2 的加權。
      英文／繁中／日文、兩種主題、約 1436 px。

### 審查修正（v1.29.0）

**自動化**

- [ ] `tests/test_security_review_fixes.py`（9 項）：空白的設定欄位保留原值，數值會限制範圍（保留期限不會是 0）；排程與手動分析共用一把鎖；
      「立即執行」在 AI 完成前就回應；無法解析的網段資產不會讓風險計算失敗；未查證位址以完整位址比對並處理 `:埠號`；送給 mcp_graylog 的查詢
      中間出現開頭萬用字元也會拒絕；預期外的 LLM 錯誤仍會留下紀錄；確認對話框會跳脫使用者文字；案件報告無法夾帶連結或 HTML（node）。

### Sigma 規則（v1.27.0）

**自動化**

- [ ] `tests/test_security_sigma.py`（66 項）：每種支援形式的轉換（OR 裡的 NOT 仍是 NOT、`|re` 的錨定、字面的 `\*` 與 `<>=` 會跳脫）（相等比對用片語、清單、`all`、startswith 萬用字元、contains／
      endswith／開頭萬用字元轉為正規表示式、Lucene 跳脫、字面的 `\*`、null／exists、數值比較、`re`、關鍵字、對應表清單、and／not、
      `1 of`、`all of them`、括號、條件清單）；`message` 以片語查詢、`short_message` 對應到 `message`，該欄位不接受正規表示式；欄位對應；
      16 種拒絕情況各有原因（base64、cidr、正規表示式旗標、彙總、near、不存在的選取條件、沒有符合的選取條件、括號未閉合、關鍵字內的萬用字元、
      非數值的 gt、空的選取條件、沒有 condition、沒有標題、沒有 detection、兩份文件、YAML 錯誤）與大小上限；等級、id 與 ATT&CK 標籤；
      偵測引擎（依群組、門檻、空群組、失敗的規則會記錄、全域排除）；資料庫中的規則與結果；通知使用規則標題與技術；API（預覽、新增、啟用、
      上限、欄位對應重新轉換、測試、刪除、稽核）；規則開出的事件顯示標題與技術；頁面會跳脫規則內容（node）；三種語言字串。
- [ ] `scripts/e2e-security-test.py`（真實 Graylog）：含片語、contains 正規表示式、startswith 萬用字元與 NOT endswith 的規則，
      在 3 台主機上各精確計得 15 筆（共 45 筆）；`short_message|contains` 比對到 61 筆。2026-11-20：7.2.2 與 6.3.15 上皆 ALL PASS。
- [ ] `scripts/upgrade-compat-test.sh`：升級後的資料庫會建立 `sec_sigma_rules`。

**手動（每個動到此功能的版本）**

- [ ] Sigma 分頁：貼上會被拒絕的規則（顯示原因，且已翻譯）、貼上正確的規則（「轉換」顯示查詢與 ATT&CK 標記）、儲存（不啟用）、啟用、
      測試 24 小時、儲存欄位對應會重新轉換；規則開出的事件會顯示規則標題。英文／繁中／日文、兩種主題、約 1436 px。

### SigmaHQ 規則庫（v1.33.0）

**自動化**

- [ ] `tests/test_sigma_library.py`（9 項）：在記憶體中讀取版本 zip（只讀 `rules*/…/*.yml`，略過重複 id 與沒有 id 的檔案，
      無法轉換的規則保留並附原因，欄位套用欄位對應，關鍵字對到 `message`）、大小上限（zip、解壓後大小、不是 zip、沒有規則）；
      只接受 https 的 GitHub 主機；更新：下載後再檢查為「已是最新」且不重新下載，重新導向到其他主機會被拒絕，規則庫保留並記下錯誤；
      從規則庫加入的規則隨新版更新（保留啟用狀態、計數依據與門檻，無法轉換時停用，關閉自動更新則不動），同 id 的手動貼上規則永遠不被取代；
      API（預設關閉、關閉時拒絕更新、不明套組、篩選：可轉換／Graylog 有欄位／記錄來源／等級／文字，加入＝停用且 `origin=library`、
      已加入、欄位對應會重新轉換規則庫、稽核）；排程預設關閉；頁面連結與三種語言字串。
- [ ] `scripts/e2e-security-test.py` 的 `sigma_library_step`（真實 Graylog，以替身代替 GitHub）：套組存入、從 `/api/system/fields`
      讀到 Graylog 的欄位清單、Graylog 沒有的欄位會被標出、規則庫條目的查詢與貼上的規則一樣計得 45 筆。2026-11-20：7.2.2 與 6.3.15 上皆 ALL PASS。
- [ ] `scripts/upgrade-compat-test.sh`：升級後有 `sec_sigma_library`、`sec_sigma_library_meta` 與 `sec_sigma_rules.origin`。

**手動（每個動到此功能的版本）**

- [ ] Sigma 分頁：下載設定（開啟、套組）、立即檢查會下載（顯示版本、數量、Graylog 欄位）、篩選、缺少的欄位加刪除線、
      加入／加入選取的規則（規則以停用狀態出現在 Sigma 規則中，並附 SigmaHQ 連結）、重新下載。英文／繁中／日文、兩種主題、約 1436 px。

### 記錄來源停止傳送（v1.26.0）

**自動化**

- [ ] `tests/test_security_silent.py`（6 項）：預設關閉；兩個時間範圍（基準範圍結束於最近範圍的開始）、套用全域排除；仍在傳送、
      未達最少筆數、空值都不算停止；最少筆數可調整；最近清單被截斷時不回報並說明原因；查詢失敗會記錄；ATT&CK T1562 與三種語言字串。
- [ ] `scripts/e2e-security-test.py`（真實 Graylog）：60 筆記錄都在 3 小時前的主機會被判定停止傳送（基準 60 筆），仍在傳送的主機不會。
      2026-11-20：7.2.2 與 6.3.15 上皆 ALL PASS。

### 資產與風險排名（v1.25.0）

**自動化**

- [ ] `tests/test_security_risk.py`（24 項）：資產值的檢查與正規化（位址、網段、主機與帳號不分大小寫、拒絕標記語法）；比對規則
      （完全相同的位址優先於網段、範圍最小的網段、IPv6 不會落在 IPv4 網段、帳號不分大小寫）；分數與計算說明（嚴重程度、外部來源、
      資產重要性、AI 判斷；已結案事件不計；排序）；資料庫中的資產（依類型與值更新、不存在的 id、刪除）；API 會檢查輸入、拒絕改成
      其他資產已用的類型與值（409）、標示事件、排名、整批匯入並逐行回報錯誤、記入稽核；AI 分析的證據與智慧問答的排名工具都知道
      資產；頁面會跳脫資產名稱與重要性（node）；三種語言字串。
- [ ] `scripts/upgrade-compat-test.sh`：升級後的資料庫會建立 `sec_assets`。

**手動（每個動到此功能的版本）**

- [ ] 「資產與風險」分頁：新增、編輯、刪除、匯入資產；與資產有關的事件會顯示標記；排名的時間範圍選單；分數可展開查看事件與加權。
      英文／繁中／日文、兩種主題、約 1436 px。

### 調查案件（v1.24.0）

**自動化**

- [ ] `tests/test_security_cases.py`（8 項）：案件的生命週期與只增不改的時間軸（建立、加入／移除事件、狀態／負責人／結論變更、
      筆記；重複與不存在的事件會略過；重新開啟會清除結案時間；不存在的案件回傳 None）；白名單以外的欄位一律忽略；保留期限
      不會刪除已加入案件的事件；智慧問答工具可讀取案件；API 會檢查輸入（標題、嚴重程度、狀態、空白筆記、沒有事件）、回 404、
      在事件上列出所屬案件，並以登入者身分記入每一次變更的稽核；案件對話框會跳脫標題、筆記與事件內容，且不接受非 http 的
      Graylog 連結（node）；Markdown 報告會跳脫自由文字、把記錄內容放在程式碼區段，且反引號不會破壞格式；三種語言字串。
- [ ] `scripts/upgrade-compat-test.sh`：升級後的資料庫會建立三個新資料表。

**手動（每個動到此功能的版本）**

- [ ] 「資安事件」頁：事件列的「案件」→ 新案件 → 對話框：修改標題、狀態、嚴重程度、負責人、說明、結論後儲存；新增筆記；
      移除事件；下載報告；事件列顯示案件標記；「調查案件」分頁的清單與篩選。英文／繁中／日文、兩種主題、約 1436 px。

### MITRE ATT&CK 對應（v1.23.0）

**自動化**

- [ ] `tests/test_security_attack.py`（19 項）：每項偵測都對應到已定義的技術與戰術；MITRE 網址路徑；IDS 簽章依關鍵字
      對應（掃描、漏洞利用、網站攻擊、惡意程式／C2、阻斷服務、暴力破解；INFO／POLICY 不對應）；涵蓋狀態（監看中、沒有
      資料、查詢錯誤、已關閉、尚未執行、僅 IDS 簽章；技術取其專屬偵測中最好的狀態，只有 IDS 看得到時標示僅 IDS 簽章；戰術順序不變）；通知內容附上技術代號；AI 分析的證據與
      智慧問答的事件工具都帶有技術；事件 API 與 `/api/security/attack`；頁面上的技術標記會跳脫，且只連到 attack.mitre.org
      （node）；三種語言都有對應字串。

**手動（每個動到此功能的版本）**

- [ ] 「資安事件」頁：偵測名稱下方的技術標記會開啟 MITRE 說明頁；ATT&CK 按鈕顯示戰術表，狀態與「涵蓋狀況」表一致。
      英文／繁中／日文、兩種主題、約 1436 px。

### 資安頁面與 Sigma 全選（v1.36.1）

- [ ] `tests/test_sigma_library.py`：`ids_only=1` 只回傳可加入的 ID；`/api/security/sigma-bulk` 啟用到 `sigma_max_rules` 為止、其餘以 `cap` 回報，可停用，非布林值拒絕。`tests/test_security_attack.py`：`attack.py` 裡每個戰術與技術都有英文（＝MITRE）、繁中、日文名稱。`tests/test_phone_layout.py`：未翻譯的文字在 `.i18n-ready` 之前隱藏，1.2 秒後仍會顯示。
- [ ] 手動（約 1436 px、兩種主題、390 px）：事件清單欄位對齊、圖示按鈕同尺寸、AI 判定色點、日期分兩行；總覽圖約 210 px 高、數字卡同高且靠左；ATT&CK 矩陣中文在上、英文在下，狀態在同一欄；設定／涵蓋狀況／ATT&CK 可用各自的按鈕收合，上方按鈕呈按下狀態；Sigma 規則庫：表頭勾選框選取整頁、「選取全部符合篩選的 N 條」、分批加入；Sigma 規則：全選、啟用／停用、上限提示；切換頁面時不再先閃英文。

### 智慧問答：統計、分頁、用量、迴圈、多台 LLM、預覽（v1.36.0）

**自動**

- [ ] `tests/test_ai_136.py`（33 項）：迴圈偵測（思考過程中完全重複與換句話說的同一句都會抓到；表格、HTML、
      主機清單不會誤判；重複的回答截到第一份；參數順序不同仍算同一次呼叫）；保留的結果（大結果在預算內成為有效 JSON，
      附整份結果每一欄的摘要；`read_result` 的篩選／包含／排序／計數／欄位；文字分頁；別人讀不到；逾時）；`aggregate`
      （送給 Graylog 的請求、隱藏的 count(欄位) 探測、首見／末見轉成 ISO 時間、時間區間自動改粗、超過 10,000 列拒絕、
      指標欄位不存在時註明）；`summarize_messages`（每次 500 筆分頁，只差一個字的樣式合併）；超過 Graylog 10,000 筆
      分頁上限拒絕；模型資訊（llama.cpp `/props`、`/v1/models`、手動設定優先、無法偵測時以預設值計算）；上下文小時只提供
      核心工具與較小的結果；重複的工具呼叫不再執行；思考迴圈中止並重問一次、第二次結束；前文保留最近幾輪與其查詢、更早的
      問題列出；單一伺服器設定成為清單第一台並寫回舊欄位；全站／伺服器／使用者上限；釘選最多 5 個、排最前、保留天數不刪；
      訊息轉成 Claude 格式（Claude 自己的回合原封不動、工具結果合成一則 user 訊息）；Claude 請求內容（不送 temperature、
      自動調節思考、`tool_choice: none`、思考強度、JSON schema、只在 Claude API 本身啟用備援）；以真實 `anthropic` SDK
      對模擬傳輸跑完整一輪工具呼叫（請求標頭與內容、思考區塊連同簽章送回）；私有欄位不會送到 OpenAI 相容伺服器；儲存多台
      伺服器（Claude 必須允許外部、遮罩金鑰保留、改名跟著走、換網址清除、同名拒絕、寫回舊欄位）；對話指定不存在的 LLM
      拒絕；第 6 個釘選回 409；預覽的沙箱 CSP、只有預覽是 `X-Frame-Options: SAMEORIGIN`、內嵌 Chart.js、Mermaid 為 strict
      且圖的文字無法結束 script、下載、別人的訊息 404；內含的 Mermaid 與 manifest 一致。

**手動（每個動到此功能的版本）**

- [ ] 對測試用 Graylog、使用 owner 的模型：分組統計的問題使用 `aggregate`（數字與 Graylog 一致）；「訊息有哪幾種」使用
      `summarize_messages`；「做成 HTML 儀表板」產生的頁面按「預覽」能畫出圖表；預覽內 `document.cookie`、
      `fetch('/api/...')`、`parent.document` 都被拒絕（headless Chromium）。進度列顯示模型與上下文長度。
- [ ] 設定 → LLM 伺服器：新增 Claude API 伺服器（必須允許外部）、測試、設為預設、改名（金鑰跟著走）；對話時的伺服器選單
      可逐題切換。
- [ ] 對話清單：收合、折疊分群、釘選最多 5 個（第 6 個拒絕）；提問框下方的開關可展開或折起思考過程。預覽窗格：對話旁／
      整個對話區／新分頁／下載。英文／繁中／日文、兩種主題、約 1436 px；預覽開啟時提問框的按鈕不重疊。
- [ ] 查詢進行中，進度列顯示這次查詢自己的計時；查完的每次查詢留在下方，列出花費時間與結果；回答下方的查詢清單顯示每次
      查詢的時間。

**2026-11-27 補充（仍屬 1.36.0）**

- [ ] `tests/test_ai_136.py` 新增 7 項：已取消且未回答的問題在前文中會註明（之後有回答就不註明）；`stopped_at` 只記在
      問題上；看板依頁面主題配色（提示中寫明淺色／深色配色，不明的值當淺色，頁面送出 `getTheme()`）；回答長度可用
      回報上下文的四分之一（262,144 → 65,536；未知 → 8,192）；`preview_blocks(partial=True)` 會算進還在寫的區塊；即時預覽
      只提供自己正在回答的內容（沙箱 CSP、`no-store`，別人或已完成回 404）；頁面上的收折、即時預覽、拖拉分隔線與已取消標示。
      `tests/test_ai.py::test_stop_ends_an_answer_left_running` 也檢查 `stopped_at`。
- [ ] 手動：模型思考中按停止 → 該問題顯示「已取消」（重新開啟對話也一樣）；超過 15 行的程式碼區塊預設收合，顯示「展開
      （N 行）」；請模型做看板時，頁面一邊寫預覽窗格就自己打開並跟著更新，回答完成後換成儲存的版本；關掉窗格後這次回答
      不再自動打開；淺色主題下新產生的看板是淺色；拖拉預覽窗格左緣可調寬度（會記住，按兩下還原）；查詢完成清單對齊成欄；
      LLM 伺服器卡片在約 1436 與 1180 px 寬時欄位對齊。
- [ ] `tests/test_ai_136.py`（另）：Markdown 預覽有跳脫（沒有 script、沒有 javascript: 連結），表格／清單／Mermaid 有畫出，
      淺色／深色主題，下載為 `.md`；對話清單的 `more`／`limit`（釘選不計入，上限 1000）。手動：完成的看板在串流正常結束與
      被切斷時都會在窗格自動開啟（headless 檢查把 `/api/ai/chat` 導向有與沒有 `done` 的串流）；預覽標題列與對話卡片同高；
      我方泡泡為深底白字；建議問題有底色；「顯示更早的對話」每次多 50 個；登入頁說明為提醒框，兩個控制項都是 34 px。

### 資安事件 AI 分析（v1.22.0）

**自動化**

- [ ] `tests/test_security_ai.py`（20 項；回覆在 token 上限被截斷時會提高上限再問一次；AI 判斷通知需要開啟，只列出勾選的判斷，三種語言都附上摘要）：驗證模型回傳的 JSON（程式碼區塊、`<think>`、前後多餘文字；未知的判斷或
      把握程度一律拒絕；清單有上限）；回覆提到但證據沒有的位址會被標示（IPv4 與縮寫的 IPv6，版本號不算）；時間範圍
      上限 24 小時；自動分析只挑新增或升級的事件，由高到低、有上限；證據查詢都與該事件有關，空欄位會略過，會查成功
      登入；HTTP 400 時回覆格式由 json_schema 退回 json_object；範例記錄裡的 `</data>` 無法提前結束資料區塊；範例記錄
      不會保存；無法使用的回覆會再問一次，仍不行就記為失敗，且不會蓋掉上一次的判斷；LLM 連不上或 token 額度用完時
      記下錯誤，額度用完時不再查 Graylog；事件刪除時分析一併刪除；自動分析需要兩個開關都開啟，遇到第一個失敗就停止
      （記入稽核）；預設關閉；API 在關閉時拒絕、未知事件回 404、執行中回 202 後再呼叫回 409、清單帶出判斷、記入
      稽核；設定會檢查嚴重程度並限制件數；頁面會跳脫模型寫的內容（node）；頁面用到的字串三種語言都有。
- [ ] `scripts/e2e-ai-test.py` 第 5 步（見上）。

**手動（每個動到此功能的版本）**

- [ ] 開啟 AI 後，對測試用 Graylog 開「資安事件」頁面：列上的 AI 按鈕、分析、執行中提示、完成後列上的判斷標記、
      證據區塊、「先前的分析」、「到智慧問答詢問」開啟智慧問答並帶入問題；設定：自動分析開關、嚴重程度、件數。
      英文／繁中／日文、兩種主題、約 1436 px。

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

## SBOM（每次發版）

`./scripts/run-tests.sh` 會依**已安裝**的套件產生 `github/sbom.cdx.json`（CycloneDX 1.5）。
它從 `/tmp` 執行，避免原始碼目錄裡過時的 `*.egg-info` 被讀到；已安裝的 jt-glogarch
不是要發的版本時就停止發版（先用 `--force-reinstall` 重新安裝）。每次推送都要跟
`TEST-RESULTS.md` 一起提交。

- [ ] `github/sbom.cdx.json` 的版本是這次發的版本，且列出 `pyproject.toml` 的每個執行
      相依套件（`tests/test_sbom.py` 會檢查這兩項）。
- [ ] 離線安裝包裡有 `sbom.cdx.json`，沒有就 `build-offline-bundle.sh` 中止。裡面列出包內
      每個 wheel 的 SHA-256、Chromium 版本和字型。
- [ ] 在測試主機執行 `sudo -u jt-glogarch glogarch sbom -o /tmp/s.json`，得到有效的 JSON，
      版本是部署的版本（`glogarch sbom > 檔案` 也一樣：警告輸出到 stderr）。

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
