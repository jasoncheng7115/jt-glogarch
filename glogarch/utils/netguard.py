"""SSRF guard for user-supplied connection targets (OWASP A01 / SSRF).

The "test connection" endpoints legitimately connect to an operator-specified
host, so loopback and RFC1918 private ranges are ALLOWED (this is a self-hosted
tool that routinely tests internal OpenSearch / Graylog). What must be blocked
is the cloud-metadata / link-local range (169.254.0.0/16, fe80::/10), whose
169.254.169.254 endpoint hands out cloud IAM credentials.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

_META_HOSTS = {"metadata.google.internal", "metadata"}


def ssrf_block_reason(url: str) -> str | None:
    """Return a human-readable reason if ``url`` targets a blocked (link-local /
    cloud-metadata) address, otherwise ``None``."""
    if not url:
        return "empty URL"
    try:
        host = urlparse(url if "://" in url else "http://" + url).hostname
    except Exception:
        return "invalid URL"
    if not host:
        return "invalid URL"
    if host.lower() in _META_HOSTS:
        return "cloud metadata host blocked"

    ips: list = []
    try:
        ips = [ipaddress.ip_address(host)]
    except ValueError:
        # Hostname — resolve and check every returned address.
        try:
            ips = [ipaddress.ip_address(i[4][0]) for i in socket.getaddrinfo(host, None)]
        except Exception:
            return None  # unresolvable: let the normal connection attempt fail

    for ip in ips:
        if ip.is_link_local:  # 169.254.0.0/16 and fe80::/10 (incl. cloud metadata)
            return f"link-local/metadata address blocked ({ip})"
    return None
