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
    # Two windows, see engine._silent: who sent logs before, and who still does.
    Probe("silent_sources", "*", ("source",), (("count", None),), limit=1000),
    # (account, source) pairs of successful logins, see runner.new_source_findings
    Probe("auth_ok_pairs", AUTH_OK, ("user_name", "source_ip"), (("count", None),), limit=1000),
    # Message volume of the run window per host and per event category, see
    # engine._volume and runner.volume_findings.
    Probe("volume", "*", ("source", "event_category"), (("count", None),), limit=1000),
)}

# account_new_source (added 1.29): a successful login from a source the account has
# not used for NEW_SOURCE_MEMORY_DAYS. No alert while the account's history is
# younger than NEW_SOURCE_LEARN_DAYS (a new install, a new account).
NEW_SOURCE_LEARN_DAYS = 7
NEW_SOURCE_MEMORY_DAYS = 30

# source_silent (added 1.26): a host that sent at least min_count messages in the
# BASELINE_HOURS before the last SILENT_HOURS and nothing since. Logging that stops
# is how an attacker hides (ATT&CK T1562) and how a broken forwarder looks.
SILENT_HOURS = 2
BASELINE_HOURS = 24

# volume_anomaly (added 1.30): a host or an event category sending far more than it
# usually does at this time of day. The usual = the median of the same hour (+-1 h)
# on each of the last ANOMALY_HISTORY_DAYS days; needs ANOMALY_MIN_DAYS such days and
# a history at least ANOMALY_LEARN_DAYS old. A spike = at least min_count messages per
# hour, at least ANOMALY_FACTOR times the usual, and ANOMALY_Z robust deviations above
# it (median absolute deviation, floored so a flat history does not alert on noise).
ANOMALY_HISTORY_DAYS = 14
ANOMALY_LEARN_DAYS = 7
ANOMALY_MIN_DAYS = 5
ANOMALY_FACTOR = 5.0
ANOMALY_Z = 4.0
ANOMALY_MEDIUM_FACTOR = 20.0


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
    # Off by default: it aggregates a day of ALL messages per run (one terms
    # aggregation by source, 1000 buckets), heavier than the other probes.
    Detector("source_silent", "silent_sources", min_count=50,
             severity=({"sev": "medium"},), default_enabled=False),
    # Off by default: it keeps state (every account/source pair) and needs a week
    # of learning; machine accounts are left out like for account_multi_host.
    Detector("account_new_source", "auth_ok_pairs", min_count=1,
             severity=({"external": True, "sev": "medium"}, {"sev": "low"}),
             exclude='user_name:/.*[$]/', default_enabled=False),
    # Off by default: two more aggregations of ALL messages of the window per run,
    # and it keeps an hourly history per host and category (sec_volumes). Never
    # high: an unusual volume is a reason to look, not an attack by itself.
    Detector("volume_anomaly", "volume", min_count=500,
             severity=({"sev": "low"},), default_enabled=False),
)

DETECTOR_IDS = tuple(d.id for d in DETECTORS)
