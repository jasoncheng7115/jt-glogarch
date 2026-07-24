# Changelog

All notable changes to jt-glogarch will be documented in this file.

## [1.13.33] - 2026-07-24

### Changed

- **The import progress badge now labels each metric with WHOSE it is.** It
  showed bare `Heap` / `Buffer` / `Mem` with no indication of the source. The
  metrics are now grouped under **"Target Graylog"** (its disk journal, JVM heap
  and output buffer — what the import throttles on) and **"jt-glogarch host"**
  (this machine's free system RAM), each with a hover tooltip explaining it. The
  memory metric is relabelled "Free RAM" for clarity.

## [1.13.32] - 2026-07-24

### Fixed

- **Reports and System Logs shared the same sidebar icon.** Both used the
  horizontal-lines `log` icon. Reports now has its own bar-chart icon (nav item,
  page header, and the Report Definitions section).

## [1.13.31] - 2026-07-23

### Changed

- **OpenSearch-direct export progress no longer regresses on multi-index-set
  runs.** The export now scans/plans EVERY index set up front (phase A) and sets
  one stable total, then exports (phase B). Previously the denominator grew as
  each index set was reached, so the % bar could jump backwards. It's now
  monotonic. (Trade-off: a brief "scanning" phase up front before the first
  archive is written.)
- **Cross-page "select all matching" now selects only COMPLETED archives.** It
  resolves the exact id set via `status=completed` so batch import/delete never
  act on corrupted / missing / in-progress rows, and the count shown reflects the
  true actionable number.

## [1.13.30] - 2026-07-23

### Fixed

Found during a full-application test + logic-review pass:

- **CSP violation on the Archives / Import pages.** The import modal's "Close"
  button carried a static `style="display:none;…"` attribute, which the strict
  `style-src 'self'` Content-Security-Policy blocked (logged a console violation).
  Moved to a CSS rule; JS still toggles visibility via CSSOM (CSP-safe).
- **A malformed/truncated archive header crashed the reader's fallback instead of
  degrading.** `ArchiveIterator`'s metadata fallback constructed
  `ArchiveMetadata()`, but that model has required fields → it raised
  `ValidationError`. It now builds a graceful empty-placeholder metadata.
- **Indexer-failure auto-diagnosis hardened against false field matches.** The
  error-message parser could, in principle, pick a leading `[timestamp]`/`[logger]`
  bracket as the "field" and pin a junk mapping. It now validates the extracted
  token is a plausible field name (rejects timestamps, colons, spaces) and the
  reason parser also recognises CamelCase exceptions.

## [1.13.29] - 2026-07-23

### Fixed

- **Each OpenSearch server row now has its own "Test Connection" button.**
  The dashboard's OpenSearch card listed one row per Graylog server but only had
  a single shared test button (which tested the global config), inconsistent with
  the Graylog servers table where every row has its own button. Now each row
  carries a per-server test button that tests that server's resolved OpenSearch
  cluster (per-server config, or the global fallback). The existing per-host
  right-click test is unchanged.
- **Sorting a table by a URL (or other text) column did nothing.** The client-side
  table sort's numeric detection was too loose: a cell like
  `http://192.0.2.10:9000` was parsed as the number `192.0` for every row
  (parseFloat stops at the second dot), so the comparison was always 0 and the
  rows never reordered. Numeric sorting now applies only when the whole cell is a
  number (with optional thousands separators / size unit); URL, name and auth
  columns sort as text.

## [1.13.28] - 2026-07-23

### Changed

- **Indexer failures during import are now diagnosed and fixed automatically —
  no more "go check Graylog yourself".** Previously a compliance violation just
  reported a count and told the operator to open Graylog's Indexer Failures page.
  Now, when failures are detected, jt-glogarch reads the failure details, parses
  **which field(s) and error type** caused them, and **auto-pins those fields as
  string (keyword) + cycles the index** so a re-import indexes cleanly. The job
  message names the culprit, e.g. *"173 indexer failures on field(s): 'Keywords'
  (×173) [mapper_parsing_exception]. Auto-remediated: pinned 1 field(s) as string
  and cycled the index — re-import to recover the affected messages."*
- **Preventive: numeric values that overflow Java `long` are pinned as string up
  front.** A Windows Event Log `Keywords` 2^63 bitmask (the most common cause of
  restore indexer failures) is now detected at archive-write time and pinned as
  keyword by preflight BEFORE the GELF send, so the failure never happens. (Both
  changes are non-destructive — keyword mapping never alters already-indexed data.)

## [1.13.27] - 2026-07-23

### Added

- **Cross-page "select all matching" on the Archives page.** Previously "select
  all" only ticked the *current* page, so clicking it and Batch Import imported
  just that page (e.g. one day) — easy to mistake for "all pages". Now, after
  selecting a page, a discoverable link appears — **"Select all N archives
  matching this filter"** — that selects every archive matching the active
  filter (server / stream / time range) across all pages in one request, and a
  count confirmation is shown before importing. Set a time range (type or drag
  the timeline), then one click selects the whole range.

### Fixed

- **The hidden Shift+Select-All "all pages" mode ignored the active filter** and
  would have selected the *entire* archive store instead of the filtered subset.
  Cross-page selection is now always scoped to the current filter, and is
  discoverable (no Shift needed).

## [1.13.26] - 2026-07-23

### Fixed

- **The import batch size / rate chosen in the Web UI dialog was silently
  ignored — the import always ran at the config default (batch 500).** Setting
  e.g. "50 per batch / 100 ms" in the import dialog, the running import used 500.
  Root cause: `Importer.import_archives` unconditionally overwrote the
  flow-control object's `batch_size` and `rate_ms` with the config defaults, even
  though the Web UI had already set the user's values on it before passing it in.
  Now the config defaults are only applied when the caller (CLI / scheduled)
  provides no flow control; the Web UI dialog's batch size and rate are honoured.
  The live "Batch" selector during an import (which mirrors the actual running
  value) will now correctly show the chosen size instead of 500. (CLI / scheduled
  imports are unchanged — they still take the batch/rate from config.)

## [1.13.25] - 2026-07-23

### Fixed

- **OpenSearch-direct export progress showed a nonsensical "done of total" and a
  stuck 99% when exporting more than one index set.** The export loops over each
  index-set prefix and was resetting the job's denominator (`messages_total`) to
  only the *current* prefix's document count, while the processed count is
  cumulative across all prefixes. On a multi-index-set export this displayed e.g.
  `214,981,759 of 21,160,634 records` (processed far larger than the total) with
  the bar pinned at 99%. Now the denominator accumulates a **grand total across
  all prefixes**, so processed ≤ total holds for the whole run and the percentage
  is the true overall fraction. **Display-only bug — no data was lost or skipped;
  every index in every index set was always exported.** (Single-index-set exports
  and API-mode export were unaffected.)

## [1.13.24] - 2026-07-23

### Changed

- **The systemd memory cap is now SOFT-only (`MemoryHigh`), never a hard kill.**
  Previously the shipped unit / upgrade drop-in also set a hard `MemoryMax=4G`,
  which would let the kernel OOM-kill jt-glogarch's whole cgroup — and the PDF-report
  Chromium runs in that same cgroup, so a heavy report render could be killed.
  Now only `MemoryHigh=3G` is set: past it the kernel throttles jt-glogarch and
  reclaims its memory (protecting co-located OpenSearch/Graylog and the box) but
  never kills the process. `upgrade.sh` migrates an existing hard-cap drop-in to
  soft-only automatically. This is a backstop only — the real protection is the
  streaming archive reader (import memory stays flat regardless of archive size:
  measured ~47 MB for a 500k-message archive vs ~545 MB for the old full-load) plus
  the import memory guard, both already shipped.

## [1.13.23] - 2026-07-23

### Added

- **"Relieve target Graylog" — a one-click, non-destructive way to unstick a
  wedged target.** When a large import backs up the target Graylog (journal
  piling up, a ring buffer stuck near capacity, or a write index that won't
  accept writes), operators can now relieve it without touching any message
  data. It **cycles the write index** (rotates the deflector so a fresh index
  takes writes) and **rebuilds index ranges** (fixes "data present but Search
  finds nothing"), then shows a before/after snapshot of the journal and
  buffers so you can see it draining. It **never deletes messages, indices, or
  index sets** — a confirmation dialog states this. Available in two places: on
  the **import progress screen** (relieve the import's own target mid-run) and
  next to each server in **Settings** (routine maintenance). New endpoint
  `POST /api/graylog/flush`; a configured server and an ad-hoc import target are
  both supported (import-target secrets reconcile against stored defaults).
- **Release gate now includes a headless-browser UI smoke** (`scripts/ui-smoke.py`):
  a real headless Chromium loads the UI, asserts i18n is wired, switches to
  zh-TW, and HARD-FAILS on any uncaught page/console error. `node --check`
  catches only JavaScript *syntax* errors; this also catches runtime/render
  breakage.

## [1.13.22] - 2026-07-23

### Fixed

- **Critical: the whole UI fell back to English and Settings appeared blank
  (regression since 1.13.20).** A stray apostrophe in a single-quoted i18n string
  (`… the target's buffers …`) was a JavaScript **syntax error** that stopped
  `i18n.js` from parsing — so translations never applied (the page kept its English
  defaults) and JS-rendered pages like Settings failed to render. **No data was lost**
  — `config.yaml` is never touched by this; fixing the string restores the language
  and all settings.
- **New release gate: static JavaScript is now syntax-checked (`node --check`) and a
  broken `.js` HARD-FAILS the release.** The Python test suite never loaded the browser
  JS, so this shipped undetected; it can't happen again.

## [1.13.21] - 2026-07-23

### Fixed

- **Import no longer OOM-kills the box — the archive reader now truly streams.**
  `ArchiveIterator` claimed to stream but actually did `json.load()` on the whole
  archive: a 50 MB `.json.gz` expands to multiple GB of Python objects, so importing
  large archives grew jt-glogarch's memory to ~12 GB and the kernel OOM-killer took
  down jt-glogarch (**"Interrupted by service restart"** at a reproducible message
  count) and/or OpenSearch — especially on the common same-VM deployment. It now
  pulls one message at a time via `raw_decode` and holds only ~one batch (+ a 256 KiB
  window) in memory. **This is the root-cause fix for the import OOM crashes.**
- **Cancel now works on a paused/wedged import.** The journal auto-pause was an
  uninterruptible 30 s sleep, so Cancel did nothing while the import was backed off;
  it now polls the cancel flag every second. The GELF sender also gained connect
  (15 s) and drain (30 s) timeouts — a target whose TCP buffer is full (Graylog
  wedged) used to block the send forever, so the loop could never reach its cancel
  checkpoint. Cancel is now responsive in both cases.
- **Import progress memory leak.** The import progress event list grew unbounded
  (the export path already pruned) — a multi-million-record import ballooned service
  memory. Now capped to the last ~100 events.

### Added

- **Local box-memory guard on import.** jt-glogarch is usually deployed on the SAME
  VM as the target Graylog + OpenSearch, so a big import can exhaust shared RAM and
  trip the OOM killer (which shows as "Interrupted by service restart"). The import
  now reads `MemAvailable` and pauses when free memory is low (`import.mem_pause_mb`,
  default 700 MB; slow at `mem_slow_mb`, default 1400 MB). Free memory is shown live
  next to the journal/buffer/heap badges.
- **Batch delay is now a keyboard-editable number field** (dialog + live view), not
  only a slider — precise entry without dragging. The slider stays, synced both ways.
- **systemd memory cap (defense in depth).** Upgrade/install now add a drop-in
  (`MemoryHigh=3G`, `MemoryMax=4G`) so that even a hypothetical runaway is OOM-killed
  within jt-glogarch's OWN cgroup — it can never take down the co-located OpenSearch /
  Graylog or the whole VM. Adjust for large boxes / heavy report use.

## [1.13.20] - 2026-07-23

### Fixed

- **Import must never wedge the target Graylog.** The throttle now watches the
  **process/output ring buffers** — the earliest sign Graylog can't drain to
  OpenSearch (they fill at ~65K, long before the journal shows a big backlog).
  Buffer ≥ 70% → slow, ≥ 90% → pause. This stops an import from filling the journal
  and jamming Graylog in the first place.
- **Preflight now refuses to start an import into an already-jammed Graylog.** If the
  process/output buffer is ≥ 90% full (OpenSearch not keeping up) the import is
  blocked with a clear message (≥ 70% warns) — so you never start an import that
  would stall and make Graylog worse.
- **JVM-heap throttle no longer false-triggers on a healthy Graylog.** Graylog with
  G1GC idles at 80–95% heap by design, so the old 80/92% thresholds would have
  throttled *every* import. Heap is now a high near-OOM safety net (slow ≥ 95%,
  pause ≥ 98%); the ring buffers are the reliable signal.
- **Import progress memory leak.** The import progress event list grew unbounded (the
  export path already pruned); a multi-million-record import could balloon service
  memory. Now capped to the last ~100 events like export.

Live in the import view: the journal badge now also shows **Buffer%** and **Heap%**
so you can see exactly which signal is throttling.

## [1.13.19] - 2026-07-23

### Fixed

- **Import batch-size dropdown could not be changed (live view).** The new selects
  were being wrapped by the app's custom-dropdown component; interactive selects
  need `class="no-custom"` (as every other `data-act-change` select has). Both the
  dialog and live-view batch selectors are now native and adjustable.
- **Live "Batch Size" label wrapped onto two lines** in the tight control row — the
  live view now uses a short "Batch" / 「批次」 label with no-wrap, and the live
  selector reflects the ACTUAL running batch size instead of showing a stale value.

## [1.13.18] - 2026-07-23

### Fixed

- **Import now pauses when the target Graylog journal is STUCK, not just when it
  overflows.** Previously the throttle only reacted to the absolute backlog
  (slow ≥ 100K, pause ≥ 500K, stop ≥ 1M). Now:
  - **Stuck (not draining):** an elevated backlog that isn't shrinking versus the
    previous sample escalates from *slow* to *pause* — we stop piling on a journal
    Graylog can't commit to OpenSearch.
  - **Journal unreadable mid-import:** if the journal check worked before and then
    fails (target unreachable/erroring), the import pauses (fail-safe) and
    auto-resumes when it recovers — instead of blasting on blind. A target that
    never exposed the journal endpoint is exempt (no deadlock; import runs at the
    user rate with a one-time warning).
  - **Check cadence is message-based (~every 5000 msgs)** instead of a fixed 10
    batches, so a large batch size no longer leaves a big blind window.

## [1.13.17] - 2026-07-23

### Added

- **GELF import: selectable batch size (50 / 500 / 1000 / 2000) in BOTH the import
  dialog and the live in-progress view.** Importing at a small batch is slow; you can
  now pick a starting batch size and change it live mid-import (`/import/{id}/rate`
  already accepted it — the UI just didn't expose it). Default stays 500.
- **Import throttle now also watches the target Graylog's JVM heap**, not just the
  journal backlog. The journal monitor samples `/api/system/jvm` and backs off on the
  more-severe of the two signals (heap ≥ 80% → slow, ≥ 92% → pause), so a fast batch
  can't OOM the target. Heap % is shown live next to the journal badge.

## [1.13.16] - 2026-07-22

### Added

- **Index-set coverage badge on export jobs.** OpenSearch export jobs now show a
  colored chip in Job History and the export result dialog: green **"all index
  sets"** when a run covered everything, or amber **"N index set(s) not covered"**
  (with their names on hover) when a run was restricted. Backed by a new structured
  `result_json` job column (auto-migrated; nullable) so it's not parsed from free
  text — the plain-text note stays too.

## [1.13.15] - 2026-07-22

### Fixed

- **Dashboard now shows EACH server's OpenSearch cluster (multi-cluster).** With
  per-server `opensearch:` blocks, the dashboard's "OpenSearch" section only listed
  the global block's cluster — per-server clusters were invisible, making users think
  those servers ran in API mode. The backend already accepted `?server=`; the
  dashboard now calls it per server and renders one row each, tagged **per-server**
  or **global fallback**. (Archiving was always correct — this was display-only.)
- **`/opensearch/reorder` is now server-aware.** "Set as primary" reordered the
  *global* host list even when you clicked a per-server cluster's node; it now
  reorders the correct server's block.

### Changed

- The OpenSearch node badge is now **"Node 1"** (shown only for multi-node clusters)
  with a tooltip — it marks the first failover node *within a cluster*, which the old
  "Primary" label could be misread as a "primary cluster" in multi-cluster setups.
- **OpenSearch export jobs now record index-set coverage in the job note**
  (`Covered all N index set(s)`, or `⚠ … NOT covered: …`) — previously log-only.

### Added

- **`glogarch schedule add`** — create a schedule from the CLI (previously only
  `list`/`enable`/`disable`, forcing manual SQLite edits). Options: `--type`,
  `--cron`, `--mode`, `--server`, `--days`, `--index-set`, `--stream`,
  `--keep-indices`, `--disabled`. Restart the service to register it.

## [1.13.14] - 2026-07-19

### Fixed

- **Silent data loss: scheduled/Web OpenSearch export only archived the DEFAULT
  index set.** In a multi-index-set Graylog deployment, a scheduled `auto-export`
  (or a Web export) in OpenSearch mode with no explicit index set resolved to *only*
  the default index set (`graylog`). Every other index set was skipped **with no
  error or warning** — its logs were never archived and were permanently lost once
  Graylog retention deleted them. `OpenSearchExporter._resolve_prefixes` now covers
  **all** index sets by default, and logs a WARNING naming any index set a run does
  NOT cover, so a partial export is never silent.
- The global `export.index_sets` config was **ignored** by the scheduler and Web
  export paths (only the CLI honored it). All entry points now read it through one
  helper (`normalize_index_set_ids`).

### Changed — please read before upgrading

- **New default: an OpenSearch export with no index set specified now archives ALL
  index sets** (previously default-only). This is the safe behaviour for an archival
  tool and closes the data-loss gap above. After upgrading, existing schedules with
  a blank `index_set` will start covering every index set; already-archived data is
  de-duplicated, so nothing is re-exported and no migration is needed.
- The `index_set` field now accepts a **single id** (unchanged), a **list of ids**,
  or `"*"` (explicit all). Leave it blank to archive everything, or set
  `export.index_sets` / the schedule's `index_set` to restrict — restricted runs log
  which index sets they skip.

## [1.13.13] - 2026-07-13

### Fixed

- **PDF report — screenshot mode now captures every dashboard tab.** A Graylog
  dashboard with multiple tabs (states) was screenshotted as only its first/active
  tab; the other tabs never appeared in the report. Screenshot mode now switches to
  each tab and renders one page per tab (titled `Dashboard｜Tab`), matching the
  rebuild mode's per-tab behaviour. Tabs are selected by their `data-tab-id`
  (= Graylog state_id), and tabs that Graylog collapses into the overflow "More
  Dashboard Pages" dropdown are opened and captured too. When the report selects
  specific tabs, only those are captured; otherwise all tabs are.
- **PDF report cover — English metadata now column-aligns.** On the cover, the
  `Generated: / Issued by: / Source: / Generated by:` values were ragged in English
  because the labels differ in width (they happened to align in Chinese only because
  every label is four characters). The label now sits in a fixed-width column so the
  values line up in any language.

## [1.13.12] - 2026-07-12

### Fixed

- **Full-width punctuation in Traditional-Chinese docs & UI strings.** Half-width
  commas / semicolons / colons that sat next to Chinese characters (in the zh-TW
  CHANGELOG, README, CONFIG, TESTING, AUDIT docs, the docs site, and i18n.js UI
  strings) are now full-width per the project convention. Digit-grouping commas
  (e.g. `1,234`) and punctuation inside code spans/blocks are left as-is.

## [1.13.11] - 2026-07-12

### Changed

- **Screenshot-mode reports reuse the server's own web login.** Screenshot mode
  drives a real browser through Graylog's Web UI login form (username + password)
  — an API token can't authenticate a browser session, which is why it needs web
  credentials. The report now falls back to the **server connection's**
  username/password when the report's web fields are blank, so you only fill them
  in when that connection was set up with an **API token** (no reusable password).
  A note in the dialog explains this.

## [1.13.10] - 2026-07-12

### Fixed

- **Screenshot mode: dashboard slices no longer cut through a widget.** The
  page-break snap relied on pixel brightness, but a data table's internal white
  rows look identical to a real inter-card gutter, so a cut could land mid-widget
  (continued on the next page). Now `capture_dashboard_png` reads the actual
  widget-row boundaries from the rendered grid (`.react-grid-item` positions) and
  `slice_tall_png` cuts on those — a widget that would overflow the page moves
  WHOLE to the next page. (Pixel-gutter heuristic kept as a fallback.)

## [1.13.9] - 2026-07-11

### Fixed

- **Screenshot mode: no more near-empty page before a dashboard capture.** The
  first screenshot slice (`slice_tall_png` first_ratio) was measured too tall
  (~643pt) — the section title + slice + margins tipped just over one A4 page, so
  the slice broke to the next page and left the title alone on a near-empty page.
  Reduced first_ratio 1.28 → 1.15 so the title and first slice share the page.

## [1.13.8] - 2026-07-11

### Changed

- **"Verify report integrity" dialog restyled.** The SHA-256 label now sits on
  its own line above the hash, the hash renders in a bordered box with the copy
  button pinned to the right, and the hint / command / note are evenly spaced —
  instead of the label, wrapping hash, and orphaned copy button crowding one row.

## [1.13.7] - 2026-07-11

### Fixed

- **Table column headers now have vertical dividers between them** (like
  Graylog). 1.13.6 added the horizontal header/body line by mistake; this adds
  the actually-requested vertical separators between adjacent column headers.

## [1.13.6] - 2026-07-11

### Fixed

- **World map: the remaining northern band is gone.** Beyond the two thin strips
  removed in 1.13.5, the bundled map path had a full-width horizontal run *woven
  into Russia's outline* that filled as a band across the top. The cleaner now
  drops such interior horizontal runs and **splits the sub-path at the gap** (pen
  lifts, no reconnection line) — so the band disappears while Russia and every
  other landmass stay intact.
- **Table column-header separator is now clearly visible** (darker 2px grey; the
  previous line was too faint to read).
- **Sidebar live-progress: a separator line between concurrent jobs.** With an
  export and a report running at once the two entries were stacked flush together
  and hard to tell apart; consecutive jobs now have a divider.

## [1.13.5] - 2026-07-11

### Fixed (report fidelity + UI)

- **World map: stray horizontal lines removed.** The bundled world SVG is one
  concatenated path containing two full-width, ~1px-thin *filled* strips
  (digitization artifacts at ~71°N and ~16°S) that rendered as lines across the
  whole map. They're now stripped by geometry at load time; country borders kept.
- **Wide message-list widgets are no longer dropped from the report.** A message
  list with more fields than `message_max_cols` (UI default 8) used to be omitted
  entirely; it now renders truncated to the first N columns with a "N more
  column(s)" note, so the block always appears like on the dashboard.
- **Pie/doughnut on-slice % labels pick black or white per slice** by luminance
  (threshold 150), matching Graylog, instead of always white.
- **Table column headers get a clear separator line** under the header row (was a
  near-invisible light border), matching Graylog.
- **Sidebar live progress shows every running job.** With an export and a report
  running at once, both now appear (previously only the most recent). A report has
  no incremental progress, so it shows an indeterminate "running" bar instead of a
  stuck 0%.

## [1.13.4] - 2026-07-11

### Fixed

- **Report time-series charts rendered with an empty left half (real root
  cause).** The bug was a grid-alignment error, not the effective-range ratio the
  1.13.2 clamp targeted: when a widget's first data bucket rounds a little BEFORE
  `eff_from` (bucket boundaries vs the query's odd-second start — the *common*
  case, even at ratio 1.0), the alignment index went negative and the fill grid
  started one bucket *after* the first data bucket. The fill loop then matched
  nothing and dumped every real bucket at the end, so a 24h chart became a 48h
  axis with all data shoved to the right. Fixed by clamping the alignment index to
  ≥0 so the grid never starts past the first data bucket. Verified end-to-end: the
  firewall "事件趨勢" chart now fills the full 24h like Graylog.

### Added

- **Clickable table of contents.** Each TOC entry (title → its page number) is now
  a GOTO link that jumps to the section, and the PDF gets outline bookmarks for
  the viewer's sidebar navigation.

### Changed

- **Cover "產製來源" Graylog version uses half-width parens with a leading space**
  in both languages, e.g. `log4 (Graylog 7.1.2)`.

## [1.13.3] - 2026-07-11

### Fixed

- **PDF report renderer could crash on memory-constrained hosts.** The 1.13.1
  legend fix set `.chart-wrap` to `height:auto; min-height` — but with Chart.js
  `maintainAspectRatio:false` that makes the canvas and its container grow each
  other in a loop until the headless Chromium renderer OOM-crashes
  (`Page.set_content: Page crashed`). Reverted to **definite** heights; the
  many-series legend still gets a taller definite tier (`.legend-heavy`, 110mm),
  so legends render in full without the sizing loop. Verified end-to-end against
  a live dashboard.

## [1.13.2] - 2026-07-11

### Fixed

- **Time bar no longer renders half-empty (issue #3).** When a widget's
  `effective_timerange` is far wider than its actual data (confirmed on live
  dashboards: normal widgets show eff≈data, but a sparse widget hit 19× its data
  span), the report filled the whole window with empty buckets while Graylog
  auto-ranges its axis to the data extent. The time-bucket fill now clamps to the
  data extent (+ one bucket margin) when the effective range exceeds 3× the data
  span; normal widgets (ratio ~1) are unaffected and interior empty buckets still
  render.

## [1.13.1] - 2026-07-11

### Fixed (PDF report fidelity — widget-by-widget audit)

- **Legend no longer clipped.** Chart cards use `min-height` (not a fixed height)
  and a taller `.legend-heavy` tier for charts with >15 series, so a stacked
  chart's full legend renders instead of the last rows being cut off.
- **Heatmap fills the page.** Row/column caps raised from 15/20 to 26/30
  (page-fit) so the grid isn't left half-empty when there's room and data.
- **Heatmap colour scales.** Added the missing Graylog/Plotly scales (Cividis,
  Greys, Reds, YlGnBu, Earth, Picnic, Rainbow, Blackbody) so a widget's chosen
  `color_scale` renders faithfully instead of silently falling back to Viridis;
  an unrecognised scale is now logged. Empty heatmap columns honour the widget's
  "Skip Empty Values" (or render as "(Empty Value)").
- **Bar mode mirrored on single-series non-time bars** (reads the widget's
  `barmode` like multi-series bars already did).
- **Scatter keeps Graylog's row order** (no longer numerically re-sorted).
- **Empty pivot values labelled "(Empty Value)"** in pie/bar/line and table
  column headers, matching Graylog.
- **Tables:** column-pivot cap raised 12 → 30; a "showing first N" note when rows
  are truncated; message-list columns now get numeric/date-aware alignment and a
  localized truncation note; date-typed metrics render even when the date-field
  set is empty; message timestamps fall back to epoch parsing.
- **Time-axis day-boundary labels** render on two lines (time over date) like
  Graylog, via a Chart.js multi-line tick callback.
- **Geo map:** distinct bubble sizes when all counts are zero; skipped
  coordinates are logged.
- Diagnostic logging added for the "time bar left-half-empty" case (a legit
  wide-range widget can be 5× its data span, so no blind axis clamp was shipped —
  a precise fix follows from live data).

## [1.13.0] - 2026-07-11

### Changed

- **Setup wizard reordered — the local admin account is now the LAST step.**
  New order: (1) Graylog server, (2) OpenSearch (optional), (3) archive path,
  (4) backup admin account, (5) done. The admin step is reframed as a *backup*
  login (you normally sign in with your Graylog account; `localadmin` works even
  when Graylog is unreachable). Because the password is no longer first, steps
  1-3 write config under a pre-auth **setup session** (`setup_mode`, granted by
  `GET /setup` on a still-unconfigured box and honoured by the auth middleware
  only for the wizard's config endpoints); the admin-password step authenticates
  the session and closes it. Mid-wizard reloads, session loss (falls back to
  Graylog login), and existing-install upgrades (never see the wizard) all
  handled.

### Added

- **New report: single Graylog server is pre-selected.** When adding a report
  and only one Graylog server is configured, it is chosen by default and its
  dashboards load immediately (no more starting on a blank "-").

## [1.12.10] - 2026-07-11

### Fixed

- **`localadmin` could not log in while Graylog was reachable.** The setup
  wizard makes the local admin password a mandatory first step, but login
  treated `localadmin` as an emergency-only account that was accepted *only*
  when every configured Graylog server was unreachable — so once a Graylog was
  configured and up, the wizard password was silently rejected. The local admin
  is now a first-class login: it is checked **before** Graylog and works
  regardless of Graylog reachability, and the reserved `localadmin` username is
  never forwarded to Graylog (a wrong password fails directly instead of being
  proxied).

## [1.12.9] - 2026-07-11

### Fixed

- **Sidebar live-progress indicator never appeared during a running
  export/import.** The element ships with the `hidden` class
  (`display:none !important`), but `checkRunningJobs()` only set an inline
  `display:block`, which cannot override an `!important` rule — so the indicator
  above the language switcher stayed invisible. It now toggles the `hidden`
  class directly.

## [1.12.8] - 2026-07-10

### Fixed

- **`install-report-engine.sh` works on Ubuntu 24.04 / Debian 12+.** It failed
  with `error: externally-managed-environment` (PEP 668); it now auto-adds
  `--break-system-packages` when the marker is present and retries with
  `--ignore-installed` if a dependency is distro-managed. It also installs the
  **full report engine** (Playwright **+ PyMuPDF + Pillow**), not just Playwright,
  so post-processing (TOC/watermark) and image slicing work.

## [1.12.7] - 2026-07-10

### Changed / Added

- **Setup wizard: the OpenSearch host example follows the Graylog host** entered
  in the previous step (same host/FQDN, port 9200) instead of a fixed placeholder.
- **Dashboard: the OpenSearch "Not configured" note explains it's optional** —
  archiving falls back to Graylog API mode when OpenSearch isn't set (shown as a
  muted note, not an alarm).
- **Reports: the "render engine not installed" warning has a "How to install"
  button** that opens a modal with the exact install command
  (`install-report-engine.sh`).

## [1.12.6] - 2026-07-09

### Fixed

- **Buttons use SVG icons, not emoji/text symbols.** The audit pagination
  buttons (`←`/`→`) and the copy-confirmation checkmark (`✓`) were literal Unicode
  characters; they now use the same SVG icon set as the rest of the app (added a
  `check` icon).

## [1.12.5] - 2026-07-09

### Setup wizard

- **Auth-method dropdown text is no longer clipped.** The native `<select>` was
  cutting off the tops of CJK glyphs (`API 權杖`); it now has an explicit height
  and line-height.
- **Buttons show icons** (Test / Back / Next) like the rest of the app.
- **No pre-created config.yaml.** A fresh install no longer writes a bootstrap
  config; with no config file the app loads defaults, launches the setup wizard,
  and writes `/opt/jt-glogarch/config.yaml` when you save. Missing config keys
  fall back to defaults.

### Changed

- **zh-TW terminology: 日誌 → 記錄** across the UI, sample report, and docs.

## [1.12.4] - 2026-07-09

### Fixed

- **Setup wizard no longer deadlocks after setting the password but abandoning
  the wizard.** If you set the admin password but closed the wizard before adding
  a server, reopening it returned to step 1 (still unconfigured) but rejected the
  password with `Admin password already set` (403) — an inescapable loop. While
  still unconfigured the password may now be re-submitted; the hard 403 gate still
  closes the moment a server is configured.

### Fixed (PDF Reports)

- **Empty-value chart series no longer shows a blank legend entry.** A column-pivot
  series whose value is empty rendered as a colour swatch with no text; it is now
  labelled `(Empty Value)` like Graylog (still dropped when the pivot's "Skip Empty
  Values" is on).
- **Data-table columns stay aligned when a row-pivot value is null.** A null
  trailing row-pivot value (e.g. an empty `source`) is dropped from Graylog's row
  key, which shifted every metric value one column to the left (the count landed in
  the `source` column). The row key is now padded to the number of row-pivot
  columns, so values line up with their headers.

## [1.12.3] - 2026-07-08

### Fixed

- **Service no longer crashes on a config with an empty/commented-out top-level
  key.** A `servers:` (or any top-level key) left empty in YAML parses to `null`,
  which the newer pydantic rejects for a typed field (`Input should be a valid
  list`). `load_settings` now drops `null` top-level keys so the model applies its
  default (e.g. `servers` → `[]`). This also unblocks the first-run setup wizard on
  a freshly-copied example config.
- **Recovery after an OS/Python major upgrade (e.g. Ubuntu 22.04 → 24.04).** When
  the system Python changes (3.10 → 3.12), previously-installed packages live under
  the old version and the service fails with `ModuleNotFoundError: No module named
  'glogarch'`. `install.sh` / `upgrade.sh` now retry the dependency install with
  `--ignore-installed` when pip aborts on a distro-managed package (`Cannot
  uninstall <pkg>, RECORD file not found …installed by debian`), so re-running the
  installer cleanly reinstalls under the new Python.
- **Setup wizard secret fields now have a show/hide toggle.** The API token /
  password fields in the first-run wizard were plain masked inputs with no way to
  reveal them — you couldn't confirm a pasted token was complete. They now have the
  same eye toggle as the main settings page.
- **Example config uses placeholder IPs** (no real host addresses), and its
  `servers:` entry is a valid list.

## [1.12.2] - 2026-07-08

### Fixed

- **Report email field labels align** — the zh-TW report-delivery email labels
  (報表 / 產製時間 / 檔案) are now all four characters wide (報表名稱 / 產製時間 /
  檔案名稱) so they line up cleanly.

## [1.12.1] - 2026-07-07

### Fixed

- **Tampered archives are labelled distinctly in notifications.** A `TAMPERED`
  (keyed HMAC mismatch) result was reported as generic "Corrupted" in the
  verify-failed alert — underselling a security event. It now has its own line
  (`🚨 TAMPERED (HMAC mismatch): N`), listed first, separate from `Corrupted` and
  `Missing`.
- **Tests can no longer send real notifications.** An autouse test fixture mutes
  the high-level `notify_*` senders, so a test run (e.g. the integrity/verify
  tests) can never fire an actual Telegram/Discord/etc. alert.

## [1.12.0] - 2026-07-07

### Added — optional archive tamper-evidence (HMAC), opt-in

A new **optional** integrity layer (default OFF) that detects deliberate
tampering, not just corruption. Plain SHA256 only catches change relative to the
stored value — anyone who can edit both the archive file AND the DB checksum can
forge a consistent pair. This adds a **keyed HMAC-SHA256**: without the secret
key an attacker cannot produce a valid MAC for altered content, so editing the
file + DB no longer passes verification.

- **Key handling** (pluggable): env `JT_HMAC_KEY` (base64/hex) takes precedence,
  else `integrity.hmac_key_file` (default `/opt/jt-glogarch/.hmac_key`, mode
  0600). For protection even against a root/service attacker, don't store the key
  file — supply it via env only at seal/verify time and keep the ledger off-box.
- **Independent ledger**: each sealed archive's `(path, sha256, hmac, size,
  sealed_at)` is recorded in an `integrity_ledger` table; `glogarch
  integrity-manifest` exports it for off-box safekeeping so a privileged attacker
  who rewrites both the files and the DB can still be caught against the copy.
- **Verify detects tampering**: `glogarch verify` (and scheduled verify) reports
  a distinct **`TAMPERED`** status (keyed HMAC mismatch) separate from
  `CORRUPTED` (SHA256), with a red badge in the UI and a notification.
- **New CLI**: `integrity-init` (generate the key), `integrity-seal` (seal
  existing archives — attests from now on, can't prove the past),
  `integrity-manifest` (export the ledger).
- Fully **no-op when disabled** — existing behaviour (SHA256 only) is unchanged.

## [1.11.1] - 2026-07-07

### Changed

- **Data Node locks the mode instead of just warning.** When the selected export
  server is a Graylog Data Node (which doesn't expose OpenSearch), the export mode
  is now forced to Graylog API and the **OpenSearch Direct option is disabled**
  (not merely flagged with a warning). Likewise the import dialog **disables Bulk
  and forces GELF** in a Data Node environment. This removes the footgun of
  picking a mode that can't work on Data Node. Standalone-OpenSearch servers are
  unaffected (both modes stay available).

## [1.11.0] - 2026-07-07

### Import (restore) dialog

- **Close / background / done buttons.** The import dialog now has a header ✕, a
  "Close (keep running)" button while an import is in progress (the import keeps
  running in the background; reopen from the sidebar running-job indicator), and
  an explicit Close button once it finishes.
- **Cancel is responsive.** Cancelling now takes effect during pre-flight too
  (credential/health/mapping/cycle/wait steps), not only during the message send
  loop — previously a cancel during pre-flight looked like it did nothing. The
  job is recorded as *cancelled* (not failed), and the button gives immediate
  "cancelling…" feedback.
- **Pre-set restore target in Settings.** A new "Restore Target Defaults" block
  in 系統設定 stores the GELF host/port/protocol + Graylog API URL + token (or
  username/password). When set, opening the import dialog auto-fills these
  fields so you don't retype the target every time; secrets stay server-side
  (masked in the UI, substituted at import time).

### PDF Reports (beta) — adversarial widget-fidelity pass

A per-widget-type audit against Graylog drove a broad set of rendering fixes:

- **Time charts are chronological and continuous.** Time-bucketed bar/line/area
  widgets are sorted by time and zero-filled across the widget's full effective
  range, so empty buckets show (data clustered at one end) exactly like Graylog
  — instead of the sparse buckets being reordered/compressed.
- **Empty widgets render empty.** An empty aggregation/table no longer emits a
  phantom value (e.g. a stray "443") from a roll-up/total row; a non-count
  single-number metric with no data shows "(no data)" rather than "0".
- **Pie/doughnut:** percentage labels on slices (shown only where they fit),
  top-N + "(Others)" so percentages match Graylog, left-aligned legend.
- **Line vs area:** honour the widget's interpolation (linear/spline/step) and
  fill; multi-series area now stacks like Graylog.
- **Bars:** single-series bars keep Graylog's configured order (no value re-sort);
  multi-series bars honour the horizontal toggle (time bars stay vertical).
- **Data tables:** column-pivot columns keep Graylog's order (grouped by pivot
  value, series order), not alphabetical.
- **Message list:** the message column isn't duplicated when shown as a preview row.
- **Heatmap:** reverse scale, empty-cell default fill, and z-min/z-max colour
  normalisation are honoured.
- **Single-number:** date-typed metrics render as datetimes; trend deltas format
  in the widget's unit.
- **Scatter** widgets render as points instead of falling back to a line/bar.
- **Per-widget snap-to-midnight.** "Use each widget's own time range" and "snap
  to 00:00" now work together: each widget keeps its own duration but its window
  ends at today 00:00 (only whole-day durations snap; e.g. a "last 2 hours"
  widget is left as-is).

## [1.10.13] - 2026-07-06

### Deployment — works behind a corporate TLS proxy / broken CA store

- **`install.sh` and `upgrade.sh` now handle TLS-interception proxies and a
  missing system CA store** instead of dying on a raw `git`/`pip` error. Real
  field case: `git pull` failed with `server certificate verification failed.
  CAfile: none` on a host where `curl` worked — the system `ca-certificates`
  bundle was missing.
  - On a certificate-verification failure the upgrade now stops with a clear,
    actionable message offering three fixes: repair `ca-certificates`
    (recommended), trust the corporate proxy's root CA (secure), or re-run with
    an explicit flag.
  - New opt-in flags on **both** scripts (also `JT_CA_BUNDLE` / `JT_INSECURE`
    env): `--ca-bundle <file>` verifies against a custom CA (e.g. the proxy root
    CA) — the secure choice — and `--insecure` skips TLS verification for that
    run (the equivalent of `curl -k`, with a loud warning). Both are applied
    consistently to `git`, `pip`, `curl` and Playwright/Node.
- **Upgrades can no longer hang.** `git` is forced non-interactive
  (`GIT_TERMINAL_PROMPT=0`) and `git pull` is wrapped in a timeout, so a proxy
  that demands credentials or black-holes the connection produces a fast, clear
  failure instead of a stuck terminal.
- A TLS/CA failure is now distinguished from a local-changes conflict, so the
  auto-stash retry path is only taken when it can actually help.

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

- Telegram/Discord/Slack/Teams/Nextcloud Talk/Email "import complete" messages always showed `Duration: 0s` / `耗時: 0s`, regardless of the actual run length. A real-world batch test on 192.168.1.20 imported five archives of 502 / 26,221 / 31,769 / 131,944 / 373,258 records taking 12 / 14 / 18 / 32 / 102 seconds respectively — every notification still said `0s`.
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
