"""Pydantic models for glogarch."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ArchiveStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DELETED = "deleted"
    IMPORTING = "importing"
    CORRUPTED = "corrupted"
    MISSING = "missing"


class JobType(str, Enum):
    EXPORT = "export"
    IMPORT = "import"
    CLEANUP = "cleanup"
    VERIFY = "verify"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ArchiveRecord(BaseModel):
    id: int | None = None
    server_name: str
    stream_id: str | None = None
    stream_name: str | None = None
    time_from: datetime
    time_to: datetime
    file_path: str
    file_size_bytes: int = 0
    original_size_bytes: int = 0
    message_count: int = 0
    part_number: int = 1
    total_parts: int = 1
    checksum_sha256: str = ""
    status: ArchiveStatus = ArchiveStatus.COMPLETED
    created_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: datetime | None = None
    # JSON: {field_name: ["numeric", "string", "other"]} — value-type observations
    # accumulated while writing this archive. Used by import preflight to set the
    # target Graylog's custom field mappings to "string" (keyword) for any field
    # whose archive contains string values, eliminating mapping conflicts before
    # any GELF send. Compliance requirement: zero indexer failures.
    field_schema: str | None = None


class JobRecord(BaseModel):
    id: str
    job_type: JobType
    status: JobStatus = JobStatus.PENDING
    progress_pct: float = 0.0
    messages_done: int = 0
    messages_total: int | None = None
    config_json: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    source: str = ""  # "manual", "scheduled", ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ScheduleRecord(BaseModel):
    id: int | None = None
    name: str
    job_type: str
    cron_expr: str
    config_json: str | None = None
    enabled: bool = True
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None


class ImportHistoryRecord(BaseModel):
    id: int | None = None
    archive_id: int
    target_server: str
    messages_sent: int = 0
    imported_at: datetime = Field(default_factory=datetime.utcnow)
    job_id: str | None = None


class ArchiveMetadata(BaseModel):
    """Metadata stored inside each .json.gz archive file.

    The archive format preserves `gl2_message_id` (used as a dedup key by
    the OpenSearch bulk import path); other `gl2_*` Graylog internal fields
    are stripped because they reference source-cluster nodes/inputs that
    don't exist in the target.
    """

    version: str = "1.0"
    server: str
    stream_id: str | None = None
    stream_name: str | None = None
    time_from: str
    time_to: str
    query: str = "*"
    message_count: int = 0
    part: int = 1
    total_parts: int = 1
    checksum_sha256: str = ""
    exported_at: str = ""
    glogarch_version: str = ""
