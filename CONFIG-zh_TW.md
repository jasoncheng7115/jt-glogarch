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
  gap_refill_hours: 168                 # API 排程匯出：補匯續傳點之前這幾小時內、先前執行留下的空缺
                                        # （失敗的區段）；0 = 關閉
  max_file_size_mb: 50                  # 單一檔案超過此大小自動分割
  min_disk_space_mb: 500                # 磁碟空間低於此值停止匯出
  delay_between_requests_ms: 5          # API 請求間隔（毫秒）
  query: "*"                            # 查詢條件（預設全部）
  streams: []                           # 限定串流（空 = 全部）
  index_sets: []                        # OpenSearch 模式：限定這些 index set ID。
                                        # 空 = 歸檔「所有」index set（安全預設；限縮清單會記錄略過哪些）
  fields: []                            # 限定欄位（空 = 全部）

  # --- 自動調節反壓守護（見下方說明） ---
  jvm_memory_threshold_pct: 75.0        # heap 軟門檻：持續高於此 % 才暫停
  jvm_memory_hard_pct: 90.0             # heap 硬上限：單次 >= 此 % 立即暫停
  health_heap_sustained_samples: 2      # 軟門檻連續超過幾次才暫停
  health_heap_signal: auto              # auto＝Graylog 有提供 GC 指標時改用 GC 指標判斷 heap
                                        # （見下方「Graylog 7 的 heap 壓力」）；used＝一律用原始使用率
  health_gc_overhead_pct: 10.0          # GC 指標：GC 時間持續 >= 總時間的此 % 即暫停
  health_pace_start_pct: 70.0           # API 匯出：GC 後 heap 超過此 % 開始放慢
  health_pace_max_delay_sec: 5.0        # API 匯出：GC 後 heap 到硬上限時，每頁等待秒數
  health_search_cache_flush_sec: 310    # 因 heap 暫停超過此秒數：每分鐘送幾次只抓 1 筆的搜尋，
                                        # 讓 Graylog 清掉過期的搜尋結果（0＝關閉）
  health_guard_enabled: true            # 守護總開關
  health_sample_interval_sec: 15        # 固定取樣節奏（秒）——非每個 chunk！
  health_rise_samples: 3                # 連續成長幾次才算「持續上升」
  health_journal_min_delta: 200         # journal 每次成長 >= 此筆數才算上升
  health_buffer_min_delta: 64           # buffer 每次成長 >= 此值才算上升
  health_pause_interval_sec: 15         # 暫停時多久重讀一次
  health_max_pause_min: 30              # 高負載持續超過此分鐘數即停止匯出
  health_stop_retry_min: 60             # 排程因此停止時，隔這麼久再試一次（0＝等下一次排程）
  health_resume_drain_ratio: 0.7        # 訊號回落到 峰值 × 此比例 以下才恢復
  connection_failure_limit: 10          # 連續連線失敗達此次數即中止
