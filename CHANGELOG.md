# Changelog

All notable changes to jt-glogarch will be documented in this file.

## [1.10.12] - 2026-07-06

### Fixed

- **`install.sh` no longer silently aborts on non-interactive installs.** The
  "Install systemd service?" prompt used `read` under `set -e`; when stdin is not
  a terminal (`curl | bash`, `ssh 'bash …'`, redirected input) `read` hits EOF and
  returns non-zero, which aborted the whole script right there — silently skipping
  systemd unit install and enable. The prompt now runs only when stdin is a TTY and
  defaults to installing the service otherwise.

### Changed

- **`install.sh` used as an upgrade now restarts a running service.** install.sh
  detects at startup whether `jt-glogarch` is already active; if so, after
  reinstalling it restarts the unit and verifies it came back up, so the newly
  installed code actually takes effect (a package reinstall alone does not restart
  the running process). Fresh installs are unchanged — they still print the
  `systemctl enable --now jt-glogarch` hint.

## [1.10.11] - 2026-07-05

### PDF Reports (beta) — rebuild fidelity

- **Area/line charts render correctly.** A widget with `visualization: area`/`line`
  is now drawn as a line/area chart dispatched on the visualization — not the
  time-vs-value heuristic. A numeric values pivot (e.g. a `duration_us`
  distribution) reads left-to-right by its key instead of being turned into 15
  value-ranked bars.
- **All stacked/grouped series are kept.** Column-pivot series were capped at 6,
  silently dropping data from a stacked chart (and its legend). Raised to 30 so
  the chart matches Graylog (palette cycles like Graylog).
- **"Skip Empty Values" is honoured** on both row and column pivots — blank
  buckets are dropped, matching the widget setting.
- **Cover logo height is configurable** per report (`logo_height_px`, default 72),
  with a field in the report editor.

## [1.10.10] - 2026-07-05

### Fixed

- **Job/report notes are language-neutral (English).** The Task Log / report-history
  note for email delivery no longer shows hardcoded Chinese ("Email 已寄送") in the
  English UI — stored operational text is now English ("Email sent" / "Email failed: …").
- **Report TOC numbers align.** Table-of-contents item numbers are right-aligned in a
  fixed-width column, so a two-digit number (10., 11., …) no longer shifts its title
  out of line with the single-digit rows.

### Changed

- **Cover logo enlarged** from 46px to 72px height (aspect preserved).

### Security

- Passed an **OWASP ZAP baseline scan** of the web UI with **0 High / 0 Medium /
  0 Low** findings (62 passive rules pass; remaining alerts are Informational
  detection tags). Larger releases now require a clean ZAP scan — see `TESTING.md`.

## [1.10.9] - 2026-07-05

### PDF Reports (beta)

- **Message preview joins its log entry as one visual row.** With "Show message in
  new row" enabled, the message line now sits directly under its fields with no
  separator between them (the row divider falls after the message), so each entry
  reads as one row instead of looking like two.
- **Polished report emails.** The email that delivers a report PDF now has a
  formatted HTML body (title, generated time, file name/size) matching the
  notification emails, instead of a single plain-text line.

### Changed

- **Default export mode `api` everywhere.** `config.yaml.example` now ships
  `export_mode: api` to match the installer and the code default (Graylog API is
  the universally-compatible, permission-respecting mode; the backpressure guard
  protects it).
- **Settings → Default Export Mode** shows a highlighted note that a schedule with
  its own export mode ignores this default (it only applies to schedules with no
  mode set and to manual exports).

### Fixed

- **Per-widget / per-tab time ranges are respected (report fidelity).** When a
  report uses "each widget's own time range", it no longer forces every widget to
  a single window — a widget saved as "last 5 days" now renders 5 days even if
  another on the same dashboard is "last 1 day". "Use dashboard time" and a
  report-wide range (incl. snap-to-midnight) are now mutually exclusive: with
  per-widget time on, no global override is applied (in both rebuild and
  screenshot modes).
- **No redundant sidebar tooltip when expanded.** The left nav's instant hover
  tooltip now only appears when the sidebar is collapsed to icons; when expanded
  (labels visible) it is suppressed.

## [1.10.8] - 2026-07-05

### Fixed

- **Custom dropdowns didn't fire their change handlers.** The styled custom-select
  widget dispatched a non-bubbling `change` event, so document-level delegated
  handlers never ran — e.g. switching a schedule's export mode from OpenSearch to
  Graylog API left the OpenSearch index panel (and hint text) showing. The widget
  now dispatches a bubbling event, so every `data-act-change` select behaves like
  a native one (this also removes the need for the `no-custom` workaround).

### Changed

- **Heap advice now recommends setting `-Xms` = `-Xmx`.** The connection-test hint
  advises setting both the initial and max heap to the same value (JVM best
  practice: pre-commit the whole heap, avoid dynamic-growth GC pauses).

## [1.10.7] - 2026-07-05

### Export safety

- **Adaptive backpressure guard (API *and* OpenSearch-direct export).** A heavy export loads the same OpenSearch cluster Graylog indexes into; on busy or HDD-backed storage this starves ingestion and can wedge Graylog until it's restarted. The export now samples Graylog's own health on a **fixed ~15 s cadence** (per batch, decoupled from chunk size) — JVM heap %, disk journal (uncommitted entries), and the input/process/output ring buffers — and **pauses whenever any of them keeps climbing, resuming only once they drain**. JVM heap is **two-tier**: a soft tier (75 %, sustained) backs off well before the ceiling without tripping on a GC-sawtooth peak, and a hard tier (90 %) pauses immediately on an acute spike. It is **fail-safe**: if Graylog can't be read (the very moment it's in trouble) the export pauses instead of hammering it. Every pause is logged and the running job shows exactly which signal is overloaded. A connection-failure circuit breaker aborts a run that keeps failing. All thresholds are configurable under `export:` in `config.yaml`.
  - *Fixes the prior guard's blind spots:* it only watched JVM heap at a near-ceiling 85 %, checked every 5 chunks (minutes apart), and — worst — returned "0 %" (healthy) when Graylog was unreachable, so it kept exporting into a frozen server.
- **Graylog heap advice on connection test.** Testing a Graylog server now reports its current JVM heap (`-Xmx`) and a recommended minimum, so under-provisioned heaps are caught before they cause an export to stall.
- **Email delivery failures are no longer silent.** A report whose PDF generated fine but whose email was rejected (e.g. an invalid *From* address) now records the SMTP error in the report history and the job note, instead of showing a green "completed".

### PDF Reports (beta)

- **String metric columns are left-aligned.** A metric like `latest(interface_name)` (value `WAN`) or a date column is no longer forced right-aligned; only genuinely numeric columns right-align, per Graylog.
- **Snap-to-midnight only applies to whole-day ranges.** For a sub-day dashboard range (e.g. last 2 hours) ending at 00:00 is meaningless, so the option is ignored; the hint text now says so.

### Fixed

- **Schedule dialog export-mode race.** Switching the export mode from OpenSearch to Graylog API no longer leaves the OpenSearch index panel showing — a slower in-flight load for the other mode can't overwrite the panel after you switch.

## [1.10.6] - 2026-07-05

### Fixed

- **Masked secret could be saved literally, breaking logins (important).** `_mask()` reveals the first/last 3 characters of a secret with asterisks in between, and the save path treats any value containing `***` as "unchanged, keep the stored secret". But a 7- or 8-character secret masked to only 1–2 asterisks (e.g. an 8-char admin password → `abc**xyz`), slipping past that check — so re-saving a report/server/notification settings could overwrite the real secret with the mask, producing "Invalid credentials" afterwards. Masks now always embed at least three asterisks, so every masked secret is reliably recognised and preserved on save. Any secret saved while the bug was present must be re-entered once.
- **Report password field is now blank-on-edit.** Editing a report no longer echoes the (masked) stored password back into the field. It shows an empty field with a "leave blank to keep, type to change" hint — so the save rule is unambiguous and it is impossible to accidentally re-save a masked/partial value over the real password.

### PDF Reports (beta)

