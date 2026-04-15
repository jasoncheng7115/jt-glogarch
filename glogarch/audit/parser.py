"""Parse nginx syslog audit lines into structured events."""

from __future__ import annotations

import base64
import json
import re

from glogarch.utils.logging import get_logger
from glogarch.utils.sanitize import sanitize

log = get_logger("audit.parser")

# Sensitive operation patterns: (method_regex, uri_regex, operation_label)
SENSITIVE_PATTERNS: list[tuple[str, str, str]] = [
    (r"DELETE", r"/api/users/", "user.delete"),
    (r"PUT|POST", r"/api/users/", "user.modify"),
    (r"POST", r"/api/system/sessions$", "auth.login"),
    (r"DELETE", r"/api/system/sessions", "auth.logout"),
    (r"DELETE", r"/api/streams/", "stream.delete"),
    (r"DELETE", r"/api/system/inputs/", "input.delete"),
    (r"DELETE", r"/api/cluster/inputstates/", "input.stop"),
    (r"PUT", r"/api/cluster/inputstates/", "input.start"),
    (r"DELETE", r"/api/system/inputstates/", "input.stop"),
    (r"PUT", r"/api/system/inputstates/", "input.start"),
    (r"PUT", r"/api/system/inputs/", "input.modify"),
    (r"PUT|DELETE", r"/api/system/indices/index_sets/", "indexset.modify"),
    (r"PUT|DELETE", r"/api/system/pipelines/", "pipeline.modify"),
    (r"PUT|DELETE", r"/api/plugins/org\.graylog\.plugins\.pipelineprocessor/", "pipeline.modify"),
    (r"DELETE", r"/api/dashboards/", "dashboard.delete"),
    (r"PUT|DELETE", r"/api/events/definitions/", "alert.modify"),
    (r".*", r"/shutdown", "system.shutdown"),
]

# Compiled for performance
_SENSITIVE_COMPILED = [
    (re.compile(m), re.compile(u), label)
    for m, u, label in SENSITIVE_PATTERNS
]

# Operation classification (broader, non-sensitive)
_OP_PATTERNS: list[tuple[str, str, str]] = [
    (r"GET", r"/api/views/search", "search.execute"),
    (r"POST", r"/api/views/search", "search.execute"),
    (r"GET", r"/api/system$", "system.info"),
    (r"GET", r"/api/streams", "stream.list"),
    (r"POST", r"/api/streams", "stream.create"),
    (r"GET", r"/api/system/inputs", "input.list"),
    (r"POST", r"/api/system/inputs", "input.create"),
    (r"GET", r"/api/users", "user.list"),
    (r"GET", r"/api/dashboards", "dashboard.list"),
    (r"POST", r"/api/dashboards", "dashboard.create"),
    (r"PUT", r"/api/dashboards/", "dashboard.modify"),
]

_OP_COMPILED = [
    (re.compile(m), re.compile(u), label)
    for m, u, label in _OP_PATTERNS
]


def parse_syslog_payload(data: bytes) -> str | None:
    """Extract the JSON payload from a syslog UDP packet.

    nginx syslog format: ``<PRI>TIMESTAMP HOSTNAME TAG: JSON``
    We only need the JSON part after the last ``: ``.
    """
    try:
        text = data.decode("utf-8", errors="replace")
        # Find the JSON object — look for first '{'
        idx = text.find("{")
        if idx < 0:
            return None
        return text[idx:]
    except Exception:
        return None


def parse_nginx_json(json_str: str) -> dict | None:
    """Parse the nginx JSON log line into a dict."""
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        return None


def decode_graylog_username(auth_header: str) -> tuple[str, str]:
    """Extract username from Basic Auth header.

    Returns (username, auth_type) where auth_type is one of:
    - ``"basic"`` — regular username/password login
    - ``"token"`` — API token auth
    - ``"session"`` — Graylog session ID (needs resolution)
    - ``""`` — no auth header

    - ``Basic base64("admin:password")`` → ``("admin", "basic")``
    - ``Basic base64("tokenvalue:token")`` → ``("token:tokenva...", "token")``
    - ``Basic base64("sessionId:session")`` → ``("sessionId", "session")``
    - Empty/invalid → ``("", "")``
    """
    if not auth_header or not auth_header.startswith("Basic "):
        return "", ""
    try:
        decoded = base64.b64decode(auth_header[6:]).decode("utf-8", errors="replace")
        parts = decoded.split(":", 1)
        username = parts[0]
        password = parts[1] if len(parts) > 1 else ""
        if password == "token":
            return f"token:{username[:8]}...", "token"
        if password == "session":
            return username, "session"
        return username, "basic"
    except Exception:
        return "", ""


