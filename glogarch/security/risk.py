# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Asset matching and risk scores (added 1.25).

A risk score ranks the entities (addresses, accounts, signatures) behind the
recent incidents so the worst comes first. It is deliberately simple and
EXPLAINED: every point comes from one incident, multiplied by named factors the
page lists, so an operator can see why something ranks high and disagree.

    score(entity) = sum over its open incidents in the window of
                    severity weight x external x asset criticality x AI verdict

Closed incidents do not count (someone looked and closed them). Pure: no I/O.
"""
from __future__ import annotations

import ipaddress
import re

from glogarch.utils.logging import get_logger

log = get_logger("security.risk")

SEV_WEIGHT = {"low": 1.0, "medium": 3.0, "high": 8.0}
CRITICALITY = ("low", "medium", "high", "critical")
CRIT_MULT = {"low": 1.0, "medium": 1.5, "high": 2.0, "critical": 3.0}
EXTERNAL_MULT = 1.5
VERDICT_MULT = {"malicious": 1.5, "suspicious": 1.0, "unclear": 1.0, "benign": 0.3}
ASSET_KINDS = ("ip", "cidr", "host", "account")
_NAME = re.compile(r"^[^\s<>\"']{1,255}$")


def normalize_asset(kind: str, value: str) -> tuple[str | None, str]:
    """(normalized value, error). IPs and networks in canonical form, hosts and
    accounts lower-cased (Graylog field values are compared case-insensitively here)."""
    v = str(value or "").strip()
    if kind not in ASSET_KINDS:
        return None, "Unknown asset kind"
    try:
        if kind == "ip":
            return str(ipaddress.ip_address(v)), ""
        if kind == "cidr":
            return str(ipaddress.ip_network(v, strict=False)), ""
    except ValueError:
        return None, "Not a valid address or network"
    if not _NAME.match(v):
        return None, "Not a valid host or account name"
    return v.lower(), ""


def match_asset(entity: str, assets: list[dict]) -> dict | None:
    """The asset an incident's entity is: an exact address, host or account, else
    the narrowest network containing the address. Highest criticality wins a tie."""
    e = str(entity or "").strip()
    try:
        ip = ipaddress.ip_address(e)
    except ValueError:
        ip = None
    best, best_key = None, None
    for a in assets:
        kind, val = a.get("kind"), a.get("value")
        if kind == "ip" and ip is not None and val == str(ip):
            key = (3, 128, CRITICALITY.index(a.get("criticality", "low")))
        elif kind in ("host", "account") and e.lower() == val:
            key = (3, 128, CRITICALITY.index(a.get("criticality", "low")))
        elif kind == "cidr" and ip is not None:
            try:
                net = ipaddress.ip_network(val)
            except ValueError as err:   # stored by an older/hand-edited DB: skip, say so
                log.debug("Ignoring an asset network that does not parse", value=str(val)[:60], error=str(err))
                continue
            if ip.version != net.version or ip not in net:
                continue
            key = (2, net.prefixlen, CRITICALITY.index(a.get("criticality", "low")))
        else:
            continue
        if best_key is None or key > best_key:
            best, best_key = a, key
    return best


def score_entities(incidents: list[dict], assets: list[dict], verdicts: dict[int, dict] | None = None,
                   limit: int = 50, ti=None) -> list[dict]:
    """`ti`: a threat_intel.Matcher (or None): a listed source counts x TI_MULT."""
    verdicts = verdicts or {}
    out: dict[str, dict] = {}
    for inc in incidents:
        if inc.get("status") == "closed":
            continue
        ent = str(inc.get("entity") or "")
        sev = inc.get("severity", "low")
        pts = SEV_WEIGHT.get(sev, 1.0)
        # structured, so the page can say them in its own language; a x1 factor is left out
        factors = [{"k": "severity", "v": sev, "x": SEV_WEIGHT.get(sev, 1.0)}]
        if inc.get("external") in (1, True):
            pts *= EXTERNAL_MULT
            factors.append({"k": "external", "x": EXTERNAL_MULT})
        asset = match_asset(ent, assets)
        if asset:
            m = CRIT_MULT.get(asset.get("criticality", "low"), 1.0)
            pts *= m
            if m != 1.0:
                factors.append({"k": "asset", "v": asset.get("criticality"), "x": m})
        listed = ti.match(ent) if ti else []
        if listed:
            from glogarch.security.threat_intel import FEEDS, TI_MULT
            pts *= TI_MULT
            factors.append({"k": "ti", "v": ", ".join(FEEDS[f]["name"] for f in listed), "x": TI_MULT})
        v = (verdicts.get(inc["id"]) or {}).get("verdict")
        if v in VERDICT_MULT and VERDICT_MULT[v] != 1.0:
            pts *= VERDICT_MULT[v]
            factors.append({"k": "ai", "v": v, "x": VERDICT_MULT[v]})
        row = out.setdefault(ent, {"entity": ent, "entity_field": inc.get("entity_field", ""), "score": 0.0,
                                   "incidents": 0, "max_severity": "low", "external": inc.get("external"),
                                   "asset": None, "last_seen": "", "parts": []})
        row["score"] += pts
        row["incidents"] += 1
        if SEV_WEIGHT.get(sev, 0) > SEV_WEIGHT.get(row["max_severity"], 0):
            row["max_severity"] = sev
        if asset:
            row["asset"] = {k: asset.get(k) for k in ("id", "kind", "value", "name", "criticality", "owner")}
        if listed:
            row["threat_intel"] = listed
        row["last_seen"] = max(row["last_seen"], str(inc.get("last_seen") or ""))
        part = {"incident": inc["id"], "detector": inc.get("detector"), "points": round(pts, 2), "factors": factors}
        if str(inc.get("detector", "")).startswith("sigma:"):
            part["title"] = "Sigma: " + str((inc.get("metrics") or {}).get("sigma_title") or inc["detector"])
        row["parts"].append(part)
    ranked = sorted(out.values(), key=lambda r: (-r["score"], r["entity"]))[:limit]
    for r in ranked:
        r["score"] = round(r["score"], 1)
    return ranked
