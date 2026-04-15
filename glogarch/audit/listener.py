"""UDP syslog listener for receiving nginx audit logs."""

from __future__ import annotations

import asyncio
import re
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from glogarch.audit.parser import parse_syslog_payload, parse_nginx_json, process_raw_entry, is_noise
from glogarch.core.config import ApiAuditConfig, Settings
from glogarch.core.database import ArchiveDB
from glogarch.utils.logging import get_logger

log = get_logger("audit.listener")


class AuditSyslogProtocol(asyncio.DatagramProtocol):
    """asyncio UDP protocol for receiving syslog messages."""

    def __init__(self, listener: "AuditSyslogListener"):
        self.listener = listener

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        self.listener.handle_datagram(data, addr)


class AuditSyslogListener:
    """Listens for nginx syslog UDP audit messages, parses and stores them."""

    def __init__(self, config: ApiAuditConfig, db: ArchiveDB, settings: Settings):
        self.config = config
        self.db = db
        self.settings = settings
        self.transport: asyncio.DatagramTransport | None = None
        self.allowed_ips: set[str] = set()
        self.received_count: int = 0
        self.rejected_count: int = 0
        self.last_received_at: str = ""
        self._batch: list[dict] = []
        self._batch_lock = asyncio.Lock()
        self._flush_task: asyncio.Task | None = None
        self._refresh_task: asyncio.Task | None = None
        self._token_cache: dict[str, str] = {}  # token_prefix → username
        self._token_tried: set[str] = set()  # prefixes already tried async resolve
        self._token_cache_task: asyncio.Task | None = None
        self._session_cache: dict[str, str] = {}  # session_id → username
        self._resource_cache: dict[str, str] = {}  # resource_id → name

    async def start(self) -> None:
        """Start the UDP listener + periodic tasks."""
        if not self.config.enabled:
            log.info("API Audit disabled")
            return

        # Build initial allowed IPs
        self._build_allowed_ips_from_config()
        # Try to get cluster nodes (may fail if Graylog not ready)
        try:
            await self._refresh_allowed_ips()
        except Exception as e:
            log.warning("Could not refresh cluster IPs on startup", error=str(e))

        loop = asyncio.get_event_loop()
        transport, _ = await loop.create_datagram_endpoint(
            lambda: AuditSyslogProtocol(self),
            local_addr=("0.0.0.0", self.config.listen_port),
        )
        self.transport = transport
        log.info("API Audit listener started",
                 port=self.config.listen_port,
                 allowed_ips=sorted(self.allowed_ips))

        # Periodic flush (every 5 seconds)
        self._flush_task = asyncio.ensure_future(self._periodic_flush())
        # Periodic IP refresh (every 5 minutes)
        self._refresh_task = asyncio.ensure_future(self._periodic_refresh())
        # Token → username cache (every 10 minutes)
        self._token_cache_task = asyncio.ensure_future(self._periodic_token_cache())
        # Heartbeat: detect silent audit failure
        self._heartbeat_task = asyncio.ensure_future(self._periodic_heartbeat())

    async def stop(self) -> None:
        if self.transport:
            self.transport.close()
            self.transport = None
        if self._flush_task:
            self._flush_task.cancel()
        if hasattr(self, '_heartbeat_task') and self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._refresh_task:
            self._refresh_task.cancel()
        if self._token_cache_task:
            self._token_cache_task.cancel()
        # Final flush
        await self._flush_batch()
        log.info("API Audit listener stopped")

    def _build_allowed_ips_from_config(self) -> None:
        """Extract IPs from config.yaml servers list."""
        for srv in self.settings.servers:
            try:
                parsed = urlparse(srv.url)
                if parsed.hostname:
                    self.allowed_ips.add(parsed.hostname)
            except Exception:
                pass
        # Always allow localhost
        self.allowed_ips.add("127.0.0.1")
        self.allowed_ips.add("::1")

    async def _refresh_allowed_ips(self) -> None:
        """Query Graylog Cluster API to get all node IPs."""
        import httpx
        for srv in self.settings.servers:
            try:
                auth = None
                if srv.auth_token:
                    auth = (srv.auth_token, "token")
                elif srv.username:
                    auth = (srv.username, srv.password or "")
                async with httpx.AsyncClient(
                    verify=srv.verify_ssl, timeout=10, auth=auth,
                    headers={"Accept": "application/json"},
                ) as client:
                    r = await client.get(f"{srv.url.rstrip('/')}/api/system/cluster/nodes")
                    if r.status_code == 200:
                        nodes = r.json()
                        for node_data in (nodes.values() if isinstance(nodes, dict) else []):
                            addr = node_data.get("transport_address", "")
                            try:
                                host = urlparse(f"http://{addr}").hostname or addr.split(":")[0]
                                if host:
                                    self.allowed_ips.add(host)
                            except Exception:
                                pass
            except Exception:
                pass

    _HEARTBEAT_INTERVAL = 300   # check every 5 minutes
    _HEARTBEAT_THRESHOLD = 600  # alert if no data for 10 minutes
    _heartbeat_alerted = False

    async def _periodic_heartbeat(self) -> None:
        """Detect silent audit failure: Graylog is up but no syslog received."""
        await asyncio.sleep(self._HEARTBEAT_THRESHOLD)  # initial grace period
        while True:
            await asyncio.sleep(self._HEARTBEAT_INTERVAL)
            try:
                # Skip if we never received anything (nginx not configured yet)
                if not self.last_received_at:
                    continue

                # Check how long since last syslog
                from datetime import datetime, timezone
                last = datetime.fromisoformat(self.last_received_at.replace("Z", "+00:00"))
                age_seconds = (datetime.now(timezone.utc) - last).total_seconds()

                if age_seconds < self._HEARTBEAT_THRESHOLD:
                    # All good — reset alert flag
                    if self._heartbeat_alerted:
                        self._heartbeat_alerted = False
                        log.info("Audit syslog resumed")
                    continue

                # Stale — check if Graylog is actually up
                graylog_up = await self._check_graylog_health()
                if not graylog_up:
                    continue  # Graylog is down, not an audit failure

                # Graylog is up but no syslog → audit pipeline broken
                if not self._heartbeat_alerted:
                    self._heartbeat_alerted = True
                    age_min = int(age_seconds // 60)
                    log.warning("Audit heartbeat alert: no syslog received",
                                last_received=self.last_received_at,
                                age_minutes=age_min)
                    try:
                        from glogarch.notify.sender import send_notification, NotifyEvent
                        from glogarch.notify.sender import _t
                        await send_notification(
                            NotifyEvent.AUDIT_ALERT,
                            _t("audit_alert_title"),
                            _t("audit_alert_body", minutes=age_min, last=self.last_received_at),
                        )
                    except Exception:
                        pass
            except Exception as e:
                log.debug("Heartbeat check failed", error=str(e))

    async def _check_graylog_health(self) -> bool:
        """Quick check if Graylog API is reachable."""
        import httpx
        for srv in self.settings.servers:
            try:
                auth = None
                if srv.auth_token:
                    auth = (srv.auth_token, "token")
                elif srv.username:
                    auth = (srv.username, srv.password or "")
                async with httpx.AsyncClient(
                    verify=srv.verify_ssl, timeout=5, auth=auth,
                    headers={"Accept": "application/json"},
                ) as client:
                    r = await client.get(f"{srv.url.rstrip('/')}/api/system")
                    return r.status_code == 200
            except Exception:
                pass
        return False

    async def _periodic_refresh(self) -> None:
        """Refresh allowed IPs every 5 minutes."""
        while True:
            await asyncio.sleep(300)
            try:
                old_count = len(self.allowed_ips)
                await self._refresh_allowed_ips()
                if len(self.allowed_ips) != old_count:
                    log.info("Allowed IPs refreshed", count=len(self.allowed_ips))
            except Exception:
                pass

    async def _refresh_token_cache(self) -> None:
        """Query Graylog Users API to build token_prefix → username map.

        Strategy:
        1. Get all users from GET /api/users
        2. For each user with tokens, try per-user endpoint GET /api/users/{name}/tokens
           which returns actual token values (the user list endpoint may not)
        3. Map token_value[:8] → username
        """
        import httpx
        for srv in self.settings.servers:
            try:
                auth = None
                if srv.auth_token:
                    auth = (srv.auth_token, "token")
                elif srv.username:
                    auth = (srv.username, srv.password or "")
                async with httpx.AsyncClient(
                    verify=srv.verify_ssl, timeout=10, auth=auth,
                    headers={"Accept": "application/json"},
                ) as client:
                    r = await client.get(f"{srv.url.rstrip('/')}/api/users")
                    if r.status_code != 200:
                        continue
                    users = r.json().get("users", [])
                    for user in users:
                        uname = user.get("username", "")
                        if not uname:
                            continue
                        # Try tokens from user list first (fast path)
                        got_token = False
                        for tok in user.get("tokens", []):
                            tv = tok.get("token", "")
                            if tv and len(tv) >= 8:
                                self._token_cache[tv[:8]] = uname
                                got_token = True
                        # Fallback: per-user token endpoint returns actual values
                        if not got_token and user.get("tokens"):
                            try:
                                tr = await client.get(
                                    f"{srv.url.rstrip('/')}/api/users/{uname}/tokens")
                                if tr.status_code == 200:
                                    tdata = tr.json()
                                    tlist = tdata if isinstance(tdata, list) else tdata.get("tokens", [])
                                    for tok in tlist:
                                        tv = tok.get("token", "")
                                        if tv and len(tv) >= 8:
                                            self._token_cache[tv[:8]] = uname
                            except Exception:
                                pass
                self._token_tried.clear()  # reset async resolve attempts
                log.debug("Token cache refreshed", entries=len(self._token_cache))
                return  # One server is enough
            except Exception:
                pass

    async def _refresh_ip_user_cache(self) -> None:
        """Build IP → username cache and backfill records without username.

        Strategy:
        1. Query Graylog API for human users (exclude system accounts)
        2. If only 1 human user → use as default for all records
        3. If multiple → use login history to map IP → user
        4. Backfill DB records that have no username
        """
        try:
            # 1. Get human users from Graylog API
            human_users = await self._get_human_users()

            # 2. If only 1 human user, use as default
            if len(human_users) == 1:
                default_user = human_users[0]
                if not self._session_cache.get("_default_user"):
                    log.info("Single admin user detected, using as default",
                             user=default_user)
                self._session_cache["_default_user"] = default_user
            elif human_users:
                self._session_cache.pop("_default_user", None)

            # 3. Build from DB: login records that have username in body
            rows = self.db.conn.execute(
                "SELECT DISTINCT remote_addr, username FROM api_audit "
                "WHERE username != '' AND username != '-' "
                "ORDER BY id DESC LIMIT 200"
            ).fetchall()
            for r in rows:
                ip = r["remote_addr"]
                user = r["username"]
                if ip and user:
                    self._session_cache[f"ip:{ip}"] = user

            # 4. Backfill DB records without username
            backfill_count = 0
            for ip_key, user in list(self._session_cache.items()):
                if not ip_key.startswith("ip:"):
                    continue
                ip = ip_key[3:]
                cnt = self.db.conn.execute(
                    "UPDATE api_audit SET username = ? "
                    "WHERE remote_addr = ? AND (username = '' OR username = '-')",
                    (user, ip)
                ).rowcount
                backfill_count += cnt

            # 5. Backfill remaining with default user
            default = self._session_cache.get("_default_user", "")
            if default:
                cnt = self.db.conn.execute(
                    "UPDATE api_audit SET username = ? "
                    "WHERE username = '' OR username = '-'",
                    (default,)
                ).rowcount
                backfill_count += cnt

            if backfill_count:
                self.db.conn.commit()
                log.info("Backfilled audit usernames", count=backfill_count)

        except Exception as e:
            log.warning("IP→user cache refresh failed", error=str(e))

    async def _get_human_users(self) -> list[str]:
        """Query Graylog API for human (non-system) user accounts.

        Includes external (LDAP/SSO) users — they are real users who make API calls.
        Only filters out Graylog built-in system service accounts.
        """
        import httpx
        system_users = {"graylog-sidecar", "graylog-forwarder", "graylog-report",
                        "graylog-datanode", "graylog-web"}
        for srv in self.settings.servers:
            try:
                auth = None
                if srv.auth_token:
                    auth = (srv.auth_token, "token")
                elif srv.username:
                    auth = (srv.username, srv.password or "")
                async with httpx.AsyncClient(
                    verify=srv.verify_ssl, timeout=10, auth=auth,
                    headers={"Accept": "application/json"},
                ) as client:
                    r = await client.get(f"{srv.url.rstrip('/')}/api/users")
                    if r.status_code == 200:
                        users = []
                        for u in r.json().get("users", []):
                            name = u.get("username", "")
                            if name and name not in system_users:
                                users.append(name)
                        return users
            except Exception:
                pass
        return []

    async def _periodic_token_cache(self) -> None:
        """Refresh caches: resources every 5 min, IP→user every 2 min, tokens every 10 min."""
        # Initial load — build all caches immediately on startup
        try:
            await self._refresh_resource_cache()
        except Exception:
            pass
        try:
            await self._refresh_token_cache()
        except Exception:
            pass
        try:
            await self._refresh_ip_user_cache()
        except Exception:
            pass
        cycle = 0
        while True:
            await asyncio.sleep(120)  # every 2 minutes
            cycle += 1
            try:
                await self._refresh_ip_user_cache()
            except Exception:
                pass
            if cycle % 3 == 0:  # every 6 minutes
                try:
                    await self._refresh_resource_cache()
                except Exception:
                    pass
            if cycle % 5 == 0:  # every 10 minutes
                try:
                    await self._refresh_token_cache()
                except Exception:
                    pass

    async def _resolve_session(self, session_id: str, entry: dict) -> None:
        """Resolve a Graylog session ID to a username via API.

        Uses the session ID itself as Basic Auth credentials to query
        GET /api/system/sessions — Graylog returns the username for that session.
        Falls back to default_user if resolution fails.
        """
        import httpx
        for srv in self.settings.servers:
            try:
                # Use session ID as Basic Auth: base64(sessionId:session)
                async with httpx.AsyncClient(
                    verify=srv.verify_ssl, timeout=5,
                    auth=(session_id, "session"),
                    headers={"Accept": "application/json"},
                ) as client:
                    r = await client.get(f"{srv.url.rstrip('/')}/api/system/sessions")
                    if r.status_code == 200:
                        data = r.json()
                        user = data.get("username", "")
                        if user and data.get("is_valid"):
                            self._session_cache[session_id] = user
                            entry["username"] = user
                            return
            except Exception:
                pass
        # Fallback: use IP cache or default user
        remote = entry.get("remote_addr", "")
        ip_user = self._session_cache.get(f"ip:{remote}", "")
        default = self._session_cache.get("_default_user", "")
        fallback = ip_user or default
        if fallback and entry.get("username") == session_id:
            entry["username"] = fallback

    def _resolve_target_name(self, uri: str) -> str:
        """Extract resource ID from URI and resolve to human-readable name."""
        # Match patterns like /api/.../inputs/XXXX or /api/.../inputstates/XXXX
        m = re.search(r"/api/(?:system|cluster)/(?:inputs|inputstates)/([a-f0-9]{24})", uri)
        if m:
            rid = m.group(1)
            return self._resource_cache.get(f"input:{rid}", f"input:{rid[:8]}...")
        m = re.search(r"/api/streams/([a-f0-9]{24})", uri)
        if m:
            rid = m.group(1)
            return self._resource_cache.get(f"stream:{rid}", f"stream:{rid[:8]}...")
        m = re.search(r"/api/users/([a-f0-9]{24})(?:/|$)", uri)
        if m:
            rid = m.group(1)
            return self._resource_cache.get(f"user:{rid}", rid)
        m = re.search(r"/api/users/([^/]+?)(?:/|$)", uri)
        if m and m.group(1) not in ("tokens",):
            return m.group(1)  # username in URI (e.g. /api/users/admin)
        m = re.search(r"/api/system/indices/index_sets/([a-f0-9]{24})", uri)
        if m:
            rid = m.group(1)
            return self._resource_cache.get(f"indexset:{rid}", f"indexset:{rid[:8]}...")
        m = re.search(r"/api/events/definitions/([a-f0-9]{24})", uri)
        if m:
            rid = m.group(1)
            return self._resource_cache.get(f"event:{rid}", f"event:{rid[:8]}...")
        m = re.search(r"/api/views/([a-f0-9]{24})", uri)
        if m:
            rid = m.group(1)
            return self._resource_cache.get(f"view:{rid}", f"view:{rid[:8]}...")
        m = re.search(r"/api/system/pipelines/(pipeline|rule)/([a-f0-9]{24})", uri)
        if m:
            kind, rid = m.group(1), m.group(2)
            return self._resource_cache.get(f"pipeline_{kind}:{rid}", f"{kind}:{rid[:8]}...")
        m = re.search(r"/api/system/lookup/(?:tables|adapters|caches)/([a-f0-9]{24}|[^/]+)", uri)
        if m:
            rid = m.group(1)
            return self._resource_cache.get(f"lookup:{rid}", rid)
        m = re.search(r"/api/events/notifications/([a-f0-9]{24})", uri)
        if m:
            rid = m.group(1)
            return self._resource_cache.get(f"event_notif:{rid}", f"notif:{rid[:8]}...")
        # Outputs
        m = re.search(r"/api/system/outputs/([a-f0-9]{24})", uri)
        if m:
            rid = m.group(1)
            return self._resource_cache.get(f"output:{rid}", f"output:{rid[:8]}...")
        # Deflector cycle contains index set ID
        m = re.search(r"/api/(?:system|cluster)/deflector/([a-f0-9]{24})/cycle", uri)
        if m:
            rid = m.group(1)
            return self._resource_cache.get(f"indexset:{rid}", f"indexset:{rid[:8]}...")
        # GRN in share URLs: grn::::dashboard:ID, grn::::stream:ID, etc.
        m = re.search(r"grn::::(\w+):\s*([a-f0-9]{24})", uri)
        if m:
            rtype, rid = m.group(1), m.group(2)
            cache_map = {
                "dashboard": f"view:{rid}",
                "search": f"view:{rid}",
                "stream": f"stream:{rid}",
                "event_definition": f"event:{rid}",
                "notification": f"event_notif:{rid}",
            }
            cache_key = cache_map.get(rtype, "")
            if cache_key:
                return self._resource_cache.get(cache_key, f"{rtype}:{rid[:8]}...")
            return f"{rtype}:{rid[:8]}..."
        return ""

    async def _refresh_resource_cache(self) -> None:
        """Cache Graylog resource IDs → names (inputs, streams, etc.)."""
        import httpx
        for srv in self.settings.servers:
            try:
                auth = None
                if srv.auth_token:
                    auth = (srv.auth_token, "token")
                elif srv.username:
                    auth = (srv.username, srv.password or "")
                async with httpx.AsyncClient(
                    verify=srv.verify_ssl, timeout=10, auth=auth,
                    headers={"Accept": "application/json"},
                ) as client:
                    # Inputs
                    r = await client.get(f"{srv.url.rstrip('/')}/api/system/inputs")
                    if r.status_code == 200:
                        for inp in r.json().get("inputs", []):
                            self._resource_cache[f"input:{inp['id']}"] = inp.get("title", inp["id"])
                    # Streams
                    r = await client.get(f"{srv.url.rstrip('/')}/api/streams")
                    if r.status_code == 200:
                        for s in r.json().get("streams", []):
                            self._resource_cache[f"stream:{s['id']}"] = s.get("title", s["id"])
                    # Index sets
                    r = await client.get(f"{srv.url.rstrip('/')}/api/system/indices/index_sets")
                    if r.status_code == 200:
                        for s in r.json().get("index_sets", []):
                            self._resource_cache[f"indexset:{s['id']}"] = s.get("title", s["id"])
                    # Views / Dashboards
                    r = await client.get(f"{srv.url.rstrip('/')}/api/views?per_page=100")
                    if r.status_code == 200:
                        for v in r.json().get("views", r.json().get("elements", [])):
                            self._resource_cache[f"view:{v['id']}"] = v.get("title", v["id"])
                    # Lookup tables
                    r = await client.get(f"{srv.url.rstrip('/')}/api/system/lookup/tables?per_page=100")
                    if r.status_code == 200:
                        for t in r.json().get("lookup_tables", []):
                            self._resource_cache[f"lookup:{t['id']}"] = t.get("title", t["id"])
                    # Pipelines
                    r = await client.get(f"{srv.url.rstrip('/')}/api/system/pipelines/pipeline")
                    if r.status_code == 200:
                        for p in (r.json() if isinstance(r.json(), list) else []):
                            self._resource_cache[f"pipeline_pipeline:{p['id']}"] = p.get("title", p["id"])
                    # Pipeline rules
                    r = await client.get(f"{srv.url.rstrip('/')}/api/system/pipelines/rule")
                    if r.status_code == 200:
                        for p in (r.json() if isinstance(r.json(), list) else []):
                            self._resource_cache[f"pipeline_rule:{p['id']}"] = p.get("title", p["id"])
                    # Event definitions
                    r = await client.get(f"{srv.url.rstrip('/')}/api/events/definitions?per_page=100")
                    if r.status_code == 200:
                        for e in r.json().get("event_definitions", []):
                            self._resource_cache[f"event:{e['id']}"] = e.get("title", e["id"])
                    # Event notifications
                    r = await client.get(f"{srv.url.rstrip('/')}/api/events/notifications?per_page=100")
                    if r.status_code == 200:
                        for n in r.json().get("notifications", []):
                            self._resource_cache[f"event_notif:{n['id']}"] = n.get("title", n["id"])
                    # Outputs
                    r = await client.get(f"{srv.url.rstrip('/')}/api/system/outputs")
                    if r.status_code == 200:
                        for o in r.json().get("outputs", []):
                            self._resource_cache[f"output:{o['id']}"] = o.get("title", o["id"])
                    # Users (ID → username, for share grantee resolution)
                    r = await client.get(f"{srv.url.rstrip('/')}/api/users")
                    if r.status_code == 200:
                        for u in r.json().get("users", []):
                            uid = u.get("id", "")
                            uname = u.get("username", "")
                            if uid and uname:
                                full = u.get("full_name") or uname
                                self._resource_cache[f"user:{uid}"] = full
                    log.debug("Resource cache refreshed", total=len(self._resource_cache))
                return
            except Exception:
                pass

    def _resolve_token_username(self, username: str) -> str:
        """If username is token:XXXXXXXX..., try to resolve from cache."""
        if not username.startswith("token:"):
            return username
        prefix = username[6:].rstrip(".")  # "token:abcd1234..." → "abcd1234"
        resolved = self._token_cache.get(prefix)
        if resolved:
            return f"{resolved} (token)"
        return username

    async def _resolve_token_via_api(self, full_token: str, entry: dict) -> None:
        """Resolve unresolved token by querying per-user token endpoints."""
        import httpx
        prefix = full_token[:8]
        if prefix in self._token_tried:
            return
        self._token_tried.add(prefix)
        for srv in self.settings.servers:
            try:
                auth = None
                if srv.auth_token:
                    auth = (srv.auth_token, "token")
                elif srv.username:
                    auth = (srv.username, srv.password or "")
                async with httpx.AsyncClient(
                    verify=srv.verify_ssl, timeout=10, auth=auth,
                    headers={"Accept": "application/json"},
                ) as client:
                    r = await client.get(f"{srv.url.rstrip('/')}/api/users")
                    if r.status_code != 200:
                        continue
                    for user in r.json().get("users", []):
                        uname = user.get("username", "")
                        if not uname:
                            continue
                        tr = await client.get(
                            f"{srv.url.rstrip('/')}/api/users/{uname}/tokens")
                        if tr.status_code != 200:
                            continue
                        tdata = tr.json()
                        tlist = tdata if isinstance(tdata, list) else tdata.get("tokens", [])
                        for tok in tlist:
                            tv = tok.get("token", "")
                            if tv and len(tv) >= 8 and tv[:8] == prefix:
                                self._token_cache[prefix] = uname
                                entry["username"] = f"{uname} (token)"
                                log.info("Token resolved via API", user=uname)
                                return
            except Exception:
                pass

    async def _periodic_flush(self) -> None:
        """Flush batch to DB every 5 seconds."""
        while True:
            await asyncio.sleep(5)
            await self._flush_batch()

    async def _flush_batch(self) -> None:
        """Write accumulated entries to DB."""
        async with self._batch_lock:
            if not self._batch:
                return
            batch = self._batch[:]
            self._batch.clear()
        try:
            count = self.db.insert_api_audit_batch(batch)
            if count:
                log.debug("Flushed audit entries", count=count)

                # Check for sensitive operations and notify
                if self.config.alert_sensitive:
                    sensitive = [e for e in batch if e.get("is_sensitive")]
                    if sensitive:
                        await self._notify_sensitive(sensitive)
        except Exception as e:
            log.error("Failed to flush audit batch", error=str(e))

    async def _notify_sensitive(self, entries: list[dict]) -> None:
        """Send notification for sensitive API operations."""
        try:
            from glogarch.notify.sender import send_notification, NotifyEvent
            lines = []
            for e in entries[:5]:
                lines.append(
                    f"{e.get('username', '?')} — {e.get('method')} {e.get('uri')} "
                    f"({e.get('operation', '?')}) → {e.get('status_code')}"
                )
            if len(entries) > 5:
                lines.append(f"... +{len(entries) - 5} more")
            from glogarch.notify.sender import _t
            title = _t("sensitive_title", n=len(entries))
            body = "\n".join(lines)
            await send_notification(NotifyEvent.SENSITIVE_API_OPERATION, title, body)
        except Exception as e:
            log.warning("Failed to send sensitive operation notification", error=str(e))

    _MAX_BATCH_PENDING = 10000  # Drop if batch grows too large (DoS protection)
    _MAX_PACKET_SIZE = 65536    # Ignore oversized UDP packets

    def handle_datagram(self, data: bytes, addr: tuple[str, int]) -> None:
        """Process a received UDP syslog datagram."""
        src_ip = addr[0]

        # IP allowlist check
        if self.allowed_ips and src_ip not in self.allowed_ips:
            self.rejected_count += 1
            if self.rejected_count % 100 == 1:
                log.warning("Rejected audit syslog from unknown IP",
                            ip=src_ip, total_rejected=self.rejected_count)
            return

        # DoS protection: drop if batch queue too large or packet oversized
        if len(data) > self._MAX_PACKET_SIZE:
            return
        if len(self._batch) > self._MAX_BATCH_PENDING:
            return

        self.received_count += 1
        self.last_received_at = datetime.utcnow().isoformat() + "Z"

        # Parse syslog → JSON → structured entry
        payload = parse_syslog_payload(data)
        if not payload:
            return
        raw = parse_nginx_json(payload)
        if not raw:
            return

        # Skip background polling noise
        method = raw.get("method", "")
        uri = raw.get("uri", "")
        if is_noise(method, uri):
            return

        entry = process_raw_entry(raw, max_body_size=self.config.max_body_size)
        auth_type = entry.pop("_auth_type", "")
        full_token = entry.pop("_full_token", "")
        cookie_session = entry.pop("_cookie_session", "")
        username = entry.get("username", "")
        remote_addr = entry.get("remote_addr", "")

        # Login request — extract username from request body JSON
        if entry.get("operation") == "auth.login":
            body = raw.get("request_body") or ""
            if body and body != "-":
                try:
                    import json as _json
                    body_data = _json.loads(body)
                    body_user = body_data.get("username", "")
                    if body_user:
                        entry["username"] = body_user
                        username = body_user
                        self._session_cache[f"ip:{remote_addr}"] = body_user
                        log.info("Login detected", ip=remote_addr, user=body_user)
                except Exception:
                    pass

        # Resolve token → username
        if auth_type == "token":
            resolved = self._resolve_token_username(username)
            if resolved != username:
                entry["username"] = resolved
            elif full_token:
                # Cache miss — resolve asynchronously via per-user token API
                asyncio.get_event_loop().create_task(
                    self._resolve_token_via_api(full_token, entry)
                )
        # Resolve session → username via Graylog API
        elif auth_type == "session" and username:
            resolved = self._session_cache.get(username)
            if resolved:
                entry["username"] = resolved
            else:
                # Async resolve — will update entry before batch flush
                log.debug("Session resolve queued", session=username[:8],
                          op=entry.get("operation"))
                asyncio.get_event_loop().create_task(
                    self._resolve_session(username, entry)
                )
        elif not auth_type and cookie_session:
            # No Authorization header but cookie has session ID — resolve it
            resolved = self._session_cache.get(cookie_session)
            if resolved:
                entry["username"] = resolved
            else:
                asyncio.get_event_loop().create_task(
                    self._resolve_session(cookie_session, entry)
                )
        elif not auth_type and not username:
            # No Authorization header and no cookie — use IP cache or default user
            ip_user = self._session_cache.get(f"ip:{remote_addr}", "")
            default = self._session_cache.get("_default_user", "")
            if ip_user:
                entry["username"] = ip_user
            elif default:
                entry["username"] = default

        # Fill server_name if empty (nginx $server_name may be blank)
        if not entry.get("server_name") and self.settings.servers:
            entry["server_name"] = self.settings.servers[0].name

        # Resolve target resource name (input/stream/user ID → human name)
        target_name = self._resolve_target_name(uri)
        if target_name:
            entry["target_name"] = target_name

        # For search operations, extract the query
        if entry.get("operation") in ("search.execute", "search.create", "search.update") and not entry.get("target_name"):
            # GET /api/search/universal/relative?query=xxx
            qs = entry.get("query_string", "")
            if qs:
                from urllib.parse import parse_qs, unquote
                params = parse_qs(qs)
                q = params.get("query", params.get("q", [""]))[0]
                if q:
                    q = unquote(q)
                    entry["target_name"] = q[:100] + ("..." if len(q) > 100 else "")
            # POST /api/views/search/sync — query is in body
            if not entry.get("target_name"):
                body_raw = raw.get("request_body") or ""
                if body_raw and body_raw != "-":
                    try:
                        import json as _json
                        body_obj = _json.loads(body_raw)
                        for qobj in body_obj.get("queries", []):
                            q = qobj.get("query", {}).get("query_string", "")
                            if q and q != "*":
                                entry["target_name"] = q[:100] + ("..." if len(q) > 100 else "")
                                break
                    except Exception:
                        pass

        # For create/modify operations, extract title/name/username from request body
        if not entry.get("target_name"):
            body_raw = raw.get("request_body") or ""
            if body_raw and body_raw != "-":
                try:
                    import json as _json
                    body_obj = _json.loads(body_raw)
                    op = entry.get("operation", "")
                    if op == "auth.login":
                        t = body_obj.get("username", "")
                    elif op.startswith("user."):
                        t = body_obj.get("username") or body_obj.get("full_name") or ""
                    elif op == "processing.config":
                        # Show processor names from the order list
                        procs = body_obj.get("processor_order", [])
                        names = [p.get("name", "") for p in procs if p.get("name")]
                        t = ", ".join(names) if names else ""
                    elif op == "role.create" or op == "role.modify":
                        t = body_obj.get("name") or body_obj.get("description") or ""
                    else:
                        t = body_obj.get("title") or body_obj.get("name") or ""
                    if t:
                        entry["target_name"] = str(t)[:120]
                except Exception:
                    pass

        # Fallback: extract meaningful segment from URI for operations without target
        if not entry.get("target_name"):
            op = entry.get("operation", "")
            # Map operation prefixes to URI segment extraction
            uri_hints = {
                "cluster_config": r"/api/system/cluster_config/([^/?]+)",
                "field_mapping": r"/api/system/indices/mappings",
                "processing": r"/api/system/(?:processing|messageprocessors)/(\w+)",
                "deflector": r"/api/(?:system|cluster)/deflector",
                "index": r"/api/system/indexer/indices/([^/]+)",
                "grok": r"/api/system/grok(?:/([^/]+))?",
                "content_pack": r"/api/system/content_packs(?:/([^/]+))?",
            }
            for prefix, pattern in uri_hints.items():
                if op.startswith(prefix):
                    m = re.search(pattern, uri)
                    if m and m.lastindex:
                        entry["target_name"] = m.group(1)
                    break

        # For share operations, enrich target with grantees from body
        if entry.get("operation") == "share.modify" and entry.get("target_name"):
            body_raw = raw.get("request_body") or ""
            if body_raw and body_raw != "-":
                try:
                    import json as _json
                    body_obj = _json.loads(body_raw)
                    caps = body_obj.get("selected_grantee_capabilities", {})
                    grantees = []
                    for grn, perm in caps.items():
                        # grn::::user:ID or grn::::team:ID
                        m = re.search(r"grn::::(\w+):\s*([a-f0-9]{24})", grn)
                        if m:
                            gtype, gid = m.group(1), m.group(2)
                            if gtype == "user":
                                # Try resource cache for user ID → name
                                uname = self._resource_cache.get(f"user:{gid}", "")
                                grantees.append(f"{uname or gid[:8]} ({perm})")
                            else:
                                grantees.append(f"{gtype}:{gid[:8]} ({perm})")
                    if grantees:
                        entry["target_name"] += " → " + ", ".join(grantees[:3])
                except Exception:
                    pass

        # For logout, use the username as target
        if entry.get("operation") == "auth.logout" and not entry.get("target_name"):
            entry["target_name"] = entry.get("username", "")

        # Queue for batch insert
        asyncio.get_event_loop().create_task(self._enqueue(entry))

    async def _enqueue(self, entry: dict) -> None:
        async with self._batch_lock:
            self._batch.append(entry)

    def get_status(self) -> dict:
        return {
            "enabled": self.config.enabled,
            "listening": self.transport is not None,
            "port": self.config.listen_port,
            "received": self.received_count,
            "rejected": self.rejected_count,
            "last_received_at": self.last_received_at,
            "allowed_ips": sorted(self.allowed_ips),
            "heartbeat_alert": self._heartbeat_alerted,
        }
