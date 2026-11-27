# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Suppressions (added 1.31): "this detection on this entity is known and accepted".

Unlike a detector's exclusion query, a suppression does not change what Graylog
counts; the detection still runs, and the finding is dropped just before it
would become (or update) an incident. Each drop is counted on the suppression
(hits, last hit), so a suppressed source that keeps going is still visible. A
suppression has a reason, an author and usually an expiry.

Matching: the detection id exactly, or `*` for every detection; the entity
exactly, or a network (CIDR) that contains an address entity; the server
exactly, or blank for every server. Networks wider than MIN_PREFIX are refused:
one entry must not be able to silence half the internet.
"""
from __future__ import annotations

import ipaddress
from datetime import datetime

from glogarch.utils.logging import get_logger

log = get_logger("security.suppress")

MIN_PREFIX = {4: 16, 6: 32}
MAX_ENTITY = 512
MAX_REASON = 500
DAYS_MAX = 3650


class SuppressionError(ValueError):
    pass


_MAPPED = ipaddress.ip_network("::ffff:0:0/96")


def entity_key(value) -> str:
    """How an entity is compared: stripped; an address in canonical form, an
    IPv4-mapped IPv6 address (::ffff:a.b.c.d) as the IPv4 address. Found by a
    review: `2001:DB8::1` did not match `2001:db8::1`, and a padded entity missed."""
    v = str(value or "").strip()
    try:
        ip = ipaddress.ip_address(v)
    except ValueError:
        return v
    if ip.version == 6 and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return str(ip)


def _network(v: str):
    """An IP network if `v` is one (an address before the "/"), else None."""
    if "/" not in v:
        return None
    try:
        ipaddress.ip_address(v.split("/", 1)[0])
    except ValueError:
        return None          # a URL path, a group-by value with a slash: an exact entity
    try:
        return ipaddress.ip_network(v, strict=False)
    except ValueError:
        return False         # looks like a network but is not one


def normalize_entity(value: str) -> str:
    """The stored form: stripped; an address or a network in canonical form.
    Raises SuppressionError."""
    v = (value or "").strip()
    if not v:
        raise SuppressionError("The entity is empty")
    if len(v) > MAX_ENTITY:
        raise SuppressionError(f"The entity is longer than {MAX_ENTITY} characters")
    net = _network(v)
    if net is False:
        raise SuppressionError(f"Not a network: {v}")
    if net is None:
        return entity_key(v)
    if net.version == 6 and net.overlaps(_MAPPED):
        if not net.subnet_of(_MAPPED):
            # e.g. ::/32 or ::ffff:0:0/96 would silence every IPv4 address written as IPv6
            raise SuppressionError(f"The network {net} contains IPv4-mapped addresses; give the IPv4 network instead")
        net = ipaddress.ip_network(f"{net.network_address.ipv4_mapped}/{net.prefixlen - 96}")
    if net.prefixlen < MIN_PREFIX[net.version]:
        raise SuppressionError(f"The network {net} is too wide (at most /{MIN_PREFIX[net.version]} "
                               f"for IPv{net.version})")
    return str(net)


def _active(rule: dict, now_s: str) -> bool:
    exp = rule.get("expires_at")
    return not exp or exp > now_s


class Suppressor:
    def __init__(self, rules: list[dict], now_s: str):
        self.exact: dict[tuple[str, str, str], int] = {}
        self.nets: list[tuple[str, str, ipaddress._BaseNetwork, int]] = []
        for r in rules:
            if not _active(r, now_s):
                continue
            ent = r["entity"]
            net = _network(ent)
            if net is False or (net is not None and net.version == 6 and net.overlaps(_MAPPED)
                                and not net.subnet_of(_MAPPED)):
                # never stored through the API (any more); ignored, never matches everything
                log.warning("Unusable suppression network ignored", id=r["id"], entity=ent)
                continue
            if net is not None:
                if net.version == 6 and net.subnet_of(_MAPPED):
                    net = ipaddress.ip_network(f"{net.network_address.ipv4_mapped}/{net.prefixlen - 96}")
                if net.prefixlen < MIN_PREFIX[net.version]:   # the same limit as on save, for stored rows
                    log.warning("Too wide suppression network ignored", id=r["id"], entity=ent)
                    continue
                self.nets.append((r["server"], r["detector"], net, r["id"]))
            else:
                self.exact.setdefault((r["server"], r["detector"], entity_key(ent)), r["id"])

    def match(self, server: str, detector: str, entity: str) -> int | None:
        key = entity_key(entity)
        for srv in (server, ""):
            for det in (detector, "*"):
                rid = self.exact.get((srv, det, key))
                if rid is not None:
                    return rid
        if self.nets:
            try:
                ip = ipaddress.ip_address(key)
            except ValueError:
                return None
            for srv, det, net, rid in self.nets:
                if srv in (server, "") and det in (detector, "*") and ip.version == net.version and ip in net:
                    return rid
        return None


def apply_suppressions(findings: list[dict], server: str, rules: list[dict],
                       now: datetime) -> tuple[list[dict], dict[int, int]]:
    """(findings that stay, {suppression id: findings dropped})."""
    from glogarch.core.database import _dt_to_str
    if not rules:
        return findings, {}
    sup = Suppressor(rules, _dt_to_str(now))
    kept, hits = [], {}
    for f in findings:
        rid = sup.match(server, f["detector"], str(f["entity"]))
        if rid is None:
            kept.append(f)
        else:
            hits[rid] = hits.get(rid, 0) + 1
    return kept, hits
