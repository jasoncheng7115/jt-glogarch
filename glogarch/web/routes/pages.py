# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""HTML page routes for jt-glogarch web UI with Graylog auth."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from glogarch.web.authz import check_graylog_role, mark_authenticated, session_is_authenticated
from glogarch import __version__ as _APP_VERSION
from glogarch.utils.logging import get_logger

log = get_logger("web.pages")

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


def _render(name: str, request: Request, context: dict | None = None):
    # ``version`` is auto-injected into every template so there is only ONE
    # place to bump the version (``glogarch/__init__.py``). Never hardcode
    # version strings inside the HTML templates — always use ``{{ version }}``.
    ctx = {"request": request, "version": _APP_VERSION}
    if context:
        ctx.update(context)
    return templates.TemplateResponse(request=request, name=name, context=ctx)


def _is_logged_in(request: Request) -> bool:
    return session_is_authenticated(request.session)


def _is_unconfigured(request: Request) -> bool:
    """Fresh install with no Graylog server yet → send the user to /setup."""
    return len(request.app.state.settings.servers) == 0


_VALID_LOGIN_ERRORS = {"auth_failed", "graylog_offline_with_local", "graylog_offline",
                       "role_not_allowed", "role_unknown"}

_NO_RETURN = ("/login", "/logout", "/setup")


def _safe_next(nxt) -> str:
    """A page of this site to go to after the login, or "" (never another host:
    no scheme, no //, no backslash, printable ASCII only, not login/logout/setup)."""
    nxt = str(nxt or "")[:500]
    if (nxt.startswith("/") and not nxt.startswith("//") and "\\" not in nxt and "://" not in nxt
            and not nxt.startswith(_NO_RETURN) and all(32 < ord(c) < 127 for c in nxt)):
        return nxt
    return ""


def _login_url(error: str = "", nxt: str = "") -> str:
    from urllib.parse import urlencode
    q = {k: v for k, v in (("error", error), ("next", _safe_next(nxt))) if v}
    return "/login" + ("?" + urlencode(q) if q else "")


def _to_login(request: Request) -> RedirectResponse:
    """To the login page, carrying the page that was asked for (a link in a
    notification: /security?incident=12) in the URL. Not in the session: a link
    clicked in webmail is a cross-site navigation, the SameSite=Strict cookie is
    not sent, and a session written then would replace the signed-in one."""
    url = getattr(request, "url", None)
    nxt = ""
    if url is not None and getattr(request, "method", "") == "GET":
        nxt = url.path + ("?" + url.query if url.query else "")
    return RedirectResponse(url=_login_url(nxt="" if nxt == "/" else nxt), status_code=303)


def _after_login(nxt) -> str:
    """Where a successful login goes: the requested page when it is a page of this site, else /."""
    return _safe_next(nxt) or "/"


def _start_login(request: Request) -> None:
    """A successful login starts from an empty session: the Graylog identities of
    whoever used this browser before are dropped and the identity handle is new
    (a second sign-in kept the first user's identity on servers the second one
    could not reach, so Alerting and AI chat there ran as the first user)."""
    from glogarch.web import gl_identity
    gl_identity.drop_all(request.session)
    request.session.clear()


@router.get("/setup", response_class=HTMLResponse)
def setup_page(request: Request):
    """First-run setup wizard.

    The local admin password is the LAST step, so steps 1-3 (Graylog /
    OpenSearch / archive path) must write config BEFORE any password
    authenticates the session. We grant a pre-auth `setup_mode` session here —
    the sole place it is issued, and only on a still-unconfigured box. The
    APIAuthMiddleware honours it for the wizard's config endpoints; the admin-
    password step clears it. `setup_mode` also keeps the wizard reachable on a
    mid-wizard reload after step 1 has written the Graylog server (which flips
    _is_unconfigured to False)."""
    if _is_unconfigured(request):
        request.session["setup_mode"] = True
    elif not request.session.get("setup_mode"):
        return _to_login(request)
    return _render("setup.html", request)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if _is_unconfigured(request):
        return RedirectResponse(url="/setup", status_code=303)
    error = request.query_params.get("error", "")
    if error not in _VALID_LOGIN_ERRORS:
        error = ""
    # Issue a per-session anti-CSRF token embedded as a hidden field in the
    # login form and verified on POST (mitigates login CSRF; complements the
    # SameSite=Strict session cookie).
    import secrets
    csrf_token = secrets.token_urlsafe(32)
    request.session["csrf_token"] = csrf_token
    return _render("login.html", request, {"error": error, "csrf_token": csrf_token,
                                           "next": _safe_next(request.query_params.get("next"))})


