# jt-glogarch 測試清單

**語言**: [English](TESTING.md) | **繁體中文**

每次發版前必須全數通過。在專案根目錄執行：

```bash
./scripts/run-tests.sh
```

---

## 自動化測試（103 筆）

### 單元測試

| # | 測試檔 | 筆數 | 覆蓋範圍 |
|---|---|---|---|
| 1 | `test_sanitize.py` | 10 | 密碼/Token/URL/JSON/Basic Auth/Bearer 脫敏、截斷、無誤殺 |
| 2 | `test_local_admin.py` | 9 | SHA256 hash、帳號必須 `localadmin`、Graylog 拒絕不 fallback、Graylog 離線有/無 hash、向下相容 |
| 3 | `test_bulk_import.py` | 7 | 保留欄位剝除、deflector alias、stream 改寫、marker 欄位、dedup id/none |
| 4 | `test_notify_format.py` | 7 | 狀態 emoji（✅/⚠️/❌）、每行一項、URL 縮短、en/zh-TW key 一致 |
| 5 | `test_repo_structure.py` | 7 | pyproject.toml 在根目錄、無 src/ 目錄、deploy 檔案、README/CHANGELOG/CONFIG 存在、版號同步 |
| 6 | `test_upgrade_script.py` | 7 | upgrade.sh 存在 + 5 步驟、root 檢查、版本顯示、README 引用、systemd 預設=Yes、git clone sudo |
| 7 | `test_field_schema.py` | 6 | 純 JSON 通過、zlib 壓縮 round-trip、None/損壞處理、DB 儲存+讀取 |
| 8 | `test_database_datetime.py` | 5 | naive/UTC/+08:00 round-trip、None 通過、offset 字串解析 |
| 9 | `test_import_lock.py` | 5 | 取得/衝突/釋放/錯誤 owner/重複取得 |
| 10 | `test_db_rebuild.py` | 5 | dry-run、實際重建、跳過已存在、備份、清理舊備份 |
| 11 | `test_preflight_conflicts.py` | 4 | intra-archive conflict、cross-conflict 實際 mapping、string-only 不 pin、混合場景 |
| 12 | `test_config.py` | 4 | 預設值、搜尋路徑 `/etc/jt-glogarch/`、檔案載入、WebConfig localadmin |
| 13 | `test_upgrade.py` | 4 | 舊 DB 自動升級、舊 config 向下相容、歸檔升級後保留、DB 備份有效性 |
| 14 | `test_api_error_handling.py` | 4 | Graylog API 401/502/連線失敗的錯誤處理（/api/index-sets 與 /api/streams） |
| 15 | `test_cli_commands.py` | 3 | 16 個指令全註冊、hash-password help、root 警告邏輯 |
| 16 | `test_cleanup_race.py` | 3 | 寬限常數 = 600 秒、新檔跳過、舊檔不跳過 |
| 17 | `test_storage_ownership.py` | 3 | root chown 修復、非 root 報錯、限定 base_path 以下 |
| 18 | `test_health_endpoint.py` | 2 | 回應結構（status/version/checks/issues）、公開路徑（免認證） |
| 19 | `test_opensearch_client.py` | 1 | `_doc` 排序 tiebreaker（非 `_id` — circuit breaker 修正） |

### 整合測試

| # | 測試檔 | 筆數 | 覆蓋範圍 |
|---|---|---|---|
| 20 | `test_integration.py` | 6 | 真實 OpenSearch cross-conflict 偵測、zlib schema 完整 preflight 流程、timezone dedup/retention/coverage-ratio 正確性、歸檔寫入→SHA256→讀回完整性 |

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

### 客戶安裝 / 升級模擬

- [ ] 複製 `github/` 到暫存目錄 → `pip install` 成功
- [ ] `deploy/install.sh` 路徑正確、systemd 預設 = Yes
- [ ] `deploy/upgrade.sh` 可正常執行（db-backup → git pull → install → restart → verify）

### 測試結果

- [ ] `./scripts/run-tests.sh` 通過 — `TEST-RESULTS.md` 已產生
- [ ] `TEST-RESULTS.md` 已 commit 到這個版本

---

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
