# jt-glogarch 設定參考

**語言**： [English](CONFIG.md) | **繁體中文**

設定檔位於 `/opt/jt-glogarch/config.yaml`，檔案擁有者必須是 `jt-glogarch`。

大部分設定可在 Web UI 的「排程作業」和「通知設定」頁面完成，不需手動編輯。
以下為完整欄位說明，供需要手動調整或自動化部署時參考。

---

## servers — Graylog 連線

```yaml
servers:
  - name: log4                          # 自訂名稱（用於歸檔目錄分類）
    url: "http://192.168.1.10:9000"    # Graylog REST API URL
    auth_token: "your-api-token"        # API Token（建議）
    # username: admin                   # 或帳號密碼（二擇一）
    # password: admin
    verify_ssl: false                   # HTTPS 驗證

default_server: log4                    # 預設使用的伺服器
```

> API Token 取得：Graylog → System → Users → 你的帳號 → Edit Tokens → Create Token

### 多台伺服器（多來源歸檔）

把每台 Graylog 伺服器都列在 `servers:` 下。每個匯出工作（手動或排程）都鎖定**一台**伺服器（在 Web UI 匯出／排程對話框選擇，或用 `glogarch export --server <名稱>`）。要自動歸檔多台，就**為每台各建一個匯出排程**。

每台伺服器還能透過 per-server 的 `opensearch:` 區塊帶**自己的** OpenSearch 叢集（供 OpenSearch 直連模式使用）；未填時則退回全域的 `opensearch:` 區塊：

```yaml
servers:
  - name: graylog-main
    url: "http://192.168.1.10:9000"
    auth_token: "TOKEN_A"
    verify_ssl: false
    opensearch:                         # 此伺服器背後的叢集
      hosts:
        - "http://192.168.1.10:9200"
        - "http://192.168.1.11:9200"   # 「同一個叢集」的容錯節點
      username: admin
      password: "OS_PASSWORD_A"
      verify_ssl: false

  - name: graylog-siteB
    url: "http://10.0.0.5:9000"
    auth_token: "TOKEN_B"
    verify_ssl: false
    opensearch:
      hosts: ["http://10.0.0.5:9200"]
      username: admin
      password: "OS_PASSWORD_B"
      verify_ssl: false

default_server: graylog-main
```

---

## export — 匯出設定

```yaml
export_mode: opensearch                 # api 或 opensearch

export:
  base_path: /data/graylog-archives     # 歸檔存放路徑
  batch_size: 1000                      # API 模式每次查詢筆數
  chunk_duration_minutes: 60            # 每個歸檔檔案涵蓋的時間長度（分鐘）
  max_file_size_mb: 50                  # 單一檔案超過此大小自動分割
  min_disk_space_mb: 500                # 磁碟空間低於此值停止匯出
  delay_between_requests_ms: 5          # API 請求間隔（毫秒）
  query: "*"                            # 查詢條件（預設全部）
  streams: []                           # 限定串流（空 = 全部）
  fields: []                            # 限定欄位（空 = 全部）

  # --- 自適應反壓守護（見下方說明） ---
  jvm_memory_threshold_pct: 75.0        # heap 軟門檻：持續高於此 % 才暫停
  jvm_memory_hard_pct: 90.0             # heap 硬上限：單次 >= 此 % 立即暫停
  health_heap_sustained_samples: 2      # 軟門檻連續超過幾次才暫停
  health_guard_enabled: true            # 守護總開關
  health_sample_interval_sec: 15        # 固定取樣節奏（秒）——非每個 chunk！
  health_rise_samples: 3                # 連續成長幾次才算「持續上升」
  health_journal_min_delta: 200         # journal 每次成長 >= 此筆數才算上升
  health_buffer_min_delta: 64           # buffer 每次成長 >= 此值才算上升
  health_pause_interval_sec: 15         # 暫停時多久重讀一次
  health_max_pause_min: 30              # 高負載持續超過此分鐘數即停止匯出
  health_resume_drain_ratio: 0.7        # 訊號回落到 峰值 × 此比例 以下才恢復
  connection_failure_limit: 10          # 連續連線失敗達此次數即中止
```