@router.post("/login")
async def login_submit(request: Request):
    form = await request.form()
    username = form.get("username", "")
    password = form.get("password", "")
    nxt = _safe_next(form.get("next"))

    # Anti-CSRF: the submitted token must match the one issued on GET /login.
    sess_token = request.session.get("csrf_token", "")
    if not sess_token or form.get("csrf_token", "") != sess_token:
        return RedirectResponse(url=_login_url("auth_failed", nxt), status_code=303)

    settings = request.app.state.settings
    graylog_ok = False

    # 1. Local admin account. Set in the setup wizard (step 1, "Administrator
    #    Password"), this is a FIRST-CLASS login that always works — independent
    #    of whether Graylog is reachable. Check it up front so the reserved
    #    "localadmin" username is never forwarded to Graylog. (Previously this
    #    was an emergency-only fallback that only fired when EVERY Graylog was
    #    unreachable — so a user who set the wizard password could never log in
    #    with it while Graylog was up.)
    if username == "localadmin" and settings.web.localadmin_password_hash:
        import hashlib
        if hashlib.sha256(password.encode()).hexdigest() == settings.web.localadmin_password_hash:
            _start_login(request)
            mark_authenticated(request.session, "localadmin")
            request.session["emergency_mode"] = True
            _audit(request, "login_success", "User: localadmin (local admin)")
            return RedirectResponse(url=_after_login(nxt), status_code=303)
        # Wrong password for the reserved local account — never forward it to
        # Graylog (it isn't a Graylog user); reject directly.
        _audit(request, "login_failed", "User: localadmin")
        return RedirectResponse(url=_login_url("auth_failed", nxt), status_code=303)

    # 2. Try Graylog API authentication against EACH configured server, default
    #    first. With multiple Graylog clusters the account may exist on any of
    #    them, so the first server that accepts the credentials wins. (Fresh
    #    install with no servers → this loop is empty and we fall through to the
    #    local admin path.)
    import httpx
    servers = list(settings.servers)
    try:
        dflt = settings.get_server()
        servers = [dflt] + [s for s in servers if s.name != dflt.name]
    except ValueError:
        servers = []
    denied = None   # "role_not_allowed" / "role_unknown" once valid credentials were refused
    for server in servers:
        try:
            async with httpx.AsyncClient(verify=server.verify_ssl, timeout=10.0) as client:
                auth = httpx.BasicAuth(username, password)
                resp = await client.get(
                    f"{server.url.rstrip('/')}/api/system",
                    auth=auth,
                    headers={"Accept": "application/json"},
                )
                if resp.status_code == 200:
                    # Valid credentials are not enough: the account also needs
                    # an allowed role (web.allowed_graylog_roles).
                    rc = await check_graylog_role(client, server.url, auth,
                                                  settings.web.allowed_graylog_roles)
                    if not rc.allowed:
                        graylog_ok = True
                        if denied != "role_not_allowed":
                            denied = "role_not_allowed" if rc.allowed is False else "role_unknown"
                        who = rc.username or ("token-user" if len(username) > 30 else username)
                        _audit(request, "login_failed",
                               f"User: {who} @ {server.name}: {rc.reason}; roles={','.join(rc.roles)}")
                        log.warning("Graylog login refused: no role allowed to use jt-glogarch",
                                    user=who, server=server.name, reason=rc.reason, roles=rc.roles,
                                    allowed=settings.web.allowed_graylog_roles)
                        continue
                    display_name = rc.username or username
                    if len(display_name) > 30:
                        display_name = "token-user"
                    _start_login(request)
                    mark_authenticated(request.session, display_name)
                    request.session["gl_server"] = server.name
                    await _remember_graylog_identity(request, server, username, password)
                    await _remember_other_servers(request, server, servers, username, password)
                    from glogarch.web import gl_identity as _gli
                    if _gli.signed_in_servers(request.session):
                        # an identity kept on another server only also ends with this process
                        _gli.mark_login(request.session)
                    _audit(request, "login_success", f"User: {display_name} @ {server.name}")
                    return RedirectResponse(url=_after_login(nxt), status_code=303)
                # This server responded but rejected the credentials — Graylog is
                # reachable, so keep trying the other servers before giving up.
                graylog_ok = True
        except Exception as e:
            # This server is unreachable — try the next one.
            log.debug("Graylog server unreachable during login; trying the next one", error=str(e))
            continue

    if denied:
        return RedirectResponse(url=_login_url(denied, nxt), status_code=303)

    _audit(request, "login_failed", f"User: {username}")

    if not graylog_ok:
        # Graylog unreachable — tell user what's happening
        has_local = bool(settings.web.localadmin_password_hash)
        error = "graylog_offline_with_local" if has_local else "graylog_offline"
    else:
        error = "auth_failed"
    return RedirectResponse(url=_login_url(error, nxt), status_code=303)


