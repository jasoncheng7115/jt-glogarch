# jt-glogarch Testing Checklist

**Language**: **English** | [繁體中文](TESTING-zh_TW.md)

This checklist must pass before every release. Run `pytest` from the project root.

> **JS syntax gate (mandatory):** the Python suite never loads the browser JS, so a
> syntax error in `web/static/js/*.js` (e.g. an apostrophe inside a single-quoted
> i18n string) ships undetected and breaks the whole UI (falls back to English,
> Settings renders blank). `scripts/run-tests.sh` runs `node --check` on every JS
> file and HARD-FAILS the release on error. Always `node --check` after editing JS.
>
> **Headless UI smoke (mandatory):** `node --check` catches *syntax* errors only.
> A real headless Chromium must also load the running UI and confirm it renders —
> `scripts/ui-smoke.py` loads the login page, asserts `typeof t === 'function'`,
> switches to zh-TW, and fails on ANY uncaught `pageerror`/console error. Point it
> at your live deploy target (credential-free pre-auth checks catch the i18n class;
> pass `localadmin` creds for the post-login Settings-renders check):
> ```bash
> python3 scripts/ui-smoke.py https://192.0.2.36:8990            # pre-auth
> python3 scripts/ui-smoke.py https://192.0.2.36:8990 localadmin '<pw>'  # +Settings
> ```
> `run-tests.sh` runs this automatically against `UI_SMOKE_URL` (default
> `https://localhost:8990`) and HARD-FAILS on a broken UI. **Every release must show
> both `JS syntax check: OK` and `UI smoke (...): OK` before push.**

```bash
# run against a live instance so the UI smoke has a target
UI_SMOKE_URL=https://192.0.2.36:8990 ./scripts/run-tests.sh
```

---

## Rule 0 — the checklist grows with the product (MANDATORY)

**Every new feature or behaviour change MUST update this checklist in the same
release**: add the item that would catch its breakage, extend the matching
script (`ui-sim-test.py` for UI flows, `e2e-archive-test.sh` for data paths,
`test_static_sweeps.py` for a new failure class), and note WHY (which bug
class it guards). A feature without a checklist entry is effectively
untested — that is exactly how the bulk-import OOM survived many releases.
Reviewers: reject any feature change that does not touch this file.

## One-command release check

```bash
UI_URL=https://<staging>:8990 UI_USER=localadmin UI_PASS=... \
GL_HOST=<graylog-ip> GL_USER=admin GL_PASS=... \
GL_SSH=root@<graylog-ip> REPO=<git-clone> \
bash scripts/release-check.sh        # ALL PASS = ok to ship
```

Layers it runs, and the shipped bug class each one exists for:

| # | Layer | Command | Guards against |
|---|-------|---------|----------------|
| 1 | Static + unit gates | `./scripts/run-tests.sh` | JS syntax (broken i18n.js shipped 2 releases); undefined identifiers (dead Cancel button); pytest incl. static sweeps (unimported names, import shadowing, i18n gaps, XSS-unescaped errors, silent-except ratchet) and perf regressions (45 s/run dedup, 7%-of-a-core polling) |
| 2 | Browser simulation | `scripts/ui-sim-test.py` | every page + zh/en switch renders with zero JS errors; import dialog autofill; custom dropdown PAINTS (options existed while the user saw blank); danger section collapsed; settings suggestion contracts |
| 3 | Real-click actions | `scripts/ui-cancel-test.py` | the layer below lied three times: class vs route, `<option>` vs painted skin, syntax vs runtime. Asserts modal opens, job stops, status = `cancelled` |
| 4 | Live report machinery | `scripts/report-bigrange-test.py` | live-schema mismatches units cannot see (coarsening and slicing silently never fired while every unit test was green) |
| 5 | Archive round-trip | `scripts/e2e-archive-test.sh` ON the Graylog host | the 7 data-path steps incl. bulk (whole-file OOM survived many releases untested), dedup/gap refill, self-heal, clear-then-import |
| 6 | Upgrade compatibility | `REPO=... scripts/upgrade-compat-test.sh` | the three upgrade principles; MANDATORY for any schema / config-default / scheduler change |

Manual items that cannot be scripted are in the sections below (ZAP scan for
larger releases, eyeballing UI changes, reading the actual notification text,
customer-facing docs). `RESULT/RELEASE CHECK: ALL PASS` on all six layers plus
the manual sections below = ship.

## Automated Tests (~485 tests)

### Unit Tests

| # | Test File | Tests | Covers |
|---|---|---|---|
| 1 | `test_audit.py` | 28 | Audit parser (username decode, classify, sensitive, noise filter, syslog/JSON parse, process_raw_entry), config defaults/custom/YAML/missing/no-section, DB insert/list/stats, token resolve, cleanup with audit-specific retention, cleanup fallback, notify event |
| 2 | `test_sanitize.py` | 10 | Password/token/URL/JSON/Basic Auth/Bearer redaction, truncation, no false positives |
| 3 | `test_local_admin.py` | 9 | SHA256 hash, `localadmin` username required, Graylog-rejects-no-fallback, Graylog-down-with/without-hash, backward compat |
| 4 | `test_upgrade_script.py` | 9 | upgrade.sh exists + 5 steps, root check, version display, README refs, systemd default=Yes, git clone sudo, retention_days migration, op_audit retention_days default |
| 5 | `test_repo_structure.py` | 8 | pyproject.toml at root, no src/ dir, deploy files, README/CHANGELOG/CONFIG exist, version sync, github/glogarch matches source |
| 6 | `test_bulk_import.py` | 7 | Reserved field stripping, deflector alias, stream rewrite, marker field, dedup id/none |
| 7 | `test_notify_format.py` | 23 | Status emoji (✅/⚠️/❌), per-line format, URL shortening, en/zh-TW key parity, column alignment by display width, full-width colons, Telegram HTML escaping, overflow local-time |
| 8 | `test_notify_test_endpoint.py` | 8 | Discord/Slack/Teams/Telegram/Nextcloud Talk/Zulip/Email send function params, the one shared channel list calls each correctly |
| 9 | `test_field_schema.py` | 6 | Plain JSON passthrough, zlib round-trip, None/corrupted handling, DB store+read |
| 10 | `test_multi_server.py` | 6 | Multi-server config, get-server-by-name, scheduler reads server, UI server selector, JS save/load server |
| 11 | `test_database_datetime.py` | 5 | Naive/UTC/+08:00 round-trip, None passthrough, offset string parsing |
| 12 | `test_import_lock.py` | 5 | Claim/conflict/release/wrong-owner/reclaim |
| 13 | `test_db_rebuild.py` | 5 | Dry-run, actual rebuild, skip existing, backup, prune |
| 14 | `test_preflight_conflicts.py` | 4 | Intra-archive conflict, cross-conflict with actual mapping, string-only not pinned, mixed scenario |
| 15 | `test_config.py` | 4 | Default settings, search paths `/etc/jt-glogarch/`, file loading, WebConfig localadmin |
| 16 | `test_upgrade.py` | 4 | Old DB auto-migration, old config backward compat, archives survive upgrade, DB backup validity |
| 17 | `test_api_error_handling.py` | 4 | Graylog API 401/502/unreachable error handling for /api/index-sets and /api/streams |
| 18 | `test_cli_commands.py` | 3 | All 16 commands registered, hash-password help, root warning logic |
| 19 | `test_cleanup_race.py` | 3 | Grace constant = 600s, recent file skipped, old file not skipped |
| 20 | `test_storage_ownership.py` | 3 | Root chown fix, non-root error, scoped to base_path only |
| 21 | `test_health_endpoint.py` | 2 | Response structure (status/version/checks/issues), public path (no auth) |
| 22 | `test_recent_fixes.py` | 11 | Notification timestamp local tz, test endpoint tz, retention default 3yr, Data Node detection/warning i18n/import modal/export mode, schedule OpenSearch display, config example retention, Discord/test endpoint correct args |
| 23 | `test_opensearch_client.py` | 1 | `_doc` sort tiebreaker (not `_id` — circuit breaker fix) |
| 25 | `test_config_writer.py` | 5 | Atomic config write (temp+`os.replace`), preserves untouched top-level keys, missing-file bootstrap, failure leaves original intact + no temp left, `reconcile_secret` keeps stored value when masked/empty |
| 26 | `test_settings_api.py` | 10 | Fresh-install → `/setup` redirect, config endpoints require auth (401), setup password min-length, setup flow + gate closes (403 once configured), server secret masking + reconcile, delete reassigns default, OpenSearch save/mask, login with empty servers never 500, **upgrade** existing-servers skip wizard, **upgrade** partial edit preserves untouched fields + top-level keys |

### Integration Tests

| # | Test File | Tests | Covers |
|---|---|---|---|
| 24 | `test_integration.py` | 6 | Real OpenSearch cross-conflict detection, zlib schema in full preflight pipeline, timezone dedup/retention/coverage-ratio correctness, archive write-SHA256-read integrity |

---

## Pre-Release Manual Checklist

Run these after all automated tests pass:

### Version Consistency

- [ ] `glogarch/__init__.py` has the new version
- [ ] `scripts/check-version.sh` passes
- [ ] README titles: `# jt-glogarch vX.Y.Z` (both EN + zh_TW)
- [ ] README badges: `version-X.Y.Z-green` (both)
- [ ] CHANGELOG has new version entry (both EN + zh_TW)
- [ ] `CLAUDE.md` version updated

### GitHub Repo Structure

- [ ] `github/pyproject.toml` exists at root (not in `src/`)
- [ ] `github/glogarch/` exists at root (not in `src/`)
- [ ] `github/glogarch/__init__.py` matches source version
- [ ] No `github/src/` directory

### Documentation

- [ ] New features documented in README (both EN + zh_TW)
- [ ] CONFIG.md / CONFIG-zh_TW.md updated if config fields changed
- [ ] AUDIT-OPERATIONS.md / AUDIT-OPERATIONS-zh_TW.md updated if operations changed
- [ ] No half-width commas in zh_TW CJK context
- [ ] No half-width colons/semicolons in zh_TW CJK context
- [ ] zh_TW uses Taiwan Traditional Chinese terminology
- [ ] Upgrade instructions in README are current
- [ ] **License references are consistent** — `LICENSE` is the verbatim GNU AGPL
      v3 text (title + Section 13 "Remote Network Interaction" + copyright
      notice), and every reference agrees: `pyproject.toml`
      (`license = "AGPL-3.0-or-later"`), both README badges/headers/footers, and
      both docs pages (en / zh-TW). Third-party dependency licenses in
      `THIRD-PARTY-LICENSES.md` keep their own terms (v1.13.84)

### Deployment Verification

- [ ] `pip install --force-reinstall --no-deps /opt/jt-glogarch` succeeds
- [ ] `systemctl restart jt-glogarch` — service starts
- [ ] `curl -sk https://localhost:8990/api/health` returns new version + healthy
- [ ] Login page shows correct version
- [ ] `/openapi.json` shows correct version
- [ ] Deploy to .36 staging — health returns new version

### Archive Round-Trip — MANDATORY every release

This is a **hard release gate**: a green `pytest` run does NOT prove the export /
import pipeline works — the unit suite is mocked. A release is not "done" until this
prints `RESULT: ALL PASS`.

> First install the **current build** on the test host
> (`pip install --force-reinstall --no-deps ...`) and confirm
> `python3 -c "import glogarch; print(glogarch.__version__)"` shows the release
> version — otherwise you are testing stale code.

Run the real end-to-end archive pipeline against a live Graylog + OpenSearch
(needs a GELF TCP input on `GELF_PORT`; uses throwaway `/tmp` configs/DBs):

```bash
GL_PASS='<graylog-admin-pw>' bash scripts/e2e-archive-test.sh
```

- [ ] **[1] Graylog log archiving (API mode)** — export produces an archive
- [ ] **[2] OpenSearch archiving (OpenSearch-direct mode)** — export produces an
      archive (the script cycles the deflector first so the seeded index seals;
      OS-direct export always skips the active write index)
- [ ] **[3] GELF import back into the Graylog TCP input** — importer reports
      `Messages sent: N` (N>0) and **0 indexer failures** (compliance pass)
