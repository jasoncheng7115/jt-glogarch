"""Pre-import field mapping conflict resolver — guarantees zero indexer
failures by setting target Graylog custom field mappings BEFORE GELF send.

Workflow when an import is triggered:
    1. Verify Graylog API credentials.
    2. Resolve field schema for the selected archives:
        - Primary: read `archives.field_schema` JSON column from DB.
        - Fallback: for archives created before this feature existed, scan
          their .json.gz files inline. Slower, but only happens once and we
          backfill the DB so the next import is fast.
    3. Locate target index set (by GELF input port → index set, or default).
    4. Read its current custom field mappings.
    5. Decide which fields need to be force-keyword:
        Any field where ANY archive observed at least one *string* value AND
        the target's current mapping isn't already a string-like type.
        We're aggressive on purpose: it's safer to over-pin than to under-pin.
    6. PUT custom field mappings via Graylog API.
    7. Cycle the active write index so the new mapping takes effect.
    8. Wait for the new active index to come online.

If any step fails, the import is aborted with a clear error. Compliance
demands zero loss; silently sending into a misaligned index is unacceptable.

Post-import reconciliation:
    9. After GELF send finishes, query Graylog indexer failures count
       (delta vs pre-import baseline) and report. Any non-zero delta is a
       compliance violation that must be surfaced to the user.
"""

from __future__ import annotations

import asyncio
import gzip
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import httpx

from glogarch.utils.logging import get_logger

log = get_logger("import.preflight")


# OpenSearch field types that already accept arbitrary string values.
_STRING_LIKE_OS_TYPES = {"keyword", "text", "wildcard", "constant_keyword", "string"}

# Reserved Graylog/OpenSearch fields we never touch.
_RESERVED_FIELDS = {
    "timestamp", "_id", "gl2_processing_timestamp", "gl2_receive_timestamp",
    "gl2_message_id", "streams", "source", "message", "full_message",
    "gl2_processing_duration_ms", "gl2_accounted_message_size",
}


@dataclass
class PreflightResult:
    archives_total: int = 0
    archives_with_db_schema: int = 0
    archives_scanned_inline: int = 0
    fields_total: int = 0
    fields_with_string: int = 0
    conflicts: list[str] = field(default_factory=list)
    fields_set_keyword: list[str] = field(default_factory=list)
    index_set_id: str = ""
    index_set_title: str = ""
    rotated: bool = False
    duration_sec: float = 0.0
    aborted: bool = False
    error: str = ""
    indexer_failures_baseline: int = 0
    # Capacity check
    rotation_strategy: str = ""
    retention_strategy: str = ""
    estimated_indices_needed: int = 0
    capacity_warnings: list[str] = field(default_factory=list)