def classify_operation(method: str, uri: str) -> str:
    """Classify the API call into an operation label."""
    # Check sensitive patterns first (more specific)
    for m_re, u_re, label in _SENSITIVE_COMPILED:
        if m_re.fullmatch(method) and u_re.search(uri):
            return label
    # Then check the whitelist patterns
    for m, pat, label in _KEEP_COMPILED:
        if (m == "ANY" or m == method) and pat.search(uri):
            return label
    # Fallback to broader patterns
    for m_re, u_re, label in _OP_COMPILED:
        if m_re.fullmatch(method) and u_re.search(uri):
            return label
    return ""


def is_sensitive(method: str, uri: str) -> bool:
    """Check if this operation is classified as sensitive."""
    for m_re, u_re, _ in _SENSITIVE_COMPILED:
        if m_re.fullmatch(method) and u_re.search(uri):
            return True
    return False


# Whitelist approach: only keep requests that match these patterns.
# Everything else (background polling, static assets, metrics, etc.) is dropped.
_KEEP_PATTERNS: list[tuple[str, re.Pattern, str]] = [
    # Authentication
    ("POST", re.compile(r"/api/system/sessions$"), "auth.login"),
    ("DELETE", re.compile(r"/api/system/sessions"), "auth.logout"),
    # User management
    ("POST", re.compile(r"/api/users"), "user.create"),
    ("PUT", re.compile(r"/api/users/.+/password$"), "user.password_change"),
    ("PUT", re.compile(r"/api/users/.+/permissions$"), "user.permissions_change"),
    ("PUT", re.compile(r"/api/users/.+/status/"), "user.status_change"),
    ("POST", re.compile(r"/api/users/.+/tokens/"), "user.token_create"),
    ("DELETE", re.compile(r"/api/users/.+/tokens/"), "user.token_delete"),
    ("PUT", re.compile(r"/api/users/"), "user.modify"),
    ("DELETE", re.compile(r"/api/users/"), "user.delete"),
    # Role management
    ("POST", re.compile(r"/api/roles"), "role.create"),
    ("PUT", re.compile(r"/api/roles/"), "role.modify"),
    ("DELETE", re.compile(r"/api/roles/"), "role.delete"),
    # Extractor management (must be before input.modify — more specific URI)
    ("POST", re.compile(r"/api/system/inputs/.+/extractors$"), "extractor.create"),
    ("POST", re.compile(r"/api/system/inputs/.+/extractors/order$"), "extractor.reorder"),
    ("PUT", re.compile(r"/api/system/inputs/.+/extractors/"), "extractor.modify"),
    ("DELETE", re.compile(r"/api/system/inputs/.+/extractors/"), "extractor.delete"),
    # Static fields on inputs
    ("POST", re.compile(r"/api/system/inputs/.+/staticfields$"), "static_field.create"),
    ("DELETE", re.compile(r"/api/system/inputs/.+/staticfields/"), "static_field.delete"),
    # Input management
    ("POST", re.compile(r"/api/system/inputs$"), "input.create"),
    ("PUT", re.compile(r"/api/system/inputs/[a-f0-9]{24}$"), "input.modify"),
    ("DELETE", re.compile(r"/api/system/inputs/[a-f0-9]{24}$"), "input.delete"),
    ("PUT", re.compile(r"/api/(system|cluster)/inputstates/setup/"), "input.setup_mode"),
    ("PUT", re.compile(r"/api/(system|cluster)/inputstates/"), "input.start"),
    ("DELETE", re.compile(r"/api/(system|cluster)/inputstates/"), "input.stop"),
    # Stream management
    ("POST", re.compile(r"/api/streams$"), "stream.create"),
    ("POST", re.compile(r"/api/streams/.+/clone"), "stream.clone"),
    ("PUT", re.compile(r"/api/streams/"), "stream.modify"),
    ("DELETE", re.compile(r"/api/streams/"), "stream.delete"),
    ("POST", re.compile(r"/api/streams/.+/pause"), "stream.pause"),
    ("POST", re.compile(r"/api/streams/.+/resume"), "stream.resume"),
    ("POST", re.compile(r"/api/streams/bulk_delete"), "stream.bulk_delete"),
    ("POST", re.compile(r"/api/streams/bulk_pause"), "stream.bulk_pause"),
    ("POST", re.compile(r"/api/streams/bulk_resume"), "stream.bulk_resume"),
    # Stream rules
    ("POST", re.compile(r"/api/streams/.+/rules"), "stream_rule.create"),
    ("PUT", re.compile(r"/api/streams/.+/rules/"), "stream_rule.modify"),
    ("DELETE", re.compile(r"/api/streams/.+/rules/"), "stream_rule.delete"),
    # Index set management
    ("POST", re.compile(r"/api/system/indices/index_sets$"), "indexset.create"),
    ("PUT", re.compile(r"/api/system/indices/index_sets/.+/default$"), "indexset.set_default"),
    ("PUT", re.compile(r"/api/system/indices/index_sets/"), "indexset.modify"),
    ("DELETE", re.compile(r"/api/system/indices/index_sets/"), "indexset.delete"),
    # Index operations
    ("DELETE", re.compile(r"/api/system/indexer/indices/"), "index.delete"),
    ("POST", re.compile(r"/api/system/indexer/indices/.+/close"), "index.close"),
    ("POST", re.compile(r"/api/system/indexer/indices/.+/reopen"), "index.reopen"),
    ("POST", re.compile(r"/api/system/deflector"), "deflector.cycle"),
    ("POST", re.compile(r"/api/cluster/deflector"), "deflector.cycle"),
    # Pipeline management
    ("POST", re.compile(r"/api/system/pipelines/pipeline$"), "pipeline.create"),
    ("PUT", re.compile(r"/api/system/pipelines/pipeline/"), "pipeline.modify"),
    ("DELETE", re.compile(r"/api/system/pipelines/pipeline/"), "pipeline.delete"),
    ("POST", re.compile(r"/api/system/pipelines/rule$"), "pipeline_rule.create"),
    ("PUT", re.compile(r"/api/system/pipelines/rule/"), "pipeline_rule.modify"),
    ("DELETE", re.compile(r"/api/system/pipelines/rule/"), "pipeline_rule.delete"),
    ("POST", re.compile(r"/api/system/pipelines/connections"), "pipeline.connect"),
    # Event/alert definitions
    ("POST", re.compile(r"/api/events/definitions$"), "event.create"),
    ("POST", re.compile(r"/api/events/definitions/.+/duplicate$"), "event.duplicate"),
    ("PUT", re.compile(r"/api/events/definitions/.+/schedule$"), "event.enable"),
    ("PUT", re.compile(r"/api/events/definitions/.+/unschedule$"), "event.disable"),
    ("POST", re.compile(r"/api/events/definitions/.+/execute$"), "event.execute"),
    ("PUT", re.compile(r"/api/events/definitions/.+/clear-notification-queue$"), "event.clear_queue"),
    ("POST", re.compile(r"/api/events/definitions/bulk_delete"), "event.bulk_delete"),
    ("POST", re.compile(r"/api/events/definitions/bulk_schedule"), "event.bulk_enable"),
    ("POST", re.compile(r"/api/events/definitions/bulk_unschedule"), "event.bulk_disable"),
    ("PUT", re.compile(r"/api/events/definitions/"), "event.modify"),
    ("DELETE", re.compile(r"/api/events/definitions/"), "event.delete"),
    ("POST", re.compile(r"/api/events/notifications$"), "event_notif.create"),
    ("PUT", re.compile(r"/api/events/notifications/"), "event_notif.modify"),
    ("DELETE", re.compile(r"/api/events/notifications/"), "event_notif.delete"),
    # Dashboard/view management (exclude searchjobs/export/search sub-paths)
    ("POST", re.compile(r"/api/views$"), "view.create"),
    ("PUT", re.compile(r"/api/views/[a-f0-9]{24}$"), "view.modify"),
    ("DELETE", re.compile(r"/api/views/[a-f0-9]{24}$"), "view.delete"),
    ("GET", re.compile(r"/api/views/[a-f0-9]{24}$"), "view.open"),
    # Search
    ("POST", re.compile(r"/api/views/search$"), "search.create"),
    ("PUT", re.compile(r"/api/views/search/[a-f0-9]+$"), "search.update"),
    ("POST", re.compile(r"/api/views/search/sync$"), "search.execute"),
    ("GET", re.compile(r"/api/search/universal/"), "search.execute"),
    # Search export (CSV download)
    ("POST", re.compile(r"/api/views/search/messages"), "search.export"),
    ("POST", re.compile(r"/api/views/export"), "search.export"),
    # Lookup tables, adapters, caches
    ("POST", re.compile(r"/api/system/lookup/tables$"), "lookup_table.create"),
    ("PUT", re.compile(r"/api/system/lookup/tables/"), "lookup_table.modify"),
    ("DELETE", re.compile(r"/api/system/lookup/tables/"), "lookup_table.delete"),
    ("POST", re.compile(r"/api/system/lookup/adapters$"), "lookup_adapter.create"),
    ("PUT", re.compile(r"/api/system/lookup/adapters/"), "lookup_adapter.modify"),
    ("DELETE", re.compile(r"/api/system/lookup/adapters/"), "lookup_adapter.delete"),
    ("POST", re.compile(r"/api/system/lookup/caches$"), "lookup_cache.create"),
    ("PUT", re.compile(r"/api/system/lookup/caches/"), "lookup_cache.modify"),
    ("DELETE", re.compile(r"/api/system/lookup/caches/"), "lookup_cache.delete"),
    # Content packs
    ("POST", re.compile(r"/api/system/content_packs"), "content_pack.install"),
    ("DELETE", re.compile(r"/api/system/content_packs/"), "content_pack.delete"),
    # Grok patterns
    ("POST", re.compile(r"/api/system/grok"), "grok.create"),
    ("PUT", re.compile(r"/api/system/grok"), "grok.modify"),
    ("DELETE", re.compile(r"/api/system/grok/"), "grok.delete"),
    # Output management
    ("POST", re.compile(r"/api/system/outputs$"), "output.create"),
    ("PUT", re.compile(r"/api/system/outputs/"), "output.modify"),
    ("DELETE", re.compile(r"/api/system/outputs/"), "output.delete"),
    # System configuration
    ("PUT", re.compile(r"/api/system/cluster_config/"), "cluster_config.modify"),
    ("DELETE", re.compile(r"/api/system/cluster_config/"), "cluster_config.delete"),
    ("PUT", re.compile(r"/api/system/indices/mappings"), "field_mapping.modify"),
    # Processing control
    ("PUT", re.compile(r"/api/system/processing/pause"), "processing.pause"),
    ("PUT", re.compile(r"/api/system/processing/resume"), "processing.resume"),
    ("PUT", re.compile(r"/api/system/messageprocessors/config"), "processing.config"),
    # Sharing
    ("POST", re.compile(r"/api/authz/shares/entities/grn[^/]+$"), "share.modify"),  # exclude /prepare
    # Sidecar
    ("POST", re.compile(r"/api/sidecar/(collectors|configurations)$"), "sidecar.create"),
    ("PUT", re.compile(r"/api/sidecar/(collectors|configurations)/"), "sidecar.modify"),
    ("DELETE", re.compile(r"/api/sidecar/(collectors|configurations)/"), "sidecar.delete"),
    # System shutdown
    ("ANY", re.compile(r"/shutdown"), "system.shutdown"),
]

