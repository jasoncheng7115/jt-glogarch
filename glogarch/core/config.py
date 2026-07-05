"""Configuration loading and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class OpenSearchConfig(BaseModel):
    hosts: list[str] = Field(default_factory=list)  # e.g. ["http://192.168.1.127:9200"]
    username: str | None = None
    password: str | None = None
    verify_ssl: bool = False


class GraylogServerConfig(BaseModel):
    name: str
    url: str  # e.g. "https://graylog.example.com/api"
    auth_token: str | None = None
    username: str | None = None
    password: str | None = None
    verify_ssl: bool = True
    # Optional per-server OpenSearch cluster for OpenSearch-mode export.
    # When unset, the global top-level `opensearch:` block is used as fallback.
    # `hosts` within are failover NODES of THIS server's single cluster.
    opensearch: OpenSearchConfig | None = None


class ExportConfig(BaseModel):
    base_path: str = "/data/graylog-archives"
    chunk_duration_minutes: int = 60
    max_file_size_mb: int = 50
    query: str = "*"
    streams: list[str] = Field(default_factory=list)
    index_sets: list[str] = Field(default_factory=list)
    fields: list[str] = Field(default_factory=list)
    batch_size: int = 1000
    min_disk_space_mb: int = 500
    delay_between_requests_ms: int = 5
    # JVM heap uses TWO tiers so we back off well before the ceiling without
    # false-tripping on a momentary GC peak:
    #   * soft (75%) pauses only when SUSTAINED (health_heap_sustained_samples)
    #   * hard (90%) pauses immediately on a single reading (safety net)
    jvm_memory_threshold_pct: float = 75.0  # soft: pause when sustained above this %
    jvm_memory_hard_pct: float = 90.0       # hard: pause immediately at/above this %
    health_heap_sustained_samples: int = 2  # consecutive soft-over reads before pausing
    # --- Adaptive backpressure guard (applies to BOTH API and OpenSearch export) ---
    # Pause the export whenever Graylog is falling behind on ingestion — JVM heap
    # high, or the disk journal / process-output-input buffers keep climbing — and
    # resume only once they drain. Protects log collection on any storage (incl.
    # slow HDD) where a heavy export would otherwise starve indexing.
    health_guard_enabled: bool = True
    health_sample_interval_sec: int = 15    # FIXED wall-clock sampling cadence (not per-chunk)
    health_rise_samples: int = 3            # consecutive climbs before "rising" trips
    health_journal_min_delta: int = 200     # min journal-entry growth/sample to count
    health_buffer_min_delta: int = 64       # min buffer growth/sample to count
    health_pause_interval_sec: int = 15     # re-check cadence while paused
    health_max_pause_min: int = 30          # give up (stop export) after this long paused
    health_resume_drain_ratio: float = 0.7  # resume when signal <= peak * this
    connection_failure_limit: int = 10      # consecutive connection failures → abort


class ImportConfig(BaseModel):
    gelf_host: str = "localhost"
    gelf_port: int = 32202
    gelf_protocol: str = "tcp"  # "udp" or "tcp"
    batch_size: int = 500
    delay_between_batches_ms: int = 100


class RetentionConfig(BaseModel):
    enabled: bool = True
    retention_days: int = 1095


class RateLimitConfig(BaseModel):
    requests_per_second: float = 2.0
    adaptive: bool = True
    max_cpu_percent: float = 80.0
    backoff_seconds: float = 10.0


class ScheduleConfig(BaseModel):
    export_cron: str | None = "0 * * * *"
    export_days: int = 180
    cleanup_cron: str | None = "0 3 * * *"


class TelegramConfig(BaseModel):
    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""


class DiscordConfig(BaseModel):
    enabled: bool = False
    webhook_url: str = ""


class SlackConfig(BaseModel):
    enabled: bool = False
    webhook_url: str = ""


class TeamsConfig(BaseModel):
    enabled: bool = False
    webhook_url: str = ""


class NextcloudTalkConfig(BaseModel):
    enabled: bool = False
    server_url: str = ""       # e.g. "https://cloud.example.com"
    token: str = ""            # conversation token
    username: str = ""
    password: str = ""


class EmailConfig(BaseModel):
    enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_tls: bool = True
    smtp_user: str = ""
    smtp_password: str = ""
    from_addr: str = ""
    to_addrs: list[str] = Field(default_factory=list)  # can send to multiple recipients
    subject_prefix: str = "[jt-glogarch]"


class NotifyConfig(BaseModel):
    language: str = "zh-TW"  # "en" or "zh-TW"
    on_export_complete: bool = True
    on_import_complete: bool = True
    on_cleanup_complete: bool = False
    on_error: bool = True
    on_verify_failed: bool = True
    on_sensitive_operation: bool = True
    on_audit_alert: bool = True
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    discord: DiscordConfig = Field(default_factory=DiscordConfig)
    slack: SlackConfig = Field(default_factory=SlackConfig)
    teams: TeamsConfig = Field(default_factory=TeamsConfig)
    nextcloud_talk: NextcloudTalkConfig = Field(default_factory=NextcloudTalkConfig)
    email: EmailConfig = Field(default_factory=EmailConfig)


class ApiAuditConfig(BaseModel):
    enabled: bool = True
    listen_port: int = 8991
    retention_days: int = 180
    max_body_size: int = 65536
    alert_sensitive: bool = True


class WebConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8990
    ssl_certfile: str = "/opt/jt-glogarch/certs/server.crt"
    ssl_keyfile: str = "/opt/jt-glogarch/certs/server.key"
    # Emergency local admin — SHA256 hash of password. Used as fallback
    # when Graylog API is unreachable. Empty string = disabled (default).
    # Generate with: python3 -c "import hashlib;print(hashlib.sha256(input('Password: ').encode()).hexdigest())"
    localadmin_password_hash: str = ""


class Settings(BaseModel):
    servers: list[GraylogServerConfig] = Field(default_factory=list)
    default_server: str = ""
    export_mode: str = "api"  # "api" or "opensearch"
    export: ExportConfig = Field(default_factory=ExportConfig)
    import_config: ImportConfig = Field(default_factory=ImportConfig, alias="import")
    opensearch: OpenSearchConfig = Field(default_factory=OpenSearchConfig)
    notify: NotifyConfig = Field(default_factory=NotifyConfig)
    retention: RetentionConfig = Field(default_factory=RetentionConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)
    op_audit: ApiAuditConfig = Field(default_factory=ApiAuditConfig)
    web: WebConfig = Field(default_factory=WebConfig)
    database_path: str = "glogarch.db"
    log_level: str = "INFO"
    _config_path: str = ""  # Path to the loaded config file (not serialized)

    model_config = {"populate_by_name": True}

    @property
    def config_path(self) -> str:
        return self._config_path

    def get_server(self, name: str | None = None) -> GraylogServerConfig:
        """Get server config by name, or the default server."""
        target = name or self.default_server
        for s in self.servers:
            if s.name == target:
                return s
        if self.servers:
            return self.servers[0]
        raise ValueError(f"No server configured (requested: {target!r})")

    def get_opensearch(self, server_name: str | None = None) -> OpenSearchConfig:
        """Resolve the OpenSearch cluster for a given Graylog server.

        Returns the server's own `opensearch` block when set (multi-cluster
        archiving), otherwise falls back to the global top-level `opensearch:`
        block. Resolution never raises — an unconfigured server yields the
        global block (which may itself be empty)."""
        try:
            server = self.get_server(server_name)
        except ValueError:
            return self.opensearch
        if server.opensearch is not None and server.opensearch.hosts:
            return server.opensearch
        return self.opensearch


# Singleton
_settings: Settings | None = None


def load_settings(config_path: str | Path | None = None) -> Settings:
    """Load settings from YAML file."""
    global _settings

    search_paths = [
        config_path,
        Path("config.yaml"),
        Path.home() / ".jt-glogarch" / "config.yaml",
        Path("/etc/jt-glogarch/config.yaml"),
    ]

    for p in search_paths:
        if p is None:
            continue
        p = Path(p)
        if p.is_file():
            with open(p) as f:
                data: dict[str, Any] = yaml.safe_load(f) or {}
            # Backward compat: api_audit → op_audit
            if "api_audit" in data and "op_audit" not in data:
                data["op_audit"] = data.pop("api_audit")
            elif "api_audit" in data:
                data.pop("api_audit")
            _settings = Settings(**data)
            _settings._config_path = str(p.resolve())
            return _settings

    # Return defaults if no config file found
    _settings = Settings()
    return _settings


def get_settings() -> Settings:
    """Get the current settings singleton."""
    global _settings
    if _settings is None:
        return load_settings()
    return _settings
