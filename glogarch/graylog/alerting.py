# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Graylog event definitions + notifications: read them, plan a bulk change,
apply it one definition at a time.

Two facts about Graylog's API decide how a write must look (measured on
Graylog 7.1.5):

* ``PUT /api/events/definitions/{id}`` takes the WHOLE definition. So every
  write re-reads the definition right before it and changes only
  ``notifications`` — whatever else someone edited in Graylog meanwhile is sent
  back untouched.
* The PUT's ``schedule`` query parameter IS the definition's state, and it
  defaults to true: a PUT without it turned a DISABLED definition ENABLED;
  ``schedule=false`` on an ENABLED one disabled it. Adding a notification to a
  few hundred definitions without passing the current state would switch on
  every disabled one at once. ``schedule_for()`` is the only place that value
  is chosen.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import httpx

from glogarch.utils.logging import get_logger

log = get_logger("graylog.alerting")

_H = {"Accept": "application/json", "X-Requested-By": "jt-glogarch"}
_PAGE = 200
# Graylog's own "System notification events" definition — not ours to edit.
SYSTEM_SCOPE = "GRAYLOG_NONDELETEABLE_SCOPE"


class GraylogAuthError(Exception):
    """Graylog rejected the credentials (401) — sign in again."""


class GraylogPermissionError(Exception):
    """Graylog refused the action for this user (403)."""


KNOWN_STATES = ("ENABLED", "DISABLED")


def schedule_for(defn: dict) -> bool:
    """The `schedule` value that KEEPS the definition's current state. A state we
    do not know (missing, or a new one such as "PAUSED") is refused: the PUT's
    `schedule` SETS the state, and guessing False would disable the definition."""
    state = str(defn.get("state") or "").upper()
    if state not in KNOWN_STATES:
        raise ValueError(f"Unknown event definition state {defn.get('state')!r}; not changed")
    return state == "ENABLED"


def notif_ids(defn: dict) -> list[str]:
    return [n.get("notification_id") for n in (defn.get("notifications") or [])
            if n.get("notification_id")]


_BRACKET = re.compile(r"\[([^\]]{1,60})\]")
_DASH_PREFIX = re.compile(r"^\s*([^\[\]\-–—:]{1,30}?)\s+[-–—]\s+\S")


def title_tags(title: str) -> list[str]:
    """Tags read from the naming convention people already use: the leading
    ``[Vendor] [Team]`` brackets, or a short ``Product - `` prefix."""
    title = title or ""
    lead = re.match(r"^\s*((?:\[[^\]]+\]\s*)+)", title)
    if lead:
        return [t.strip() for t in _BRACKET.findall(lead.group(1)) if t.strip()]
    m = _DASH_PREFIX.match(title)
    return [m.group(1).strip()] if m else []


def summarize(defn: dict) -> dict:
    """What the page needs for one definition (the full body stays server-side)."""
    cfg = defn.get("config") or {}
    ns = defn.get("notification_settings") or {}
    return {
        "id": defn.get("id"),
        "title": defn.get("title") or "",
        "description": defn.get("description") or "",
        "priority": defn.get("priority"),
        "state": str(defn.get("state") or "").upper(),
        "notifications": notif_ids(defn),
        "matched_at": defn.get("matched_at"),
        "updated_at": defn.get("updated_at"),
        "system": defn.get("_scope") == SYSTEM_SCOPE,
        "type": cfg.get("type") or "",
        "query": cfg.get("query") or "",
        "streams": len(cfg.get("streams") or []),
        "grace_ms": ns.get("grace_period_ms") or 0,
        "backlog": ns.get("backlog_size") or 0,
        "tags": title_tags(defn.get("title") or ""),
    }


# --------------------------------------------------------------------------- #
# Planning                                                                    #
# --------------------------------------------------------------------------- #

ACTIONS = ("add", "remove", "replace", "restore")


