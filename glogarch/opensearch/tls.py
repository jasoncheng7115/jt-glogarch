# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""One place that turns an OpenSearchConfig into httpx connection options.

Every code path that talks to OpenSearch (export, bulk import, preflight
mapping reads, disk/heap probes, the connection test) must go through
`httpx_options()`. Building `verify=`/`auth=` by hand in each caller is how a
Data Node certificate would reach the exporter but not the bulk importer —
two rules for one decision.
"""

from __future__ import annotations

import os
import ssl
from datetime import datetime
from typing import Any

import httpx

from glogarch.core.config import OpenSearchConfig
from glogarch.utils.logging import get_logger

log = get_logger("opensearch.tls")


class ClientCertError(RuntimeError):
    """The configured client certificate cannot be used (missing, unreadable)."""


def _ssl_context(cfg: OpenSearchConfig) -> ssl.SSLContext | bool:
    if not cfg.uses_client_cert() and not cfg.ca_file:
        return bool(cfg.verify_ssl)
    if cfg.ca_file:
        if not os.path.isfile(cfg.ca_file):
            raise ClientCertError(f"CA file not found: {cfg.ca_file}")
        ctx = ssl.create_default_context(cafile=cfg.ca_file)
        # The chain is always checked against this cluster's own CA. The
        # hostname check is what `verify_ssl` turns on: a Data Node certificate
        # names the node's hostname, which is often reached by IP.
        ctx.check_hostname = bool(cfg.verify_ssl)
        ctx.verify_mode = ssl.CERT_REQUIRED
    elif cfg.verify_ssl:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    else:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE  # nosec B501 - operator turned verify_ssl off
    if cfg.uses_client_cert():
        for p in (cfg.client_cert_file, cfg.client_key_file):
            if not os.path.isfile(p):
                raise ClientCertError(f"client certificate file not found: {p}")
        try:
            ctx.load_cert_chain(cfg.client_cert_file, cfg.client_key_file)
        except (ssl.SSLError, OSError) as e:
            raise ClientCertError(f"cannot load client certificate: {e}") from e
    return ctx


def httpx_options(cfg: OpenSearchConfig) -> dict[str, Any]:
    """`verify` and `auth` for an httpx client talking to this cluster.

    With a client certificate no Basic auth is sent: the Data Node's
    OpenSearch authenticates by certificate, and a stray Authorization header
    would be tried first and logged as a failed login.
    """
    opts: dict[str, Any] = {"verify": _ssl_context(cfg)}
    if not cfg.uses_client_cert() and cfg.username and cfg.password:
        opts["auth"] = httpx.BasicAuth(cfg.username, cfg.password)
    return opts


def cert_not_after(path: str) -> datetime | None:
    """notAfter of a PEM certificate (naive UTC), or None if unreadable.

    Uses the stdlib decoder; `cryptography` is not a dependency.
    """
    if not path or not os.path.isfile(path):
        return None
    try:
        info = ssl._ssl._test_decode_cert(path)  # noqa: SLF001 - stdlib, no public equivalent
        raw = info.get("notAfter")
        if not raw:
            return None
        return datetime.utcfromtimestamp(ssl.cert_time_to_seconds(raw))
    except Exception as e:
        log.warning("Cannot read certificate expiry", path=path, error=str(e))
        return None
