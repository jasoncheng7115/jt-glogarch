# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Graylog scripting-API aggregation for the security detectors.

`POST /api/search/aggregate` (measured on 7.2.2, 2026-11-19): needs at
least one grouping, returns `schema` (one column per grouping and metric, in
request order) and `datarows`. Events without the grouping field come back as
one "(Empty Value)" row, which the engine reads as coverage.
"""
from __future__ import annotations

from datetime import datetime, timezone

from glogarch.graylog.client import GraylogClient


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def aggregate_body(query: str, group_field: str, metrics: tuple, time_from: datetime,
                   time_to: datetime, limit: int) -> dict:
    return {
        "query": query,
        "timerange": {"type": "absolute", "from": _iso(time_from), "to": _iso(time_to)},
        "group_by": [{"field": group_field, "limit": int(limit)}],
        "metrics": [{"function": fn, **({"field": fld} if fld else {})} for fn, fld in metrics],
    }


def parse_rows(resp: dict, metrics: tuple) -> list[dict]:
    keys = ["entity"] + [fn if fld is None else f"{fn}:{fld}" for fn, fld in metrics]
    rows = []
    for raw in resp.get("datarows") or []:
        if not isinstance(raw, list) or len(raw) != len(keys):
            continue
        row = dict(zip(keys, raw))
        for k in keys[1:]:
            v = row[k]
            if isinstance(v, float) and v.is_integer():
                row[k] = int(v)
        rows.append(row)
    return rows


def make_pair_fetch(client: GraylogClient):
    """Counts per (field_a, field_b) combination (added 1.29, new login sources):
    two groupings in one aggregation; each datarow is [a, b, count]."""
    async def fetch_pairs(query, fields, time_from, time_to, limit):
        body = aggregate_body(query, fields[0], (("count", None),), time_from, time_to, limit)
        body["group_by"] = [{"field": f, "limit": int(limit)} for f in fields]
        resp = await client.post_once("/api/search/aggregate", json=body,
                                      headers={"X-Requested-By": "jt-glogarch"})
        out = []
        for raw in (resp or {}).get("datarows") or []:
            if isinstance(raw, list) and len(raw) == 3:
                n = raw[2]
                out.append({"a": raw[0], "b": raw[1], "count": int(n) if isinstance(n, (int, float)) else 0})
        return out
    return fetch_pairs


def make_fetch(client: GraylogClient):
    async def fetch(query, group_field, metrics, time_from, time_to, limit):
        body = aggregate_body(query, group_field, metrics, time_from, time_to, limit)
        resp = await client.post_once("/api/search/aggregate", json=body,
                                 headers={"X-Requested-By": "jt-glogarch"})
        return parse_rows(resp or {}, metrics)
    return fetch
