# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""SQLite database for archive tracking."""

from __future__ import annotations
from glogarch.utils.logging import get_logger

log = get_logger(__name__)

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import threading

from glogarch.core.models import (
    ArchiveRecord,
    ArchiveStatus,
    ImportHistoryRecord,
    JobRecord,
    JobStatus,
    ScheduleRecord,
)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS archives (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    server_name     TEXT NOT NULL,
    stream_id       TEXT,
    stream_name     TEXT,
    time_from       TEXT NOT NULL,
    time_to         TEXT NOT NULL,
    file_path       TEXT NOT NULL UNIQUE,
    file_size_bytes INTEGER NOT NULL DEFAULT 0,
    original_size_bytes INTEGER NOT NULL DEFAULT 0,
    message_count   INTEGER NOT NULL DEFAULT 0,
    part_number     INTEGER NOT NULL DEFAULT 1,
    total_parts     INTEGER NOT NULL DEFAULT 1,
    checksum_sha256 TEXT NOT NULL DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'completed',
    created_at      TEXT NOT NULL,
    deleted_at      TEXT,
    UNIQUE(server_name, stream_id, time_from, time_to, part_number)
);

CREATE INDEX IF NOT EXISTS idx_archives_time
    ON archives (server_name, time_from, time_to);
CREATE INDEX IF NOT EXISTS idx_archives_status
    ON archives (status);

-- Export dedup hot path: covered_ranges() seeks (server, stream_id) directly.
-- At 200K archives the OR-form scan cost 475 ms per call x54 calls per
-- scheduled run; with this index + split queries it is a direct range seek.
CREATE INDEX IF NOT EXISTS idx_archives_srv_stream_time
    ON archives (server_name, stream_id, time_from);

CREATE TABLE IF NOT EXISTS jobs (
    id              TEXT PRIMARY KEY,
    job_type        TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    progress_pct    REAL NOT NULL DEFAULT 0.0,
    messages_done   INTEGER NOT NULL DEFAULT 0,
    messages_total  INTEGER,
    config_json     TEXT,
    error_message   TEXT,
    started_at      TEXT,
    completed_at    TEXT,
    created_at      TEXT NOT NULL,
    source          TEXT NOT NULL DEFAULT ''
);

-- Job History polling: the UI reads the newest 50 jobs every ~2 s. Without
-- this index that is a full-table sort — measured 140 ms/call at 50K job rows
-- (7% of a core, forever, on the co-located VM); 2.9 ms with it.
CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs (created_at DESC);

CREATE TABLE IF NOT EXISTS schedules (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    job_type    TEXT NOT NULL,
    cron_expr   TEXT NOT NULL,
    config_json TEXT,
    enabled     INTEGER NOT NULL DEFAULT 1,
    last_run_at TEXT,
    next_run_at TEXT
);

CREATE TABLE IF NOT EXISTS import_history (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    archive_id    INTEGER NOT NULL REFERENCES archives(id),
    target_server TEXT NOT NULL,
    messages_sent INTEGER NOT NULL DEFAULT 0,
    imported_at   TEXT NOT NULL,
    job_id        TEXT REFERENCES jobs(id)
);

CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT NOT NULL,
    username    TEXT,
    action      TEXT NOT NULL,
    detail      TEXT,
    ip_address  TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp
    ON audit_log (timestamp);