@dataclass
class Action:
    type: str
    ids: list[str] = field(default_factory=list)      # add / remove
    src: str = ""                                      # replace: from
    dst: str = ""                                      # replace: to
    target: list[dict] | None = None                   # restore: the exact list

    @classmethod
    def from_dict(cls, d: dict) -> "Action":
        t = (d or {}).get("type") or ""
        if t not in ("add", "remove", "replace"):
            raise ValueError(f"Unknown action: {t}")
        ids = list(dict.fromkeys(str(i) for i in (d.get("notification_ids") or []) if i))   # no duplicates
        src, dst = str(d.get("from") or ""), str(d.get("to") or "")
        if t in ("add", "remove") and not ids:
            raise ValueError("Choose at least one notification")
        if t == "replace" and (not src or not dst or src == dst):
            raise ValueError("Choose two different notifications to replace")
        return cls(type=t, ids=ids, src=src, dst=dst)

    def describe(self, titles: dict[str, str]) -> str:
        nm = lambda i: titles.get(i, i)  # noqa: E731
        if self.type == "add":
            return "add " + ", ".join(nm(i) for i in self.ids)
        if self.type == "remove":
            return "remove " + ", ".join(nm(i) for i in self.ids)
        if self.type == "replace":
            return f"replace {nm(self.src)} with {nm(self.dst)}"
        return "restore"


def new_notifications(defn: dict, action: Action) -> list[dict] | None:
    """The notification list after `action`, or None when nothing changes.

    Entries that stay keep their `notification_parameters` exactly as they were.
    """
    cur = [dict(n) for n in (defn.get("notifications") or [])]
    have = [n.get("notification_id") for n in cur]
    if action.type == "add":
        out = cur + [{"notification_id": i, "notification_parameters": None}
                     for i in action.ids if i not in have]
    elif action.type == "remove":
        out = [n for n in cur if n.get("notification_id") not in action.ids]
    elif action.type == "replace":
        if action.src not in have:
            return None
        out = []
        for n in cur:
            nid = n.get("notification_id")
            if nid == action.src:
                if action.dst not in have:
                    out.append({"notification_id": action.dst, "notification_parameters": None})
            else:
                out.append(n)
    elif action.type == "restore":
        out = [dict(n) for n in (action.target or [])]
    else:
        raise ValueError(f"Unknown action: {action.type}")
    return None if out == cur else out


def skip_reason(defn: dict) -> str | None:
    if defn.get("_scope") == SYSTEM_SCOPE:
        return "Graylog system definition (not editable)"
    return None


def plan(defs: list[dict], ids: list[str], action: Action) -> dict:
    """Split the selected definitions into change / unchanged / skipped."""
    by_id = {d.get("id"): d for d in defs}
    change, unchanged, skipped = [], [], []
    for i in dict.fromkeys(ids):
        d = by_id.get(i)
        if d is None:
            skipped.append({"id": i, "title": "", "reason": "Not found in Graylog"})
            continue
        why = skip_reason(d)
        if why:
            skipped.append({"id": i, "title": d.get("title") or "", "reason": why})
            continue
        after = new_notifications(d, action)
        row = {"id": i, "title": d.get("title") or "", "state": str(d.get("state") or "").upper(),
               "before": notif_ids(d)}
        if after is None:
            unchanged.append(row)
        else:
            row["after"] = [n.get("notification_id") for n in after]
            change.append(row)
    return {"change": change, "unchanged": unchanged, "skipped": skipped}


# --------------------------------------------------------------------------- #
# Graylog REST client                                                         #
# --------------------------------------------------------------------------- #

