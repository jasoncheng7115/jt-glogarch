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
    url: "http://192.168.1.10:9000"    # Graylog REST API URL
    auth_token: "your-api-token"        # API Token (recommended)
    # username: admin                   # Or username/password (pick one)
    # password: admin
    verify_ssl: false                   # HTTPS certificate verification

default_server: log4                    # Default server to use
```

> Get an API Token: Graylog → System → Users → Your Account → Edit Tokens → Create Token

### Multiple servers (multi-source archiving)

List every Graylog server under `servers:`. Each export job — manual or scheduled — targets **one** server (chosen in the Web UI export/schedule dialog, or via `glogarch export --server <name>`). To archive several servers automatically, create **one export schedule per server**.

Each server may carry its **own** OpenSearch cluster via a per-server `opensearch:` block (used by OpenSearch-mode export). When omitted, the global top-level `opensearch:` block is used as fallback:

```yaml
servers:
  - name: graylog-main
    url: "http://192.168.1.10:9000"
    auth_token: "TOKEN_A"
    verify_ssl: false
    opensearch:                         # cluster behind THIS server
      hosts:
        - "http://192.168.1.10:9200"
        - "http://192.168.1.11:9200"   # failover NODES of the SAME cluster
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
  query: "*"                            # Search query (default: all)
  streams: []                           # Limit to specific streams (empty = all)
  index_sets: []                        # OpenSearch mode: restrict to these index set IDs.
                                        # EMPTY = archive ALL index sets (safe default —
                                        # a restricted list logs which index sets it skips).
  fields: []                            # Limit to specific fields (empty = all)

  # --- Adaptive backpressure guard (see below) ---
  jvm_memory_threshold_pct: 75.0        # heap SOFT tier: pause when SUSTAINED above this %
  jvm_memory_hard_pct: 90.0             # heap HARD tier: pause immediately at/above this %
  health_heap_sustained_samples: 2      # consecutive soft-over reads before pausing
  health_heap_signal: auto              # auto = judge heap from Graylog's GC metrics when it exposes them
                                        # (see "Heap pressure on Graylog 7" below); used = raw used % always
  health_gc_overhead_pct: 10.0          # GC metrics: pause when GC time is >= this % of wall time (sustained)
  health_pace_start_pct: 70.0           # API export: start slowing down at this % of heap after GC
  health_pace_max_delay_sec: 5.0        # API export: wait this long per page at jvm_memory_hard_pct
  health_search_cache_flush_sec: 310    # heap-bound pause longer than this: send 1-message searches each
                                        # minute so Graylog drops expired search results (0 = off)
  health_guard_enabled: true            # Master switch for the guard
  health_sample_interval_sec: 15        # FIXED wall-clock sampling cadence (not per-chunk!)
  health_rise_samples: 3                # Consecutive climbs before a signal is "rising"
  health_journal_min_delta: 200         # Min journal-entry growth/sample to count as rising
  health_buffer_min_delta: 64           # Min ring-buffer growth/sample to count as rising
  health_pause_interval_sec: 15         # How often to re-check while paused
  health_max_pause_min: 30              # Stop the export if still high after this many minutes
  health_stop_retry_min: 60             # A scheduled run stopped that way tries once more after this (0 = next run)
  health_resume_drain_ratio: 0.7        # Resume once a signal falls to <= peak * this
  connection_failure_limit: 10          # Abort after this many consecutive connection failures