- [ ] **[4] OpenSearch Bulk import** — docs actually land in OpenSearch. Bulk
      bypasses Graylog entirely, so [3] does not cover it. The script must NOT
      pre-create the index: provisioning it is the product's job and the bug
      hid there (DEFECTS #4, #24)
- [ ] **[5] Re-export dedup** — a re-export over archived time adds **0** records,
      yet a punched gap comes back **exactly once** (DEFECTS #1–#3)
- [ ] **[6] Deleted archive file** — `verify` reports it missing and the next
      export re-archives exactly that range
- [ ] **[7] Clear target index set, then import into it** — the clear leaves
      exactly **one empty** index, internal `gl-*` sets are never listed, and a
      following import still succeeds (a clear that wedges ingestion is worse
      than no clear at all)
- [ ] Script prints `RESULT: ALL PASS`

> **Run it ON the Graylog host.** `GL_URL`/`OS_URL` default to `localhost`, and
> the GELF seed connects to `127.0.0.1` — running it from a different machine
> fails immediately with `ConnectionRefusedError` / `FAIL: seed not indexed`.
> Override `GL_URL`/`OS_URL` only if you also have a route to the GELF port.

> Note: re-imported messages land ~8h earlier than the run time on Asia/Taipei
> systems (naive-Taipei-vs-UTC timestamp offset — see CLAUDE.md "Restore /
> Re-import"); the script counts over a 24h window and trusts the importer's own
> 0-indexer-failures reconciliation, not a last-1h count.

### Operation Audit

- [ ] `op_audit.enabled: true` — listener starts on port 8991, audit page shows "Listening"
- [ ] `op_audit.enabled: false` — listener does not start, audit page shows disabled
- [ ] Config without `op_audit` section — uses all defaults (enabled, port 8991, retention 180)
- [ ] Config with `op_audit` but missing `retention_days` — falls back to default 180
- [ ] `op_audit.retention_days` controls audit cleanup independently from archive retention
- [ ] Cleanup runs audit cleanup even when no archive files to clean
- [ ] `upgrade.sh` adds full `op_audit` block when missing from config.yaml
- [ ] `upgrade.sh` adds `retention_days: 180` to existing `op_audit` block when missing
- [ ] nginx syslog received → audit records appear in Web UI
- [ ] Syslog from non-allowed IP → rejected with warning log
- [ ] Username resolved correctly (Basic Auth, Token, Session, Cookie)
- [ ] Target name shows human-readable resource names (not raw IDs)
- [ ] Sensitive operations trigger notification alerts
- [ ] **A nested URI is named for the nested resource, not its parent**
      (`tests/test_audit_operation_labels.py`) — creating an API token is
      `user.token_create`, not `user.modify`; deleting a stream rule is
      `stream_rule.delete`, not `stream.delete`. The whitelist is ordered
      most-specific-first and it, not the broad sensitive list, names the
      operation
- [ ] **Every sensitive pattern has a sample request that reaches the database**
      — a pattern the whitelist does not keep would alert and store nothing
- [ ] Token targets name the token (`local:admin / token 'backup-tool'`) and a
      delete-by-value never shows any part of the secret
- [ ] Heartbeat alert when no syslog received for 10+ minutes while Graylog is up
- [ ] Filter dropdowns show correct language labels (Method/Status vs 方法/狀態碼)

### Customer Install / Upgrade Simulation

- [ ] Copy `github/` to temp dir → `pip install` succeeds
- [ ] `deploy/install.sh` references correct paths, systemd default = Yes
- [ ] `deploy/install.sh` writes a minimal `config.yaml` with `servers: []` (triggers setup wizard)
- [ ] `deploy/upgrade.sh` runs successfully (db-backup → git pull → install → restart → verify)
- [ ] **A rewritten upstream history does not block the upgrade** — if the
      published history is ever force-pushed, every existing clone diverges and
      `git pull --ff-only` fails. `upgrade.sh` must detect ahead-AND-behind and
      reset the install to `origin`, saying so; a pull failure that is not a
      divergence must still stop the upgrade
      (`tests/test_upgrade_divergence.py` runs the shipped recovery block
      against a genuinely diverged pair of repositories)
- [ ] **The DB backup actually produced a file** — `/var/backups/jt-glogarch/` gains a
      fresh `jt-glogarch-*.db` snapshot. The presence probe once ran from root's cwd,
      hit `PermissionError` on `./config.yaml`, and SILENTLY skipped the backup while
      printing a benign "not available" line (v1.13.82). `test_upgrade_script.py`
      pins the probe running inside `$INSTALL_DIR`.
- [ ] `deploy/upgrade.sh` never overwrites an existing `servers:` / `opensearch:` block

**Air-gapped install / upgrade (v1.14.5)** — static gates live in
`test_static_sweeps.py::test_offline_bundle_can_do_a_first_install` and
`::test_report_engine_install_is_verified_not_assumed`; the manual pass needs a
VM with the network genuinely blackholed (not just "we did not use it").

- [ ] **A bundle can install onto a host that has never been online** —
      `bash scripts/build-offline-bundle.sh`, carry the tarball to a host with
      NO jt-glogarch and no route to PyPI, `sudo bash install-offline.sh`, then
      `systemctl enable --now jt-glogarch` and reach `/setup`. *Before v1.14.5
      this was impossible: the bundle could only upgrade a host that had once
      been online.*
- [ ] **Neither offline script can do the other's job** — `upgrade-offline.sh`
      on a fresh host names `install-offline.sh` instead of dead-ending;
      `install-offline.sh` over an existing install refuses and points at the
      upgrade (which is the only one that backs up the database first).
- [ ] **pip really never reaches the network** — run the install with the
      default route removed. `--no-index` is explicit; a fallback to PyPI hangs
      for minutes and then fails.
- [ ] **A Python minor-version mismatch is caught BEFORE anything is written** —
      a `cp310` bundle on a 3.12 host aborts with the version named, not with a
      compiled-wheel ImportError halfway through.
- [ ] **The render engine is verified, not assumed** — every installer runs
      `verify_report_engine`, which LAUNCHES Chromium as `jt-glogarch` and
      renders a PDF. On a host missing the OS libraries it must print the
      missing `lib*.so` names (from `ldd`) and the final summary must say PDF
      Reports do not work — while stating that archiving and restore are
      unaffected. *A tarball cannot carry those libraries and offline mode
      skips `playwright install-deps`, so "installed" and "works" are different
      facts; the upgrade used to report success and the first scheduled report
      failed hours later.*
- [ ] **Log what you swallow** — after any change that adds an `except`, run
      `test_silent_except_count_only_goes_down` (budget 15, only goes DOWN) and
      `test_remaining_silent_excepts_are_narrow` (no broad `except` that does
      nothing, anywhere). *A degradation nobody can see in the log is a
      degradation nobody can diagnose.*

### WebUI Connection Settings + Setup Wizard (v1.8.0) — Feature ↔ Test

| Feature | Automated test | Manual check |
|---|---|---|
| Fresh install → guided setup | `test_settings_api::test_fresh_install_redirects_to_setup` | Open `https://host:8990/` on a `servers: []` config → lands on `/setup` |
| Step 1 sets admin password + opens session | `test_setup_flow_then_gate_closes` | Wizard step 1 accepts ≥8-char password, then continues authenticated |
| Setup is the only pre-auth write path, self-closing | `test_setup_flow_then_gate_closes` (403 after configured) | After finishing, `POST /api/setup/admin-password` → 403; `/setup` → `/login` |
| Config endpoints require auth | `test_config_endpoints_require_auth` | Logged out, `/api/config/*` → 401 |
| Add/edit/delete Graylog servers | `test_server_delete_reassigns_default` | Settings page: add, edit, delete, set default; test-connection button |
| Secrets masked on GET, reconciled on save | `test_server_masking_and_secret_reconcile`, `test_opensearch_save_and_mask` | Save without changing a secret → `config.yaml` keeps the real value (no `***`) |
| Global OpenSearch editable | `test_opensearch_save_and_mask` | Settings page: edit hosts/user/pass, test connection |
| Live apply, no restart | (in-memory update asserted via subsequent GET) | Change a server → next export/import uses it without `systemctl restart` |
| Login robust when unconfigured | `test_login_with_empty_servers_does_not_500` | `POST /login` on empty config never 500s |
| **Upgrade**: existing servers skip wizard | `test_upgrade_existing_servers_skip_wizard` | Existing customer config → `/` → `/login` (not `/setup`) |
| **Upgrade**: partial edit preserves fields | `test_upgrade_partial_edit_preserves_untouched_fields` | Edit only a server URL → token/user/pass/per-server OS + other top-level keys intact |

### Security — Bandit SAST (every release, automated)

Run by `run-tests.sh`; ZAP is dynamic and structurally cannot see any of this.

- [ ] `bash scripts/bandit-scan.sh` prints `Bandit: OK` — **HIGH and MEDIUM must
      be ZERO**. Fix, or annotate the line `# nosec <IDs> - <why it is safe>`;
      never disable a whole rule, or the next real one is invisible
- [ ] The LOW ratchet (budget 8) did not grow. It EXCLUDES B110/B112 on purpose:
      `try/except/pass` is owned by `tests/test_static_sweeps.py` and its own
      budget — two rules for one decision is how gates start contradicting
- [ ] **No call hardcodes `verify=False`** (`tests/test_tls_verify.py`, AST).
      *Seven sites did, so an operator who turned `verify_ssl` ON got it on most
      paths and silently not on those — several carrying credentials (v1.13.91).*
- [ ] **The CA bundle httpx trusts is current** (`tests/test_tls_trust.py`):
      `certifi >= 2026.10.19` stays in BOTH `pyproject.toml` copies, and the
      installed bundle does not contain *emSign ECC Root CA - G3*
      (GHSA-6q48-6c7w-9gw2). httpx reads certifi, not the OS store — an OS
      `ca-certificates` update alone leaves the notification channels exposed.
      Upgrade path: from a host holding an older certifi, `upgrade.sh` must leave
      2026.10.19+ (its `[report]` deps step resolves the floor)
- [ ] A raised budget or a new `# nosec` is justified in the commit message

### Security — OWASP ZAP DAST (must be 0 High / 0 Medium)

- [ ] `scripts/zap-scan.sh` run against a live instance — **0 High, 0 Medium** alerts
- [ ] Response carries `Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`
- [ ] Session cookie is `Secure` + `HttpOnly` + `SameSite=Strict`
- [ ] Non-static responses carry `Cache-Control: no-store`
- [ ] `Server` response header is absent (uvicorn banner stripped)
- [ ] Any accepted ZAP rule in `.zap/rules.tsv` has a written justification

### Destructive operations — clear target index set (v1.13.66)

Any feature that DELETES customer data must be re-verified every release; a
regression here is not recoverable by the customer.

- [ ] Import dialog → "Clear target indices before import" is **collapsed** by default
- [ ] "Load index sets" lists the target's sets with a **non-zero** index count and
      size (a zero here means the response shape changed — see DEFECTS #27; a clear
      would then look like a harmless no-op)
- [ ] The target's **default** index set is pre-selected
- [ ] Graylog-internal sets (`gl-events`, `gl-system-events`) are **not listed**,
      and are refused by the API even when their ID is posted directly
- [ ] Typing the wrong prefix is rejected client-side AND server-side (`confirm`)
- [ ] After a clear: the set holds exactly **one** index, and it is the **new, empty
      write index** — the target can still ingest
- [ ] An import into the cleared set succeeds afterwards (this is the whole point:
      a bad field mapping from older data is gone)
- [ ] The action appears in Operation Audit as `graylog_index_set_cleared` with
      prefix, count and bytes freed
- [ ] jt-glogarch's own archives are untouched (archive list unchanged)

- [ ] **Captions never understate the request** — a widget whose data spans
      less than the requested window shows BOTH (e.g. "Last 6d (…) ⚠ requested
      Last 90d; data exists only for the range shown"). A 90-day report whose
      caption read "Last 6d" made the request itself vanish from the page
      (v1.13.86)
- [ ] **Every table states its total row count** — untruncated "12 rows",
      truncated "showing first 40 of 128 rows". A reader must never have to
      count rows by hand, and a truncated table must say what it is a subset OF
- [ ] **A long report shows progress while it runs** — generate a 90-day
      report and watch Job History / the sidebar: the bar must advance per
      finished slice (`3 / 13`), not sit at 0% until the PDF appears. It must
      NOT reach 100% before the file exists (the render happens after the last
      slice). A dozen sliced queries take minutes; a frozen 0% reads as a hang
      and customers cancel a run that was working (v1.13.88).
      Unit cover: `tests/test_report_progress.py`

### Wide-Window Reports — MANDATORY for report-affecting changes

`GL_PASS=<pw> python3 scripts/report-bigrange-test.py [GL_URL]` against a live
Graylog — must print `RESULT: ALL PASS`. Creates (and deletes) a throwaway
dashboard with exactly the two widget shapes the machinery must handle.

Why a unit suite is NOT enough here: both bugs this script would have caught
were LIVE-SCHEMA mismatches invisible to tests built on assumed JSON — the
search definition writes intervals as `{"timeunit":"5m"}` and series as
`{"type":"count"}` (not the widget-config `{"value":5,"unit":"minutes"}` /
`{"function":"count()"}`), so coarsening and slicing each silently never fired
while every unit test stayed green, and a naive "sliced == unsliced" comparison
passed because BOTH runs were unsliced.

- [ ] Coarsening fired — the fixed-5m timeline's caption announces
      "interval adjusted 5m -> 6h"
- [ ] The avg widget carries the "cannot be merged from slices" caption
      (avg / cardinality / percentiles are NEVER stitched)
- [ ] The sliced 90-day count total exactly equals an unsliced control run
- [ ] The sections render to a real PDF (needs the render engine)
- [ ] Log shows BOTH `coarsened wide-range intervals` and
      `wide-window slicing done` — equal numbers alone prove nothing if
      neither mechanism engaged

### UI Actions — real-click verification (MANDATORY for changed UI actions)

Three consecutive bugs in ONE feature each passed a check one layer below what
the user experiences: the endpoint 500'd while unit tests called the class
directly; the dropdown rendered empty while `<option>` elements existed; the
Cancel button was dead (`customConfirm` undefined — valid syntax, defined
nowhere) while the API, the flag and every unit test were fine. The rule:
**verify the user's actual action at the layer the user sees.**

- [ ] Every UI action CHANGED in this release is clicked in a real browser
      against a live instance — not asserted via markup/`<option>`/route alone
- [ ] `UI_URL=... UI_USER=... UI_PASS=... GL_HOST=... GL_PASS=...
      python3 scripts/ui-cancel-test.py` — must print `RESULT: ALL PASS`
      (confirm modal opens, job stops, status records `cancelled` not
      `completed`). Mandatory whenever import/cancel/job-status paths change
- [ ] Any notification path touched: read the ACTUAL message produced — a
      user-initiated cancel must notify as cancelled, never as
      "completed with errors"

- [ ] **A scheduled export can be cancelled, and cancelling frees the lock** —
      `tests/test_export_cancel_registry.py` passes. Cancellation used to work
      only through `progress_callback` raising, which the scheduler never
      supplies: the run kept going, kept the per-server lock, and every nightly
      run afterwards was skipped with "Previous export still holds lock" —
      archiving stopped for ~4 weeks with only info lines (v1.13.87)
- [ ] **A manual export on a busy server is REFUSED, visibly** — `POST
      /api/export` answers 409 with `export_already_running`, not 200
      "started". *The job row is written inside the exporter, after the lock,
      so a refused run left no row at all and the failure lived only in an
      in-memory list Job History never reads — a customer pressed Run now, was
      told it started, and found nothing anywhere (v1.13.92).*
- [ ] **Any export failure before the exporter's own row still appears in Job
      History** — failed row, sanitized reason, correct `source`. Covers lock
      held, disk full, unreachable server.
      Unit cover: `tests/test_export_busy_visibility.py`
### Audit coverage (every release)

- [ ] **Every state-changing route leaves an audit record** —
      `tests/test_audit_coverage.py` walks all routes; a POST/DELETE that
      changes nothing must be listed in READ_ONLY_POSTS **with a reason**.
      *An inventory found 18 of 43 unaudited, including `POST /cleanup`, which
      DELETES ARCHIVE FILES — deleting one archive was audited, deleting
      hundreds by retention was not (v1.14.0).*
- [ ] **The destructive ones specifically**: cleanup, archive delete, clear
      index set, delete server / schedule / report
- [ ] **jt-glogarch's own log is readable in the UI** — Operation Audit →
      "jt-glogarch operations", filterable and paged. *The records were written
      from day one with no interface at all; the only way to read them was to
      open the SQLite file.*
- [ ] The Graylog stat cards are hidden on that tab — they count Graylog
      operations and would read as counts of this tool's

### Search security

- [ ] **XSS: archived log content is attacker-controlled.** Anyone who can send
      a log line to the customer's Graylog gets that text into our archives and
      onto this page. Render `<script>`, `<img onerror>`, `<svg onload>`,
      `</td></tr>` breakout and a payload as a FIELD NAME and as the archive
      filename: all must appear as text, nothing may execute.
- [ ] Field/server/stream values are bound SQL parameters; no user-supplied
      path ever reaches the filesystem (archive paths come from the DB row)
- [ ] All `/api/search*` endpoints answer 401 without a session
- [ ] Page size clamped, retained hits capped, live searches pruned

### Record search (Archives page)

- [ ] **No time range = no search, enforced twice** — the button is genuinely
      `disabled` (not merely labelled so) AND `POST /api/search` answers 400
      for a rangeless, half-range or unparseable-range request. *The range is
      the only index; without it the scan is the entire corpus — 173 GB and
      1.06 billion records on one real box.* The hint names the control to use
      ("drag on the Archive timeline above").
- [ ] **The cost is stated before the search runs** — `/api/search/plan` shows
      archives, records and an estimate, and opens no archive to do it
- [ ] **The prefilter never under-selects** — a term containing a JSON-escaped
      character (`"` `\`) bypasses the byte scan, and an unreadable archive is
      treated as a candidate. *A skipped archive is a silently missing result,
      indistinguishable from "nothing was there".*
- [ ] **"Load more" resumes, it does not re-run** — every hit appears exactly
      once across pages, no gaps, and archives already scanned are not
      reopened. `has_more: false` means the range really is exhausted.
- [ ] **Per-page 50/100/200/500/1000 is honoured** — picking 50 returns 50
- [ ] **Long records are truncated visibly, not clipped** — a 4,000-character
      syslog line shows ~320 characters plus "…", never a line with a chunk
      silently missing from the middle
- [ ] **An OpenSearch-direct scan that reads fewer documents than the index
      holds FAILS the index** — it does not report success. `iter_index_docs`
      reconciles `fetched` against the pre-scan `_count` and raises
      `IncompleteIndexScan`. *The cursor is `(timestamp, _doc)` and `_doc` is
      shard-local, so on a multi-shard index a page boundary can exclude a
      record that was never returned — and the chunks already written are
      recorded as covering their time range, so dedup hides the gap on every
      later run. Production indices have 4 shards; the e2e cluster has 1, which
      is why no data-path test could ever have caught this.*
- [ ] **Cancelling an export never records a partial hour** —
      `test_export_cancel_paths.py` (runtime, both real exporters, faked
      backends): a flag-only cancel mid-index records ONLY the whole hours
      (`..._never_records_a_partial_hour`), and the next run brings the
      discarded hour back whole (`..._resumes_from_the_discarded_hour`).
      *A `break` fell through to "close the last writer" and stamped a
      half-scanned hour as complete; dedup then hid its tail forever. Scheduled
      runs always took that path.*
- [ ] **Every cancel path ends CANCELLED, never COMPLETED or FAILED** — same
      file: flag path (scheduled), callback path (Web UI), Phase A dedup loop,
      API mid-chunk, and the backpressure pause
      (`test_backpressure_pause_honours_cancel`). No error notification on any
      of them. Manually: press Cancel while the job shows "Paused — source
      under load" and confirm it stops within one pause tick, not 30 minutes.
- [ ] **The cancelled row is honest** — `messages_done` = what is on disk,
      `messages_total` keeps the plan's denominator, `progress_pct` stays where
      the work stopped (not 100), no "Covered all N index set(s)" and no green
      coverage chip, the note says the hour in progress was discarded. Live
      export page shows "Cancelled by user (N records)", not "Completed!".
      Release script: `scripts/ui-cancel-test.py` now cancels a real
      OpenSearch-direct EXPORT (not only an import) and asserts all of this.
- [ ] **Cancel and backpressure are never reported as data loss** — breaking
      out of the scan closes the generator, so the reconciliation must not run.
      A user pressing Cancel must not be told the archive lost records.
- [ ] **On a BUSY cluster, bound the window** — `E2E_WINDOW_HOURS=2 bash
      scripts/e2e-archive-test.sh` replaces the `--days 1/3` exports with a
      fixed window. *A production Graylog ingesting ~9.5M messages/hour turns
      `--days 3` into tens of millions of documents and hours of load.*
- [ ] **Do NOT run step [3] (GELF re-import) against a production Graylog** —
      it imports the archive back into the LIVE index set, which on a busy
      cluster means hundreds of thousands of duplicated production messages.
      The full round-trip belongs on a test cluster; production runs the
      read-only and isolated-index steps.
- [ ] **A 4-SHARD index is scanned completely** — e2e step [8] builds one on
      purpose, with 30 documents per timestamp so sort keys collide across
      shards, and demands every document back in timestamp order.
      *`tests/test_os_shard_scan.py` reproduces the loss deterministically; the
      e2e step exists because production has 4 shards and this cluster has 1,
      which is how a real record-dropping bug hid for its whole life. Any new
      scan/cursor work must keep BOTH.*
- [ ] **Every shard request pins the primary copy** (`_shards:N|_primary`) —
      `_shards:N` alone may alternate between primary and replica, whose `_doc`
      order differs, which reintroduces exactly the bug being fixed.
- [ ] **The merged scan still yields ascending timestamps** — the exporter
      closes and RECORDS a chunk archive when the hour boundary is crossed, so a
      scan that restarted at t0 per shard would reopen chunks already written.
- [ ] **Peak memory did not grow** — each shard holds a page and has one in
      flight, so the byte budget is divided by 2N. Measure with wide (~9 KB)
      documents: `test_bytes_in_flight_stay_within_the_single_page_budget`.
      *The 500-document page floor was written for ONE cursor; applied per shard
      it silently became a 36 MB memory floor on the box that gets OOM-killed.*
- [ ] **A single-shard index is scanned exactly as before** — no per-shard
      requests, no new behaviour, for small deployments and this test cluster.
- [ ] **The results table keeps its geometry** (`ui-sim-test.py`) — expanding a
      hit changes neither the table width nor the record column's; the detail
      row's `colspan` equals the number of VISIBLE columns; header and body
      agree on which columns exist and the visible ones fill the table.
      *Hiding a column is a property of the table, not of each cell: a
      hardcoded colspan invents phantom columns, and per-cell hiding misses
      every row appended later. Both squeeze the record text into 96 px, and
      no backend test can see either.*
- [ ] **Expanding shows every field at once** — no "… N more fields" second
      click; a wide-schema record (1,100+ fields) scrolls inside its own box
      rather than burying the results below it
- [ ] **Download covers every page, not the screen** — CSV and JSON Lines both
      return the whole matching set for the range, and the two agree on the
      record count. *`limit` bounds the screen; an export that honoured it
      would hand over a quarter of the evidence and look complete doing it.*
- [ ] **The download streams and reads each archive once** — the first row is
      available before the last is found (no materialising), and a full export
      opens each archive exactly once. *The screen's "load more" resumes by
      re-parsing the archive it stopped inside — correct for a few clicks,
      quadratic for a download: three 1,000-row pages examined 220K, 531K then
      464K messages. Streaming cut a real 4,041-row export from 62 s to 35 s
      with byte-identical output.*
- [ ] **The row cap is marked IN the file** — hitting it writes a TRUNCATED
      row (CSV) / `_jt_note` object (JSONL), never a silent stop
- [ ] **CSV opens correctly in Excel** — UTF-8 BOM present, so Chinese fields
      are not mojibake; embedded newlines stay inside quoted fields
- [ ] **The export is audited** (`search_exported`) — records leaving the
      archive is egress, and egress leaves a record
- [ ] **`/search/export` is declared before `/search/{search_id}`** — FastAPI
      matches in declaration order, and the parameterised route silently
      swallowed the literal one, answering the download with a 404 JSON body
- [ ] **Matched terms are highlighted, and the highlight is safe** — the
      keyword is marked in the Record column and in the expanded record (never
      in Source), a field filter marks its key as well as its value, and a
      message containing `<img src=x onerror=...>` renders as TEXT with the
      term still marked. *The highlight builds HTML from a log line: escape
      each span first, insert the marks second — the other order is an XSS.*
- [ ] **Search yields to archiving** — it pauses per archive while an export or
      import holds a lock, and says so on screen
- [ ] **The scope is stated in the UI** — that this is a scan, not a query
      engine, and that full analysis means importing back into Graylog
      Unit cover: `tests/test_search_engine.py`, `tests/test_search_api.py`

- [ ] **Dashboard stat values are never clipped** — the UI smoke measures the
      rendered text against the card at magnitudes from thousands to 10^18.
      *`.stat-card` sets overflow:hidden for the sparkline, so 1,060,702,960
      records rendered as `1,060,702,96` (v1.13.93). No Python test can measure
      type — this needs the browser.*
- [ ] **Days Archived counts days that hold an archive, not the span** — one
      stray old archive must not stretch it, deleted archives do not count, an
      hour ending at local midnight belongs to the day it starts, and the gaps
      are listed. Unit: `tests/test_archive_day_coverage.py`. By eye on .36:
      the card's value, range and "N day(s) in between have no archive" with
      the dates on hover, in both themes. *.36 had one archive on 01-01 and
      nothing again until 02-11: the span said 307 days, the archive held 266.*
- [ ] **Only Graylog accounts with an allowed role sign in** — a Reader account
      (password or token) is refused with `role_not_allowed` and gets no API access;
      Admin, the `*` permission and a role added to `web.allowed_graylog_roles` sign
      in; roles that cannot be read refuse the login; a session from before 1.18.2
      counts as signed out. Unit: `tests/test_login_roles.py`. Live: a throwaway
      Graylog 6.3 and 7.x with a Reader user and tokens (the 1.18.2 run used both).
- [ ] **A cleanup retention saved in the Schedules page survives a restart** —
      save a value shorter than `retention.retention_days`, restart, the page
      still shows it. Unit: `tests/test_cleanup_schedule_retention.py`
      (`test_retention_saved_through_the_api_survives_the_startup_reconciliation`).
      *The 1.13.57 safety net ran on every startup and reset .36's 150 days to
      1095 at a deploy (2026-11-03).*
- [ ] **No template carries an inline `style="…"`** — the app's own
      `style-src 'self'` CSP refuses them (`style-src-attr`), so they look
      applied and do nothing. Two elements meant to start hidden rendered
      visible. Sweep: `tests/test_static_sweeps.py`
- [ ] **Run the UI smoke WITH credentials** — without them the post-login
      checks (Settings renders, stat clipping, main-page console errors) do not
      run at all. It now prints `post-login checks NOT run`; a gate line that
      says OK while a layer was skipped is how the CSP error above survived.
- [ ] **The audit heartbeat alert names its cause** — the body carries the
      per-server reason, and two consecutive failed probes are required before
      alerting. *It was logged at DEBUG (dropped at INFO) and fired on a single
      blip: alert / restored / alert in 11 minutes while both servers answered
      in 50 ms (v1.13.92).* Unit cover: `tests/test_audit_heartbeat.py`
- [ ] **A helper that reads a config field is tested against the REAL model** —
      never a hand-rolled stub. *`verify_for_url` read `graylog_servers`
      (the field is `servers`); the stub used the same invented name, so the
      test agreed with the bug and the feature shipped inert (v1.13.92).*
- [ ] **A lock-skip escalates only when work has actually stopped** — the streak
      alone is NOT the signal. Check what the lock protects: no running export
      at all → stale lock, alert and say restart clears it; running and
      ADVANCING → healthy, log the progress and never alert; running but not
      advancing across several runs → its own message saying that, warning that
      a throttled export is paused on purpose and resumes by itself.
      *A first full backlog can be billions of records over weeks and displaces
      every daily run while archiving perfectly. Alerting on the streak told
      such a site "no data is being archived" and invited them to cancel a job
      that was 58 hours in — false, and destructive if believed (v1.13.90).*
      Unit cover: `tests/test_schedule_lock_skip.py`
- [ ] **A running job says how much longer it has** — Job History and the
      sidebar show a remaining estimate from the job's own averaged rate
      (`~53d left`), suppressed until there is signal, never on a finished job.
      *"4% · 58h26m" on 11.58 billion records could not be told apart from a
      hang; it had 53 days left.* Unit cover: `tests/test_job_eta.py`

### Performance & liveness at scale (for export/import/DB/polling changes)

Costs that grow with TOTAL data (not with the work) surface only at customer
scale: `covered_ranges` cost 45 s/run at 200K archives; Job History polling
cost 7% of a core forever at 50K job rows. Both were invisible at test-size.

- [ ] `tests/test_perf_covered_ranges.py` passes (scale-pattern regression
      bounds; seeds 30K synthetic archives)
- [ ] For new hot-path queries: benchmark against a synthetic 200K-archive DB
      before shipping, and state the measured number in the changelog
- [ ] No config value used as a loop step/divisor without a clamp
      (`chunk_duration_minutes <= 0` used to hang the export forever)
- [ ] Static sweeps pass (`tests/test_static_sweeps.py`): undefined names,
      import shadowing, i18n both-languages + zh punctuation/terminology,
      data-act handlers, innerHTML error-escaping, silent-except ratchet

> Staging note: .36 has REAL notification channels configured — import/export
> tests there deliver actual mails. Announce test noise, or disable channels
> first.

### API export — single-millisecond overflow (v1.13.83 / 85)

Whole-second syslog bursts (`12:23:03.000`, no sub-second precision) can put
more than 10,000 messages at one timestamp — past Graylog's REST offset limit.
This must degrade precisely, never lose the chunk, and never be mislabelled a
failure.

- [ ] `tests/test_export_pagination.py` passes, incl.
      `test_overflow_ms_does_not_lose_messages_after_it` (everything AFTER the
      over-full ms is still exported — the old code deleted the whole chunk)
- [ ] A single-ms overflow is recorded in `search.truncated_windows` and lands
      in `result.truncations`, NOT `result.errors`
- [ ] `tests/test_notify_format.py` passes: an overflow-only run is titled
      `export_overflow` (not `export_err`), routed `EXPORT_COMPLETE` (not
      `ERROR`), and its body says "archived; NOT retried" — a real chunk
      failure still outranks it and reports as an error
- [ ] **The notice carries the numbers** (`test_overflow_notice_states_how_many_were_not_read`,
      `tests/test_overflow_holes.py::test_truncation_record_carries_the_count`):
      each timestamp line says "N in that millisecond: 10,000 kept, M unread".
      Graylog's `to` is EXCLUSIVE — the count must ask `[ms, ms + 1)`; `from == to`
      counts 0 and the numbers silently vanished. A fake Graylog in a test must be
      end-exclusive too (the inclusive one let this pass). Live: on an overflow
      notice, the unread number matches an OpenSearch count of that millisecond
      minus 10,000. The title never says "a few".
- [ ] Testing any `notify_*` path: bypass conftest's autouse mute — capture the
      REAL function at import (`_REAL = S.notify_export_complete`) then patch
      `send_notification`; asserting against the stub passes vacuously
- [ ] **The overflow notice explains itself** — it must state the CAUSE (one
      millisecond held >10,000 messages; 10,000 is the API's per-query ceiling),
      the BLAST RADIUS (everything else was archived, the run did not fail, no
      retry), and the ACTION (re-run just these windows in OpenSearch Direct).
      A customer read the old jargon-led wording and had to ask what it meant.
- [ ] **Overflow timestamps show local time AND UTC** — Graylog returns UTC and
      the operator re-runs in their own zone; on Asia/Taipei a bare `...Z` sends
      them to the wrong eight hours, defeating the notice's only purpose
- [ ] **Notification stats line up in one column** — labels padded to a common
      DISPLAY width (CJK counts as two columns), export/import/cleanup/verify,
      both languages; and zh bodies use full-width colons
- [ ] **Telegram bodies are HTML-escaped** — `parse_mode=HTML` turns a literal
      `<url>` (produced by URL shortening in error text) into an unsupported
      tag, so Telegram 400s and the notification is silently never delivered
- [ ] Live (optional): seed >10,000 messages at one second + a few after, run
      the API export, confirm the "after" messages are archived and the overflow
      is reported (not a chunk failure). Clean up the seed afterwards.

### Overflow holes (v1.14.8)

- [ ] **An OpenSearch Direct run over an overflowed hour fetches exactly the
      missing millisecond** — e2e step [9]: 10,500 messages seeded into one
      millisecond, API export records the overflow, OS Direct re-run adds
      exactly 500. `tests/test_overflow_holes.py` pins the hole in
      `covered_ranges()` and that BOTH dedup rules see it. *The notification's
      remedy used to be de-duplicated away by the hour's own API archive.*
- [ ] **The overflow notification names the unread count** — "(N in that
      millisecond: 10,000 kept, K unread)". `test_truncation_record_carries_the_count`.
- [ ] **Upgrade adds `archives.overflow_ms`** — `upgrade-compat-test.sh`
      (auto-migration; nullable, additive).

### Reports — enable switch (v1.36.0)

- [ ] `tests/test_reports_enabled.py` (4): the switch turns a
      report off (its job removed from the scheduler) and on (registered again), unknown report 404,
      a non-boolean refused, a save without `enabled` keeps the stored state. By hand: the switch in
      the list, its label follows, Generate still works on a disabled report; no BETA tag.

### Reports — one-off time range (v1.14.9)

- [ ] **"Generate" opens the one-off range dialog** (`ui-sim-test.py`): two
      datetime-local inputs, a hint that says the values are for this run only,
      Cancel closes it. Left empty, the saved range applies.
- [ ] **The range is used for this run and never saved**
      (`tests/test_report_adhoc_range.py`): `effective_window()` overrides
      per-widget ranges and snap-to-midnight, feeds the SAME bounds to both
      dashboard modes; the API rejects a single bound / inverted / unparseable
      / >400-day range with 400 before anything runs; the stored `config_json`
      is byte-identical afterwards; the job note records the range.
- [ ] Manually: generate a report with a past week as the range and check the
      cover's period line shows that week, then confirm the report's settings
      page still shows the original range.

### Japanese UI + notifications (v1.15.0)

- [ ] **Japanese translation is complete and intact** (`tests/test_i18n_ja.py`):
      same keys as English, every `{placeholder}` and HTML tag kept, no
      Traditional-Chinese-only glyphs, no half-width `,;!?` against Japanese,
      every page's `#lang-select` offers every language defined in `i18n.js`,
      cron labels verified by executing `cronHuman()`.
- [ ] **zh-TW rules stay scoped to the zh-TW block** (`test_static_sweeps.py`
      `_i18n_spans`): adding a language after zh-TW must not feed it to the
      Taiwan-terminology / full-width checks.
- [ ] **Switching really renders Japanese** (`ui-smoke.py`, `ui-sim-test.py`):
      kana on the login page and in the sidebar; zh-TW / ja / en cycle on every
      page with no console errors.
- [ ] **Japanese notifications** (`tests/test_notify_ja.py`): template keys and
      placeholders match English; a real import-complete notification renders
      in Japanese. Manually: set 通知語言 to 日本語 and send a test notification.
- [ ] Manually: open setup wizard, login and Settings in Japanese on staging —
      no English left in the chrome, nothing overflows the sidebar.
- [ ] **Japanese PDF reports** (`tests/test_report_ja.py`): every report string
      table has Japanese for every English key; the helpers (time spans, row
      counts, incomplete warning, interval-coarsening note) really return
      Japanese; **any function in `glogarch/report/` that branches on
      `== "zh-TW"` must also handle `"ja"`** (the gate that stops a new string
      from silently falling back to English); a Japanese report is set in a JP
      font face; the report form offers 日本語 and a new report follows the UI
      language.
- [ ] Manually: generate a Japanese report (archive summary + one rebuilt
      dashboard) on log4, render pages to PNG and read cover, TOC, table notes,
      header/footer and watermark — no Chinese fallback, no tofu.

### Job lists stay current; Cancel uses live state (v1.15.1)

- [ ] **Ended jobs cannot be cancelled** (`tests/test_job_cancel_stale_view.py`):
      completed / failed / cancelled → 409 with the real status, status unchanged,
      no cancel flag; running job still cancels; unknown id → 404, no flag.
- [ ] **Lists refresh themselves** (`ui-sim-test.py` step 7, routed `/api/jobs`):
      the Task Log changes on its own when a job's state changes.
- [ ] **Stale Cancel is explained, not sent** (same step): clicking Cancel on a
      row that still says running while the server says ended shows "already
      ended" and makes no cancel request.
- [ ] Manually: open the Task Log as two different accounts in two browsers,
      cancel a throwaway export in one — the other shows it cancelled within ~5 s
      without reloading.
- [ ] **Multi-admin guards** (`tests/test_multi_admin_guards.py`): schedule edit
      keeps `enabled` and `server`; Run now (export) 409 while that server
      exports, no row, no last-run move; Run now (cleanup/verify) returns at once
      on a long-lived loop, uses the SCHEDULE's retention, second run 409; stale
      audit toggle 409 and unchanged; server used by a schedule/report cannot be
      deleted; archive being imported cannot be deleted; index set being imported
      into cannot be cleared; scheduled exports publish live progress.
- [ ] **Schedule edit through the real dialog** (`ui-sim-test.py` step 8):
      a disabled throwaway schedule stays disabled and keeps its server.

### Export heap guard on Graylog 7 — GC metrics, pacing, cached search results (v1.16.0)

- [ ] **GC signal** (`tests/test_health_guard_gc.py`): a healthy 80–94 % used %
      sawtooth with no full GC never pauses on GC metrics (and does pause with
      `health_heap_signal: used`); a full GC, heap still `>=` the hard limit right
      after GC, or GC time `>=` `health_gc_overhead_pct` on two readings in a row
      pauses; a Graylog restart (counters reset) does not; missing GC metrics fall
      back to used %; journal and buffers are still watched.
- [ ] **Pacing** (same file): delay per page is 0 at or below
      `health_pace_start_pct` and rises linearly to `health_pace_max_delay_sec` at
      `jvm_memory_hard_pct`; never for OpenSearch-direct or without GC metrics; the
      API exporter calls `guard.pace()` for every page.
- [ ] **A heap-bound pause releases Graylog's expired search results** after
      `health_search_cache_flush_sec`, at most once a minute, and resumes once the
      heap falls; a journal/buffer pause never sends those searches.
- [ ] **Against a real Graylog — .83, never a production one**: an API export with
      lowered thresholds logs `export pacing adjusted` with the delay rising as
      Graylog's heap after GC rises, and a forced heap-bound pause logs
      `asked Graylog to release expired search results searches=8`.
- [ ] **One nightly run on staging** with a read-only GC sampler on the source
      Graylog: total time vs the previous nights, pauses by reason, no
      "did not drain" stop, full GCs during the run.

### Hot-path speed-ups, GELF reconnects, backpressure stop (v1.16.1)

- [ ] **Fast paths are exact** (`tests/test_fast_paths_equivalence.py`): the
      fixed-shape timestamp parser never disagrees with the strptime loop it
      fronts (edge cases + 4,000 fuzzed strings, both format sets), the GELF and
      OS-direct parsers return what the old functions returned (a literal `Z`
      still read as local time, the same exceptions), field-type tracking equals
      the isinstance chain (incl. subclasses and 2^63), the reused encoder writes
      the same bytes as `json.dumps`. Archive JSON spacing is unchanged on purpose:
      the record-search prefilter matches raw bytes.
- [ ] **GELF send keeps every message accounted for**: all messages arrive with no
      fault; a reset by a receiver on its own thread is noticed, counted
      (`reconnects`) and loses only bytes in transit; a closed connection raises
      instead of silently dropping writes. Against a real Graylog (.83): 30,000
      sent, 30,000 indexed, old and new.
- [ ] **A GELF import that reconnected is never "verified"**: 0 indexer failures
      plus a reconnect gives the NOT-verified warning in the result and the job
      row; no reconnect still gives "Verified at target".
- [ ] **Backpressure stop ends the run once** (`tests/test_backpressure_stop.py`):
      the guard raises `BackpressureStop` and sends nothing; the API export stops
      inside a chunk without "Chunk N failed" and keeps only whole hours; the
      OS-direct export stops without "Index X failed" and never touches the next
      index; manual runs notify once, scheduled runs leave it to the scheduler;
      the scheduler retries once after `health_stop_retry_min` (not three quick
      retries), notifies once, adds no empty failed row, and keeps the quick
      retries for other errors. Against a real Graylog (.83): a forced stop ends
      after one pause with the "stay archived" summary.

### Server messages in the UI language (v1.16.2)

- [ ] **Translated, not printed raw** (`tests/test_srv_messages.py`): every `srv_*`
      English template exists in the backend source; zh-TW / ja keep every
      placeholder; every template translates in both languages through the real
      `i18n.js`; real composite job notes translate; unknown text and the English UI
      are unchanged; `fetchJSON()`, job notes and the setup wizard go through it.
- [ ] **In a browser** (`ui-sim-test.py` step 7b): an English job note shows in
      Chinese / Japanese / English with the UI language.
- [ ] A NEW user-facing backend message gets its `srv_*` key in all three blocks in
      the same change (otherwise it shows in English).
- [ ] **Upgrades install the Chromium build the installed Playwright needs**
      (`tests/test_report_deps_browser_build.py`); after an upgrade that changed the
      Playwright version, `verify_report_engine` passes on the staging box.

### OS release upgrade under jt-glogarch (v1.16.3) — MANDATORY for upgrade-flow changes

- [ ] `bash scripts/os-upgrade-sim.sh` prints `RESULT: ALL PASS` (docker, ubuntu:24.04,
      the real `upgrade.sh` after a simulated 22.04 → 24.04: Python-change notice,
      database backed up, reinstalled for 3.12, healthy, every schedule registered).
- [ ] `tests/test_os_upgrade_paths.py` passes; the test suite also passes on the newest
      supported Ubuntu's Python (run it in that container).
- [ ] Any new step in `upgrade.sh` that runs BEFORE the reinstall works when the
      installed package cannot be imported (a different Python).

### Retry a failed import from Job History (v1.16.4)

- [ ] **Clicked, not called** (`ui-sim-test.py` step 7c): Job History → Retry → the
      real Confirm button opens the import dialog on the Archives page with the job's
      archives, target and mode. The dialog lives only in the Archives page's block,
      so Confirm threw on Job History and did nothing from v1.13.35 to v1.16.3.
- [ ] **The mode follows what reached the target**: nothing imported → same mode,
      "cannot duplicate"; a Bulk job → Bulk (dedups by message id); a GELF job that
      sent messages → GELF with a duplicate warning (GELF never forwards
      `gl2_message_id`, so no mode can skip what it already indexed).
- [ ] Any button that opens a dialog from ANOTHER page's template block navigates
      there instead (`tests/test_retry_import_ui.py`).

### OS-direct coverage note and Graylog-internal index sets (v1.16.5)

- [ ] A schedule that selects only the log index sets: the job note has no ⚠ and
      says "Graylog internal event index sets not included: …"; the Job History
      chip is green (`tests/test_index_set_coverage.py`).
- [ ] A log index set left out still gets "⚠ … NOT covered" and an amber chip.

### Password auto-completion (v1.16.5)

- [ ] Every `type="password"` input in `login.html` / `index.html` has
      `autocomplete="off"`, and so does the login form (`tests/test_password_autocomplete.py`).
      `curl -sk https://<host>:8990/login | grep -E '<form|type="password"'` shows it.

### Look and feel (v1.18.0)

`glogarch/web/static/css/refine.css` holds the site-wide scale; colours are tokens at the top of `style.css`. `test_no_select_uses_the_browsers_own_dropdown` keeps native dropdowns out.

- [ ] `tests/test_notify_links.py` (16, v1.34.0): the jt-glogarch address is a bare http(s) origin (no path,
      query, credentials, spaces; ≤ 200 chars); with it set every incident / AI verdict notification links to
      `/security?incident=<id>`, without it no link; e-mail makes only our own links clickable, never a URL from a
      log line; the settings API stores the notification language (sent and dropped before 1.34) and the address,
      400 for a bad one; the runner passes the incident id; `/security?incident=` opens the incident.
- [ ] `tests/test_reports_poll.py` (1, v1.34.0): the Reports page polls its two lists through `startJobsPoll` and
      never redraws under the open report editor.
- [ ] `tests/test_form_fields.py` (7, v1.34.0): the setup wizard's archive path is accepted (`path` / `base_path`);
      `auth_type: password` drops a server's old token (an API call without it keeps partial-update behaviour);
      a schedule goes back to the default server only with `server_default`, an empty server alone keeps it;
      typed import credentials win over the saved token and ONE helper (`target_credentials`) serves every target
      endpoint; the security-notification switch is on the form; manual OS export sends "recent N" only when
      lowered. `tests/test_ai.py`: a masked LLM key with a new URL is dropped.
- [ ] `tests/test_sigma_library.py` (v1.34.0 additions): `version.txt` read bounded (20 MB of zeros in the zip);
      YAML aliases refused from the event stream before anything expands (a nine-level alias bomb in under 2 s);
      tags that are not a list and a 3,000-deep condition do not stop the package; unbalanced `|re` refused,
      `[(]` / `[]x]` / `[^]x]` accepted; redirects only to port 443; the download's overall deadline.
- [ ] Review fixes (v1.34.0): `tests/test_datanode.py` (two Connects at once do not freeze, colliding names
      refused, replaced CA re-issues but hostname mismatch does not, delete refused while connected, vanished
      block uses the API); `tests/test_threat_intel.py` (junk/huge/private networks skipped, shrink keeps the old
      list, streamed download with deadline, indexed matching under 1 s for 2,000 lookups on 1,500 networks,
      refresh scheduled from the last one); `tests/test_security_suppress.py` (canonical / mapped-IPv6
      entities, mapped networks refused, "/" literal entities, close only a covered incident);
      `tests/test_security_digest.py` (one fixed-time cron that runs, a bad stored cron does not stop the
      analysis job, healthy needs analysis on and a good run in the last day).
- [ ] MCP and Alerting review fixes (v1.34.0): `tests/test_ai.py` (rotating fake tokens stopped before Graylog, batch / body caps,
      per-message errors, unknown server 400, numbers clamped to the schema); `tests/test_alerting.py` (a flipped
      state put back once, unknown state skipped before writing, failed rows undoable, duplicate ids dropped).
      `scripts/e2e-alerting-test.py` ran against the throwaway Graylog 7.2.2 of `datanode-stack/up.sh` (.83 down):
      ALL PASS 2026-11-21.
- [ ] **Phone width (1.34)**: `UI_URL=https://<host>:8990 UI_USER=... UI_PASS=... python3 scripts/ui-phone-width-check.py`
      opens every page at 390 px and must print ALL PASS (no page wider than the screen; wide tables scroll
      inside their box). `tests/test_phone_layout.py` keeps the phone block last in `refine.css`. From 1.18.0
      to 1.33 the phone layout was broken (menu labels as vertical text, pages 600–990 px wide).

**By hand, after any style change**
- [ ] Every page in light and dark at about 1440 px and 1180 px: nothing crosses the page's right padding, and no number is clipped.
- [ ] Open a dropdown on a form, in a dialog and in the sidebar: the list is not cut off.
- [ ] A dropdown whose value code sets (Settings export mode) shows that value.

### Content Packs page (v1.18.0)

**Automated**: `tests/test_packs.py` (the four real packs, install checks, the library, routes against a fake Graylog that copies measured behaviour, and the publishing boundary).

**Live, in a real browser**: `tests/live_packs_check.py` uploads, edits, installs, starts, uninstalls and deletes a throwaway `ZZTEST` pack on a real Graylog, then checks nothing is left. Its stream matches a hostname that does not exist and its rule is `when false`. Ask before pointing it at production.

**Download bundle**: `tests/test_pack_guide.py` covers the SOP's text in all three languages, the facts it reads from the pack, that every SOP has the new-install, upgrade and uninstall parts, that the upgrade and uninstall checklists name what this pack leaves behind, escaping and the ZIP. `tests/live_packs_check.py` downloads through a real browser and checks that the ZIP holds the pack and its SOP.

- [ ] Download a library pack in each language: the ZIP holds the `.json` and one `.md`; the `.md` reads cleanly in a plain text editor and has the three parts, and its upgrade checklist names this pack's pipelines, rules prefix and dashboards.

**Sensitive values and versions**: `tests/test_packs.py` covers the scan, the removal and the refusal at each way out. `tests/live_packs_check.py` uploads a pack with an address in its notification and checks that what reaches Graylog holds none, and that a 6.3 download really is converted.

**By hand**
- [ ] On a site with no local packs, the Jason Tools tab lists exactly the published packs (Windows Active Directory, Linux 登入與 SSH, Apache HTTP Server, QNAP NAS), each marked published, and each download carries a translated guide. `tests/test_packs.py` fails on any pack in `glogarch/jt_library/` the owner did not agree to publish.
- [ ] Open a pack with several dashboards and check each tab's layout against Graylog.
- [ ] Dashboard preview: hovering a widget shows no browser tooltip; clicking it opens the app's box with the widget query, tab query and fields; the query text can be selected and Copy puts it on the clipboard; Esc, a click elsewhere, scrolling, switching tab and closing the viewer all close it. Check both themes at about 1436 px.
- [ ] Install a published pack with a stream on a fresh Graylog 7 (default Message Processors order) and on one with the Stream Rule Processor first: its pipeline parses in both, and a message from another source gets none of its fields.
- [ ] Dashboard preview: the tab picker is readable when hovered and when active in both themes, and a pie or donut widget has its legend under the chart.
- [ ] Sign in as a user with fewer permissions: the install preview lists what it could not read as not checked.
- [ ] A library pack whose rule titles exist on the target cannot be installed, and the reason names them.

### Alerting — Graylog event definitions + notifications in bulk (v1.17.0)

Writes go to a REAL Graylog, so the two live layers run against a TEST Graylog
(.83), never production. The jt-glogarch for the UI test must point at that test
Graylog too (a scratch config on any box; `.36` points at production log4).

**Automated**

- [ ] `tests/test_alerting.py` (32) — planning (add / remove / replace keep the
      other entries and their `notification_parameters`), the `schedule` value is
      the definition's current state, a definition edited after the preview is
      skipped, other fields edited meanwhile are kept, one failure does not stop
      the rest, an expired sign-in stops the batch, cancel, Graylog storing a
      different state counts as a failure, undo (and undo of a change that was
      sent but never confirmed), the real HTTP client (query param, whole body,
      `X-Requested-By`, 401/403 mapping, paging past 200), the identity store
      (secret never in the cookie, expiry, logout), login keeps a Graylog session
      and not the password, the API (403 + `need_signin` never 401, a plan runs
      once and only for the browser session that made it, unknown notification
      refused, undo), and node running the real `alerting.js` filters (AND, `-`,
      phrases, `notif:` / `notif:none` / `tag:` / `prio:` / `state:`, presets,
      shift-click range, quick-filter counts == health counts).
- [ ] `GL_URL=http://<test-graylog>:9000 GL_PASS=... python3 scripts/e2e-alerting-test.py`
      prints `RESULT: ALL PASS` — 30 real definitions (12 disabled): add to all
      (no state change, every other field byte-identical), edit-between-preview-
      and-apply skipped, replace, undo restores exactly, the Graylog system
      definition is never written, a Reader-role user changes nothing, cleanup.
- [ ] `UI_URL=https://<jt-glogarch-on-test-graylog>:8990 GL_URL=... GL_PASS=...
      RESTART_CMD='...' python3 scripts/ui-alerting-test.py` prints
      `RESULT: ALL PASS` — real clicks: log in with a Graylog account, tag chip,
      search, shift-click, select all matching, Add → Preview → Apply, the result
      checked IN GRAYLOG (all 15 have it, the other tag untouched, no state
      changed), the loading state (data request held: spinner in the toolbar and
      table, every spinner actually turning, its arc at contrast >= 2 against the
      track, action buttons disabled), the layout (toolbar items on one centre
      line, filter labels in one column, every tab pane opens with a card, title
      and description styled differently), clicking a title opens the live
      definition with a link into Graylog, Job History row, Undo from Change history, health cards, zh-TW,
      and after a service restart the page asks to sign in again and the dialog
      works. No JS errors.

**By hand (each release that touches Alerting)**

- [ ] Light + dark theme, en / zh-TW / ja, and a 400 px wide window: the page
      looks like the other pages (toolbar card, tabs, table, pagination).
- [ ] Log in as `localadmin`: the page asks to sign in to Graylog; changes then
      run as that Graylog user, and the audit line names both.
- [ ] A Graylog user without edit permission: the preview loads, Apply stops at
      the first definition with "Graylog refused this for your account".
- [ ] Logout closes the Graylog session (`DELETE /api/system/sessions/{id}`).

### Zulip notification channel (v1.17.1)

**Automated**

- [ ] `tests/test_notify_zulip.py` (8): what goes on the wire, against a real httpx
      client on a MockTransport — `POST {server}/api/v1/messages`, Basic auth with
      the bot email + API key, form `type=stream`, `to`, `topic` (default
      `jt-glogarch`), the body in a code fence; Zulip's own error text on 4xx
      ("HTTP 401: Invalid API key"); missing settings fail without sending; a
      message containing ``` cannot close the fence; real notifications AND "Send
      test" go through the ONE channel list (`deliver_to_channels`); the settings API
      masks the key, keeps it when the form posts the masked value, and refuses a
      link-local server URL.
- [ ] `tests/test_notify_test_endpoint.py`: `_send_zulip` signature, and the shared
      channel list calls every channel with the right arguments.
- [ ] `ui-sim-test.py` step 1b: the Zulip card is on Notify Settings, ticking
      Enable shows its fields and unticking hides them (a channel that started
      disabled — the case that was broken for every channel), only the API key is a
      masked field (read-only, nothing is saved).

**Manual (every release that touches notifications)**

- [ ] Fill in a real Zulip bot (server URL, bot email, API key, stream), save, press
      **Send test notification**: the message arrives in that stream/topic with the
      title in bold and the body aligned; reload the page — the key is masked and
      still works.
- [ ] A wrong API key: the test result says "HTTP 401: Invalid API key".

### Graylog Data Node access, beta (v1.19.0)

**Automated**

- [ ] `tests/test_datanode.py` (22): hosts from `transport_address` (nodes not
      serving skipped; 6.3's `data_node_status` read too); a 6.3 `roles` refusal
      retries with one `role`; the Test button and capacity probes keep the
      certificate; the listing endpoint is `/api/system/cluster/datanodes`
      (the dashboard probe tries it first); principal unique per server; a plain
      OpenSearch block keeps `verify=bool` + Basic auth, a certificate block sends
      NO Basic auth and pins the CA (hostname only with `verify_ssl`); a missing
      file is a clear error; expiry read with the stdlib; PEM files 0600 in a 0700
      dir, no temp files left; renewal timing (a third of the lifetime, at least
      7 days, never more than half); a failed renewal keeps the working
      certificate; only 401/403/bad-certificate re-issues; an import target picks
      up ONLY certificate blocks; bulk + preflight route through the config; a
      scheduled OS run with an unusable certificate archives via the API and
      notifies once; editing a server keeps the block and never returns the key
      path; connect refuses `http://`; disconnect asks when OS schedules use it.
- [ ] **`scripts/e2e-datanode-test.py` against a REAL Data Node** (MANDATORY for
      any change to the Data Node / certificate / OpenSearch client path):
      `bash scripts/datanode-stack/up.sh` (Graylog + Data Node + MongoDB in
      docker, loopback, memory-capped; prints the env), then run it; must print
      `RESULT: ALL PASS`: connect, seed + rotate, OS-direct export of every seeded
      message, Bulk import of all of them, forced renewal, recovery after the role
      mapping is removed behind our back, scheduled fallback to the API,
      disconnect. `bash scripts/datanode-stack/down.sh` removes it. Run it on
      more than one Graylog line (`GL_VERSION=6.3.15 / 7.0.15 / 7.1.11 / 7.2.2`):
      6.3 differs in the certificate request (one `role`) and the status field.
      Step [6b] (2026-11-27): the Data Node container is stopped -> 4 tries then reported, no new
      certificate; started again during the wait -> used directly. `tests/test_datanode.py`: an unreachable
      node is tried after 1, 2 and 5 minutes, the first success ends the wait, a refused certificate is not
      waited for, manual runs do not wait, the fallback notification says how many tries and minutes.
- [ ] Dashboard Hardware Sizing card (2026-11-27): one row per resource (this host / recommended /
      Enough or Not enough), archive disk with a bar of months held vs retention, then only the actions;
      check an archive-only host and a co-located one, both themes and 390 px.

**By hand (each release that touches it)**

- [ ] Settings → Graylog servers → Edit a Data Node server: the box lists the
      nodes, Connect with the default host (or an IP) shows "Connected: … green";
      the per-server OpenSearch fields hide; Test / Renew / Disconnect work; en /
      zh-TW / ja and both themes read correctly at ~1436 px.
- [ ] Export page: the Data Node server is not locked to Graylog API once
      connected, and the hint says beta; the import dialog allows Bulk.

### Security incidents (v1.20.0)

**Automated**

- [ ] `tests/test_security_incidents.py` (30): thresholds and severity per detection
      (external sources rank higher; Suricata severity 1 is high, 2 only in volume, 3
      never); the "(Empty Value)" bucket is coverage, never an incident; every peer
      field is tried (`client_ip` for the WAF); detections sharing a search share one
      aggregation; one failing search is recorded and the rest still run; per-site
      thresholds and exclusions, the machine-account regex; an entity is quoted in the
      Graylog query; incident lifecycle (new, ongoing, escalated, never lowered, new
      after `reopen_hours`, closed then new, NEW badge and learning period); notify
      decision (held while ongoing, again after `renotify_hours`); notification text
      neutralised (control characters, markdown, backticks) and e-mail/Slack bodies
      escaped; OFF by default, saving the settings registers / removes the scheduler
      job; API validation, status changes audited, Graylog link; an unreachable
      Graylog is a failed run and alerts once at three; two real runner passes notify
      once (DB timestamps end in `Z`).
- [ ] **`scripts/e2e-security-test.py` against a REAL Graylog** (MANDATORY for any
      change to `glogarch/security/`): `bash scripts/datanode-stack/up.sh`, then run
      it with the printed `GL_URL` / `GL_PASS` / `GELF_PORT`; seeds authentication
      events over GELF and must print `RESULT: ALL PASS` (four login detections,
      distinct accounts/hosts counted by Graylog, the second search, an event without
      a peer field counted as coverage). Never against production: it writes events.
      2026-11-19: ALL PASS on 6.3.15 and 7.2.2. 2026-11-21 (1.34.0): ALL PASS on 7.2.2 (29 checks).

**By hand (each release that touches it)**

- [ ] Security Incidents page on a test instance pointed at real data: Run now
      finishes with a count of searches; incidents list with severity, NEW, the
      Graylog link opens the matching search; Acknowledge / Close / Reopen; Coverage
      marks a field empty in every event in red and an unused alternate in grey;
      Settings save and the next-run time appears. en / zh-TW / ja, both themes,
      ~1436 px. Do not enable it on a site whose notification channels reach people
      unless they expect it.

### AI chat and MCP endpoint (v1.21.0)

**Automated**

- [ ] `tests/test_ai.py` (33): the vendored mcp_graylog matches its manifest and loads on this
      Python (1.10.2: 3.10 too); when it cannot load, its status says why and the built-in tools
      still work; its import leaves the root logger and `~/.mcp_graylog.log` alone;
      `find_silent_sources`' look-back is capped; a `*` / `*:*` query becomes empty and another leading
      wildcard is refused; the three message-pulling tools are opt-in; the SDK stand-in is used only without the real
      SDK; time ranges parsed or refused, the pull cap and the 31-day cap; unknown tools/arguments
      refused; exact `top_values` through the aggregation API; results over the budget kept and paged (1.36); LLM
      replies (native tool calls, `<tool_call>` text, `<think>` stripped); private-first URL check,
      metadata addresses always refused; token budgets; the chat loop (tool round, forced answer
      after the last round, empty answer asked again, a `</data>` inside a tool result cannot close
      the data block, every tool call audited with user and IP); MCP methods, version negotiation,
      notifications, batches, Bearer/Basic token, rate limit; `/mcp` off by default, 401 without a
      token, 403 for a refused token, 202 for notifications only; settings keep a masked key, drop
      the key when the URL changes, refuse an external URL unless allowed (audited); chat needs a
      Graylog sign-in; another user's conversation is not found; the page's Markdown renderer
      (run in node) escapes before formatting and allows https links only.
- [ ] `tests/test_ai.py` (v1.33.1 additions): a reply cut at the length limit is continued and joined without
      repeating the cut line, every request asks for `ANSWER_TOKENS`, one still cut after the continuations is
      marked `truncated`; **against a real uvicorn** (TestClient reads every response to its end, so it cannot
      leave a page): an answer goes on after the stream is closed, the list and the conversation say it is
      running with its progress, a second question to it is 409, the answer is stored with its time; Stop ends
      one left running ("Stopped", audited); page wiring (copy / edit / answer again, follow, keys).
- [ ] `tests/test_ai.py` (v1.34.0 additions): each tool call is kept with the answer as a record of the query,
      the absolute range it ran over and its count / rows, never the rows or log text (and a result cut at
      the cap still records the arguments); the stored queries come back with a link to the same search in
      Graylog, per call server, none for a server since removed; conversations are found by title or message
      text (`%` / `_` literal, another user's never) and renamed (blank / too long 400, another user's 404,
      audited); a question left unanswered is answered once with `retry` (not stored twice, 409 when the last
      message is an answer, audited `retry=1`); an old `ai_messages` table gets `calls`; streaming: the client
      assembles text, tool-call deltas and usage from the chunk shapes measured on the owner's llama.cpp,
      keeps `<think>` off the page, falls back to plain requests after an HTTP 400 and remembers it, turns a
      dropped connection into an LLM error, estimates tokens when no usage is sent; the chat loop resets the
      text when a round turns into tool calls and streams a continuation onto what is shown; **against a real
      uvicorn** a page that comes back reads the text written so far; number columns are right-aligned (node);
      the Markdown download (node) escapes `|`, demotes the answer's headings, lists the queries; a tool whose
      result does not report its range (mcp_graylog) gets it from its arguments and defaults, and a failed call
      keeps its query; page wiring (incident examples read `incidents`).
- [ ] `tests/test_login_identity.py` (5, v1.33.1): a Graylog login is signed out after a service restart (its
      Graylog identity is gone) and signing in again gives it back, `localadmin` is not; a login also signs in
      on every other configured server that accepts the account and leaves out one that refuses it; the model
      list (`POST /api/ai/models`) reads the URL in the form, sends the stored key only to the stored URL,
      reports an LLM error as 502; the model is a list, not a text field.
- [ ] `tests/test_ai.py` reasoning (4, v1.35.0): `chat_stream` passes `reasoning_content` / `reasoning` / a `<think>` block in content to `on_reasoning` as it grows, throttled, and ALL of it before the first answer text; `run_chat` emits `reasoning` deltas and a reset per request; a page that comes back gets `run.reasoning`; reasoning is never stored. Manual: ask a reasoning model a question with tools and watch the thinking box fill from the first seconds, fold when the answer starts, stay as you set it after a click.
- [ ] `tests/test_ai_query_syntax.py` (51, v1.35.0): every Graylog query form measured to give a wrong count or an error on Graylog Open 7.2.2 (regex flags, lower-case operators, leading wildcards, unquoted CIDR, a group without an operator, `OR NOT`, Enterprise `$name$` parameters) is refused by `call_tool` before Graylog is asked, with how to write it; every measured right form passes; the system prompt carries the rules and the Open / Enterprise difference.
- [ ] `tests/test_api_heap_hint.py` (12, v1.35.0): the API export estimate is about 200 records/s per GB of Graylog heap and counts as heap-bound under 4 GB; `GET /api/servers/api-heap` reads the chosen (or default) server's `/api/system/jvm`, caches it, says `available: false` for an unknown server or an unreadable Graylog, and `api_in_use` follows the default export mode and enabled API export schedules of that server; the export / schedule dialogs show the hint only for API mode on a small heap (latest choice wins), the sizing card only when API mode is in use; the text has its placeholders in all three languages.
- [ ] `tests/test_ai.py` follow-up questions (v1.35.0): `split_followups` takes the questions after the `[[follow-up]]` line (bullets, numbering, quotes stripped; at most 3, ≤ 200 characters, no repeats); while the answer streams the marker or its beginning never shows, and what was streamed equals what is stored; a cut-off answer offers none; they are stored (`ai_messages.followups`, migrated on an old database), returned in the done event and the conversation; the page shows them under the last answer only, escaped, and a click sends the question.
- [ ] `tests/test_ai.py` model-server wait notice (v1.35.0): no streamed chunk for `llm.SILENT_SEC` (no headers, or headers and no chunk) → `on_silent(True)`, then `on_silent(False)` at the first chunk, before any text; a server that answers at once gives none; a failing notice never fails the request; `run_chat` emits `waiting_model` and then the phase line it was on; the page translates it in all three languages.
- [ ] `tests/test_export_gap_refill.py` (14, v1.35.0): a chunk that failed in an earlier scheduled API run is
      exported again. `Exporter.find_gaps` returns holes between archives only (any stream, this server; not
      time before the first archive; under 60 s ignored; cut at the window); `export(refill_windows=)` exports
      them FIRST in the same job, pre-counts only the holes and the new range, never fetches archived hours, and
      runs even when there is nothing new; `_run_export_once` passes the holes behind the resume point within
      `gap_refill_hours` and the schedule's days, passes nothing when there are none (a healthy site's run is
      unchanged) or when it is 0; the Schedules page's Run now uses the same plan (`Exporter.plan_scheduled_run`); a timeout is noted as "Chunk N failed: ReadTimeout", not an empty reason.
      Live: on .36 the 03:00 run after 1.35.0 must refill 2026-11-21 03:00–04:00Z (note "Refilled 1 gap(s)").
- [ ] `tests/test_archive_status.py` (7, v1.35.0): the `archive_status` tool (chat + `/mcp`, replaces
      `archive_coverage`) gives per server the archive count, earliest/latest, hours since the latest and the
      GAPS (overlaps and touching archives merge, holes under an hour are left out, newest first, capped);
      corrupted/missing/tampered/failed archives; running jobs with an ETA; the last export/verify/cleanup
      jobs (report cleanup left out) with their notes cut to 300 chars and 7-day counts; schedules with the
      next run from the same rule as the Schedules page (`scheduler.next_fire_time`); disk free and months
      left. Manual: ask the chat "how is archiving doing, did last night's export work" and check the answer
      against Job History and the dashboard.
- [ ] `scripts/check-mcp-graylog.py` (run by `run-tests.sh`): the vendored file matches its
      manifest and is the published upstream version; a newer upstream fails the release check
      (`--update` takes it in whole).
- [ ] **`scripts/e2e-ai-test.py` against a REAL Graylog** (MANDATORY for any change to
      `glogarch/ai/` or `web/routes/ai.py`): `bash scripts/datanode-stack/up.sh`, then run it with
      the printed env (and `AI_URL` / `AI_MODEL` / `AI_KEY` for the real-LLM step). It seeds 60
      failed logins, then checks exact counts, `/mcp` with a token Graylog issued (and a bogus one
      refused, audited), mcp_graylog through MCP (`get_log_sample`, `analyze_source_distribution`,
      `find_silent_sources` and its look-back cap, `*:*` answered quickly, the message-pulling tools
      not offered by default), that a real LLM states what its own query
      returned (whether the model picked the right query is printed as WARN), and (step 5) that a
      real detector run opens the password-spraying incident, its AI-analysis evidence matches
      Graylog, and a real model returns a valid verdict naming no address missing from the
      evidence. 2026-11-19: ALL PASS on Graylog 7.2.2 with Python 3.10 and (in docker) 3.12;
      2026-11-20 (1.33.1): ALL PASS on 7.2.2, Python 3.10. 2026-11-21 (1.34.0): ALL PASS on 7.2.2 (28 checks,
      incl. the streamed text adding up to the stored answer and each query recorded with its range).

**By hand (each release that touches it)**

- [ ] AI Chat page against a test Graylog: sign in to Graylog on the page, ask a question, watch the
      progress line (round, tool), read the answer with its query, model, time, tokens and tools;
      Stop works; conversations list, reopen and delete; Settings: test connection, save, MCP config
      snippet, mcp_graylog status. Ask, go to another page, come back: the list says "Answering…",
      opening it follows the progress and the answer arrives whole; hover a question / an answer / a table
      (copy, edit, answer again, copy table); message times; model picked from the list. (1.34) The answer
      streams in with a caret and the elapsed time counts; leave and come back mid-answer, the text so far is
      there and grows; "Queries: N" opens each query with range and count, Open in Graylog shows the same
      search and count; search the list (title and message text), Today / Yesterday groups; rename in the
      header (Enter / Esc); Download as Markdown; Stop, then "Answer it" answers once (also after a reload);
      number columns right-aligned.
      en / zh-TW / ja, both themes, ~1436 px.
- [ ] **`scripts/ui-ai-chat-test.py` (1.34)** against a jt-glogarch whose AI chat is on: `UI_URL=... UI_USER=<Graylog
      login or token> UI_PASS=... python3 scripts/ui-ai-chat-test.py` must print ALL PASS (streaming with caret and time,
      leaving and coming back mid-answer, the Queries panel with Graylog links and copy, rename / search / Markdown
      download, Stop at once then "Answer it" answered once, deleting the followed conversation frees the page; it
      deletes what it created). 2026-11-21 on .36 with the owner's LLM: ALL PASS (17 checks).

### mcp_graylog 1.12.0 event tools and Zulip formatting (v1.35.0)

**Automated**

- [ ] `tests/test_ai.py::test_event_tools_are_offered_and_search_events_gets_the_long_range`: the five event
      tools are offered by default, debug tools never; `search_events` may cover 31 days, message tools 24 h.
- [ ] `scripts/e2e-ai-test.py` `events_step` (real Graylog): an HTTP notification whose URL holds a token and
      whose description holds an e-mail, a URL and an IP, bound to an event definition; through /mcp
      `list_event_definitions` names both, `list_event_notifications` and `get_event_definition` return none of
      the URL, token, password or addresses, `search_events` over 2 days finds the triggered event and
      `get_event_source_messages` its messages. 2026-11-22: ALL PASS on 7.2.2 (with the real LLM) and 6.3.15.
- [ ] `tests/test_notify_zulip.py`: one bold-label line per figure, no code block, list items for errors,
      rich code spans kept, log text sent as entities (no formatting, mention, stream link, emoji, KaTeX or
      link); `rich` reaches the Zulip sender from the channel list.

**Manual**

- [ ] A Zulip notification on a phone and a desktop: no sideways scrolling, figures one per line.

### Security notification layout, incident context and WAF blocking (v1.35.0)

**Automated**

- [ ] `tests/test_security_incidents.py`: a scan the WAF blocked (let through < min_count) is low; partly
      through keeps its severity with blocked / passed; 1,000+ (or the detector's `blocked_min_count`) keeps
      it; the blocked count failing leaves the incident as before; the blocked query comes from the field map;
      the runner stores `metrics.context` and notifies with it.
- [ ] `tests/test_security_context.py`: context = top 3 per field over the incident's own query, site field
      names, the entity field skipped, nothing for a silent host, a failed field left out, at most 12 findings
      (highest first).
- [ ] `tests/test_notify_rich.py`: heading + one labelled line per item (no duplicate labels), reporter / site
      / paths / responses / WAF line; bold only on our headings and labels (Telegram, Zulip, Slack `*`), a link
      line and a value with a colon are never labels.
- [ ] `scripts/e2e-security-test.py` `waf_step` (real Graylog): 30 blocked events -> low, 10 blocked + 20
      through -> medium with blocked/passed; the context names the reporting host, the site, the responses
      (mapped `http_status`) and 3 paths.

**Manual**

- [ ] A security notification on Zulip / Telegram, phone and desktop: heading bold, labels bold, no sideways
      scroll; the Security page shows the context lines and the WAF result under each incident's figures.

### Field mapping for the built-in detections (v1.35.0)

**Automated**

- [ ] `tests/test_security_fieldmap.py` (13): with no map the probes are EXACTLY the old ones (same searches
      after an upgrade); validation (unknown key, one field, at most 4, `gl2_*` / non-field names, query length,
      defaults and empty boxes not stored); a broken stored map falls back key by key; the engine counts the
      mapped fields and stores metrics under GIM names (`card:user_name`), queries name the mapped field, the
      machine-account exclusion follows the account field; mapped queries for IDS / WAF / silent / volume /
      success-after-fail / new-source; the detector rows and the AI evidence use the map; `candidates()` picks
      by value shape and name (not `useragent`, `request_id`, GeoIP-derived fields; destination-like last);
      `detect()` on a log4-shaped fake: exact shares, events with none of the fields named by input, no
      sampling when the query matches nothing; API: save (400 on bad, stored only non-defaults, audited),
      the general settings save never writes the map, detection tries the form as sent.
- [ ] `scripts/e2e-security-test.py` `fieldmap_step` (real Graylog): non-GIM login events are invisible with
      the defaults and found once mapped (bruteforce, spray, success-after-fail via `IpAddress`, metrics under
      GIM names, coverage 65/5), and `detect()` finds `IpAddress` / `TargetUserName` with Graylog's exact
      `count(field)` (with + without = all). 2026-11-22: ALL PASS on 7.2.2 and 6.3.15.

**Manual**

- [ ] Security → Settings → Field mapping: Find fields on each group shows counts and examples; Use fills the
      box (a list field puts it first); Save, Export, Import, Back to defaults; both themes at about 1436 px.

### Rich security notifications (v1.32.1)

**Automated**

- [ ] `tests/test_notify_rich.py` (4): Telegram rich HTML escapes title and body, turns code spans into
      `<code>`, uses only b / i / code, no `<pre>` and no backticks; job notifications keep `<pre>`; incident
      and AI notifications are sent rich, have no indented lines, one block per incident with the entity on
      its own line; the e-mail HTML is paragraphs with escaped code.

**Manual**

- [ ] A real incident notification in Telegram (phone) and e-mail reads as formatted text, not a code block.

### Weekly security summary (v1.32.0)

**Automated**

- [ ] `tests/test_security_digest.py` (6): contents over 7 days (new by severity vs older incidents, top
      detections, open, cases, runs, suppressions matched, risk); health (no run = warning whatever the
      incidents, more failures than good runs = warning); the text (warning title for a week without runs,
      "turned off" stated, counts, our detection names plain, log text cannot start a line); API (cron
      validated, empty box keeps the stored schedule, preview gives the exact text, send, a send failure is a
      502 with the reason, audit); schedule off by default, POSIX day of week, a bad stored cron falls back;
      labels and placeholders in all languages.

**Manual**

- [ ] Security → Settings: Preview shows the text in the notification language; Send now asks first and
      arrives in a real channel; after saving with the switch on, the job `internal-security-digest` exists.

### Suppressions (v1.31.0)

**Automated**

- [ ] `tests/test_security_suppress.py` (7): entity normalization (networks canonical, too-wide networks,
      bad values refused); matching (exact, every detection, every server vs one server, IPv4/IPv6 networks,
      a name never inside a network, expired ignored, log values not trimmed); hits counted; the API
      (validation messages, network canonicalized, close the incident, same entry replaces reason and expiry,
      Sigma detections, delete, audit); the runner drops a suppressed finding before it becomes an incident
      and records the hit; prune keeps live and recently expired entries; UI wiring, escaped confirm, labels
      in all languages.

**Manual**

- [ ] Incidents: the suppress button opens the dialog (detection or every detection, entity editable,
      reason required, expiry, close the incident); after saving the incident is closed and the entry is in
      Suppressions under the table; Run now with the entity still active increases its matches; removing it
      asks first. en / zh-TW / ja, both themes, ~1436 px.

### Unusual message volume (v1.30.0)

**Automated**

- [ ] `tests/test_security_anomaly.py` (10): off by default (no aggregation of all messages unless enabled);
      both fields collected, one failing field does not stop the other; the usual rate counts quiet hours as 0
      and leaves out days the analysis did not run, needs 5 days; a spike against a learned history (metrics,
      query with exclusions, medium at >= 20x); thresholds (5x, min per hour, a 30-minute window scaled to per
      hour, a noisy history inside its spread is not a spike); learning (history < 7 days, a never-seen host);
      one row per hour, last run wins, prune; the runner decides BEFORE recording this run's volume; not mapped
      to ATT&CK; labels in all languages; the AI evidence explains the metrics.
- [ ] `scripts/e2e-security-test.py` (real Graylog): a 600-message burst is counted per host and per category
      by the two real aggregations, the history logic against 10 days of 20/h finds both (30x, medium), and the
      incident's query finds the burst. 2026-11-20: ALL PASS on 7.2.2.

**Manual**

- [ ] Security → Settings: the detection row says the minimum is per hour and that it needs 7 days of history.

### Account logged in from a new source (v1.29.0)

**Automated**

- [ ] `tests/test_security_new_source.py` (4): off by default; pairs collected from two groupings
      (empty values are coverage, machine accounts excluded); learning (account history < 7 days),
      memory (a source unused for 30 days is new again), one finding per account with its new sources,
      severity by external source, a pair seen now is known next run; prune forgets old pairs; T1078
      and labels in all languages.
- [ ] `scripts/e2e-security-test.py` (real Graylog): the two-grouping aggregation returns the seeded
      (account, source, 3) and the history logic flags the account. 2026-11-20: ALL PASS on 7.2.2.

### Security overview (v1.29.0)

**Automated**

- [ ] `tests/test_security_overview.py` (5; plus the CSV export: filters, formula cells neutralized,
      techniques column, audit): the summary (14 local days, per-severity counts, open by
      severity, cases, top detections and techniques, risk top, days clamped to 90); the chart is SVG
      with no inline style (the CSP), one segment per non-zero severity, a title per day, a legend;
      ATT&CK "watched" merges the last 24 hours of runs (a quiet run does not turn a detection into
      no data); i18n keys.

**By hand (each release that touches it)**

- [ ] Security Incidents opens on Overview: tiles (incidents and investigations open their tabs), the
      chart's hover numbers and table view, the three lists. en / zh-TW / ja, both themes, ~1436 px.

### Threat intelligence (v1.28.0)

**Automated**

- [ ] `tests/test_threat_intel.py` (10): feed parsing (comments, junk, CIDR normalized); matching
      (address and network, several feeds, non-addresses); refresh replaces a feed, a failed one
      keeps the previous entries and records the error; an empty or oversized feed is refused and
      only fixed https URLs are fetched; off by default and only selected feeds are used; the risk
      factor x2; the API (settings clamp and filter feeds, refresh refused while off, incidents and
      ranking marked, audits); the AI evidence explains the listing; the scheduler job follows the
      switch and interval; i18n keys.
- [ ] `scripts/upgrade-compat-test.sh`: `sec_ti_entries` and `sec_ti_feeds` are created.

**By hand (each release that touches it)**

- [ ] Assets & risk tab: turn the lists on, Download now (three counts and times), an incident from a
      listed address shows the list tag and a x2 factor. en / zh-TW / ja, both themes, ~1436 px.

### Review fixes (v1.29.0)

**Automated**

- [ ] `tests/test_security_review_fixes.py` (9): an empty settings box keeps the stored value and
      numbers are clamped (retention never 0); scheduled and manual runs share one lock; Run now
      answers before the AI finishes; an unparsable network asset does not break risk; whole-address
      comparison and `:port` in the unverified check; mid-query leading wildcards refused for
      mcp_graylog; an unexpected LLM error leaves a row; confirm dialogs escape user text; the case
      report cannot carry links or HTML (node).

### Sigma rules (v1.27.0)

**Automated**

- [ ] `tests/test_security_sigma.py` (66): conversion of every supported shape (NOT kept as NOT inside an OR,
      `|re` anchoring, literal `\*` and `<>=` escaped) (equality as a
      phrase, lists, `all`, startswith wildcard, contains/endswith/leading-wildcard as regex,
      Lucene escaping, literal `\*`, null/exists, numeric comparisons, `re`, keywords, list of maps,
      and/not, `1 of`, `all of them`, parentheses, condition lists); `message` searched as a
      phrase and `short_message` mapped to it, regex refused there; the field map; 16 refusals each
      with its reason (base64, cidr, regex flags, aggregation, near, unknown selection, no match,
      unclosed parenthesis, inner keyword wildcard, non-numeric gt, empty selection, no condition,
      no title, no detection, two documents, bad YAML) and the size cap; level, id and ATT&CK tags;
      the engine (per group, threshold, empty group, a failing rule recorded, the global exclusion);
      DB rules and results; the notification uses the rule title and techniques; the API (preview,
      add, enable, the cap, a field map that reconverts, test, delete, audits); a rule's incident
      shows its title and techniques; the page escapes rules (node); i18n keys.
- [ ] `scripts/e2e-security-test.py` (real Graylog): a converted rule with a phrase, a contains
      regex, a startswith wildcard and NOT endswith counts exactly 15 per host on 3 hosts (45);
      `short_message|contains` matches the 61 messages. 2026-11-20: ALL PASS on 7.2.2 and 6.3.15.
- [ ] `scripts/upgrade-compat-test.sh`: `sec_sigma_rules` is created on an upgraded DB.

**By hand (each release that touches it)**

- [ ] Sigma tab: paste a refused rule (reason shown, translated), paste a good rule (Convert shows
      the query and ATT&CK chips), save (disabled), enable, Test 24 h, field map save reconverts;
      an incident from a rule shows its title. en / zh-TW / ja, both themes, ~1436 px.

### SigmaHQ rule library (v1.33.0)

**Automated**

- [ ] `tests/test_sigma_library.py` (9): a release zip read in memory (`rules*/…/*.yml` only, duplicate ids and
      files without an id skipped, a rule that does not convert kept with its reason, fields after the field map,
      keywords → `message`), size limits (zip, expanded size, not a zip, no rules); only https GitHub hosts;
      refresh: download, then "current" without downloading, a redirect to another host refused and the library
      kept with the error; rules added from the library follow a new release (enabled / group by / threshold
      kept, disabled when it no longer converts, auto update off leaves it), a pasted rule with the same id is
      never replaced; API (off by default, refresh refused while off, unknown package, filters: convertible /
      fields in Graylog / log source / level / text, add = disabled + `origin=library`, already added, field map
      reconverts the library, audits); schedule off by default; page wiring and i18n.
- [ ] `scripts/e2e-security-test.py` `sigma_library_step` (real Graylog, GitHub stand-in): the package is stored,
      Graylog's field list is read from `/api/system/fields`, a rule on a field Graylog never saw is marked, and
      the library entry's query counts 45 like the pasted rule. 2026-11-20: ALL PASS on 7.2.2 and 6.3.15.
- [ ] `scripts/upgrade-compat-test.sh`: `sec_sigma_library`, `sec_sigma_library_meta` and `sec_sigma_rules.origin`
      exist after an upgrade.

**By hand (each release that touches it)**

- [ ] Sigma tab: Download settings (on, package), Check now downloads (release, counts, Graylog fields shown),
      filters, a missing field struck through, Add / Add selected (rules appear disabled in Sigma rules with a
      SigmaHQ link), Download again. en / zh-TW / ja, both themes, ~1436 px.

### Log source went silent (v1.26.0)

**Automated**

- [ ] `tests/test_security_silent.py` (6): off by default; two windows (baseline ends where the
      recent one starts), the global exclusion applies; still sending / under min_count / empty
      are not silent; min_count configurable; a truncated recent list reports nothing and says
      why; a failed query is recorded; ATT&CK T1562 and labels in all languages.
- [ ] `scripts/e2e-security-test.py` (real Graylog): a host whose 60 messages are 3 h old is silent
      with baseline 60, a host still sending is not. 2026-11-20: ALL PASS on 7.2.2 and 6.3.15.

### Assets and risk ranking (v1.25.0)

**Automated**

- [ ] `tests/test_security_risk.py` (24): asset values validated and normalized (addresses,
      networks, case-insensitive hosts/accounts, markup refused); matching (exact address over
      networks, narrowest network, v6 never in a v4 network, accounts case-insensitive); the score
      and its explanation (severity, external, asset criticality, AI verdict; closed incidents do
      not count; order); assets in the DB (upsert by kind+value, unknown id, delete); the API
      validates, refuses editing into another asset (409), marks incidents, ranks, imports lines
      with per-line errors, audits; AI evidence and the chat's ranking tool know the asset; the page
      escapes asset names and criticality (node); i18n keys.
- [ ] `scripts/upgrade-compat-test.sh`: `sec_assets` is created on an upgraded DB.

**By hand (each release that touches it)**

- [ ] Assets & risk tab: add, edit, delete and import assets; an incident on an asset shows the
      tag; the ranking's window select; a score opens into its incidents and factors. en / zh-TW /
      ja, both themes, ~1436 px.

### Investigations / cases (v1.24.0)

**Automated**

- [ ] `tests/test_security_cases.py` (8): case lifecycle and the append-only timeline (created,
      incident added/removed, status/assignee/conclusion changes, notes; duplicates and unknown
      incidents ignored; reopening clears closed_at; unknown case = None); fields outside the
      whitelist are ignored; retention keeps incidents that are in a case; the chat tools read
      cases; the API validates (title, severity, status, empty note, no incidents), 404s, lists
      the case on its incidents, and audits every change with the signed-in user; the case dialog
      escapes titles, notes, entities and refuses a non-http Graylog link (node); the Markdown
      report escapes free text, code-spans log values and survives a backtick; i18n keys.
- [ ] `scripts/upgrade-compat-test.sh`: the three new tables are created on an upgraded DB.

**By hand (each release that touches it)**

- [ ] Security Incidents page: Case button on an incident → new case → the dialog: edit title,
      status, severity, assignee, description, conclusion, Save; add a note; remove an incident;
      Download report; the incident row shows the case badge; the Investigations tab lists and
      filters cases. en / zh-TW / ja, both themes, ~1436 px.

### MITRE ATT&CK mapping (v1.23.0)

**Automated**

- [ ] `tests/test_security_attack.py` (19): every detection maps to known techniques and tactics;
      MITRE URL paths; IDS signatures by keyword (scan, exploit, web attack, malware/C2, DoS,
      brute force; INFO/POLICY map to nothing); coverage states (watched, no data, query error,
      turned off, not run yet, IDS signatures only; a technique takes the best of its own detections,
      signature-only when only the IDS sees it; tactic order kept);
      the notification line carries the ids; AI evidence and the chat's incident tool carry them;
      the incidents API and `/api/security/attack`; the page's chips are escaped and link only to
      attack.mitre.org (node); i18n keys in all three languages.

**By hand (each release that touches it)**

- [ ] Security Incidents page: technique chips under the detection name open MITRE's page; the
      ATT&CK button shows the tactic table with states matching the Coverage table. en / zh-TW /
      ja, both themes, ~1436 px.

### Security pages and Sigma select-all (v1.36.1)

- [ ] `tests/test_sigma_library.py`: `ids_only=1` returns only addable ids; `/api/security/sigma-bulk` enables up to `sigma_max_rules` and reports the rest as `cap`, disables, refuses a non-boolean. `tests/test_security_attack.py`: every tactic / technique in `attack.py` has en (= MITRE), zh-TW and ja names. `tests/test_phone_layout.py`: untranslated text hidden until `.i18n-ready`, shown after 1.2 s anyway.
- [ ] By hand (~1436 px, both themes, 390 px): incidents list columns aligned, icon buttons one size, verdict dot, dates on two lines; overview chart about 210 px high, tiles one height and left-aligned; ATT&CK matrix in Chinese with English under it, states in one column; Settings / Coverage / ATT&CK each collapse from their own button and the bar button shows pressed; Sigma library: header box selects the page, "select all N matching", add in batches; Sigma rules: select all, enable / disable, cap message; no English flash when moving between pages.

### AI chat: statistics, paging, budgets, loops, several LLMs, preview (v1.36.0)

**Automated**

- [ ] `tests/test_ai_136.py` (33): loop guards (an exact repeat and a reworded sentence in the
      reasoning are caught; tables, HTML and lists of hosts are not; a looping answer is cut to its
      first copy; the same call whatever the key order); kept results (a big result becomes valid
      JSON within the budget with a summary of every column; `read_result` where / contains / sort /
      group / fields; text in pages; another user cannot read it; expiry); `aggregate` (the Graylog
      request, the hidden count(field) probes, first/last seen as ISO times, time buckets made coarser,
      more than 10,000 rows refused, a missing metric field noted); `summarize_messages` (pages of 500,
      patterns merged when they differ in one word); paging past Graylog's 10,000 window refused; model
      profile (llama.cpp `/props`, `/v1/models`, the setting wins, unknown assumed); a small context
      gets the core tools only and smaller results; repeated tool calls not run again; a reasoning
      loop stopped and asked again once, twice = stopped; history keeps the newest turns with their
      queries and lists older questions; a single-server config becomes the first server and is
      written back; limits site / server / user; pins capped at 5, listed first, kept by the prune;
      messages converted to the Claude shape (Claude's own turn unchanged, tool results in one user
      message); Claude request choices (no temperature, adaptive thinking, `tool_choice: none`,
      effort, JSON schema, fallback only on the Claude API); a full tool round through the real
      `anthropic` SDK against a mock transport (request headers and body, thinking blocks sent back
      with their signature); private keys never reach an OpenAI-compatible server; several servers
      saved (Claude needs allow_external, keys kept when masked, follow a rename, dropped on a new
      URL, duplicate names refused, legacy fields written back); unknown LLM refused in the chat; pin
      409 at 6; the preview's sandbox CSP, `X-Frame-Options: SAMEORIGIN` on the preview only, Chart.js
      inlined, Mermaid strict and its text cannot close the script, download, another user's message
      404; the bundled Mermaid matches its manifest.

**By hand (each release that touches it)**

- [ ] Against a throwaway Graylog with the owner's model: a breakdown question uses `aggregate`
      (numbers match Graylog), "what kinds of messages" uses `summarize_messages`, "make an HTML
      dashboard" gives a page whose Preview renders its charts; in the preview, `document.cookie`,
      `fetch('/api/...')` and `parent.document` are all refused (headless Chromium). The progress
      line shows the model and its context.
- [ ] Settings → LLM servers: add a Claude API server (allow_external required), test, set the
      default, rename (the key follows); the chat's server picker switches per question.
- [ ] Conversation list: fold it, fold a group, pin up to 5 (the 6th is refused); the thinking switch
      under the box folds or shows the thinking. Preview pane beside / wide / new tab / download.
      en / zh-TW / ja, both themes, ~1436 px, and with the preview open the box's buttons do not
      overlap.
- [ ] While a lookup runs, its own timer counts beside the answer's; each finished lookup stays
      listed with its time and result; the query list under the answer shows each lookup's time.

**Added 2026-11-27 (still 1.36.0)**

- [ ] `tests/test_ai_136.py` +7: a stopped, unanswered question is marked for the model (and not once it
      is answered); `stopped_at` stored for questions only; the dashboard follows the page theme (light /
      dark colours in the prompt, unknown = light, the page sends `getTheme()`); the reply may use a quarter
      of the reported context (262,144 -> 65,536; unknown -> 8,192); `preview_blocks(partial=True)` counts
      a block still being written; the live preview serves only the owner's running answer (sandbox CSP,
      `no-store`, 404 for another user or once done); folding, live preview, splitter and the stopped label
      on the page. `tests/test_ai.py::test_stop_ends_an_answer_left_running` also checks `stopped_at`.
- [ ] By hand: Stop a question while the model thinks -> the question shows "Stopped" (also after reopening
      the conversation); a code block over 15 lines starts folded with "Expand (N lines)"; asking for a
      dashboard opens the preview by itself while the page is written and keeps it current, the stored
      page replaces it when the answer is done, closing the pane keeps it closed for that answer; in the
      light theme the new dashboard is light; drag the pane's left edge (width kept, double-click resets);
      the finished-lookups list lines up in columns; the LLM server card fields line up at ~1436 and ~1180 px.
- [ ] `tests/test_ai_136.py` (also): Markdown preview escaped (no script, no javascript: link), table / list /
      mermaid rendered, theme light / dark, `.md` download; the conversation list's `more` / `limit` (pinned not
      counted, capped at 1000). By hand: a finished dashboard opens in the pane when the stream ends normally AND
      when it is cut (headless check routes `/api/ai/chat` to a stream with and without `done`); the preview
      header is as tall as the conversation's; your bubble is dark with white text; the suggestions are tinted;
      "Show older conversations" adds 50; login page: the note is a reminder box and both controls are 34 px.

### AI analysis of security incidents (v1.22.0)

**Automated**

- [ ] `tests/test_security_ai.py` (20; an answer cut off at the token limit is asked again with more; the verdict notification is opt-in, lists only the chosen
      verdicts and carries the summary in all three languages): the model's JSON is validated (fences, `<think>`, text
      around it, unknown verdict or confidence refused, lists capped); addresses the answer names
      but the evidence does not are flagged (IPv4 and compressed IPv6, version numbers ignored);
      the window is capped to 24 h; automatic picks are new or escalated, highest first, capped;
      evidence queries are all about the incident, empty fields dropped, successful logins
      checked; response format falls back json_schema -> json_object on HTTP 400; a `</data>` in
      an example message cannot close the data block; example messages are NOT stored; an
      unusable answer is asked again, then recorded as failed without hiding the last verdict;
      LLM down / budget used up = an error row and no Graylog queries once the budget is gone;
      analyses are deleted with their incident; automatic analysis needs both switches and stops
      at the first failure (audited); defaults are off; the API refuses when off, 404 for an
      unknown incident, 202 then 409 while running, lists the verdict, audits; settings validate
      the severity and cap the count; the page escapes what the model wrote (node); every page
      key is in all three languages.
- [ ] `scripts/e2e-ai-test.py` step 5 (above).

**By hand (each release that touches it)**

- [ ] Security Incidents page against a test Graylog with the AI on: AI button on a row, Analyse,
      the running line, the verdict chip in the row afterwards, the evidence section, an earlier
      analysis under "Earlier analyses", "Ask in AI chat" opens the chat with the question filled
      in; settings: automatic analysis switch, severity, count. en / zh-TW / ja, both themes,
      ~1436 px.

### Test Results

- [ ] `./scripts/run-tests.sh` passes — `TEST-RESULTS.md` generated
- [ ] `TEST-RESULTS.md` committed with this release

---

### AI chat: Graylog dashboard, summary PDF, timeline (v1.37.0)

**Automated**

- [ ] `tests/test_ai_137.py` (51): recorded calls keep `group_by` / `metrics` as lists, older str() records
      still make charts and a cut one makes none; the chart kind follows the groupings (time first =
      over time, one field and one metric = top values, else a table); only successful aggregate /
      top_values / count calls with a range become charts, the same question twice is one; the re-run
      uses the recorded query and absolute range through the chat tool's own code, and a Graylog
      refusal is said, not raised; report widgets (lines per value capped with a note, bars, tables
      capped with a note, numbers, ISO times shown local); Graylog JSON (metrics -> series incl.
      percentile, widgets mapped to search types, titles, positions, "*" as the empty query, the
      dashboard's range choices, nothing picked refused); summary JSON validated and unknown chart ids
      dropped; numbers and addresses missing from the conversation, the re-run data and the query
      parameters are listed; findings carry their charts in one section, recommendations and limits
      together, the query appendix puts each query on its own line; the model's text escaped on the
      page; text sections in the report template escaped; the timeline parses its time formats,
      escapes labels, draws bars and points without style attributes; dialog titles follow the language.
- [ ] **`scripts/e2e-ai-dashboard-test.py`** against a throwaway Graylog (`scripts/datanode-stack/up.sh`):
      seeds GELF, re-runs every chart (count 100 / 300), creates the dashboard through the product code,
      reads it back (five widgets each mapped to its search type, chart types and titles kept), executes
      its search (no errors, every widget has rows, the number widget equals the re-run), removes only its
      own dashboard, and a broken view is refused with Graylog's reason. Must print `RESULT: ALL PASS` on
      7.2.2 and 6.3.15.

**By hand (each release that touches it)**

- [ ] On an answer with queries: the dashboard button opens the dialog (title, range, charts with
      title and type); Create gives "Open in Graylog", and the dashboard opens there with every widget
      drawn; a custom range with the end before the start is refused; signed out of Graylog -> the
      sign-in box. An answer with no chartable query shows no button.
- [ ] Summary report: the header button lists the conversation's charts; Make the PDF shows progress,
      then Download; the PDF has the cover, contents, summary (with "check before use" when a value is
      not in the data), findings with their charts, recommendations and limits, the query appendix;
      it is in Reports → history. With an LLM that fails, the PDF still comes with charts and the
      dialog says the text is missing. Cancel from Job History stops it.
- [ ] A table with start / end times shows "Timeline"; it draws below the table at the chat's width
      with round time steps. en / zh-TW / ja, both themes, ~1436 px and 390 px (no sideways scroll).

- [ ] Summary PDF review items (owner 2026-11-27): Mermaid / HTML dashboard / SVG / timeline pictures in the PDF (`tests/test_ai_137.py::test_pictures_are_drawn_offline` runs a real headless Chromium and proves the page's fetch and image never reach a local listener); model chart titles; highlighted key facts (`marked` is the only markup); ISO/UTC -> short local times (`localize_times`); formal section names; "Look" from a report (logo, watermark); cover model row (AI settings); progress phases and the streamed request; empty time buckets filled. By hand: a real conversation with a sequence diagram and an HTML dashboard -> PDF in both a light report look and none.
- [ ] AI settings cards fold and each Save works; the open conversation is tinted; the report editor's close button stays in its title bar when the form scrolls.

- [ ] Save as an investigation case: the case opens from the link, its timeline holds the conversation in plain text (no `###` / `**`), a big HTML block is replaced by a line; audit row. Summary look card in AI settings: logo upload / clear, colour, watermark; the PDF cover shows them and the model + server lines; history lists the title. Every dialog (archives, schedules, audit, reports, security x4, AI, packs x5, alerting x3, settings) has its × in the title bar, still there after scrolling, and it closes the dialog (`scratchpad` check: `modalx.py`). Chip text centred on the icons (pixel check in headless Chromium with Noto Sans CJK).

- [ ] `tests/test_security_export.py`: text / detection / time filters (a % is literal, a Sigma title is searched), the detection list, every export format (CSV prefixes formula-looking cells; XLSX and ODS are well-formed, hold no formula, ODS starts with its uncompressed mimetype; JSON and Markdown follow the filters), an unknown format refused, the old `.csv` link kept, the format audited. By hand: open the .xlsx in Excel and the .ods in LibreOffice; incidents list at ~1436 px in both themes (edges, pills, the action block within its column).
- [ ] Library: 13 published packs (`tests/test_packs.py::PUBLISHED`, `test_contentpack_guard.py::PUBLISHED_PACKS`); each installs from the Content Packs page and its download carries the guide.

### 1.38.0

- [ ] `tests/test_notify_webhook.py`: JSON body, HMAC signature a receiver can recompute, no signature without a secret, TLS verify off, the receiver's error text, missing URL sends nothing, the one channel list, masked URL / secret kept on save, SSRF refused, form fields present. By hand: point it at a request catcher and check the signature.
- [ ] `tests/test_ui_138.py`: app-audit tiles (24 h counts and trends), loading row in tables, date picker wired and value format kept, report pictures turned light, plain finding cards, plain current-page row, Sigma select-all reports what it left out. `tests/test_halfwidth_slash.py`: no full-width slash.
- [ ] By hand at ~1436 px, light and dark: sidebar, dashboard, archives (date picker open and set), security incidents (tags), op-audit both tabs (tiles), reports (loading row, Verify button); an AI summary PDF from a conversation with an HTML dashboard (blocks, none cut), and a timeline of events, of counts and of from-to rows.
- [ ] Pages: `python3 scripts/pages/build.py` prints no LINT; the label/line overlap check is clean in all three languages.

## Upgrade Compatibility Test (mandatory)

    REPO=/path/to/git-clone bash scripts/upgrade-compat-test.sh [version ...]

Builds REAL state with an OLD release's OWN code (taken from git history) — 12
archives with files on disk, three schedules, and a config.yaml in the old format
— then hands that state to the CURRENT code and asserts the three
non-negotiable upgrade principles:

1. **Never lose data** — archive rows, message counts and files intact after
   `_migrate()`; nothing deleted anywhere in the upgrade path.
2. **Never leave the system unusable** — the old `config.yaml` loads, legacy
   `api_audit:` migrates to `op_audit`, fields added since then take defaults.
3. **Never stop scheduled archiving** — every pre-existing schedule survives AND
   is registered with APScheduler; a cleanup schedule storing a SHORTER retention
   than the one in force is reconciled upward, and the cleanup run is proven to
   use the safe value (otherwise the first 04:00 after the upgrade would delete
   200–1095-day-old archives).

Verified from **1.7.9, 1.7.15, 1.9.2, 1.10.13, 1.11.0, 1.12.0, 1.12.10, 1.13.0,
1.13.20, 1.13.40** — all ALL PASS. Run it whenever you touch a schema migration,
a config default, the scheduler, or any code that reinterprets stored state.

## Design-Review Pitfall Checklist

Every item below has actually shipped as a bug in this project — the incident is
cited so the check is concrete rather than abstract. Walk this list for any
change to export, import, de-duplication, storage or progress reporting. It is
much cheaper than the incident.

### 1. Scale — does the cost grow with the DATA, or with the WORK?

- [ ] Does the work scale with the amount of NEW work, or with total data volume?
  *De-duplication ran only after each document had been fetched and parsed, so a
  re-export dragged an entire 344M-document index across the network just to
  discover it was already archived. Progress sat at "0%" for 14 h at several
  unrelated sites (v1.13.53).*
- [ ] Any `fetchall()` or list comprehension over a whole table?
  *70K archive rows were materialized to render one page (v1.13.47).*
- [ ] Any whole-file `json.load()` / read-into-memory?
  *Bulk import loaded an entire 1.2 GB archive as Python objects (v1.13.47).*
- [ ] Is a per-item query or HTTP call issued inside a loop over millions of items?
- [ ] Does a "check" get more expensive as history accumulates? Merge/aggregate it
  so it scales with the number of RANGES, not the number of records.

### 2. First run, empty state, and UPGRADE

- [ ] **Does the fix itself delete data on upgrade?** A behaviour correction is
  applied to state that was written under the OLD behaviour, and the first
  scheduled run after the upgrade acts on it unattended.
  *v1.13.56 made cleanup schedules honour their own `retention_days` — correct in
  isolation, but a site whose Schedules page showed "200 Days" while config.yaml
  said 1095 was really keeping 3 years, so the next 04:00 run would have deleted
  every archive between 200 and 1095 days old. v1.13.57 reconciles the stored
  value on startup instead: never shorten what the previous version was keeping,
  log both numbers, and let the operator opt in.*
- [ ] Which direction is destructive? Apply the change only in the SAFE direction
  automatically; require an explicit action for the destructive one.
- [ ] Would changing a DEFAULT alter behaviour for anyone who never set it?
  *`retention_days` was left at 1095 for exactly this reason — lowering it would
  silently shorten retention everywhere it was not set explicitly, and the next
  cleanup would delete data those sites still expect (v1.13.57).*

- [ ] Fresh install, nothing configured, zero archives: no crash, no false warning.
  *The sizing advisor reported "ok" when `/proc/meminfo` was unreadable — a claim
  it could not support (v1.13.50).*
- [ ] The FIRST use of a new target/resource, not just the steady state.
  *The first bulk import to a new index pattern ALWAYS failed: creating a Graylog
  index set only writes MongoDB metadata; the index and deflector alias are not
  provisioned until the deflector is cycled (v1.13.53).*
- [ ] Does a newly created remote resource need time to become usable? Poll for
  readiness — do not assume, and do not just sleep a fixed amount.
  *Writing <1 s after the cycle put documents into an index Graylog then replaced;
  they were reported as indexed and were silently gone (v1.13.54).*

### 3. Mode and topology switching

- [ ] Run the same job in the OTHER mode: is state written by mode A understood by
  mode B?
  *API-mode archives store `stream_id = NULL`; the dedup rule
  `stream_id NOT LIKE '<prefix>%'` never matched them, so switching between API
  and OpenSearch archiving stored the same logs twice (v1.13.55).*
- [ ] Do the two modes agree on BOUNDARIES?
  *API chunks start at the requested time (10:43:58-11:43:58) while OpenSearch
  chunks are hour-aligned (11:00-12:00), so "one archive fully contains this
  chunk" could never hold across modes (v1.13.55).*
- [ ] Co-located versus separate hosts.
  *Sizing budgeted ~8 GB for an OpenSearch that was running on another host
  (v1.13.47).*
- [ ] A fast path that "bypasses" a component still loads the same machine.
  *Bulk import was deliberately built with "no back-pressure" because it bypasses
  Graylog — but it drives the same OpenSearch and the same RAM, 5-10x faster
  (v1.13.48).*
- [ ] Is a partial view being treated as complete? A stream-filtered archive or a
  sister index holds only part of the hour; counting it as coverage skips an
  export and loses the rest (v1.13.55).

### 4. NULL, boundaries and formats

- [ ] SQL three-valued logic: `NULL NOT LIKE 'x%'` is NULL, **not true**. Match
  `IS NULL` explicitly or wrap in `COALESCE` (v1.13.55).
- [ ] Is `0` a legitimate value being treated as "unknown"?
  *`if remaining:` discarded a count of 0, so a fully-archived index still ran a
  guaranteed-empty scan (v1.13.53).*
- [ ] The date/time FORMAT the remote system expects.
  *Graylog maps `timestamp` as `uuuu-MM-dd HH:mm:ss.SSS` and rejects an ISO-8601
  value with `parse_exception`; a range filter must carry an explicit `format`,
  or it errors — or worse, filters nothing (v1.13.53).*
- [ ] Timezone: archive times are naive local, and re-imported messages land ~8 h
  earlier on Asia/Taipei. Any time assertion must account for it.
- [ ] Off-by-one on grid alignment (`k = max(0, floor((first - t_from)/step))`).

### 5. Interruption and inconsistency

- [ ] Cancel must be polled INSIDE long operations, not only between units.
  *A 500-message batch takes tens of seconds on a loaded box, so Cancel looked
  dead (v1.13.45).*
- [ ] Long sleeps must be interruptible (a flat `sleep(5)`/30 s pause loop ignored
  cancel and user resume).
- [ ] The database says one thing, the disk another: an archive row whose FILE was
  deleted must not be skipped forever.
  *`verify` marks it `missing` and dedup counts only `completed` rows, so the next
  export re-archives exactly that range — asserted by e2e step [6].*
- [ ] A corrupt or truncated single item must fail THAT item, not abort the run.
- [ ] Locks, claims and in-memory registries released in `finally`.

### 6. Resource ceilings

- [ ] Is the REQUEST SIZE bounded, or only the item count?
  *`batch_docs=10000` produced a ~93 MB `_bulk` request for 9 KB Windows Event Log
  documents; OpenSearch's default `http.max_content_length` is 100 MB, and the
  whole request is held in the coordinating node's heap (v1.13.49).*
- [ ] The same question on the READ side.
  *A 10,000-document search page is ~90 MB for wide documents — a fetch-phase heap
  spike plus an equally large parse on our side (v1.13.49).*
- [ ] PEAK memory, not just steady state — the peak is what the OOM killer sees.
- [ ] Disk: does the CONFIGURED retention actually fit?
  *`retention_days` defaults to 1095 (3 years); at a measured ~557 GB/month that
  needs ~19.6 TB, so on a 2.8 TB disk cleanup silently deletes at ~5 months
  (v1.13.52).*

### 7. Silent failure

- [ ] No `except: pass` around anything load-bearing — log it.
  *A missing `import json` disabled the page-size guard entirely while every test
  still passed (v1.13.50).*
- [ ] Does a failure actually SURFACE to the operator?
  *The scheduled export's failure path called `create_job` inside a try/except
  that always failed, so a broken export left nothing in Task Log — only
  `last_run` moved.*
- [ ] Does "success" mean the data is really there? Verify at the DESTINATION.
  *Bulk reported 4,900 documents indexed that Graylog then replaced (v1.13.54).*
- [ ] Does a cleanup/maintenance command actually delete what it created?
  *`streams-cleanup` matched stream TITLES, but bulk names its stream
  "jt-glogarch Restored (&lt;prefix&gt;)" — it found 0 streams and silently failed at
  its only job (v1.13.51).*

### 8. Progress and perception

- [ ] Does the progress DENOMINATOR match what will actually be processed, and
  does the numerator advance for SKIPPED work too? *("0%" for 14 h — v1.13.53.)*
- [ ] Never gate the UI on a single transport.
  *The progress bar updated only from the SSE stream, so when the stream stalled
  the bar froze although the job was advancing and the poll had fresh data
  (v1.13.44).*
- [ ] Does a paused or throttled state SAY so? A frozen bar reads as "stuck"
  (v1.13.42).
- [ ] Colour must convey severity: informational text must not look like a warning
  (orange info lines alarmed a customer — v1.13.41).

### 9. Test blind spots

- [ ] Is there an e2e step for EVERY import/export path?
  *Bulk was never covered, so a whole-file `json.load()` OOM risk survived many
  releases (v1.13.48).*
- [ ] Does the test set up state that the PRODUCT should create itself?
  *The e2e pre-created the bulk index and alias, which both masked the
  first-import bug and raced with Graylog's own provisioning (v1.13.54).*
- [ ] Would the test still pass if the feature were silently disabled? If yes, it
  is not testing the feature.
- [ ] Does the test clean up after itself? Leftover state changes the next run's
  code path — and hid a first-import bug for several releases.

## Running Tests

```bash
# Full suite + generate TEST-RESULTS.md (required before every GitHub push)
./scripts/run-tests.sh

# Or run manually:
python3 -m pytest tests/ -v

# Unit tests only (fast, no external deps)
python3 -m pytest tests/ -v --ignore=tests/test_integration.py

# Integration tests only (requires live OpenSearch)
python3 -m pytest tests/test_integration.py -v

# Version + structure checks
./scripts/check-version.sh
```

## Test Results File

`TEST-RESULTS.md` is auto-generated by `./scripts/run-tests.sh` and must be
committed with every GitHub push. It records: pass/fail status, version,
timestamp, platform, full pytest output, and version check result.

See the latest results: [TEST-RESULTS.md](TEST-RESULTS.md)

## SBOM (every release)

`./scripts/run-tests.sh` writes `github/sbom.cdx.json` (CycloneDX 1.5) from the
INSTALLED packages, run from `/tmp` so the checkout's stale `*.egg-info` cannot
answer, and stops the release when the installed jt-glogarch is not the version
being released (reinstall with `--force-reinstall` first). Commit it with every
push, like `TEST-RESULTS.md`.

- [ ] `github/sbom.cdx.json` shows this release's version and lists every runtime
      dependency of `pyproject.toml` (`tests/test_sbom.py` checks both).
- [ ] An offline bundle contains `sbom.cdx.json`; `build-offline-bundle.sh` aborts
      without one. It lists every wheel in the bundle with SHA-256, the Chromium
      build and the font.
- [ ] `sudo -u jt-glogarch glogarch sbom -o /tmp/s.json` on the staging host gives
      valid JSON with the deployed version (`glogarch sbom > file` too: warnings go
      to stderr).

## Security scan (larger releases)

Every **larger version change** (minor/major, e.g. `1.11.0`, `2.0.0` — not routine
patch releases unless they change the web surface) must pass an **OWASP ZAP** scan
before it is considered done. **Fix every finding until there are zero High /
Medium / Low risk alerts** (or suppress a false positive with a documented reason).

```bash
# Baseline (passive: spider + passive rules — no attack payloads, no data changes)
docker run --rm -t zaproxy/zaproxy zap-baseline.py -t https://<host>:8990

# Full active scan sends SQLi/XSS payloads and can create/modify data via the API —
# run ONLY against a clean/scratch instance, with explicit approval.
```

The app already sets a strong header/cookie baseline via `SecurityHeadersMiddleware`
(`glogarch/web/app.py`): strict CSP, HSTS, `X-Frame-Options: DENY`, `nosniff`,
Referrer/Permissions-Policy, COOP/COEP, and `HttpOnly; SameSite=Strict; Secure`
cookies — so most common ZAP header/cookie findings are pre-empted.

Save each scan report under `zap/<YYYY-MM-DD>/` (JSON + summary). **Do NOT commit these to GitHub** (they contain scan-target hosts) — `zap/` is git-ignored.