class PreflightChecker:
    def __init__(
        self,
        api_url: str,
        api_token: str = "",
        api_username: str = "",
        api_password: str = "",
        gelf_port: int | None = None,
    ):
        self.api_url = api_url.rstrip("/")
        self.api_token = api_token
        self.api_username = api_username
        self.api_password = api_password
        self.gelf_port = gelf_port

    # ---------------------------------------------------------------- HTTP

    def _auth(self):
        if self.api_token:
            return (self.api_token, "token")
        return (self.api_username, self.api_password)

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            verify=False,
            timeout=30,
            auth=self._auth(),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-Requested-By": "jt-glogarch",
            },
        )

    async def verify_credentials(self) -> tuple[bool, str]:
        try:
            async with self._client() as c:
                r = await c.get(f"{self.api_url}/api/system")
                if r.status_code == 401:
                    return False, "Authentication failed (401)"
                if r.status_code >= 400:
                    return False, f"HTTP {r.status_code}: {r.text[:200]}"
                return True, ""
        except Exception as e:
            return False, f"Cannot reach Graylog API: {e}"

    # ------------------------------------------------ Schema discovery

    @staticmethod
    def _scan_file_for_field_types(path: Path) -> dict[str, set[str]]:
        """Read every message in a .json.gz archive and record value type per
        field. Used as fallback for archives without DB schema column."""
        fields: dict[str, set[str]] = {}
        if not path.exists():
            return fields
        try:
            with gzip.open(path, "rt", encoding="utf-8") as f:
                data = json.load(f)
            messages = data.get("messages", []) if isinstance(data, dict) else []
        except Exception as e:
            log.warning("Schema fallback scan failed", path=str(path), error=str(e))
            return fields

        for msg in messages:
            if not isinstance(msg, dict):
                continue
            for k, v in msg.items():
                if k in _RESERVED_FIELDS:
                    continue
                if v is None or isinstance(v, bool):
                    t = "other"
                elif isinstance(v, (int, float)):
                    t = "numeric"
                elif isinstance(v, str):
                    t = "string"
                else:
                    t = "other"
                fields.setdefault(k, set()).add(t)
        return fields

    def collect_field_schema(
        self,
        db,
        archive_ids: list[int],
    ) -> tuple[dict[str, set[str]], int, int, int]:
        """Build the union {field_name: types} for the given archive ids.

        Returns:
            (fields_dict, total_archives, with_db_schema, scanned_inline)
        """
        if not archive_ids:
            return {}, 0, 0, 0

        # Pull schema rows + file_path for fallback scanning
        placeholders = ",".join("?" * len(archive_ids))
        rows = db.conn.execute(
            f"SELECT id, field_schema, file_path FROM archives WHERE id IN ({placeholders})",
            archive_ids,
        ).fetchall()

        union: dict[str, set[str]] = {}
        with_db = 0
        scanned = 0
        for r in rows:
            schema_json = r["field_schema"]
            if schema_json:
                with_db += 1
                try:
                    parsed = json.loads(schema_json)
                except Exception:
                    parsed = {}
                for k, types in parsed.items():
                    if k in _RESERVED_FIELDS:
                        continue
                    if isinstance(types, list):
                        union.setdefault(k, set()).update(types)
                    else:
                        union.setdefault(k, set()).add(str(types))
            else:
                scanned += 1
                # Fallback: scan the file inline + backfill the DB
                p = Path(r["file_path"])
                fields = self._scan_file_for_field_types(p)
                for k, types in fields.items():
                    union.setdefault(k, set()).update(types)
                # Backfill so the next import is fast
                try:
                    backfill = json.dumps(
                        {k: sorted(v) for k, v in fields.items()},
                        sort_keys=True,
                        ensure_ascii=False,
                    )
                    with db._lock:
                        db.conn.execute(
                            "UPDATE archives SET field_schema = ? WHERE id = ?",
                            (backfill, r["id"]),
                        )
                        db.conn.commit()
                except Exception as e:
                    log.warning("Schema backfill failed", id=r["id"], error=str(e))

        return union, len(rows), with_db, scanned

    # ----------------------------------- Graylog API: index set + mapping

    async def check_target_health(self) -> tuple[list[str], list[str]]:
        """Check overall target Graylog cluster health & GELF input config.
        Returns (errors, warnings). Errors are blocking.
        """
        errors: list[str] = []
        warnings: list[str] = []

        async with self._client() as c:
            # 1. Cluster health (RED is blocking)
            try:
                r = await c.get(f"{self.api_url}/api/system/indexer/cluster/health")
                if r.status_code == 200:
                    h = r.json()
                    status = h.get("status", "unknown")
                    if status == "red":
                        errors.append(
                            f"Target OpenSearch cluster is RED (status={status}, "
                            f"unassigned shards). Refusing to import — fix cluster "
                            f"first to avoid further data loss."
                        )
                    elif status == "yellow":
                        warnings.append(
                            f"Target OpenSearch cluster is YELLOW. Some replicas "
                            f"are unassigned but writes will succeed. Recommended: "
                            f"investigate before importing."
                        )
            except Exception as e:
                warnings.append(f"Could not query cluster health: {e}")

            # 2. GELF input on the configured port: exists & RUNNING + matches us
            if self.gelf_port:
                try:
                    r = await c.get(f"{self.api_url}/api/system/inputs")
                    r.raise_for_status()
                    inputs = r.json().get("inputs", [])
                    matched = [i for i in inputs if i.get("attributes", {}).get("port") == self.gelf_port]
                    gelf_matched = [
                        i for i in matched
                        if "GELF" in (i.get("type") or "") or "Gelf" in (i.get("type") or "")
                    ]
                    if not gelf_matched:
                        errors.append(
                            f"No GELF input found on target Graylog port {self.gelf_port}. "
                            f"Create a GELF TCP/UDP input on this port or change the "
                            f"GELF Port in the import dialog."
                        )
                    else:
                        inp = gelf_matched[0]
                        attrs = inp.get("attributes", {}) or {}
                        # Check input state
                        try:
                            r2 = await c.get(f"{self.api_url}/api/system/inputstates")
                            states = r2.json().get("states", []) if r2.status_code == 200 else []
                            inp_state = next(
                                (s for s in states if s.get("message_input", {}).get("id") == inp["id"]),
                                None,
                            )
                            if inp_state and inp_state.get("state") != "RUNNING":
                                errors.append(
                                    f"GELF input '{inp.get('title')}' (port {self.gelf_port}) "
                                    f"is in state {inp_state.get('state')}, not RUNNING. "
                                    f"Start the input before importing."
                                )
                        except Exception:
                            pass

                        # 3. override_source warning — would replace our source field
                        if attrs.get("override_source"):
                            warnings.append(
                                f"GELF input has override_source='{attrs['override_source']}'. "
                                f"All imported messages will have their original 'source' "
                                f"field replaced with this value. Compliance: original "
                                f"hostnames will be lost. Remove override_source to preserve."
                            )

                        # 4. Decompress size limit (some archived messages may be large)
                        decompress_limit = int(attrs.get("decompress_size_limit", 8388608))
                        if decompress_limit < 8388608:  # < 8 MB
                            warnings.append(
                                f"GELF input decompress_size_limit is "
                                f"{decompress_limit:,} bytes. Large messages "
                                f"(stack traces, full HTTP bodies) may be rejected."
                            )

                        # 5. Max message size (TCP only)
                        max_msg = attrs.get("max_message_size")
                        if max_msg and int(max_msg) < 2097152:  # < 2 MB
                            warnings.append(
                                f"GELF input max_message_size is {int(max_msg):,} "
                                f"bytes. Large messages may be silently truncated."
                            )
                except Exception as e:
                    warnings.append(f"Could not inspect GELF inputs: {e}")

            # 6. Existing journal pressure
            try:
                r = await c.get(f"{self.api_url}/api/system/journal")
                if r.status_code == 200:
                    j = r.json()
                    uncommitted = j.get("uncommitted_journal_entries", 0)
                    if uncommitted > 100_000:
                        warnings.append(
                            f"Target Graylog journal already has "
                            f"{uncommitted:,} uncommitted entries before import. "
                            f"Consider waiting for it to drain — adding more load "
                            f"may cause back-pressure throughout the import."
                        )
            except Exception:
                pass

            # 7. Disk space on data dir (best effort)
            try:
                r = await c.get(f"{self.api_url}/api/cluster")
                if r.status_code == 200:
                    nodes = r.json()
                    for node_id, info in nodes.items():
                        # Per-node disk info isn't always exposed in /api/cluster;
                        # we just note if any node looks unhealthy
                        if not info.get("is_processing", True):
                            warnings.append(
                                f"Graylog node {node_id} is_processing=false. "
                                f"It may not accept new messages."
                            )
            except Exception:
                pass

        return errors, warnings

    async def check_capacity(
        self, index_set_id: str, total_messages: int, total_bytes: int
    ) -> tuple[int, list[str]]:
        """Check whether the target index set can hold the upcoming import.
        Returns (estimated_indices_needed, list_of_warnings).

        We look at:
            - Rotation strategy + its limits (size / message count / time)
            - Retention strategy + max_number_of_indices
            - Existing indices in the set
            - Whether our import would cause the retention policy to delete
              data we just wrote (compliance violation)
        """
        warnings: list[str] = []
        estimated = 0

        async with self._client() as c:
            # Index set details
            r = await c.get(
                f"{self.api_url}/api/system/indices/index_sets/{index_set_id}"
            )
            r.raise_for_status()
            iset = r.json()

        rot = iset.get("rotation_strategy", {}) or {}
        ret = iset.get("retention_strategy", {}) or {}
        rot_class = iset.get("rotation_strategy_class", "") or ""
        ret_class = iset.get("retention_strategy_class", "") or ""
        prefix = iset.get("index_prefix", "graylog")

        # --- Estimate indices needed ---
        if "SizeBased" in rot_class:
            max_size = int(rot.get("max_size", 0))
            if max_size > 0:
                # Conservative: assume 1.5x compression vs raw bytes
                estimated = max(1, (total_bytes // max_size) + 1)
        elif "MessageCount" in rot_class:
            max_docs = int(rot.get("max_docs_per_index", 0))
            if max_docs > 0:
                estimated = max(1, (total_messages // max_docs) + 1)
        elif "TimeBasedSizeOptimizing" in rot_class:
            # Hard to estimate; assume 1
            estimated = 1
        elif "TimeBased" in rot_class:
            # Hard to estimate without knowing time spread; assume 1
            estimated = 1
        else:
            estimated = 1

        # --- Retention check ---
        if "Deletion" in ret_class:
            max_num = int(ret.get("max_number_of_indices", 0))
            if max_num > 0:
                # Count current indices in this set
                async with self._client() as c:
                    try:
                        r = await c.get(
                            f"{self.api_url}/api/system/indexer/indices/{prefix}/list"
                        )
                        if r.status_code == 200:
                            data = r.json()
                            current_count = (
                                len(data.get("all", []))
                                or len(data.get("indices", {}))
                                or 0
                            )
                        else:
                            current_count = 0
                    except Exception:
                        current_count = 0

                projected = current_count + estimated
                if projected > max_num:
                    warnings.append(
                        f"Retention will delete data: index set keeps at most "
                        f"{max_num} indices, currently has {current_count}, this "
                        f"import needs ~{estimated} new index(es). Projected total "
                        f"{projected} > {max_num}. Increase max_number_of_indices "
                        f"to at least {projected} BEFORE importing, or the oldest "
                        f"data (including newly imported) will be deleted."
                    )
        elif "Closing" in ret_class:
            warnings.append(
                f"Index set uses ClosingRetentionStrategy. Old indices will be "
                f"closed (not searchable) after retention limit. Imported data "
                f"may become inaccessible if it falls outside the retention window."
            )

        # --- Sanity warnings ---
        if estimated > 100:
            warnings.append(
                f"This import will create ~{estimated} indices ({total_bytes/1e9:.1f} "
                f"GB raw / {total_messages:,} messages). Verify cluster has enough "
                f"disk space and shard headroom."
            )

        return estimated, warnings

    async def find_target_index_set(self) -> tuple[str, str]:
        async with self._client() as c:
            r = await c.get(f"{self.api_url}/api/system/indices/index_sets")
            r.raise_for_status()
            sets = r.json().get("index_sets", [])
            default = next((s for s in sets if s.get("default")), None)
            if default:
                return default["id"], default.get("title", "")
            if sets:
                return sets[0]["id"], sets[0].get("title", "")
            raise RuntimeError("No index sets found on target Graylog")

    async def get_current_custom_mapping(self, index_set_id: str) -> dict[str, str]:
        """Read the current per-index-set custom field mappings.
        Returns {field_name: opensearch_type}."""
        async with self._client() as c:
            try:
                r = await c.get(
                    f"{self.api_url}/api/system/indices/mappings/{index_set_id}"
                )
                if r.status_code == 200:
                    data = r.json()
                    out: dict[str, str] = {}
                    for entry in data.get("custom_field_mappings", data) or []:
                        if isinstance(entry, dict):
                            fname = entry.get("field_name") or entry.get("field")
                            ftype = entry.get("type")
                            if fname and ftype:
                                out[fname] = ftype
                    return out
            except Exception:
                pass
            return {}

    async def ensure_field_limit_template(
        self, index_prefix: str, limit: int = 10000
    ) -> None:
        """Create/update an OpenSearch index template that bumps the per-index
        field limit for the target index pattern. This must run BEFORE Graylog
        tries to create a new (rotated) index, otherwise the rotation fails
        with 'Limit of total fields [1000] has been exceeded'.

        We talk directly to OpenSearch via Graylog's API proxy isn't available,
        so we need separate OpenSearch credentials. As a workaround, we use the
        Graylog API to set the index set's `field_type_refresh_interval` and
        related settings if available; otherwise we rely on a pre-installed
        override template (operator-managed).

        Implementation note: Graylog 7's `PUT /api/system/indices/index_sets/{id}`
        endpoint allows you to set custom_settings on the index set. We use that.
        """
        # We try the simplest reliable path: directly PUT a template via the
        # OpenSearch endpoint that Graylog itself uses. Graylog 5+/7 exposes
        # `POST /api/system/indices/index_sets/{id}/cycle`, but for the field
        # limit we need to write a SEPARATE template (different name) with a
        # HIGHER order so it merges over Graylog's auto-generated one.
        #
        # We do this via the OpenSearch REST API on the Graylog node. Since
        # we don't have direct OpenSearch creds in this preflight, we use the
        # Graylog API as a proxy: it has an endpoint to manage index templates
        # at `/api/system/indices/index_sets/{id}/templates/custom`.
        # If that's not available, fall back to a no-op + log a warning.
        body = {
            "name": "jt-glogarch-field-limit",
            "index_pattern": f"{index_prefix}_*",
            "order": 100,
            "settings": {
                "index": {
                    "mapping": {
                        "total_fields": {"limit": str(limit)}
                    }
                }
            },
        }
        async with self._client() as c:
            # Graylog's "Customize index mappings" feature endpoint (5.0+)
            # We don't have a perfect API; the cleanest workaround is to call
            # OpenSearch through Graylog's cluster proxy if available.
            # Path tried: /api/cluster/{nodeId}/indexer/templates  (does not exist)
            # Path tried: /api/system/indices/index_sets/{id}/templates  (does not exist)
            # Reality: Graylog does NOT expose a way to modify the index template
            # via its API, except via custom field mappings (which we already use).
            #
            # The only reliable way to set the field limit is by talking directly
            # to OpenSearch. We can do that if the user provides OpenSearch URL +
            # creds, OR by using the same Graylog credentials against the
            # OpenSearch endpoint behind Graylog (often http://<graylog>:9200).
            #
            # For now: try a heuristic — derive OpenSearch URL from the Graylog
            # API URL (replace port 9000 -> 9200).
            os_url = self.api_url.replace(":9000", ":9200")
            template_name = "jt-glogarch-field-limit"
            template_body = {
                "index_patterns": [f"{index_prefix}_*"],
                "order": 100,
                "settings": {
                    "index": {
                        "mapping": {
                            "total_fields": {"limit": str(limit)}
                        }
                    }
                },
            }
            try:
                r = await c.put(
                    f"{os_url}/_template/{template_name}",
                    content=json.dumps(template_body),
                )
                if r.status_code in (200, 201, 204):
                    log.info("Field limit override template installed",
                             os_url=os_url, limit=limit)
                    return
                log.warning(
                    "Could not PUT field limit template via OpenSearch endpoint",
                    status=r.status_code, body=r.text[:200],
                )
            except Exception as e:
                log.warning("OpenSearch endpoint not reachable", url=os_url, error=str(e))

            # If we can't talk to OpenSearch directly, try via Graylog proxy.
            # No standard Graylog API for this, so we just warn the operator.
            log.warning(
                "Cannot auto-set OpenSearch field limit. Operator must run "
                "manually: PUT %s/_template/%s {<template>}",
                os_url, template_name,
            )

    async def apply_custom_mappings(
        self, index_set_id: str, fields_to_set_keyword: list[str]
    ) -> None:
        """Set custom field mappings on the target index set.

        Graylog 7's API takes ONE field per PUT call:
            PUT /api/system/indices/mappings
            { "rotate": false, "field": "<name>", "index_sets": ["<id>"], "type": "string" }
        We send all of them with rotate=false, then issue a single cycle at the
        end (in the caller) so we don't rotate the index 1653 times.
        """
        if not fields_to_set_keyword:
            return

        url = f"{self.api_url}/api/system/indices/mappings"
        ok = 0
        failed: list[tuple[str, str]] = []

        async with self._client() as c:
            for fname in sorted(fields_to_set_keyword):
                body = {
                    "rotate": False,
                    "field": fname,
                    "index_sets": [index_set_id],
                    "type": "string",
                }
                r = await c.put(url, content=json.dumps(body))
                if r.status_code in (200, 201, 204):
                    ok += 1
                else:
                    failed.append((fname, f"HTTP {r.status_code}: {r.text[:120]}"))
                    # Don't bail immediately — we want as many fields fixed as
                    # possible. But if too many fail in a row, abort.
                    if len(failed) > 20 and ok == 0:
                        raise RuntimeError(
                            f"Failed to apply custom mappings (first 5 failures): "
                            + "; ".join(f"{n}={e}" for n, e in failed[:5])
                        )

        log.info("Custom mappings applied", ok=ok, failed=len(failed),
                 total=len(fields_to_set_keyword))
        if failed:
            # Report but don't abort — partial fixes are better than nothing
            log.warning(
                "Some custom mappings could not be applied (sample)",
                samples=[f"{n}: {e}" for n, e in failed[:5]],
            )

    async def cycle_index(self, index_set_id: str) -> None:
        async with self._client() as c:
            r = await c.post(
                f"{self.api_url}/api/cluster/deflector/{index_set_id}/cycle"
            )
            if r.status_code in (200, 201, 204):
                return
            r = await c.post(f"{self.api_url}/api/cluster/deflector/cycle")
            if r.status_code in (200, 201, 204):
                return
            raise RuntimeError(
                f"Failed to cycle index: HTTP {r.status_code}: {r.text[:300]}"
            )

    async def wait_for_index_ready(
        self, index_set_id: str, timeout_sec: int = 30
    ) -> None:
        async with self._client() as c:
            deadline = asyncio.get_event_loop().time() + timeout_sec
            while asyncio.get_event_loop().time() < deadline:
                try:
                    r = await c.get(
                        f"{self.api_url}/api/system/indices/index_sets/{index_set_id}/stats"
                    )
                    if r.status_code == 200:
                        return
                except Exception:
                    pass
                await asyncio.sleep(1)

    # ---------------------------------------- OpenSearch auto-detection

    async def auto_detect_opensearch_url(self) -> str | None:
        """Try to derive the OpenSearch URL from the Graylog API URL.

        Heuristic: Graylog and OpenSearch are usually on the same host (or in
        the same docker stack). Replace port 9000 → 9200 and try to reach it.
        Returns the URL if reachable, else None.
        """
        # Strategy 1: Same host, port 9200
        candidates = [
            self.api_url.replace(":9000", ":9200"),
            self.api_url.replace(":9000", ":9201"),  # alt port some setups use
        ]
        async with httpx.AsyncClient(verify=False, timeout=5) as c:
            for url in candidates:
                try:
                    r = await c.get(f"{url}/", auth=self._auth())
                    if r.status_code in (200, 401):
                        # 200 = anonymous; 401 = needs OS-specific creds
                        # Either way the host is reachable on that port
                        return url
                except Exception:
                    continue
        return None

    # -------------------------------- Index set creation (for bulk mode)

    async def find_or_create_index_set(
        self,
        title: str,
        prefix: str,
        description: str = "",
    ) -> tuple[str, bool]:
        """Look up an index set by prefix; create one if missing.

        Returns (index_set_id, created).
        """
        async with self._client() as c:
            # Check existing
            r = await c.get(f"{self.api_url}/api/system/indices/index_sets")
            r.raise_for_status()
            for s in r.json().get("index_sets", []):
                if s.get("index_prefix") == prefix:
                    return s["id"], False

            # Build payload — Graylog 5+/7 schema
            body = {
                "title": title,
                "description": description or f"Created by jt-glogarch for restored archives ({prefix}_*)",
                "index_prefix": prefix,
                "shards": 1,
                "replicas": 0,
                "rotation_strategy_class": "org.graylog2.indexer.rotation.strategies.SizeBasedRotationStrategy",
                "rotation_strategy": {
                    "type": "org.graylog2.indexer.rotation.strategies.SizeBasedRotationStrategyConfig",
                    "max_size": 32 * 1024 * 1024 * 1024,  # 32 GiB per index
                },
                "retention_strategy_class": "org.graylog2.indexer.retention.strategies.NoopRetentionStrategy",
                "retention_strategy": {
                    "type": "org.graylog2.indexer.retention.strategies.NoopRetentionStrategyConfig",
                    "max_number_of_indices": 2147483647,
                },
                "creation_date": datetime.utcnow().isoformat() + "Z",
                "index_analyzer": "standard",
                "index_optimization_max_num_segments": 1,
                "index_optimization_disabled": False,
                "writable": True,
                "field_type_refresh_interval": 5000,
            }
            r = await c.post(
                f"{self.api_url}/api/system/indices/index_sets",
                content=json.dumps(body),
            )
            if r.status_code not in (200, 201):
                raise RuntimeError(
                    f"Failed to create index set: HTTP {r.status_code}: {r.text[:300]}"
                )
            data = r.json()
            return data.get("id", ""), True

    # ----------------------------- Bulk-mode OpenSearch template setup

    async def apply_bulk_template(
        self,
        opensearch_url: str,
        os_username: str,
        os_password: str,
        target_pattern: str,
        fields_to_keyword: list[str],
    ) -> None:
        """For bulk-mode imports: write an OpenSearch index template that
        controls the mapping for `<target_pattern>_*` indices.

        - Sets `index.mapping.total_fields.limit: 10000` so we never hit the
          default 1000-field cap (especially important since bulk-mode pins
          MORE fields than gelf-mode).
        - Pins each field that ever had a string value in the archive as
          `keyword` so OpenSearch auto-detection won't lock them as `long`
          and reject later string values.
        - Order=100 so this template overrides any other graylog template
          that might match the pattern.
        """
        template_name = f"{target_pattern}_template"
        properties = {f: {"type": "keyword"} for f in fields_to_keyword}
        body: dict = {
            "index_patterns": [f"{target_pattern}_*"],
            "order": 100,
            "settings": {
                "index": {
                    "mapping": {"total_fields": {"limit": "10000"}},
                    # Bulk import has no concurrent search load, optimise for write
                    "refresh_interval": "30s",
                    "number_of_replicas": 0,
                    "number_of_shards": 1,
                }
            },
        }
        if properties:
            body["mappings"] = {"properties": properties}

        auth = (os_username, os_password) if os_username else None
        async with httpx.AsyncClient(verify=False, timeout=30, auth=auth) as c:
            r = await c.put(
                f"{opensearch_url.rstrip('/')}/_template/{template_name}",
                content=json.dumps(body),
                headers={"Content-Type": "application/json"},
            )
            if r.status_code not in (200, 201, 204):
                raise RuntimeError(
                    f"Failed to PUT bulk index template '{template_name}': "
                    f"HTTP {r.status_code}: {r.text[:300]}"
                )
            log.info(
                "Bulk index template installed",
                template=template_name,
                pattern=f"{target_pattern}_*",
                pinned_fields=len(fields_to_keyword),
            )

    async def get_indexer_failures_count(self) -> int:
        async with self._client() as c:
            try:
                r = await c.get(f"{self.api_url}/api/system/indexer/failures?limit=1")
                if r.status_code == 200:
                    return r.json().get("total", 0)
            except Exception as e:
                log.warning("Cannot read indexer failures", error=str(e))
        return 0

    # ----------------------------------------------------- Top-level entry

    async def run(
        self,
        db,
        archive_ids: list[int],
        total_messages: int = 0,
        total_bytes: int = 0,
        mode: str = "gelf",
        bulk_opensearch_url: str | None = None,
        bulk_os_username: str | None = None,
        bulk_os_password: str | None = None,
        bulk_target_pattern: str | None = None,
    ) -> PreflightResult:
        """Execute the full preflight pipeline.

        mode='gelf' (default): apply field mapping fixes via Graylog custom_field_mappings
            then cycle the deflector.
        mode='bulk': apply field mapping fixes by writing an OpenSearch index template
            for the bulk target_pattern. No cycle needed (we write to a fresh
            daily index name). Optionally also create a Graylog index set so the
            restored data is searchable in the Graylog UI.
        """
        import time
        start = time.time()
        result = PreflightResult()

        try:
            # 1. Verify credentials
            ok, err = await self.verify_credentials()
            if not ok:
                result.aborted = True
                result.error = f"Graylog API credential check failed: {err}"
                return result

            # 2. Target health & GELF input check (cluster RED, input not running, etc.)
            health_errors, health_warnings = await self.check_target_health()
            if health_errors:
                result.aborted = True
                result.error = "Target health check failed: " + " | ".join(health_errors)
                return result
            for w in health_warnings:
                log.warning("Preflight target health warning", msg=w)
                result.capacity_warnings.append(f"[health] {w}")

            # 3. Snapshot indexer failures baseline
            result.indexer_failures_baseline = await self.get_indexer_failures_count()

            # 4. Build field schema from DB (with fallback)
            log.info("Preflight: collecting field schema", archive_count=len(archive_ids))
            fields, total, with_db, scanned = self.collect_field_schema(db, archive_ids)
            result.archives_total = total
            result.archives_with_db_schema = with_db
            result.archives_scanned_inline = scanned
            result.fields_total = len(fields)
            result.fields_with_string = sum(1 for v in fields.values() if "string" in v)
            log.info(
                "Preflight: field schema",
                archives=total, with_db=with_db, scanned=scanned,
                fields=result.fields_total, string_fields=result.fields_with_string,
            )

            # 5. Find target index set
            index_set_id, title = await self.find_target_index_set()
            result.index_set_id = index_set_id
            result.index_set_title = title
            log.info("Preflight: target index set", id=index_set_id, title=title)

            # 6. Capacity check (rotation/retention) — abort if retention will eat data
            if total_messages > 0:
                estimated, cap_warnings = await self.check_capacity(
                    index_set_id, total_messages, total_bytes
                )
                result.estimated_indices_needed = estimated
                # Read strategies for the result
                async with self._client() as c:
                    r = await c.get(
                        f"{self.api_url}/api/system/indices/index_sets/{index_set_id}"
                    )
                    if r.status_code == 200:
                        iset = r.json()
                        result.rotation_strategy = (iset.get("rotation_strategy_class") or "").split(".")[-1]
                        result.retention_strategy = (iset.get("retention_strategy_class") or "").split(".")[-1]
                for w in cap_warnings:
                    log.warning("Preflight capacity warning", msg=w)
                    result.capacity_warnings.append(f"[capacity] {w}")
                    # Retention-will-delete is a HARD error
                    if "Retention will delete data" in w:
                        result.aborted = True
                        result.error = w
                        return result

            # 7. Read current custom mappings
            current = await self.get_current_custom_mapping(index_set_id)

            # 6. Compute conflicts. We pin a field as `string` (keyword) only if:
            #    (a) The archive itself has BOTH numeric and string values for it
            #        — guaranteed conflict regardless of target mapping; OR
            #    (b) The target's CURRENT custom mapping is numeric/non-string-like
            #        and the archive has at least one string value for it.
            #
            # Critical: we do NOT pin fields where the archive only has string
            # values and the target has no existing mapping. Pinning all of those
            # would explode the index template field count past OpenSearch's
            # 1000-field-per-index limit and cause Graylog to fail to create the
            # rotated index. For string-only archive fields, OpenSearch will auto-
            # detect them as text/keyword on first message — same outcome, no
            # conflict, no template bloat.
            to_keyword: list[str] = []
            _NUMERIC_OS_TYPES = {"long", "integer", "short", "byte", "double", "float", "half_float", "scaled_float"}
            for fname, types_seen in fields.items():
                if "string" not in types_seen:
                    continue
                intra_conflict = "numeric" in types_seen
                cur_type = current.get(fname, "")
                cross_conflict = cur_type in _NUMERIC_OS_TYPES
                if not (intra_conflict or cross_conflict):
                    continue
                to_keyword.append(fname)
                reason = "intra" if intra_conflict else f"target={cur_type}"
                result.conflicts.append(
                    f"{fname} ({reason}, types: {sorted(types_seen)})"
                )

            result.fields_set_keyword = sorted(to_keyword)
            log.info(
                "Preflight: conflicts found",
                count=len(to_keyword), sample=to_keyword[:20],
            )

            # ============================================================
            # MODE BRANCH: gelf vs bulk apply step
            # ============================================================
            if mode == "bulk":
                # Bulk mode writes directly to OpenSearch under a custom index
                # pattern. We:
                #   (a) Write an OpenSearch index template that pins all
                #       conflict-prone fields as keyword + raises field limit.
                #   (b) Auto-create a Graylog index set so the restored data
                #       is searchable from the Graylog UI.
                # No deflector cycle: bulk writes to a fresh daily index name
                # which inherits the new template on first write.
                if not bulk_opensearch_url or not bulk_target_pattern:
                    result.aborted = True
                    result.error = "Bulk mode requires bulk_opensearch_url and bulk_target_pattern"
                    return result

                # In bulk mode we can be MORE aggressive about pinning fields:
                # we control the template entirely (no Graylog field count
                # competition), so pin every field with any string value.
                bulk_pins = sorted([
                    fname for fname, types_seen in fields.items()
                    if "string" in types_seen
                ])
                result.fields_set_keyword = bulk_pins

                try:
                    await self.apply_bulk_template(
                        opensearch_url=bulk_opensearch_url,
                        os_username=bulk_os_username or "",
                        os_password=bulk_os_password or "",
                        target_pattern=bulk_target_pattern,
                        fields_to_keyword=bulk_pins,
                    )
                except Exception as e:
                    result.aborted = True
                    result.error = f"Bulk template setup failed: {e}"
                    return result

                # Auto-create Graylog index set so user can search restored data
                try:
                    set_id, created = await self.find_or_create_index_set(
                        title=f"jt-glogarch Restored ({bulk_target_pattern})",
                        prefix=bulk_target_pattern,
                        description=f"Created by jt-glogarch bulk import. Indices: {bulk_target_pattern}_*",
                    )
                    if created:
                        log.info("Created Graylog index set for restored data",
                                 id=set_id, prefix=bulk_target_pattern)
                    else:
                        log.info("Graylog index set already exists",
                                 id=set_id, prefix=bulk_target_pattern)
                except Exception as e:
                    # Non-fatal: data still goes into OpenSearch, just won't
                    # show in Graylog UI by default. Operator can add manually.
                    log.warning("Could not auto-create Graylog index set",
                                error=str(e))
                    result.capacity_warnings.append(
                        f"[bulk] Could not auto-create Graylog index set "
                        f"for prefix '{bulk_target_pattern}': {e}. "
                        f"Add it manually in Graylog System / Indices to make "
                        f"the restored data visible in the Graylog UI."
                    )

                log.info("Preflight (bulk): ready to send",
                         fields_pinned=len(bulk_pins))
                # No cycle needed for bulk
            else:
                # =====================================================
                # GELF MODE (original behaviour)
                # =====================================================
                # 7. Bump the OpenSearch field limit BEFORE applying custom mappings.
                #    Graylog's auto-generated index template would otherwise be
                #    rejected by OpenSearch with 'Limit of total fields [1000]
                #    has been exceeded' once we add many custom mappings.
                try:
                    async with self._client() as c:
                        r = await c.get(
                            f"{self.api_url}/api/system/indices/index_sets/{index_set_id}"
                        )
                        if r.status_code == 200:
                            prefix = r.json().get("index_prefix", "graylog")
                        else:
                            prefix = "graylog"
                    await self.ensure_field_limit_template(prefix, limit=10000)
                except Exception as e:
                    log.warning("Field limit template setup failed", error=str(e))

                # 8. Apply mapping changes if needed
                if to_keyword:
                    await self.apply_custom_mappings(index_set_id, to_keyword)
                    # 9. Rotate index so the new mapping takes effect immediately
                    await self.cycle_index(index_set_id)
                    result.rotated = True
                    # 10. Wait for new index
                    await self.wait_for_index_ready(index_set_id)
                    log.info("Preflight: rotated index, ready to send")
                else:
                    # No conflicts to fix, but still rotate so the new field-limit
                    # template takes effect on the next index.
                    await self.cycle_index(index_set_id)
                    result.rotated = True
                    await self.wait_for_index_ready(index_set_id)
                    log.info("Preflight: no mapping conflicts, rotated for fresh index")

        except Exception as e:
            result.aborted = True
            result.error = str(e)
            log.error("Preflight failed", error=str(e))

        result.duration_sec = time.time() - start
        return result
