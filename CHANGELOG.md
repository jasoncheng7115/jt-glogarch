# Changelog

All notable changes to jt-glogarch will be documented in this file.

## [1.5.5] - 2026-04-13

### Fixed — Test notification broken for Discord/Slack/Teams/Email

The `/notify/test` endpoint called `_send_discord(client, cfg, full_msg)`
with 3 arguments, but the function signature requires 5:
`(client, cfg, title, message, ts)`. Same mismatch for Slack, Teams,
and Email. The call crashed silently, and the frontend showed
"No channels enabled" instead of the actual error.

- Fixed all 4 function calls to pass correct arguments
- Added `test_notify_test_endpoint.py` (7 tests) verifying every
  send function's parameter count and every call site's argument list

## [1.5.4] - 2026-04-13

### Fixed — Graylog API 401 causes infinite "Loading..." in dropdowns

`/api/index-sets` and `/api/streams` did not catch `HTTPStatusError`.
When Graylog returned 401 (bad token), the frontend dropdown stayed on
"Loading..." forever instead of showing an error.

- Backend now catches 401 → returns `{"error": "...authentication failed...", "items": []}` with HTTP 401
- Backend catches connection errors → returns `{"error": "Cannot reach Graylog: ...", "items": []}` with HTTP 502
- Frontend reads `data.error` and displays the message in the dropdown instead of spinning

### Added — One-command upgrade script (`deploy/upgrade.sh`)

```bash
cd /opt/jt-glogarch && sudo bash deploy/upgrade.sh
```

Automates: DB backup → git pull → pip install → restart → verify health.
Displays before/after version. Exits non-zero if health check fails.
README upgrade sections updated to reference the script.

### Fixed — install.sh systemd default was No

`[y/N]` → `[Y/n]`. Pressing Enter now installs the systemd service
(was skipping it, breaking the "5-minute install" promise).

### Fixed — `git clone /opt/` needs sudo

README install instructions now include `sudo git clone`.

### Fixed — Author email and URL

- Email: `jason@jasontools.com` → `jason@jason.tools`
- Jason Tools URL: `https://jasontools.com` → `https://github.com/jasoncheng7115`

### Added — Tests for API error handling + upgrade process

- `test_api_error_handling.py` (4 tests): 401/502/unreachable for index-sets and streams
- `test_upgrade_script.py` (7 tests): script exists, 5 steps, root check, systemd default, README refs

## [1.5.3] - 2026-04-13

### Fixed — Customer install fails: pyproject.toml not found

`git clone` + `pip install /opt/jt-glogarch` failed because the GitHub
repo had `pyproject.toml` and `glogarch/` inside a `src/` subdirectory.
`pip` requires them at the repository root.

- Moved `github/src/glogarch/` → `github/glogarch/`
- Moved `github/src/pyproject.toml` → `github/pyproject.toml`
- Removed `github/src/` directory entirely
- Updated `check-version.sh` and `CLAUDE.md` references
- Added `test_repo_structure.py` (7 tests) to prevent regression

### Added — Upgrade instructions in README

Both READMEs now include a step-by-step upgrade procedure:
`db-backup` → `git pull` → `pip install --force-reinstall` →
`systemctl restart` → verify `/api/health`.

### Added — Upgrade simulation tests (`test_upgrade.py`)

4 tests verifying: old DB auto-migration, old config backward
compatibility, existing archives survive upgrade, DB backup validity.

## [1.5.2] - 2026-04-12

### Added — Emergency local admin login

When Graylog is offline, the Web UI was completely inaccessible because
authentication is delegated to the Graylog REST API. This is a critical
gap for disaster recovery scenarios.

- **`web.localadmin_password_hash`** config option — stores a SHA256
  hash of the emergency password. When Graylog API is unreachable AND
  this hash is configured, the login page accepts the local password
  as fallback. Username must be `localadmin`.
- **Login page feedback** — three distinct error states:
  - Graylog rejects credentials → "Login failed"
  - Graylog offline + hash configured → orange warning with
    instructions to use `localadmin` account
  - Graylog offline + no hash → red error with config hint
- **`glogarch hash-password`** CLI command — interactive prompt to
  generate the SHA256 hash for `config.yaml`.
- **Backward compatible** — the field defaults to empty string
  (disabled). Existing installations without it configured behave
  exactly as before.
- Login logic: Graylog API is always tried first. Local fallback only
  activates when Graylog is unreachable (connection error/timeout),
  NOT when Graylog rejects the credentials (wrong password).

## [1.5.1] - 2026-04-12

### Fixed — Archive directory ownership auto-repair

Running `glogarch export` as root (without `sudo -u jt-glogarch`)
created archive subdirectories owned by root. Subsequent scheduled
exports by the `jt-glogarch` service user then failed with
`PermissionError: Cannot create archive file`.

- **`ArchiveStorage._fix_dir_ownership()`** — when `mkdir` fails with
  PermissionError and the process is running as root, automatically
  chown non-`jt-glogarch`-owned directories under `base_path` to
  `jt-glogarch`. Scoped to archive directories only — never touches
  system directories above `base_path`.
- **CLI root warning** — running any `glogarch` command as root now
  prints a warning recommending `sudo -u jt-glogarch`.

## [1.5.0] - 2026-04-11

### Fixed — OpenSearch `_id` fielddata circuit breaker (critical)