```

### 自動調節反壓守護

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
| JVM heap（GC 指標，Graylog 有提供時的預設） | GC 剛結束 heap 仍 `>=` 硬上限；距上次讀取發生過 Full GC；GC 時間持續 `>=` 總時間的 N% | `jvm_memory_hard_pct: 90`、`health_gc_overhead_pct: 10` + `health_heap_sustained_samples: 2` |
| JVM heap %（硬）：無 GC 指標或設為 `health_heap_signal: used` | 單次讀到 `>=` 硬上限 | `jvm_memory_hard_pct: 90` |
| JVM heap %（軟）：同上 | **持續** N 次 `>=` 軟門檻 | `jvm_memory_threshold_pct: 75` + `health_heap_sustained_samples: 2` |
| disk journal（未提交筆數） | **持續上升** | `health_rise_samples: 3` + `health_journal_min_delta: 200` |
| input／process／output buffer | 任一**持續上升** | `health_rise_samples: 3` + `health_buffer_min_delta: 64` |
| 讀不到 Graylog | 立即暫停（**fail-safe**） | — |

- **兩段式 heap**（原始使用率，沒有 GC 指標時）：軟門檻（75%）遠早於天花板就退載，但要連續 `health_heap_sustained_samples`
  次都偏高才暫停，避免單一 GC 鋸齒尖峰誤觸；硬上限（90%）單次就暫停以抓突發飆高。
  反應：軟 ≈ 2×15 秒 = 30 秒、硬 ≤ 15 秒。
- **「持續上升」**＝ `health_rise_samples + 1` = **4 次連續讀數**（15 秒節奏下約 60 秒），
  每次至少成長 min-delta（journal 每次 ≥ 200 筆 → 淨增 ≥ 600；buffer 每次 ≥ 64）。可濾掉
  正常抖動，只在真正積壓時觸發。
- **暫停中**每 `health_pause_interval_sec`（15 秒）重讀一次。
- **恢復**需：heap `<` 門檻、沒有任何訊號在上升，且每個 journal／buffer 訊號都回落到
  暫停期間峰值 × `health_resume_drain_ratio`（0.7 → 從峰值退 ≥ 30%）以下。也就是必須真的
  降下來，不是只停止上升。
- **放棄**：高負載持續 `health_max_pause_min`（30 分鐘）未降，這次執行就在這裡結束，而且只停一次，
  不會一個區段、一個 index 地重來。已封存的每個小時都保留，正在寫的那一小時會丟棄，下次從那裡接續。
  排程執行會在 `health_stop_retry_min`（60 分鐘）後**再試一次**（1 分鐘後就重試只會碰到同樣的負載），
  還是不行就留給下一次排程。不論哪種情況都只發一則通知，作業紀錄會寫明停止前已封存多少筆。
- **斷路器**：`connection_failure_limit`（10）次連續連線失敗即中止，不再對死掉的伺服器猛打。
- **fail-safe**：讀不到 Graylog（正是它可能出狀況的當下）視為有壓力並暫停，**不會**把
  「讀不到」當成健康。

#### Graylog 7 的 heap 壓力：GC 指標、控速與暫存的搜尋結果

- **看 GC 指標，不看使用率**：`health_heap_signal: auto`（預設）用 Graylog 自己的 GC 指標判斷
  heap（`jvm.*` 指標；可辨識 G1、Parallel、Serial）。使用率會把下一次 young GC 就會回收的垃圾
  也算進去：健康的 3 GB Graylog 沒有匯出時也會在 75%～95% 之間來回，所以舊的判斷讓每晚的
  API 匯出暫停了一半以上的時間。沒有 GC 指標時，沿用上方的兩段式使用率判斷。
- **API 匯出為什麼會把 Graylog 的 heap 撐滿**：Graylog 7 會把每次搜尋的完整結果，在最後一次
  讀取後保留 5 分鐘（最多 1,000 次搜尋）。所以 API 匯出佔用的 heap，大約等於它自己最近 5 分鐘
  的匯出量。實測在訊息約 2.4 KB 的站台，每匯出 1 筆約佔 Graylog 10 KB heap；3 GB 的 Graylog
  在每秒約 760 筆時，GC 後 heap 就到 90%。
- **控速（只有 API 匯出）**：GC 後 heap 超過 `health_pace_start_pct`，匯出就在每頁之間等待，
  等待時間線性增加，到 `jvm_memory_hard_pct` 時為 `health_pace_max_delay_sec`。匯出速度因此
  會穩定在這台 Graylog 撐得住的程度，而不是一路衝到 Full GC。延遲改變時，記錄會出現
  `export pacing adjusted`。OpenSearch 直連不會對 Graylog 搜尋，所以不控速。
- **光靠暫停放不掉這些 heap**：Graylog 只有在處理下一次搜尋時，才會清掉過期的結果。匯出一暫停
  就沒人搜尋，留下來的 heap 就一直留著：實際站台在整整 30 分鐘的暫停裡，GC 後 heap 都停在
  90%～91%（GC 跑了幾十輪，判斷全都還在使用），送出 4 次小搜尋後 5 分鐘內就降到 74%。所以
  因 heap 暫停超過 `health_search_cache_flush_sec`（310 秒，剛好超過 5 分鐘的保留時間）時，
  會每分鐘送幾次只抓 1 筆的搜尋，並記錄 `asked Graylog to release expired search results`。
  因 journal 或 buffer 暫停時不會送。
- **API 模式的上限在 Graylog 每次搜尋的固定成本**：Graylog 7 每次搜尋都會讀取所涵蓋的每個
  index 的欄位型別，和每頁筆數無關：119 個 index、15 萬個欄位的站台每次約 550 毫秒，小站台
  約 40 毫秒。每頁 1,000 筆時，API 模式最多約每秒 890 筆。保留的 index 少一點、不同的欄位少
  一點，Graylog 所有的搜尋都會變快，不只是匯出。

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

### Graylog Data Node（用戶端憑證，beta）

Data Node 的 OpenSearch 只接受用戶端憑證。**請在網頁介面設定**（系統設定 → Graylog 伺服器 → 編輯 → Graylog Data Node（beta）→ 連接 Data Node），它會寫入下面這個 per-server 區塊，請不要手動修改：

```yaml
servers:
  - name: graylog-dn
    url: "http://192.168.1.20:9000"
    username: admin                     # 必須是 Graylog Admin（ca_clientcert:create）
    password: "..."
    opensearch:
      hosts: ["https://datanode1:9200"] # Graylog 回報的 transport_address，或 IP
      verify_ssl: false                 # true = 同時檢查 Data Node 主機名稱
      client_cert_file: /opt/jt-glogarch/certs/datanode/graylog-dn/client.crt
      client_key_file:  /opt/jt-glogarch/certs/datanode/graylog-dn/client.key   # 0600
      ca_file:          /opt/jt-glogarch/certs/datanode/graylog-dn/ca.crt       # 一律驗證
      datanode: true                    # 經由 Graylog 簽發，自動更新
      datanode_principal: jt-glogarch-<主機>-graylog-dn
      datanode_roles: [all_access]
      datanode_lifetime_days: 90
      cert_not_after: '2027-02-12T15:42:21'
