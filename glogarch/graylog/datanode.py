# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Graylog Data Node access for OpenSearch-direct export and Bulk import (beta).

A Data Node's OpenSearch takes only certificate (mutual TLS) logins. Graylog
issues such certificates itself: ``POST /api/ca/clientcert`` (permission
``ca_clientcert:create``, i.e. an admin) signs a new key with the cluster CA
and adds the principal to the requested OpenSearch role mappings. The answer
carries the PEM certificate, private key and CA certificate; nothing is kept
by Graylog except the role mapping, which ``DELETE
/api/ca/clientcert/{role}/{principal}`` removes.

jt-glogarch asks for one under its own principal, stores the three PEM files
next to its config (0600), and points the server's per-server ``opensearch``
block at the Data Nodes' OpenSearch REST port. From then on the exporter,
the bulk importer and preflight connect with that certificate.

Certificates expire (Graylog's default is 30 days), and an expired one would
silently stop scheduled archiving. So `ensure_fresh()` renews it before each
OpenSearch-direct run and from a daily internal job; a run that still cannot
get a working certificate falls back to the Graylog API mode rather than not
archiving (see scheduler).
"""

from __future__ import annotations

import asyncio
import os
import re
import socket
import tempfile
import threading as _threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from glogarch.core.config import GraylogServerConfig, OpenSearchConfig
from glogarch.opensearch.tls import cert_not_after
from glogarch.utils.logging import get_logger

log = get_logger("graylog.datanode")

DEFAULT_ROLES = ["all_access"]
DEFAULT_LIFETIME_DAYS = 90
# A scheduled run that cannot REACH the Data Node (restarting, network blip)
# waits and tries again before archiving through the much slower Graylog API
# (owner 2026-11-27): 1, 2 and 5 minutes, about 10 minutes in all with the
# probes. A refused certificate is not retried this way: it gets one new
# certificate, as before.
UNREACHABLE_RETRY_SEC = (60, 120, 300)
OPENSEARCH_PORT = 9200
# Renew when less than this share of the lifetime is left (and never later
# than RENEW_MIN_DAYS before expiry), so one failed renewal still leaves days
# of working certificate for the next attempt.
RENEW_FRACTION = 1 / 3
RENEW_MIN_DAYS = 7


class DataNodeError(RuntimeError):
    pass


def _auth(server: GraylogServerConfig):
    if server.auth_token:
        return httpx.BasicAuth(server.auth_token, "token")
    return httpx.BasicAuth(server.username or "", server.password or "")


def _client(server: GraylogServerConfig, timeout: float = 30.0) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=server.url.rstrip("/"), auth=_auth(server), verify=server.verify_ssl,
        timeout=timeout,
        headers={"Accept": "application/json", "Content-Type": "application/json",
                 "X-Requested-By": "jt-glogarch"})


def default_principal(server_name: str = "") -> str:
    """CN for a certificate: unique per jt-glogarch host AND configured server.

    Removing a principal from a role mapping cuts off every certificate that
    carries it. Two configured servers can be nodes of one Graylog cluster,
    sharing its Data Nodes; with one principal per host, disconnecting one of
    them would lock the other out. So the server name is part of it.
    """
    host = re.sub(r"[^A-Za-z0-9.-]", "-", socket.gethostname() or "host")[:40]
    srv = re.sub(r"[^A-Za-z0-9.-]", "-", server_name or "")[:40]
    return f"jt-glogarch-{host}-{srv}" if srv else f"jt-glogarch-{host}"


def _elements(data: Any) -> list[dict]:
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]
    if isinstance(data, dict):
        for k in ("elements", "datanodes", "nodes"):
            if isinstance(data.get(k), list):
                return [d for d in data[k] if isinstance(d, dict)]
    return []


async def list_datanodes(server: GraylogServerConfig) -> list[dict]:
    """The Data Nodes registered with this Graylog.

    ``GET /api/system/cluster/datanodes`` (paginated, ``elements``) on 6.x/7.x.
    ``/api/datanodes`` is NOT a listing (404 on 7.2.2): only its proxy
    sub-paths exist. Measured on 7.2.2: each element carries
    ``transport_address`` = the node's OpenSearch REST URL
    (``https://<hostname>:9200``), ``rest_api_address`` = the Data Node's own
    API (8999), ``datanode_status`` and ``cert_valid_until``.
    """
    async with _client(server, timeout=10.0) as c:
        r = await c.get("/api/system/cluster/datanodes", params={"per_page": 200})
        if r.status_code == 404:
            return []
        r.raise_for_status()
        return _elements(r.json())


_NOT_SERVING = {"REMOVED", "REMOVING", "UNAVAILABLE", "UNCONFIGURED"}


def node_status(n: dict) -> str:
    """`datanode_status` on 7.x, `data_node_status` on 6.3 (both measured)."""
    return str(n.get("datanode_status") or n.get("data_node_status") or "")


def opensearch_hosts(nodes: list[dict]) -> list[str]:
    """OpenSearch REST URLs of the Data Nodes that are serving."""
    out: list[str] = []
    for n in nodes:
        status = node_status(n).upper()
        if status in _NOT_SERVING:
            continue
        url = str(n.get("transport_address") or "")
        if "://" not in url:
            host = n.get("hostname") or ""
            url = f"https://{host}:{OPENSEARCH_PORT}" if host else ""
        if url and url not in out:
            out.append(url.rstrip("/"))
    return out


async def issue_client_cert(server: GraylogServerConfig, principal: str,
                            roles: list[str], lifetime_days: int) -> dict:
    """Ask Graylog for a client certificate. Returns the PEM strings.

    The key is requested unencrypted: the service has to load it unattended,
    and the file is written 0600 for the service user only.
    """
    body = {"principal": principal, "roles": list(roles), "password": "",  # nosec B105 - empty = unencrypted key, by design (see docstring)
            "certificate_lifetime": f"P{int(lifetime_days)}D"}
    async with _client(server, timeout=60.0) as c:
        r = await c.post("/api/ca/clientcert", json=body)
        if r.status_code == 400 and "property roles" in r.text and roles:
            # Graylog 6.3 takes ONE `role` and refuses the `roles` list that
            # 7.x accepts (measured: 6.3.15 "Unable to map property roles").
            single = {k: v for k, v in body.items() if k != "roles"}
            single["role"] = list(roles)[0]
            r = await c.post("/api/ca/clientcert", json=single)
    if r.status_code in (401, 403):
        raise DataNodeError(
            "Graylog refused to issue a Data Node client certificate "
            f"(HTTP {r.status_code}): the server account needs the "
            "ca_clientcert:create permission (an Admin)")
    if r.status_code >= 400:
        msg = r.text[:300]
        try:
            msg = r.json().get("message") or msg
        except Exception as e:
            log.debug("Non-JSON error from clientcert", error=str(e))
        raise DataNodeError(f"Graylog could not issue the client certificate "
                            f"(HTTP {r.status_code}): {msg}")
    d = r.json()

    def pick(*names):
        for n in names:
            if d.get(n):
                return d[n]
        return ""
    cert = pick("certificate")
    key = pick("private_key", "privateKey")
    ca = pick("ca_certificate", "caCertificate")
    if not (cert and key and ca):
        raise DataNodeError("Graylog's client certificate answer is missing "
                            "the certificate, key or CA")
    return {"certificate": cert, "private_key": key, "ca_certificate": ca,
            "principal": d.get("principal") or principal,
            "roles": d.get("roles") or list(roles)}


async def revoke_client_cert(server: GraylogServerConfig, principal: str,
                             roles: list[str]) -> list[str]:
    """Remove our principal from each role mapping. Returns errors (if any)."""
    errors = []
    async with _client(server, timeout=30.0) as c:
        for role in roles or DEFAULT_ROLES:
            try:
                r = await c.delete(f"/api/ca/clientcert/{role}/{principal}")
                if r.status_code >= 400 and r.status_code != 404:
                    errors.append(f"{role}: HTTP {r.status_code}")
            except httpx.HTTPError as e:
                errors.append(f"{role}: {e}")
    return errors


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)[:64] or "server"


def cert_dir(config_path: str | Path | None, server_name: str) -> Path:
    base = Path(config_path).resolve().parent if config_path else Path("/opt/jt-glogarch")
    return base / "certs" / "datanode" / _safe_name(server_name)


def _write_private(path: Path, text: str) -> None:
    """Write atomically, mode 0600 from the first byte (never world-readable)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path.parent, 0o700)
    except OSError as e:
        log.debug("Cannot tighten cert dir mode", dir=str(path.parent), error=str(e))
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-")
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(text if text.endswith("\n") else text + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError as e:
            log.debug("Cannot remove temp cert file", error=str(e))
        raise
    _chown_like_parent(path)


def _chown_like_parent(path: Path) -> None:
    """Running as root (CLI), hand the file to whoever owns the config dir
    (the service user) or the service could not read its own certificate."""
    if os.geteuid() != 0:
        return
    try:
        st = path.parent.parent.parent.stat()   # <config dir>/certs/datanode/<srv>
        os.chown(path.parent, st.st_uid, st.st_gid)
        os.chown(path, st.st_uid, st.st_gid)
    except OSError as e:
        log.debug("Cannot chown cert file", path=str(path), error=str(e))


def store_bundle(config_path, server_name: str, bundle: dict) -> dict:
    """Write the PEM files; returns their paths. Old files are replaced only
    after the new ones are complete (rename), so a renewal that dies halfway
    leaves the previous working certificate in place."""
    d = cert_dir(config_path, server_name)
    paths = {"cert": d / "client.crt", "key": d / "client.key", "ca": d / "ca.crt"}
    # Key first: a cert without its key is useless, a stale key with the old
    # cert still pairs until the cert is replaced right after.
    new = {k: d / f".new-{p.name}" for k, p in paths.items()}
    _write_private(new["key"], bundle["private_key"])
    _write_private(new["cert"], bundle["certificate"])
    _write_private(new["ca"], bundle["ca_certificate"])
    for k in ("key", "cert", "ca"):
        os.replace(new[k], paths[k])
    return {k: str(v) for k, v in paths.items()}


def remove_bundle(config_path, server_name: str) -> None:
    d = cert_dir(config_path, server_name)
    for n in ("client.crt", "client.key", "ca.crt"):
        (d / n).unlink(missing_ok=True)
    try:
        d.rmdir()
    except OSError as e:
        log.debug("Cert dir not removed", dir=str(d), error=str(e))


def build_os_config(paths: dict, hosts: list[str], principal: str, roles: list[str],
                    lifetime_days: int, verify_hostname: bool = False) -> OpenSearchConfig:
    na = cert_not_after(paths["cert"])
    return OpenSearchConfig(
        hosts=hosts, username=None, password=None, verify_ssl=verify_hostname,
        client_cert_file=paths["cert"], client_key_file=paths["key"], ca_file=paths["ca"],
        datanode=True, datanode_principal=principal, datanode_roles=list(roles),
        datanode_lifetime_days=int(lifetime_days),
        cert_not_after=na.isoformat(timespec="seconds") if na else None)


def needs_renewal(os_cfg: OpenSearchConfig, now: datetime | None = None) -> bool:
    if not os_cfg.datanode:
        return False
    now = now or datetime.utcnow()
    na = cert_not_after(os_cfg.client_cert_file) if os_cfg.client_cert_file else None
    if na is None and os_cfg.cert_not_after:
        try:
            na = datetime.fromisoformat(os_cfg.cert_not_after)
        except ValueError:
            na = None
    if na is None:
        return True
    lifetime = timedelta(days=max(1, os_cfg.datanode_lifetime_days or DEFAULT_LIFETIME_DAYS))
    margin = max(lifetime * RENEW_FRACTION, timedelta(days=RENEW_MIN_DAYS))
    margin = min(margin, lifetime / 2)   # a 1-day cert must not renew forever
    return na - now <= margin


def expired(os_cfg: OpenSearchConfig, now: datetime | None = None) -> bool:
    now = now or datetime.utcnow()
    na = cert_not_after(os_cfg.client_cert_file) if os_cfg.client_cert_file else None
    return na is None or na <= now


async def probe(os_cfg: OpenSearchConfig) -> dict:
    """Connect with the certificate: cluster name/version/health per host."""
    from glogarch.opensearch.client import OpenSearchClient
    out = {"connected": False}
    try:
        async with OpenSearchClient(os_cfg) as c:
            out = await c.test_connection()
    except Exception as e:
        out = {"connected": False, "error": str(e)}
    return out


def os_config_for_url(settings, url: str) -> OpenSearchConfig | None:
    """The Data Node certificate cluster of the configured server at `url`.

    An import target is typed in as a Graylog URL. When it is one of the
    configured servers AND that server has a client-certificate OpenSearch
    block, Bulk import and preflight use that block. Only certificate blocks
    are picked up, so a site whose import worked before this feature keeps
    exactly the behaviour it had (auto-detected OpenSearch, import creds).
    """
    from glogarch.utils.tlsverify import _authority
    want = _authority(url or "")
    if not want:
        return None
    for srv in getattr(settings, "servers", None) or []:
        osc = getattr(srv, "opensearch", None)
        if (osc is not None and osc.hosts and osc.uses_client_cert()
                and _authority(getattr(srv, "url", "")) == want):
            return osc
    return None


# ------------------------------------------------------------ lifecycle

_renew_locks: dict[str, _threading.Lock] = {}
_renew_locks_guard = _threading.Lock()


def _lock_for(server_name: str) -> _threading.Lock:
    with _renew_locks_guard:
        return _renew_locks.setdefault(server_name, _threading.Lock())


def persist_os_block(settings, server_name: str, cfg: OpenSearchConfig | None) -> None:
    """Store the server's OpenSearch block in memory AND in config.yaml."""
    from glogarch.core.config_writer import update_config
    for srv in settings.servers:
        if srv.name == server_name:
            srv.opensearch = cfg
    path = getattr(settings, "_config_path", "") or ""
    if not path:
        return

    def _mut(c):
        for e in c.get("servers", []) or []:
            if isinstance(e, dict) and e.get("name") == server_name:
                if cfg is None:
                    e.pop("opensearch", None)
                else:
                    e["opensearch"] = cfg.model_dump(exclude_none=True)
    update_config(path, _mut)


def _server(settings, server_name: str) -> GraylogServerConfig:
    if not settings.has_server(server_name):
        raise DataNodeError(f"Server '{server_name}' is not configured")
    return settings.get_server(server_name)


def _is_auth_failure(err: str | None) -> bool:
    e = (err or "").lower()
    # Only refusals a NEW certificate can cure. An unreachable host or a
    # hostname mismatch is not one: re-issuing on those would mint a
    # certificate on every run.
    # A CA that Graylog replaced shows here as a chain error (found by a review):
    # "unable to get local issuer certificate" / a self-signed one in the chain. A
    # hostname mismatch is still not one.
    return any(k in e for k in ("401", "403", "unauthorized", "forbidden",
                                "bad certificate", "unknown ca",
                                "certificate expired", "certificate unknown",
                                "unable to get local issuer certificate",
                                "self-signed certificate in certificate chain",
                                "self signed certificate in certificate chain"))


def name_clash(settings, server_name: str) -> str | None:
    """Why this server cannot get its own certificate folder and principal, or None.
    Names are reduced to ASCII for both, so `台北` and `高雄` (or `log 3` and `log_3`)
    would share one folder and one principal: connecting one overwrote the other's
    key, disconnecting one revoked the other (found by a review)."""
    if _safe_name(server_name) in (".", "..") or not _safe_name(server_name).strip("._-"):
        return f"The server name {server_name!r} cannot name a certificate folder; rename the server"
    mine = (_safe_name(server_name), default_principal(server_name))
    for other in getattr(settings, "servers", []):
        if other.name == server_name:
            continue
        theirs = (_safe_name(other.name), default_principal(other.name))
        if mine[0] == theirs[0] or mine[1] == theirs[1]:
            return (f"The servers {server_name!r} and {other.name!r} would share one Data Node "
                    "certificate; rename one of them (letters, digits, '.', '-' and '_' are kept)")
    return None


async def connect(settings, server_name: str, hosts: list[str] | None = None,
                  roles: list[str] | None = None, lifetime_days: int | None = None,
                  verify_hostname: bool = False) -> dict:
    """Issue a certificate, test it, and save the server's OpenSearch block.

    Nothing is saved unless the certificate actually reaches OpenSearch, so a
    wrong host leaves a working configuration untouched.
    """
    server = _server(settings, server_name)
    clash = name_clash(settings, server_name)
    if clash:
        raise DataNodeError(clash)
    nodes = await list_datanodes(server)
    found = opensearch_hosts(nodes)
    use_hosts = [h.strip().rstrip("/") for h in (hosts or []) if h and h.strip()] or found
    if not use_hosts:
        raise DataNodeError("Graylog lists no Data Node that is serving, and no "
                            "OpenSearch address was given")
    prev = server.opensearch
    principal = (prev.datanode_principal if prev is not None and prev.datanode
                 and prev.datanode_principal else default_principal(server_name))
    roles = list(roles or (prev.datanode_roles if prev is not None and prev.datanode
                           and prev.datanode_roles else DEFAULT_ROLES))
    lifetime = int(lifetime_days or (prev.datanode_lifetime_days if prev is not None
                                     and prev.datanode else DEFAULT_LIFETIME_DAYS))
    lifetime = max(1, min(lifetime, 3650))
    # never wait for this lock here: connect() runs on the web server's event loop, and a
    # blocked loop can never let the holder finish (two clicks on Connect froze the service)
    lock = _lock_for(server_name)
    if not lock.acquire(blocking=False):
        raise DataNodeError("A certificate for this server is being issued or renewed right now; "
                            "try again in a minute")
    try:
        bundle = await issue_client_cert(server, principal, roles, lifetime)
        paths = store_bundle(getattr(settings, "_config_path", ""), server_name, bundle)
        cfg = build_os_config(paths, use_hosts, principal, roles, lifetime,
                              verify_hostname=verify_hostname)
        test = await probe(cfg)
        if not test.get("connected"):
            if prev is None or not prev.datanode:
                # First attempt failed: leave nothing behind.
                remove_bundle(getattr(settings, "_config_path", ""), server_name)
                await revoke_client_cert(server, principal, roles)
            raise DataNodeError(
                "The certificate was issued but OpenSearch at "
                f"{', '.join(use_hosts)} could not be reached with it: "
                f"{test.get('error', 'unknown error')}")
        persist_os_block(settings, server_name, cfg)
    finally:
        lock.release()
    log.info("Data Node OpenSearch access configured", server=server_name,
             hosts=use_hosts, principal=principal, roles=roles,
             not_after=cfg.cert_not_after)
    return {"hosts": use_hosts, "discovered": found, "principal": principal,
            "roles": roles, "not_after": cfg.cert_not_after, "test": test,
            "nodes": [{"hostname": n.get("hostname"), "status": node_status(n),
                       "address": n.get("transport_address"),
                       "version": n.get("datanode_version")} for n in nodes]}


async def disconnect(settings, server_name: str) -> dict:
    """Remove our role mappings, the PEM files and the server's OpenSearch block."""
    server = _server(settings, server_name)
    cfg = server.opensearch
    errors: list[str] = []
    if cfg is not None and cfg.datanode and cfg.datanode_principal:
        try:
            errors = await revoke_client_cert(server, cfg.datanode_principal,
                                              cfg.datanode_roles or DEFAULT_ROLES)
        except Exception as e:
            errors = [str(e)]
    remove_bundle(getattr(settings, "_config_path", ""), server_name)
    persist_os_block(settings, server_name, None)
    log.info("Data Node OpenSearch access removed", server=server_name, errors=errors)
    return {"removed": True, "revoke_errors": errors}


async def ensure_fresh(settings, server_name: str, force: bool = False
                       ) -> tuple[OpenSearchConfig | None, bool, str | None]:
    """Renew the server's Data Node certificate when it is due.

    Returns (current block, renewed?, error). A failed renewal keeps the
    current block: an unexpired certificate still works, and the next run
    tries again (renewal starts a third of the lifetime before expiry).
    """
    try:
        server = _server(settings, server_name)
    except DataNodeError as e:
        return None, False, str(e)
    cfg = server.opensearch
    if cfg is None or not cfg.datanode:
        return cfg, False, None
    if not force and not needs_renewal(cfg):
        return cfg, False, None
    lock = _lock_for(server_name)
    if not lock.acquire(blocking=False):
        return cfg, False, None          # another run is renewing right now
    try:
        principal = cfg.datanode_principal or default_principal(server_name)
        roles = cfg.datanode_roles or DEFAULT_ROLES
        lifetime = cfg.datanode_lifetime_days or DEFAULT_LIFETIME_DAYS
        bundle = await issue_client_cert(server, principal, roles, lifetime)
        paths = store_bundle(getattr(settings, "_config_path", ""), server_name, bundle)
        new = build_os_config(paths, list(cfg.hosts), principal, roles, lifetime,
                              verify_hostname=cfg.verify_ssl)
        persist_os_block(settings, server_name, new)
        log.info("Data Node client certificate renewed", server=server_name,
                 not_after=new.cert_not_after, forced=force)
        return new, True, None
    except Exception as e:
        from glogarch.utils.sanitize import sanitize
        log.warning("Data Node client certificate renewal failed",
                    server=server_name, error=str(e))
        return cfg, False, sanitize(str(e))
    finally:
        lock.release()


async def ensure_working(settings, server_name: str, *, retry_delays=(),
                         stats: dict | None = None, sleep=asyncio.sleep
                         ) -> tuple[OpenSearchConfig | None, str | None]:
    """Renew when due, then prove the certificate works. Re-issue once when
    OpenSearch refuses it (role mapping removed, CA replaced). Returns
    (block, problem) — `problem` is None when OpenSearch answered.

    `retry_delays` (seconds): when the Data Node could not be REACHED, wait
    each delay in turn and try again; stops at the first success, at a
    refusal (a new certificate was already tried) or when the block is gone.
    `stats` gets {"attempts", "waited_sec"}."""
    cfg, problem = await _ensure_working_once(settings, server_name)
    attempts, waited = 1, 0
    for delay in retry_delays:
        if not problem or cfg is None or not cfg.datanode or _is_auth_failure(problem):
            break
        log.warning("Data Node OpenSearch not reachable — trying again", server=server_name,
                    attempt=attempts, wait_sec=delay, problem=problem[:300])
        await sleep(delay)
        waited += delay
        attempts += 1
        cfg, problem = await _ensure_working_once(settings, server_name)
    if attempts > 1 and not problem:
        log.info("Data Node OpenSearch reachable again", server=server_name,
                 attempts=attempts, waited_sec=waited)
    if stats is not None:
        stats.update(attempts=attempts, waited_sec=waited)
    return cfg, problem


async def _ensure_working_once(settings, server_name: str
                               ) -> tuple[OpenSearchConfig | None, str | None]:
    cfg, _renewed, err = await ensure_fresh(settings, server_name)
    if cfg is None or not cfg.datanode:
        return cfg, None
    test = await probe(cfg)
    if test.get("connected"):
        return cfg, None
    first = test.get("error") or "unknown error"
    if _is_auth_failure(first) or expired(cfg):
        cfg2, renewed, err2 = await ensure_fresh(settings, server_name, force=True)
        if renewed and cfg2 is not None:
            test2 = await probe(cfg2)
            if test2.get("connected"):
                return cfg2, None
            first = test2.get("error") or first
        elif err2:
            first = f"{first}; renewal failed: {err2}"
    return cfg, first


async def ensure_fresh_for(settings, target_url: str) -> OpenSearchConfig | None:
    """`ensure_fresh` for the configured server at `target_url` (import)."""
    from glogarch.utils.tlsverify import _authority
    want = _authority(target_url or "")
    for srv in settings.servers:
        if _authority(srv.url) == want and srv.opensearch is not None and srv.opensearch.datanode:
            cfg, _r, _e = await ensure_fresh(settings, srv.name)
            return cfg
    return None


def status(cfg: OpenSearchConfig | None) -> dict:
    """What the UI shows for a server's Data Node connection."""
    if cfg is None or not cfg.datanode:
        return {"connected": False}
    na = cert_not_after(cfg.client_cert_file) if cfg.client_cert_file else None
    days = None
    if na is not None:
        days = round((na - datetime.utcnow()).total_seconds() / 86400, 1)
    return {"connected": True, "hosts": list(cfg.hosts), "principal": cfg.datanode_principal,
            "roles": list(cfg.datanode_roles), "lifetime_days": cfg.datanode_lifetime_days,
            "not_after": na.isoformat(timespec="seconds") if na else cfg.cert_not_after,
            "days_left": days, "renewal_due": needs_renewal(cfg),
            "files_present": all(os.path.isfile(p or "") for p in
                                 (cfg.client_cert_file, cfg.client_key_file, cfg.ca_file))}
