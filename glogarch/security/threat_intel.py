# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Threat-intelligence lists (added 1.28): known-bad addresses from public feeds.

OFF by default. When on, a few well-known public lists are DOWNLOADED (nothing
about this site is sent anywhere) about once a day and kept in the DB. An
incident whose source address is on a list is marked with it, scores higher
in the risk ranking, and the AI analysis is told. Enrichment only: being on a
list is a reason to look, not proof (Tor exits carry ordinary users too).

The feeds are a fixed list in this file (no URL comes from the page, so the
download cannot be pointed at an internal service). Each feed's own terms of
use apply.
"""
from __future__ import annotations

import ipaddress

import httpx

from glogarch.utils.logging import get_logger

log = get_logger("security.ti")

FEEDS: dict[str, dict] = {
    "spamhaus_drop": {
        "name": "Spamhaus DROP", "url": "https://www.spamhaus.org/drop/drop.txt", "kind": "cidr",
        "about": "networks hijacked or leased by spammers and cyber-criminals ('do not route or peer')"},
    "tor_exit": {
        "name": "Tor exit nodes", "url": "https://check.torproject.org/torbulkexitlist", "kind": "ip",
        "about": "Tor exit relays: the real origin of the traffic is hidden (also used by ordinary users)"},
    "feodo": {
        "name": "abuse.ch Feodo Tracker", "url": "https://feodotracker.abuse.ch/downloads/ipblocklist.txt", "kind": "ip",
        "about": "botnet command-and-control servers (Dridex, Emotet, QakBot and similar)"},
}
DEFAULT_FEEDS = tuple(FEEDS)
MAX_BYTES = 5 * 1024 * 1024
MAX_ENTRIES = 200_000
TI_MULT = 2.0


def parse_feed(text: str, kind: str) -> list[str]:
    """One entry per line; `#` and `;` start comments; the first token is the
    address or network. Anything that does not parse is skipped (counted by the caller)."""
    out, skipped = [], 0
    for ln in text.splitlines():
        ln = ln.split("#", 1)[0].split(";", 1)[0].strip()
        if not ln:
            continue
        tok = ln.split()[0]
        try:
            v = ipaddress.ip_network(tok, strict=False) if kind == "cidr" else ipaddress.ip_address(tok)
        except ValueError:
            skipped += 1
            continue
        out.append(str(v))
        if len(out) >= MAX_ENTRIES:
            break
    if skipped:
        log.debug("Threat-intel feed lines skipped", kind=kind, skipped=skipped)
    return out


async def download(feed_id: str, client: httpx.AsyncClient | None = None) -> list[str]:
    feed = FEEDS[feed_id]
    own = client is None
    # no redirects: a feed host that started redirecting could point the download at an
    # internal address (all three answer 200 directly, measured 2026-11-20)
    client = client or httpx.AsyncClient(timeout=30, follow_redirects=False,
                                         headers={"User-Agent": "jt-glogarch threat-intel"})
    try:
        r = await client.get(feed["url"])
        r.raise_for_status()
        if len(r.content) > MAX_BYTES:
            raise ValueError(f"feed larger than {MAX_BYTES // (1024 * 1024)} MB")
        entries = parse_feed(r.text, feed["kind"])
        if not entries:
            raise ValueError("feed held no usable entries")
        return entries
    finally:
        if own:
            await client.aclose()


async def refresh(db, feeds: list[str] | tuple[str, ...]) -> dict:
    """Downloads the given feeds; a feed that fails keeps its previous entries."""
    out = {}
    for fid in feeds:
        if fid not in FEEDS:
            continue
        try:
            entries = await download(fid)
            db.replace_ti_feed(fid, entries)
            out[fid] = {"count": len(entries), "error": ""}
        except Exception as e:
            err = str(e)[:300]
            db.record_ti_error(fid, err)
            out[fid] = {"count": None, "error": err}
            log.warning("Threat-intel feed refresh failed", feed=fid, error=err)
    return out


class Matcher:
    """Address -> the feeds listing it. Built from the DB entries of the enabled feeds."""

    def __init__(self, entries: dict[str, list[str]]):
        self.ips: dict[str, set[str]] = {}
        self.nets: list[tuple[ipaddress._BaseNetwork, str]] = []
        for fid, vals in entries.items():
            if FEEDS.get(fid, {}).get("kind") == "cidr":
                for v in vals:
                    self.nets.append((ipaddress.ip_network(v), fid))
            else:
                for v in vals:
                    self.ips.setdefault(v, set()).add(fid)

    def __bool__(self) -> bool:
        return bool(self.ips or self.nets)

    def match(self, entity: str) -> list[str]:
        try:
            ip = ipaddress.ip_address(str(entity).strip())
        except ValueError:
            return []
        hits = set(self.ips.get(str(ip), ()))
        for net, fid in self.nets:
            if ip.version == net.version and ip in net:
                hits.add(fid)
        return sorted(hits, key=list(FEEDS).index)


_cache: dict = {"key": None, "matcher": None}


def matcher_for(settings, db) -> Matcher | None:
    """The matcher for the enabled feeds, or None when threat intel is off.
    Rebuilt only when a feed was refreshed since (cached on the refresh times)."""
    cfg = settings.security
    if not getattr(cfg, "ti_enabled", False):
        return None
    feeds = [f for f in cfg.ti_feeds if f in FEEDS]
    status = db.ti_status()
    key = (tuple(feeds), tuple((f, (status.get(f) or {}).get("refreshed_at")) for f in feeds))
    if _cache["key"] != key:
        _cache["matcher"] = Matcher(db.ti_entries(feeds))
        _cache["key"] = key
    return _cache["matcher"]


def describe(feed_ids: list[str]) -> list[dict]:
    return [{"id": f, "name": FEEDS[f]["name"], "about": FEEDS[f]["about"]} for f in feed_ids if f in FEEDS]