- **Date-typed metrics render as datetimes.** `min(timestamp)` / `max(timestamp)` (and any metric on a `date`-typed field) now show a formatted local datetime like Graylog (e.g. `2026-07-05 05:50:32.000`) instead of a raw epoch number.
- **Message tables honour "Show message in new row" (message preview).** When a message-list widget has message preview enabled, the full message is now rendered on a second line under each row — matching the on-screen widget.
- **Message-table timestamps show local time** in `YYYY-MM-DD HH:MM:SS.mmm` format instead of a raw ISO `…Z` string.
- **Bar/line charts honour the widget's axis type** (`linear` / `logarithmic`) and bar mode (`group` / `stack` / `relative` / `overlay`).
- **Screenshot mode now captures the WHOLE dashboard.** Graylog lazy-renders each widget's chart only while it is on screen, so a tall dashboard previously captured every off-screen widget as blank. The capture now grows the browser viewport tall enough to hold the entire grid at once, so every widget renders before the shot.
- **Screenshot mode now honours the report's time range and snap-to-midnight.** The capture best-effort overrides the live dashboard's global time range to the report's window (previously screenshot mode always used the dashboard's own range). Falls back to the dashboard's range if the override can't be applied. (Note: widgets with their OWN explicit per-widget time range are kept by Graylog and are not affected by a global override.)
- **Widget-aware page breaks for screenshot mode.** The tall dashboard capture is now split into pages at the GAPS between widget rows (detected from the image), so a widget is never cut in half across a page boundary. The section title now also shares its page with the first slice instead of sitting alone.

## [1.10.5] - 2026-07-05

### PDF Reports (beta)

- **Grouped row-pivots.** A multi-level row pivot (e.g. source_ip → hostname → device) now blanks repeated parent values and separates groups, so sub-rows visibly belong to their parent — matching Graylog instead of repeating the IP on every row.
- **Heatmap column headers rendered vertically** (long category names no longer overlap in narrow columns); long labels are truncated.
- **Watermark** text is now balanced across its (max two) lines and font-auto-fit, so the whole watermark — including the base word and full date — fits and shows completely on every page.
- **Cover** adds a "Generated by: jt-glogarch vX.Y.Z" line.

### Web UI

- The Graylog-server "test connection" result now shows inline **under that server's row** (not below the whole table), at the same size as the OpenSearch panel.

## [1.10.4] - 2026-07-05

### Fixed — **critical: online upgrade could lose config/certs**

- **`upgrade.sh` git-stash data loss.** When `git pull` needed to stash (any
  local/untracked divergence), `git stash push -u` swept up the **untracked
  `config.yaml`, `certs/`, `.session_secret`, and the DB** on installs without a
  `.gitignore` (i.e. every install before 1.10.3) and did not restore them —
  leaving the service on HTTP with default config. `upgrade.sh` now writes the
  protective ignore rules **before** any git operation, so stash/clean can never
  touch user data. **Recovery for an already-affected box:** the data is intact
  in `git stash` — `cd /opt/jt-glogarch && git stash pop` (stop the service and
  move the current DB aside first) restores it.
- **Recommended upgrade command changed** to `curl -fsSL …/deploy/upgrade.sh |
  sudo bash`, which runs the newest (fixed) script directly. This makes a big
  jump such as 1.7.9 → latest a single, data-safe run — and installs the PDF
  runtime deps in that one run. See the README "Upgrade" section.

## [1.10.3] - 2026-07-05

### Fixed — upgrade tooling (found during full .83 upgrade testing)

- **Offline bundle Chromium revision mismatch.** The bundle installed Chromium using the build host's (possibly older) Playwright, while shipping a newer Playwright *wheel* — so the target installed playwright-X, looked for `chromium-<rev-for-X>`, and couldn't find the bundled browser (PDF rendering failed offline). The bundle now installs Chromium via the exact bundled wheel in an isolated venv, so the revision always matches.
- **Repository `.gitignore` added.** `config.yaml`, `*.db`(+`-wal`/`-shm`), `.session_secret`, `certs/`, `.playwright/`, and report/backup output are now ignored, so an upgrade's `git` operations can never touch user data.

### Note

- Upgrading **online** from a pre-1.10.0 version to 1.10.x installs the new code on the first `upgrade.sh` run and the PDF-report runtime deps (Chromium + CJK font) on a **second** run (the first run is still executing the old script that predates the dependency step). The **offline** upgrade installs everything in a single run. Verified end-to-end on a clean box for both paths (PDF render smoke test passes as the service user).

## [1.10.2] - 2026-07-05

### PDF Reports (beta) — major fidelity + feature pass

- **Faithful widget rendering.** Heatmaps render as colour-graded grids honouring the widget's `color_scale` (Portland/Viridis/…) with a legend and no in-cell numbers by default (matching Graylog; optional toggle). Tables stay tables, maps stay maps. Column-pivot tables now include the rollup total column and sort the pivot columns. Metric values map to columns by series key, so a null metric no longer shifts the next column's value. Bar mode (group/stack/overlay) mirrored; overlay drawn with outlined layers for legibility.
- **Units.** Byte metrics render as GB/MB/B on chart axes and single values, matching each series' Graylog unit setting.
- **Colours match Graylog** (Plotly default colourway).
- **Single-value trend badges** (delta + %, coloured by `trend_preference`).
- **Best-fit table columns** (no more forced equal widths); wide message tables guarded by a configurable max-columns setting + row-limit note.
- **Empty-data widgets** show "(no data)" instead of a broken empty chart.
- **World map** redesigned (clean palette, brand bubbles).
- **Header/footer** brand bands drawn full-bleed (no viewer-dependent gap), only from page 2; cover has clean white margins with a centred brand block. **Table of contents shows page numbers.** Time-range captions now in local time.
- **Screenshot mode**: full long-capture of just the dashboard grid (auto-scroll to load every widget, sliced across pages); clear, specific failure reasons.
- **Snap-to-midnight** time option for scheduled reports; cron presets default to 05:00.
- **Flattened watermark** (non-selectable/non-deletable), configurable text/size/direction, auto-appends server/IP/time/dashboard/recipients across at most two lines, font auto-fit so every page shows all of it.
- **SHA-256 fingerprint** for each report (DB + `.sha256` sidecar + Web UI verify), report name editable, job history shows 100% + widget count, two header-logo variants (dark/light) with drag-and-drop upload.
- **Auto report-cleanup schedule** (720-day default, editable days + cron), bootstrapped on install and upgrade.

### Deployment

- Install / upgrade / offline scripts now install the PDF Reports runtime deps (Chromium into a shared path + a CJK font + PyMuPDF + Pillow).

### Web UI

- Inline "test connection" for Graylog servers (dashboard + settings); server table delete/set-default/test buttons tidied.
- Upgrade command blocks readable in light theme; upgrade steps numbered.
- Heavier dashboards: search poll window raised (partial results kept) so large boards return complete data.

## [1.9.3] - 2026-07-04

### Improved — PDF Reports (beta)

- **Readable time-axis labels.** Rebuilt time-series charts showed raw ISO bucket keys (`2026-07-03T09:45:00.000+08:00`) crammed at 45°. Now formatted to `MM-DD HH:MM` and thinned to ~12 horizontal ticks.
- **Bar-chart mode fidelity.** A rebuilt bar widget now mirrors the source Graylog visualization's `barmode` — stacked / grouped / overlay / relative — instead of always grouping.
- **`max_widgets = 0` (or blank) now means "all widgets"** (it previously rendered none).
- **Per-dashboard tab selection.** Multi-tab dashboards (e.g. 13-tab OPNsense) can now target a single tab; the report picker shows a tab dropdown, and `GET /api/reports/dashboard-tabs` lists them. Default is still all tabs.
- **Cover logo.** New optional cover-logo upload in the report editor (client-side data-URI, ≤300 KB) rendered on the cover page.
- **Cron picker.** The report schedule field now has a friendly frequency dropdown (hourly / daily / weekly / monthly / custom) in addition to the raw cron text.
- **UI polish.** Report action buttons aligned; the Reports nav item is now `統計報表` (four chars, consistent with the other nav items); "Rebuild → branded charts" (was "our charts").

### Improved — project site

- The zh-TW landing hero rotates five taglines (4s each, cross-faded, respects `prefers-reduced-motion`).

## [1.9.2] - 2026-07-04

### Added — offline / air-gapped upgrade

- **`scripts/build-offline-bundle.sh`** builds a self-contained upgrade bundle (`dist/jt-glogarch-<ver>-offline.tar.gz`) on any internet-connected machine: the jt-glogarch wheel + **every runtime dependency wheel** (full transitive closure, including the compiled uvloop/httptools/watchfiles) + the **source tree** + the offline installer.
- **`deploy/upgrade-offline.sh`** upgrades a host that has **no internet**. It installs from the bundled wheels only (`pip --no-index`), so pip never touches the network. Backs up the DB, refreshes the `/opt/jt-glogarch` source tree, force-reinstalls the package into dist-packages, restarts, and verifies `/api/health`.
- Both upgrade methods (online git-pull and offline bundle) are now documented in **README** (EN + zh_TW) and in a new **Settings → System Upgrade** section in the Web UI.

### Fixed