Scheduled OpenSearch exports were failing on large indices (650K+ docs)
with `circuit_breaking_exception: [fielddata] Data too large, data for
[_id] would be [1.6gb], which is larger than the limit of [1.5gb]`.
Three indices (graylog_489, 490, 492) failed consistently every night.

Root cause: `search_after` pagination used `{"_id": "asc"}` as
tiebreaker sort. Sorting by `_id` forces OpenSearch to load the entire
field into heap-resident fielddata — 680K doc IDs consumed 1.6 GB,
exceeding the default circuit breaker limit.

Fix: replaced `_id` tiebreaker with `_doc` (index insertion order).
Zero-cost, no fielddata needed. Verified: graylog_495 (680K docs)
now exports in 3m53s with zero errors.

### Fixed — OpenSearch transient error retry

`OpenSearchClient._request()` previously only retried on connection
errors (ConnectError / ConnectTimeout). HTTP 500, 502, 503, and 429
responses raised immediately without retry or host failover.

Now: transient HTTP errors trigger exponential backoff retry (up to
3 attempts with 1s/2s/4s waits) before falling back to the next host.
Non-transient errors (4xx) still raise immediately.

### Changed — Notification format overhaul

- Removed emoji from body lines — one status emoji on the title line
  only (✅ success, ⚠️ partial errors, ❌ failure)
- Each stat on its own line with clean `label: value` format
- Long URLs in error messages auto-shortened to `<url>` to prevent
  line-breaking in chat clients
- Import notifications now include duration
- Title examples: `✅ 匯出成功`, `⚠️ 匯出完成（有錯誤）`, `❌ 驗證失敗`

### Fixed — Preflight `collect_field_schema` failed on compressed schemas (code review)

`json.loads()` was called directly on the raw `field_schema` column, but
`ArchiveDB.record_archive()` compresses large schemas as `zlib:…`. This
caused preflight to silently fall back to `{}` for large archives, making
mixed-type field conflict detection ineffective. Now uses
`ArchiveDB.decompress_schema()` and logs a warning on parse failure
instead of silently swallowing. Backfill path also uses
`_maybe_compress_schema()` for consistency.

### Fixed — `_dt_to_str()` / `_str_to_dt()` timezone handling (code review)

`replace(tzinfo=None)` stripped timezone info without first converting to
UTC. A `+08:00` datetime would be stored as if it were UTC, shifting the
absolute time by 8 hours. Now calls `astimezone(timezone.utc)` before
stripping. All internal code uses `datetime.utcnow()` (naive UTC) so
existing DB data is unaffected.

### Fixed — Cross-conflict detection missed auto-created numeric mappings (code review)

`get_current_custom_mapping()` only read Graylog's custom field mappings
API. Numeric mappings auto-created by OpenSearch on first document were
invisible, so preflight could miss cross-conflicts (target=long,
archive=string). Now queries the actual OpenSearch mapping of the active
write index via `GET /<deflector>/_mapping` as primary source, with
custom mappings as fallback.

### Added — 55 unit tests (pytest)

First public test suite. Covers: secret sanitization (10), DB datetime
round-trip (5), field_schema compression (6), DB rebuild/backup (5),
cleanup race guard (3), bulk import mechanics (7), concurrent import
lock (5), notification format (7), OpenSearch `_doc` sort (1),
`/api/health` structure (2), preflight conflict computation (4).

### Fixed — Document / implementation consistency (reported by reviewer)

- **FastAPI `version` was hardcoded `"1.3.1"`** in `web/app.py` instead of
  reading `glogarch.__version__`. Now uses the single source of truth.
- **Export metadata `glogarch_version` was hardcoded `"1.3.1"`** in both
  `export/exporter.py` and `opensearch/exporter.py`. Fixed to read
  `__version__` so archive files always carry the correct version.
- **Config search path `/etc/glogarch/`** did not match the install script's
  `CONFIG_DIR="/etc/jt-glogarch"`. Renamed to `/etc/jt-glogarch/` (and
  home dir fallback to `~/.jt-glogarch/`).

## [1.4.4] - 2026-04-10

### Changed — Job History "Error" column → "Note"

- Column header renamed from "Error" / "錯誤" to "Note" / "備註" in
  both en and zh-TW i18n, since the column now carries informational
  notices (e.g. "where to find imported data") alongside actual errors.
- Color logic: red (`--danger`) only for failed jobs or messages
  containing "Compliance violation" / "Interrupted". All other notes
  display in muted grey (`--text-muted`). Applied in both the Jobs
  page and the Dashboard recent-jobs table.

### Fixed — Architecture diagram alignment

ASCII art diagram in both `README.md` and `README-zh_TW.md` had
inconsistent right-border alignment (the outer `|` column drifted
between rows). Redrawn at a fixed 70-char width with Python-verified
alignment.

## [1.4.3] - 2026-04-10

### Fixed — Live progress controls leaked into bulk mode

The import-modal "live controls" bar (Pause + Speed slider) was being
shown for both GELF and bulk imports, even though bulk mode honors
neither. Reported via screenshot showing 50-archive bulk import in
preflight phase with the slider visible at "100ms".

- Wrapped Pause + Speed slider in `#import-gelf-controls` and hid them
  in bulk mode (`doImportSingle` → `gelfControls.style.display='none'
  when mode==='bulk'`)
- Added a real `#import-cancel-btn` (always visible) so bulk imports
  can be cancelled mid-flight from the modal

### Fixed — `/jobs/{id}/cancel` did not stop bulk imports