class AlertingClient:
    """`auth` is a Basic-auth pair: (session_id, "session") or (token, "token")."""

    def __init__(self, url: str, auth: tuple[str, str], verify_ssl: bool = False,
                 timeout: float = 30.0):
        self.base = url.rstrip("/") + "/api"
        self._client = httpx.AsyncClient(auth=httpx.BasicAuth(*auth), verify=verify_ssl,
                                         timeout=timeout, headers=_H)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self._client.aclose()

    async def _req(self, method: str, path: str, **kw) -> Any:
        r = await self._client.request(method, self.base + path, **kw)
        if r.status_code == 401:
            raise GraylogAuthError("Graylog sign-in expired or was rejected")
        if r.status_code == 403:
            raise GraylogPermissionError("Graylog refused this for your account (permission)")
        if r.status_code >= 400:
            msg = ""
            try:
                msg = (r.json() or {}).get("message") or ""
            except ValueError:
                msg = r.text[:200]
            raise RuntimeError(f"Graylog HTTP {r.status_code}: {msg}".strip())
        return r.json() if r.content else {}

    async def _paged(self, path: str, key: str) -> list[dict]:
        out: list[dict] = []
        page = 1
        while True:
            d = await self._req("GET", path, params={"per_page": _PAGE, "page": page})
            items = d.get(key) or []
            out.extend(items)
            total = d.get("total") or 0
            if not items or len(out) >= total:
                return out
            page += 1
            if page > 500:  # 100K definitions: something is wrong, stop
                log.warning("Stopped paging Graylog", path=path, fetched=len(out), total=total)
                return out

    async def whoami(self) -> str:
        d = await self._req("GET", "/system/sessions")
        return d.get("username") or ""

    async def list_definitions(self) -> list[dict]:
        return await self._paged("/events/definitions", "event_definitions")

    async def list_notifications(self) -> list[dict]:
        return await self._paged("/events/notifications", "notifications")

    async def get_definition(self, def_id: str) -> dict:
        return await self._req("GET", f"/events/definitions/{def_id}")

    async def stream_titles(self) -> dict[str, str]:
        """{stream_id: title}; empty when this user may not list streams."""
        try:
            d = await self._req("GET", "/streams")
        except GraylogPermissionError:
            return {}
        return {x.get("id"): x.get("title") or "" for x in (d.get("streams") or [])}

    async def put_notifications(self, fresh: dict, notifications: list[dict]) -> dict:
        """Write `notifications` onto the just-read definition `fresh`, keeping its
        state. Returns Graylog's stored result."""
        body = dict(fresh)
        body["notifications"] = notifications
        return await self._req("PUT", f"/events/definitions/{fresh['id']}",
                               params={"schedule": "true" if schedule_for(fresh) else "false"},
                               json=body)

    async def test_notification(self, notif_id: str) -> tuple[bool, str]:
        try:
            await self._req("POST", f"/events/notifications/{notif_id}/test")
            return True, ""
        except (GraylogAuthError, GraylogPermissionError):
            raise
        except RuntimeError as e:
            return False, str(e)


async def create_session(url: str, username: str, password: str, verify_ssl: bool,
                         remote_host: str = "") -> dict:
    """POST /api/system/sessions. Returns {session_id, valid_until, username}."""
    async with httpx.AsyncClient(verify=verify_ssl, timeout=10.0) as c:
        r = await c.post(url.rstrip("/") + "/api/system/sessions",
                         headers={**_H, "Content-Type": "application/json"},
                         json={"username": username, "password": password, "host": remote_host})
    if r.status_code in (401, 403):
        raise GraylogAuthError("Graylog rejected the username or password")
    r.raise_for_status()
    d = r.json()
    if not d.get("session_id"):
        raise RuntimeError("Graylog returned no session")
    return d


async def delete_session(url: str, session_id: str, verify_ssl: bool) -> None:
    async with httpx.AsyncClient(verify=verify_ssl, timeout=5.0) as c:
        await c.delete(url.rstrip("/") + f"/api/system/sessions/{session_id}",
                       auth=httpx.BasicAuth(session_id, "session"), headers=_H)


# --------------------------------------------------------------------------- #
# Applying a batch                                                            #
# --------------------------------------------------------------------------- #

class BatchAborted(Exception):
    """Stop the whole batch (sign-in expired, no permission)."""