def _audit(request: Request, action: str, detail: str = ""):
    """Helper to log audit events."""
    try:
        db = request.app.state.db
        username = request.session.get("username", "")
        ip = request.client.host if request.client else ""
        db.audit(action, detail, username, ip)
    except Exception as e:
        log.warning("Audit record could not be written - this operation is NOT in the audit log", error=str(e))


async def _remember_graylog_identity(request: Request, server, username: str, password: str) -> None:
    """Keep who this user is on Graylog, so Alerting changes are made AS them.

    The password is exchanged for a Graylog session right here and then dropped;
    a token login keeps the token. Memory only (see web/gl_identity.py). A
    failure never blocks the login — the Alerting page asks to sign in instead.
    """
    from glogarch.graylog import alerting as gla
    from glogarch.web import gl_identity
    host = request.client.host if request.client else ""
    try:
        d = await gla.create_session(server.url, username, password, server.verify_ssl, host)
        gl_identity.put(request.session, server.name, gl_identity.Identity(
            kind="session", secret=d["session_id"], username=d.get("username") or username,
            server_url=server.url, verify_ssl=server.verify_ssl,
            expires_at=gl_identity.parse_valid_until(d.get("valid_until"))))
        gl_identity.mark_login(request.session)
        return
    except Exception as e:
        log.info("No Graylog session for this login (token login, or sessions unavailable)",
                 server=server.name, error=str(e))
    if password == "token":  # nosec B105 - Graylog token auth: the password field is the literal word "token"
        # Graylog token auth: the token is the username, "token" the password.
        gl_identity.put(request.session, server.name, gl_identity.Identity(
            kind="token", secret=username, username="token-user", server_url=server.url,
            verify_ssl=server.verify_ssl, expires_at=gl_identity.parse_valid_until(None)))
        gl_identity.mark_login(request.session)


async def _remember_other_servers(request: Request, signed, servers, username: str, password: str) -> None:
    """The same account on the OTHER configured Graylog servers, best effort.

    The AI page and Alerting let the user pick a server; one that already knows
    this account should not ask for the same password again. A server that
    refuses it or does not answer within a few seconds is left out (the page
    asks for that one). The jt-glogarch login itself came from ``signed``.
    """
    import asyncio
    import httpx
    from glogarch.graylog import alerting as gla
    from glogarch.web import gl_identity
    host = request.client.host if request.client else ""
    others = [s for s in servers if s.name != signed.name]

    async def one(srv):
        try:
            if password == "token":  # nosec B105 - Graylog token auth: the password is the literal word "token"
                async with httpx.AsyncClient(verify=srv.verify_ssl, timeout=5.0) as c:
                    r = await c.get(srv.url.rstrip("/") + "/api/system", auth=httpx.BasicAuth(username, password),
                                    headers={"Accept": "application/json"})
                if r.status_code != 200:
                    return srv.name, None
                return srv.name, gl_identity.Identity(
                    kind="token", secret=username, username="token-user", server_url=srv.url,
                    verify_ssl=srv.verify_ssl, expires_at=gl_identity.parse_valid_until(None))
            d = await asyncio.wait_for(gla.create_session(srv.url, username, password, srv.verify_ssl, host), 5.0)
            return srv.name, gl_identity.Identity(
                kind="session", secret=d["session_id"], username=d.get("username") or username,
                server_url=srv.url, verify_ssl=srv.verify_ssl,
                expires_at=gl_identity.parse_valid_until(d.get("valid_until")))
        except Exception as e:
            log.info("This account is not signed in on another Graylog server", server=srv.name, error=str(e))
            return srv.name, None

    async def bounded(srv):
        try:
            return await asyncio.wait_for(one(srv), 8.0)
        except asyncio.TimeoutError:
            log.info("This account is not signed in on another Graylog server", server=srv.name, error="timeout")
            return srv.name, None

    for name, ident in await asyncio.gather(*(bounded(s) for s in others)):
        if ident:
            gl_identity.put(request.session, name, ident)