- **Offline upgrade now refreshes the `/opt/jt-glogarch` source tree, not just dist-packages.** A pip wheel install only updates dist-packages (which the systemd service uses); the `/opt` source is what `python -m glogarch` loads when the CLI is run from `/opt` (Python imports the CWD first). Leaving it stale meant a post-upgrade CLI run from `/opt` silently executed the *old* code. The offline installer now syncs the source in place, mirroring what the online git-pull does.
- **`upgrade.sh` / `upgrade-offline.sh` DB backup** now runs from the install dir so `db-backup` finds `config.yaml` (and thus the DB), and the "continue without a fresh backup?" prompt no longer hangs when run non-interactively (scripted SOP) — it falls back to a loud warning + continue.

### Verified in the field

- Full **offline SOP dry-run** on a Graylog-7.1.2 customer VM: 1.7.9 → 1.9.2 with `pip --no-index` (zero network), healthy.
- Reproduced the customer's 1.7.9 `500 Result window is too large` (scheduled backup completing green with **0 messages archived**), then confirmed 1.9.2 exports the **same** dataset with no 500 and archives written.

## [1.9.1] - 2026-07-04

### Fixed — export data-integrity sweep (Graylog API + OpenSearch Direct)

A full audit of both export paths for customers upgrading from 1.7.9. Every finding below could, under load, silently lose or duplicate messages while still reporting a green "Completed" job.

- **Graylog API — same-millisecond boundary data loss (HIGH).** When a time window filled the 10,000-result ceiling, the next window advanced by `last_timestamp + 1ms`, silently dropping every message that shared that exact millisecond beyond the ceiling. The window now advances to the *exact* last timestamp and de-duplicates the boundary millisecond by `gl2_message_id`, so no message is lost or duplicated. This required sending the search window at **millisecond precision** (it was truncated to whole seconds, which also caused duplicate re-fetching of the boundary second).
- **Graylog API — early window termination (HIGH).** Pagination stopped on the mutable per-request `total_results`, which can shrink mid-export if an index rotates/retention-deletes, dropping the window's tail. It now ends on a short page (the reliable end-of-data signal).
- **Graylog API — silent truncation on odd timestamps (MEDIUM).** An unparseable/stale boundary timestamp used to `break` and silently truncate the chunk. It now raises (surfaced + retried) and the timestamp parser handles any ISO-8601 shape (nanoseconds, explicit offsets).
- **OpenSearch Direct — no failover on transient 5xx (HIGH).** A `429/500/502/503` that exhausted retries on one node used to abort the whole index; a single overloaded node (circuit breaker / GC pause) silently dropped an entire index even when a healthy node was available. It now fails over to the next host and only raises when *all* hosts are exhausted.
- **OpenSearch Direct — `search_after` early stop (MEDIUM).** Pagination stopped at a pre-counted `total`, which can under-count due to concurrent merge/refresh drift and skip the tail. It now paginates until the cursor is exhausted.
- **Both modes — partial failures no longer hide behind a green "Completed".** Per-index/per-chunk failures are now reported in the job note (`⚠ N failed — will retry next run`). A systematic mid-run failure (cluster goes RED after some success) now aborts fast instead of grinding for hours. Disk-exhaustion during OpenSearch export is now a fatal abort, not a per-index error retried on every remaining index.
- **Rate limiter** no longer holds its lock across the wait, which had serialized all requests and defeated the burst allowance.

### Fixed — upgrade / migration (1.7.9 → 1.9.1)

- **Stuck `IMPORTING` archives are recovered at startup.** An import killed mid-flight (e.g. the service restart during an upgrade) left the archive row `IMPORTING`, which the per-archive lock made permanently un-importable. Startup now flips stale `IMPORTING` rows back to `COMPLETED`, honoring the documented crash-recovery guarantee.
- **`upgrade.sh` hardened.** A failing database backup is no longer silently swallowed (it prompts before continuing without a fresh backup); a `git pull` blocked by local hotfixes auto-stashes and retries instead of aborting the upgrade half-done.

### Notes

- DB schema and 1.7.9 `config.yaml` already auto-migrate with no manual steps (verified): new columns/tables are added on connect, `api_audit→op_audit` is remapped, no new config key is required, and an existing `servers:` correctly skips the first-run wizard.
- Known limitation (unchanged): mixing API-mode (stream-filtered) and OpenSearch-mode (whole-index) exports on the *same* server can let time-range dedup skip whole-index data. Use one export mode per server.

## [1.9.0] - 2026-07-03

### Added — PDF Reports (beta)