async def apply_batch(client: "AlertingClient", db, *, batch_id: str, server: str,
                      username: str, items: list[dict], action: Action,
                      cancel_check=None, progress_cb=None, delay: float = 0.05,
                      undoes_batch: str | None = None) -> dict:
    """Apply `action` to each item, one definition at a time.

    Per item: re-read the definition; if its notifications are no longer what the
    preview showed (someone edited it in Graylog meanwhile) skip it rather than
    overwrite their change; log the change BEFORE sending it; send it with the
    definition's current state; check what Graylog stored.

    Restore items carry ``target`` (the exact list to put back), ``expect`` (what
    the undone batch left there) and ``row_id`` (that batch's log row).
    """
    import asyncio
    res = {"changed": 0, "unchanged": 0, "skipped": [], "failed": [], "cancelled": False,
           "aborted": ""}
    total = len(items)
    for n, item in enumerate(items, 1):
        if cancel_check and cancel_check():
            res["cancelled"] = True
            break
        did, title = item["id"], item.get("title") or ""
        try:
            fresh = await client.get_definition(did)
        except GraylogAuthError as e:
            res["aborted"] = str(e)
            break
        except Exception as e:
            res["failed"].append({"id": did, "title": title, "reason": str(e)})
            continue
        title = fresh.get("title") or title
        current = notif_ids(fresh)
        if action.type == "restore":
            act = Action(type="restore", target=item.get("target") or [])
            if current != (item.get("expect") or []):
                res["skipped"].append({"id": did, "title": title,
                                       "reason": "Notifications changed since that batch"})
                _progress(progress_cb, n, total)
                continue
        else:
            act = action
            if current != (item.get("before") or []):
                res["skipped"].append({"id": did, "title": title,
                                       "reason": "Changed in Graylog since the preview"})
                _progress(progress_cb, n, total)
                continue
        why = skip_reason(fresh)
        if not why and str(fresh.get("state") or "").upper() not in KNOWN_STATES:
            why = f"Unknown state {fresh.get('state')!r}: not changed"   # schedule_for could only guess
        after = None if why else new_notifications(fresh, act)
        if why:
            res["skipped"].append({"id": did, "title": title, "reason": why})
        elif after is None:
            res["unchanged"] += 1
        else:
            row = db.add_alerting_change(batch_id, server, did, title, action.type,
                                         fresh.get("notifications") or [], after, username,
                                         undoes_batch=undoes_batch)
            try:
                stored = await client.put_notifications(fresh, after)
                if "state" not in stored:
                    stored = await client.get_definition(did)
                if str(stored.get("state") or "").upper() != str(fresh.get("state") or "").upper():
                    # Graylog flipped the enabled state: put the original state back once
                    log.warning("Graylog changed an event definition's state; putting it back",
                                definition=did, was=fresh.get("state"), now=stored.get("state"))
                    stored = await client.put_notifications({**stored, "state": fresh.get("state")}, after)
                    if "state" not in stored:
                        stored = await client.get_definition(did)
                bad = []
                if notif_ids(stored) != [x["notification_id"] for x in after]:
                    bad.append("notifications differ from what was sent")
                if str(stored.get("state") or "").upper() != str(fresh.get("state") or "").upper():
                    bad.append(f"state changed {fresh.get('state')} -> {stored.get('state')}")
                if bad:
                    raise RuntimeError("Graylog stored something else: " + "; ".join(bad))
                db.set_alerting_change(row, "applied")
                if item.get("row_id"):
                    db.set_alerting_change(int(item["row_id"]), "restored")
                res["changed"] += 1
            except (GraylogAuthError, GraylogPermissionError) as e:
                db.set_alerting_change(row, "failed", str(e))
                res["failed"].append({"id": did, "title": title, "reason": str(e)})
                res["aborted"] = str(e)
                break
            except Exception as e:
                db.set_alerting_change(row, "failed", str(e))
                res["failed"].append({"id": did, "title": title, "reason": str(e)})
                log.warning("Alerting change failed", definition=did, error=str(e))
        _progress(progress_cb, n, total)
        if delay:
            await asyncio.sleep(delay)
    return res


def _progress(cb, done: int, total: int) -> None:
    if cb:
        try:
            cb(done, total)
        except Exception as e:
            log.debug("Alerting progress callback failed", error=str(e))


def restore_items(rows: list[dict]) -> list[dict]:
    """Undo items for a batch's log rows: every row whose write may have reached
    Graylog. A "failed" row too: a timeout or a "stored something else" can follow a
    PUT that landed (found by a review); the `expect` check skips any definition
    whose notifications are not what that batch left there."""
    out = []
    for r in rows:
        if r.get("status") not in ("applied", "pending", "failed"):
            continue
        out.append({"id": r["definition_id"], "title": r.get("title") or "",
                    "target": r["before_notifications"],
                    "expect": [x.get("notification_id") for x in r["after_notifications"]],
                    "row_id": r["id"]})
    return out
