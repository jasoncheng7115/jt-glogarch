"""HTML page routes for jt-glogarch web UI with Graylog auth."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from glogarch import __version__ as _APP_VERSION

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
    return request.session.get("authenticated", False)


def _is_unconfigured(request: Request) -> bool:
    """Fresh install with no Graylog server yet → send the user to /setup."""
    return len(request.app.state.settings.servers) == 0


_VALID_LOGIN_ERRORS = {"auth_failed", "graylog_offline_with_local", "graylog_offline"}

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
        return RedirectResponse(url="/login", status_code=303)
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
    return _render("login.html", request, {"error": error, "csrf_token": csrf_token})


@router.post("/login")
async def login_submit(request: Request):
    form = await request.form()
    username = form.get("username", "")
    password = form.get("password", "")

    # Anti-CSRF: the submitted token must match the one issued on GET /login.
    sess_token = request.session.get("csrf_token", "")
    if not sess_token or form.get("csrf_token", "") != sess_token:
        return RedirectResponse(url="/login?error=auth_failed", status_code=303)

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
            request.session["authenticated"] = True
            request.session["username"] = "localadmin"
            request.session["emergency_mode"] = True
            _audit(request, "login_success", "User: localadmin (local admin)")
            return RedirectResponse(url="/", status_code=303)
        # Wrong password for the reserved local account — never forward it to
        # Graylog (it isn't a Graylog user); reject directly.
        _audit(request, "login_failed", "User: localadmin")
        return RedirectResponse(url="/login?error=auth_failed", status_code=303)

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
    for server in servers:
        try:
            async with httpx.AsyncClient(verify=server.verify_ssl, timeout=10.0) as client:
                resp = await client.get(
                    f"{server.url.rstrip('/')}/api/system",
                    auth=httpx.BasicAuth(username, password),
                    headers={"Accept": "application/json"},
                )
                if resp.status_code == 200:
                    display_name = username
                    if len(username) > 30:
                        display_name = "token-user"
                    request.session["authenticated"] = True
                    request.session["username"] = display_name
                    _audit(request, "login_success", f"User: {display_name} @ {server.name}")
                    return RedirectResponse(url="/", status_code=303)
                # This server responded but rejected the credentials — Graylog is
                # reachable, so keep trying the other servers before giving up.
                graylog_ok = True
        except Exception:
            # This server is unreachable — try the next one.
            continue

    _audit(request, "login_failed", f"User: {username}")

    if not graylog_ok:
        # Graylog unreachable — tell user what's happening
        has_local = bool(settings.web.localadmin_password_hash)
        error = "graylog_offline_with_local" if has_local else "graylog_offline"
    else:
        error = "auth_failed"
    return RedirectResponse(url=f"/login?error={error}", status_code=303)


def _audit(request: Request, action: str, detail: str = ""):
    """Helper to log audit events."""
    try:
        db = request.app.state.db
        username = request.session.get("username", "")
        ip = request.client.host if request.client else ""
        db.audit(action, detail, username, ip)
    except Exception:
        pass


@router.get("/logout")
def logout(request: Request):
    _audit(request, "logout")
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


# --- Protected pages ---

@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    if _is_unconfigured(request):
        return RedirectResponse(url="/setup", status_code=303)
    if not _is_logged_in(request):
        return RedirectResponse(url="/login", status_code=303)
    return _render("index.html", request, {"page": "dashboard"})


@router.get("/archives", response_class=HTMLResponse)
def archives_page(request: Request):
    if not _is_logged_in(request):
        return RedirectResponse(url="/login", status_code=303)
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
        return RedirectResponse(url="/login", status_code=303)
    return _render("index.html", request, {"page": "jobs"})


@router.get("/schedules", response_class=HTMLResponse)
def schedules_page(request: Request):
    if not _is_logged_in(request):
        return RedirectResponse(url="/login", status_code=303)
    return _render("index.html", request, {"page": "schedules"})


@router.get("/notify-settings", response_class=HTMLResponse)
def notify_settings_page(request: Request):
    if not _is_logged_in(request):
        return RedirectResponse(url="/login", status_code=303)
    return _render("index.html", request, {"page": "notify-settings"})


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    """Connection settings — Graylog servers + OpenSearch (Web UI editable)."""
    if _is_unconfigured(request):
        return RedirectResponse(url="/setup", status_code=303)
    if not _is_logged_in(request):
        return RedirectResponse(url="/login", status_code=303)
    return _render("index.html", request, {"page": "settings"})


@router.get("/reports", response_class=HTMLResponse)
def reports_page(request: Request):
    """PDF reports (beta) — Graylog dashboard → branded PDF."""
    if _is_unconfigured(request):
        return RedirectResponse(url="/setup", status_code=303)
    if not _is_logged_in(request):
        return RedirectResponse(url="/login", status_code=303)
    return _render("index.html", request, {"page": "reports"})


@router.get("/logs", response_class=HTMLResponse)
def logs_page(request: Request):
    if not _is_logged_in(request):
        return RedirectResponse(url="/login", status_code=303)
    return _render("index.html", request, {"page": "logs"})


@router.get("/op-audit", response_class=HTMLResponse)
def op_audit_page(request: Request):
    if not _is_logged_in(request):
        return RedirectResponse(url="/login", status_code=303)
    return _render("index.html", request, {"page": "op-audit"})