The cancel endpoint set `_cancel_flags[job_id]` but the bulk loop's
cancel checkpoint reads `ImportFlowControl.cancelled` (set via
`get_import_control(job_id).cancel()`). Two unrelated cancel
mechanisms — pressing Cancel did nothing for bulk. Now the endpoint
also calls `get_import_control(job_id).cancel()` so cancel actually
stops the bulk loop between batches.

### Added — i18n for cancel-import confirmation

`confirm_cancel_import` strings in en + zh-TW (used by the new
`cancelActiveImport()` modal flow).

## [1.4.2] - 2026-04-10

End-to-end test of the v1.4.0 hardening release on a Graylog 7 target
(.83) surfaced two latent architectural bugs in bulk import mode plus
several UX issues. All fixed in this release.

### Fixed — Bulk mode imports were invisible to Graylog Search

Symptom: bulk import reported "completed, 159,286 messages" and the
data was confirmed in OpenSearch (`jt_restored_2026_04_09` index, 166 MB),
but searching the `jt-glogarch Restored (jt_restored)` stream in Graylog
returned 0 results. Found that 32 万筆 messages had accumulated as
orphan indices invisible to the UI.

Root cause: `BulkImporter._index_name_for_doc()` derived the target
index name from each doc's `timestamp` field
(`jt_restored_YYYY_MM_DD`). Graylog tracks an index set's membership in
MongoDB by sequential index name (`jt_restored_0`, `jt_restored_1`,
...), NOT by `<prefix>_*` wildcard. Indices created outside that
tracking are invisible to Graylog Search even when their name matches
the prefix. Stream → index_set → MongoDB list query never returned the
date-based indices.

Fix: bulk writes now ALWAYS go through the Graylog-managed deflector
alias (`<prefix>_deflector`). OpenSearch routes the bulk request to
whichever underlying index Graylog has marked `is_write_index=true`,
so:
- Graylog Search picks up our docs immediately (they live in the
  Graylog-tracked write index)
- Graylog's own SizeBased / TimeBased rotation strategy still applies
- No more orphan indices

`_ensure_index()` learned to detect the deflector alias suffix and
verify it via HEAD instead of trying to PUT it (which would fail with
`invalid_index_name_exception`). The per-doc index name walk that
earlier versions did to pre-create date-based indices is gone.

### Fixed — Bulk import "where to find" notice was silently swallowed

Symptom: bulk import succeeds, the Graylog stream is created correctly,
but the import-completed modal in the Web UI shows only "已完成! (N
記錄數)" with no hint about where in Graylog to look for the data. The
backend was writing the notice to `jobs.error_message` correctly (verified
via direct DB query) but the frontend never displayed it.

Root cause (`web/routes/api.py::get_job`): when a job is triggered from
the Web UI, `_job_progress[job_id]` accumulates SSE events. The
`/api/jobs/{id}` endpoint always preferred this in-memory cache over
the DB. The in-memory representation hardcoded `error_message =
last.get("error")` — which is None on success — and never read the
real `error_message` column from the DB. So the where_msg notice was
written but never returned.

Fix: when the in-memory progress shows the job is done (`phase=done`
or `pct>=100`), read the canonical row from the DB instead. This
returns the correct `error_message`, the correct `job_type`, and the
correct status. The in-memory cache is still used for in-progress
polling.

### Fixed — `/api/jobs/{id}` returned wrong `job_type` for imports

Side effect of the same `_job_progress` shortcut: it hardcoded
`"job_type": "export"` regardless of the actual job. Imports triggered
from the Web UI were mislabelled as exports in API responses (the
listing endpoint and Job History UI used a different code path so this
was usually invisible). Now the type is read from the DB row.

### Added — Verify schedule "Run Now" button

The Schedules page already supported run-now for export and cleanup
schedules. Verify schedules were missing the button purely because of
a single condition in the JS render. The backend
`POST /api/schedules/{name}/run` already supported all three job types.
One-line fix in `app.js` re-enables the button for verify schedules.

### Changed — Bulk batch_docs default 5000 → 10000

Validated on `.83` Graylog 7 target during v1.4.1 testing — 10k docs
per `_bulk` request runs cleanly without 429 backpressure. Doubles
throughput on most targets. Adjusted in 4 places: `BulkImporter.
DEFAULT_BATCH_DOCS`, `web/routes/api.py` body default, `index.html`
modal `value`, `cli/main.py --batch-docs` default.

### Documentation — Bulk mode rate slider has no effect

The "Batch Delay (ms)" slider in the import modal applies ONLY to
GELF mode. `BulkImporter.import_archives()` has no inter-batch sleep
in its hot loop — only retry backoff on OpenSearch 429. The slider is
already inside `#gelf-mode-fields` and is hidden when bulk mode is
selected, so users no longer see it as an option in bulk mode. The
real performance dial for bulk mode is `batch_docs`.

## [1.4.1] - 2026-04-10

Internal point release rolled into 1.4.2 — see above for details.
The deflector-alias bulk write fix landed here originally.

## [1.4.0] - 2026-04-09

Hardening release. End-to-end test of v1.3.1 surfaced a 20-item risk list
across disaster recovery, secret leakage, retention, race conditions,
reserved field handling, concurrency control, and operational concerns.
This release addresses every item.

### Added — Disaster recovery

- **`glogarch db-backup`** — online SQLite snapshot via the `.backup` API
  (safe while jt-glogarch is writing). Auto-prunes old snapshots
  (`--keep`, default 14). Recommended cron entry:
  `0 4 * * * /usr/bin/python3 -m glogarch db-backup`.
