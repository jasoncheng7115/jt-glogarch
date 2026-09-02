# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Resolve the TLS-verify setting for an ad-hoc target URL.

Most HTTP calls carry a server config and simply use `srv.verify_ssl`. A few
paths do not: the import target is given as a bare URL plus credentials typed
into the import dialog, so there is no config object to read.

Those paths used to hardcode `verify=False`, which silently ignored an
operator who had deliberately turned verification ON. Where the target happens
to be a server they HAVE configured, honour that server's setting; otherwise
keep the previous behaviour rather than inventing a stricter default, because
turning verification on for a site that never asked is the direction that
breaks a working system.
"""
from __future__ import annotations

from urllib.parse import urlparse


def _authority(url: str) -> str:
    """host:port of a URL, lowercased; '' when unparseable."""
    try:
        p = urlparse((url or "").strip())
        if not p.hostname:
            return ""
        port = p.port or (443 if p.scheme == "https" else 80)
        return f"{p.hostname.lower()}:{port}"
    except Exception:
        return ""


def verify_for_url(settings, url: str, default: bool = False) -> bool:
    """The `verify` value to pass to httpx for `url`.

    Matches by host:port against the configured Graylog servers. Returns
    `default` (False — today's behaviour) when nothing matches, so a target
    the operator never configured is treated exactly as before.
    """
    want = _authority(url)
    if not want:
        return default
    try:
        # Settings.servers — NOT `graylog_servers`, which does not exist. An
        # invented name here fails open and silently: getattr returns [], the
        # loop never runs, and every caller quietly gets `default` while the
        # feature looks implemented. test_tls_verify builds its stub from the
        # real Settings model so the two cannot drift apart again.
        servers = getattr(settings, "servers", None) or []
    except Exception:
        return default
    for srv in servers:
        if _authority(getattr(srv, "url", "")) == want:
            return bool(getattr(srv, "verify_ssl", default))
    return default