```

| 鍵 | 說明 |
|---|---|
| `client_cert_file` / `client_key_file` | 雙向 TLS 用的 PEM 憑證與未加密金鑰。設定後不會再送 Basic 認證。 |
| `ca_file` | 伺服器憑證一律以這個 CA 驗證；`verify_ssl` 只再加上主機名稱檢查。 |
| `datanode` | `true`：jt-glogarch 會在剩下三分之一有效期時更新憑證（每次 OpenSearch Direct 作業之前，以及每天 04:45），OpenSearch 拒絕時會重新簽發。排程的 OpenSearch Direct 作業若仍無法使用，會改用 Graylog API 歸檔並通知。 |
| `datanode_roles` | `all_access`：唯讀的 `readall` 無法列出索引與別名（7.2.2 實測）。Graylog 只接受已有角色對應的角色。 |

這三個檔案放在 `config.yaml` 旁的 `certs/` 底下，升級不會動到。同一個對話框的「中斷連線」會把憑證名稱從角色對應中移除並刪除檔案。匯入目標網址是這台伺服器的網址時，Bulk 匯入也會使用這個區塊。

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
  language: zh-TW                       # en、zh-TW 或 ja
  link_base_url: ""                     # 例如 https://192.0.2.10:8990：資安通知附上各事件的連結（留空＝不附連結）
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

  zulip:
    enabled: false
    server_url: ""       # 例如 https://chat.example.com
    bot_email: ""        # bot 的電子郵件（Zulip：個人設定 → Bots）
    api_key: ""          # bot 的 API 金鑰（Web UI 中以遮罩顯示）
    stream: ""           # bot 已加入的串流（頻道）
    topic: "jt-glogarch"

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

## security — 資安事件（v1.20.0，預設關閉）

```yaml
security:
  enabled: false              # 開啟後，本機會依間隔查詢下方的 Graylog
  server: ""                  # 空白 = default_server
  interval_minutes: 15        # 5 到 1440
  window_minutes: 60          # 每次統計最近 N 分鐘
  reopen_hours: 24            # 沉寂這麼久就視為事件結束；之後再出現會開新事件
  new_days: 90                # 偵測項目 N 天內沒看過這個來源，就標示「首次出現」
  notify_min_severity: high   # high｜medium｜low｜off
  renotify_hours: 24          # 持續中的事件，隔 N 小時再提醒一次
  retention_days: 180
  exclude_query: ""           # 所有偵測都排除的 Graylog 查詢
  detectors:                  # 每項偵測可設 enabled、min_count、exclude（皆可省略）
    account_multi_host:
      exclude: "user_name:/.*[$]/"   # 預設值：排除電腦帳號（DC1$）
    waf_scanner:
      blocked_min_count: 1000        # v1.35.0：被 WAF 擋下的掃描，在分析時間範圍內未達這個筆數就記成「低」
                                     #   （預設的通知門檻下不會通知）
    account_new_source:              # v1.29.0，預設關閉（記下每組帳號與來源；7 天學習期）
      enabled: false
    volume_anomaly:                  # v1.30.0，預設關閉（每次分析多兩次所有記錄的彙總；
      enabled: false                 #   為每台主機與類別保存每小時紀錄，7 天學習期）
      min_count: 500                 # 每「小時」的筆數（另需達平常的 5 倍、穩健 z 分數 >= 4）
    source_silent:                   # v1.26.0，預設關閉（每次分析要彙總一整天的所有記錄）
      enabled: false
      min_count: 50                  # 最近 2 小時之前的 24 小時內的筆數
  ai_auto: false              # v1.22.0：每次分析後由 AI 分析（需要 ai.analysis_enabled）
  ai_auto_min_severity: high  # high、medium 或 low：從這個嚴重程度起的新增或升級事件
  ai_auto_max_per_run: 3      # 1 到 10；每件呼叫一次模型，並對 Graylog 查詢約十次
  ai_notify_verdicts: []      # v1.29.0：例如 [malicious, suspicious]，自動分析後送出一則後續通知
  field_map: {}               # v1.35.0：內建偵測讀取的資料在本站的哪個欄位（設定 → 欄位對應）；
                              #   項目 q_auth_failure、q_auth_success、q_ids_passed、q_web_attack（搜尋條件），
                              #   f_peer、f_waf_peer（逗號分隔）、f_account、f_host、f_ids_signature、
                              #   f_ids_severity、f_ids_peer、f_uri、f_vhost、f_category；未設定＝GIM 預設
                              #   （1.35）q_waf_blocked：哪些網站攻擊被 WAF 擋下（在 q_web_attack 之內判斷）；
                              #   f_status：HTTP 回應碼（事件細節用）
  sigma_field_map: {}         # v1.27.0：Sigma 欄位 -> Graylog 欄位（在 Sigma 分頁編輯）
  sigma_max_rules: 50         # 可啟用的 Sigma 規則數，每條每次分析做一次彙總查詢
  sigma_library_enabled: false   # v1.33.0：下載 SigmaHQ 規則套組（每天檢查，只連 github.com）
  sigma_library_package: core    # core | core+ | core++ | emerging_threats | all
  sigma_library_auto_update: true  # 從規則庫加入的規則隨新版本更新
  ti_enabled: false           # v1.28.0：下載威脅情資清單（不會送出這個站台的任何資料）
  ti_feeds: [spamhaus_drop, tor_exit, feodo]
  ti_refresh_hours: 24        # 1 到 168
  digest_enabled: false       # v1.32.0：透過通知管道寄送每週摘要
  digest_cron: "0 8 * * 1"    # POSIX cron，本地時間（每週一 08:00）；儲存時會檢查格式
