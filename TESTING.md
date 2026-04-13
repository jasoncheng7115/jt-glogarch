# jt-glogarch Testing Checklist

**Language**: **English** | [繁體中文](TESTING-zh_TW.md)

This checklist must pass before every release. Run `pytest` from the project root.

```bash
./scripts/run-tests.sh
```

---

## Automated Tests (103 tests)

### Unit Tests

| # | Test File | Tests | Covers |
|---|---|---|---|
| 1 | `test_sanitize.py` | 10 | Password/token/URL/JSON/Basic Auth/Bearer redaction, truncation, no false positives |
| 2 | `test_local_admin.py` | 9 | SHA256 hash, `localadmin` username required, Graylog-rejects-no-fallback, Graylog-down-with/without-hash, backward compat |
| 3 | `test_bulk_import.py` | 7 | Reserved field stripping, deflector alias, stream rewrite, marker field, dedup id/none |
| 4 | `test_notify_format.py` | 7 | Status emoji (✅/⚠️/❌), per-line format, URL shortening, en/zh-TW key parity |
| 5 | `test_repo_structure.py` | 7 | pyproject.toml at root, no src/ dir, deploy files, README/CHANGELOG/CONFIG exist, version sync |
| 6 | `test_upgrade_script.py` | 7 | upgrade.sh exists + 5 steps, root check, version display, README refs, systemd default=Yes, git clone sudo |
| 7 | `test_field_schema.py` | 6 | Plain JSON passthrough, zlib round-trip, None/corrupted handling, DB store+read |
| 8 | `test_database_datetime.py` | 5 | Naive/UTC/+08:00 round-trip, None passthrough, offset string parsing |
| 9 | `test_import_lock.py` | 5 | Claim/conflict/release/wrong-owner/reclaim |
| 10 | `test_db_rebuild.py` | 5 | Dry-run, actual rebuild, skip existing, backup, prune |
| 11 | `test_preflight_conflicts.py` | 4 | Intra-archive conflict, cross-conflict with actual mapping, string-only not pinned, mixed scenario |
| 12 | `test_config.py` | 4 | Default settings, search paths `/etc/jt-glogarch/`, file loading, WebConfig localadmin |
| 13 | `test_upgrade.py` | 4 | Old DB auto-migration, old config backward compat, archives survive upgrade, DB backup validity |
| 14 | `test_api_error_handling.py` | 4 | Graylog API 401/502/unreachable error handling for /api/index-sets and /api/streams |
| 15 | `test_cli_commands.py` | 3 | All 16 commands registered, hash-password help, root warning logic |
| 16 | `test_cleanup_race.py` | 3 | Grace constant = 600s, recent file skipped, old file not skipped |
| 17 | `test_storage_ownership.py` | 3 | Root chown fix, non-root error, scoped to base_path only |
| 18 | `test_health_endpoint.py` | 2 | Response structure (status/version/checks/issues), public path (no auth) |
| 19 | `test_opensearch_client.py` | 1 | `_doc` sort tiebreaker (not `_id` — circuit breaker fix) |

### Integration Tests

| # | Test File | Tests | Covers |
|---|---|---|---|
| 20 | `test_integration.py` | 6 | Real OpenSearch cross-conflict detection, zlib schema in full preflight pipeline, timezone dedup/retention/coverage-ratio correctness, archive write-SHA256-read integrity |

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
