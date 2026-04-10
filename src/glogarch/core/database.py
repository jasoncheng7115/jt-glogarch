"""SQLite database for archive tracking."""

from __future__ import annotations

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
"""


def _dt_to_str(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    # Strip timezone info to store consistent naive UTC
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _str_to_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    # Always return naive UTC datetime for consistent comparison
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    return dt


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
        existing_arc = {row[1] for row in conn.execute("PRAGMA table_info(archives)").fetchall()}
        if "original_size_bytes" not in existing_arc:
            conn.execute("ALTER TABLE archives ADD COLUMN original_size_bytes INTEGER NOT NULL DEFAULT 0")
        if "field_schema" not in existing_arc:
            conn.execute("ALTER TABLE archives ADD COLUMN field_schema TEXT")

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
            cur = self.conn.execute(
                """INSERT OR REPLACE INTO archives
                   (server_name, stream_id, stream_name, time_from, time_to,
                    file_path, file_size_bytes, original_size_bytes, message_count, part_number, total_parts,
                    checksum_sha256, status, created_at, field_schema)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                ),
            )
            self.conn.commit()
            return cur.lastrowid  # type: ignore[return-value]

    def get_archive_field_schemas(self, archive_ids: list[int]) -> dict[int, str | None]:
        """Return {archive_id: field_schema_json or None} for the given ids.
        Used by import preflight to discover field types without re-scanning files.
        """
        if not archive_ids:
            return {}
        placeholders = ",".join("?" * len(archive_ids))
        rows = self.conn.execute(
            f"SELECT id, field_schema, file_path FROM archives WHERE id IN ({placeholders})",
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
            self.conn.execute(f"UPDATE archives SET {', '.join(sets)} WHERE id = ?", vals)
            self.conn.commit()

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

    def list_archives(
        self,
        server: str | None = None,
        stream: str | None = None,
        time_from: datetime | None = None,
        time_to: datetime | None = None,
        status: ArchiveStatus | None = None,
        sort: str = "time_from",
        order: str = "DESC",
    ) -> list[ArchiveRecord]:
        ALLOWED_SORT = {"time_from", "time_to", "message_count", "file_size_bytes", "created_at", "server_name"}
        sort_col = sort if sort in ALLOWED_SORT else "time_from"
        sort_dir = "ASC" if order.upper() == "ASC" else "DESC"
        query = "SELECT * FROM archives WHERE 1=1"
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
        rows = self.conn.execute(query, params).fetchall()
        return [self._row_to_archive(r) for r in rows]

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

    # --- Jobs ---

    def create_job(self, job: JobRecord) -> None:
        from glogarch.utils.sanitize import sanitize
        with self._lock:
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

    def update_job(self, job_id: str, **kwargs) -> None:
        from glogarch.utils.sanitize import sanitize
        ALLOWED_JOB_COLS = {"status", "progress_pct", "messages_done", "messages_total",
                            "config_json", "error_message", "started_at", "completed_at", "source"}
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
            self.conn.execute(f"UPDATE jobs SET {', '.join(sets)} WHERE id = ?", vals)
            self.conn.commit()

    def get_job(self, job_id: str) -> JobRecord | None:
        row = self.conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return self._row_to_job(row) if row else None

    def list_jobs(self, limit: int = 50) -> list[JobRecord]:
        rows = self.conn.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [self._row_to_job(r) for r in rows]

    # --- Schedules ---

    def save_schedule(self, sched: ScheduleRecord) -> int:
        with self._lock:
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
            return cur.lastrowid  # type: ignore[return-value]

    def list_schedules(self) -> list[ScheduleRecord]:
        rows = self.conn.execute("SELECT * FROM schedules ORDER BY name").fetchall()
        return [self._row_to_schedule(r) for r in rows]

    def delete_schedule(self, name: str) -> None:
        with self._lock:
            self.conn.execute("DELETE FROM schedules WHERE name = ?", (name,))
            self.conn.commit()

    # --- Import History ---

    def record_import(self, record: ImportHistoryRecord) -> int:
        with self._lock:
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

    # --- Audit Log ---

    def audit(self, action: str, detail: str = "", username: str = "", ip_address: str = "") -> None:
        """Record an audit log entry."""
        from glogarch.utils.sanitize import sanitize
        with self._lock:
            self.conn.execute(
                "INSERT INTO audit_log (timestamp, username, action, detail, ip_address) VALUES (?, ?, ?, ?, ?)",
                (_dt_to_str(datetime.utcnow()), username, action, (sanitize(detail) or "")[:500], ip_address),
            )
            self.conn.commit()

    def list_audit(self, limit: int = 200) -> list[dict]:
        """Get recent audit log entries."""
        rows = self.conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

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
