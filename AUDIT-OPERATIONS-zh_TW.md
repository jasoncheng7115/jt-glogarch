# jt-glogarch 行為稽核 — 追蹤的操作清單

**語言**: [English](AUDIT-OPERATIONS.md) | **繁體中文**

jt-glogarch 的行為稽核透過 nginx 反向代理的 syslog 記錄 Graylog API 操作。
僅記錄有意義的使用者操作，背景輪詢、狀態檢查、靜態資源等自動篩除。

---

## 敏感操作（⚠）

啟用 `op_audit.alert_sensitive` 時，以下操作會觸發通知。

| 分類 | 操作代號 | 說明 |
|------|----------|------|
| **認證** | `auth.login` | 使用者登入 |
| | `auth.logout` | 使用者登出 |
| **使用者管理** | `user.create` | 建立使用者帳號 |
| | `user.modify` | 修改使用者（密碼、權限、狀態） |
| | `user.delete` | 刪除使用者帳號 |
| **Input 管理** | `input.create` | 建立 Input |
| | `input.modify` | 修改 Input 設定 |
| | `input.delete` | 刪除 Input |
| | `input.start` | 啟動 / 重新啟動 Input |
| | `input.stop` | 停止 Input |
| **Stream 管理** | `stream.create` | 建立 Stream |
| | `stream.delete` | 刪除 Stream |
| | `stream.pause` | 暫停 Stream |
| | `stream.resume` | 恢復 Stream |
| | `stream.bulk` | 批次刪除 / 暫停 / 恢復 Stream |
| **Index Set** | `indexset.create` | 建立 Index Set |
| | `indexset.modify` | 修改 Index Set 設定 |
| | `indexset.delete` | 刪除 Index Set |
| **Index 操作** | `index.delete` | 刪除 Index |
| | `index.close` | 關閉 Index |
| | `index.reopen` | 重新開啟 Index |
| | `deflector.cycle` | 強制 Index 輪替（Cycle Deflector） |
| **Pipeline** | `pipeline.create` | 建立 Pipeline |
| | `pipeline.modify` | 修改 Pipeline |
| | `pipeline.delete` | 刪除 Pipeline |
| | `pipeline_rule.create` | 建立 Pipeline 規則 |
| | `pipeline_rule.modify` | 修改 Pipeline 規則 |
| | `pipeline_rule.delete` | 刪除 Pipeline 規則 |
| | `pipeline.connect` | 連結 Stream 至 Pipeline |
| **事件 / 告警** | `event.create` | 建立事件定義 |
| | `event.modify` | 修改事件定義 |
| | `event.delete` | 刪除事件定義 |
| | `event_notif.create` | 建立事件通知 |
| | `event_notif.modify` | 修改事件通知 |
| | `event_notif.delete` | 刪除事件通知 |
| **Dashboard / View** | `view.create` | 建立 Dashboard 或已儲存搜尋 |
| | `view.modify` | 修改 Dashboard（Widget、版面） |
| | `view.delete` | 刪除 Dashboard 或已儲存搜尋 |
| **系統** | `cluster_config.modify` | 修改叢集設定 |
| | `cluster_config.delete` | 刪除叢集設定 |
| | `field_mapping.modify` | 變更欄位型別對應 |
| | `processing.pause` | 暫停訊息處理 |
| | `processing.resume` | 恢復訊息處理 |
| | `processing.config` | 變更訊息處理器設定 |
| | `system.shutdown` | 關閉 Graylog 節點 |
| **認證服務** | `auth_service.create` | 建立認證服務（LDAP、SSO 等） |
| | `auth_service.modify` | 修改認證服務 |
| | `auth_service.delete` | 刪除認證服務 |
| | `auth_service.activate` | 啟用認證服務 |
| | `auth_service.deactivate` | 停用認證服務 |

---

## 一般操作

這些操作會被記錄，但不會觸發通知。

