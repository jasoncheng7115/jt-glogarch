# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Built-in security detectors.

Each detector reads ONE aggregation ("probe") from Graylog's scripting API
(`POST /api/search/aggregate`): counts per entity, never raw messages, so a run
costs a handful of searches whatever the volume.

Field names are NOT uniform across products even on a GIM-style site
(measured on a production site, 2026-11-19): the WAF puts the peer in `client_ip`, Suricata
and the firewall in `source_ip`, Suricata's severity is `alert_severity`; and
sshd failures arrived with `source_ip`/`user_name` EMPTY for 9,585 events a
week. So a probe lists every field that may hold the entity and is run once per
field, and the "(Empty Value)" bucket Graylog returns tells how much of the data
lacks it (shown as coverage, so a detector that sees nothing says so instead of
reporting a clean zero).

Thresholds were calibrated against a week of real data on a production site: the defaults
must not open incidents for internet background noise (an `ET SCAN NMAP` alert
from 396 sources a day) or for a pair of domain controllers failing pam_unix
logins with machine accounts all day.
"""
from __future__ import annotations

from dataclasses import dataclass, field

SEVERITIES = ("low", "medium", "high")


def sev_rank(s: str) -> int:
    return SEVERITIES.index(s) if s in SEVERITIES else -1


AUTH_FAIL = "event_category:authentication AND event_outcome:failure"
AUTH_OK = "event_category:authentication AND event_outcome:success"
PEER_FIELDS = ("source_ip", "client_ip")


@dataclass(frozen=True)
class Probe:
    """One aggregation: `query`, grouped by one of `fields`, with `metrics`.

    `metrics` are (function, field) pairs; `count` has no field."""
    id: str
    query: str
    fields: tuple[str, ...]
    metrics: tuple[tuple[str, str | None], ...] = (("count", None),)
    limit: int = 100


@dataclass(frozen=True)
class Detector:
    id: str
    probe: str
    # Minimum events in the window before anything is considered.
    min_count: int = 1
    # Optional cardinality condition: (metric field, minimum distinct values).
    min_card: tuple[str, int] | None = None
    # Severity rules, checked in order; first match wins. Each is a dict of
    # optional conditions: count>=, card>=, external (bool), max_sev<= .
    severity: tuple[dict, ...] = field(default_factory=tuple)
    # Default exclusion (Lucene), editable per site.
    exclude: str = ""
    default_enabled: bool = True


PROBES: dict[str, Probe] = {p.id: p for p in (
    Probe("auth_fail_peer", AUTH_FAIL, PEER_FIELDS,
          (("count", None), ("card", "user_name"), ("card", "source"))),
    Probe("auth_fail_account", AUTH_FAIL, ("user_name",),
          (("count", None), ("card", "source"), ("card", "source_ip"))),
    Probe("ids_passed", "event_category:intrusion_detection AND NOT event_action:blocked",
          ("alert_signature",),
          (("count", None), ("card", "source_ip"), ("min", "alert_severity"))),
    Probe("waf_peer", "event_category:web_attack", ("client_ip", "source_ip"),
          (("count", None), ("card", "uri"), ("card", "vhost"))),
)}


DETECTORS: tuple[Detector, ...] = (
    # One peer failing many logins.
    Detector("auth_bruteforce", "auth_fail_peer", min_count=20,
             severity=({"count": 200, "external": True, "sev": "high"},
                       {"count": 20, "sev": "medium"})),
    # One peer trying many different accounts (password spraying).
    Detector("auth_spray", "auth_fail_peer", min_count=5, min_card=("user_name", 5),
             severity=({"card": 5, "sev": "high"},)),
    # One peer failing on many hosts: per-host thresholds miss it (jt-wazuh-mgr
    # account-guard: 8,856 failures across 7 hosts stayed under each host's).
    Detector("auth_multi_host", "auth_fail_peer", min_count=10, min_card=("source", 3),
             severity=({"external": True, "sev": "high"}, {"sev": "medium"})),
    # One account failing on many hosts.
    Detector("account_multi_host", "auth_fail_account", min_count=10, min_card=("source", 3),
             severity=({"sev": "medium"},),
             # machine accounts (DC1$) fail all day between domain controllers.
             # A regex: Graylog refuses a leading wildcard (`*$`) by default.
             exclude='user_name:/.*[$]/'),
    # A success from a peer that just failed many times (second query, see engine).
    Detector("auth_success_after_fail", "auth_fail_peer", min_count=10,
             severity=({"sev": "high"},)),
    # IDS alerts that were NOT blocked. Suricata severity 1 is the highest.
    Detector("ids_alert_passed", "ids_passed", min_count=1,
             severity=({"max_sev": 1, "sev": "high"},
                       {"max_sev": 2, "count": 100, "sev": "low"})),
    # One peer scanning many paths through the WAF.
    Detector("waf_scanner", "waf_peer", min_count=20, min_card=("uri", 20),
             severity=({"external": True, "card": 100, "sev": "high"},
                       {"sev": "medium"})),
)

DETECTOR_IDS = tuple(d.id for d in DETECTORS)