@router.get("/logout")
async def logout(request: Request):
    from glogarch.graylog import alerting as gla
    from glogarch.web import gl_identity
    _audit(request, "logout")
    for ident in gl_identity.drop_all(request.session):
        if ident.kind != "session":
            continue
        try:
            await gla.delete_session(ident.server_url, ident.secret, ident.verify_ssl)
        except Exception as e:
            log.info("Graylog session not closed at logout (it expires on its own)", error=str(e))
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)   # a logout remembers no page


# --- Protected pages ---

@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    if _is_unconfigured(request):
        return RedirectResponse(url="/setup", status_code=303)
    if not _is_logged_in(request):
        return _to_login(request)
    return _render("index.html", request, {"page": "dashboard"})


@router.get("/archives", response_class=HTMLResponse)
def archives_page(request: Request):
    if not _is_logged_in(request):
        return _to_login(request)
    return _render("index.html", request, {"page": "archives"})


@router.get("/export", response_class=HTMLResponse)
def export_page(request: Request):
    """Redirect to schedules — export is now triggered from there."""
    return RedirectResponse(url="/schedules", status_code=303)


@router.get("/import", response_class=HTMLResponse)
def import_page(request: Request):
    """Redirect to archives page — import is now done from there."""
    return RedirectResponse(url="/archives", status_code=303)


@router.get("/jobs", response_class=HTMLResponse)
def jobs_page(request: Request):
    if not _is_logged_in(request):
        return _to_login(request)
    return _render("index.html", request, {"page": "jobs"})


@router.get("/schedules", response_class=HTMLResponse)
def schedules_page(request: Request):
    if not _is_logged_in(request):
        return _to_login(request)
    return _render("index.html", request, {"page": "schedules"})


@router.get("/notify-settings", response_class=HTMLResponse)
def notify_settings_page(request: Request):
    if not _is_logged_in(request):
        return _to_login(request)
    return _render("index.html", request, {"page": "notify-settings"})


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    """Connection settings — Graylog servers + OpenSearch (Web UI editable)."""
    if _is_unconfigured(request):
        return RedirectResponse(url="/setup", status_code=303)
    if not _is_logged_in(request):
        return _to_login(request)
    return _render("index.html", request, {"page": "settings"})


@router.get("/reports", response_class=HTMLResponse)
def reports_page(request: Request):
    """PDF reports (beta) — Graylog dashboard → branded PDF."""
    if _is_unconfigured(request):
        return RedirectResponse(url="/setup", status_code=303)
    if not _is_logged_in(request):
        return _to_login(request)
    return _render("index.html", request, {"page": "reports"})


@router.get("/logs", response_class=HTMLResponse)
def logs_page(request: Request):
    if not _is_logged_in(request):
        return _to_login(request)
    return _render("index.html", request, {"page": "logs"})


@router.get("/packs", response_class=HTMLResponse)
def packs_page(request: Request):
    """Content packs: each connected Graylog's, and the Jason Tools library."""
    if _is_unconfigured(request):
        return RedirectResponse(url="/setup", status_code=303)
    if not _is_logged_in(request):
        return _to_login(request)
    return _render("index.html", request, {"page": "packs"})


@router.get("/alerting", response_class=HTMLResponse)
def alerting_page(request: Request):
    """Graylog event definitions + notifications, managed in bulk."""
    if _is_unconfigured(request):
        return RedirectResponse(url="/setup", status_code=303)
    if not _is_logged_in(request):
        return _to_login(request)
    return _render("index.html", request, {"page": "alerting"})


@router.get("/security", response_class=HTMLResponse)
def security_page(request: Request):
    """Security incidents found by the scheduled detectors (added 1.20)."""
    if _is_unconfigured(request):
        return RedirectResponse(url="/setup", status_code=303)
    if not _is_logged_in(request):
        return _to_login(request)
    return _render("index.html", request, {"page": "security"})


@router.get("/ai-chat", response_class=HTMLResponse)
def ai_chat_page(request: Request):
    """AI chat over the logs and incidents (added 1.21)."""
    if _is_unconfigured(request):
        return RedirectResponse(url="/setup", status_code=303)
    if not _is_logged_in(request):
        return _to_login(request)
    return _render("index.html", request, {"page": "ai-chat"})


@router.get("/op-audit", response_class=HTMLResponse)
def op_audit_page(request: Request):
    if not _is_logged_in(request):
        return _to_login(request)
    return _render("index.html", request, {"page": "op-audit"})
