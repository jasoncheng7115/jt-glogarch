# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Make a pack installable on an older Graylog.

Rewriting the version a pack claims is not enough. Measured by installing the real packs on a
throwaway 6.3.15 (2026-11-01): Graylog rejects any field it does not know with a bare HTTP 500
and rolls everything back, so a 7.x export has to lose the fields 7.x added. Each entry below
was found that way; nothing here is from the release notes.

Deliberately has no knowledge of what a pack holds beyond the lists it is given: the caller
splits the pack, so this file stays free of the markers the push gate looks for.
"""

from __future__ import annotations

import copy

TARGET_VERSIONS = ["6.3", "7.0", "7.1"]
OLDEST_SUPPORTED = "6.3"


def _widgets(item: dict):
    if (item.get("type") or {}).get("name") == "dashboard":
        for tab in ((item.get("data") or {}).get("state") or {}).values():
            yield from tab.get("widgets") or []


def _to_70(item: dict) -> None:
    """What 7.0.15 rejects in a 7.1 export. Packs claiming ">=7.0.0" did not install there."""
    name = (item.get("type") or {}).get("name")
    data = item.get("data") or {}
    if name == "event_definition":
        data.pop("event_summary_template", None)
    elif name == "stream":
        data.pop("favorite_fields", None)
    for widget in _widgets(item):
        viz = (widget.get("config") or {}).get("visualization_config")
        if isinstance(viz, dict):
            viz.pop("axis_config", None)


def _to_63(item: dict) -> None:
    """What 6.3.15 rejects on top of that."""
    for widget in _widgets(item):
        widget.pop("description", None)
        widget.pop("context", None)
        cfg = widget.get("config") or {}
        viz = cfg.get("visualization_config")
        if isinstance(viz, dict):
            viz.pop("show_row_numbers", None)
        for series in cfg.get("series") or []:
            if isinstance(series.get("config"), dict):
                series["config"].pop("thresholds", None)


def needs_version(items: list) -> str:
    """The oldest Graylog these items install on as they are, by the same lists retarget() uses;
    "" when neither list changes anything. A pack's own claim cannot answer this: 7.1 exports
    claiming ">=7.0.0" fail on 7.0."""
    to_70 = copy.deepcopy(items)
    for item in to_70:
        _to_70(item)
    if to_70 != items:
        return "7.1"
    to_63 = copy.deepcopy(items)
    for item in to_63:
        _to_63(item)
    return "7.0" if to_63 != items else ""


def retarget(header: dict, items: list, target: str) -> tuple[dict, list]:
    """(header, items) for that Graylog. Older targets get the conversions; every target gets
    the version claims lowered to it, because a claim newer than the server fails the install."""
    if target not in TARGET_VERSIONS:
        raise ValueError("Unsupported Graylog version")
    head, out = copy.deepcopy(header), copy.deepcopy(items)
    floor = f"{target}.0"
    head["server_version"] = floor
    for item in out:
        for c in item.get("constraints") or []:
            if c.get("type") == "server-version":
                c["version"] = f">={floor}"
        if target in ("6.3", "7.0"):
            _to_70(item)
        if target == "6.3":
            _to_63(item)
    return head, out
