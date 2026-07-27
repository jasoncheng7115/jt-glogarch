# Defect Register

Every defect found and fixed, with the **root cause** and — more importantly —
**what now prevents it recurring**. A fix that is not held in place by a test or
a check is not finished.

Read with `TESTING.md` → *Design-Review Pitfall Checklist*, which generalises
these into questions to ask **before** writing code.

**Language**: **English** | [繁體中文](DEFECTS-zh_TW.md)

---

## How to use this

- Adding a feature to export/import/dedup/storage/progress? Skim the class of
  defect you are touching — most of these shipped because a rule existed in two
  places, or a failure had no way to become visible.
- Fixing a bug? Add a row here **and** the guard that keeps it fixed.

---

## Data integrity

| # | Defect | Root cause | What prevents recurrence |
|---|---|---|---|
| 1 | One index set's archives suppressed another's — those logs were **never archived** (v1.13.62) | Chunk dedup asked "does ANY archive *not* from this prefix cover it?", so on a 27-index-set site a `graylog_147` archive covered `filesrv_33` | Chunk loop and query filter now use the **same merged ranges** (`covered_ranges`), so they cannot diverge. `test_chunk_dedup_and_query_filter_use_the_same_ranges` |
| 2 | Switching API ⇄ OpenSearch archived the same logs **twice** (v1.13.55) | `NULL NOT LIKE 'x%'` is NULL in SQL, so API archives (`stream_id IS NULL`) were invisible; and coverage required ONE archive to contain the chunk, which misaligned boundaries never satisfy | Coverage counts only archives holding the FULL range (`stream_id IS NULL` or this index), merged. `test_api_all_streams_archive_covers`, `test_stream_filtered_archive_does_not_cover` |
| 3 | An index ~95% archived kept a hole **forever** (v1.13.56) | `coverage >= 0.95 → skip whole index`, and the ratio was computed server-wide so sister indices inflated each other | Heuristic removed; skip only when the filtered count is exactly 0. e2e step [5] punches a gap and demands it back |
| 4 | First bulk import to a new pattern **lost documents** intermittently (v1.13.60) | Write began while Graylog was still provisioning the write index; OpenSearch accepted them, then the index was replaced | `_wait_for_stable_alias()` (same concrete index 3 polls running) **plus** post-run destination count — 0 at the destination now FAILS the run |
| 5 | Upgrade would have deleted 200–1095-day-old archives (v1.13.57) | 1.13.56 started honouring a stored `retention_days` that had never been applied | Startup reconciliation never shortens what the previous version kept. `test_upgrade_does_not_shorten_retention_and_delete_data` + `scripts/upgrade-compat-test.sh` |
| 6 | Bulk `_bulk` request reached ~93 MB for 9 KB documents (v1.13.49) | `batch_docs` bounded the doc COUNT, never the bytes; OpenSearch's default limit is 100 MB | 10 MB cap with carry-over; `test_byte_cap_loses_no_documents` proves the split drops nothing |

## Silent failure

| # | Defect | Root cause | What prevents recurrence |
|---|---|---|---|
| 7 | `streams-cleanup` could not delete what it created (v1.13.51) | Matched streams by TITLE prefix, but bulk names its stream `jt-glogarch Restored (<prefix>)` | Match by the index set the stream writes to. e2e step [4] now runs the command every release |
| 8 | Page-size guard silently disabled (v1.13.50) | A missing `import json` inside a bare `except: pass` — every test still passed | The guard logs a warning instead of swallowing; `test_adaptation_does_not_raise` asserts the warning never fires |
| 9 | A cleanup schedule's retention was decorative (v1.13.56) | The UI stored and displayed `retention_days`; the scheduler always used `config.yaml` | The run reads the schedule's own value and logs which source it used. `test_schedule_retention_days_is_used` |
| 10 | One server's export starved another's (v1.13.63) | Overlap guard keyed by job TYPE, so a second export schedule was skipped whenever the first was running — for hours, with only an info log | Guard is per-schedule; the per-server lock still protects the real resource. `test_a_second_schedule_is_not_blocked_by_the_first` |
| 11 | A scheduled export failed with nothing in Job History | The failure path's `create_job` was itself inside a try/except that always failed | Failures are recorded; `/api/health` also reports `schedules_registered` |