- **`glogarch db-rebuild`** — rebuild the SQLite metadata DB by scanning
  the archive directory. Reads each `.json.gz` metadata block + `.sha256`
  sidecar and re-inserts the row. Existing rows are preserved (no
  duplicates). Use after disaster recovery if the DB is lost or corrupted.

### Added — Operational endpoints

- **`GET /api/health`** — liveness/readiness probe for Prometheus blackbox,
  Kubernetes, Uptime Kuma, etc. Returns 200 (`healthy`) when DB is
  reachable, archive disk is writable + above the configured min-free,
  and the scheduler is running. Returns 503 with an `issues[]` array
  otherwise.

### Added — Maintenance helpers

- **`glogarch streams-cleanup`** — list/delete restored Streams + Index
  Sets created by jt-glogarch (auto-created during bulk-mode imports).
  Both the Graylog Stream and the underlying Index Set are removed
  (Graylog also drops the OpenSearch indices). Use after testing or when
  retiring an archive set.

### Added — Bulk import improvements

- **Cancel checkpoints** — `BulkImporter` now checks the cancel flag
  between batches. Pressing Cancel in the Web UI mid-import now stops
  the bulk write cleanly instead of running to completion.
- **Reserved-field stripping** — bulk body builder now drops `_id`,
  `_index`, `_source`, `_type`, `_routing`, `_parent`, `_version`,
  `_op_type` from each doc. Defends against the rare archive that
  contains a field whose name collides with an OpenSearch metadata
  field.

### Changed — `jt_restored_*` retention

- Previously: `NoopRetentionStrategy` with `max_number_of_indices = 2³¹-1`
  → indices accumulated forever after repeated bulk imports.
- Now: `DeletionRetentionStrategy` with `max_number_of_indices = 30`.
  Adjustable via the new `max_indices` parameter on
  `find_or_create_index_set()`. Protects the cluster from runaway disk
  use.

### Security

- **Secret sanitization for `jobs.error_message`** — new
  `glogarch/utils/sanitize.py` strips passwords / API tokens from any
  string before it lands in `jobs.error_message`, `audit_log.detail`,
  or any error path that goes through `update_job` / `create_job` /
  `audit`. Patterns covered: `Authorization: Basic|Bearer …`,
  `http(s)://user:pass@host`, `password=…`, `token=…`, `api_key=…`,
  and JSON-style `"password": "…"`. Output is also length-capped
  (default 2000 chars).
- **TLS verification** is now plumbed through `PreflightChecker`
  (`verify_ssl` constructor argument, default False). Hardcoded
  `verify=False` removed from the preflight HTTP client.
- **Token-expiry detection** — when an export or import fails with a
  Graylog 401, the error message now reads
  *"Graylog API authentication failed (401). Check that the API token is
  still valid: …"* and triggers the configured notification channel.

### Fixed — Race conditions and concurrency

- **Cleanup vs export race** — cleanup now skips any file modified within
  the last 10 minutes (`RECENT_FILE_GRACE_SECONDS`). Prevents the
  retention sweep from deleting an archive that is still being written
  by an in-flight export.
- **Concurrent import lock** — per-archive lock at the importer level.
  The same archive cannot be imported by two jobs at once (two browser
  tabs, schedule + manual click, CLI + Web UI). Conflicts fail fast with
  a clear message; the lock is released in the importer's `finally`
  block.
- **Notification failures are no longer swallowed** — `notify_*` exceptions
  are now logged as warnings and surfaced in the job's `errors[]` list,
  instead of being silently dropped by `try / except: pass`.

### Performance

- **`glogarch verify --workers N`** — parallel SHA256 hashing across N
  worker threads. Disk I/O bound, so threads work fine. Sequential
  behaviour preserved when `--workers 1` (the default).
- **`field_schema` column auto-compression** — when the per-archive field
  schema JSON exceeds 4 KiB it is now stored as `zlib:` + base64. Decoded
  transparently on read via `ArchiveDB.decompress_schema()`. Keeps the
  metadata DB compact for archives with many distinct fields.

### Documentation

- **DST and APScheduler**: APScheduler honours the system TZ; cron
  expressions like `0 3 * * *` may run twice or be skipped on DST
  transition days. Users who need wall-clock guarantees should use UTC
  cron expressions.
- **`gl2_processing_timestamp` / `gl2_remote_ip` after bulk**: bulk imports
  bypass Graylog's processing chain, so these fields reflect the
  *original* processing time at the source cluster. They are NOT
  rewritten on import. This is by design — bulk mode is intended to
  preserve the source-cluster journey.
- **Single-tenant**: jt-glogarch is single-tenant. There is no per-user
  data scoping in the metadata DB or the Web UI.
- **Web UI overwrites manual edits**: saving any setting from the Web UI
  rewrites `config.yaml` from the in-memory `Settings` object. Manual
  edits made between page load and save will be lost. For
  bulk/automated config changes, edit `config.yaml` directly and
  restart the service.
- **IndexSet name collision**: `find_or_create_index_set` looks up by
  `index_prefix`, not title. If two callers race to create the same
  prefix, the second one reuses the first's index set (the API enforces
  prefix uniqueness server-side).

## [1.3.1] - 2026-04-10

### Fixed — Bulk-mode imports were not visible in Graylog UI