CREATE TABLE IF NOT EXISTS api_audit (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    server_name     TEXT NOT NULL DEFAULT '',
    timestamp       TEXT NOT NULL,
    remote_addr     TEXT NOT NULL DEFAULT '',
    username        TEXT NOT NULL DEFAULT '',
    method          TEXT NOT NULL DEFAULT '',
    uri             TEXT NOT NULL DEFAULT '',
    query_string    TEXT NOT NULL DEFAULT '',
    status_code     INTEGER NOT NULL DEFAULT 0,
    request_body    TEXT,
    user_agent      TEXT NOT NULL DEFAULT '',
    request_time_ms REAL NOT NULL DEFAULT 0.0,
    operation       TEXT NOT NULL DEFAULT '',
    is_sensitive    INTEGER NOT NULL DEFAULT 0,
    target_name     TEXT NOT NULL DEFAULT '',
    created_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_api_audit_ts ON api_audit (timestamp);
CREATE INDEX IF NOT EXISTS idx_api_audit_user ON api_audit (username);
CREATE INDEX IF NOT EXISTS idx_api_audit_uri ON api_audit (method, uri);

CREATE TABLE IF NOT EXISTS reports (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL UNIQUE,
    config_json  TEXT NOT NULL DEFAULT '{}',
    enabled      INTEGER NOT NULL DEFAULT 1,
    last_run_at  TEXT,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS report_history (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id    INTEGER,
    report_name  TEXT NOT NULL DEFAULT '',
    file_path    TEXT NOT NULL DEFAULT '',
    filename     TEXT NOT NULL DEFAULT '',
    size_bytes   INTEGER NOT NULL DEFAULT 0,
    status       TEXT NOT NULL DEFAULT 'completed',
    error        TEXT,
    triggered_by TEXT NOT NULL DEFAULT 'manual',
    sha256       TEXT NOT NULL DEFAULT '',
    created_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_report_hist ON report_history (report_id, created_at);

-- Alerting (Graylog event definitions): one row per definition a batch touched,
-- written BEFORE the change is sent, so a batch can be undone even after a
-- crash mid-run. status: pending (sent or about to be) | applied | failed |
-- restored (undone by a later batch).
CREATE TABLE IF NOT EXISTS alerting_changes (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id             TEXT NOT NULL,
    server               TEXT NOT NULL DEFAULT '',
    definition_id        TEXT NOT NULL,
    title                TEXT NOT NULL DEFAULT '',
    action               TEXT NOT NULL DEFAULT '',
    before_notifications TEXT NOT NULL DEFAULT '[]',
    after_notifications  TEXT NOT NULL DEFAULT '[]',
    status               TEXT NOT NULL DEFAULT 'pending',
    error                TEXT,
    username             TEXT NOT NULL DEFAULT '',
    undoes_batch         TEXT,
    created_at           TEXT NOT NULL,
    updated_at           TEXT
);
CREATE INDEX IF NOT EXISTS idx_alerting_batch ON alerting_changes (batch_id);
CREATE INDEX IF NOT EXISTS idx_alerting_server ON alerting_changes (server, created_at);

-- Security incidents (added 1.20, glogarch/security/). One row per
-- (server, detector, entity) episode: a later run that sees the same entity
-- while the incident is open updates it instead of opening another; a closed
-- one, or one quiet for longer than security.reopen_hours, starts a new row.
CREATE TABLE IF NOT EXISTS sec_incidents (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    server            TEXT NOT NULL DEFAULT '',
    detector          TEXT NOT NULL,
    entity            TEXT NOT NULL,
    entity_field      TEXT NOT NULL DEFAULT '',
    severity          TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'open',
    is_new            INTEGER NOT NULL DEFAULT 0,
    external          INTEGER,
    first_seen        TEXT NOT NULL,
    last_seen         TEXT NOT NULL,
    runs              INTEGER NOT NULL DEFAULT 1,
    peak_count        INTEGER NOT NULL DEFAULT 0,
    last_count        INTEGER NOT NULL DEFAULT 0,
    metrics           TEXT NOT NULL DEFAULT '{}',
    query             TEXT NOT NULL DEFAULT '',
    notified_at       TEXT,
    notified_severity TEXT,
    status_by         TEXT,
    status_at         TEXT
);
CREATE INDEX IF NOT EXISTS idx_sec_inc_key ON sec_incidents (server, detector, entity, status);
CREATE INDEX IF NOT EXISTS idx_sec_inc_seen ON sec_incidents (last_seen);
-- When an entity was last seen by a detector: drives the NEW badge.
CREATE TABLE IF NOT EXISTS sec_seen (
    server     TEXT NOT NULL,
    detector   TEXT NOT NULL,
    entity     TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    last_seen  TEXT NOT NULL,
    PRIMARY KEY (server, detector, entity)
);
CREATE TABLE IF NOT EXISTS sec_runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    server      TEXT NOT NULL DEFAULT '',
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    window_from TEXT,
    window_to   TEXT,
    status      TEXT NOT NULL DEFAULT 'running',
    queries     INTEGER NOT NULL DEFAULT 0,
    findings    INTEGER NOT NULL DEFAULT 0,
    opened      INTEGER NOT NULL DEFAULT 0,
    coverage    TEXT NOT NULL DEFAULT '[]',
    errors      TEXT NOT NULL DEFAULT '[]',
    note        TEXT
);
CREATE INDEX IF NOT EXISTS idx_sec_runs ON sec_runs (server, id);

-- AI analysis of a security incident (added 1.22). Advisory text from the model
-- plus the evidence it was given, WITHOUT the example messages (no second copy
-- of log text). Deleted with its incident.
CREATE TABLE IF NOT EXISTS sec_ai_analyses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id INTEGER NOT NULL,
    created_at  TEXT NOT NULL,
    trigger     TEXT NOT NULL DEFAULT 'manual',
    username    TEXT NOT NULL DEFAULT '',
    lang        TEXT NOT NULL DEFAULT 'en',
    model       TEXT,
    verdict     TEXT,
    confidence  TEXT,
    result      TEXT,
    evidence    TEXT,
    unverified  TEXT NOT NULL DEFAULT '[]',
    tokens      INTEGER NOT NULL DEFAULT 0,
    elapsed_ms  INTEGER NOT NULL DEFAULT 0,
    error       TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_sec_ai_inc ON sec_ai_analyses (incident_id, id);

-- Investigations (added 1.24). A case groups incidents for one investigation.
-- Never deleted (closed instead): it is the record of what was looked at and
-- decided. Its timeline keeps notes and every change, append-only.
CREATE TABLE IF NOT EXISTS sec_cases (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'open',
    severity    TEXT NOT NULL DEFAULT 'medium',
    assignee    TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    resolution  TEXT NOT NULL DEFAULT '',
    created_by  TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    closed_at   TEXT
);
CREATE INDEX IF NOT EXISTS idx_sec_cases_status ON sec_cases (status, updated_at);
CREATE TABLE IF NOT EXISTS sec_case_incidents (
    case_id     INTEGER NOT NULL,
    incident_id INTEGER NOT NULL,
    added_by    TEXT NOT NULL DEFAULT '',
    added_at    TEXT NOT NULL,
    PRIMARY KEY (case_id, incident_id)
);
CREATE INDEX IF NOT EXISTS idx_sec_case_inc ON sec_case_incidents (incident_id);
CREATE TABLE IF NOT EXISTS sec_case_notes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id    INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    username   TEXT NOT NULL DEFAULT '',
    kind       TEXT NOT NULL DEFAULT 'note',
    body       TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_sec_case_notes ON sec_case_notes (case_id, id);

-- Assets (added 1.25): what matters at this site, for risk scores and context.
CREATE TABLE IF NOT EXISTS sec_assets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    kind        TEXT NOT NULL,
    value       TEXT NOT NULL,
    name        TEXT NOT NULL DEFAULT '',
    criticality TEXT NOT NULL DEFAULT 'medium',
    owner       TEXT NOT NULL DEFAULT '',
    notes       TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    UNIQUE (kind, value)
);

-- Sigma rules (added 1.27). The YAML as given, its conversion, run results.
CREATE TABLE IF NOT EXISTS sec_sigma_rules (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sigma_id    TEXT NOT NULL DEFAULT '',
    title       TEXT NOT NULL,
    level       TEXT NOT NULL DEFAULT 'medium',
    tags        TEXT NOT NULL DEFAULT '[]',
    yaml        TEXT NOT NULL,
    query       TEXT NOT NULL DEFAULT '',
    error       TEXT NOT NULL DEFAULT '',
    group_by    TEXT NOT NULL DEFAULT 'source',
    threshold   INTEGER NOT NULL DEFAULT 1,
    enabled     INTEGER NOT NULL DEFAULT 0,
    created_by  TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    last_run_at TEXT,
    last_count  INTEGER,
    last_error  TEXT NOT NULL DEFAULT '',
    origin      TEXT NOT NULL DEFAULT ''
);

-- Sigma rule library (added 1.33): SigmaHQ's release package, replaced as a whole
-- on each download. Nothing here runs; a rule runs once added to sec_sigma_rules.
CREATE TABLE IF NOT EXISTS sec_sigma_library (
    sigma_id    TEXT PRIMARY KEY,
    path        TEXT NOT NULL DEFAULT '',
    title       TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT '',
    level       TEXT NOT NULL DEFAULT '',
    author      TEXT NOT NULL DEFAULT '',
    modified    TEXT NOT NULL DEFAULT '',
    product     TEXT NOT NULL DEFAULT '',
    category    TEXT NOT NULL DEFAULT '',
    service     TEXT NOT NULL DEFAULT '',
    tags        TEXT NOT NULL DEFAULT '[]',
    yaml        TEXT NOT NULL,
    query       TEXT NOT NULL DEFAULT '',
    error       TEXT NOT NULL DEFAULT '',
    fields      TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS sec_sigma_library_meta (
    k TEXT PRIMARY KEY,
    v TEXT NOT NULL DEFAULT ''
);

-- Threat-intel lists (added 1.28): the entries of each downloaded feed.
CREATE TABLE IF NOT EXISTS sec_ti_entries (
    feed  TEXT NOT NULL,
    value TEXT NOT NULL,
    PRIMARY KEY (feed, value)
);
CREATE TABLE IF NOT EXISTS sec_ti_feeds (
    feed         TEXT PRIMARY KEY,
    refreshed_at TEXT,
    count        INTEGER NOT NULL DEFAULT 0,
    error        TEXT NOT NULL DEFAULT '',
    tried_at     TEXT
);

-- (account, source) pairs of successful logins (added 1.29, new login sources).
CREATE TABLE IF NOT EXISTS sec_pairs (
    server     TEXT NOT NULL,
    account    TEXT NOT NULL,
    source     TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    last_seen  TEXT NOT NULL,
    PRIMARY KEY (server, account, source)
);
CREATE INDEX IF NOT EXISTS idx_sec_pairs_acct ON sec_pairs (server, account);

-- Messages per hour per host / event category, one row per UTC hour (added 1.30,
-- volume anomaly). The last run of an hour wins. Kept ~16 days.
CREATE TABLE IF NOT EXISTS sec_volumes (
    server TEXT NOT NULL,
    field  TEXT NOT NULL,
    key    TEXT NOT NULL,
    hour   TEXT NOT NULL,
    rate   REAL NOT NULL,
    PRIMARY KEY (server, field, key, hour)
);
CREATE INDEX IF NOT EXISTS idx_sec_volumes_hour ON sec_volumes (server, field, hour);

-- Suppressions (added 1.31): a known, accepted detection on one entity. server ''
-- = every server, detector '*' = every detection, entity = a value or a network.
CREATE TABLE IF NOT EXISTS sec_suppressions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    server      TEXT NOT NULL DEFAULT '',
    detector    TEXT NOT NULL,
    entity      TEXT NOT NULL,
    reason      TEXT NOT NULL,
    created_by  TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL,
    expires_at  TEXT,
    hits        INTEGER NOT NULL DEFAULT 0,
    last_hit_at TEXT,
    UNIQUE (server, detector, entity)
);

-- AI chat (added 1.21). One user's conversations are theirs only. A message
-- keeps the question or the final answer and the NAMES of the tools used, not
-- the tool results (log data does not get a second copy here).
CREATE TABLE IF NOT EXISTS ai_conversations (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username   TEXT NOT NULL,
    server     TEXT NOT NULL DEFAULT '',
    title      TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    pinned_at  TEXT
);
CREATE INDEX IF NOT EXISTS idx_ai_conv_user ON ai_conversations (username, updated_at);
CREATE TABLE IF NOT EXISTS ai_messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    role            TEXT NOT NULL,
    content         TEXT NOT NULL DEFAULT '',
    model           TEXT,
    tools           TEXT NOT NULL DEFAULT '[]',
    tokens          INTEGER NOT NULL DEFAULT 0,
    elapsed_ms      INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL,
    truncated       INTEGER NOT NULL DEFAULT 0,
    calls           TEXT NOT NULL DEFAULT '[]',
    followups       TEXT NOT NULL DEFAULT '[]',
    llm             TEXT NOT NULL DEFAULT '',
    stopped_at      TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_ai_msg_conv ON ai_messages (conversation_id, id);
-- Tokens spent per UTC day, for the daily / monthly budget.
CREATE TABLE IF NOT EXISTS ai_usage (
    day    TEXT PRIMARY KEY,
    tokens INTEGER NOT NULL DEFAULT 0,
    calls  INTEGER NOT NULL DEFAULT 0
);
-- The same tokens by LLM server and signed-in user (1.36), for their own limits.
-- ai_usage stays the site total: its limits mean what they meant before.
CREATE TABLE IF NOT EXISTS ai_usage_detail (
    day      TEXT NOT NULL,
    llm      TEXT NOT NULL DEFAULT '',
    username TEXT NOT NULL DEFAULT '',
    tokens   INTEGER NOT NULL DEFAULT 0,
    calls    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (day, llm, username)
);
"""


def _dt_to_str(dt: datetime | None) -> str | None:
    """Convert datetime to a naive-UTC ISO string for DB storage.

    If the input is timezone-aware, it is first converted to UTC
    (``astimezone(timezone.utc)``) before stripping tzinfo. This
    ensures the absolute point in time is preserved regardless of the
    source timezone — a previous implementation simply did
    ``replace(tzinfo=None)`` which silently stored local-time values
    as if they were UTC.
    """
    if dt is None:
        return None
    from datetime import timezone
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_ms_ts(s: str) -> datetime | None:
    """Parse a millisecond UTC timestamp as Graylog emits it
    ("2026-09-09T08:25:02.000Z") to a naive-UTC datetime."""
    if not s:
        return None
    raw = str(s).strip().rstrip("Z")
    if "." not in raw:
        raw += ".000"          # one format, so one parse and one clear failure
    try:
        return datetime.strptime(raw, "%Y-%m-%dT%H:%M:%S.%f")
    except ValueError:
        return None


def _load_json_list(s: str | None) -> list:
    if not s:
        return []
    try:
        v = json.loads(s)
        return v if isinstance(v, list) else []
    except Exception:
        return []


def _str_to_dt(s: str | None) -> datetime | None:
    """Parse an ISO string from the DB back to a naive-UTC datetime.

    The DB stores all timestamps as naive UTC with a ``Z`` suffix.
    This function strips timezone info after parsing so callers always
    get a naive ``datetime`` representing UTC — consistent with
    ``_dt_to_str``.
    """
    if not s:
        return None
    from datetime import timezone
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is not None:
        # Convert to UTC first (should already be, but be safe), then strip
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


AI_MAX_PINNED = 5   # pinned AI conversations per user (owner 2026-11-26)


class ArchiveDB:
    """SQLite-backed archive metadata store."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._conn: sqlite3.Connection | None = None
        self._lock = threading.Lock()

    def connect(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute("PRAGMA busy_timeout=30000")
        self._conn.executescript(SCHEMA_SQL)
        self._migrate(self._conn)

    def _rollback_safely(self) -> None:
        """Rollback any dangling transaction. Safe to call unconditionally.

        Python sqlite3 opens an implicit transaction on the first execute().
        If a write fails (e.g. 'database is locked'), the transaction is left
        dangling on the shared connection. Subsequent writes then immediately
        fail with 'database is locked' even though the underlying contention
        cleared. This helper restores the connection to a clean state.
        """
        try:
            self._conn.rollback()
        except Exception as e:
            log.debug("Rollback failed while restoring the connection", error=str(e))
        # Crash recovery: an archive flips to IMPORTING while being read by an
        # in-flight import job. The importer's finally block flips it back to
        # COMPLETED, but if the process is killed (-9 / OOM / crash), the row
        # gets stuck. On startup we know no import is currently running for
        # this DB connection, so any IMPORTING row is stale → recover it.
        n = self._conn.execute(
            "UPDATE archives SET status = 'completed' WHERE status = 'importing'"
        ).rowcount
        if n:
            import logging
            logging.getLogger("glogarch.db").warning(
                "Recovered %d archive(s) stuck in IMPORTING state on startup", n
            )
        self._conn.commit()

    @staticmethod
    def _migrate(conn: sqlite3.Connection) -> None:
        """Add columns that may be missing from older databases."""
        existing = {row[1] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()}
        if "source" not in existing:
            conn.execute("ALTER TABLE jobs ADD COLUMN source TEXT NOT NULL DEFAULT ''")
        # Structured post-completion result (JSON) — e.g. OpenSearch export
        # index-set coverage {index_sets_covered, index_sets_skipped}. Nullable;
        # only some job types set it.
        if "result_json" not in existing:
            conn.execute("ALTER TABLE jobs ADD COLUMN result_json TEXT")
        existing_arc = {row[1] for row in conn.execute("PRAGMA table_info(archives)").fetchall()}
        if "original_size_bytes" not in existing_arc:
            conn.execute("ALTER TABLE archives ADD COLUMN original_size_bytes INTEGER NOT NULL DEFAULT 0")
        if "field_schema" not in existing_arc:
            conn.execute("ALTER TABLE archives ADD COLUMN field_schema TEXT")
        # Overflow holes: millisecond timestamps an API-mode archive
        # is knowingly missing. Nullable; only set when an overflow occurred.
        if "overflow_ms" not in existing_arc:
            conn.execute("ALTER TABLE archives ADD COLUMN overflow_ms TEXT")
        # Optional tamper-evidence HMAC (v1.12+) — nullable, only set when the
        # integrity feature is enabled.
        if "hmac_sha256" not in existing_arc:
            conn.execute("ALTER TABLE archives ADD COLUMN hmac_sha256 TEXT")
        # Independent integrity ledger (append-only in practice): a record of each
        # sealed archive's hashes, so a copy kept off-box can catch a privileged
        # attacker who rewrites both the archive files and the archives table.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS integrity_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                archive_id INTEGER,
                file_path TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                hmac_sha256 TEXT NOT NULL,
                size_bytes INTEGER NOT NULL DEFAULT 0,
                sealed_at TEXT NOT NULL
            )
        """)
        # api_audit: target_name column (v1.7.1+)
        try:
            existing_audit = {row[1] for row in conn.execute("PRAGMA table_info(api_audit)").fetchall()}
            if existing_audit and "target_name" not in existing_audit:
                conn.execute("ALTER TABLE api_audit ADD COLUMN target_name TEXT NOT NULL DEFAULT ''")
        except Exception as e:
            log.warning("Schema migration failed (api_audit.target_name) — audit inserts may break", error=str(e))
        # sec_sigma_rules.origin (1.33): 'library' = added from the downloaded library
        try:
            existing_sg = {row[1] for row in conn.execute("PRAGMA table_info(sec_sigma_rules)").fetchall()}
            if existing_sg and "origin" not in existing_sg:
                conn.execute("ALTER TABLE sec_sigma_rules ADD COLUMN origin TEXT NOT NULL DEFAULT ''")
        except Exception as e:
            log.warning("Schema migration failed (sec_sigma_rules.origin)", error=str(e))
        # ai_messages.truncated: the answer still stopped at the length limit
        try:
            existing_am = {row[1] for row in conn.execute("PRAGMA table_info(ai_messages)").fetchall()}
            if existing_am and "truncated" not in existing_am:
                conn.execute("ALTER TABLE ai_messages ADD COLUMN truncated INTEGER NOT NULL DEFAULT 0")
            # ai_messages.calls: what each tool call asked Graylog (query, range, count)
            if existing_am and "calls" not in existing_am:
                conn.execute("ALTER TABLE ai_messages ADD COLUMN calls TEXT NOT NULL DEFAULT '[]'")
            # ai_messages.followups: the questions suggested under an answer (1.35)
            if existing_am and "followups" not in existing_am:
                conn.execute("ALTER TABLE ai_messages ADD COLUMN followups TEXT NOT NULL DEFAULT '[]'")
            # ai_messages.llm: which LLM server answered (1.36, several servers)
            if existing_am and "llm" not in existing_am:
                conn.execute("ALTER TABLE ai_messages ADD COLUMN llm TEXT NOT NULL DEFAULT ''")
            # ai_messages.stopped_at: the user stopped this question before it was answered
            if existing_am and "stopped_at" not in existing_am:
                conn.execute("ALTER TABLE ai_messages ADD COLUMN stopped_at TEXT NOT NULL DEFAULT ''")
        except Exception as e:
            log.warning("Schema migration failed (ai_messages)", error=str(e))
        # ai_conversations.pinned_at: pinned to the top of the list (1.36, at most 5)
        try:
            existing_ac = {row[1] for row in conn.execute("PRAGMA table_info(ai_conversations)").fetchall()}
            if existing_ac and "pinned_at" not in existing_ac:
                conn.execute("ALTER TABLE ai_conversations ADD COLUMN pinned_at TEXT")
        except Exception as e:
            log.warning("Schema migration failed (ai_conversations.pinned_at)", error=str(e))
        # report_history: triggered_by column (manual vs scheduled)
        try:
            existing_rh = {row[1] for row in conn.execute("PRAGMA table_info(report_history)").fetchall()}
            if existing_rh and "triggered_by" not in existing_rh:
                conn.execute("ALTER TABLE report_history ADD COLUMN triggered_by TEXT NOT NULL DEFAULT 'manual'")
            if existing_rh and "sha256" not in existing_rh:
                conn.execute("ALTER TABLE report_history ADD COLUMN sha256 TEXT NOT NULL DEFAULT ''")
        except Exception as e:
            log.warning("Schema migration failed (report_history.triggered_by) — history inserts may break", error=str(e))

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self.connect()
        return self._conn  # type: ignore[return-value]

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    # --- Archives ---

    @staticmethod
    def _maybe_compress_schema(schema: str | None) -> str | None:
        """If field_schema JSON exceeds ~4 KiB, store as zlib+base64 with a
        sentinel prefix. Stays backwards-compatible: callers that read the
        column just need to detect the prefix and decompress.
        """
        if not schema or len(schema) < 4096:
            return schema
        import base64, zlib
        return "zlib:" + base64.b64encode(zlib.compress(schema.encode("utf-8"), 6)).decode("ascii")

    @staticmethod
    def decompress_schema(schema: str | None) -> str | None:
        """Inverse of _maybe_compress_schema. Safe on uncompressed input."""
        if not schema or not schema.startswith("zlib:"):
            return schema
        import base64, zlib
        try:
            return zlib.decompress(base64.b64decode(schema[5:])).decode("utf-8")
        except Exception:
            return None

    def record_archive(self, record: ArchiveRecord) -> int:
        with self._lock:
            try:
                cur = self.conn.execute(
                    """INSERT OR REPLACE INTO archives
                       (server_name, stream_id, stream_name, time_from, time_to,
                        file_path, file_size_bytes, original_size_bytes, message_count, part_number, total_parts,
                        checksum_sha256, status, created_at, field_schema, overflow_ms)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        record.server_name,
                        record.stream_id,
                        record.stream_name,
                        _dt_to_str(record.time_from),
                        _dt_to_str(record.time_to),
                        record.file_path,
                        record.file_size_bytes,
                        record.original_size_bytes,
                        record.message_count,
                        record.part_number,
                        record.total_parts,
                        record.checksum_sha256,
                        record.status.value,
                        _dt_to_str(record.created_at),
                        self._maybe_compress_schema(record.field_schema),
                        record.overflow_ms,
                    ),
                )
                self.conn.commit()
                return cur.lastrowid  # type: ignore[return-value]
            except Exception:
                self._rollback_safely()
                raise

    def get_archive_field_schemas(self, archive_ids: list[int]) -> dict[int, str | None]:
        """Return {archive_id: field_schema_json or None} for the given ids.
        Used by import preflight to discover field types without re-scanning files.
        """
        if not archive_ids:
            return {}
        placeholders = ",".join("?" * len(archive_ids))
        rows = self.conn.execute(
            f"SELECT id, field_schema, file_path FROM archives WHERE id IN ({placeholders})",  # nosec B608 - '?' placeholders generated from list length; ids bound as params
            archive_ids,
        ).fetchall()
        return {r["id"]: self.decompress_schema(r["field_schema"]) for r in rows}

    def update_archive_status(
        self, archive_id: int, status: ArchiveStatus, **kwargs: str | int
    ) -> None:
        sets = ["status = ?"]
        vals: list = [status.value]
        if "checksum_sha256" in kwargs:
            sets.append("checksum_sha256 = ?")
            vals.append(kwargs["checksum_sha256"])
        if "file_size_bytes" in kwargs:
            sets.append("file_size_bytes = ?")
            vals.append(kwargs["file_size_bytes"])
        if "message_count" in kwargs:
            sets.append("message_count = ?")
            vals.append(kwargs["message_count"])
        if status == ArchiveStatus.DELETED:
            sets.append("deleted_at = ?")
            vals.append(_dt_to_str(datetime.utcnow()))
        vals.append(archive_id)
        with self._lock:
            try:
                self.conn.execute(f"UPDATE archives SET {', '.join(sets)} WHERE id = ?", vals)  # nosec B608 - column names are fixed literals in the branches above; values bound
                self.conn.commit()
            except Exception:
                self._rollback_safely()
                raise

    # --- Integrity (optional tamper-evidence) ---

    def set_archive_hmac(self, archive_id: int, hmac_sha256: str) -> None:
        """Store the keyed HMAC for an archive (integrity sealing)."""
        with self._lock:
            try:
                self.conn.execute(
                    "UPDATE archives SET hmac_sha256 = ? WHERE id = ?",
                    (hmac_sha256, archive_id),
                )
                self.conn.commit()
            except Exception:
                self._rollback_safely()
                raise

    def add_ledger_entry(self, archive_id, file_path: str, sha256: str,
                         hmac_sha256: str, size_bytes: int, sealed_at: str) -> None:
        """Append an integrity-ledger record (independent hash provenance)."""
        with self._lock:
            try:
                self.conn.execute(
                    """INSERT INTO integrity_ledger
                       (archive_id, file_path, sha256, hmac_sha256, size_bytes, sealed_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (archive_id, file_path, sha256, hmac_sha256, size_bytes, sealed_at),
                )
                self.conn.commit()
            except Exception:
                self._rollback_safely()
                raise

    def list_ledger(self) -> list[dict]:
        """All integrity-ledger entries, oldest first (for off-box manifest export)."""
        rows = self.conn.execute(
            """SELECT archive_id, file_path, sha256, hmac_sha256, size_bytes, sealed_at
               FROM integrity_ledger ORDER BY id"""
        ).fetchall()
        return [dict(r) for r in rows]

    def find_archive(
        self,
        server_name: str,
        stream_id: str | None,
        time_from: datetime,
        time_to: datetime,
    ) -> ArchiveRecord | None:
        """Find an existing archive for the exact time range."""
        if stream_id:
            row = self.conn.execute(
                """SELECT * FROM archives
                   WHERE server_name = ? AND stream_id = ? AND time_from = ? AND time_to = ?
                   AND status != 'deleted'
                   ORDER BY part_number LIMIT 1""",
                (server_name, stream_id, _dt_to_str(time_from), _dt_to_str(time_to)),
            ).fetchone()
        else:
            row = self.conn.execute(
                """SELECT * FROM archives
                   WHERE server_name = ? AND stream_id IS NULL AND time_from = ? AND time_to = ?
                   AND status != 'deleted'
                   ORDER BY part_number LIMIT 1""",
                (server_name, _dt_to_str(time_from), _dt_to_str(time_to)),
            ).fetchone()
        return self._row_to_archive(row) if row else None

    def is_time_range_covered(
        self,
        server_name: str,
        time_from: datetime,
        time_to: datetime,
        exclude_stream_id_prefix: str | None = None,
    ) -> bool:
        """Check if the given time range is already fully covered by any existing archive.

        Cross-mode dedup: finds any completed archive (regardless of stream_id/export mode)
        whose time range fully contains the requested range.
        Used to prevent re-exporting data when switching between API and OpenSearch modes.

        Args:
            exclude_stream_id_prefix: If set, archives whose stream_id starts with this
                prefix are excluded from the check. The OpenSearch exporter passes the
                current index-set prefix here so that sister indices in the same export
                run don't block each other (e.g., when an hourly chunk spans an index
                rotation boundary). API-mode archives are unaffected because their
                stream_id is a stream UUID, not an index name.
        """
        sql = (
            "SELECT 1 FROM archives "
            "WHERE server_name = ? AND status = 'completed' "
            "AND time_from <= ? AND time_to >= ?"
        )
        params: list = [server_name, _dt_to_str(time_from), _dt_to_str(time_to)]
        if exclude_stream_id_prefix:
            sql += " AND stream_id NOT LIKE ?"
            params.append(f"{exclude_stream_id_prefix}%")
        sql += " LIMIT 1"
        row = self.conn.execute(sql, params).fetchone()
        return row is not None

    def get_coverage_ratio(
        self,
        server_name: str,
        time_from: datetime,
        time_to: datetime,
    ) -> float:
        """Calculate what fraction of the given time range is covered by existing archives.

        Returns 0.0 to 1.0. Used by OpenSearch exporter to check if an index's time range
        is already mostly covered by API-mode archives.
        """
        total_seconds = max((time_to - time_from).total_seconds(), 1)
        rows = self.conn.execute(
            """SELECT time_from, time_to FROM archives
               WHERE server_name = ? AND status = 'completed'
               AND time_to > ? AND time_from < ?
               ORDER BY time_from""",
            (server_name, _dt_to_str(time_from), _dt_to_str(time_to)),
        ).fetchall()
        if not rows:
            return 0.0

        # Merge overlapping intervals and sum covered seconds
        intervals = []
        for r in rows:
            a_from = max(_str_to_dt(r["time_from"]), time_from)
            a_to = min(_str_to_dt(r["time_to"]), time_to)
            if a_from < a_to:
                intervals.append((a_from, a_to))

        if not intervals:
            return 0.0

        # Merge overlapping
        intervals.sort()
        merged = [intervals[0]]
        for start, end in intervals[1:]:
            if start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))

        covered = sum((end - start).total_seconds() for start, end in merged)
        return min(covered / total_seconds, 1.0)

    def get_archive(self, archive_id: int) -> ArchiveRecord | None:
        row = self.conn.execute(
            "SELECT * FROM archives WHERE id = ?", (archive_id,)
        ).fetchone()
        return self._row_to_archive(row) if row else None

    def _archive_cols_no_schema(self) -> str:
        """Column list for `archives` minus `field_schema`, derived from the LIVE
        table so migration-added columns (original_size_bytes, hmac_sha256, …)
        are included and a not-yet-migrated DB can't produce a bad SELECT."""
        if getattr(self, "_arch_cols_cache", None):
            return self._arch_cols_cache
        cols = [r[1] for r in self.conn.execute("PRAGMA table_info(archives)").fetchall()
                if r[1] != "field_schema"]
        self._arch_cols_cache = ", ".join(cols) if cols else "*"
        return self._arch_cols_cache

    def list_archives_for_search(
        self,
        server: str | None = None,
        stream_id: str | None = None,
        time_from: datetime | None = None,
        time_to: datetime | None = None,
    ) -> list[ArchiveRecord]:
        """Archives whose time range OVERLAPS the query window, oldest first.

        This is the search's only index. Overlap (not containment) is the
        correct test: an archive covering 09:00-10:00 must be scanned for a
        query of 09:30-09:45, and vice versa — a containment test would
        silently drop most of the matching data.

        Deleted/corrupted rows are excluded, and the order is deterministic
        (time, then id) because the search's resume cursor is an index into
        this list: an unstable order would make "load more" skip or repeat
        archives between pages.
        """
        q = "SELECT * FROM archives WHERE status = 'completed'"
        params: list = []
        if server:
            q += " AND server_name = ?"
            params.append(server)
        if stream_id:
            q += " AND stream_id = ?"
            params.append(stream_id)
        if time_to is not None:
            q += " AND time_from <= ?"
            params.append(_dt_to_str(time_to))
        if time_from is not None:
            q += " AND time_to >= ?"
            params.append(_dt_to_str(time_from))
        q += " ORDER BY time_from ASC, id ASC"
        rows = self.conn.execute(q, params).fetchall()
        return [self._row_to_archive(r) for r in rows]

    def list_archives(
        self,
        server: str | None = None,
        stream: str | None = None,
        time_from: datetime | None = None,
        time_to: datetime | None = None,
        status: ArchiveStatus | None = None,
        sort: str = "time_from",
        order: str = "DESC",
        include_schema: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[ArchiveRecord]:
        """List archives.

        `field_schema` is EXCLUDED by default: it averages ~2.5 KB (max 41 KB)
        per row, and nothing here consumes it — `_row_to_archive()` does not even
        copy it into `ArchiveRecord`, and preflight reads the column with its own
        targeted query. Selecting it made `fetchall()` materialize every schema
        blob at once purely to throw it away: a ~62 MB PEAK for a 24.5K-archive
        import, ~177 MB for a 69K-archive export dedup scan. Peak RSS is what
        trips the OOM killer on the common co-located single-VM deployment, so
        this spike is worth removing even though it is transient.
        """
        ALLOWED_SORT = {"time_from", "time_to", "message_count", "file_size_bytes", "created_at", "server_name"}
        sort_col = sort if sort in ALLOWED_SORT else "time_from"
        sort_dir = "ASC" if order.upper() == "ASC" else "DESC"
        cols = "*" if include_schema else self._archive_cols_no_schema()
        query = f"SELECT {cols} FROM archives WHERE 1=1"  # nosec B608 - cols is internal; sort/order come from the ALLOWED_SORT whitelist
        params: list = []
        if server:
            query += " AND server_name = ?"
            params.append(server)
        if stream:
            query += " AND (stream_id = ? OR stream_name = ?)"
            params.extend([stream, stream])
        if time_from:
            query += " AND time_to >= ?"
            params.append(_dt_to_str(time_from))
        if time_to:
            query += " AND time_from <= ?"
            params.append(_dt_to_str(time_to))
        if status:
            query += " AND status = ?"
            params.append(status.value)
        else:
            query += " AND status != 'deleted'"
        query += f" ORDER BY {sort_col} {sort_dir}"
        if limit is not None:
            # Push paging into SQL. The Archives page used to materialize EVERY
            # matching row (70K+ at customer scale) just to slice one page out of
            # it — a large allocation spike on every page view / refresh.
            query += " LIMIT ? OFFSET ?"
            params.extend([int(limit), int(offset or 0)])
        rows = self.conn.execute(query, params).fetchall()
        return [self._row_to_archive(r) for r in rows]

    def overflow_holes(
        self,
        server_name: str,
        time_from: datetime | None = None,
        time_to: datetime | None = None,
    ) -> list[tuple[str, str]]:
        """(overflow_ms_timestamp, archive_file_path) for every API-mode archive
        that is knowingly missing part of a millisecond in this window.

        The time-range hole in `covered_ranges()` lets an OpenSearch-direct run
        fetch that millisecond — but the API archive already holds the first
        10,000 records OF that millisecond, and a range cannot tell those from
        the unread rest. The OS exporter reads the ids archived in the hole
        from the file named here and excludes them by `gl2_message_id`, so the
        refill is exactly the unread records and nothing is archived twice.
        """
        sql = ("SELECT overflow_ms, file_path FROM archives "
               "WHERE server_name = ? AND status = 'completed' "
               "AND stream_id IS NULL AND overflow_ms IS NOT NULL")
        params: list = [server_name]
        if time_to:
            sql += " AND time_from <= ?"; params.append(_dt_to_str(time_to))
        if time_from:
            sql += " AND time_to >= ?"; params.append(_dt_to_str(time_from))
        out: list[tuple[str, str]] = []
        for o, fp in self.conn.execute(sql, params).fetchall():
            for ts in _load_json_list(o):
                if _parse_ms_ts(ts):
                    out.append((str(ts), fp))
        return out

    def archive_spans(
        self,
        server_name: str,
        time_from: datetime,
        time_to: datetime,
    ) -> list[tuple[datetime, datetime]]:
        """(time_from, time_to) of every completed archive of the server that
        touches [time_from, time_to], any stream or mode, oldest first, plus
        the newest one that ends before time_from (so a hole that starts before
        the window still has its left edge).
        Used to find holes earlier runs left (Exporter.find_gaps)."""
        before = self.conn.execute(
            "SELECT time_from, time_to FROM archives "
            "WHERE server_name = ? AND status = 'completed' AND time_to < ? "
            "ORDER BY time_to DESC LIMIT 1",
            (server_name, _dt_to_str(time_from))).fetchall()
        rows = before + self.conn.execute(
            "SELECT time_from, time_to FROM archives "
            "WHERE server_name = ? AND status = 'completed' "
            "AND time_from <= ? AND time_to >= ? ORDER BY time_from",
            (server_name, _dt_to_str(time_to), _dt_to_str(time_from))).fetchall()
        out = []
        for a, b in rows:
            fa, fb = _str_to_dt(a), _str_to_dt(b)
            if fa and fb:
                out.append((fa, fb))
        return out

    def covered_null_spans(
        self,
        server_name: str,
        time_from: datetime | None = None,
        time_to: datetime | None = None,
    ) -> list[tuple[datetime, datetime]]:
        """Merged ranges of API-mode (stream_id IS NULL) archives only.

        These are IDENTICAL for every index of a server, yet the export used
        to re-fetch them inside every covered_ranges() call — 54 times per
        scheduled run on a 27-index-set site. Compute once per run and pass
        the result to covered_ranges(null_spans=...)."""
        sql = ("SELECT time_from, time_to, overflow_ms FROM archives "
               "WHERE server_name = ? AND status = 'completed' "
               "AND stream_id IS NULL")
        params: list = [server_name]
        if time_to:
            sql += " AND time_from <= ?"; params.append(_dt_to_str(time_to))
        if time_from:
            sql += " AND time_to >= ?"; params.append(_dt_to_str(time_from))
        return self._merge_rows_with_holes(self.conn.execute(sql, params).fetchall())

    def covered_ranges(
        self,
        server_name: str,
        index_name: str,
        exclude_stream_id_prefix: str | None = None,
        time_from: datetime | None = None,
        time_to: datetime | None = None,
        null_spans: list[tuple[datetime, datetime]] | None = None,
    ) -> list[tuple[datetime, datetime]]:
        """Merged, disjoint time ranges already archived for this index.

        Mirrors the per-chunk dedup rule used during export: a chunk counts as
        covered when an archive exists for THIS index, or when any archive from a
        different index prefix covers it (cross-mode). Returned ranges let the
        exporter exclude that time at the QUERY level instead of fetching every
        document and discarding it.
        """
        # Count ONLY archives that hold the FULL data for their time range:
        #   * stream_id IS NULL  -> an API-mode export of ALL streams
        #   * stream_id = index  -> this very OpenSearch index
        # Everything else is a partial view and must NOT suppress an export:
        #   * a sister index of the same prefix (graylog_75 vs graylog_74) holds
        #     only its own slice of the hour,
        #   * a stream-FILTERED API archive (stream_id = a stream UUID) holds
        #     only that stream's messages.
        # The previous rule was `stream_id NOT LIKE '<prefix>%'`, which had two
        # defects: in SQL `NULL NOT LIKE 'x%'` is NULL (not true), so API-mode
        # archives — the main cross-mode case — were invisible and the same logs
        # got archived twice when switching modes; and it accepted partial,
        # stream-filtered archives as if they covered everything.
        if null_spans is not None:
            # Caller precomputed the (identical-for-every-index) NULL spans:
            # fetch only THIS index's rows — a direct seek on
            # idx_archives_srv_stream_time instead of a 70K-row scan.
            sql = ("SELECT time_from, time_to, overflow_ms FROM archives "
                   "WHERE server_name = ? AND status = 'completed' "
                   "AND stream_id = ?")
        else:
            sql = ("SELECT time_from, time_to, overflow_ms FROM archives "
                   "WHERE server_name = ? AND status = 'completed' "
                   "AND (stream_id IS NULL OR stream_id = ?)")
        params: list = [server_name, index_name]
        if time_to:
            sql += " AND time_from <= ?"
            params.append(_dt_to_str(time_to))
        if time_from:
            sql += " AND time_to >= ?"
            params.append(_dt_to_str(time_from))
        sql += " ORDER BY time_from"

        rows = self.conn.execute(sql, params).fetchall()
        own = self._merge_rows_with_holes(rows)
        if not null_spans:
            return own
        # merge the per-index spans with the precomputed NULL spans
        allspans = sorted(list(null_spans) + own)
        merged: list[list[datetime]] = [list(allspans[0])] if allspans else []
        for a, b in allspans[1:]:
            if a <= merged[-1][1]:
                if b > merged[-1][1]:
                    merged[-1][1] = b
            else:
                merged.append([a, b])
        return [(m[0], m[1]) for m in merged]

    def _merge_rows_with_holes(self, rows) -> list[tuple[datetime, datetime]]:
        """Merge (time_from, time_to, overflow_ms) rows into disjoint ranges,
        leaving a 1 ms HOLE at every overflow timestamp.

        An API-mode archive that hit Graylog's 10,000-per-query ceiling inside
        one millisecond is complete everywhere EXCEPT that millisecond. Counting
        it as full coverage meant the documented remedy — "re-run this window
        in OpenSearch Direct" — was de-duplicated away and fetched nothing; the
        only way to recover the records was to delete the whole hour's archive
        and re-export it. With the hole, an OpenSearch-direct run of the same
        window skips everything already archived and fetches exactly the
        missing millisecond. Both dedup rules (the query's must_not filter and
        the per-chunk skip) read this same list, so they cannot disagree.

        Rows without holes take the fast string-merge path unchanged; holed
        rows are rare (one per overflow) and are split with datetimes.
        """
        plain = [(a, b) for a, b, o in rows if not o]
        holed = [(a, b, o) for a, b, o in rows if o]
        spans: list[tuple[datetime, datetime]] = list(self._merge_span_rows(plain))
        for a, b, o in holed:
            fa, fb = _str_to_dt(a), _str_to_dt(b)
            if not fa or not fb or fb <= fa:
                continue
            cuts = sorted(t for t in (_parse_ms_ts(x) for x in _load_json_list(o)) if t)
            cur = fa
            for t in cuts:
                if t < cur or t >= fb:
                    continue
                if t > cur:
                    spans.append((cur, t))
                cur = t + timedelta(milliseconds=1)
            if cur < fb:
                spans.append((cur, fb))
        if not spans:
            return []
        spans.sort()
        merged: list[list[datetime]] = [list(spans[0])]
        for a, b in spans[1:]:
            if a <= merged[-1][1]:
                if b > merged[-1][1]:
                    merged[-1][1] = b
            else:
                merged.append([a, b])
        return [(a, b) for a, b in merged]

    @staticmethod
    def _merge_span_rows(rows) -> list[tuple[datetime, datetime]]:
        """Merge sorted (time_from, time_to) rows into disjoint ranges.

        PERFORMANCE (measured at 200K archives / 74K matching rows): strptime
        on every row made this 1.05 s per call; the canonical storage format
        %Y-%m-%dT%H:%M:%SZ is fixed-width so its LEXICOGRAPHIC order equals
        its time order — merge on the raw strings (62 ms) and parse only the
        few merged spans. Any non-canonical row (pre-1.x data) falls back to
        the parse-everything path; correctness never depends on the fast path.
        """
        if not rows:
            return []
        if all(isinstance(a, str) and isinstance(b, str)
               and len(a) == 20 and len(b) == 20 and a[10] == "T" and b[10] == "T"
               for a, b in rows):
            sspans = sorted((a, b) for a, b in rows if b > a)
            if not sspans:
                return []
            sm: list[list[str]] = [list(sspans[0])]
            for a, b in sspans[1:]:
                if a <= sm[-1][1]:
                    if b > sm[-1][1]:
                        sm[-1][1] = b
                else:
                    sm.append([a, b])
            out = []
            for a, b in sm:
                da, db_ = _str_to_dt(a), _str_to_dt(b)
                if da and db_:
                    out.append((da, db_))
            return out
        spans = []
        for r in rows:
            a, b = _str_to_dt(r[0]), _str_to_dt(r[1])
            if a and b and b > a:
                spans.append((a, b))
        spans.sort()
        if not spans:
            return []
        merged: list[list[datetime]] = [list(spans[0])]
        for a, b in spans[1:]:
            if a <= merged[-1][1]:
                if b > merged[-1][1]:
                    merged[-1][1] = b
            else:
                merged.append([a, b])
        return [(m[0], m[1]) for m in merged]

    def count_archives(
        self,
        server: str | None = None,
        stream: str | None = None,
        time_from: datetime | None = None,
        time_to: datetime | None = None,
        status: ArchiveStatus | None = None,
    ) -> int:
        """COUNT(*) matching the same filters as list_archives (for pagination
        totals, without materializing the rows)."""
        query = "SELECT COUNT(*) FROM archives WHERE 1=1"
        params: list = []
        if server:
            query += " AND server_name = ?"
            params.append(server)
        if stream:
            query += " AND (stream_id = ? OR stream_name = ?)"
            params.extend([stream, stream])
        if time_from:
            query += " AND time_to >= ?"
            params.append(_dt_to_str(time_from))
        if time_to:
            query += " AND time_from <= ?"
            params.append(_dt_to_str(time_to))
        if status:
            query += " AND status = ?"
            params.append(status.value)
        else:
            query += " AND status != 'deleted'"
        row = self.conn.execute(query, params).fetchone()
        return int(row[0]) if row else 0

    def get_archives_older_than(self, days: int) -> list[ArchiveRecord]:
        cutoff = datetime.utcnow() - timedelta(days=days)
        rows = self.conn.execute(
            "SELECT * FROM archives WHERE time_to < ? AND status = 'completed'",
            (_dt_to_str(cutoff),),
        ).fetchall()
        return [self._row_to_archive(r) for r in rows]

    def get_archive_stats(self) -> dict:
        """Get summary statistics."""
        row = self.conn.execute(
            """SELECT
                COUNT(*) as total,
                COALESCE(SUM(file_size_bytes), 0) as total_bytes,
                COALESCE(SUM(original_size_bytes), 0) as total_original_bytes,
                COALESCE(SUM(message_count), 0) as total_messages,
                MIN(time_from) as earliest,
                MAX(time_to) as latest
               FROM archives WHERE status = 'completed'"""
        ).fetchone()
        return dict(row) if row else {}

    def get_archive_day_coverage(self, max_ranges: int = 20) -> dict:
        """How many calendar days (host local time) the completed archives hold.

        The span MIN(time_from)..MAX(time_to) is not the answer: one stray old
        archive stretches it (.36 had one archive on 01-01 and nothing again
        until 02-11). So count the days that hold an archive and list the
        days in between that hold none.
        """
        w = "status = 'completed'"
        # time_to is exclusive: a 23:00-00:00 hour belongs to the day it starts.
        rows = self.conn.execute(
            f"""SELECT date(time_from, 'localtime') FROM archives WHERE {w}
                UNION
                SELECT date(time_to, '-1 second', 'localtime') FROM archives WHERE {w}"""  # nosec B608 - fixed literal
        ).fetchall()
        days = {r[0] for r in rows if r[0]}
        # An archive longer than a day also covers the days in between.
        for tf, tt in self.conn.execute(
            f"""SELECT date(time_from, 'localtime'), date(time_to, '-1 second', 'localtime')
                FROM archives WHERE {w} AND julianday(time_to) - julianday(time_from) > 1"""  # nosec B608 - fixed literal
        ):
            if not (tf and tt):
                continue
            d, end = datetime.fromisoformat(tf).date(), datetime.fromisoformat(tt).date()
            while d <= end:
                days.add(d.isoformat())
                d += timedelta(days=1)
        if not days:
            return {"days": 0, "first_day": None, "last_day": None,
                    "span_days": 0, "missing_days": 0, "missing_ranges": [],
                    "missing_ranges_total": 0}
        first, last = min(days), max(days)
        d, end = datetime.fromisoformat(first).date(), datetime.fromisoformat(last).date()
        span = (end - d).days + 1
        ranges, run = [], None
        while d <= end:
            iso = d.isoformat()
            if iso not in days:
                run = [iso, iso] if run is None else [run[0], iso]
            elif run is not None:
                ranges.append(run)
                run = None
            d += timedelta(days=1)
        return {
            "days": len(days),
            "first_day": first,
            "last_day": last,
            "span_days": span,
            "missing_days": span - len(days),
            "missing_ranges": ranges[:max_ranges],
            "missing_ranges_total": len(ranges),
        }

    # --- Jobs ---

    def create_job(self, job: JobRecord) -> None:
        from glogarch.utils.sanitize import sanitize
        with self._lock:
            try:
                self.conn.execute(
                    """INSERT INTO jobs (id, job_type, status, progress_pct, messages_done,
                       messages_total, config_json, error_message, started_at, completed_at, created_at, source)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        job.id,
                        job.job_type.value,
                        job.status.value,
                        job.progress_pct,
                        job.messages_done,
                        job.messages_total,
                        job.config_json,
                        sanitize(job.error_message),
                        _dt_to_str(job.started_at),
                        _dt_to_str(job.completed_at),
                        _dt_to_str(job.created_at),
                        job.source,
                    ),
                )
                self.conn.commit()
            except Exception:
                self._rollback_safely()
                raise

    def update_job(self, job_id: str, **kwargs) -> None:
        from glogarch.utils.sanitize import sanitize
        ALLOWED_JOB_COLS = {"status", "progress_pct", "messages_done", "messages_total",
                            "config_json", "error_message", "started_at", "completed_at", "source",
                            "result_json"}
        sets = []
        vals = []
        for key, val in kwargs.items():
            if key not in ALLOWED_JOB_COLS:
                continue
            if key in ("status",) and hasattr(val, "value"):
                val = val.value
            if isinstance(val, datetime):
                val = _dt_to_str(val)
            # Strip credentials from any user-visible message column
            if key == "error_message" and val is not None:
                val = sanitize(val)
            sets.append(f"{key} = ?")
            vals.append(val)
        if not sets:
            return
        vals.append(job_id)
        with self._lock:
            try:
                self.conn.execute(f"UPDATE jobs SET {', '.join(sets)} WHERE id = ?", vals)  # nosec B608 - column names filtered by ALLOWED_JOB_COLS; values bound
                self.conn.commit()
            except Exception:
                self._rollback_safely()
                raise

    def get_job(self, job_id: str) -> JobRecord | None:
        row = self.conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return self._row_to_job(row) if row else None

    def list_jobs(self, limit: int = 50) -> list[JobRecord]:
        rows = self.conn.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [self._row_to_job(r) for r in rows]

    def list_running_jobs(self) -> list:
        """All jobs currently `running`, ANY age. A scheduled export of a large
        historical backlog can run for weeks (throttled by the backpressure
        guard); its row keeps status='running' with advancing progress, so it
        would fall off `list_jobs(limit=50)` (newest-first) — this finds it
        regardless of age, indexed by idx_jobs_created only for the sort."""
        rows = self.conn.execute(
            "SELECT * FROM jobs WHERE status = 'running' ORDER BY started_at ASC"
        ).fetchall()
        return [self._row_to_job(r) for r in rows]

    def prune_jobs(self, keep_days: int) -> int:
        """Delete TERMINAL job rows older than keep_days. 0 disables.

        Job rows grow forever otherwise (every scheduled run adds one).
        Running/pending rows are never touched, whatever their age — pruning
        must not be able to erase a live job's state.
        """
        if not keep_days or keep_days <= 0:
            return 0
        cutoff = _dt_to_str(datetime.utcnow() - timedelta(days=keep_days))
        with self._lock:
            try:
                cur = self.conn.execute(
                    "DELETE FROM jobs WHERE created_at < ? "
                    "AND status IN ('completed','failed','cancelled')", (cutoff,))
                self.conn.commit()
                if cur.rowcount:
                    log.info("Pruned old job-history rows",
                             deleted=cur.rowcount, keep_days=keep_days)
                return cur.rowcount or 0
            except Exception as e:
                self._rollback_safely()
                log.warning("Job-history prune failed", error=str(e))
                return 0

    # --- Schedules ---

    def save_schedule(self, sched: ScheduleRecord) -> int:
        with self._lock:
            try:
                # Check if exists — if so, preserve last_run_at
                existing = self.conn.execute(
                    "SELECT last_run_at FROM schedules WHERE name = ?", (sched.name,)
                ).fetchone()
                if existing and sched.last_run_at is None:
                    sched.last_run_at = _str_to_dt(existing["last_run_at"])

                cur = self.conn.execute(
                    """INSERT OR REPLACE INTO schedules
                       (name, job_type, cron_expr, config_json, enabled, last_run_at, next_run_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        sched.name,
                        sched.job_type,
                        sched.cron_expr,
                        sched.config_json,
                        1 if sched.enabled else 0,
                        _dt_to_str(sched.last_run_at),
                        _dt_to_str(sched.next_run_at),
                    ),
                )
                self.conn.commit()
            except Exception:
                self._rollback_safely()
                raise
            return cur.lastrowid  # type: ignore[return-value]

    def list_schedules(self) -> list[ScheduleRecord]:
        rows = self.conn.execute("SELECT * FROM schedules ORDER BY name").fetchall()
        return [self._row_to_schedule(r) for r in rows]

    def delete_schedule(self, name: str) -> None:
        with self._lock:
            try:
                self.conn.execute("DELETE FROM schedules WHERE name = ?", (name,))
                self.conn.commit()
            except Exception:
                self._rollback_safely()
                raise

    # --- Reports (beta) ---

    def save_report(self, name: str, config_json: str, enabled: bool = True) -> int:
        with self._lock:
            try:
                existing = self.conn.execute(
                    "SELECT last_run_at, created_at FROM reports WHERE name = ?", (name,)
                ).fetchone()
                created = existing["created_at"] if existing else _dt_to_str(datetime.utcnow())
                last_run = existing["last_run_at"] if existing else None
                cur = self.conn.execute(
                    """INSERT OR REPLACE INTO reports
                       (id, name, config_json, enabled, last_run_at, created_at)
                       VALUES ((SELECT id FROM reports WHERE name = ?), ?, ?, ?, ?, ?)""",
                    (name, name, config_json, 1 if enabled else 0, last_run, created),
                )
                self.conn.commit()
                return cur.lastrowid  # type: ignore[return-value]
            except Exception:
                self._rollback_safely()
                raise

    def list_reports(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM reports ORDER BY name").fetchall()
        return [dict(r) for r in rows]

    def get_report(self, name: str) -> dict | None:
        r = self.conn.execute("SELECT * FROM reports WHERE name = ?", (name,)).fetchone()
        return dict(r) if r else None

    def get_report_by_id(self, report_id: int) -> dict | None:
        r = self.conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
        return dict(r) if r else None

    def update_report(self, report_id: int, name: str, config_json: str,
                      enabled: bool = True) -> None:
        """Update an existing report by its stable id — supports renaming.
        Raises sqlite3.IntegrityError if the new name collides with another row."""
        with self._lock:
            try:
                self.conn.execute(
                    "UPDATE reports SET name = ?, config_json = ?, enabled = ? WHERE id = ?",
                    (name, config_json, 1 if enabled else 0, report_id),
                )
                self.conn.commit()
            except Exception:
                self._rollback_safely()
                raise

    def set_report_enabled(self, name: str, enabled: bool) -> bool:
        """Turn a report definition on or off (its schedule runs only when on)."""
        with self._lock:
            try:
                cur = self.conn.execute("UPDATE reports SET enabled = ? WHERE name = ?", (1 if enabled else 0, name))
                self.conn.commit()
                return cur.rowcount > 0
            except Exception:
                self._rollback_safely()
                raise

    def delete_report_by_id(self, report_id: int) -> None:
        with self._lock:
            try:
                self.conn.execute("DELETE FROM reports WHERE id = ?", (report_id,))
                self.conn.commit()
            except Exception:
                self._rollback_safely()
                raise

    def delete_report(self, name: str) -> None:
        with self._lock:
            try:
                self.conn.execute("DELETE FROM reports WHERE name = ?", (name,))
                self.conn.commit()
            except Exception:
                self._rollback_safely()
                raise

    def update_report_last_run(self, name: str, when: datetime | None = None) -> None:
        with self._lock:
            try:
                self.conn.execute("UPDATE reports SET last_run_at = ? WHERE name = ?",
                                  (_dt_to_str(when or datetime.utcnow()), name))
                self.conn.commit()
            except Exception:
                self._rollback_safely()
                raise

    def record_report_history(self, report_name: str, file_path: str, filename: str,
                              size_bytes: int, status: str = "completed",
                              error: str | None = None, triggered_by: str = "manual",
                              sha256: str = "") -> int:
        with self._lock:
            try:
                cur = self.conn.execute(
                    """INSERT INTO report_history
                       (report_name, file_path, filename, size_bytes, status, error, triggered_by, sha256, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (report_name, file_path, filename, size_bytes, status, error, triggered_by, sha256,
                     _dt_to_str(datetime.utcnow())),
                )
                self.conn.commit()
                return cur.lastrowid  # type: ignore[return-value]
            except Exception:
                self._rollback_safely()
                raise

    # --- Alerting change log ------------------------------------------------

    def add_alerting_change(self, batch_id: str, server: str, definition_id: str, title: str,
                            action: str, before: list, after: list, username: str,
                            undoes_batch: str | None = None) -> int:
        import json as _json
        with self._lock:
            try:
                cur = self.conn.execute(
                    """INSERT INTO alerting_changes (batch_id, server, definition_id, title, action,
                       before_notifications, after_notifications, status, username, undoes_batch,
                       created_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)""",
                    (batch_id, server, definition_id, title, action, _json.dumps(before),
                     _json.dumps(after), username, undoes_batch, _dt_to_str(datetime.utcnow())))
                self.conn.commit()
                return cur.lastrowid  # type: ignore[return-value]
            except Exception:
                self._rollback_safely()
                raise

    def set_alerting_change(self, row_id: int, status: str, error: str | None = None) -> None:
        from glogarch.utils.sanitize import sanitize
        with self._lock:
            try:
                self.conn.execute(
                    "UPDATE alerting_changes SET status = ?, error = ?, updated_at = ? WHERE id = ?",
                    (status, sanitize(error) if error else None, _dt_to_str(datetime.utcnow()), row_id))
                self.conn.commit()
            except Exception:
                self._rollback_safely()
                raise

    def list_alerting_changes(self, batch_id: str) -> list[dict]:
        import json as _json
        rows = self.conn.execute(
            "SELECT * FROM alerting_changes WHERE batch_id = ? ORDER BY id", (batch_id,)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["before_notifications"] = _json.loads(d["before_notifications"] or "[]")
            d["after_notifications"] = _json.loads(d["after_notifications"] or "[]")
            out.append(d)
        return out

    def list_alerting_batches(self, server: str, limit: int = 50) -> list[dict]:
        rows = self.conn.execute(
            """SELECT batch_id, MIN(created_at) AS created_at, MAX(username) AS username,
                      MAX(action) AS action, MAX(undoes_batch) AS undoes_batch,
                      SUM(status = 'applied') AS applied, SUM(status = 'pending') AS pending,
                      SUM(status = 'failed') AS failed, SUM(status = 'restored') AS restored,
                      COUNT(*) AS total
               FROM alerting_changes WHERE server = ?
               GROUP BY batch_id ORDER BY MIN(id) DESC LIMIT ?""", (server, limit)).fetchall()
        return [dict(r) for r in rows]

    # --- Security incidents -------------------------------------------------

    def apply_security_findings(self, server: str, findings: list[dict], now: datetime, *,
                                reopen_hours: float, new_days: int,
                                learning: bool) -> list[dict]:
        """Merge one run's findings into sec_incidents, in ONE transaction.

        Returns one dict per finding: {id, change: new|escalated|ongoing,
        severity, notified_at, notified_severity}. `learning` suppresses the NEW
        badge (the first day after the feature is enabled, when everything is
        "new")."""
        import json as _json
        now_s = _dt_to_str(now)
        reopen_s = _dt_to_str(now - timedelta(hours=reopen_hours))
        new_s = _dt_to_str(now - timedelta(days=new_days))
        rank = {"low": 0, "medium": 1, "high": 2}
        out: list[dict] = []
        with self._lock:
            try:
                for f in findings:
                    cnt = int((f.get("metrics") or {}).get("count") or 0)
                    ext = None if f.get("external") is None else int(bool(f["external"]))
                    row = self.conn.execute(
                        """SELECT * FROM sec_incidents WHERE server = ? AND detector = ? AND entity = ?
                           AND status IN ('open', 'acknowledged') AND last_seen >= ?
                           ORDER BY id DESC LIMIT 1""",
                        (server, f["detector"], f["entity"], reopen_s)).fetchone()
                    if row:
                        sev = f["severity"] if rank.get(f["severity"], 0) > rank.get(row["severity"], 0) \
                            else row["severity"]
                        change = "escalated" if sev != row["severity"] else "ongoing"
                        self.conn.execute(
                            """UPDATE sec_incidents SET severity = ?, last_seen = ?, runs = runs + 1,
                               peak_count = MAX(peak_count, ?), last_count = ?, metrics = ?, query = ?,
                               entity_field = ? WHERE id = ?""",
                            (sev, now_s, cnt, cnt, _json.dumps(f.get("metrics") or {}),
                             f.get("query") or "", f.get("entity_field") or "", row["id"]))
                        out.append({"id": row["id"], "change": change, "severity": sev,
                                    "notified_at": row["notified_at"],
                                    "notified_severity": row["notified_severity"]})
                    else:
                        seen = self.conn.execute(
                            "SELECT last_seen FROM sec_seen WHERE server = ? AND detector = ? AND entity = ?",
                            (server, f["detector"], f["entity"])).fetchone()
                        is_new = int(not learning and (seen is None or seen["last_seen"] < new_s))
                        cur = self.conn.execute(
                            """INSERT INTO sec_incidents (server, detector, entity, entity_field, severity,
                               status, is_new, external, first_seen, last_seen, runs, peak_count,
                               last_count, metrics, query)
                               VALUES (?, ?, ?, ?, ?, 'open', ?, ?, ?, ?, 1, ?, ?, ?, ?)""",
                            (server, f["detector"], f["entity"], f.get("entity_field") or "",
                             f["severity"], is_new, ext, now_s, now_s, cnt, cnt,
                             _json.dumps(f.get("metrics") or {}), f.get("query") or ""))
                        out.append({"id": cur.lastrowid, "change": "new", "severity": f["severity"],
                                    "notified_at": None, "notified_severity": None})
                    self.conn.execute(
                        """INSERT INTO sec_seen (server, detector, entity, first_seen, last_seen)
                           VALUES (?, ?, ?, ?, ?) ON CONFLICT (server, detector, entity)
                           DO UPDATE SET last_seen = excluded.last_seen""",
                        (server, f["detector"], f["entity"], now_s, now_s))
                self.conn.commit()
            except Exception:
                self._rollback_safely()
                raise
        return out

    def mark_security_notified(self, ids: list[int], severities: dict[int, str], now: datetime) -> None:
        if not ids:
            return
        with self._lock:
            try:
                for i in ids:
                    self.conn.execute(
                        "UPDATE sec_incidents SET notified_at = ?, notified_severity = ? WHERE id = ?",
                        (_dt_to_str(now), severities.get(i), i))
                self.conn.commit()
            except Exception:
                self._rollback_safely()
                raise

    def set_security_status(self, incident_id: int, status: str, username: str) -> bool:
        if status not in ("open", "acknowledged", "closed"):
            raise ValueError(f"unknown status {status!r}")
        with self._lock:
            try:
                cur = self.conn.execute(
                    "UPDATE sec_incidents SET status = ?, status_by = ?, status_at = ? WHERE id = ?",
                    (status, username, _dt_to_str(datetime.utcnow()), incident_id))
                self.conn.commit()
                return cur.rowcount > 0
            except Exception:
                self._rollback_safely()
                raise

    def list_security_incidents(self, *, server: str | None = None, status: str | None = None,
                                severity: str | None = None, detector: str | None = None,
                                limit: int = 100, offset: int = 0) -> tuple[list[dict], int]:
        import json as _json
        where, args = [], []
        for col, val in (("server", server), ("status", status), ("severity", severity),
                         ("detector", detector)):
            if val:
                where.append(f"{col} = ?")
                args.append(val)
        w = (" WHERE " + " AND ".join(where)) if where else ""
        total = self.conn.execute(f"SELECT COUNT(*) FROM sec_incidents{w}", args).fetchone()[0]  # nosec B608 - fixed column names, bound values
        rows = self.conn.execute(
            f"SELECT * FROM sec_incidents{w} ORDER BY last_seen DESC, id DESC LIMIT ? OFFSET ?",  # nosec B608 - fixed column names, bound values
            (*args, int(limit), int(offset))).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["metrics"] = _json.loads(d.get("metrics") or "{}")
            out.append(d)
        return out, total

    def get_security_incident(self, incident_id: int) -> dict | None:
        import json as _json
        r = self.conn.execute("SELECT * FROM sec_incidents WHERE id = ?", (incident_id,)).fetchone()
        if not r:
            return None
        d = dict(r)
        d["metrics"] = _json.loads(d.get("metrics") or "{}")
        return d

    def security_counts(self, since: datetime) -> dict:
        rows = self.conn.execute(
            """SELECT severity, status, COUNT(*) AS n FROM sec_incidents
               WHERE last_seen >= ? GROUP BY severity, status""", (_dt_to_str(since),)).fetchall()
        return {f"{r['severity']}:{r['status']}": r["n"] for r in rows}

    def start_security_run(self, server: str, window_from: datetime, window_to: datetime) -> int:
        with self._lock:
            try:
                cur = self.conn.execute(
                    """INSERT INTO sec_runs (server, started_at, window_from, window_to, status)
                       VALUES (?, ?, ?, ?, 'running')""",
                    (server, _dt_to_str(datetime.utcnow()), _dt_to_str(window_from),
                     _dt_to_str(window_to)))
                self.conn.commit()
                return cur.lastrowid  # type: ignore[return-value]
            except Exception:
                self._rollback_safely()
                raise

    def finish_security_run(self, run_id: int, *, status: str, queries: int = 0, findings: int = 0,
                            opened: int = 0, coverage: list | None = None,
                            errors: list | None = None, note: str | None = None) -> None:
        import json as _json
        from glogarch.utils.sanitize import sanitize
        with self._lock:
            try:
                self.conn.execute(
                    """UPDATE sec_runs SET finished_at = ?, status = ?, queries = ?, findings = ?,
                       opened = ?, coverage = ?, errors = ?, note = ? WHERE id = ?""",
                    (_dt_to_str(datetime.utcnow()), status, queries, findings, opened,
                     _json.dumps(coverage or []),
                     _json.dumps([sanitize(str(e)) for e in (errors or [])]),
                     sanitize(note) if note else None, run_id))
                self.conn.commit()
            except Exception:
                self._rollback_safely()
                raise

    def list_security_runs(self, server: str | None = None, limit: int = 20) -> list[dict]:
        import json as _json
        if server:
            rows = self.conn.execute(
                "SELECT * FROM sec_runs WHERE server = ? ORDER BY id DESC LIMIT ?",
                (server, limit)).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM sec_runs ORDER BY id DESC LIMIT ?",
                                     (limit,)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["coverage"] = _json.loads(d.get("coverage") or "[]")
            d["errors"] = _json.loads(d.get("errors") or "[]")
            out.append(d)
        return out

    def first_security_run_at(self) -> str | None:
        r = self.conn.execute("SELECT MIN(started_at) FROM sec_runs").fetchone()
        return r[0] if r else None

    def prune_security(self, incident_days: int, run_days: int = 30, seen_days: int = 400,
                       volume_days: int = 16) -> int:
        now = datetime.utcnow()
        with self._lock:
            try:
                # an incident in a case is evidence of that investigation: kept (added 1.24)
                n = self.conn.execute("DELETE FROM sec_incidents WHERE last_seen < ? AND id NOT IN "
                                      "(SELECT incident_id FROM sec_case_incidents)",
                                      (_dt_to_str(now - timedelta(days=incident_days)),)).rowcount
                self.conn.execute("DELETE FROM sec_ai_analyses WHERE incident_id NOT IN "
                                  "(SELECT id FROM sec_incidents)")
                self.conn.execute("DELETE FROM sec_runs WHERE started_at < ?",
                                  (_dt_to_str(now - timedelta(days=run_days)),))
                self.conn.execute("DELETE FROM sec_seen WHERE last_seen < ?",
                                  (_dt_to_str(now - timedelta(days=seen_days)),))
                self.conn.execute("DELETE FROM sec_pairs WHERE last_seen < ?",
                                  (_dt_to_str(now - timedelta(days=seen_days)),))
                self.conn.execute("DELETE FROM sec_volumes WHERE hour < ?",
                                  (_dt_to_str(now - timedelta(days=volume_days)),))
                # an expired suppression stays listed for 90 days, then goes
                self.conn.execute("DELETE FROM sec_suppressions WHERE expires_at IS NOT NULL AND expires_at < ?",
                                  (_dt_to_str(now - timedelta(days=90)),))
                self.conn.commit()
                return n
            except Exception:
                self._rollback_safely()
                raise

    # --- login pairs (1.29) -------------------------------------------------------

    def pair_history(self, server: str, accounts: list[str]) -> tuple[dict, dict]:
        """({(account, source): last_seen}, {account: first_seen}) for the given accounts."""
        known, first = {}, {}
        for i in range(0, len(accounts), 500):
            chunk = accounts[i:i + 500]
            marks = ",".join("?" * len(chunk))
            for r in self.conn.execute(f"SELECT account, source, first_seen, last_seen FROM sec_pairs "  # nosec B608 - placeholders only
                                       f"WHERE server = ? AND account IN ({marks})", (server, *chunk)):
                known[(r[0], r[1])] = r[3]
                if r[0] not in first or r[2] < first[r[0]]:
                    first[r[0]] = r[2]
        return known, first

    def record_pairs(self, server: str, pairs: list[tuple[str, str]], when: datetime) -> None:
        now = _dt_to_str(when)
        with self._lock:
            try:
                self.conn.executemany(
                    "INSERT INTO sec_pairs (server, account, source, first_seen, last_seen) VALUES (?, ?, ?, ?, ?) "
                    "ON CONFLICT (server, account, source) DO UPDATE SET last_seen = excluded.last_seen",
                    [(server, a, b, now, now) for a, b in pairs])
                self.conn.commit()
            except Exception:
                self._rollback_safely()
                raise

    # --- message volume history (1.30) --------------------------------------------

    def volume_history(self, server: str, field: str, keys: list[str],
                       since: datetime) -> tuple[dict, set, dict]:
        """({key: {hour: rate}}, {hours with any row for this field}, {key: first hour})
        since `since`, for the given keys."""
        lo = _dt_to_str(since)
        samples: dict[str, dict[str, float]] = {}
        first: dict[str, str] = {}
        for i in range(0, len(keys), 500):
            chunk = keys[i:i + 500]
            marks = ",".join("?" * len(chunk))
            for k, h, r in self.conn.execute(
                    f"SELECT key, hour, rate FROM sec_volumes WHERE server = ? AND field = ? "  # nosec B608 - placeholders only
                    f"AND hour >= ? AND key IN ({marks})", (server, field, lo, *chunk)):
                samples.setdefault(k, {})[h] = r
                if k not in first or h < first[k]:
                    first[k] = h
        observed = {h for (h,) in self.conn.execute(
            "SELECT DISTINCT hour FROM sec_volumes WHERE server = ? AND field = ? AND hour >= ?",
            (server, field, lo))}
        return samples, observed, first

    def record_volumes(self, server: str, rows: list[tuple[str, str, float]], hour: datetime) -> None:
        h = _dt_to_str(hour)
        with self._lock:
            try:
                self.conn.executemany(
                    "INSERT INTO sec_volumes (server, field, key, hour, rate) VALUES (?, ?, ?, ?, ?) "
                    "ON CONFLICT (server, field, key, hour) DO UPDATE SET rate = excluded.rate",
                    [(server, f, k, h, float(r)) for f, k, r in rows])
                self.conn.commit()
            except Exception:
                self._rollback_safely()
                raise

    # --- suppressions (1.31) -----------------------------------------------------

    def list_suppressions(self) -> list[dict]:
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM sec_suppressions ORDER BY id DESC")]

    def add_suppression(self, *, server: str, detector: str, entity: str, reason: str,
                        username: str, expires_at: datetime | None) -> tuple[int, bool]:
        """(id, created). The same server/detection/entity again replaces the
        reason and expiry and keeps the counters."""
        now = _dt_to_str(datetime.utcnow())
        exp = _dt_to_str(expires_at) if expires_at else None
        with self._lock:
            try:
                row = self.conn.execute("SELECT id FROM sec_suppressions WHERE server = ? AND detector = ? "
                                        "AND entity = ?", (server, detector, entity)).fetchone()
                if row:
                    self.conn.execute("UPDATE sec_suppressions SET reason = ?, expires_at = ?, created_by = ?, "
                                      "created_at = ? WHERE id = ?", (reason, exp, username, now, row[0]))
                    self.conn.commit()
                    return row[0], False
                cur = self.conn.execute(
                    "INSERT INTO sec_suppressions (server, detector, entity, reason, created_by, created_at, "
                    "expires_at) VALUES (?, ?, ?, ?, ?, ?, ?)", (server, detector, entity, reason, username, now, exp))
                self.conn.commit()
                return cur.lastrowid, True
            except Exception:
                self._rollback_safely()
                raise

    def delete_suppression(self, sid: int) -> dict | None:
        with self._lock:
            try:
                row = self.conn.execute("SELECT * FROM sec_suppressions WHERE id = ?", (sid,)).fetchone()
                if not row:
                    return None
                self.conn.execute("DELETE FROM sec_suppressions WHERE id = ?", (sid,))
                self.conn.commit()
                return dict(row)
            except Exception:
                self._rollback_safely()
                raise

    def record_suppression_hits(self, hits: dict[int, int], when: datetime) -> None:
        if not hits:
            return
        w = _dt_to_str(when)
        with self._lock:
            try:
                self.conn.executemany("UPDATE sec_suppressions SET hits = hits + ?, last_hit_at = ? WHERE id = ?",
                                      [(n, w, sid) for sid, n in hits.items()])
                self.conn.commit()
            except Exception:
                self._rollback_safely()
                raise

    # --- threat-intel lists (1.28) ------------------------------------------------

    def replace_ti_feed(self, feed: str, entries: list[str]) -> None:
        now = _dt_to_str(datetime.utcnow())
        with self._lock:
            try:
                self.conn.execute("DELETE FROM sec_ti_entries WHERE feed = ?", (feed,))
                self.conn.executemany("INSERT OR IGNORE INTO sec_ti_entries (feed, value) VALUES (?, ?)",
                                      [(feed, v) for v in entries])
                self.conn.execute(
                    "INSERT INTO sec_ti_feeds (feed, refreshed_at, count, error, tried_at) VALUES (?, ?, ?, '', ?) "
                    "ON CONFLICT (feed) DO UPDATE SET refreshed_at = excluded.refreshed_at, count = excluded.count, "
                    "error = '', tried_at = excluded.tried_at", (feed, now, len(entries), now))
                self.conn.commit()
            except Exception:
                self._rollback_safely()
                raise

    def record_ti_error(self, feed: str, error: str) -> None:
        now = _dt_to_str(datetime.utcnow())
        with self._lock:
            try:
                self.conn.execute(
                    "INSERT INTO sec_ti_feeds (feed, error, tried_at) VALUES (?, ?, ?) "
                    "ON CONFLICT (feed) DO UPDATE SET error = excluded.error, tried_at = excluded.tried_at",
                    (feed, error[:500], now))
                self.conn.commit()
            except Exception:
                self._rollback_safely()
                raise

    def ti_status(self) -> dict[str, dict]:
        return {r["feed"]: dict(r) for r in self.conn.execute("SELECT * FROM sec_ti_feeds").fetchall()}

    def ti_entries(self, feeds: list[str]) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {f: [] for f in feeds}
        if not feeds:
            return out
        marks = ",".join("?" * len(feeds))
        for r in self.conn.execute(f"SELECT feed, value FROM sec_ti_entries WHERE feed IN ({marks})", feeds):  # nosec B608 - placeholders only
            out[r[0]].append(r[1])
        return out

    # --- Sigma rules (1.27) -------------------------------------------------------

    SIGMA_FIELDS = ("title", "level", "tags", "yaml", "query", "error", "group_by", "threshold", "enabled", "sigma_id")

    @staticmethod
    def _sigma_row(r) -> dict:
        import json as _json
        d = dict(r)
        d["tags"] = _json.loads(d.get("tags") or "[]")
        d["enabled"] = bool(d["enabled"])
        return d

    def add_sigma_rule(self, data: dict, username: str) -> int:
        import json as _json
        now = _dt_to_str(datetime.utcnow())
        with self._lock:
            try:
                cur = self.conn.execute(
                    "INSERT INTO sec_sigma_rules (sigma_id, title, level, tags, yaml, query, error, group_by, threshold, "
                    "enabled, created_by, created_at, updated_at, origin) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)",
                    (data.get("sigma_id", ""), data["title"], data["level"], _json.dumps(data.get("tags") or []),
                     data["yaml"], data.get("query", ""), data.get("error", ""), data.get("group_by") or "source",
                     int(data.get("threshold") or 1), username, now, now, data.get("origin", "")))
                self.conn.commit()
                return cur.lastrowid  # type: ignore[return-value]
            except Exception:
                self._rollback_safely()
                raise

    def update_sigma_rule(self, rule_id: int, changes: dict) -> bool:
        import json as _json
        sets, args = [], []
        for k in self.SIGMA_FIELDS:
            if k in changes:
                v = changes[k]
                if k == "tags":
                    v = _json.dumps(v or [])
                elif k == "enabled":
                    v = 1 if v else 0
                sets.append(f"{k} = ?")
                args.append(v)
        if not sets:
            return bool(self.get_sigma_rule(rule_id))
        sets.append("updated_at = ?")
        args.append(_dt_to_str(datetime.utcnow()))
        with self._lock:
            try:
                cur = self.conn.execute(f"UPDATE sec_sigma_rules SET {', '.join(sets)} WHERE id = ?",  # nosec B608 - names from SIGMA_FIELDS
                                        (*args, rule_id))
                self.conn.commit()
                return cur.rowcount > 0
            except Exception:
                self._rollback_safely()
                raise

    # --- Sigma rule library (added 1.33) ---

    LIBRARY_COLS = ("sigma_id", "path", "title", "status", "level", "author", "modified", "product",
                    "category", "service", "tags", "yaml", "query", "error", "fields")

    @staticmethod
    def _library_row(r) -> dict:
        import json as _json
        d = dict(r)
        d["tags"] = _json.loads(d.get("tags") or "[]")
        d["fields"] = _json.loads(d.get("fields") or "[]")
        return d

    def replace_sigma_library(self, entries: list[dict]) -> None:
        import json as _json
        rows = [tuple(_json.dumps(e.get(c) or []) if c in ("tags", "fields") else str(e.get(c) or "")
                      for c in self.LIBRARY_COLS) for e in entries]
        with self._lock:
            try:
                self.conn.execute("DELETE FROM sec_sigma_library")
                self.conn.executemany(
                    f"INSERT OR IGNORE INTO sec_sigma_library ({', '.join(self.LIBRARY_COLS)}) "  # nosec B608 - fixed column names
                    f"VALUES ({', '.join('?' for _ in self.LIBRARY_COLS)})", rows)
                self.conn.commit()
            except Exception:
                self._rollback_safely()
                raise

    def update_sigma_library_conversions(self, rows: list[tuple[str, str, str]]) -> None:
        """(query, error, fields_json, sigma_id) after the field map changed."""
        with self._lock:
            try:
                self.conn.executemany("UPDATE sec_sigma_library SET query = ?, error = ?, fields = ? WHERE sigma_id = ?", rows)
                self.conn.commit()
            except Exception:
                self._rollback_safely()
                raise

    def list_sigma_library(self, with_yaml: bool = False) -> list[dict]:
        cols = self.LIBRARY_COLS if with_yaml else tuple(c for c in self.LIBRARY_COLS if c != "yaml")
        return [self._library_row(r) for r in self.conn.execute(
            f"SELECT {', '.join(cols)} FROM sec_sigma_library ORDER BY title").fetchall()]  # nosec B608 - fixed column names

    def get_sigma_library_entry(self, sigma_id: str) -> dict | None:
        r = self.conn.execute("SELECT * FROM sec_sigma_library WHERE sigma_id = ?", (sigma_id,)).fetchone()
        return self._library_row(r) if r else None

    def sigma_library_meta(self) -> dict[str, str]:
        return {r["k"]: r["v"] for r in self.conn.execute("SELECT k, v FROM sec_sigma_library_meta").fetchall()}

    def set_sigma_library_meta(self, values: dict[str, str]) -> None:
        with self._lock:
            try:
                self.conn.executemany(
                    "INSERT INTO sec_sigma_library_meta (k, v) VALUES (?, ?) ON CONFLICT (k) DO UPDATE SET v = excluded.v",
                    [(k, str(v)) for k, v in values.items()])
                self.conn.commit()
            except Exception:
                self._rollback_safely()
                raise

    def record_sigma_result(self, rule_id: int, count: int | None, error: str) -> None:
        with self._lock:
            try:
                self.conn.execute("UPDATE sec_sigma_rules SET last_run_at = ?, last_count = ?, last_error = ? WHERE id = ?",
                                  (_dt_to_str(datetime.utcnow()), count, error[:500], rule_id))
                self.conn.commit()
            except Exception:
                self._rollback_safely()
                raise

    def get_sigma_rule(self, rule_id: int) -> dict | None:
        r = self.conn.execute("SELECT * FROM sec_sigma_rules WHERE id = ?", (rule_id,)).fetchone()
        return self._sigma_row(r) if r else None

    def list_sigma_rules(self, enabled_only: bool = False) -> list[dict]:
        w = " WHERE enabled = 1 AND query != ''" if enabled_only else ""
        return [self._sigma_row(r) for r in self.conn.execute(
            f"SELECT * FROM sec_sigma_rules{w} ORDER BY enabled DESC, id").fetchall()]  # nosec B608 - fixed fragment

    def delete_sigma_rule(self, rule_id: int) -> dict | None:
        with self._lock:
            try:
                r = self.conn.execute("SELECT * FROM sec_sigma_rules WHERE id = ?", (rule_id,)).fetchone()
                if not r:
                    return None
                self.conn.execute("DELETE FROM sec_sigma_rules WHERE id = ?", (rule_id,))
                self.conn.commit()
                return self._sigma_row(r)
            except Exception:
                self._rollback_safely()
                raise

    # --- assets (1.25) ----------------------------------------------------------

    def list_security_assets(self) -> list[dict]:
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM sec_assets ORDER BY CASE criticality WHEN 'critical' THEN 0 WHEN 'high' THEN 1 "
            "WHEN 'medium' THEN 2 ELSE 3 END, kind, value").fetchall()]

    def upsert_security_asset(self, kind: str, value: str, name: str, criticality: str, owner: str,
                              notes: str, asset_id: int | None = None) -> int | None:
        """Insert, or update by id / by (kind, value). None = id not found."""
        now = _dt_to_str(datetime.utcnow())
        with self._lock:
            try:
                if asset_id:
                    cur = self.conn.execute(
                        "UPDATE sec_assets SET kind = ?, value = ?, name = ?, criticality = ?, owner = ?, notes = ?, "
                        "updated_at = ? WHERE id = ?", (kind, value, name, criticality, owner, notes, now, asset_id))
                    self.conn.commit()
                    return asset_id if cur.rowcount else None
                self.conn.execute(
                    "INSERT INTO sec_assets (kind, value, name, criticality, owner, notes, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT (kind, value) DO UPDATE SET name = excluded.name, "
                    "criticality = excluded.criticality, owner = excluded.owner, notes = excluded.notes, "
                    "updated_at = excluded.updated_at", (kind, value, name, criticality, owner, notes, now, now))
                rid = self.conn.execute("SELECT id FROM sec_assets WHERE kind = ? AND value = ?",
                                        (kind, value)).fetchone()[0]
                self.conn.commit()
                return rid
            except Exception:
                self._rollback_safely()
                raise

    def delete_security_asset(self, asset_id: int) -> dict | None:
        with self._lock:
            try:
                row = self.conn.execute("SELECT * FROM sec_assets WHERE id = ?", (asset_id,)).fetchone()
                if not row:
                    return None
                self.conn.execute("DELETE FROM sec_assets WHERE id = ?", (asset_id,))
                self.conn.commit()
                return dict(row)
            except Exception:
                self._rollback_safely()
                raise

    def open_security_counts(self) -> dict[str, int]:
        rows = self.conn.execute("SELECT severity, COUNT(*) FROM sec_incidents WHERE status = 'open' GROUP BY severity")
        return {r[0]: r[1] for r in rows}

    def security_incidents_since(self, since: datetime, limit: int = 5000) -> list[dict]:
        import json as _json
        rows = self.conn.execute("SELECT * FROM sec_incidents WHERE last_seen >= ? ORDER BY last_seen DESC LIMIT ?",
                                 (_dt_to_str(since), limit)).fetchall()
        return [{**dict(r), "metrics": _json.loads(r["metrics"] or "{}")} for r in rows]

    # --- investigations / cases (1.24) ----------------------------------------

    CASE_STATUSES = ("open", "in_progress", "closed")
    CASE_FIELDS = ("title", "status", "severity", "assignee", "description", "resolution")

    def _case_event(self, case_id: int, username: str, kind: str, body: str, now: str) -> None:
        """Caller holds the lock and commits."""
        self.conn.execute("INSERT INTO sec_case_notes (case_id, created_at, username, kind, body) "
                          "VALUES (?, ?, ?, ?, ?)", (case_id, now, username, kind, body[:4000]))

    def create_security_case(self, title: str, severity: str, description: str, username: str,
                             incident_ids: list[int] | None = None) -> int:
        now = _dt_to_str(datetime.utcnow())
        with self._lock:
            try:
                cur = self.conn.execute(
                    "INSERT INTO sec_cases (title, severity, description, created_by, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)", (title[:200], severity, description[:8000], username, now, now))
                cid = cur.lastrowid
                self._case_event(cid, username, "created", title[:200], now)
                for iid in dict.fromkeys(int(i) for i in (incident_ids or [])):
                    if self.conn.execute("SELECT 1 FROM sec_incidents WHERE id = ?", (iid,)).fetchone():
                        self.conn.execute("INSERT OR IGNORE INTO sec_case_incidents (case_id, incident_id, added_by, "
                                          "added_at) VALUES (?, ?, ?, ?)", (cid, iid, username, now))
                        self._case_event(cid, username, "incident_added", str(iid), now)
                self.conn.commit()
                return cid  # type: ignore[return-value]
            except Exception:
                self._rollback_safely()
                raise

    def update_security_case(self, case_id: int, changes: dict, username: str) -> list[str] | None:
        """Applies whitelisted fields; returns the names that changed (None = no such case)."""
        now = _dt_to_str(datetime.utcnow())
        with self._lock:
            try:
                row = self.conn.execute("SELECT * FROM sec_cases WHERE id = ?", (case_id,)).fetchone()
                if not row:
                    return None
                changed = []
                for k in self.CASE_FIELDS:
                    if k in changes and str(changes[k]) != str(row[k]):
                        self.conn.execute(f"UPDATE sec_cases SET {k} = ? WHERE id = ?",  # nosec B608 - k from CASE_FIELDS
                                          (changes[k], case_id))
                        changed.append(k)
                        long = k in ("description", "resolution")
                        self._case_event(case_id, username, f"{k}_changed",
                                         "" if long else f"{row[k]} -> {changes[k]}", now)
                if "status" in changed:
                    self.conn.execute("UPDATE sec_cases SET closed_at = ? WHERE id = ?",
                                      (now if changes["status"] == "closed" else None, case_id))
                if changed:
                    self.conn.execute("UPDATE sec_cases SET updated_at = ? WHERE id = ?", (now, case_id))
                self.conn.commit()
                return changed
            except Exception:
                self._rollback_safely()
                raise

    def add_security_case_note(self, case_id: int, body: str, username: str) -> int | None:
        now = _dt_to_str(datetime.utcnow())
        with self._lock:
            try:
                if not self.conn.execute("SELECT 1 FROM sec_cases WHERE id = ?", (case_id,)).fetchone():
                    return None
                cur = self.conn.execute("INSERT INTO sec_case_notes (case_id, created_at, username, kind, body) "
                                        "VALUES (?, ?, ?, 'note', ?)", (case_id, now, username, body[:8000]))
                self.conn.execute("UPDATE sec_cases SET updated_at = ? WHERE id = ?", (now, case_id))
                self.conn.commit()
                return cur.lastrowid
            except Exception:
                self._rollback_safely()
                raise

    def link_security_case_incidents(self, case_id: int, incident_ids: list[int], username: str,
                                     remove: bool = False) -> list[int] | None:
        """Adds (or removes) incidents; returns the ids actually changed."""
        now = _dt_to_str(datetime.utcnow())
        with self._lock:
            try:
                if not self.conn.execute("SELECT 1 FROM sec_cases WHERE id = ?", (case_id,)).fetchone():
                    return None
                done = []
                for iid in dict.fromkeys(int(i) for i in incident_ids):
                    if remove:
                        cur = self.conn.execute("DELETE FROM sec_case_incidents WHERE case_id = ? AND incident_id = ?",
                                                (case_id, iid))
                    elif self.conn.execute("SELECT 1 FROM sec_incidents WHERE id = ?", (iid,)).fetchone():
                        cur = self.conn.execute("INSERT OR IGNORE INTO sec_case_incidents (case_id, incident_id, "
                                                "added_by, added_at) VALUES (?, ?, ?, ?)", (case_id, iid, username, now))
                    else:
                        continue
                    if cur.rowcount:
                        done.append(iid)
                        self._case_event(case_id, username, "incident_removed" if remove else "incident_added",
                                         str(iid), now)
                if done:
                    self.conn.execute("UPDATE sec_cases SET updated_at = ? WHERE id = ?", (now, case_id))
                self.conn.commit()
                return done
            except Exception:
                self._rollback_safely()
                raise

    def list_security_cases(self, status: str | None = None, limit: int = 200) -> list[dict]:
        w, args = ("WHERE c.status = ?", [status]) if status else ("", [])
        rows = self.conn.execute(
            f"""SELECT c.*, (SELECT COUNT(*) FROM sec_case_incidents ci WHERE ci.case_id = c.id) AS incidents,
                       (SELECT COUNT(*) FROM sec_case_notes n WHERE n.case_id = c.id AND n.kind = 'note') AS notes
                FROM sec_cases c {w} ORDER BY (c.status = 'closed'), c.updated_at DESC, c.id DESC LIMIT ?""",  # nosec B608 - fixed fragment, bound values
            [*args, limit]).fetchall()
        return [dict(r) for r in rows]

    def get_security_case(self, case_id: int) -> dict | None:
        import json as _json
        r = self.conn.execute("SELECT * FROM sec_cases WHERE id = ?", (case_id,)).fetchone()
        if not r:
            return None
        d = dict(r)
        incs = self.conn.execute(
            """SELECT i.*, ci.added_by, ci.added_at FROM sec_case_incidents ci
               JOIN sec_incidents i ON i.id = ci.incident_id WHERE ci.case_id = ? ORDER BY i.last_seen DESC""",
            (case_id,)).fetchall()
        d["incidents"] = [{**dict(x), "metrics": _json.loads(x["metrics"] or "{}")} for x in incs]
        d["timeline"] = [dict(x) for x in self.conn.execute(
            "SELECT id, created_at, username, kind, body FROM sec_case_notes WHERE case_id = ? ORDER BY id",
            (case_id,)).fetchall()]
        return d

    def cases_for_incidents(self, incident_ids: list[int]) -> dict[int, list[dict]]:
        ids = [int(i) for i in incident_ids][:1000]
        if not ids:
            return {}
        marks = ",".join("?" * len(ids))
        rows = self.conn.execute(
            f"""SELECT ci.incident_id, c.id, c.title, c.status FROM sec_case_incidents ci
                JOIN sec_cases c ON c.id = ci.case_id WHERE ci.incident_id IN ({marks})""", ids).fetchall()  # nosec B608 - placeholders only
        out: dict[int, list[dict]] = {}
        for r in rows:
            out.setdefault(r["incident_id"], []).append({"id": r["id"], "title": r["title"], "status": r["status"]})
        return out

    # --- AI analysis of incidents (1.22) --------------------------------------

    def add_security_analysis(self, row: dict) -> int:
        import json as _json
        with self._lock:
            try:
                cur = self.conn.execute(
                    """INSERT INTO sec_ai_analyses (incident_id, created_at, trigger, username, lang, model,
                       verdict, confidence, result, evidence, unverified, tokens, elapsed_ms, error)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (int(row["incident_id"]), _dt_to_str(datetime.utcnow()), row.get("trigger") or "manual",
                     row.get("username") or "", row.get("lang") or "en", row.get("model") or "",
                     row.get("verdict"), row.get("confidence"),
                     _json.dumps(row["result"], ensure_ascii=False) if row.get("result") is not None else None,
                     _json.dumps(row["evidence"], ensure_ascii=False, default=str) if row.get("evidence") is not None else None,
                     _json.dumps(row.get("unverified") or []), int(row.get("tokens") or 0),
                     int(row.get("elapsed_ms") or 0), row.get("error") or ""))
                self.conn.commit()
                return cur.lastrowid  # type: ignore[return-value]
            except Exception:
                self._rollback_safely()
                raise

    @staticmethod
    def _analysis_row(r) -> dict:
        import json as _json
        d = dict(r)
        for k, empty in (("result", None), ("evidence", None), ("unverified", [])):
            d[k] = _json.loads(d[k]) if d.get(k) else empty
        return d

    def get_security_analysis(self, analysis_id: int) -> dict | None:
        r = self.conn.execute("SELECT * FROM sec_ai_analyses WHERE id = ?", (analysis_id,)).fetchone()
        return self._analysis_row(r) if r else None

    def list_security_analyses(self, incident_id: int, limit: int = 10) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM sec_ai_analyses WHERE incident_id = ? ORDER BY id DESC LIMIT ?",
            (incident_id, limit)).fetchall()
        return [self._analysis_row(r) for r in rows]

    def latest_security_verdicts(self, incident_ids: list[int]) -> dict[int, dict]:
        """{incident_id: {verdict, confidence, created_at}} of the newest successful analysis."""
        ids = [int(i) for i in incident_ids][:1000]
        if not ids:
            return {}
        marks = ",".join("?" * len(ids))
        rows = self.conn.execute(
            f"""SELECT incident_id, verdict, confidence, created_at FROM sec_ai_analyses
                WHERE id IN (SELECT MAX(id) FROM sec_ai_analyses
                             WHERE incident_id IN ({marks}) AND verdict IS NOT NULL
                             GROUP BY incident_id)""", ids).fetchall()  # nosec B608 - placeholders only, bound values
        return {r["incident_id"]: {"verdict": r["verdict"], "confidence": r["confidence"],
                                   "created_at": r["created_at"]} for r in rows}

    def security_entity_history(self, server: str, detector: str, entity: str, exclude_id: int) -> dict:
        rows = self.conn.execute(
            """SELECT id, detector, severity, status, first_seen, last_seen FROM sec_incidents
               WHERE entity = ? AND id != ? ORDER BY last_seen DESC LIMIT 10""",
            (entity, exclude_id)).fetchall()
        seen = self.conn.execute(
            "SELECT first_seen FROM sec_seen WHERE server = ? AND detector = ? AND entity = ?",
            (server, detector, entity)).fetchone()
        return {"first_seen_by_this_detector": seen[0] if seen else None,
                "other_incidents_for_this_entity": [dict(r) for r in rows]}

    # --- AI chat ------------------------------------------------------------

    def ai_create_conversation(self, username: str, server: str, title: str) -> int:
        now = _dt_to_str(datetime.utcnow())
        with self._lock:
            try:
                cur = self.conn.execute(
                    "INSERT INTO ai_conversations (username, server, title, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?)", (username, server, title[:200], now, now))
                self.conn.commit()
                return cur.lastrowid  # type: ignore[return-value]
            except Exception:
                self._rollback_safely()
                raise

    def ai_add_message(self, conversation_id: int, role: str, content: str, *, model: str = "",
                       tools: list | None = None, tokens: int = 0, elapsed_ms: int = 0,
                       truncated: bool = False, calls: list | None = None,
                       followups: list | None = None, llm: str = "") -> int:
        import json as _json
        now = _dt_to_str(datetime.utcnow())
        with self._lock:
            try:
                cur = self.conn.execute(
                    "INSERT INTO ai_messages (conversation_id, role, content, model, tools, tokens, "
                    "elapsed_ms, created_at, truncated, calls, followups, llm) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (conversation_id, role, content, model, _json.dumps(tools or []), int(tokens),
                     int(elapsed_ms), now, 1 if truncated else 0,
                     _json.dumps(calls or [], ensure_ascii=False, default=str),
                     _json.dumps([str(q) for q in (followups or [])], ensure_ascii=False), str(llm or "")))
                self.conn.execute("UPDATE ai_conversations SET updated_at = ? WHERE id = ?",
                                  (now, conversation_id))
                self.conn.commit()
                return cur.lastrowid  # type: ignore[return-value]
            except Exception:
                self._rollback_safely()
                raise

    def ai_get_conversation(self, conversation_id: int, username: str) -> dict | None:
        """Only the owner's: another user's id reads as not found."""
        import json as _json
        r = self.conn.execute("SELECT * FROM ai_conversations WHERE id = ? AND username = ?",
                              (conversation_id, username)).fetchone()
        if not r:
            return None
        d = dict(r)
        msgs = self.conn.execute(
            "SELECT id, role, content, model, tools, tokens, elapsed_ms, created_at, truncated, calls, "
            "followups, llm, stopped_at FROM ai_messages WHERE conversation_id = ? ORDER BY id",
            (conversation_id,)).fetchall()
        d["messages"] = [{**dict(m), "tools": _json.loads(m["tools"] or "[]"),
                          "calls": _json.loads(m["calls"] or "[]"),
                          "followups": _json.loads(m["followups"] or "[]")} for m in msgs]
        return d

    def ai_mark_stopped(self, message_id: int) -> None:
        """The user stopped this question before an answer came (shown as stopped)."""
        with self._lock:
            try:
                self.conn.execute("UPDATE ai_messages SET stopped_at = ? WHERE id = ? AND role = 'user'",
                                  (_dt_to_str(datetime.utcnow()), int(message_id)))
                self.conn.commit()
            except Exception:
                self._rollback_safely()
                raise

    def ai_get_message(self, message_id: int, username: str) -> dict | None:
        """One message, only when its conversation is the user's."""
        r = self.conn.execute(
            "SELECT m.id, m.role, m.content, m.conversation_id FROM ai_messages m "
            "JOIN ai_conversations c ON c.id = m.conversation_id WHERE m.id = ? AND c.username = ?",
            (message_id, username)).fetchone()
        return dict(r) if r else None

    def ai_list_conversations(self, username: str, limit: int = 50, q: str = "") -> list[dict]:
        """Newest first. `q` matches the title or any message, case-insensitive
        for ASCII (SQLite LIKE); % and _ in it are literal."""
        sql = ("SELECT id, server, title, created_at, updated_at, pinned_at FROM ai_conversations c "
               "WHERE username = ?")
        params: list = [username]
        q = (q or "").strip()[:200]
        if q:
            like = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            sql += (" AND (title LIKE ? ESCAPE '\\' OR EXISTS (SELECT 1 FROM ai_messages m "
                    "WHERE m.conversation_id = c.id AND m.content LIKE ? ESCAPE '\\'))")
            params += [like, like]
        # pinned first (newest pin on top), then the rest newest first; a pinned one is
        # listed even when it is older than the newest `limit`
        rows = self.conn.execute(sql + " ORDER BY (pinned_at IS NULL), pinned_at DESC, updated_at DESC, id DESC "
                                 "LIMIT ?", (*params, limit + AI_MAX_PINNED)).fetchall()
        out = [dict(r) for r in rows]
        pinned = [r for r in out if r.get("pinned_at")]
        return pinned + [r for r in out if not r.get("pinned_at")][:limit]

    def ai_pin_conversation(self, conversation_id: int, username: str, pinned: bool) -> str:
        """'ok', 'not_found' or 'full' (already AI_MAX_PINNED pinned)."""
        now = _dt_to_str(datetime.utcnow())
        with self._lock:
            try:
                row = self.conn.execute("SELECT pinned_at FROM ai_conversations WHERE id = ? AND username = ?",
                                        (conversation_id, username)).fetchone()
                if not row:
                    return "not_found"
                if pinned and not row[0]:
                    n = self.conn.execute("SELECT COUNT(*) FROM ai_conversations WHERE username = ? "
                                          "AND pinned_at IS NOT NULL", (username,)).fetchone()[0]
                    if n >= AI_MAX_PINNED:
                        return "full"
                if bool(row[0]) != pinned:
                    self.conn.execute("UPDATE ai_conversations SET pinned_at = ? WHERE id = ? AND username = ?",
                                      (now if pinned else None, conversation_id, username))
                    self.conn.commit()
                return "ok"
            except Exception:
                self._rollback_safely()
                raise

    def ai_rename_conversation(self, conversation_id: int, username: str, title: str) -> bool:
        with self._lock:
            try:
                cur = self.conn.execute("UPDATE ai_conversations SET title = ? WHERE id = ? AND username = ?",
                                        (title[:200], conversation_id, username))
                self.conn.commit()
                return cur.rowcount > 0
            except Exception:
                self._rollback_safely()
                raise

    def ai_delete_conversation(self, conversation_id: int, username: str) -> bool:
        with self._lock:
            try:
                cur = self.conn.execute("DELETE FROM ai_conversations WHERE id = ? AND username = ?",
                                        (conversation_id, username))
                if cur.rowcount:
                    self.conn.execute("DELETE FROM ai_messages WHERE conversation_id = ?",
                                      (conversation_id,))
                self.conn.commit()
                return cur.rowcount > 0
            except Exception:
                self._rollback_safely()
                raise

    def ai_prune(self, days: int) -> int:
        if days <= 0:
            return 0
        cutoff = _dt_to_str(datetime.utcnow() - timedelta(days=days))
        with self._lock:
            try:
                # a pinned conversation is kept: the user marked it as one to keep
                ids = [r[0] for r in self.conn.execute(
                    "SELECT id FROM ai_conversations WHERE updated_at < ? AND pinned_at IS NULL",
                    (cutoff,)).fetchall()]
                for i in ids:
                    self.conn.execute("DELETE FROM ai_messages WHERE conversation_id = ?", (i,))
                    self.conn.execute("DELETE FROM ai_conversations WHERE id = ?", (i,))
                self.conn.commit()
                return len(ids)
            except Exception:
                self._rollback_safely()
                raise

    def ai_add_usage(self, tokens: int, when: datetime | None = None, *, llm: str = "",
                     username: str = "") -> None:
        day = (when or datetime.utcnow()).strftime("%Y-%m-%d")
        with self._lock:
            try:
                self.conn.execute(
                    "INSERT INTO ai_usage (day, tokens, calls) VALUES (?, ?, 1) ON CONFLICT (day) "
                    "DO UPDATE SET tokens = tokens + excluded.tokens, calls = calls + 1", (day, int(tokens)))
                self.conn.execute(
                    "INSERT INTO ai_usage_detail (day, llm, username, tokens, calls) VALUES (?, ?, ?, ?, 1) "
                    "ON CONFLICT (day, llm, username) DO UPDATE SET tokens = tokens + excluded.tokens, "
                    "calls = calls + 1", (day, str(llm or ""), str(username or ""), int(tokens)))
                self.conn.commit()
            except Exception:
                self._rollback_safely()
                raise

    def ai_usage(self, when: datetime | None = None, *, llm: str | None = None,
                 username: str | None = None) -> dict:
        """Tokens today and this month (UTC): the site total, or one LLM server's /
        one user's (counted from 1.36 on) when `llm` / `username` is given."""
        now = when or datetime.utcnow()
        day = now.strftime("%Y-%m-%d")
        month = now.strftime("%Y-%m")
        if llm is None and username is None:
            d = self.conn.execute("SELECT COALESCE(SUM(tokens), 0) FROM ai_usage WHERE day = ?", (day,)).fetchone()[0]
            m = self.conn.execute("SELECT COALESCE(SUM(tokens), 0) FROM ai_usage WHERE day LIKE ?",
                                  (month + "-%",)).fetchone()[0]
            return {"day": int(d), "month": int(m)}
        cond, args = [], []
        if llm is not None:
            cond.append("llm = ?")
            args.append(llm)
        if username is not None:
            cond.append("username = ?")
            args.append(username)
        where = " AND ".join(cond)
        d = self.conn.execute(f"SELECT COALESCE(SUM(tokens), 0) FROM ai_usage_detail WHERE day = ? AND {where}",  # nosec B608 - fixed column names, bound values
                              (day, *args)).fetchone()[0]
        m = self.conn.execute(f"SELECT COALESCE(SUM(tokens), 0) FROM ai_usage_detail WHERE day LIKE ? AND {where}",  # nosec B608 - fixed column names, bound values
                              (month + "-%", *args)).fetchone()[0]
        return {"day": int(d), "month": int(m)}

    def list_report_history(self, limit: int = 50) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM report_history ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_report_history_entry(self, hist_id: int) -> dict | None:
        r = self.conn.execute("SELECT * FROM report_history WHERE id = ?", (hist_id,)).fetchone()
        return dict(r) if r else None

    def prune_report_history(self, days: int = 180) -> list[str]:
        """Delete report_history rows older than `days` and return the file paths
        that were removed (so the caller can unlink the PDFs + sidecars)."""
        cutoff = _dt_to_str(datetime.utcnow() - timedelta(days=days))
        with self._lock:
            try:
                rows = self.conn.execute(
                    "SELECT file_path FROM report_history WHERE created_at < ?", (cutoff,)
                ).fetchall()
                paths = [r["file_path"] for r in rows if r["file_path"]]
                self.conn.execute("DELETE FROM report_history WHERE created_at < ?", (cutoff,))
                self.conn.commit()
                return paths
            except Exception:
                self._rollback_safely()
                raise

    def update_schedule_last_run(
        self, name: str, when: datetime | None = None
    ) -> None:
        """Update schedules.last_run_at for the named schedule.

        Locked because callers used to do `db.conn.execute(UPDATE ...); db.conn.commit()`
        directly. With long-running exports calling self.update_job() every batch
        from a worker thread, and other unlocked writers from the asyncio loop,
        the shared sqlite3.Connection's transaction-state tracker raced and
        Python auto-issued BEGIN while a tx was already open, yielding
        OperationalError("cannot start a transaction within a transaction") —
        which then aborted a whole index in the OpenSearch exporter.
        """
        when = when or datetime.utcnow()
        with self._lock:
            try:
                self.conn.execute(
                    "UPDATE schedules SET last_run_at = ? WHERE name = ?",
                    (_dt_to_str(when), name),
                )
                self.conn.commit()
            except Exception:
                self._rollback_safely()
                raise

    def recover_stuck_importing(self) -> int:
        """Flip any archive stuck in IMPORTING back to COMPLETED. Called at
        service startup: an archive flips to IMPORTING while an import reads it,
        and the importer's finally block flips it back — but if the process was
        killed (-9 / OOM / crash / a restart mid-import, e.g. during an upgrade),
        the row stays IMPORTING and the per-archive lock makes it un-importable
        forever. On startup no import can be running, so any IMPORTING row is
        stale. Returns the number of rows recovered.
        """
        with self._lock:
            try:
                n = self.conn.execute(
                    "UPDATE archives SET status = 'completed' WHERE status = 'importing'"
                ).rowcount
                self.conn.commit()
                if n:
                    import logging
                    logging.getLogger("glogarch.db").warning(
                        "Recovered %d archive(s) stuck in IMPORTING state on startup", n
                    )
                return n
            except Exception:
                self._rollback_safely()
                raise

    def cleanup_stale_running_jobs(self) -> int:
        """Mark all jobs.status='running' as failed. Called at service startup —
        any 'running' rows are from a previous process that died (restart, OOM,
        crash), so they can never finish. Returns the number of rows updated.
        """
        now = _dt_to_str(datetime.utcnow())
        with self._lock:
            try:
                rows = self.conn.execute(
                    "SELECT id, messages_done, messages_total FROM jobs WHERE status='running'"
                ).fetchall()
                for row in rows:
                    job_id, done, total = row[0], row[1] or 0, row[2] or 0
                    if done > 0:
                        msg = (f"Interrupted by service restart "
                               f"({done:,} / {total:,} processed, partial files cleaned up)")
                    else:
                        msg = "Interrupted by service restart"
                    self.conn.execute(
                        "UPDATE jobs SET status='failed', error_message=?, completed_at=? WHERE id=?",
                        (msg, now, job_id),
                    )
                self.conn.commit()
                return len(rows)
            except Exception:
                self._rollback_safely()
                raise

    # --- Import History ---

    def record_import(self, record: ImportHistoryRecord) -> int:
        with self._lock:
            try:
                cur = self.conn.execute(
                    """INSERT INTO import_history (archive_id, target_server, messages_sent, imported_at, job_id)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        record.archive_id,
                        record.target_server,
                        record.messages_sent,
                        _dt_to_str(record.imported_at),
                        record.job_id,
                    ),
                )
                self.conn.commit()
                return cur.lastrowid  # type: ignore[return-value]
            except Exception:
                self._rollback_safely()
                raise

    # --- Audit Log ---

    def audit(self, action: str, detail: str = "", username: str = "", ip_address: str = "") -> None:
        """Record an audit log entry."""
        from glogarch.utils.sanitize import sanitize
        with self._lock:
            try:
                self.conn.execute(
                    "INSERT INTO audit_log (timestamp, username, action, detail, ip_address) VALUES (?, ?, ?, ?, ?)",
                    (_dt_to_str(datetime.utcnow()), username, action, (sanitize(detail) or "")[:500], ip_address),
                )
                self.conn.commit()
            except Exception:
                self._rollback_safely()
                raise

    def list_audit(self, limit: int = 200) -> list[dict]:
        """Get recent audit log entries."""
        rows = self.conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def query_audit(self, username: str | None = None, action: str | None = None,
                    time_from: str | None = None, time_to: str | None = None,
                    limit: int = 100, offset: int = 0) -> tuple[list[dict], int]:
        """Filtered, paged view of jt-glogarch's OWN operation log.

        Separate from `api_audit`, which records what happened on Graylog via
        the nginx syslog feed. This table answers "who did what in THIS tool" —
        who deleted archives, changed settings, ran a search. It was written
        from day one and had no interface at all, so the only way to read it
        was to open the database by hand.
        """
        where, params = [], []
        if username:
            where.append("username LIKE ?")
            params.append(f"%{username}%")
        if action:
            where.append("action LIKE ?")
            params.append(f"%{action}%")
        if time_from:
            where.append("timestamp >= ?")
            params.append(time_from)
        if time_to:
            where.append("timestamp <= ?")
            params.append(time_to)
        w = (" WHERE " + " AND ".join(where)) if where else ""
        total = self.conn.execute(
            f"SELECT COUNT(*) FROM audit_log{w}", params  # nosec B608 - fixed literal fragments; values bound
        ).fetchone()[0]
        rows = self.conn.execute(
            f"SELECT * FROM audit_log{w} ORDER BY id DESC LIMIT ? OFFSET ?",  # nosec B608 - same
            params + [max(1, min(int(limit), 500)), max(0, int(offset))],
        ).fetchall()
        return [dict(r) for r in rows], total

    def distinct_audit_actions(self) -> list[str]:
        """Action names actually present, for the filter dropdown."""
        return [r[0] for r in self.conn.execute(
            "SELECT DISTINCT action FROM audit_log ORDER BY action") if r[0]]

    # --- API Audit ---

    def backfill_audit_usernames(
        self,
        ip_user_pairs: list[tuple[str, str]],
        default_user: str = "",
    ) -> int:
        """Fill in missing api_audit.username values.

        Strategy:
          1. For each (ip, user) pair, set username=user where remote_addr=ip
             and username is currently blank ('' or '-').
          2. Then, if default_user is non-empty, fill any remaining blanks.
        Returns total rows updated.

        Locked because the audit listener runs this periodically from the
        asyncio event-loop thread, while exporters/importers run in worker
        threads and write via update_job() every batch. Bypassing _lock here
        produced a race on the shared sqlite3.Connection's transaction-state
        tracker that surfaced as
        OperationalError("cannot start a transaction within a transaction")
        on a random concurrent write — causing one OpenSearch export index
        to be skipped in a long-running scheduled run.
        """
        if not ip_user_pairs and not default_user:
            return 0
        total = 0
        with self._lock:
            try:
                for ip, user in ip_user_pairs:
                    if not ip or not user:
                        continue
                    cnt = self.conn.execute(
                        "UPDATE api_audit SET username = ? "
                        "WHERE remote_addr = ? AND (username = '' OR username = '-')",
                        (user, ip),
                    ).rowcount
                    total += cnt
                if default_user:
                    cnt = self.conn.execute(
                        "UPDATE api_audit SET username = ? "
                        "WHERE username = '' OR username = '-'",
                        (default_user,),
                    ).rowcount
                    total += cnt
                if total:
                    self.conn.commit()
                return total
            except Exception:
                self._rollback_safely()
                raise

    def insert_api_audit_batch(self, entries: list[dict]) -> int:
        """Batch insert parsed API audit entries."""
        if not entries:
            return 0
        with self._lock:
            try:
                self.conn.executemany(
                    """INSERT INTO api_audit
                       (server_name, timestamp, remote_addr, username, method, uri,
                        query_string, status_code, request_body, user_agent,
                        request_time_ms, operation, is_sensitive, target_name, created_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    [
                        (
                            e.get("server_name", ""),
                            e.get("timestamp", ""),
                            e.get("remote_addr", ""),
                            e.get("username", ""),
                            e.get("method", ""),
                            e.get("uri", ""),
                            e.get("query_string", ""),
                            e.get("status_code", 0),
                            e.get("request_body"),
                            e.get("user_agent", ""),
                            e.get("request_time_ms", 0.0),
                            e.get("operation", ""),
                            1 if e.get("is_sensitive") else 0,
                            e.get("target_name", ""),
                            _dt_to_str(datetime.utcnow()),
                        )
                        for e in entries
                    ],
                )
                self.conn.commit()
                return len(entries)
            except Exception:
                self._rollback_safely()
                raise

    def list_api_audit(
        self, limit: int = 100, offset: int = 0,
        username: str = "", method: str = "", uri: str = "",
        status_code: str = "", sensitive_only: bool = False,
        time_from: str = "", time_to: str = "",
    ) -> tuple[list[dict], int]:
        """Paginated API audit listing with filters. Returns (items, total)."""
        where = ["1=1"]
        params: list = []
        if username:
            where.append("username LIKE ?")
            params.append(f"%{username}%")
        if method:
            where.append("method = ?")
            params.append(method)
        if uri:
            where.append("uri LIKE ?")
            params.append(f"%{uri}%")
        if status_code:
            if status_code.endswith("xx"):
                base = int(status_code[0]) * 100
                where.append("status_code >= ? AND status_code < ?")
                params.extend([base, base + 100])
            else:
                where.append("status_code = ?")
                params.append(int(status_code))
        if sensitive_only:
            where.append("is_sensitive = 1")
        if time_from:
            where.append("timestamp >= ?")
            params.append(time_from)
        if time_to:
            where.append("timestamp <= ?")
            params.append(time_to)

        w = " AND ".join(where)
        total = self.conn.execute(f"SELECT COUNT(*) FROM api_audit WHERE {w}", params).fetchone()[0]  # nosec B608 - w joins fixed literal fragments; every user value is bound in params
        rows = self.conn.execute(
            f"SELECT * FROM api_audit WHERE {w} ORDER BY id DESC LIMIT ? OFFSET ?",  # nosec B608 - w joins fixed literal fragments; every user value is bound in params
            params + [limit, offset],
        ).fetchall()
        return [dict(r) for r in rows], total

    def get_api_audit_entry(self, entry_id: int) -> dict | None:
        row = self.conn.execute("SELECT * FROM api_audit WHERE id = ?", (entry_id,)).fetchone()
        return dict(row) if row else None

    def get_api_audit_stats(self, hours: int = 24) -> dict:
        if hours > 0:
            cutoff = _dt_to_str(datetime.utcnow() - timedelta(hours=hours))
            where, params = "WHERE timestamp >= ?", (cutoff,)
        else:
            where, params = "", ()
        total = self.conn.execute(
            f"SELECT COUNT(*) FROM api_audit {where}", params  # nosec B608 - where is one of two fixed literals; cutoff bound in params
        ).fetchone()[0]
        users = self.conn.execute(
            f"SELECT COUNT(DISTINCT username) FROM api_audit {where}", params  # nosec B608 - where is one of two fixed literals; cutoff bound in params
        ).fetchone()[0]
        login_failures = self.conn.execute(
            f"SELECT COUNT(*) FROM api_audit {where + (' AND' if where else 'WHERE')} operation = 'auth.login' AND status_code >= 400", params  # nosec B608 - where is one of two fixed literals; cutoff bound in params
        ).fetchone()[0]
        sensitive = self.conn.execute(
            f"SELECT COUNT(*) FROM api_audit {where + (' AND' if where else 'WHERE')} is_sensitive = 1", params  # nosec B608 - where is one of two fixed literals; cutoff bound in params
        ).fetchone()[0]
        # Hourly sparkline data (last 24 hours)
        sparkline = {"ops": [], "login_failures": [], "sensitive": []}
        try:
            now = datetime.utcnow()
            for i in range(23, -1, -1):
                h_start = _dt_to_str(now - timedelta(hours=i + 1))
                h_end = _dt_to_str(now - timedelta(hours=i))
                hour_label = (now - timedelta(hours=i)).strftime("%H:00")
                ops = self.conn.execute(
                    "SELECT COUNT(*) FROM api_audit WHERE timestamp >= ? AND timestamp < ?",
                    (h_start, h_end)
                ).fetchone()[0]
                errs = self.conn.execute(
                    "SELECT COUNT(*) FROM api_audit WHERE timestamp >= ? AND timestamp < ? AND operation = 'auth.login' AND status_code >= 400",
                    (h_start, h_end)
                ).fetchone()[0]
                sens = self.conn.execute(
                    "SELECT COUNT(*) FROM api_audit WHERE timestamp >= ? AND timestamp < ? AND is_sensitive = 1",
                    (h_start, h_end)
                ).fetchone()[0]
                sparkline["ops"].append({"day": hour_label, "count": ops})
                sparkline["login_failures"].append({"day": hour_label, "count": errs})
                sparkline["sensitive"].append({"day": hour_label, "count": sens})
        except Exception as e:
            log.warning("Audit sparkline query failed - the audit dashboard will show empty charts", error=str(e))

        return {
            "total": total,
            "unique_users": users,
            "login_failures": login_failures,
            "sensitive": sensitive,
            "sparkline": sparkline,
        }

    def cleanup_api_audit(self, retention_days: int) -> int:
        cutoff = _dt_to_str(datetime.utcnow() - timedelta(days=retention_days))
        with self._lock:
            try:
                count = self.conn.execute(
                    "DELETE FROM api_audit WHERE timestamp < ?", (cutoff,)
                ).rowcount
                self.conn.commit()
                return count
            except Exception:
                self._rollback_safely()
                raise

    # --- Helpers ---

    @staticmethod
    def _row_to_archive(row: sqlite3.Row) -> ArchiveRecord:
        return ArchiveRecord(
            id=row["id"],
            server_name=row["server_name"],
            stream_id=row["stream_id"],
            stream_name=row["stream_name"],
            time_from=_str_to_dt(row["time_from"]),  # type: ignore
            time_to=_str_to_dt(row["time_to"]),  # type: ignore
            file_path=row["file_path"],
            file_size_bytes=row["file_size_bytes"],
            original_size_bytes=row["original_size_bytes"] if "original_size_bytes" in row.keys() else 0,
            message_count=row["message_count"],
            part_number=row["part_number"],
            total_parts=row["total_parts"],
            checksum_sha256=row["checksum_sha256"],
            hmac_sha256=(row["hmac_sha256"] if "hmac_sha256" in row.keys() else None),
            overflow_ms=(row["overflow_ms"] if "overflow_ms" in row.keys() else None),
            status=ArchiveStatus(row["status"]),
            created_at=_str_to_dt(row["created_at"]),  # type: ignore
            deleted_at=_str_to_dt(row["deleted_at"]),
        )

    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> JobRecord:
        return JobRecord(
            id=row["id"],
            job_type=row["job_type"],
            status=JobStatus(row["status"]),
            progress_pct=row["progress_pct"],
            messages_done=row["messages_done"],
            messages_total=row["messages_total"],
            config_json=row["config_json"],
            error_message=row["error_message"],
            started_at=_str_to_dt(row["started_at"]),
            completed_at=_str_to_dt(row["completed_at"]),
            source=row["source"] if "source" in row.keys() else "",
            result_json=row["result_json"] if "result_json" in row.keys() else None,
            created_at=_str_to_dt(row["created_at"]),  # type: ignore
        )

    @staticmethod
    def _row_to_schedule(row: sqlite3.Row) -> ScheduleRecord:
        return ScheduleRecord(
            id=row["id"],
            name=row["name"],
            job_type=row["job_type"],
            cron_expr=row["cron_expr"],
            config_json=row["config_json"],
            enabled=bool(row["enabled"]),
            last_run_at=_str_to_dt(row["last_run_at"]),
            next_run_at=_str_to_dt(row["next_run_at"]),
        )