```

每次分析都使用 Graylog 的彙總 API（`POST /api/search/aggregate`，Graylog 6.x 與 7.x；
已在 6.3.15 與 7.2.2 實測）：6 次查詢；若有來源大量登入失敗，需要再查一次登入成功，則是 7 次。
只讀取筆數，不讀取記錄內容。Graylog 的 heap 達到 `export.jvm_memory_hard_pct` 以上時會略過該次分析（並註明原因）；
Graylog 連不上算一次失敗，連續三次失敗會送出一則「資安事件分析沒有在運作」的通知。第一次分析後的 24 小時為學習期，
不標示「首次出現」。通知使用 `notify.on_security_incident` 開關（預設開啟）與原有的通知管道。
這些設定也可以在「資安事件」頁面修改。

開啟 `ai_auto` 後，該次分析新增或升級的事件會在通知送出之後交給 AI 模型分析（不會在通知之前，因為模型可能要
好幾分鐘）。遇到第一個失敗（LLM 連不上、token 額度用完）就停止該次的其餘分析。

---

## ai — 智慧問答與 MCP 端點（v1.21.0，預設關閉）

```yaml
ai:
  enabled: false              # 「智慧問答」頁面
  llm_servers:                # v1.36.0：一台或多台 LLM 伺服器
    - name: local             # 顯示在對話時的伺服器選單
      kind: openai            # openai（llama.cpp、vLLM、LM Studio、Ollama /v1）| anthropic（Claude API）
      url: http://10.0.0.5:8080/v1   # anthropic：留空 = https://api.anthropic.com
      model: ""
      api_key: ""             # API 回傳時遮罩；儲存時收到遮罩值會保留，只限同類型、同網址
      timeout_seconds: 300    # 10 到 900
      allow_external: false   # 內網以外的伺服器預設拒絕，設為 true 才允許（記入稽核）；Claude 必須開啟
      temperature: 0.2        # 只用於 openai（Claude API 不接受取樣參數）
      context_tokens: 0       # 0 = 詢問伺服器（llama.cpp /props、/v1/models、LM Studio、Ollama、Claude）
      effort: ""              # 只用於 anthropic：low|medium|high|xhigh|max；"" = 模型預設
      daily_tokens: 0         # 此伺服器自己的上限；0 = 不限
      monthly_tokens: 0
  default_llm: local          # 資安事件分析使用，也是對話的預設
  url: ""                     # 1.21～1.35 的單一伺服器：載入時成為 llm_servers 第一台；
  model: ""                   #   儲存時把預設的 OpenAI 相容伺服器寫回這裡，
  api_key: ""                 #   退回舊版仍找得到
  max_tool_rounds: 6          # 用完後模型必須依現有資料作答
  max_range_hours: 24         # 會拉取記錄的工具最長時間範圍；精確計數可到 31 天
  daily_tokens: 0             # 全站（所有使用者與伺服器合計）；0 = 不限；以 UTC 日計算
  monthly_tokens: 0
  user_daily_tokens: 0        # v1.36.0：每位使用者；0 = 不限
  user_monthly_tokens: 0
  chat_retention_days: 90     # 0 = 永久保留
  mcp_enabled: false          # 給外部 AI 用戶端的 POST /mcp
  mcp_graylog_tools: []       # 空白 = 預設的唯讀工具組
  analysis_enabled: false     # v1.22.0：「資安事件」頁面的 AI 按鈕
