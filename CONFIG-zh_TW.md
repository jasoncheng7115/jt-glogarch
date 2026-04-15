# jt-glogarch 設定參考

**語言**: [English](CONFIG.md) | **繁體中文**

設定檔位於 `/opt/jt-glogarch/config.yaml`，檔案擁有者必須是 `jt-glogarch`。

大部分設定可在 Web UI 的「排程作業」和「通知設定」頁面完成，不需手動編輯。
以下為完整欄位說明，供需要手動調整或自動化部署時參考。

---

## servers — Graylog 連線

```yaml
servers:
  - name: log4                          # 自訂名稱（用於歸檔目錄分類）
    url: "http://192.168.1.132:9000"    # Graylog REST API URL
    auth_token: "your-api-token"        # API Token（建議）
    # username: admin                   # 或帳號密碼（二擇一）
    # password: admin
    verify_ssl: false                   # HTTPS 驗證

default_server: log4                    # 預設使用的伺服器
```

> API Token 取得：Graylog → System → Users → 你的帳號 → Edit Tokens → Create Token

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
  jvm_memory_threshold_pct: 85.0        # Graylog JVM heap 超過此 % 停止匯出
  query: "*"                            # 查詢條件（預設全部）
  streams: []                           # 限定串流（空 = 全部）
  fields: []                            # 限定欄位（空 = 全部）
```

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
  hosts:                                # 可填多台，自動 failover
    - "http://192.168.1.132:9200"
    - "http://192.168.1.127:9200"
  username: admin
  password: "your-password"
  verify_ssl: false
```

> 不使用 OpenSearch 直連模式可整段不填。

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
