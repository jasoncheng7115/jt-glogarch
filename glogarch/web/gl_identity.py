# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Who to act as on Graylog: the person logged in to jt-glogarch.

Changes to Graylog's alerting config (event definitions, notifications) are made
AS the logged-in user, so Graylog's own permissions apply and its records show
the real person — not the service account in config.yaml.

At login the password is exchanged for a Graylog session (``POST
/api/system/sessions``); only that session id is kept, never the password. A
token login keeps the token. Both live in THIS process's memory only:

* never in the session cookie — Starlette's cookie is signed, not encrypted,
  so anything put there is readable by whoever holds the cookie;
* never on disk or in the DB.

The cookie carries a random handle that maps to the entry. A service restart
empties the store; the page then asks the user to sign in to Graylog again.
"""

from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass
from datetime import datetime

from glogarch.utils.logging import get_logger

log = get_logger("web.gl_identity")

_HANDLE_KEY = "gl_handle"
_MAX_HANDLES = 2000
_DEFAULT_TTL = 8 * 3600


@dataclass
class Identity:
    kind: str            # "session" | "token"
    secret: str
    username: str
    server_url: str
    verify_ssl: bool
    expires_at: float    # epoch seconds

    @property
    def auth(self) -> tuple[str, str]:
        return (self.secret, "session" if self.kind == "session" else "token")

    def expired(self) -> bool:
        return time.time() >= self.expires_at


# Changes on every service start. A login that kept a Graylog identity records it
# (``BOOT_KEY``); after a restart the identity is gone from memory, so that login is
# no longer whole and ``authz.session_is_authenticated`` signs it out. Otherwise the
# user stays "logged in" while every page acting as them asks for Graylog again.
BOOT_ID = secrets.token_hex(8)
BOOT_KEY = "gl_boot"

_store: dict[str, dict[str, Identity]] = {}
_lock = threading.Lock()


def parse_valid_until(s: str | None) -> float:
    """Graylog's `valid_until` ("2026-10-18T17:31:09.276+0000") → epoch."""
    if s:
        fmt = "%Y-%m-%dT%H:%M:%S.%f%z" if "." in s else "%Y-%m-%dT%H:%M:%S%z"
        try:
            return datetime.strptime(s, fmt).timestamp()
        except ValueError:
            log.debug("Unreadable Graylog session expiry; assuming the default", valid_until=s)
    return time.time() + _DEFAULT_TTL


def _handle(session: dict, create: bool) -> str | None:
    h = session.get(_HANDLE_KEY)
    if not h and create:
        h = secrets.token_urlsafe(24)
        session[_HANDLE_KEY] = h
    return h


def _prune_locked() -> None:
    for h in list(_store):
        for srv in [s for s, i in _store[h].items() if i.expired()]:
            del _store[h][srv]
        if not _store[h]:
            del _store[h]
    while len(_store) > _MAX_HANDLES:
        _store.pop(next(iter(_store)))


def put(session: dict, server_name: str, ident: Identity) -> None:
    h = _handle(session, create=True)
    with _lock:
        _prune_locked()
        _store.setdefault(h, {})[server_name] = ident


def get(session: dict, server_name: str) -> Identity | None:
    h = _handle(session, create=False)
    if not h:
        return None
    with _lock:
        ident = (_store.get(h) or {}).get(server_name)
        if ident and ident.expired():
            del _store[h][server_name]
            return None
        return ident


def drop(session: dict, server_name: str) -> Identity | None:
    h = _handle(session, create=False)
    with _lock:
        return (_store.get(h) or {}).pop(server_name, None) if h else None


def drop_all(session: dict) -> list[Identity]:
    h = session.get(_HANDLE_KEY)
    with _lock:
        return list((_store.pop(h, None) or {}).values()) if h else []


def signed_in_servers(session: dict) -> dict[str, str]:
    """{server_name: graylog_username} for this browser session."""
    h = _handle(session, create=False)
    if not h:
        return {}
    with _lock:
        return {s: i.username for s, i in (_store.get(h) or {}).items() if not i.expired()}


def mark_login(session: dict) -> None:
    """This login kept a Graylog identity in THIS process (see BOOT_ID)."""
    session[BOOT_KEY] = BOOT_ID


def login_lost(session: dict) -> bool:
    """A Graylog login whose identity was kept by an earlier process."""
    b = session.get(BOOT_KEY)
    return bool(b) and b != BOOT_ID