```

智慧問答以登入者的身分讀取 Graylog（在頁面上登入 Graylog；密碼會換成 Graylog 工作階段，不會儲存）。
`/mcp` 接受 `Authorization: Bearer <Graylog API token>`（或 Basic `<token>:token`），依
`web.allowed_graylog_roles` 檢查 token 的角色，並以 `X-Graylog-Server` 標頭選擇伺服器（未指定則用預設伺服器）；
每個 token 每分鐘 120 次請求。不論來自智慧問答或 MCP，每次工具呼叫都以 `ai_tool_call` 記入稽核。
對話只保存問題、答案和用到的工具名稱，不保存工具查回的資料。mcp_graylog 的兩個除錯工具、大量匯出工具和內容套件
詳細資料一律不開放；`find_silent_sources` 最多回溯 31 天。`get_log_statistics`、`analyze_error_patterns` 與
`get_log_level_analysis` 只有列在 `mcp_graylog_tools` 裡才開放（每次呼叫會拉取記錄長達兩分鐘，在 7.2.2 實測）。
查詢只有 `*` 或 `*:*` 時，送給 mcp_graylog 的是空白查詢；其他以萬用字元開頭的查詢一律拒絕。

資安事件的 AI 分析（`analysis_enabled`）使用偵測所用的伺服器連線讀取 Graylog，以針對該事件的固定查詢（最多該事件
最後 24 小時）取得：精確計數與前幾名、同一來源或帳號的成功登入、8 筆範例記錄，以及這個對象先前的事件。範例記錄
會送給模型，但不會保存；計數、模型的回覆與模型名稱會和事件一起保存（事件刪除時一併刪除）。使用與智慧問答相同的
LLM 伺服器、逾時與 token 額度（1.36 起使用預設的 LLM 伺服器）。

**v1.36.0。** 每次請求依模型的上下文長度（`context_tokens`，或伺服器回報的值）決定回答長度、每個工具結果放多少、
帶入多少前文、提供哪些工具。放不下的工具結果會在記憶體保留 30 分鐘（只限同一位使用者、同一管道、同一台 Graylog，
不寫入磁碟），模型以 `read_result` 分頁讀取。`aggregate` 與 `summarize_messages` 在 jt-glogarch 端做計數與樣式歸納：
`aggregate` 的分組最多 10,000 列、500 個時間區間（OpenSearch 上限為 65,535 個 bucket）；`summarize_messages` 最多讀
10,000 筆（Graylog 的分頁上限）、最多 60 秒。Claude 伺服器需要 Python 套件 `anthropic`（1.36.0 起為相依套件，只有設定了
這類伺服器時才載入）。

---

## web — Web UI

```yaml
web:
  host: 0.0.0.0                         # 監聽位址
  port: 8990                            # 監聽埠號
  ssl_certfile: /opt/jt-glogarch/certs/server.crt
  ssl_keyfile: /opt/jt-glogarch/certs/server.key
  localadmin_password_hash: ""          # 緊急登入密碼（SHA256 hash）
  allowed_graylog_roles: [Admin]        # 可登入的 Graylog 角色（1.18.2 起）
