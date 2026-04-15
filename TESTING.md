# jt-glogarch Testing Checklist

**Language**: **English** | [繁體中文](TESTING-zh_TW.md)

This checklist must pass before every release. Run `pytest` from the project root.

```bash
./scripts/run-tests.sh
```

---

## Automated Tests (156 tests)

### Unit Tests

| # | Test File | Tests | Covers |
|---|---|---|---|
| 1 | `test_audit.py` | 27 | Audit parser (username decode, classify, sensitive, noise filter, syslog/JSON parse, process_raw_entry), config defaults/custom/YAML/missing/no-section, DB insert/list/stats, token resolve, cleanup with audit-specific retention, cleanup fallback, notify event |
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
- [ ] `deploy/upgrade.sh` runs successfully (db-backup → git pull → install → restart → verify)

### Test Results

- [ ] `./scripts/run-tests.sh` passes — `TEST-RESULTS.md` generated
- [ ] `TEST-RESULTS.md` committed with this release

---

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