End-to-end test of v1.3.0 bulk mode found that imported documents were
written to OpenSearch correctly but **not searchable from the Graylog UI**.
Root cause: Graylog Search filters by `streams` → index sets, and our docs
had `streams` field containing UUIDs from the SOURCE cluster which don't
exist on the target. Without a target stream bound to the bulk index set,
Graylog had no entry point to query the `jt_restored_*` indices.

- **`PreflightChecker.find_or_create_stream()`** — new method that creates
  a Graylog stream bound to the bulk index set via `POST /api/streams`
  (and resumes it). Bulk preflight now creates this stream right after
  the index set.
- **Graylog 6 + 7 dual-API support** — the stream creation API schema
  differs between Graylog versions:
  - Graylog 7: `CreateEntityRequest_CreateStreamRequest`
    → `{"entity": {<config>}, "share_request": null}`
  - Graylog 6: `UnwrappedCreateEntityRequest_CreateStreamRequest`
    → `{<config>, "share_request": null}` (flat with sibling)

  Try wrapped form first; on 4xx fall back to flat form. Both versions
  verified end-to-end.
- **`BulkImporter.target_stream_id`** — new attribute set by importer from
  the preflight result. Each doc's `streams` field is rewritten to
  `[target_stream_id]` before bulk write, replacing the source-cluster
  UUIDs. Now Graylog Search routes correctly to the new stream → new
  index set → `jt_restored_*` indices.
- **Post-completion notice** — bulk import success now records a "where to
  find your data" message in `jobs.error_message`. CLI prints it as a
  cyan ⓘ note. Web UI Job History shows it as a tooltip; the active import
  modal shows it in an info box on completion.
- **`ImportResult.notices`** — new field for non-error informational
  messages.
- **SSE `done` event was missing `error_message`** — `watchJob` in app.js
  now fetches the full job record on the SSE done event so post-completion
  notices surface in the UI.

### Fixed — Modal display issues

- **Modal too tall** — base `.modal-card` now has `max-height: 90vh` +
  `overflow-y: auto` so a tall import dialog scrolls within the viewport
  instead of overflowing past the top/bottom of the screen.
- **Mode selector card text wrapping char-by-char** — the radio cards
  were too narrow for the original labels. Reduced label text
  (`GELF (Graylog Pipeline)` → `GELF`,
  `OpenSearch Bulk (~5-10x)` → `OpenSearch Bulk`),
  added `min-width: 0` + `overflow-wrap: break-word` to inner divs,
  bumped modal width 420 → 460px.
- **Form re-shown after import completes** — `watchJob` onComplete callback
  was setting `import-modal-form` display back to `block`, leaving the
  form fields visible alongside the completed progress bar. Now the form
  stays hidden after completion; user dismisses the modal via the
  click-outside handler or a future Done button.

### Fixed — Static files not refreshed by `pip install` alone

When editing `web/static/js/*.js` or `web/static/css/*.css`, FastAPI's
StaticFiles mount serves from the **installed package** at
`/usr/local/lib/python3.10/dist-packages/glogarch/web/static/`, not from
`/opt/jt-glogarch/glogarch/web/static/`. Rsyncing static files into `/opt`
alone is not enough — must always run `pip install --force-reinstall`
afterwards. Documented in CLAUDE.md.

### Changed — Taiwan terminology cleanup

- `推薦` → `建議` (i18n bulk_dedup_id, README-zh_TW)
- `殘留檔案` → `殘留檔案` (README-zh_TW)
- Removed all "v1.1+ archives" / "v1.0 archives" version-history language
  from user-facing docs and code comments since v1.3.0 is the first
  public release.
- Removed obsolete SSH journal monitoring references from README — only
  Graylog API journal monitoring remains.

### Added — README language switcher

Both `README.md` and `README-zh_TW.md` now have a language toggle line
at the top: `**Language**: **English** | [繁體中文](README-zh_TW.md)`
(and the mirror in zh-TW). GitHub renders the relative link to switch
between the two READMEs.

### Added — `gl2_message_id` preserved during export

Exporters preserve `gl2_message_id` (used as bulk-import dedup key);
other `gl2_*` fields are still stripped. GELF import path is unaffected
since Graylog regenerates all `gl2_*` on receive.

## [1.3.0] - 2026-04-09

### Added — OpenSearch Bulk Import Mode

New high-throughput import mode that bypasses Graylog entirely and writes
directly to OpenSearch via the `_bulk` API. Verified end-to-end via CLI.

- **`glogarch/import_/bulk.py`** — `BulkImporter` class
  - Reads archives, builds NDJSON bulk requests, parses per-doc results
  - Daily index naming: `<pattern>_YYYY_MM_DD` based on each doc's timestamp
  - Pre-creates target indices (Graylog clusters typically have
    `action.auto_create_index = false`)
  - Three dedup strategies: `id` (use `gl2_message_id` as `_id`, overwrites
    on re-import), `none`, `fail`
  - Exponential backoff on OpenSearch 429 (rate-limited) responses
  - Marker field `_jt_glogarch_imported_at` injected for traceability
- **Preflight extensions** for bulk mode:
  - `auto_detect_opensearch_url()` — derives OpenSearch URL from Graylog
    API URL (port 9000 → 9200) and probes connectivity
  - `find_or_create_index_set()` — auto-creates a Graylog index set for
    the bulk target prefix so restored data is searchable from the
    Graylog UI immediately
  - `apply_bulk_template()` — writes an OpenSearch index template for the
    bulk target pattern with `total_fields.limit: 10000` and all
    string-typed fields pinned as `keyword`
  - `PreflightChecker.run(mode='bulk', ...)` branch: skips Graylog
    deflector cycle (irrelevant) and instead writes the bulk template +
    creates the Graylog index set
