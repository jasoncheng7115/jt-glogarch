# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""What an incident is about, beyond its numbers (added 1.35).

Owner, 2026-11-23, on a WAF-scan notification: "要顯示是那個 source 抓到的 資訊太少".
The detectors count (108 events, 105 paths, 1 site) but do not say which host
reported it, which site was hit, which paths or what the server answered. Those
are a few top-value aggregations over the incident's own query and window, run
for the findings of a run and stored in `metrics.context`, so the notification,
the page and the AI follow-up all read the same values.

Pure with respect to I/O: `fetch` is the engine's aggregation function.
"""
from __future__ import annotations

from datetime import datetime

from glogarch.security.fieldmap import FieldMap

# GIM fields per detection, in the order they are shown. `source` (the host that
# sent the events: the WAF, the sensor, the server where the login failed) is
# what the owner asked for first.
FIELDS: dict[str, tuple[str, ...]] = {
    "waf_scanner": ("source", "vhost", "uri", "http_response_code"),
    "auth_bruteforce": ("source", "user_name"),
    "auth_spray": ("source", "user_name"),
    "auth_multi_host": ("source", "user_name"),
    "auth_success_after_fail": ("source", "user_name"),
    "account_multi_host": ("source", "source_ip"),
    "ids_alert_passed": ("source", "source_ip", "destination_ip"),
    "account_new_source": ("source",),
    "volume_anomaly": ("source", "event_category"),
    "source_silent": (),       # nothing recent to break down
}
SIGMA_FIELDS = ("source",)
TOP = 3
# A run with a flood of findings must not turn into hundreds of queries; the
# highest ones get their context, the rest show their numbers only.
MAX_FINDINGS = 12
_SEV = {"high": 3, "medium": 2, "low": 1}


def _fields_for(detector: str) -> tuple[str, ...]:
    return SIGMA_FIELDS if detector.startswith("sigma:") else FIELDS.get(detector, ("source",))


async def add_context(fetch, findings: list[dict], fm: FieldMap, time_from: datetime,
                      time_to: datetime, errors: list[str] | None = None) -> int:
    """Sets `metrics["context"] = {gim_field: [[value, count], ...]}` on up to
    MAX_FINDINGS findings (highest severity, then most events). A failed field is
    left out and noted in `errors`; the run goes on. Returns queries sent."""
    sent = 0
    order = sorted(findings, key=lambda f: (-_SEV.get(f.get("severity"), 0),
                                            -int((f.get("metrics") or {}).get("count") or 0)))
    for f in order[:MAX_FINDINGS]:
        if not f.get("query"):
            continue
        ids = f.get("detector") == "ids_alert_passed"
        ctx: dict[str, list] = {}
        for gim in _fields_for(str(f.get("detector") or "")):
            fld = fm.field(gim, ids)
            if fld == f.get("entity_field"):
                continue        # that is the entity itself
            try:
                sent += 1
                rows = await fetch(f["query"], fld, (("count", None),), time_from, time_to, TOP + 1)
            except Exception as e:
                if errors is not None:
                    errors.append(f"context/{gim}: {str(e)[:200]}")
                continue
            vals = sorted(([str(r.get("entity")), int(r.get("count") or 0)] for r in rows
                           if r.get("entity") not in (None, "", "(Empty Value)")), key=lambda x: -x[1])
            if vals:
                ctx[gim] = vals[:TOP]
        if ctx:
            f.setdefault("metrics", {})["context"] = ctx
    return sent