### 自適應反壓守護

大量匯出會對 Graylog 用來索引的**同一個** OpenSearch 叢集造成負載。在繁忙或 HDD
儲存的叢集上，這會餓死 ingestion——disk journal 與環形緩衝區積壓、Graylog 停止
收 log（最糟需重啟才能恢復）。守護會在每個 chunk／批次之間讀取 Graylog 自身的健康
訊號，**一旦 ingestion 落後就暫停匯出，降下來才續跑**。

**`export_mode: api` 與 `export_mode: opensearch` 皆適用**——同一個守護、同一組門檻
（如下）。OS 直連一樣會壓叢集，所以照樣監看同一組 Graylog 訊號。

**取樣是固定時間節奏**（`health_sample_interval_sec`，15 秒），**不是每個 chunk**。
兩種模式都在每個 batch 檢查，但只每 15 秒真正讀一次 Graylog——所以再長的 chunk 也
全程被監看，下面那些趨勢門檻的反應時間才有意義（若只在 chunk 邊界檢查，兩次讀之間可能
隔好幾分鐘，門檻等於失效）。

各訊號與「暫停」的條件：

| 訊號 | 暫停條件 | 預設門檻 |
|---|---|---|
| JVM heap %（硬） | 單次讀到 `>=` 硬上限 | `jvm_memory_hard_pct: 90` |
| JVM heap %（軟） | **持續** N 次 `>=` 軟門檻 | `jvm_memory_threshold_pct: 75` + `health_heap_sustained_samples: 2` |
| disk journal（未提交筆數） | **持續上升** | `health_rise_samples: 3` + `health_journal_min_delta: 200` |
| input／process／output buffer | 任一**持續上升** | `health_rise_samples: 3` + `health_buffer_min_delta: 64` |
| 讀不到 Graylog | 立即暫停（**fail-safe**） | — |

- **兩段式 heap**：軟門檻（75%）遠早於天花板就退載，但要連續 `health_heap_sustained_samples`
  次都偏高才暫停，避免單一 GC 鋸齒尖峰誤觸；硬上限（90%）單次就暫停以抓突發飆高。
  反應：軟 ≈ 2×15 秒 = 30 秒、硬 ≤ 15 秒。
- **「持續上升」**＝ `health_rise_samples + 1` = **4 次連續讀數**（15 秒節奏下約 60 秒），
  每次至少成長 min-delta（journal 每次 ≥ 200 筆 → 淨增 ≥ 600；buffer 每次 ≥ 64）。可濾掉
  正常抖動，只在真正積壓時觸發。
- **暫停中**每 `health_pause_interval_sec`（15 秒）重讀一次。
- **恢復**需：heap `<` 門檻、沒有任何訊號在上升，且每個 journal／buffer 訊號都回落到
  暫停期間峰值 × `health_resume_drain_ratio`（0.7 → 從峰值退 ≥ 30%）以下。也就是必須真的
  降下來，不是只停止上升。
- **放棄**：高負載持續 `health_max_pause_min`（30 分鐘）未降，匯出即以錯誤停止並發通知。
- **斷路器**：`connection_failure_limit`（20）次連續連線失敗即中止，不再對死掉的伺服器猛打。
- **fail-safe**：讀不到 Graylog（正是它可能出狀況的當下）視為有壓力並暫停，**不會**把
  「讀不到」當成健康。

每次暫停都會寫入系統記錄，並在執行中的作業上顯示是哪個訊號觸發。

---

## import — 匯入設定

```yaml
import:
  gelf_host: localhost                  # GELF 目標主機
  gelf_port: 32202                      # GELF 埠號
  gelf_protocol: tcp                    # tcp（預設，有 backpressure）或 udp
  batch_size: 500                       # 每批發送筆數
  delay_between_batches_ms: 100         # 批次間隔（毫秒）
```

> GELF 模式的主機、埠號、速率都可在 Web UI 匯入對話框中覆寫。

---

## opensearch — OpenSearch 直連