| 分類 | 操作代號 | 說明 |
|------|----------|------|
| **搜尋** | `search.create` | 建立新搜尋定義（包含查詢語句） |
| | `search.update` | 更新既有搜尋定義（包含查詢語句） |
| | `search.execute` | 執行搜尋查詢（僅限 sync 或 universal API） |
| | `search.export` | 匯出搜尋結果（CSV 下載） |
| **Dashboard / View** | `view.open` | 開啟 Dashboard 或已儲存搜尋 |
| **Stream** | `stream.modify` | 修改 Stream 設定 |
| | `stream.clone` | 複製 Stream |
| | `stream_rule.create` | 建立 Stream 規則 |
| | `stream_rule.modify` | 修改 Stream 規則 |
| | `stream_rule.delete` | 刪除 Stream 規則 |
| **角色** | `role.create` | 建立角色 |
| | `role.modify` | 修改角色 |
| | `role.delete` | 刪除角色 |
| **分享** | `share.modify` | 變更物件分享權限 |
| **Extractor** | `extractor.create` | 建立 Extractor |
| | `extractor.modify` | 修改 Extractor |
| | `extractor.delete` | 刪除 Extractor |
| **Lookup Table** | `lookup_table.create` | 建立查詢表 |
| | `lookup_table.modify` | 修改查詢表 |
| | `lookup_table.delete` | 刪除查詢表 |
| **Lookup Adapter** | `lookup_adapter.create` | 建立資料轉接器 |
| | `lookup_adapter.modify` | 修改資料轉接器 |
| | `lookup_adapter.delete` | 刪除資料轉接器 |
| **Lookup Cache** | `lookup_cache.create` | 建立快取 |
| | `lookup_cache.modify` | 修改快取 |
| | `lookup_cache.delete` | 刪除快取 |
| **Content Pack** | `content_pack.install` | 安裝 Content Pack |
| | `content_pack.delete` | 刪除 Content Pack |
| **Grok Pattern** | `grok.create` | 建立 Grok Pattern |
| | `grok.modify` | 修改 Grok Pattern |
| | `grok.delete` | 刪除 Grok Pattern |
| **Output** | `output.create` | 建立 Output |
| | `output.modify` | 修改 Output |
| | `output.delete` | 刪除 Output |
| **Sidecar** | `sidecar.create` | 建立 Sidecar Collector 或設定 |
| | `sidecar.modify` | 修改 Sidecar Collector 或設定 |
| | `sidecar.delete` | 刪除 Sidecar Collector 或設定 |

> **搜尋操作說明：** 使用者在 Graylog UI 搜尋時，會產生兩個 API 呼叫：（1）建立/更新搜尋定義（包含實際查詢語句），然後（2）執行搜尋（僅含 `global_override`）。僅記錄 `search.create`/`search.update`，後續的 execute 呼叫自動篩除以避免重複。`search.execute` 僅在直接 API 搜尋（sync 或 universal 端點）時記錄。

---

## 不記錄（自動篩除）

以下請求**不會被記錄**，以避免大量無意義的資料：

- 背景輪詢（metrics、叢集健康、throughput、journal 狀態）
- Session 心跳與驗證
- 系統狀態與通知輪詢
- 靜態資源（CSS、JS、圖片）
- 唯讀的列表/查詢操作（`view.open` 和 `search.execute` 除外）
- 欄位型別查詢、codec/input type 查詢
- Graylog 內部 API 呼叫（migration、telemetry、startpage）

---

## 帳號解析方式

| 認證方式 | 帳號解析方法 |
|----------|-------------|
| **Basic Auth**（帳號:密碼） | 從 `Authorization` header 取得 |
| **Token Auth**（token:token） | 透過 Graylog Users API 解析（逐使用者 token 端點） |
| **Session Auth**（Authorization header） | Session ID 透過 Graylog Sessions API 解析 |
| **Session Cookie**（瀏覽器，`$cookie_authentication`） | 從 cookie 擷取 Session ID，透過 API 解析 |
| **無認證 header 且無 cookie** | 以來源 IP 比對先前的登入記錄 |

> 當 Graylog 只有一個人類帳號時，所有操作自動歸屬給該使用者。
>
> **重要：** nginx 的 `log_format` 必須包含 `"http_cookie":"$cookie_authentication"` 以擷取 Graylog session cookie。缺少此欄位時，來自相同 IP 的多個使用者將無法正確區分。