- **`Importer`** accepts `mode='bulk'` + `bulk_importer` parameter and
  branches before the GELF send loop
- **Web UI modal** rebuilt with mode selector:
  - Two radio cards: `GELF (Graylog Pipeline)` (default) and
    `OpenSearch Bulk (~5-10x)`
  - Bulk mode shows an orange warning explaining what's skipped
  - Bulk-mode-only fields: target index pattern, dedup strategy,
    batch size, OpenSearch auto-detect checkbox + manual URL/credentials
  - Switching modes hides/shows field groups; values persist across
    switches; Graylog API credentials are shared between modes
  - 23 new i18n strings (en + zh-TW)
  - New CSS: `.mode-selector`, `.mode-option`, `.bulk-warning`
- **CLI `import` command** new options:
  - `--mode [gelf|bulk]`
  - `--target-os-url`, `--target-os-username`, `--target-os-password`
  - `--target-index-pattern` (default `jt_restored`)
  - `--dedup-strategy [id|none|fail]`
  - `--batch-docs` (default 5000)
- **Trade-offs documented** — bulk mode skips ALL Graylog processing
  (Pipelines, Extractors, Stream routing, Alerts). Use only for
  "restore archived data as-is" scenarios.

### Added — gl2_message_id preserved during export

To enable deterministic dedup in bulk import, both exporters preserve
the `gl2_message_id` field. Other `gl2_*` fields (`gl2_source_input`,
`gl2_processing_timestamp`, etc.) are still stripped because they reference
source-cluster nodes/inputs that don't exist in the target.

- **`opensearch/client.py`** — `iter_index_docs` keeps `gl2_message_id`
- **`graylog/search.py`** — `_extract_messages` keeps `gl2_message_id`
- GELF import path is unaffected — Graylog regenerates all `gl2_*` fields
  on receive, including a fresh `gl2_message_id`.

### Added — IMPORTING-state crash recovery

`ArchiveDB.connect()` now resets any archive stuck in `importing` state
back to `completed` on startup, with a warning log. Cause: when an import
process is killed (`-9`, OOM, crash) the importer's `finally` block doesn't
run, leaving the archive permanently flagged as `importing` and invisible
in the Web UI archive list. Now recovered automatically on next service
start or DB connect.

### Added — UI polish (continuing v1.2.0 work)

- **GELF Host → Graylog API URL auto-fill** — typing an IP into GELF Host
  auto-suggests `http://<ip>:9000` for the API URL field, but only if the
  user hasn't manually edited the API URL. Same `data-user-edited` flag
  pattern as the GELF port auto-switch.
- **Reopen running import modal from sidebar** — if the user accidentally
  clicks outside an in-progress import modal to dismiss it, clicking the
  sidebar running-job indicator reopens the modal in progress mode (form
  hidden, progress bar + controls visible). The watcher (SSE + polling)
  keeps running in the background while the modal is closed.
  - `closeImportModal()` early-returns if `_activeImportJobId` is set,
    preserving all state instead of resetting it
  - New `reopenActiveImportModal()` function
  - Sidebar `checkRunningJobs()` adds `cursor: pointer` + `onclick` handler
- **Import modal i18n complete** — `Pause`/`Resume` button, `Speed:` label,
  `sending`/`paused` phase text, `Journal: X (slow)` badge, and the
  `(N archives)` count in the "import started" message all now translate.
- **`completed_with_failures` job badge** — orange shield-checkmark icon
  in the Job History table when a `completed` job has an `error_message`
  containing "Compliance violation". Hover shows the full violation
  message. Pure frontend logic (no DB schema change).

### Fixed — bugs found during v1.3.0 CLI testing

- **`def list(...)` shadowing Python builtin** in `cli/main.py` — the
  `list` CLI command was defined as `def list(...)`, which placed a click
  Command object at the module-level name `list`, shadowing the builtin.
  Inside `import_cmd`, the line `ids = list(archive_id) if archive_id else None`
  was actually invoking the click Command, producing a confusing
  `TypeError: object of type 'int' has no len()` from click's argument
  parser. Renamed to `def list_cmd(...)` with `@cli.command("list")`.
- **Bulk path failed with `index_not_found_exception`** — Graylog clusters
  typically set OpenSearch `action.auto_create_index = false`, so the
  `_bulk` API can't auto-create the daily target indices. `BulkImporter`
  now scans archive timestamps in the pre-flight pass to enumerate every
  needed daily index name and PUTs them all (idempotent: 400 with
  `resource_already_exists_exception` is treated as success).
- **`pip install` no-op when version unchanged** — if the package version
  in `pyproject.toml` doesn't change between code edits, `pip install`
  silently treats it as already-installed and skips. Always use
  `--force-reinstall --no-deps` after editing source.

## [1.2.0] - 2026-04-09

### Added — Compliance Pipeline (Zero-Loss Import)

This release introduces a complete compliance pipeline for log restoration. Goal:
**zero message loss + zero indexer failures** when importing archived logs back
into a target Graylog. Verified end-to-end with 8.28M-message imports across 67
hourly archives spanning 2 days.

- **Field schema recording during export** — `archives.field_schema` column (JSON)
  now stores `{field_name: [observed types]}` for every archive. Both the
  OpenSearch and API exporters accumulate this in `StreamingArchiveWriter` while
  writing each message (cost: ~10 µs/msg, negligible). Used by import preflight.