```

### Adaptive backpressure guard

A heavy export loads the **same** OpenSearch cluster Graylog indexes into. On a
busy or HDD-backed cluster this can starve ingestion — the disk journal and ring
buffers back up and Graylog stops collecting logs (worst case: it wedges until
restarted). The guard samples Graylog's own health between chunks/batches and
**pauses the export the moment ingestion falls behind, resuming once it drains**.

**Applies to BOTH `export_mode: api` and `export_mode: opensearch`** — one guard,
one set of thresholds (below). OpenSearch-direct still loads the cluster, so it
watches the same Graylog signals.

**Sampling is fixed wall-clock time** (`health_sample_interval_sec`, 15 s),
*not* per chunk. The guard is checked on every batch in both modes but only
actually reads Graylog every 15 s — so a long chunk is monitored throughout, and
the trend thresholds below have meaningful reaction times (a chunk-only cadence
could leave minutes between reads and make them useless).

Signals and what makes each PAUSE the export:

| Signal | Pauses when | Threshold (default) |
|---|---|---|
| JVM heap from GC metrics (default when Graylog exposes them) | heap still `>=` the hard tier right after a collection; any full GC since the last reading; GC time `>=` N % of wall time, sustained | `jvm_memory_hard_pct: 90`, `health_gc_overhead_pct: 10` + `health_heap_sustained_samples: 2` |
| JVM heap % (hard) — no GC metrics, or `health_heap_signal: used` | a single reading is `>=` the hard tier | `jvm_memory_hard_pct: 90` |
| JVM heap % (soft) — same | **sustained** `>=` the soft tier for N reads | `jvm_memory_threshold_pct: 75` + `health_heap_sustained_samples: 2` |
| disk journal (uncommitted entries) | it keeps **rising** | `health_rise_samples: 3` + `health_journal_min_delta: 200` |
| input / process / output buffers | any keeps **rising** | `health_rise_samples: 3` + `health_buffer_min_delta: 64` |
| Graylog unreachable | immediately (**fail-safe**) | — |

- **Two-tier heap** (raw used %, when GC metrics are unavailable): the soft tier (75 %) backs off well before the ceiling, but
  only when heap stays high for `health_heap_sustained_samples` reads so a single
  GC-sawtooth peak doesn't cause a needless pause; the hard tier (90 %) pauses on
  one reading to catch an acute spike. Reaction: soft ≈ 2×15 s = 30 s, hard ≤ 15 s.
- **"Rising"** means `health_rise_samples + 1` = **4 consecutive samples** (~60 s
  at the 15 s cadence), each growing by at least the min-delta (journal ≥ 200
  entries each → ≥ 600 net; buffers ≥ 64 each). This filters normal jitter and
  only trips on a genuine backlog.
- **While paused** it re-reads every `health_pause_interval_sec` (15 s).
- **Resume** requires heap `<` threshold, nothing still rising, AND every
  journal/buffer signal fallen to `<=` its pause-time peak × `health_resume_drain_ratio`
  (0.7 → dropped ≥ 30 % from the peak). i.e. it must actually come back down, not
  just stop climbing.
- **Give up:** if load stays high for `health_max_pause_min` (30 min) the run
  ends there — once, not chunk by chunk or index by index. Every hour already
  archived stays archived and the open hour is discarded, so the next run
  continues from it. A scheduled run then tries **once** more after
  `health_stop_retry_min` (60 min) — retrying a minute later only meets the same
  load — and otherwise leaves the rest to its next scheduled run. One
  notification either way; the job row says how many records were archived
  before the stop.
- **Circuit breaker:** `connection_failure_limit` (10) consecutive connection
  failures aborts the run instead of hammering a dead server.
- **Fail-safe:** if Graylog can't be read — exactly when it may be in trouble —
  that counts as pressure and the export pauses (it does NOT treat "unreadable"
  as healthy).

Every pause is written to the system log and shown on the running job with the
exact signal(s) that triggered it.

#### Heap pressure on Graylog 7: GC metrics, pacing and cached search results

- **GC metrics, not used/max.** With `health_heap_signal: auto` (default) the heap is judged from
  Graylog's own garbage-collector metrics (the `jvm.*` set; G1, Parallel and Serial names are
  recognised). Used/max counts garbage the next young collection frees: a healthy 3 GB Graylog
  swings between 75 % and 95 % with no export running, so that check paused a nightly API export
  for over half its run. Without GC metrics the used % two-tier check above applies.
- **Why an API export fills Graylog's heap.** Graylog 7 keeps every search's complete result in
  memory for 5 minutes after it was last read (at most 1,000 searches). The heap an API export
  holds is roughly its own rate over the last 5 minutes — measured ≈ 10 KB of Graylog heap per
  exported message on a site with ≈ 2.4 KB messages, i.e. a 3 GB Graylog reached 90 % after GC at
  ≈ 760 messages/s.
- **Pacing (API export only).** Above `health_pace_start_pct` of heap after GC the export waits
  between pages, rising linearly to `health_pace_max_delay_sec` at `jvm_memory_hard_pct`, so it
  settles at the rate that Graylog can hold instead of running into full GCs. The log shows
  `export pacing adjusted` whenever the delay changes. OpenSearch-direct does not search Graylog
  and is never paced.
- **A pause cannot release that heap on its own.** Graylog drops expired results only while it
  serves another search. Once an export pauses nothing searches, so the heap it left behind stays:
  on a real site it sat at 90–91 % after GC through whole 30-minute pauses (the collector ran
  dozens of cycles and found it all in use), then fell to 74 % within five minutes of four small
  searches. So a heap-bound pause that lasts longer than `health_search_cache_flush_sec` (310 s,
  just past the 5-minute expiry) sends a few 1-message searches each minute and logs
  `asked Graylog to release expired search results`. Journal/buffer pauses never send them.
- **The API-mode ceiling is Graylog's per-search cost.** Every Graylog 7 search also reads the
  field types of every index it covers, whatever the page size: ≈ 550 ms per request on a site
  with 119 indices / 150,000 fields vs ≈ 40 ms on a small one. At 1,000 messages per page that
  caps API mode near 890 messages/s. Fewer retained indices or fewer distinct fields make every
  Graylog search faster, not just the export.

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
  hosts:                                # Failover NODES of ONE cluster
    - "http://192.168.1.10:9200"       # (NOT separate clusters)
    - "http://192.168.1.11:9200"
  username: admin
  password: "your-password"
  verify_ssl: false
```

