# jt-glogarch Configuration Reference

**Language**: **English** | [繁體中文](CONFIG-zh_TW.md)

The config file lives at `/opt/jt-glogarch/config.yaml` and must be owned by `jt-glogarch`.

Most settings can be configured from the Web UI ("Schedules" and "Notification Settings" pages).
The reference below is for manual editing and automated deployments.

---

## servers — Graylog Connection

```yaml
servers:
  - name: log4                          # Custom name (used for archive directory)
    url: "http://192.168.1.132:9000"    # Graylog REST API URL
    auth_token: "your-api-token"        # API Token (recommended)
    # username: admin                   # Or username/password (pick one)
    # password: admin
    verify_ssl: false                   # HTTPS certificate verification

default_server: log4                    # Default server to use
```

> Get an API Token: Graylog → System → Users → Your Account → Edit Tokens → Create Token

---

## export — Export Settings

```yaml
export_mode: opensearch                 # api or opensearch

export:
  base_path: /data/graylog-archives     # Archive storage path
  batch_size: 1000                      # API mode: messages per request
  chunk_duration_minutes: 60            # Time span per archive file (minutes)
  max_file_size_mb: 50                  # Auto-split if file exceeds this
  min_disk_space_mb: 500                # Stop export if disk below this
  delay_between_requests_ms: 5          # Delay between API requests (ms)
  jvm_memory_threshold_pct: 85.0        # Stop if Graylog JVM heap exceeds this %
  query: "*"                            # Search query (default: all)
  streams: []                           # Limit to specific streams (empty = all)
  fields: []                            # Limit to specific fields (empty = all)
```

---

## import — Import Settings

```yaml
import:
  gelf_host: localhost                  # GELF target host
  gelf_port: 32202                      # GELF port
  gelf_protocol: tcp                    # tcp (default, has backpressure) or udp
  batch_size: 500                       # Messages per batch
  delay_between_batches_ms: 100         # Delay between batches (ms)
```

> GELF host, port, and rate can be overridden in the Web UI import dialog.

---

## opensearch — OpenSearch Direct

```yaml
opensearch:
  hosts:                                # Multiple hosts for failover
    - "http://192.168.1.132:9200"
    - "http://192.168.1.127:9200"
  username: admin
  password: "your-password"
  verify_ssl: false
```

> Skip this section entirely if not using OpenSearch direct mode.

---

## schedule — Scheduling

```yaml
schedule:
  export_cron: "0 3 * * *"             # Export schedule (cron format)
  export_days: 180                      # Export the last N days each run
  cleanup_cron: "0 4 * * *"            # Cleanup schedule
```

> Schedules can be managed from the Web UI "Schedules" page.
> These are initial defaults; Web UI saves will overwrite them.

---

## retention — Retention Policy

```yaml
retention:
  enabled: true
  retention_days: 180                   # Delete archives older than this
```

---

## rate_limit — Rate Limiting

```yaml
rate_limit:
  requests_per_second: 2.0             # API mode requests per second
  adaptive: true                        # Auto-adjust based on CPU usage
  max_cpu_percent: 80                   # Slow down above this CPU %
  backoff_seconds: 10                   # Wait time after slowdown
```

---

## notify — Notifications

```yaml
notify:
  language: zh-TW                       # en or zh-TW
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

> All notification channels can be configured from the Web UI "Notification Settings" page.

---

## web — Web UI

```yaml
web:
  host: 0.0.0.0                         # Listen address
  port: 8990                            # Listen port
  ssl_certfile: /opt/jt-glogarch/certs/server.crt
  ssl_keyfile: /opt/jt-glogarch/certs/server.key
  localadmin_password_hash: ""          # Emergency login (SHA256 hash)
```

### Emergency Local Admin

When Graylog is offline, the Web UI is inaccessible because login is delegated to the Graylog API. Set a local emergency password to enable fallback login:

```bash
# Generate the hash
glogarch hash-password
# Enter password twice, then paste the hash into config.yaml
```

**Login credentials:** Username: `localadmin`, Password: the emergency password you set.

The login page will show an orange warning when Graylog is unreachable, instructing users to use the `localadmin` account. This only activates when Graylog is unreachable (connection error). It does NOT activate when Graylog rejects credentials (wrong password).

---

## Other

```yaml
database_path: /opt/jt-glogarch/jt-glogarch.db   # SQLite DB path
log_level: INFO                                    # DEBUG / INFO / WARNING / ERROR
```

---

## Config Search Order

1. CLI `--config` parameter
2. `./config.yaml` (current directory)
3. `~/.jt-glogarch/config.yaml`
4. `/etc/jt-glogarch/config.yaml`

First file found is used.

## Important Notes

- Saving settings from the Web UI **overwrites the entire config.yaml**. Manual edits made between page load and save will be lost.
- File owner must be `jt-glogarch` for Web UI to save: `chown jt-glogarch:jt-glogarch /opt/jt-glogarch/config.yaml`