- **`glogarch/import_/preflight.py`** — new module that runs **before** any GELF
  send and guarantees the target Graylog index will accept every message:
  1. Verifies target Graylog API credentials
  2. **Cluster health check** — refuses to import if OpenSearch cluster is RED
  3. **GELF input check** — verifies a GELF input exists on the configured port,
     is in `RUNNING` state, and warns about `override_source`, `decompress_size_limit`,
     `max_message_size` settings that might silently corrupt or drop messages
  4. **Existing journal pressure check** — warns if target's journal already has
     >100K uncommitted entries
  5. **Capacity check** — reads rotation/retention strategy of the target index
     set; estimates how many indices the import will create; **aborts** if the
     deletion-based retention policy would erase data we just wrote
  6. **Field schema collection** — pulls `field_schema` JSON from DB for each
     selected archive (milliseconds). For pre-1.2.0 archives without schema,
     falls back to scanning the .json.gz file inline and backfills the DB
  7. **Conflict detection** — pins a field as `keyword` (string) on the target
     only if (a) the archive observed both numeric and string values for it
     (intra-archive conflict, guaranteed mapping clash) OR (b) target's current
     mapping is numeric while archive has strings. Avoids over-pinning the
     1000-field limit
  8. **OpenSearch field limit override** — automatically PUTs an OpenSearch
     index template named `jt-glogarch-field-limit` with
     `index.mapping.total_fields.limit: 10000`, eliminating the
     "Limit of total fields [1000] has been exceeded" error that breaks index
     rotation when many custom mappings are set
  9. **Custom field mappings + cycle** — applies the conflict-pinned mappings
     via Graylog `PUT /api/system/indices/mappings` (one PUT per field with
     `rotate: false`), then issues a single deflector cycle so the new mappings
     take effect on the new active write index
  10. **Wait for new index** — polls until the new active write index is ready
- **Post-import reconciliation** — after the GELF send completes, jt-glogarch
  queries Graylog's indexer-failures total and compares against the pre-import
  baseline. Any non-zero delta is recorded in `jobs.error_message` and the job
  is marked completed with a compliance violation note
- **Mandatory target Graylog API credentials** — the import dialog now requires
  `target_api_url` + (`target_api_token` OR `target_api_username` + `target_api_password`).
  Both frontend and `POST /api/import` reject missing credentials. The same
  credentials power preflight, journal monitoring, and reconciliation
- **Notification field masking** — All credential fields (Bot Token, Chat ID, webhook URLs, SMTP password, Nextcloud token/user/pass, etc.) are now masked by default with an eye-icon toggle button to reveal/hide
- **Sidebar logo link** — Clicking the `jt-glogarch` title in the sidebar opens the project repository in a new tab
- **Archive timeline visualization** on Archive List page
  - Daily distribution bar chart with bar height proportional to record count
  - Drag to select time range with hour-level precision (auto-fills filter and applies)
  - Hover with vertical cursor line, full-column hover area, dashed cursor follows mouse
  - Hover tooltip shows date, archive count, record count, file size
  - Clear selection button (always reserves space to prevent layout shift)
  - Bordered chart with accent-colored bars and red markers for gap days
- **Table flash animation** when filter applied or data reloaded
- **Import flow control system**
  - Pause/resume during import via Web UI
  - Real-time speed adjustment (batch delay slider)
  - **Three monitoring modes** to prevent target Graylog buffer/journal overflow:
    - None (manual control)
    - Graylog API monitoring (`/api/system/journal`)
    - SSH monitoring (remote `du` on journal directory)
  - Dynamic rate control based on `uncommitted_journal_entries`:
    - >100K → triple delay
    - >500K → auto-pause 30s
    - >1M → stop import + admin notification
- **OpenSearch keep_indices mode**
  - Schedule by "keep N most recent indices" instead of days
  - Allows N > current index count (anticipating future growth)
  - UI shows `60 份 Index` instead of `180 天`
- **Dashboard 5th stat card**: original (uncompressed) size with sparkline
- **Sparkline tooltips**: hover bars show date and value
- **Tabular numerals** in timeline tooltip for consistent width as digits change

### Changed — Compliance Pipeline Side Effects
- **Import dialog refactored**: removed Journal-monitoring dropdown (`None`/`API`/`SSH`) and the entire SSH-monitoring code path. Target Graylog API credentials are now always required (one set powers preflight, journal monitoring, and reconciliation).
- **Default GELF protocol = TCP / port = 32202** (was UDP / 12201). UDP is still selectable but README explicitly warns about silent packet loss under load.
- **TCP backpressure + journal monitoring** are always-on. The importer auto-pauses when target Graylog's `uncommitted_journal_entries` exceeds 500K and resumes after 30 s, preventing buffer overflow.
- **`POST /api/import`, `POST /api/export`, `POST /api/schedules/{name}/run`** now run their work in a worker thread (`asyncio.run(...)` inside `loop.run_in_executor`) so the main FastAPI event loop is no longer blocked by gzip/JSON/GELF CPU work. Web UI stays responsive during multi-million-message imports/exports.
- **`ArchiveScheduler._run_export`** is registered with APScheduler via a sync wrapper (`_run_export_in_thread`) for the same reason.
- Compressed size card label changed to "Compressed" (vs new "Original Size")
- Records count display: `9,458,948 of 9,458,948` (bold + dimmed total)
- Sidebar toggle button vertically aligned with logo
- Dark theme number colors brightened for readability
- Notification settings: unchecked channels auto-collapse their config fields
- Notification test endpoint bypasses event-type check (always sends if channel enabled)
- "操作" → "動作" (Taiwan terminology, throughout UI)

