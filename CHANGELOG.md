# Changelog

All notable changes to jt-glogarch will be documented in this file.

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

### Added — gl2_message_id preserved during export (v1.1 archive format)

To enable deterministic dedup in bulk import, both exporters now preserve
the `gl2_message_id` field instead of stripping it with the rest of `gl2_*`.
Other `gl2_*` fields (`gl2_source_input`, `gl2_processing_timestamp`, etc.)
are still stripped because they reference source-cluster nodes/inputs that
don't exist in the target.

- **`opensearch/client.py`** — `iter_index_docs` keeps `gl2_message_id`
- **`graylog/search.py`** — `_extract_messages` keeps `gl2_message_id`
- **`ArchiveMetadata.version`** bumped from `"1.0"` to `"1.1"` to mark the
  format change. Old (v1.0) archives still import correctly via GELF; bulk
  import of v1.0 archives degrades to "no dedup" (auto-generated `_id`).
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
- Repository URL corrected throughout README/CHANGELOG/`glogarch.service` to `https://github.com/jasoncheng7115/jt-glogarch`
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