```yaml
opensearch:
  hosts:                                # 「同一個叢集」的容錯節點
    - "http://192.168.1.10:9200"       # （並非多個叢集）
    - "http://192.168.1.11:9200"
  username: admin
  password: "your-password"
  verify_ssl: false
```

> 不使用 OpenSearch 直連模式可整段不填。

**全域 vs per-server。** 這個頂層 `opensearch:` 區塊是**全域後備**。若某台伺服器設了自己的 `servers[].opensearch:` 區塊，就會改用該區塊。`hosts` 清單永遠是**同一個叢集的容錯節點** —— 要歸檔**不同的** OpenSearch 叢集，請各自建立獨立的伺服器條目，並為其設定 per-server 的 `opensearch:` 區塊（見[多台伺服器](#多台伺服器多來源歸檔)）。

| 你要歸檔的是… | 設定方式 |
|---|---|
| 一個叢集、多個節點 | `hosts: [節點1, 節點2, …]`（容錯備援） |
| 多個獨立叢集 | 每個叢集各建一個 `servers[]` 條目，各自帶 `opensearch:` 區塊 |

> CLI：`glogarch test-opensearch --server <名稱>` 會測試該伺服器解析到的叢集。

---

## schedule — 排程

```yaml
schedule:
  export_cron: "0 3 * * *"             # 匯出排程（Cron 格式）
  export_days: 180                      # 每次匯出涵蓋最近 N 天
  cleanup_cron: "0 4 * * *"            # 清理排程
```

> 排程可在 Web UI「排程作業」頁面新增、編輯、立即執行。
> 此處為初始預設值，Web UI 儲存後會覆寫。

---

## retention — 保留策略

```yaml
retention:
  enabled: true
  retention_days: 1095                   # 超過此天數的歸檔自動刪除（預設：3 年）
```

---

## integrity — 歸檔防竄改（選用，預設關閉）

在裸 SHA256 之上加一層**帶秘鑰的 HMAC-SHA256**，讓「同時改歸檔檔案與 DB checksum」也無法
偽造出正確的完整性值——只有握有秘鑰的人才算得出來。預設關閉，依部署需求啟用。

```yaml
integrity:
  enabled: false                          # 需自行啟用;啟用後新歸檔才會 HMAC 封存
  hmac_key_file: /opt/jt-glogarch/.hmac_key   # 權限 0600;未設 JT_HMAC_KEY 環境變數時使用
  ledger_enabled: true                    # 每次封存寫入 integrity_ledger 表
```

設定步驟：

```bash
glogarch integrity-init            # 產生金鑰檔（請備份到機器外！）
# 在 config.yaml 設 integrity.enabled: true,然後:
glogarch integrity-seal            # 封存既有歸檔（僅證明「從現在起」未被動）
glogarch verify                    # 會回報 TAMPERED（HMAC 不符）與 CORRUPTED（SHA256）之別
glogarch integrity-manifest -o /安全/機器外/manifest.json   # 把清單存到歸檔主機以外
```

- **金鑰優先序：** 環境變數 `JT_HMAC_KEY`（base64／hex）> `hmac_key_file`。
- **防 root 模式：** 不要把金鑰檔留在機器上——僅在封存／驗證時以 `JT_HMAC_KEY` 提供，並把
  manifest 存到機器外。這樣即使 root／服務帳號把檔案與 DB 全改了，也能用機外副本揪出。
- **誠實界線：** 對已被竄改的舊檔補封，只能證明「從現在起」未被動，無法回溯證明過去。遺失
  金鑰則 HMAC 檢查退回僅 SHA256。

---

## rate_limit — 速率限制

```yaml
rate_limit:
  requests_per_second: 2.0             # API 模式每秒請求數
  adaptive: true                        # 依 CPU 使用率自動調整
  max_cpu_percent: 80                   # CPU 超過此 % 自動降速
  backoff_seconds: 10                   # 降速後等待秒數
```

---

## notify — 通知

```yaml
notify:
  language: zh-TW                       # en 或 zh-TW
  on_export_complete: true
  on_import_complete: true
  on_cleanup_complete: false
  on_error: true
  on_verify_failed: true

  telegram:
    enabled: false
    bot_token: ""
    chat_id: ""

  discord:
    enabled: false
    webhook_url: ""

  slack:
    enabled: false
    webhook_url: ""

  teams:
    enabled: false
    webhook_url: ""

  nextcloud_talk:
    enabled: false
    server_url: ""
    token: ""
    username: ""
    password: ""

  email:
    enabled: false
    smtp_host: ""
    smtp_port: 587
    smtp_tls: true
    smtp_user: ""
    smtp_password: ""
    from_addr: ""
    to_addrs: []
    subject_prefix: "[jt-glogarch]"
```

> 所有通知管道都可在 Web UI「通知設定」頁面完成，不需手動編輯。

---

## op_audit — 行為稽核（Graylog 操作追蹤）

```yaml
op_audit:
  enabled: true                           # 啟用行為稽核（接收 nginx syslog）
  listen_port: 8991                       # syslog UDP 監聽埠號
  max_body_size: 65536                    # 每筆記錄最大 request body（bytes）
  alert_sensitive: true                   # 偵測到敏感操作時發送通知（刪除使用者/stream/input 等）
```

> 稽核記錄會在排程清理（cleanup）執行時一併清除，使用與歸檔檔案相同的 `retention.retention_days` 保留天數，不需要單獨設定。

### 運作方式

每台 Graylog 前端的 nginx 反向代理將 access log 透過 syslog UDP 傳送至 jt-glogarch。
jt-glogarch 解析 log、從 Authorization header 解碼 Graylog 帳號、分類操作類型，
並儲存至 SQLite。敏感操作（刪除使用者/stream/input、登入登出等）會觸發通知。

IP 白名單**完全自動**：從 `servers[].url` + Graylog Cluster API
（`GET /api/system/cluster/nodes`）取得，每 5 分鐘自動更新，無需手動設定。

Token 認證會自動解析為實際 Graylog 帳號（透過 Users API 快取，每 10 分鐘更新）。

### nginx 設定

請至 Web UI「API 稽核」頁面 →「設定說明」查看完整 nginx 設定範例，
或使用 CLI：`glogarch audit-status`。

---

## web — Web UI

```yaml
web:
  host: 0.0.0.0                         # 監聽位址
  port: 8990                            # 監聯埠號
  ssl_certfile: /opt/jt-glogarch/certs/server.crt
  ssl_keyfile: /opt/jt-glogarch/certs/server.key
  localadmin_password_hash: ""          # 緊急登入密碼（SHA256 hash）
```

### 緊急本機管理員

Graylog 離線時 Web UI 無法登入（認證委派給 Graylog API）。設定緊急密碼可在 Graylog 不可用時 fallback 登入：

```bash
# 產生 hash
glogarch hash-password
# 輸入兩次密碼，把產生的 hash 貼入 config.yaml
```

**登入帳密：** 帳號 `localadmin`，密碼為你設定的緊急密碼。

Graylog 連不上時登入頁面會顯示橘色警告，提示使用 `localadmin` 帳號登入。本機管理員**只在 Graylog 連不上時**啟用。Graylog 正常但密碼錯誤時**不會** fallback。

---

## 其他

```yaml
database_path: /opt/jt-glogarch/jt-glogarch.db   # SQLite DB 路徑
log_level: INFO                                    # DEBUG / INFO / WARNING / ERROR
```

---

## Config 搜尋順序

1. CLI `--config` 參數指定的路徑
2. `./config.yaml`（目前目錄）
3. `~/.jt-glogarch/config.yaml`
4. `/etc/jt-glogarch/config.yaml`

找到第一個存在的檔案就使用。

## 注意事項

- 從 Web UI 儲存設定會**覆寫整個 config.yaml**。手動編輯後若在 Web UI 按儲存，手動修改會被覆蓋。
- 檔案擁有者必須是 `jt-glogarch`，否則 Web UI 無法寫入：`chown jt-glogarch:jt-glogarch /opt/jt-glogarch/config.yaml`