### Fixed — Compliance Pipeline Bugs Found During Validation
- **OpenSearch exporter cross-index data loss** — `is_time_range_covered()` was blocking sister indices in the same OpenSearch run from writing data for hours that span an index rotation boundary. Symptom: visibly low message counts on certain hours. Fixed by adding `exclude_stream_id_prefix` so cross-mode dedup only applies across mode boundaries, not within an OpenSearch run. **This was causing ~17% data loss on affected hours**.
- **Web UI import dialog state leak** — `_batchImportIds` was being cleared immediately after the POST returned (success or fail), so retry attempts after a failed first import silently did nothing. Fixed by deferring cleanup until `closeImportModal()`.
- **Web UI import dialog progress residue** — failed import progress bar/text persisted into the next attempt visually. Fixed by resetting bar width and text content at the start of `watchJob()`.
- **Web UI import dialog wrong host on retry** — related to the above; new code now correctly reads form values for each retry.
- **OpenSearch field limit exceeded** — when applying many custom field mappings, Graylog's auto-generated index template exceeded OpenSearch's default 1000-field-per-index limit, causing `Limit of total fields [1000] has been exceeded` and breaking index rotation. Preflight now installs an override template `jt-glogarch-field-limit` with `total_fields.limit: 10000`.
- **Stale custom field mappings on target** — when preflight aborts mid-flow, the partially-applied custom mappings stay in Graylog's MongoDB and clobber subsequent index rotations. Documented cleanup procedure in README.
- FastAPI route order: `/archives/timeline` must be before `/archives/{archive_id}` (422 error)
- pip install cache: `build/` directory caused stale installs (now force-reinstalled)
- Schedule edit modal: `keep_indices` value not restored after coverage widget loads
- Single click on timeline no longer clears existing selection (now moves the highlight to a 1-hour box at the click position)
- Archive timeline bar height now uses message count (not file count)
- Notification test was blocked by `_should_send` event-type check
- OpenSearch resume point removed (relied on per-chunk dedup to avoid gaps)
- Schedule edit: pause auto-refresh polling while modal is open
- Mode selector reset bug during edit (caused by `initCustomSelects` race)
- Import dialog: GELF Port input and Protocol select now have matching height (38px) and vertical alignment
- Import dialog: Graylog API URL / API Token / Username / Password / SSH Host / SSH Port / SSH User / Journal Path labels and placeholders now respect the i18n language setting
- Journal monitoring dropdown: option labels (`None (manual control)` / `Graylog API` / `SSH`) were always English — added a `data-i18n-opt` handler in `i18n.js` so they translate
- Notification password fields are now `type="password"` by default with autocomplete disabled, preventing accidental exposure on shared screens
- All version display locations unified to v1.2.0 (login page, sidebar, package metadata, exporter `glogarch_version`)

### Documentation
- README updated with installation SOP improvements
- install.sh now cleans `build/` cache before pip install
- Deployed and verified on fresh Ubuntu 22.04 LXC
- Repository URL corrected throughout README/CHANGELOG/`jt-glogarch.service` to `https://github.com/jasoncheng7115/jt-glogarch`
- New FAQ entry: scheduled job didn't run at expected time → check that the system timezone matches the timezone you wrote your cron expression in (APScheduler inherits the system timezone)

## [1.0.0] - 2026-04-06

### Added
- **Dual export mode**: Graylog API + OpenSearch Direct
- **OpenSearch single-scan export**: Scan entire index once, split into hourly archive files (5x faster)
- **Cross-mode deduplication**: Prevents re-exporting when switching between API and OpenSearch modes
- **GELF UDP import**: UDP sender (default) with protocol selector in Web UI
- **JVM memory guard**: Auto-stops API export if Graylog heap > 85%, sends admin notification
- **Verify schedule**: Scheduled SHA256 integrity checks (new job type)
- **Archive status**: `corrupted` and `missing` statuses with visual indicators
- **Dashboard sparklines**: Grafana-style area graph backgrounds on stat cards
- **Original size tracking**: Pre-compression size alongside compressed size
- **Notification language**: Bilingual messages (English / Traditional Chinese)
- **Sidebar collapse**: Persistent collapsible sidebar
- **Job detail display**: Current index/chunk shown during export
- **Elapsed time column**: Duration in job history and dashboard
- **Schedule Run Now**: All types (export, cleanup, verify) support immediate execution
- **Monthly schedule**: "1st Saturday 03:00" frequency option

### Changed
- API batch_size: 300 -> 1000, delay: 200ms -> 5ms (with JVM memory guard)
- OpenSearch batch_size: 10,000, delay: 2ms
- Export/Import pages merged into Schedules and Archive List
- "Scheduled Export" renamed to "Scheduled Jobs"

### Fixed
- Scheduled export 0-record bug (resume point cross-stream contamination)
- OpenSearch timestamp format mismatch
- Job ID mismatch between Web UI and DB
- DB thread safety, XSS vulnerabilities, permission issues

## [0.7.1] - 2026-03-29

### Added
- Initial release with core functionality
- Graylog API export with streaming write
- OpenSearch direct export (per-index)
- GELF TCP import
- Web UI with 7 pages
- CLI commands, APScheduler, 6-channel notifications
- Dark/light theme, English/zh-TW i18n
