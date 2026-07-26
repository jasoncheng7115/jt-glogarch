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

## Automated Tests (202 tests)

### Unit Tests

| # | Test File | Tests | Covers |
|---|---|---|---|
| 1 | `test_audit.py` | 28 | Audit parser (username decode, classify, sensitive, noise filter, syslog/JSON parse, process_raw_entry), config defaults/custom/YAML/missing/no-section, DB insert/list/stats, token resolve, cleanup with audit-specific retention, cleanup fallback, notify event |
| 2 | `test_sanitize.py` | 10 | Password/token/URL/JSON/Basic Auth/Bearer redaction, truncation, no false positives |
| 3 | `test_local_admin.py` | 9 | SHA256 hash, `localadmin` username required, Graylog-rejects-no-fallback, Graylog-down-with/without-hash, backward compat |
| 4 | `test_upgrade_script.py` | 9 | upgrade.sh exists + 5 steps, root check, version display, README refs, systemd default=Yes, git clone sudo, retention_days migration, op_audit retention_days default |
| 5 | `test_repo_structure.py` | 8 | pyproject.toml at root, no src/ dir, deploy files, README/CHANGELOG/CONFIG exist, version sync, github/glogarch matches source |
| 6 | `test_bulk_import.py` | 7 | Reserved field stripping, deflector alias, stream rewrite, marker field, dedup id/none |
| 7 | `test_notify_format.py` | 7 | Status emoji (✅/⚠️/❌), per-line format, URL shortening, en/zh-TW key parity |
| 8 | `test_notify_test_endpoint.py` | 7 | Discord/Slack/Teams/Telegram/Nextcloud Talk/Email send function params, test endpoint signature match |
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
- [ ] Script prints `RESULT: ALL PASS`

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
- [ ] Heartbeat alert when no syslog received for 10+ minutes while Graylog is up
- [ ] Filter dropdowns show correct language labels (Method/Status vs 方法/狀態碼)

### Customer Install / Upgrade Simulation

- [ ] Copy `github/` to temp dir → `pip install` succeeds
- [ ] `deploy/install.sh` references correct paths, systemd default = Yes
- [ ] `deploy/install.sh` writes a minimal `config.yaml` with `servers: []` (triggers setup wizard)
- [ ] `deploy/upgrade.sh` runs successfully (db-backup → git pull → install → restart → verify)
- [ ] `deploy/upgrade.sh` never overwrites an existing `servers:` / `opensearch:` block

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

### Security — OWASP ZAP DAST (must be 0 High / 0 Medium)

- [ ] `scripts/zap-scan.sh` run against a live instance — **0 High, 0 Medium** alerts
- [ ] Response carries `Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`
- [ ] Session cookie is `Secure` + `HttpOnly` + `SameSite=Strict`
- [ ] Non-static responses carry `Cache-Control: no-store`
- [ ] `Server` response header is absent (uvicorn banner stripped)
- [ ] Any accepted ZAP rule in `.zap/rules.tsv` has a written justification

### Test Results

- [ ] `./scripts/run-tests.sh` passes — `TEST-RESULTS.md` generated
- [ ] `TEST-RESULTS.md` committed with this release

---

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
