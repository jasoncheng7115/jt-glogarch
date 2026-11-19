# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""MITRE ATT&CK mapping of the built-in detections (added 1.23).

Computed when an incident is read, from its detection (and, for IDS alerts,
its signature): nothing is stored, so incidents recorded by an older version
get their techniques too and a corrected mapping applies everywhere at once.

The mapping says what a detection is EVIDENCE OF, not proof that the technique
succeeded: a brute-force incident maps to T1110 whether or not a password was
guessed. IDS alerts are mapped by keywords in the signature (Suricata/ET
naming); a signature matching none of them gets no technique rather than a
guess. Technique and tactic names are MITRE's own (English proper nouns, kept
untranslated like MITRE's own localized material does).
"""
from __future__ import annotations

import re

ATTACK_VERSION = "v16"   # the Enterprise matrix the ids and names below were checked against

TACTICS: tuple[tuple[str, str], ...] = (
    ("TA0043", "Reconnaissance"),
    ("TA0001", "Initial Access"),
    ("TA0003", "Persistence"),
    ("TA0004", "Privilege Escalation"),
    ("TA0005", "Defense Evasion"),
    ("TA0006", "Credential Access"),
    ("TA0008", "Lateral Movement"),
    ("TA0011", "Command and Control"),
    ("TA0040", "Impact"),
)

# id -> (name, tactic ids)
TECHNIQUES: dict[str, tuple[str, tuple[str, ...]]] = {
    "T1110": ("Brute Force", ("TA0006",)),
    "T1110.001": ("Brute Force: Password Guessing", ("TA0006",)),
    "T1110.003": ("Brute Force: Password Spraying", ("TA0006",)),
    "T1078": ("Valid Accounts", ("TA0001", "TA0003", "TA0004", "TA0005")),
    "T1021": ("Remote Services", ("TA0008",)),
    "T1595": ("Active Scanning", ("TA0043",)),
    "T1595.002": ("Active Scanning: Vulnerability Scanning", ("TA0043",)),
    "T1190": ("Exploit Public-Facing Application", ("TA0001",)),
    "T1071": ("Application Layer Protocol", ("TA0011",)),
    "T1498": ("Network Denial of Service", ("TA0040",)),
    "T1562": ("Impair Defenses", ("TA0005",)),
}

DETECTOR_TECHNIQUES: dict[str, tuple[str, ...]] = {
    "auth_bruteforce": ("T1110.001",),
    "auth_spray": ("T1110.003",),
    # one source failing on many hosts: guessing, and trying to move between hosts
    "auth_multi_host": ("T1110", "T1021"),
    "account_multi_host": ("T1110",),
    # failures then a success: the guessed account is now a valid account in use
    "auth_success_after_fail": ("T1110", "T1078"),
    "waf_scanner": ("T1595.002",),
    # logs that stop: possibly logging turned off to hide (also a broken forwarder)
    "source_silent": ("T1562",),
    # a valid account used from somewhere new: possibly stolen credentials
    "account_new_source": ("T1078",),
    # ids_alert_passed: by signature, see IDS_RULES
}

# (pattern on the signature, technique). Every match counts; order is display order.
IDS_RULES: tuple[tuple[re.Pattern, str], ...] = (
    (re.compile(r"\bSCAN\b|\bscan(ner|ning)?\b", re.I), "T1595"),
    (re.compile(r"\bEXPLOIT\b|\bWEB_(SERVER|SPECIFIC_APPS|CLIENT)\b|\bATTACK_RESPONSE\b"
                r"|\bCVE-\d{4}-\d+|\bSQL\b.*\binjection\b|\bRCE\b|\boverflow\b", re.I), "T1190"),
    (re.compile(r"\b(TROJAN|MALWARE|CnC|C2|BOTCC|COINMINER|Cobalt ?Strike)\b", re.I), "T1071"),
    (re.compile(r"\bDOS\b|\bDDoS\b|\bflood\b", re.I), "T1498"),
    (re.compile(r"\bbrute[ -]?force\b|\bauthentication failure", re.I), "T1110"),
)

URL = "https://attack.mitre.org/techniques/"


def technique_url(tid: str) -> str:
    return URL + tid.replace(".", "/") + "/"


def _info(tid: str) -> dict:
    name, tactics = TECHNIQUES.get(tid, ("", ()))   # a Sigma rule may tag any technique
    return {"id": tid, "name": name, "tactics": list(tactics), "url": technique_url(tid)}


def techniques_for(detector: str, entity: str = "", tags: list | None = None) -> list[dict]:
    """The techniques an incident of this detection is evidence of. A Sigma rule
    (detector `sigma:<id>`) brings its own `attack.tNNNN` tags."""
    if detector.startswith("sigma:"):
        from glogarch.security.sigma import attack_ids
        return [_info(t) for t in attack_ids([str(x) for x in (tags or [])])]
    if detector == "ids_alert_passed":
        ids = [t for rx, t in IDS_RULES if rx.search(entity or "")]
    else:
        ids = list(DETECTOR_TECHNIQUES.get(detector, ()))
    return [_info(t) for t in dict.fromkeys(ids)]


def detector_technique_ids(detector: str) -> list[str]:
    """Every technique a detection CAN map to (for the coverage view)."""
    if detector == "ids_alert_passed":
        return list(dict.fromkeys(t for _, t in IDS_RULES))
    return list(DETECTOR_TECHNIQUES.get(detector, ()))


def _detector_state(det_row: dict, coverage: list[dict], ran: bool) -> str:
    """active | no_data | error | disabled | not_run, from the settings and the
    last finished run's coverage (one row per probe field)."""
    if not det_row["enabled"]:
        return "disabled"
    if not ran:
        return "not_run"
    rows = [c for c in coverage if c.get("probe") == det_row["probe"]]
    if not rows:
        return "not_run"
    if any((c.get("events") or 0) > (c.get("missing") or 0) and not c.get("error") for c in rows):
        return "active"
    if all(c.get("error") for c in rows):
        return "error"
    return "no_data"


_RANK = {"active": 5, "signature": 4, "no_data": 3, "error": 2, "not_run": 1, "disabled": 0}


def coverage_matrix(detector_rows: list[dict], coverage: list[dict], ran: bool) -> list[dict]:
    """Per tactic, its techniques with the detections that map to them and the
    best state among those detections: 'active' means a detection runs AND
    this site's logs carry the field it needs. A technique watched only through
    IDS signature keywords is 'signature': it is seen only if the IDS happens
    to have a signature for it, which is weaker than a detection built for it."""
    by_tech: dict[str, list[dict]] = {}
    for d in detector_rows:
        state = _detector_state(d, coverage, ran)
        for tid in detector_technique_ids(d["id"]):
            by_tech.setdefault(tid, []).append({"detector": d["id"], "state": state,
                                                "by_signature": d["id"] == "ids_alert_passed"})
    out = []
    for ta, ta_name in TACTICS:
        techs = []
        for tid, (name, tactics) in TECHNIQUES.items():
            if ta not in tactics or tid not in by_tech:
                continue
            dets = by_tech[tid]
            own = [x for x in dets if not x["by_signature"]]
            sig = [x for x in dets if x["by_signature"]]
            if own and any(x["state"] == "active" for x in own):
                best = "active"
            elif any(x["state"] == "active" for x in sig):
                best = "signature"
            else:
                best = max(dets, key=lambda x: _RANK[x["state"]])["state"]
            techs.append({**_info(tid), "detectors": dets, "state": best})
        if techs:
            out.append({"id": ta, "name": ta_name, "techniques": techs})
    return out