- **New "Reports" page** — generate branded, professional PDF reports, a la Graylog Enterprise reporting, but open. Reports have a gradient **cover page** (title, subtitle, logo, author, period), **table of contents**, **executive summary with KPI cards**, running **header/footer with page numbers**, and CJK-capable fonts (Traditional Chinese renders correctly).
- **Graylog dashboards in one of two selectable modes per report:**
  - **Rebuild** (default) — queries the dashboard's widgets via the Graylog Views API (executes the search + polls the async job across all tabs) and **redraws them as our own branded Chart.js charts** (bar / doughnut / line / grouped, single-value cards, tables) from live data. No Graylog web login needed — the API token suffices.
  - **Screenshot** — a headless Chromium logs into the Graylog web UI (with the report's configured Graylog web credentials) and captures the native dashboard image — "looks exactly like Graylog".
- Plus an always-available **archive & audit summary** (branded charts from jt-glogarch's own archive / job / audit statistics) with an executive KPI summary.
- **Scheduling + email delivery**: reports can run on a cron schedule (APScheduler) and be emailed as PDF attachments via the configured SMTP settings. Generate-now and download-history are available in the UI.
- **Rendering** mirrors Graylog Enterprise's approach (a headless-Chromium single print pass) via Playwright. Requires the optional `report` extra (`pip install 'jt-glogarch[report]'`), `playwright install chromium`, and CJK fonts on the host; the UI shows a clear notice and degrades gracefully when the render engine is absent.
- New DB tables `reports` / `report_history` (auto-created), `/api/reports*` endpoints, and `test_reports.py` coverage.

### Security

- Reports developed against the **OWASP Top 10:2025**: report download is path-contained to the reports directory and forced to `attachment` (A01 Broken Access Control); dashboard capture only ever targets a **configured** Graylog server, never an arbitrary URL (A01/SSRF); Chart.js is vendored + pinned, no runtime CDN (A03 Software Supply Chain); web password is masked in transit and reconciled on save (A04); generation failures are caught, sanitized, and recorded rather than surfaced as stack traces (A10 Mishandling of Exceptional Conditions); a per-report concurrency guard prevents duplicate heavy renders (A06). Verified with an OWASP ZAP baseline scan — 0 High / 0 Medium / 0 Low.
- **Penetration test hardening** (authenticated + unauthenticated probing of the running app): disabled the FastAPI interactive docs and OpenAPI schema (`/docs`, `/redoc`, `/openapi.json`), which sat outside the `/api/` auth middleware and let anonymous clients enumerate every endpoint (A01/A02); added an **SSRF guard** on the connection-test endpoints (`/api/opensearch/test`, `/api/config/servers/test`) that blocks link-local / cloud-metadata targets like `169.254.169.254` while still allowing loopback and RFC1918 internal hosts (A01); malformed JSON bodies now return 400 instead of 500, and a malformed `time_from`/`time_to` on export returns 400 instead of silently starting a broken job (A10). SQL filters confirmed parameterized (no injection); 500 responses confirmed to leak no stack traces. New `test_security.py`.

### Fixed

- **API-mode export no longer 500s on high-volume time chunks ("Result window is too large").** The deep-pagination loop bounded offset by a fixed `MAX_SAFE_OFFSET = 9500` but still requested `limit = batch_size` on top, so a fetch could ask for `from + size = 9500 + 1000 = 10500`, exceeding OpenSearch's default `index.max_result_window` of 10000 → Graylog returned 500. On a busy source (e.g. a firewall) *every* time chunk exceeds this, so every chunk failed and the export produced 0 records after hours of retrying. The loop now guarantees `offset + batch ≤ 10000` for any batch size, and advances the time window using the **last message actually fetched** (previously it re-fetched at offset 9499, which could also skip the tail of a window). Verified end-to-end against a 661,427-message window — paginates cleanly with zero 500s.
- **API-mode export errors now surface Graylog's actual reason** instead of an opaque `500 Internal Server Error`. The Graylog/OpenSearch error body (e.g. *"Failed to obtain results: Result window is too large, [from + size] must be less than or equal to: [10000] … use scroll or search_after"*) is now included in the job error and notification — previously `raise_for_status()` discarded it. Added a **fail-fast circuit breaker**: if 10 chunks fail in a row with nothing exported, the export aborts immediately (with the real error) instead of grinding through thousands of chunks for hours on a systematic failure. New `test_graylog_error_detail.py`.

## [1.8.0] - 2026-07-02

### Added — Configure Graylog & OpenSearch from the Web UI + first-run setup wizard

- **Connection settings are now editable in the Web UI** (previously `config.yaml` only, requiring a restart). A new **Settings** page manages Graylog servers (add / edit / delete, per-server OpenSearch, default server, test-connection), the global OpenSearch cluster, the default export mode, and an optional emergency local admin password. Changes apply live — no `systemctl restart` needed for connection settings.
- **First-run setup wizard.** A fresh install ships with an empty `servers:` list; the Web UI detects the unconfigured state and redirects to `/setup`, a 5-step wizard: (1) set an admin password, (2) add a Graylog server (with test), (3) OpenSearch (optional — skip for API-mode), (4) archive path, (5) done. `install.sh` now writes a minimal bootstrap `config.yaml` instead of a dummy example, so the wizard drives first-time configuration.
- **Bootstrap auth.** Because login authenticates against Graylog, a fresh install (no server yet) had no way in. The wizard's step 1 sets a local admin password (username `localadmin`) and opens an authenticated session; the setup endpoints are the only pre-auth write path and are hard-gated — they return 403 the moment a server exists.

### Changed — Upgrade path (existing customers)

- **Zero-migration and fully backward compatible.** Existing installs already have `servers:` configured, so the wizard never triggers — they simply gain the new Settings page. `upgrade.sh` never overwrites `servers:` / `opensearch:`. Editing a server does a partial update that preserves fields the UI doesn't surface (e.g. a server carrying both username/password and a token) and unrelated top-level config keys.
- Secrets are masked (`***`) in every GET and reconciled on save — saving without changing a secret keeps the stored value (fixes a latent bug where the notification config could overwrite real secrets with their masked form on restart).

### Security

- **Passes an OWASP ZAP baseline scan with zero High/Medium/Low findings.** Added a strict `Content-Security-Policy` **without `unsafe-inline`** — the entire Web UI was refactored to carry no inline scripts, inline event handlers, or inline `style` attributes (all via external JS event-delegation, CSS classes, and CSSOM for dynamic values). Also added `Permissions-Policy`, `Cross-Origin-Opener-Policy`/`Embedder-Policy`/`Resource-Policy`, `Cache-Control: no-store` (non-static), an anti-CSRF token on the login form, `SameSite=Strict` session cookie (+ existing `Secure`/`HttpOnly`), and stripped the `Server` banner.
- New `scripts/zap-scan.sh` runs the ZAP baseline DAST scan against a live instance and fails on any Medium/High alert (`.zap/rules.tsv` documents justified exceptions).
- All Web UI config writes now go through a single **atomic, locked** config writer (`glogarch/core/config_writer.py`): temp-file + `os.replace()` and a process-wide lock, eliminating the previous non-atomic read-modify-write that could lose concurrent updates or truncate `config.yaml` on a crash.

### Tests

- +15 tests: `test_config_writer.py` (atomic write, key preservation, secret reconcile) and `test_settings_api.py` (setup gate, server CRUD, secret masking, and the OLD→NEW **upgrade** path). See `TESTING.md` for the feature↔test map.

### Fixed

- **Export progress bar could read 0% while records were clearly being exported.** API-mode progress is time-/chunk-based (reliable), but one stray message-based percentage remained in the skip path: on a *resume* of a mostly-already-archived range, `messages_done` counts only newly-exported messages while the denominator was the full-range pre-count — so the live bar collapsed to ~0% even though most chunks were done. All export progress views are now consistently chunk-based. (Display-only; no effect on the exported data.)
- **Login now works with any configured Graylog server.** Previously only the *default* server's account could sign in. Login now tries each configured server (default first) and the first that accepts the credentials wins — important for multi-cluster setups where user directories differ per server. Falls back to the local admin only when no server is reachable.
- **Dashboard/Settings server list stalled ~10-14s.** The Data Node detection (`GET /api/datanodes`) went through the retrying client, so a 404 on Graylog without data nodes tripped the retry decorator's 2+4+8s backoff (~14s). It is now a direct single-shot call (5s timeout, no retry) skipped entirely for unreachable servers, and `/api/servers` probes all servers concurrently — the endpoint now returns in ~30ms (measured 14.05s → 0.01s for the probe).
- Settings page: added an icon and explanatory text to "Default Export Mode", and a description to "Global OpenSearch".

## [1.7.17] - 2026-07-02

### Fixed — Schedules page took 20-40s to load with no loading indicator

- Opening the **Schedules** page (`/schedules`) blocked for 20-40 seconds before any content appeared, and showed a blank table (no "loading" state) while it waited.
- Root cause: the page awaited `GET /api/servers` **before** rendering the schedule table. `/api/servers` runs a live per-server connectivity check (`GET /api/system`) plus a Data Node probe (`GET /api/datanodes`), both routed through the retry decorator (3 attempts, 2s/4s/8s backoff) with a 10s connect timeout. On Graylog 6 `/api/datanodes` returns 404 and burns the full ~14s of retry backoff; an unreachable node adds the connect timeouts on top — 20-40s total. The schedule table itself is a fast DB-only read, but it never ran until that probe finished (`.finally()`).
- Fix (frontend): render the schedule table immediately with a loading spinner via `loadTable()`, and fetch `/api/servers` in parallel without blocking. The server name is only a display fallback (schedules store their own `c.server`) and fills in on the next poll once the probe resolves.
- Fix (backend): `/api/servers` now probes all servers concurrently (`asyncio.gather`) instead of serially, so N slow/unreachable servers no longer add up.

## [1.7.16] - 2026-06-17

### Added — Per-server OpenSearch cluster (archive multiple sources)

- jt-glogarch could already archive **multiple Graylog servers** (list them all under `servers:`, then create one export schedule per server — each export job targets one server, chosen in the Web UI export/schedule dialog or via `glogarch export --server <name>`). This was never documented, so users assumed only one source was possible. The README, CONFIG reference (EN + zh_TW), and `deploy/config.yaml.example` now show a multi-source config example.
- **OpenSearch Direct mode was limited to a single cluster.** The top-level `opensearch:` block is one cluster, and its `hosts` list is the failover *nodes* of that one cluster — there was no way to point different Graylog servers at different OpenSearch clusters. OpenSearch-mode export of a *second* site's cluster was impossible.
- Fix: `GraylogServerConfig` gains an optional `opensearch:` block. When set, OpenSearch-mode export for that server uses its own cluster; when omitted, it falls back to the global top-level `opensearch:` block. Resolution is centralised in the new `Settings.get_opensearch(server_name)` helper, used by every export path:
  - Scheduled export (`scheduler.py`), manual export + schedule run-now (`web/routes/api.py`), and CLI `glogarch export` (`cli/main.py`).
  - The OpenSearch settings/test endpoints (`/api/opensearch/status|indices|test`) and `glogarch test-opensearch` accept an optional `server` argument to operate on a specific server's resolved cluster.
- **Fully backward compatible.** Existing single-cluster configs are unchanged — a server with no `opensearch:` block transparently uses the global block. The `hosts` list still means "failover nodes of one cluster"; to archive *separate* clusters, give each its own `servers[]` entry with a per-server `opensearch:` block.
- Docs: new "Archiving Multiple Sources" section in both READMEs, expanded `servers` / `opensearch` sections in CONFIG.md + CONFIG-zh_TW.md (with a "one cluster vs multiple clusters" table), commented per-server example in `deploy/config.yaml.example`, and a richer `glogarch config` generated template.

## [1.7.15] - 2026-05-28

### Fixed — Sensitive-operation notification omits the source IP

- A customer reported receiving `[jt-glogarch] ⚠️ 偵測到 1 個敏感行為` with body `admin — auth.login [admin] → 200` and no IP information. For a login alert the whole point is to know *where* the login came from — without the IP the operator can't tell whether it's themselves on the office network or someone on the wild internet.
- Two bugs in `glogarch/audit/listener.py::_notify_sensitive`:
  1. The line format only printed `user — op [target] → status`, dropping `remote_addr` even though it's already on every audit entry.
  2. The dedup key was `(username, operation, target_name, status_code)`. The same user appearing from two different IPs in the same flush window got merged into a single line with `×2`, *hiding the security-relevant signal* that two distinct IPs were involved.
- Fix: include `remote_addr` in the dedup key, and render the user as `user@ip` (falls back to bare `user` when the IP is empty, which can happen for cookie-session entries that haven't been resolved yet). Same-user/same-IP repeats still collapse into `×N`; same-user/different-IP now correctly shows on separate lines.
- New notification body example: `admin@10.0.0.5 — auth.login [admin] → 200` (was: `admin — auth.login [admin] → 200`).
- Body-formatting logic extracted to `AuditSyslogListener._format_sensitive_body` (pure static helper). New `tests/test_sensitive_notify_body.py` covers the six cases that matter — IP shown, IP missing, two-IP no-merge, same-IP merge with count, no target, and >5 groups truncation.

## [1.7.14] - 2026-05-14

### Fixed — `deploy/install.sh` failed on a clean Ubuntu 24.04 install with `externally-managed-environment`

- A customer doing a fresh install on Ubuntu 24.04.4 LTS (Python 3.12) reported `sudo bash deploy/install.sh` aborted at "Installing jt-glogarch and dependencies..." with `error: externally-managed-environment` / "This environment is externally managed", suggesting `apt install python3-xyz`, a venv, or `pipx`. The installer never reached the systemd / directories / SSL-cert steps, so the system was left half-configured.
- Root cause: Ubuntu 24.04 (and Debian 12+) ship `/usr/lib/python3.12/EXTERNALLY-MANAGED` per PEP 668. With that marker present, `pip install <pkg>` against the system Python refuses by default and requires `--break-system-packages` to override. `deploy/install.sh`, `deploy/upgrade.sh`, and `deploy/uninstall.sh` were written before PEP 668 was widely enforced and never passed the flag. Ubuntu 22.04 (Python 3.10/3.11) does not ship the marker, so the same scripts worked there — the breakage only surfaced when a customer installed on 24.04.
- jt-glogarch is a dedicated single-purpose service install: it runs as its own system user, the systemd unit invokes `/usr/local/bin/glogarch`, and there is no expectation that the host runs other Python applications side-by-side. Writing into the system Python is the intended deployment model, so `--break-system-packages` is the correct flag here. (Migrating to a venv would change the systemd unit path, every reference in docs, the upgrade flow, and is not in scope.)
- Fix: detect the EXTERNALLY-MANAGED marker at the top of each deploy script and add `--break-system-packages` to every `pip install` / `pip uninstall` call when present. On older distros without the marker, behavior is unchanged. Detection is portable:
  ```bash
  EM_FILE=$(python3 -c 'import sysconfig; print(sysconfig.get_paths()["stdlib"] + "/EXTERNALLY-MANAGED")' 2>/dev/null || true)
  PIP_FLAGS=""
  if [ -n "$EM_FILE" ] && [ -f "$EM_FILE" ]; then
      PIP_FLAGS="--break-system-packages"
      echo "Detected PEP 668 (EXTERNALLY-MANAGED) — using --break-system-packages"
  fi
  ```
  Applied to `deploy/install.sh` (setuptools/wheel upgrade + both jt-glogarch installs), `deploy/upgrade.sh` (the `pip install --force-reinstall`), and `deploy/uninstall.sh` (the `pip uninstall`).
- Customer workaround if they cannot wait for v1.7.14 to land in their checkout: re-run pip manually with the flag explicitly, e.g. `sudo pip install --break-system-packages --no-build-isolation --no-cache-dir --force-reinstall --no-deps /opt/jt-glogarch` (then the second pip with deps), then re-run `sudo bash deploy/install.sh` — the user / dirs / SSL / systemd steps that the script aborted before are idempotent and complete cleanly on the second pass.

## [1.7.13] - 2026-05-12

### Fixed — Random "cannot start a transaction within a transaction" failure aborts one index in long OpenSearch exports

- A customer's overnight scheduled OpenSearch export reported `匯出區段: 9 / 略過區段: 0 / 錯誤: 1` after 12h15m, with the error `Index graylog_1254 failed: cannot start a transaction within a transaction`. That string is a literal SQLite error message, not from OpenSearch, and it means the index was silently skipped — no archive file produced, no DB record for the time window — even though the export itself was reported as "completed (with errors)". The other nine chunks finished fine, so the symptom appears intermittent.
- Root cause: `glogarch/core/database.py` uses a single shared `sqlite3.Connection` and serialises writes with `self._lock`. Four code paths were writing through the connection directly with `db.conn.execute(UPDATE ...); db.conn.commit()` without holding `_lock`:
  1. `glogarch/audit/listener.py::_refresh_ip_user_cache` — runs every ~5 min from the asyncio event loop while exports run for hours, doing per-IP `UPDATE api_audit` + `commit` on the shared connection.
  2. `glogarch/web/routes/api.py` (4 sites) — `UPDATE schedules SET last_run_at` issued by the "run now" schedule endpoint and by the export run finally-block in a worker thread.
  3. `glogarch/web/app.py::_cleanup_stale_jobs` — startup-time cleanup (low risk, but inconsistent with the rest).
  During a 12h export, the worker thread calls `db.update_job()` every batch (≈20,000 times). The audit listener fires ~144 times in parallel. When the worker had just committed (the C-level `in_transaction` flag flipped to False, lock released) and the audit listener entered `execute(UPDATE)` in the same instant, both threads read `in_transaction=False` and both auto-issued `BEGIN`. Whichever lost the race got SQLite's `cannot start a transaction within a transaction` raised inside `record_archive` / `update_job`, which the exporter's per-index `try/except` caught at `glogarch/opensearch/exporter.py:269` — aborting the whole index for that run.
- Fix: every write now goes through a locked helper.
  - New `ArchiveDB.update_schedule_last_run(name, when=None)` — replaces the 4× unlocked `UPDATE schedules` sites in `web/routes/api.py`.
  - New `ArchiveDB.backfill_audit_usernames(ip_user_pairs, default_user)` — replaces the per-IP backfill loop and final commit in `audit/listener.py::_refresh_ip_user_cache`.
  - New `ArchiveDB.cleanup_stale_running_jobs()` — replaces the inline implementation in `web/app.py::_cleanup_stale_jobs`.
  - Added `tests/test_concurrent_db_writes.py` with four regression tests that hammer the new helpers from multiple threads alongside `update_job()` for 1–2s of dense contention each. The previous unlocked pattern fails these reliably; the locked pattern is clean.
- Operational note: the failed `graylog_1254` segment will be picked up automatically by the next scheduled OpenSearch export, because dedup (`find_archive` + `get_coverage_ratio`) returns "not archived" for that time window — no archive file or DB row was created during the failed attempt. The retry only succeeds if the index still exists in OpenSearch when the schedule fires (i.e. before Graylog rotation deletes it).

## [1.7.12] - 2026-05-04

### Fixed — Import-complete notification always reported `Duration: 0s`

- Telegram/Discord/Slack/Teams/Nextcloud Talk/Email "import complete" messages always showed `Duration: 0s` / `耗時: 0s`, regardless of the actual run length. A real-world batch test on 192.168.1.83 imported five archives of 502 / 26,221 / 31,769 / 131,944 / 373,258 records taking 12 / 14 / 18 / 32 / 102 seconds respectively — every notification still said `0s`.
- Root cause: `notify_import_complete(...)` accepts `duration_seconds: float = 0`, but neither call site in `glogarch/import_/importer.py` (Bulk-mode path and GELF-mode path) ever measured or passed it. The `Importer.run()` method had no start-time bookkeeping. The export side already does this correctly (`ExportResult.duration_seconds` is set right before `notify_export_complete(...)`); the import side never received the same treatment.
- Fix: record `_start_time = time.time()` at the top of `Importer.run()`, add `duration_seconds: float` to `ImportResult`, compute `result.duration_seconds = time.time() - _start_time` immediately before each `notify_import_complete(...)` call, and pass it through. Mirrors the existing exporter pattern. No template / message format change — the existing `{duration}` placeholder was already correct, just always receiving `0`.

### Fixed — `Notification send failed` warning logged on every successful send

- `journalctl -u jt-glogarch` was filling with `Notification send failed   error="_make_filtering_bound_logger.<locals>.make_method.<locals>.meth() got multiple values for argument 'event'"` after every notification. Confusing in monitoring, even though the messages themselves were arriving fine.
- Root cause: `glogarch/notify/sender.py::send_notification` logs `log.info("Notification sent", channel=..., event=event.value)`. structlog's bound logger reserves the first positional/`event` kwarg for the message, so passing both `"Notification sent"` and `event=` triggers the duplicate-kw error. The exception bubbled up to the importer, which logged it as `Notification send failed` despite the actual delivery having succeeded.
- Fix: rename the structured-log key from `event=` to `notify_event=`. Notifications were never broken — only the post-delivery info-log line — but the spurious warning is now gone.

## [1.7.11] - 2026-05-03

### Fixed — Operation Audit page stat cards looked "wrong" without explaining the time window

- The four stat cards on `/op-audit` (`Operations`, `Users`, `Login Fail`, `Sensitive`) are computed by `/api/audit/stats?hours=24`, i.e. last-24-hour counts. The list below them is paginated all-time history. When older sensitive entries appeared in the list (each showing a `!` marker) but the `Sensitive` card showed `0`, users reasonably assumed the page was buggy — the time-window difference was only documented in the cards' hover tooltips, which most users never see.
- Fix: added a small subtitle line "Statistics for the last 24 hours" / "最近 24 小時統計" directly above the card grid, plus tightened the sensitive card tooltip to also say "in the last 24 hours" so all four tooltips are consistent. No code/data change — purely a labelling clarification.

## [1.7.10] - 2026-05-03

### Fixed — Job History "Records" column was misleading for verify and cleanup

- The Job History column header read "Records" / "記錄數", but for verify the cell shows the count of *archive files* scanned and for cleanup the count of *files deleted*. A reader could easily mistake "verify completed: 3,454" as "only 3,454 messages verified" when in fact 3,454 archive files containing millions of messages had been verified.
- Fix: column header renamed to neutral "Processed" / "處理量", and each cell now appends an explicit unit per `job_type` — `records / 筆` for export and import, `archives / 份` for verify, `files / 個檔` for cleanup. Three call sites of `formatRecords()` updated to pass `j.job_type`.
- Also factored out a separate `unit_records` i18n key for the four other places (archive timeline tooltip, export-complete inline status, op-audit total count) that had been reusing `th_messages` purely to render the word "records" — those now no longer change meaning when the table header gets renamed in the future.

## [1.7.9] - 2026-05-02

### Fixed — Schedules with day-of-week fired one day off (critical correctness)

- A customer reported that auto-verify, configured to run "every first Saturday of the month at 03:00" via the UI preset (cron `0 3 1-7 * 6`), did NOT fire on Saturday 2026-05-02. Instead the next-fire was 2026-05-03 Sunday.
- Root cause: APScheduler's `CronTrigger.from_crontab` numbers the day-of-week field as `0=Mon, 6=Sun`, while POSIX cron — which everything in this project's UI presets, README, and customer mental model assumes — uses `0=Sun, 6=Sat`. The off-by-one meant `* * * * 6` executed on Sunday rather than Saturday, and `* * * * 0` executed on Monday rather than Sunday. The two affected built-in UI presets:
  - `0 0 * * 0` labelled "Weekly (Sunday 00:00)" actually fired Mondays.
  - `0 3 1-7 * 6` labelled "Monthly (1st Saturday 03:00)" actually fired the first Sunday.
- Fix: added `posix_cron_to_apscheduler()` in `glogarch/scheduler/scheduler.py` that translates the dow field before handing it to APScheduler. Single numbers, ranges, lists, wildcards, step expressions, and named days are all handled; ranges that wrap after conversion (e.g. POSIX Fri-Mon `5-1` → APS `4-6,0`) are split at the week edge. Both `apply_schedule()` (runtime registration) and `_schedule_to_dict()` (UI's "next run" column computed from cron) route through the same helper, so what the user sees and what fires now agree. Existing schedules in the DB are stored as POSIX and interpreted correctly on next service start. 17 new unit tests in `tests/test_posix_cron.py`.
- **Impact on existing schedules**: any schedule that had a numeric dow field will now fire on the day a POSIX user would expect. Schedules without dow numbers (`0 3 * * *`, `0 0 * * *`, etc.) are unaffected. Customers who were unknowingly relying on the off-by-one should not see any harm — the actual fire day shifts to match what the cron string literally says.

## [1.7.8] - 2026-04-30

### Fixed — Schedule page mirrored running progress to every export schedule

- When one export schedule was running, every other export-type row on the schedules page showed the same progress bar / percentage / message count. The customer report case: an `api-export` schedule (mode=API, manually triggered) and an `auto-export` schedule (mode=OpenSearch, cron-fired) — running either one decorated both rows with identical progress.
- Root cause: `loadSchedules()` in `web/static/js/app.js` did `(jobsData.items || []).find(j => j.status === 'running' && j.job_type === 'export' ...)` to locate "the" running export job, then attached its progress bar to **every** row whose `job_type === 'export'`. There was no way to tell which schedule had triggered the job because the `source` column was only `"manual:api"` / `"scheduled:opensearch"` etc. — no schedule name.
- Fix: extended the `source` field format to a third segment carrying the schedule name. New format: `"{manual|scheduled}:{api|opensearch}:{schedule_name}"`.
  - `scheduler.py::_run_export_once` and `web/routes/api.py::run_schedule_now` now write the third segment.
  - `/api/export` (manual export from the /export page, not bound to any schedule) keeps the two-segment form so it does NOT decorate any schedule row.
- Frontend: `loadSchedules()` now builds `runningBySchedule[name]` from the third segment and only attaches progress to the row whose `name` matches. The two existing `srcType`/`srcMode` consumers (jobs page badges, dashboard recent-jobs badges) ignore unknown extra segments, so they keep working unchanged.
- "Run Now" button visibility is unchanged in spirit: still hidden on every row while any export is running (server-level export lock would reject a concurrent run anyway).

### Fixed — Manual "Run Now" of verify / cleanup did not appear in Job History

- Triggering an `auto-verify` or `auto-cleanup` run via the "立即執行" button only wrote an `audit_log` entry and updated `schedules.last_run_at` — it never touched the `jobs` table. As a result the run was invisible from Job History, Dashboard recent jobs, and the `/api/jobs` API.
- Fix: `web/routes/api.py::run_schedule_now` now creates a `RUNNING` `JobRecord` before invoking `Cleaner`/`Verifier`, transitions it to `COMPLETED` (with a summary in the notes column) or `FAILED` (with a sanitized error) when the call returns. Source format follows the v1.7.8 convention: `manual:cleanup:<name>` / `manual:verify:<name>`. Scheduled cron firings of verify/cleanup also got their source upgraded to `scheduled:verify:<name>` / `scheduled:cleanup:<name>` for consistency with export.

## [1.7.7] - 2026-04-30

### Fixed — Language switch did not fully refresh dynamic content

- The `langchange` listener in `web/static/js/app.js` only re-rendered the `/logs` and `/op-audit` pages. Every other page (`/`, `/archives`, `/jobs`, `/schedules`, `/notify-settings`) had JS-rendered innerHTML (status badges, table cells, modal labels, channel results) that stayed in the previous language until the user manually refreshed the browser.
- Fix: extended the listener to re-fire each page's loader on language change, preserving pagination state (e.g. `archivePage`, `_auditPage`).
- Also i18n'd four hardcoded English fragments: OpenSearch test result (`Connected!` / `Failed:` / `Error:` / `Unknown error` / `Status:` / `Nodes:`), notify channel test outcome (`OK` / `Failed`), GELF Port label, schedule type select options (`Export` / `Cleanup` / `Verify`), and the OK button on info-only confirm dialogs. New i18n keys: `btn_ok`, `test_connected`, `test_failed`, `test_error`, `unknown_error`, `result_ok`, `result_failed`, `os_status`, `os_nodes`, `import_gelf_port`, `sched_type_export/cleanup/verify`.

## [1.7.6] - 2026-04-29

### Fixed — Scheduled verify and cleanup did not appear in Job History

- `_run_verify` and `_run_cleanup` in `glogarch/scheduler/scheduler.py` never wrote a row to the `jobs` table. Only export was tracked, so users running auto-verify or auto-cleanup saw the schedule's `last_run_at` update but found nothing in `/jobs` (作業歷程).
- `_run_export`'s rare failure-path also tried to call `db.create_job(job_id, "export", source="scheduled")` — that signature has not existed since `create_job()` was changed to accept a `JobRecord`. The call was wrapped in `try/except`, so it silently swallowed every error and never recorded the failed export.
- Fix: added `_create_run_job()` / `_finish_run_job()` helpers on `ArchiveScheduler` and routed all three scheduled handlers through them. Each scheduled run now creates a `RUNNING` job at start, then transitions to `COMPLETED` (with summary in the notes column) or `FAILED` (with sanitized error) at the end. Verify with corrupted/missing files is recorded as `FAILED` so it stands out in the UI.

## [1.7.5] - 2026-04-29

### Fixed — Email notification: non-secret fields rendered as masked password inputs

- On the Notification Settings page, **SMTP host**, **SMTP user**, and **From address** were rendered with `_secret()` (`<input type="password">`), so the values were dotted-out and got an unhelpful eye-toggle button. Only the SMTP password should be masked.
- Fix: `web/static/js/app.js` — switched the three fields to plain `<input type="text">` (still XSS-safe via `esc()`); SMTP password remains masked.

## [1.7.4] - 2026-04-27

### Fixed — Schedule changes via Web UI required service restart (critical)

- **Newly-created `auto-verify` (or any custom schedule) never fired**, and edits to existing schedules' cron expressions were ignored, until the service was restarted. `POST /api/schedules`, `POST /api/schedules/{name}/toggle`, and `DELETE /api/schedules/{name}` only wrote to the SQLite `schedules` table — they never told the running APScheduler about the change.
- The "Next run" column in the Web UI is computed live from the cron expression every time the page loads (`api.py::_schedule_to_dict`), so the UI looked correct even though APScheduler had no job registered. This masked the bug.
- `ArchiveScheduler.setup()` only ran once at startup (called from `start()` in the FastAPI lifespan), so the only way to register a new DB schedule with APScheduler was to restart `jt-glogarch.service`.
- Fix: added `ArchiveScheduler.apply_schedule(sched)` and `remove_schedule(name)`. The three schedule API endpoints now call them after the DB write, so changes take effect immediately. `setup()` was also simplified to delegate to `apply_schedule()` for every DB record (DRY) and to bootstrap missing `auto-export` / `auto-cleanup` records from `config.yaml` only on first run.

### Fixed — Custom-named schedules updated wrong `last_run_at` row

- `_run_export`, `_run_cleanup`, `_run_verify` had the schedule name hardcoded (`"auto-export"` / `"auto-cleanup"` / `"auto-verify"`), so a user-named schedule (e.g. `daily-stream-A`) would either skip the timestamp write or stomp the wrong row. `_run_export_once` also loaded its config from the hardcoded `"auto-export"` row, so a custom export schedule silently inherited `auto-export`'s mode/days/streams instead of its own.
- Fix: each handler now takes a `schedule_name` argument; `apply_schedule()` passes the schedule's actual name via APScheduler `args=[sched.name]` so the right row is read for config and updated for `last_run_at`.

## [1.7.3] - 2026-04-19

### Fixed — Export lock leak on early failure (critical)

- **Scheduled exports could get permanently stuck** after a transient failure. If `create_job()` or any operation between `_export_lock[key] = True` and the `try:` block raised an exception (e.g. "database is locked" from SQLite contention), the lock was set but never released. All subsequent retry attempts — and the next day's scheduled run — failed with "Export already running".
- Observed pattern in logs: attempt 1 fails with "database is locked", attempts 2-3 and subsequent scheduled runs fail with "Export already running for 'X'".
- Affected both `glogarch.export.exporter` (API mode) and `glogarch.opensearch.exporter` (OpenSearch mode).
- Fix: moved job creation inside the `try:` block so the existing `finally: _export_lock.pop(...)` always runs, regardless of where the exception originates.

### Improved — Audit server_name fallback to syslog hostname

- When nginx `server {}` block has no `server_name` directive, `$server_name` is empty and all audit records show blank server. jt-glogarch now falls back to the hostname parsed from the syslog envelope (e.g. `log3` from `<190>Apr 19 00:07:15 log3 graylog_audit: {...}`).
- No action required if nginx already has `server_name`; fallback only applies when the JSON field is empty.

## [1.7.2] - 2026-04-17

### Improved — JVM memory guard: pause & resume instead of stop

- API export now **pauses** when Graylog JVM heap exceeds the threshold (default 85%), checks every 30 seconds, and **resumes automatically** when GC recovers. Only stops after 5 minutes of sustained high heap. Previously, export stopped immediately on first threshold breach.
- Progress display shows "JVM heap 87%, paused (waiting for GC)..." during wait.

### Improved — Heartbeat: active probe instead of passive timeout

- Heartbeat no longer alerts simply because no syslog was received for 10 minutes (false positive when nobody is using Graylog). Now sends an active probe through nginx (HTTPS :443) every 5 minutes. Only alerts when the HTTP probe succeeds but no corresponding syslog arrives — indicating nginx forwarding was disabled.
- nginx URL auto-derived from `servers[].url` (same host, HTTPS port 443).

### Improved — Export job UX: accurate totals and skip info

- OpenSearch export now uses `_count` API for accurate document counts instead of `_cat/indices` (which includes deleted/merged docs and overstates the total).
- Completed export jobs show skip info in the notes column: "Skipped 75 indices (already archived)" or "Skipped 4200/4320 chunks (already archived)".
- Interrupted jobs show context: "Interrupted by service restart (502,202 / 1,397,360 processed, partial files cleaned up)".
- Progress detail visible in schedule page (separate line) and sidebar widget.

### Fixed — Schedule "Run Now" export not updating last_run_at

### Fixed — Upgrade script: git safe.directory

- `upgrade.sh` now runs `git config --global --add safe.directory` before `git pull` to prevent "dubious ownership" error when `/opt/jt-glogarch` is owned by `jt-glogarch` user.

## [1.7.1] - 2026-04-16

### Improved — Export progress UX

- **Scanning/dedup phase shows detail text** — OpenSearch export now shows "Scanning 45/88 indices...", "skipped 75/88 indices (archived)", and "querying graylog_515 (4,651,029 docs)..." instead of a blank 0% progress bar. API export shows "skipped 43/4320 (archived)" during dedup skip phase.
- **Polling fallback shows detail** — when SSE is unavailable, the polling-based progress display shows `current_detail` instead of "0/?" during phases with no records yet.

### Improved — Sensitive operation notification dedup

- **Duplicate entries merged** — identical operations in the same batch (same user, operation, target, status) are now merged with a "×N" suffix instead of sending N separate notification lines. Example: 12 identical logout-401 entries become one line with "×12".

### Fixed — Schedule "Run Now" for export not updating last_run_at

- "Run Now" on export schedules now updates the "Last Run" timestamp on completion. Previously only cleanup and verify schedules updated this field.

### Fixed — Scheduled export retry on transient errors

- Scheduled export now retries up to 3 times (30s delay) on transient errors like "database is locked". On final failure, a failed job record is created so it appears in Job History (previously silent failure — only visible in system logs).

### Fixed — Audit cleanup skipped when no archives exist

- `Cleaner.cleanup()` had an early return that prevented audit record cleanup when no archive files matched retention. Refactored so audit cleanup always runs.

### Fixed — Audit retention independent from archive retention

- `op_audit.retention_days` (default 180) now controls audit record cleanup separately from archive retention (default 1095). `upgrade.sh` auto-adds the field for existing installs.

### Fixed — alert.enable / alert.disable classification

- Event definition schedule/unschedule now classified as `alert.enable` / `alert.disable` instead of generic `alert.modify`, so users can distinguish enable vs disable in audit records and notifications.

## [1.7.0] - 2026-04-15

### Added — Operation Audit (Graylog compliance auditing)

Track who did what on Graylog — for compliance auditing. Records full
request body (see exactly what was changed), stored independently
from Graylog (admin cannot delete audit records).

**Architecture:**
- nginx on each Graylog server sends access logs via UDP syslog
- jt-glogarch receives on port 8991, parses, classifies, stores in SQLite
- IP allowlist auto-built from Graylog Cluster API (zero config)
- Whitelist-based filtering: only records meaningful operations (60+ operation types)
- Background polling, static assets, metrics automatically filtered out

**Username resolution:**
- Basic Auth → extract username from Authorization header
- Token auth → resolved via per-user Graylog token API
- Session auth → session ID resolved via Graylog Sessions API
- Cookie session (`$cookie_authentication`) → session ID from nginx log, resolved via API
- Login POST body → extract username → cache by client IP
- Single-user environments → auto-attributed
- Periodic backfill of records without username

**Resource name resolution:**
- Input/Stream/Index Set/Dashboard/Pipeline/Lookup Table IDs → human-readable names
- Cached from Graylog API, refreshed every 6 minutes

**Heartbeat monitoring:**
- Detects silent audit failure (Graylog up but no syslog received)
- Alerts via notification after 10 minutes of silence

**Web UI — "Operation Audit" page:**
- Dashboard-style stat cards with sparkline trends (24h)
- Filterable table (time range, user, method, status, sensitive only)
- Detail modal with JSON syntax-highlighted request body + copy button
- nginx setup instructions with syntax-highlighted config snippet
- Enabled by default; upgrade.sh auto-adds config for existing installs

**Notifications:**
- `on_sensitive_operation` — alert when sensitive operations detected
- `on_audit_alert` — alert when audit pipeline fails (no syslog received)
- Both independently configurable in notification settings

**Security:**
- Session cookie `https_only=True`
- Security headers: X-Frame-Options, X-Content-Type-Options, HSTS, Referrer-Policy
- Notification config secrets masked in API responses
- Login error parameter whitelist validation
- UDP listener DoS protection (batch queue limit, packet size limit)
- SSH command injection prevention (`shlex.quote`)

**Config:**
```yaml
op_audit:
  enabled: true          # enabled by default
  listen_port: 8991
  max_body_size: 65536
  alert_sensitive: true
  retention_days: 180
```

**Documentation:**
- `AUDIT-OPERATIONS.md` / `AUDIT-OPERATIONS-zh_TW.md` — full list of 60+ tracked operations
- `CONFIG.md` updated with `op_audit` section
- `README.md` — nginx setup guide with port 9000 firewall instructions

**Tests:** 17 new tests (parser, username decoding, session auth, sensitive classification, DB operations, notify events).

### Fixed — Operation Audit refinements

- **Removed redundant `search.execute` records** — Graylog search creates two API calls: create/update (contains query) + execute (only `global_override`). Only `search.create`/`search.update` is now recorded. The subsequent `/execute` call is filtered out to avoid duplicate entries.
- **Token auth username resolution** — `GET /api/users` doesn't return actual token values. Added fallback to query per-user `GET /api/users/{username}/tokens` endpoint which returns the real token values. Also added async resolution (`_resolve_token_via_api`) for cache misses.
- **Cookie-based session resolution** — browser sessions use cookies, not Authorization header. Added `$cookie_authentication` to the nginx log format to capture the Graylog session cookie. The listener extracts the session ID from the cookie and resolves it via the Graylog Sessions API. Falls back to IP cache when cookie is not available.
- **External users excluded from detection** — `_get_human_users()` incorrectly filtered LDAP/SSO users (`external=true`), causing single-user default attribution to the wrong account. External users are now included.
- **Search target column showed raw URI** — `search.execute` target_name was empty, causing the UI to fall back to showing the full API URI path. Fixed by removing the redundant execute pattern (query is already captured in `search.create`/`search.update`).
- **Audit table missing server column** — added "Server" column before "User" in the Operation Audit table.
- **Auth service operations not tracked** — added `_KEEP_PATTERNS` for `/api/system/authentication/services/backends` (create/modify/delete/activate/deactivate). Also marked as sensitive operations.
- **Content pack name not resolved** — added content pack caching in `_refresh_resource_cache` from Graylog API. Added UUID-with-dashes URI matching in `_resolve_target_name`.
- **Dashboard name not resolved via /api/dashboards** — unified `_resolve_target_name` to match both `/api/views/` and `/api/dashboards/` paths using the same view cache.
- **Lookup adapter/cache names not resolved** — `_refresh_resource_cache` only cached lookup tables. Added caching for data adapters (`/api/system/lookup/adapters`) and caches (`/api/system/lookup/caches`).
- **Audit retention independent from archive retention** — `op_audit.retention_days` (default 180) now controls audit record cleanup separately from archive retention (default 1095 days). Previously, audit cleanup used the archive retention setting and early-returned when no archives existed.
- **Audit cleanup skipped when no archives to clean** — `Cleaner.cleanup()` had an early return that prevented audit record cleanup when no archive files matched the retention criteria. Refactored so audit cleanup always runs.
- **upgrade.sh auto-adds `retention_days`** — existing installs with `op_audit` config but missing `retention_days` get it added automatically during upgrade.

### Fixed — zh_TW terminology

- 損壞 → 損毀 (Taiwan usage)
- 過濾 → 篩選/篩除
- 對象 → 項目
- README cleanup retention example: 60 天 → 1095 天

## [1.6.2] - 2026-04-15

### Added — Multi-server schedule support

Export schedules can now target a specific Graylog server. Schedule
form has a new "Graylog Server" dropdown. Schedule table shows the
server name badge in the "Server / Mode" column.

### Added — Terminal-style system log viewer

System Logs "Real-time Log" section now has a dark terminal background
with color-coded lines by log level (ERROR=red, WARN=orange,
info=green, INFO=white, DEBUG=gray, systemd=blue).

### Fixed — System log showed "no data" on some hosts

`jt-glogarch` user lacked `systemd-journal` group membership, so
`journalctl` returned empty. Fixed in `install.sh` and `upgrade.sh`.

### Fixed — OpenSearch mode hint missing Data Node warning

The export mode hint text now always mentions that Data Node
environments do not support OpenSearch direct access.

### Fixed — Modal closes on drag outside

All modals now only close via Save/Cancel buttons, not backdrop click
or mousedown-drag-outside.

### Fixed — Missing pause/close icons

Added `pause` and `close` SVG icons to the ICONS map. Schedule table
enable/disable buttons now show play/pause icons. Cancel buttons show
close icon.

### Fixed — Cleanup/verify run-now didn't update last_run_at

Manually triggered cleanup and verify schedules now update the
`last_run_at` field in the database.

### Fixed — TEST-RESULTS.md had ANSI color codes

`run-tests.sh` now strips all ANSI escape sequences with
`NO_COLOR=1 TERM=dumb` + sed filter.

## [1.6.1] - 2026-04-14

### Added — Multi-server schedule support

Export schedules can now target a specific Graylog server instead of
always using the default. The schedule form has a new "Graylog Server"
dropdown that lists all configured servers. The schedule table shows
the server name as a badge next to the export mode.

This enables archiving multiple Graylog clusters from a single
jt-glogarch instance — create one schedule per server.

### Fixed — Modal closes on drag outside

All modals (import, schedule edit, confirm) no longer close when the
user mousedowns inside the modal and drags outside. Modals can only be
closed via Save/Cancel buttons.

### Fixed — Missing icons on enable/disable buttons

Schedule table enable/disable buttons now show play/pause icons.

## [1.6.0] - 2026-04-14

### Fixed — Code review findings

- **Security: XSS in OpenSearch test** — `testOpenSearch()` inserted OS
  cluster_name/version/status into innerHTML without `esc()`. Fixed.
- **Bug: Email channel missing from notify status** — `GET /api/notify/status`
  did not include the email channel. Dashboard showed "no channels"
  when only email was enabled.
- **Consistency: `batch_docs` default mismatch** — CLI help said 5000
  but code used 10000. Fixed help text + JS fallback + CLAUDE.md.
- **i18n: Hardcoded Chinese in statusBadge** — `corrupted` and `missing`
  labels were hardcoded in Chinese. Now uses `t('status_corrupted')` /
  `t('status_missing')`.
- **Memory: `_cancel_flags` never pruned** — Added cleanup alongside
  `_job_progress` pruning (keep last 50) in both export and import paths.

### Added — 11 regression tests (`test_recent_fixes.py`)

Covers: notification timezone, Data Node detection, retention default,
batch_docs consistency, Discord args, schedule display, i18n keys.

## [1.5.9] - 2026-04-14

### Fixed — Schedule table showed "days" for OpenSearch mode without index count

When an OpenSearch-mode export schedule had no `keep_indices` set (e.g.
auto-export), the settings column showed "180 天" which was misleading.
Now shows "180 天 (all indices)" to clarify that it exports all indices
within the time range, not a specific count.

## [1.5.8] - 2026-04-14

### Changed — Default retention from 180 days to 3 years (1095 days)

180 days was too short for most compliance scenarios. Changed default
`retention_days` from 180 to 1095 (3 years) in config, CLI example,
JS fallbacks, CONFIG docs, and config.yaml.example.

## [1.5.7] - 2026-04-14

### Fixed — Notification timestamp showed UTC instead of local timezone

Notifications (Telegram, Discord, etc.) displayed timestamps in UTC
(`2026-04-13 19:23:35 UTC`). Changed to use the system's local timezone
(`2026-04-14 03:23:35 CST`). Applies to both scheduled job notifications
and test notifications.

### Changed — Data Node warning text toned down

Import/export dialog Data Node warning changed from "do not use Data
Node" to a neutral factual statement: "Data Node does not support
OpenSearch direct access. Use API/GELF mode instead."

## [1.5.6] - 2026-04-14

### Added — Graylog 7 Data Node compatibility documentation

Tested jt-glogarch against Graylog 7.0.6 with Data Node 7.0.6
(managed OpenSearch 2.19.3). Key findings:

- **OpenSearch Direct export: NOT supported** in Data Node environments.
  Data Node uses Graylog-managed TLS certificate authentication — no
  credentials are exposed, external tools cannot access OS port 9200.
- **OpenSearch Bulk import: NOT supported** for the same reason.
- **Graylog API export: works normally** (uses Graylog REST API).
- **GELF import: works normally** (sends to Graylog GELF input).
- Graylog API proxy (`/api/system/indexer/*`) only supports limited
  read-only endpoints (health, indices info) — no `_search` or `_bulk`
  passthrough.
- Both READMEs updated with Data Node compatibility row in the export
  mode comparison table + user-facing warning note.
- `GET /api/servers` now includes `has_datanode` flag for UI to detect
  and warn users.

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
