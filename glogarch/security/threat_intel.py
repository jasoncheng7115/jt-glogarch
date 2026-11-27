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

import asyncio
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
# the widest network a feed line may name: one broken or hostile line such as 0.0.0.0/0
# must not mark every address as listed (Spamhaus DROP's widest entries are far narrower)
MIN_PREFIX = {4: 8, 6: 16}
# a list that shrinks to under this share of a sizable previous list is taken for a broken
# download: the previous list is kept and the feed shows the error
SHRINK_KEEP = 0.1
SHRINK_MIN_PREVIOUS = 100
DOWNLOAD_DEADLINE_SEC = 120


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
        # public addresses only, and no network wider than MIN_PREFIX (0.0.0.0/0, ::/0, 10.0.0.0/8 ...)
        if (not v.is_global) or (kind == "cidr" and v.prefixlen < MIN_PREFIX[v.version]):
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
    async def fetch() -> bytes:
        # streamed with the cap applied per chunk (r.content held the whole, possibly
        # decompressed, body before the size was checked)
        async with client.stream("GET", feed["url"]) as r:
            r.raise_for_status()
            buf = bytearray()
            async for chunk in r.aiter_bytes():
                buf += chunk
                if len(buf) > MAX_BYTES:
                    raise ValueError(f"feed larger than {MAX_BYTES // (1024 * 1024)} MB")
            return bytes(buf)
    try:
        try:   # httpx's timeout is per read: a host trickling bytes must not hold the refresh forever
            body = await asyncio.wait_for(fetch(), DOWNLOAD_DEADLINE_SEC)
        except asyncio.TimeoutError:
            raise ValueError(f"feed download took longer than {DOWNLOAD_DEADLINE_SEC} s")
        entries = parse_feed(body.decode("utf-8", "replace"), feed["kind"])
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
            prev = int((db.ti_status().get(fid) or {}).get("count") or 0)
            if prev >= SHRINK_MIN_PREVIOUS and len(entries) < prev * SHRINK_KEEP:
                raise ValueError(f"the feed shrank from {prev} to {len(entries)} entries; "
                                 "the previous list is kept")
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

    _CACHE_MAX = 20_000

    def __init__(self, entries: dict[str, list[str]]):
        self.ips: dict[str, set[str]] = {}
        # networks indexed by (version, prefix length) -> {network address as int: feeds}:
        # a lookup is one dict probe per distinct prefix length, not a scan of every
        # network (2.4 ms a match with 1,500 networks, measured by a review)
        self.nets: dict[tuple[int, int], dict[int, set[str]]] = {}
        self._cache: dict[str, list[str]] = {}
        for fid, vals in entries.items():
            if FEEDS.get(fid, {}).get("kind") == "cidr":
                for v in vals:
                    net = ipaddress.ip_network(v)
                    self.nets.setdefault((net.version, net.prefixlen), {}).setdefault(
                        int(net.network_address), set()).add(fid)
            else:
                for v in vals:
                    self.ips.setdefault(v, set()).add(fid)

    def __bool__(self) -> bool:
        return bool(self.ips or self.nets)

    def match(self, entity: str) -> list[str]:
        key = str(entity).strip()
        hit = self._cache.get(key)
        if hit is not None:
            return list(hit)
        try:
            ip = ipaddress.ip_address(key)
        except ValueError:
            return []
        hits = set(self.ips.get(str(ip), ()))
        n, bits = int(ip), ip.max_prefixlen
        for (ver, plen), table in self.nets.items():
            if ver != ip.version:
                continue
            fids = table.get((n >> (bits - plen)) << (bits - plen) if plen else 0)
            if fids:
                hits |= fids
        out = sorted(hits, key=list(FEEDS).index)
        if len(self._cache) < self._CACHE_MAX:
            self._cache[key] = out
        return list(out)


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

