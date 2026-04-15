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


_VALID_LOGIN_ERRORS = {"auth_failed", "graylog_offline_with_local", "graylog_offline"}

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    error = request.query_params.get("error", "")
    if error not in _VALID_LOGIN_ERRORS:
        error = ""
    return _render("login.html", request, {"error": error})


@router.post("/login")
async def login_submit(request: Request):
    form = await request.form()
    username = form.get("username", "")
    password = form.get("password", "")

    settings = request.app.state.settings
    server = settings.get_server()
    graylog_ok = False

    # 1. Try Graylog API authentication (primary)
    import httpx
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
                _audit(request, "login_success", f"User: {display_name}")
                return RedirectResponse(url="/", status_code=303)
            # Graylog responded but auth failed — don't fall through
            graylog_ok = True
    except Exception:
        # Graylog unreachable — allow fallback to local admin
        pass

    # 2. Fallback: local emergency admin (only when Graylog is unreachable)
    if not graylog_ok:
        pw_hash = settings.web.localadmin_password_hash
        if pw_hash and username == "localadmin":
            import hashlib
            if hashlib.sha256(password.encode()).hexdigest() == pw_hash:
                request.session["authenticated"] = True
                request.session["username"] = "localadmin"
                request.session["emergency_mode"] = True
                _audit(request, "login_success", "User: localadmin (emergency, Graylog offline)")
                return RedirectResponse(url="/", status_code=303)

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
