# jt-glogarch

**Graylog Open Archive** — Graylog Open (6.x / 7.x) 的記錄歸檔與還原工具

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.3.0-green.svg)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)]()

Graylog Open 版本不支援 Enterprise 版的 Archive 功能。
**jt-glogarch** 補上這個缺口,提供完整的記錄歸檔與還原工具,支援**兩種匯出模式**:

1. **Graylog REST API** — 標準方式,適用任何 Graylog Open 安裝
2. **OpenSearch Direct** — 繞過 Graylog 直接查詢 OpenSearch (約 5 倍速)

匯出的記錄會壓縮為 `.json.gz` 並有 SHA256 完整性驗證,可透過 GELF (UDP / TCP) 還原回任何 Graylog 實例。

> **作者:** Jason Cheng ([Jason Tools](https://jasontools.com))
> **授權:** Apache 2.0



---



## 目錄

- [功能特色](#功能特色)
- [架構與運作原理](#架構與運作原理)
- [使用情境](#使用情境)
- [快速開始](#快速開始)
- [安裝詳細說明](#安裝詳細說明)
- [設定](#設定)
- [Web UI 使用說明](#web-ui-使用說明)
  - [儀表板](#儀表板)
  - [歸檔清單](#歸檔清單)
  - [作業歷程](#作業歷程)
  - [排程作業](#排程作業)
  - [通知設定](#通知設定)
  - [系統記錄](#系統記錄)
- [匯入(還原)流程](#匯入還原流程)
- [效能與調校](#效能與調校)
- [CLI 指令參考](#cli-指令參考)
- [疑難排解 / 常見問題](#疑難排解--常見問題)
- [授權與作者](#授權與作者)



---



## 功能特色


### 雙模式匯出

| 功能 | Graylog API | OpenSearch Direct |
|---|---|---|
| 速度 | ~730 筆/秒 | ~3,300 筆/秒 |
| 分頁方式 | 時間視窗(突破 10K offset 限制) | `search_after` (無限制) |
| 串流篩選 | ✅ 支援 | ❌ 不支援(依 index) |
| 需要 | Graylog API Token | OpenSearch 帳密 |
| 記憶體保護 | JVM heap 監控(85% 自動停止) | 不需要 |
| 適用 | 串流篩選匯出、OpenSearch 鎖定的環境 | 大量歷史匯出、時間敏感任務 |


### 智慧去重

- **同模式去重** — 精確比對防止重複匯出相同時間範圍
- **跨模式去重** — 切換 API/OpenSearch 模式不會重複匯出
- **斷點續傳** — 已完成的區段絕不重做


### 歸檔管理

- **串流寫入** — 不會將所有訊息載入記憶體
- 自動分檔(預設 50MB)
- SHA256 完整性驗證(含 `.sha256` 附檔)
- 排程定期 SHA256 重新檢查
- 保留天數自動清理
- 從磁碟重新掃描歸檔(偵測孤兒檔案 / 遺失檔案)


### 匯入(還原)

- GELF UDP(預設,快速)或 TCP 發送器
- 完整保留原始 `timestamp`、`source`、`level`、`facility` 及所有自訂欄位
- **流量控制** — 暫停/繼續、即時調整速率
- **Journal 監控** — 依目標 Graylog journal 狀態自動限速 (API 或 SSH)
- 三種監控模式:無、Graylog API、SSH


### Web 管理介面

- **儀表板** — Grafana 風格的迷你圖表卡片、伺服器狀態、最近工作
- **歸檔清單** — 篩選、排序、批次操作、可拖曳選取的時間軸
- **作業歷程** — 即時進度(SSE)、耗時、取消、來源/模式標籤
- **排程作業** — Cron 編輯器、行內進度、立即執行
- **通知設定** — 6 種管道含語言選擇
- **系統記錄** — 即時記錄檢視器 + 稽核記錄
- 深色/淺色主題、English/繁體中文 雙語
- 可收摺側邊欄、HTTPS、Session 認證


### 通知

Telegram • Discord • Slack • Microsoft Teams • Nextcloud Talk • Email (SMTP)

觸發事件:匯出完成、匯入完成、清理完成、錯誤、驗證失敗。
雙語訊息(English / 繁體中文)。


### 排程作業 (APScheduler)

- **匯出** — Cron 排程,支援 API 或 OpenSearch 模式
- **清理** — 自動移除過期歸檔
- **驗證** — 定期 SHA256 完整性檢查
- 預設頻率(每小時、每日、每週、每月第一個週六、自訂 cron)
- 所有類型都支援「立即執行」


### 安全與效能

- **JVM 記憶體保護** — Graylog heap > 85% 時自動停止 API 匯出
- 同伺服器並行匯出鎖定
- 自適應速率限制(依 CPU 使用率)
- 執行緒安全 SQLite (WAL 模式)
- 錯誤時自動清理暫存檔案
- 磁碟空間監控



---



## 架構與運作原理


```
+------------------------------------------------------------------+
|                          jt-glogarch                             |
|                                                                  |
|   +-------------+         +-----------------------------+        |
|   |   Web UI    |<--------|  FastAPI + Jinja2 + JS SPA  |        |
|   |   (HTTPS)   |         +-----------------------------+        |
|   +-------------+                                                |
|                                                                  |
|   +-------------+   +------------------+   +------------+        |
|   |  REST API   |   |   APScheduler    |   |    CLI     |        |
|   +------+------+   +--------+---------+   +------+-----+        |
|          +-----------+-------+------------------+               |
|                      v                                          |
|   +----------------------------------------------------+        |
|   |       Export / Import / Cleanup / Verify           |        |
|   +-----+----------------+-----------------+-----------+        |
|         |                |                 |                   |
|         v                v                 v                   |
|   +----------+   +---------------+   +---------------+         |
|   |  SQLite  |   |   Streaming   |   |  GELF Sender  |         |
|   |    DB    |   |    Writer     |   |  (UDP / TCP)  |         |
|   +----------+   +-------+-------+   +-------+-------+         |
+--------------------------+-------------------+----------------+
                           v                   v
                  +----------------+   +----------------+
                  |    .json.gz    |   |    Graylog     |
                  | Archive Files  |   |   GELF Input   |
                  +----------------+   +----------------+
```


### 匯出流程 (Graylog API 模式)

1. 把要求的時間範圍切成每小時的區段
2. 對每個區段:
   - 已歸檔則跳過(同模式去重)
   - 已被 OpenSearch 歸檔覆蓋則跳過(跨模式去重)
   - 用 Graylog Universal Search 查詢(含串流篩選與時間範圍)
   - 串流寫入 gzip 檔案(不全量緩衝)
   - 計算 SHA256、寫入 `.sha256` 附檔
   - 寫入 SQLite DB
3. 定期檢查 Graylog JVM heap;>85% 自動停止
4. 發送結果通知


### 匯出流程 (OpenSearch Direct 模式)

1. 列出指定 prefix 的所有 OpenSearch indices
2. 跳過 active write index
3. 篩選「最近 N 份」index(或依時間範圍)
4. 對每個 index,**單次掃描**整個 index 並依 timestamp 排序
5. 隨掃描進度將文件依小時切分成歸檔檔案
6. 每個小時檔案完成立即記錄(支援斷點續傳)
7. 發送結果通知



---



## 使用情境


### 1. 法規遵循 — 長期記錄保留

資安要求保留 1 年的認證記錄,但 Graylog Open 為了效能只設了 90 天保留期。
排程每日匯出認證 stream,讓 jt-glogarch 把超過 90 天的歸檔到便宜儲存。

> 設定:排程 → 每日 03:00 → API 模式 → 串流篩選 `authentication-stream`


### 2. 鑑識調查 — 還原過去的記錄供調查

6 個月前發生的資安事件需要調查,但相關記錄已從 Graylog 滾掉。在歸檔清單頁面
找到相關歸檔,點「匯入」,指向目前的 Graylog 與 GELF UDP,即可重新注入。

> 流程:歸檔清單 → 篩選時間範圍 → 選擇歸檔 → 批次匯入 → GELF UDP


### 3. 遷移 — 從舊 Graylog 叢集搬到新叢集

從舊叢集用 OpenSearch Direct 大量快速匯出,然後透過 GELF 匯入到新叢集。

> 流程:OpenSearch Direct 模式 → 依 index 匯出 → 傳輸檔案 → 匯入新 GELF


### 4. 災難復原 — 異地備份

排程每日匯出到掛載的 NFS / S3 / 雲端儲存。即使 Graylog 掛了,你還有可搜尋的歸檔。

> 設定:把遠端儲存掛載到 `/data/graylog-archives` → 排程每日匯出


### 5. 降低成本 — 減少熱儲存

OpenSearch hot tier 很貴。把舊 indices 歸檔到壓縮儲存(約 10 倍壓縮率),
OpenSearch 只保留最近的資料供搜尋。

> 設定:OpenSearch 模式 → 匯出「保留最近 30 份 index」 → 清理保留 90 天



---



## 快速開始


### 系統需求

- Python 3.10+
- Graylog 6.x 或 7.x (Open 版)
- OpenSearch 2.x (選用,Direct 模式需要)
- Linux (已測試 Ubuntu 22.04 / Debian 12 / RHEL 9)


### 安裝(5 分鐘)

```bash
# 1. clone 專案
git clone https://github.com/jasoncheng7115/jt-glogarch.git /opt/jt-glogarch
cd /opt/jt-glogarch

# 2. 執行安裝腳本(建立使用者、目錄、SSL 憑證、systemd 服務)
sudo bash deploy/install.sh

# 3. 編輯設定檔填入 Graylog 資訊
sudo vi /opt/jt-glogarch/config.yaml

# 4. 啟動服務
sudo systemctl enable --now glogarch

# 5. 開啟 Web UI
echo "Open: https://$(hostname):8990"
```

使用 Graylog 帳號登入。



---



## 安裝詳細說明


### 手動安裝

如果你不想用 `install.sh`:

```bash
# 1. 安裝 Python 依賴
pip install --no-build-isolation --no-cache-dir /opt/jt-glogarch

# 2. 建立系統使用者
useradd -r -s /bin/false -d /opt/jt-glogarch jt-glogarch

# 3. 建立歸檔儲存目錄
mkdir -p /data/graylog-archives
chown -R jt-glogarch:jt-glogarch /data/graylog-archives

# 4. 產生自簽 SSL 憑證
mkdir -p /opt/jt-glogarch/certs
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout /opt/jt-glogarch/certs/server.key \
  -out /opt/jt-glogarch/certs/server.crt \
  -days 3650 -subj '/CN=jt-glogarch'

# 5. 複製設定範本
cp /opt/jt-glogarch/deploy/config.yaml.example /opt/jt-glogarch/config.yaml
chown jt-glogarch:jt-glogarch /opt/jt-glogarch/config.yaml

# 6. 安裝 systemd 服務
cp /opt/jt-glogarch/deploy/glogarch.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now glogarch
```


### 驗證安裝

```bash
# 服務狀態
systemctl status glogarch

# 即時日誌
journalctl -u glogarch -f

# 測試 Web UI (應回傳 HTTP 200)
curl -sk https://localhost:8990/login -o /dev/null -w '%{http_code}\n'
```



---



## 設定

設定檔在 `/opt/jt-glogarch/config.yaml`,**檔案擁有者必須是 `jt-glogarch`** 才能透過 Web UI 儲存。

完整參考請見 [`deploy/config.yaml.example`](deploy/config.yaml.example)。

```yaml
servers:
  - name: log4
    url: "http://192.168.1.132:9000"
    auth_token: "你的_GRAYLOG_API_TOKEN"
    verify_ssl: false

default_server: log4
export_mode: opensearch        # api 或 opensearch

export:
  base_path: /data/graylog-archives
  batch_size: 1000             # API 模式批次大小
  delay_between_requests_ms: 5
  chunk_duration_minutes: 60
  max_file_size_mb: 50
  jvm_memory_threshold_pct: 85.0

import:
  gelf_host: localhost
  gelf_port: 32202
  gelf_protocol: tcp           # tcp(預設,有 backpressure)或 udp

opensearch:
  hosts:
    - "http://192.168.1.132:9200"
  username: admin
  password: "你的_OS_密碼"

schedule:
  export_cron: "0 3 * * *"
  export_days: 180
  cleanup_cron: "0 4 1 * *"

retention:
  enabled: true
  retention_days: 60

notify:
  language: zh-TW              # en 或 zh-TW
  on_export_complete: true
  on_error: true
  telegram:
    enabled: true
    bot_token: "BOT_TOKEN"
    chat_id: "CHAT_ID"

web:
  host: 0.0.0.0
  port: 8990
  ssl_certfile: /opt/jt-glogarch/certs/server.crt
  ssl_keyfile: /opt/jt-glogarch/certs/server.key
```



---



## Web UI 使用說明

Web UI 是**主要操作介面**,CLI 用於自動化和腳本。

登入使用您的 Graylog 帳號密碼 — 沒有獨立的使用者資料庫,身份驗證委派給 Graylog REST API。

![登入](images/login_zhtw.png)


### 儀表板

![儀表板](images/dashboard_zhtw.png)

首頁顯示五個關鍵統計卡片(含 sparkline):

| 卡片 | 顯示內容 |
|---|---|
| **歸檔總數** | 已完成的歸檔檔案數量 |
| **記錄總數** | 已歸檔的記錄總筆數 |
| **歸檔前大小** | 壓縮前的總大小 |
| **壓縮後大小** | 磁碟上的總大小(gzip 後) |
| **可用磁碟空間** | 歸檔磁區的剩餘空間 |

每張卡片背後的 sparkline 顯示最近 30 天的每日活動。
滑鼠移到任一長條可看該日的精確數值。

下方區塊:
- **伺服器** — 已連接的 Graylog 伺服器與狀態
- **OpenSearch** — 連線測試狀態(右鍵點主機可設為 primary)
- **通知** — 已啟用的通知管道與「傳送測試通知」按鈕
- **最近工作** — 最近 5 個工作含進度、來源/模式標籤、耗時


### 歸檔清單

![歸檔清單](images/archives_zhtw.png)

這是管理所有歸檔的地方。

**頂部區域:**
- **歸檔路徑** — 目前儲存位置,有「設定」(變更路徑)和「重新掃描」(從磁碟同步)
- **歸檔時間軸** — 顯示所有歸檔的每日分布圖
  - 長條高度 = 該日記錄數
  - **拖曳**選取時間範圍(精確到小時) — 自動填入篩選並套用
  - **滑鼠移到**任一欄位可看日期、歸檔數、記錄數、檔案大小
  - 紅色標記 = 該日無歸檔(資料缺口)
  - 點**清除選取**重設

**篩選:** 伺服器、串流、起始、結束。點「篩選」套用。

**表格:**
- 可排序欄位(伺服器端排序,跨頁保持)
- **批次選取** — 用核取方塊,Shift+全選可跨頁批次
- **每列動作:** 匯入(單筆)、刪除

**批次動作**(勾選列後出現):
- **批次匯入** — 開啟匯入 modal 含 GELF 設定 + 流量控制
- **批次刪除** — 從磁碟移除檔案並標記為已刪除

**欄位設定** — 可開關欄位顯示(存在 localStorage)


### 作業歷程

![作業歷程](images/tasks_zhtw.png)
![作業歷程 — 執行中的任務細節](images/tasks2_zhtw.png)

顯示所有匯出、匯入、清理、驗證作業。

| 欄位 | 說明 |
|---|---|
| ID | Job UUID 前 8 碼 |
| 類型 | export / import / cleanup / verify 含標籤(手動/排程,API/OpenSearch) |
| 狀態 | running / completed / failed / cancelled |
| 進度 | 行內進度條 + 百分比;執行中顯示目前 chunk/index |
| 記錄數 | 已完成/總數(粗體+灰色總數) |
| 開始時間 | 工作開始時間 |
| 完成時間 | 工作結束時間 |
| 耗時 | 執行時間 |
| 錯誤 | 失敗時的錯誤訊息 |
| 動作 | 執行中工作的取消按鈕 |

完成時記錄數為 **0** 的工作會以淡色顯示「無新資料」 — 排程匯出在沒有新累積資料時是正常現象。


### 排程作業

![排程作業](images/schedules_zhtw.png)

管理自動化工作。支援三種類型:

#### 匯出排程

```
名稱:     auto-export
類型:     Export
頻率:     Daily 03:00
模式:     OpenSearch Direct
保留:     最近 60 份 Index   ← API 模式則為「天數」
```

OpenSearch 模式可選擇**保留最近 N 份 index**。下方的「可用 indices」時間軸顯示
目前存在的 index(及作為 active write index 的那一份,永遠排除)。

#### 清理排程

```
名稱:     auto-cleanup
類型:     Cleanup
頻率:     每月 1 號 04:00
保留天數:  60 天
```

刪除超過保留天數的歸檔檔案並更新 DB。

#### 驗證排程

```
名稱:     auto-verify
類型:     Verify
頻率:     每月第一個週六 03:00
```

重新驗證所有歸檔的 SHA256 校驗碼。校驗失敗的會在 DB 標記為**損壞**,在歸檔清單以紅色警告 icon 顯示。

**立即執行按鈕** — 所有排程類型都支援手動立即執行。
匯出工作的行內進度會直接顯示在排程列上。


### 通知設定

![通知設定](images/notification_zhtw.png)

設定通知要送到哪裡。

**通知語言** — 可選 English 或繁體中文。會套用到**所有**通知訊息(測試通知、匯出完成、錯誤等)。

**觸發事件** — 勾選哪些事件要發送通知:
- 匯出完成
- 匯入完成
- 清理完成
- 錯誤
- 驗證失敗

**通知管道** — 設定每個管道。**取消勾選「啟用」**會自動收摺該管道的設定欄位,讓頁面更整潔。

> **欄位敏感資料遮罩:** 所有敏感欄位（Bot Token、Chat ID、Webhook URL、
> Nextcloud token / 帳號 / 密碼、SMTP host / 帳號 / 密碼 等）預設以遮罩顯示
> 為密碼欄位。點擊欄位右側的眼睛按鈕可暫時顯示內容。瀏覽器自動填入功能也已
> 在這些欄位上停用,避免不小心被填入舊值。

| 管道 | 必填欄位 |
|---|---|
| Telegram | Bot Token、Chat ID |
| Discord | Webhook URL |
| Slack | Webhook URL |
| Microsoft Teams | Webhook URL |
| Nextcloud Talk | Server URL、Token、Username、Password |
| Email (SMTP) | Host、Port、TLS、User、Password、From、To |

點**傳送測試通知**驗證所有已啟用的管道。測試訊息會以設定的語言發送。


### 系統記錄

![系統記錄](images/syslog_zhtw.png)

即時 tail `journalctl -u glogarch` 加上稽核記錄(登入、匯出開始、設定儲存等)。



---



## 匯入(還原)流程

匯入流程圍繞「**合規流程**」設計,目標是 **零訊息遺失 + 零 indexer failures**。
所有保護措施都在送任何 GELF 訊息**之前**自動執行:

1. **Cluster health check** — 對方 OpenSearch 是 RED 直接拒絕匯入
2. **GELF input 驗證** — 必須存在於指定 port 且為 RUNNING 狀態
3. **Capacity check** — 用對方 rotation strategy 估算這次匯入會建立幾份
   index;如果**刪除型 retention 會把剛匯入的資料刪掉**直接 abort
4. **欄位 mapping 衝突自動修正** — 從 DB 讀每份歸檔記錄好的 `field_schema`,
   找出歸檔內部矛盾(同欄位有 numeric 和 string)或對方目前是 numeric 而歸檔
   有字串值的欄位,**透過 Graylog custom field mappings API 自動把這些欄位
   pin 為 `keyword`**
5. **OpenSearch 欄位上限突破** — 自動 PUT 一個 OpenSearch index template 把
   `index.mapping.total_fields.limit` 拉到 10000,徹底解決套用大量 custom
   mappings 時撞到 Graylog 預設 1000 欄位上限導致 index rotation 失敗的問題
6. **Index rotation** — cycle deflector 一次,讓新 mappings 在新的 active
   write index 上生效
7. **GELF send** — 用 TCP backpressure + Graylog journal 監控(對方
   uncommitted entries > 50 萬時自動暫停)
8. **匯入後對帳** — 撈 Graylog indexer failures 數字跟匯入前 baseline 比對,
   差異 > 0 就把 compliance violation 訊息寫進 job 的 `error_message`

### 必填:目標 Graylog API 帳密

從 v1.2.0 開始,匯入對話框**必填** Graylog API URL + Token(或帳號/密碼)。
同一組帳密同時用於 preflight、journal 監控、與對帳。**沒有「不監控」這個
選項了**。

### 兩種匯入模式(v1.3.0 起)

匯入對話框上方有**模式選擇器**:

| 模式 | 速度 | 經過 | 適用情境 |
|---|---|---|---|
| **GELF (Graylog Pipeline)**(預設) | ~5,000 筆/秒 | Graylog Input → Process buffer → Output buffer → OpenSearch | 你需要 Graylog 規則(pipeline、extractors、stream routing、alerts)在匯入資料上跑 |
| **OpenSearch Bulk** | ~30,000-100,000 筆/秒 | 直接 OpenSearch `_bulk` API | 還原已處理過的歷史資料,要最快速度 |

**Bulk 模式取捨:**
- ✅ **5-10 倍速度**(沒有 GELF framing、沒有 Graylog journal 寫盤、沒有 buffer 壓力)
- ✅ **每筆精確對帳**從 `_bulk` response(不依賴 Graylog 的 circular failure buffer)
- ✅ **不會誤觸 alert**(訊息不經過 stream routing)
- ❌ **跳過所有 Graylog 處理規則** — pipeline、extractors、stream routing、alerts。資料原樣從歸檔進到 OpenSearch。
- ❌ **需要 OpenSearch 帳密**(預設會自動偵測)。

**Bulk 匯入的資料寫到哪:**
- Bulk 模式寫進**專屬 index pattern**(預設 `jt_restored_*`),不是即時的
  `graylog_*` index。讓還原資料跟即時流量完全隔離。
- 每個 daily index 命名 `<pattern>_YYYY_MM_DD`,依訊息 timestamp 決定。
- Preflight 階段 jt-glogarch 會自動:
  1. 寫一個 OpenSearch index template `<pattern>_*`,設
     `total_fields.limit: 10000` 並把所有字串型欄位 pin 為 `keyword`
  2. 預先建立每個 daily index(Graylog 環境的 OpenSearch 通常設
     `action.auto_create_index = false`)
  3. **自動建立 Graylog Index Set** 對應這個 prefix,還原資料立刻可在
     Graylog UI 上搜尋。不需手動到「System / Indices」設定。

**去重機制:**
- v1.1+ 歸檔保留 `gl2_message_id`,bulk 模式拿來當 OpenSearch 文件 `_id`。
  重複匯入同一份歸檔會 overwrite 既有文件,不會產生重複。
- v1.0 歸檔沒有 `gl2_message_id` → bulk 模式自動產生 `_id`,重複匯入
  **會產生重複**(用 `--dedup-strategy fail` 來改成偵測到就中止)。



### 步驟 1 — 選擇歸檔

進入**歸檔清單**,可選擇性地依時間範圍或串流篩選,然後勾選歸檔。點**批次匯入**。


### 步驟 2 — 設定 GELF 目標

```
GELF Host:    192.168.1.132
Port:         32202   ← TCP 預設值;切換到 UDP 會自動變成 32201
Protocol:     TCP   ← 預設。可靠,有 backpressure
              UDP   ← 較快但 buffer 滿時會丟封包
目標名稱:      log-recovery
```

> Port 欄位會跟著 Protocol 自動切換(TCP → 32202、UDP → 32201)。如果你
> 手動改過 port,你的值會被保留。請確認目標 Graylog 有設定對應的 GELF
> Input 監聽這些 port。

> **⚠️ UDP vs TCP — 重要警告:**
> - **TCP(推薦,預設):** 有內建 backpressure。當目標 Graylog input buffer 滿
>   時,TCP 寫入會自然阻塞,jt-glogarch 會跟著降速,**不會掉訊息**。吞吐量
>   約 1,000~3,000 筆/秒。
> - **UDP(不建議用於大量匯入):** 較快(~5,000~10,000 筆/秒)但 buffer 滿時
>   會**靜默丟掉封包**,jt-glogarch 完全收不到任何錯誤回報 — `messages_done`
>   會說「我送了 X 筆」,但目標 Graylog 可能只收到一部分。症狀:匯入後的時間
>   軸會看到一段一段空白。**百萬筆等級的匯入若沒有流量控制,UDP 損失率常見
>   20-30%。**
>
> 如果一定要用 UDP,**務必**同時開啟 Journal 監控(Graylog API 或 SSH),
> 讓 jt-glogarch 偵測對面 buffer 壓力後自動降速。即使如此,UDP 在初始衝量
> 時還是無法完全避免丟封包。


### 步驟 3 — 設定初始速率

用**批次延遲(ms)** 滑桿設定批次之間的等待時間。
- 5-50ms = 積極(僅在有監控時使用)
- 100ms = 平衡預設值
- 500-1000ms = 保守


### 步驟 4 — 提供目標 Graylog API 帳密(必填)

從 v1.3.0 開始**必填**。同一組帳密用於 preflight、journal 監控、匯入後對帳。

```
Graylog API URL:  http://192.168.1.132:9000
API Token:        你的_TOKEN          ← 用 Token...
   — 或 —
帳號:            admin                ← ...或帳號 + 密碼
密碼:            ******
```

> 沒填這些對話框不會讓你按開始匯入。後端也會回 HTTP 400 拒絕。


### 步驟 5 — 開始與監控

點**開始匯入**後,modal 切換到控制面板:

- **暫停 / 繼續** — 暫停匯入而不丟失進度
- **速率滑桿** — 即時調整延遲,不需重啟
- **Journal 標籤** — 顯示目前 Graylog journal 狀態:
  - 🟢 normal — 全速
  - 🟡 slow — uncommitted entries 10萬-50萬,延遲加 3 倍
  - 🟠 paused — uncommitted entries 50萬-100萬,自動暫停 30 秒
  - 🔴 stop — uncommitted entries >100萬,中止匯入並通知管理員


### 自動限速規則

| Journal `uncommitted_entries` | 動作 |
|---|---|
| < 100,000 | 正常速度(你設定的延遲) |
| 100,000 — 500,000 | 慢速模式(延遲 × 3) |
| 500,000 — 1,000,000 | 暫停 30 秒 |
| > 1,000,000 | 停止匯入並發送通知 |



---



## 效能與調校


### Benchmark(預設設定)

| 模式 | batch_size | delay | 速度 | 1 小時(~175K 筆) |
|---|---|---|---|---|
| Graylog API | 1,000 | 5ms | ~730 筆/秒 | ~4 分鐘 |
| OpenSearch Direct | 10,000 | 2ms | ~3,300 筆/秒 | ~1 分鐘 |


### 何時用哪種模式

**用 Graylog API 模式當:**
- 需要串流層級的篩選
- OpenSearch 已鎖定(無直接存取權)
- 想要 JVM 記憶體保護(85% heap 自動停止)

**用 OpenSearch Direct 模式當:**
- 需要快速大量匯出歷史資料
- 有 OpenSearch 帳密
- 想要 index 層級的粒度


### 調校建議

**Graylog API 模式** — 如果你的 Graylog 叢集有充裕資源:
```yaml
export:
  batch_size: 2000              # 預設 1000
  delay_between_requests_ms: 0  # 預設 5ms
  jvm_memory_threshold_pct: 90.0
```
> ⚠️ 注意 JVM 記憶體保護 — 如果 Graylog OOM,降低這些值。

**OpenSearch Direct 模式** — 預設值已經很積極。如果 OpenSearch 機器很強,可以推到 batch_size 20000+。



---



## CLI 指令參考

CLI 提供給自動化和腳本使用。Web UI 才是日常操作的主要介面。

```bash
glogarch --help
```

| 指令 | 說明 |
|---|---|
| `glogarch server` | 啟動 Web UI + 排程器 (systemd 跑的就是這個) |
| `glogarch export` | 手動匯出 (`--mode api|opensearch --days 180`) |
| `glogarch import` | 匯入歸檔 (`--archive-id N --target-host HOST`) |
| `glogarch list` | 列出歸檔(支援篩選) |
| `glogarch verify` | 驗證所有歸檔的 SHA256 |
| `glogarch cleanup` | 移除過期歸檔 |
| `glogarch status` | 顯示系統狀態 |
| `glogarch schedule` | 管理排程作業 |
| `glogarch config` | 印出設定範本 |


### 範例:CLI 一次性匯出

```bash
sudo -u jt-glogarch glogarch export \
  --mode opensearch \
  --days 30
```


### 範例:從 CLI 還原歸檔

```bash
sudo -u jt-glogarch glogarch import \
  --archive-id 42 \
  --target-host 192.168.1.132 \
  --target-port 12201
```



---



## 疑難排解 / 常見問題


### 寫入 `/data/graylog-archives/` 出現「Permission denied」

服務以 `jt-glogarch` 使用者執行。確認歸檔目錄擁有者:
```bash
sudo chown -R jt-glogarch:jt-glogarch /data/graylog-archives
```


### Web UI 顯示「Not authenticated」但我剛登入

自簽憑證問題。瀏覽器可能拒絕了 cookie。試試:
1. 點 SSL 警告的「進階」→「繼續前往網站」
2. 用無痕視窗開
3. 或用 Let's Encrypt 換真憑證


### Pip install 顯示 `Successfully installed UNKNOWN-0.0.0`

舊的 `setuptools` 無法讀取 `pyproject.toml` metadata。修法:
```bash
pip install --upgrade setuptools wheel
rm -rf /opt/jt-glogarch/build /opt/jt-glogarch/*.egg-info
pip install --no-build-isolation --no-cache-dir --force-reinstall /opt/jt-glogarch
```


### 排程作業沒有在預期時間執行

`jt-glogarch` 使用 APScheduler,而 APScheduler **會繼承系統時區**。如果你的
系統時區是 UTC,但你寫的 cron 是 `0 3 * * *` 並期待「每天台灣時間凌晨 3 點」
執行,實際上會在 UTC 03:00 觸發(也就是台灣時間早上 11 點)。

**檢查系統時區:**
```bash
timedatectl
```

**設成本地時區:**
```bash
sudo timedatectl set-timezone Asia/Taipei
sudo systemctl restart glogarch
```

重啟後 scheduler 會自動讀到新時區。可用以下指令確認下次觸發時間:
```bash
python3 -c '
from apscheduler.triggers.cron import CronTrigger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
s = AsyncIOScheduler()
print("scheduler tz:", s.timezone)
t = CronTrigger.from_crontab("0 3 * * *", timezone=s.timezone)
print("next fire:", t.get_next_fire_time(None, datetime.now(s.timezone)))
'
```


### OpenSearch 模式排程匯出顯示「0 筆」

最有可能是 resume point 跳過了你的 indices。這已在 v1.0.0 修復 — OpenSearch 模式現在依靠 per-chunk dedup 而非 resume point 來避免缺口。確認你的版本 ≥ 1.0.0。


### 啟用 jt-glogarch 後 Graylog OOM

降低 `config.yaml` 裡的 `batch_size` 並提高 `delay_between_requests_ms`:
```yaml
export:
  batch_size: 300
  delay_between_requests_ms: 200
  jvm_memory_threshold_pct: 75.0
```


### 歸檔時間軸有紅色標記(缺口)

紅色標記表示該日無歸檔。這是資訊性的。手動執行匯出補上對應時間範圍即可。


### 匯入太慢/太快

匯入時用 modal 裡的**速率滑桿**,可即時調整批次延遲。
大量匯入時,啟用 journal 監控讓它自動限速。


### 驗證回報歸檔為「損壞」

可能是檔案被歸檔後被修改(罕見),或儲存有 bit-rot。損壞的歸檔仍可手動檢視,但無法通過完整性檢查。重新匯出受影響的時間範圍即可替換。


### 可以對同一個 Graylog 跑兩個 jt-glogarch 實例嗎?

可以,但要用不同的歸檔路徑。DB 是獨立的。


### 「stream」和「index」有什麼差別?

- **Stream** = Graylog 的邏輯篩選(例:「所有認證記錄」)
- **Index** = OpenSearch 的儲存單位(會定期 rotation)

API 模式在 stream 上操作。OpenSearch Direct 模式在 index 上操作。


### 可以用 Docker 跑嗎?

目前沒有官方支援,但專案是標準 Python 套件,沒有 OS 特定依賴 — Dockerfile 不難寫。



---



## 授權與作者

**授權:** [Apache License 2.0](LICENSE)

**作者:** Jason Cheng — [Jason Tools](https://jasontools.com)

**專案網址:** https://github.com/jasoncheng7115/jt-glogarch


### 第三方授權

- [Iconoir](https://iconoir.com) — MIT License (內嵌 SVG 圖示)
- [FastAPI](https://fastapi.tiangolo.com) — MIT License
- [APScheduler](https://apscheduler.readthedocs.io) — MIT License

詳見 [THIRD-PARTY-LICENSES.md](THIRD-PARTY-LICENSES.md)。