## Scale — cost growing with data, not with work

| # | Defect | Root cause | What prevents recurrence |
|---|---|---|---|
| 12 | Export stuck at "0%" for 14 h (v1.13.53) | Dedup ran only AFTER each document was fetched, so a re-export dragged a 344M-doc index across the network to discard it | Covered time is excluded in the OpenSearch query; an index with nothing left is skipped outright |
| 13 | Bulk import loaded a whole 1.2 GB archive into memory (v1.13.47) | `json.load()` on the full `.json.gz`; only the GELF path had been converted to streaming | Bulk uses the same `ArchiveIterator`; `test_import_path_never_calls_whole_file_loader` |
| 14 | 70K archive rows materialised to render one page (v1.13.47) | `SELECT *` + slice in Python | SQL `limit`/`offset` + `count_archives()` |
| 15 | `field_schema` blob read on every archive listing (v1.13.47) | `SELECT *` pulled a ~2.5 KB column nothing consumes | Excluded by default; `include_schema=True` to opt in |
| 16 | Search pages ~90 MB for wide documents (v1.13.49) | Page size bounded documents, not bytes | Page size adapts to the measured average document size (floor 500) |

## Visibility — a working system that looks broken

| # | Defect | Root cause | What prevents recurrence |
|---|---|---|---|
| 17 | Progress bar froze while the job advanced (v1.13.44) | The 2 s poll was gated behind `sseOk`, which latches true on every heartbeat | The poll always refreshes from the job record via a shared monotonic renderer |
| 18 | A paused job was indistinguishable from a hung one (v1.13.42, v1.13.61) | Progress counts only WRITTEN messages, so a throttled job just stops moving | Amber "Paused — source/target under load" in the dialog, sidebar and Job History |
| 19 | False `SSE timeout` during a backpressure pause (v1.13.41) | The stream declared a synthetic error after 10 min of no events | Heartbeats during a pause; the stream ends only with the job's real status |
| 20 | System Logs unusable for diagnosis (v1.13.61) | UI polling filled the window — 57% of the last 100 lines were HTTP access noise | `app_only=true` by default filters access lines |
| 21 | Backpressure messages appeared in Chinese on an English UI (v1.13.61) | Hardcoded strings in `health_guard.py` | Guard messages are English; UI strings go through i18n |

## Security

| # | Defect | Root cause | What prevents recurrence |
|---|---|---|---|
| 22 | Notification webhook URLs had no SSRF check (v1.13.63) | Every other URL-taking endpoint used `ssrf_block_reason()`; this one was missed | The guard is applied to `webhook_url` / `server_url` on save |

## Testing gaps that let the above survive

| # | Gap | Consequence | Fixed by |
|---|---|---|---|
| 23 | e2e never covered **bulk import** | A whole-file `json.load()` OOM risk survived many releases | e2e step [4] |
| 24 | The e2e **pre-created** the bulk index | Masked the "first import to a new pattern always fails" bug AND raced with Graylog's provisioning | The test no longer sets up what the product must create |
| 25 | No upgrade test | Upgrade safety was assumed | `scripts/upgrade-compat-test.sh` — verified from 1.7.9 through 1.13.40 |
| 26 | Tests passed with the feature disabled | See #8 | Assert the failure path is *not* taken, not just that nothing raised |

---

## The three rules these keep landing on

1. **One decision, one rule.** Two code paths deciding the same thing will drift (#1, #2, #9).
2. **A failure must be able to become visible.** No `except: pass`; "success" means verified at the destination (#4, #7, #8, #11).
3. **Cost must scale with the work, not with the data** (#12–#16).