_KEEP_COMPILED = [(m, p, l) for m, p, l in _KEEP_PATTERNS]


def is_noise(method: str, uri: str) -> bool:
    """Return True if this request should be skipped (not a meaningful operation)."""
    # Non-API requests (static assets, etc.) are always noise
    if not uri.startswith("/api/"):
        return True
    # Pre-check / preview endpoints are not actual actions
    if uri.endswith("/prepare") or uri.endswith("/preview"):
        return True
    # Check against whitelist — if it matches, it's NOT noise
    for m, pat, _ in _KEEP_COMPILED:
        if (m == "ANY" or m == method) and pat.search(uri):
            return False
    # Everything else is noise
    return True


def process_raw_entry(raw: dict, max_body_size: int = 65536) -> dict:
    """Process a parsed nginx JSON dict into a DB-ready audit entry.

    - Decodes username from Authorization header
    - Classifies the operation
    - Sanitizes the request body (removes passwords/tokens)
    - Truncates large bodies
    - NEVER stores the raw Authorization header
    """
    method = raw.get("method", "")
    uri = raw.get("uri", "")
    auth = raw.get("http_authorization", "")

    username, auth_type = decode_graylog_username(auth)
    operation = classify_operation(method, uri)
    sensitive = is_sensitive(method, uri)

    body = raw.get("request_body") or ""
    if body == "-":
        body = ""
    if body:
        body = sanitize(body) or ""
        if len(body) > max_body_size:
            body = body[:max_body_size] + "...[truncated]"

    request_time = raw.get("request_time", 0)
    try:
        request_time_ms = float(request_time) * 1000
    except (ValueError, TypeError):
        request_time_ms = 0.0

    # Extract full token value for async resolution (never stored in DB)
    full_token = ""
    if auth_type == "token" and auth.startswith("Basic "):
        try:
            decoded = base64.b64decode(auth[6:]).decode("utf-8", errors="replace")
            full_token = decoded.split(":", 1)[0]
        except Exception:
            pass

    # If no auth header but cookie has session ID, use it
    cookie_session = ""
    if not auth_type:
        cookie_val = raw.get("http_cookie", "") or ""
        if cookie_val and cookie_val != "-":
            cookie_session = cookie_val.strip()

    return {
        "server_name": raw.get("server_name", ""),
        "timestamp": raw.get("time", ""),
        "remote_addr": raw.get("remote_addr", ""),
        "username": username,
        "_auth_type": auth_type,  # stripped before DB insert
        "_full_token": full_token,  # stripped before DB insert
        "_cookie_session": cookie_session,  # stripped before DB insert
        "method": method,
        "uri": uri,
        "query_string": raw.get("args", ""),
        "status_code": int(raw.get("status", 0)),
        "request_body": body,
        "user_agent": raw.get("user_agent", ""),
        "request_time_ms": request_time_ms,
        "operation": operation,
        "is_sensitive": sensitive,
    }
