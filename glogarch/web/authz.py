# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Who may sign in to jt-glogarch, and whether a session still counts.

A Graylog account signs in only if it holds a role listed in
`web.allowed_graylog_roles` (default Admin) or the `*` permission.

The roles are read at every sign-in: `GET /api/system/sessions` gives the
caller's user name for a password and a token login alike, and
`GET /api/users/{name}` gives its roles and permissions (measured on 6.3.15 and
7.1.9). If they cannot be read, the sign-in is refused.

Every session carries `auth_v`. A session without the current value counts as
signed out, so an upgrade makes everybody sign in again under the check.
"""
from __future__ import annotations

from urllib.parse import quote

import httpx

SESSION_AUTH_VERSION = 2


def session_is_authenticated(session) -> bool:
    """The ONE test of a signed-in session, used by pages and the API alike."""
    return bool(session.get("authenticated")) and session.get("auth_v") == SESSION_AUTH_VERSION


def mark_authenticated(session, username: str) -> None:
    session["authenticated"] = True
    session["auth_v"] = SESSION_AUTH_VERSION
    session["username"] = username


class RoleCheck:
    """Outcome of checking a Graylog account against the allowed roles."""

    def __init__(self, allowed: bool | None, username: str = "", roles: list | None = None, reason: str = ""):
        self.allowed = allowed          # None = could not be determined
        self.username = username
        self.roles = roles or []
        self.reason = reason


def role_allowed(roles, permissions, allowed_roles) -> bool:
    allowed = {str(r).strip().lower() for r in (allowed_roles or []) if str(r).strip()}
    if "*" in allowed:
        return True
    if "*" in (permissions or []):
        return True
    return any(str(r).strip().lower() in allowed for r in (roles or []))


async def check_graylog_role(client: httpx.AsyncClient, base_url: str, auth, allowed_roles) -> RoleCheck:
    """Read the signed-in account's roles from Graylog. Never raises.

    Anything that keeps the roles from being read gives `allowed=None`; the
    caller refuses the login then (fail closed).
    """
    base = base_url.rstrip("/")
    hdr = {"Accept": "application/json"}
    try:
        r = await client.get(f"{base}/api/system/sessions", auth=auth, headers=hdr)
        name = (r.json() or {}).get("username") if r.status_code == 200 else None
        if not name:
            return RoleCheck(None, reason=f"user name not readable (sessions HTTP {r.status_code})")
        r = await client.get(f"{base}/api/users/{quote(name, safe='')}", auth=auth, headers=hdr)
        if r.status_code != 200:
            return RoleCheck(None, name, reason=f"roles not readable (users HTTP {r.status_code})")
        u = r.json() or {}
        roles = list(u.get("roles") or [])
        ok = role_allowed(roles, u.get("permissions") or [], allowed_roles)
        return RoleCheck(ok, name, roles, "" if ok else "no allowed role")
    except Exception as e:  # network error, non-JSON body: refuse, say why
        return RoleCheck(None, reason=f"roles not readable ({type(e).__name__})")