> Skip this section entirely if not using OpenSearch direct mode.

**Global vs per-server.** This top-level `opensearch:` block is the **global fallback**. A server with its own `servers[].opensearch:` block uses that instead. The `hosts` list is always the **failover nodes of a single cluster** — to archive *different* OpenSearch clusters, give each cluster its own server entry with a per-server `opensearch:` block (see [Multiple servers](#multiple-servers-multi-source-archiving)).

| You want to archive… | How |
|---|---|
| One cluster, multiple nodes | `hosts: [node1, node2, …]` (failover) |
| Multiple separate clusters | One `servers[]` entry per cluster, each with its own `opensearch:` block |

> CLI: `glogarch test-opensearch --server <name>` tests the cluster resolved for that server.

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
  retention_days: 1095                   # Delete archives older than this (default: 3 years)
```

---

## integrity — Archive Tamper-Evidence (optional, default OFF)

Adds a **keyed HMAC-SHA256** on top of the plain SHA256 so that editing an
archive file *and* its DB checksum can no longer forge a valid integrity value
— only someone with the secret key can. Off by default; enable per deployment.

```yaml
integrity:
  enabled: false                          # opt-in; when true, new archives are HMAC-sealed
  hmac_key_file: /opt/jt-glogarch/.hmac_key   # 0600; used unless JT_HMAC_KEY env is set
  ledger_enabled: true                    # record each seal in the integrity_ledger table
```

Setup:

```bash
glogarch integrity-init            # generate the key file (back it up off-box!)
# set integrity.enabled: true in config.yaml, then:
glogarch integrity-seal            # seal existing archives (attests from now on)
glogarch verify                    # reports TAMPERED (HMAC mismatch) vs CORRUPTED (SHA256)
glogarch integrity-manifest -o /safe/off-box/manifest.json   # keep a copy off the archive host
```

- **Key precedence:** env `JT_HMAC_KEY` (base64/hex) > `hmac_key_file`.
- **Root-proof mode:** don't store the key file — supply `JT_HMAC_KEY` only at
  seal/verify time and keep the manifest off-box. Then even a root/service
  attacker who rewrites the files + DB is caught against the external copy.
- **Honest limit:** sealing an already-tampered archive only attests it from
  that point on; it cannot prove the past. Losing the key means HMAC checks fall
  back to SHA256 only.

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

  zulip:
    enabled: false
    server_url: ""       # e.g. https://chat.example.com
    bot_email: ""        # the bot's email (Zulip: Personal settings > Bots)
    api_key: ""          # the bot's API key (masked in the Web UI)
    stream: ""           # stream (channel) the bot is subscribed to
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

> All notification channels can be configured from the Web UI "Notification Settings" page.

---

## op_audit — Operation Audit (Graylog Operation Tracking)

```yaml
op_audit:
  enabled: true                           # Enable operation audit (receives nginx syslog)
  listen_port: 8991                       # UDP syslog listen port
  max_body_size: 65536                    # Max request body stored per entry (bytes)
  alert_sensitive: true                   # Notify on sensitive operations (DELETE user/stream/input etc.)
```

> Audit records are cleaned automatically when the scheduled cleanup runs, using the same `retention.retention_days` as archive files. No separate retention setting needed.


### How it works

Each Graylog server's nginx reverse proxy sends access logs via syslog UDP to jt-glogarch.
jt-glogarch parses the logs, decodes the Graylog username from the Authorization header,
classifies operations, and stores them in SQLite. Sensitive operations (user/stream/input
deletion, login/logout, etc.) trigger notifications.

The IP allowlist is **auto-built** from `servers[].url` + Graylog Cluster API
(`GET /api/system/cluster/nodes`), refreshed every 5 minutes. No manual IP configuration needed.

Token-based authentication is automatically resolved to the actual Graylog username
via the Users API cache (refreshed every 10 minutes).

### Setup

1. Open UDP port on jt-glogarch server firewall: `sudo ufw allow 8991/udp`
2. Add `log_format` to `/etc/nginx/nginx.conf` `http {}` block (once per server)
3. Add `access_log` + `client_body_buffer_size` to Graylog site config `server {}` block
4. `sudo nginx -t && sudo systemctl reload nginx`

See the Web UI "Operation Audit" page → "nginx Prerequisites" for the ready-to-copy config snippet.

---

## web — Web UI

```yaml
web:
  host: 0.0.0.0                         # Listen address
  port: 8990                            # Listen port
  ssl_certfile: /opt/jt-glogarch/certs/server.crt
  ssl_keyfile: /opt/jt-glogarch/certs/server.key
  localadmin_password_hash: ""          # Emergency login (SHA256 hash)
  allowed_graylog_roles: [Admin]        # Graylog roles that may sign in (since 1.18.2)
```

### Who can sign in

A Graylog account signs in only if it holds a role listed in `allowed_graylog_roles`
(case-insensitive, default `Admin`) or the `*` permission, which Graylog's built-in
`admin` has. jt-glogarch reads the roles from Graylog at every sign-in, for password
and API-token logins alike; if it cannot read them, the sign-in is refused.

- Add a role to let its members in, for example `allowed_graylog_roles: [Admin, Archive Operators]`.
- `["*"]` admits every Graylog account and gives each of them every function here.
  Not recommended.
- Upgrading to 1.18.2 signs everybody out once. An account without an allowed role
  then sees "This Graylog account may not use jt-glogarch"; sign in with a Graylog
  administrator or `localadmin`, or add the role.

### Emergency Local Admin

When Graylog is offline, the Web UI is inaccessible because login is delegated to the Graylog API. Set a local emergency password to enable fallback login:

```bash
# Generate the hash
glogarch hash-password
# Enter password twice, then paste the hash into config.yaml
```

**Login credentials:** Username: `localadmin`, Password: the emergency password you set.

`localadmin` works whether or not Graylog is reachable (since 1.12.10), and the role check above does not apply to it. When Graylog is unreachable the login page shows an orange warning pointing to it.

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