```

### 誰可以登入

Graylog 帳號必須具有 `allowed_graylog_roles` 列出的角色（不分大小寫，預設 `Admin`），
或具有 `*` 權限（Graylog 內建的 `admin` 有）才能登入。每次登入時 jt-glogarch 都會向 Graylog
讀取該帳號的角色，密碼登入與 API 權杖登入都一樣；讀不到角色時拒絕登入。

- 要讓某個角色的成員登入，就把角色加進去，例如 `allowed_graylog_roles: [Admin, Archive Operators]`。
- `["*"]` 讓所有 Graylog 帳號都能登入，並使用這裡的所有功能。不建議。
- 升級到 1.18.2 會讓所有人登出一次。沒有允許角色的帳號會看到「這個 Graylog 帳號不能使用 jt-glogarch」；
  請改用 Graylog 管理員帳號或 `localadmin` 登入，或把角色加進設定。

### 緊急本機管理員

Graylog 離線時 Web UI 無法登入（認證委派給 Graylog API）。設定緊急密碼可在 Graylog 不可用時 fallback 登入：

```bash
# 產生 hash
glogarch hash-password
# 輸入兩次密碼，把產生的 hash 貼入 config.yaml
```

**登入帳密：** 帳號 `localadmin`，密碼為你設定的緊急密碼。

`localadmin` 不論 Graylog 是否連得上都能登入（1.12.10 起），也不受上面的角色檢查限制。Graylog 連不上時，登入頁面會顯示橘色警告，提示改用它。

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
