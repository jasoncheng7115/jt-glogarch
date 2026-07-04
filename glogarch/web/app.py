"""FastAPI application factory."""

from __future__ import annotations

import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from glogarch.core.config import get_settings
from glogarch.core.database import ArchiveDB
from glogarch.scheduler.scheduler import ArchiveScheduler
from glogarch.utils.logging import get_logger, setup_logging

log = get_logger("web.app")

WEB_DIR = Path(__file__).parent
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses.

    Tuned so an OWASP ZAP baseline scan reports zero High/Medium findings:
    a Content-Security-Policy is always present (frame-ancestors/object-src/
    base-uri locked down), cookies/headers are hardened, sensitive (non-static)
    responses are marked no-store, and the Server banner is removed.

    The UI carries no inline scripts, inline event handlers, or inline style
    attributes (all via external JS event-delegation and CSS classes / CSSOM),
    so 'unsafe-inline' is not needed for either script-src or style-src.
    """

    CSP = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "frame-ancestors 'none'; "
        "form-action 'self'"
    )

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Content-Security-Policy"] = self.CSP
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=(), usb=()"
        )
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        # All subresources are same-origin, so require-corp is safe and clears
        # ZAP's COEP-missing check.
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        # Don't let uvicorn advertise itself (MutableHeaders has no .pop()).
        if "server" in response.headers:
            del response.headers["server"]
        # Sensitive (non-static) responses must never be cached by shared caches.
        if not request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-store, max-age=0"
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


class APIAuthMiddleware(BaseHTTPMiddleware):
    """Protect /api/* endpoints — require session authentication.

    /api/health is exempt so external monitoring tools (Prometheus blackbox,
    k8s probes, Uptime Kuma) can poll it without credentials.

    The first-run setup endpoints are also exempt: they are the only pre-auth
    write path and each self-gates to the unconfigured state (returns 403 once
    a server exists), so exposing them before login is safe.
    """

    PUBLIC_API_PATHS = {
        "/api/health",
        "/api/setup/status",
        "/api/setup/admin-password",
    }

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/api/") and request.url.path not in self.PUBLIC_API_PATHS:
            if not request.session.get("authenticated", False):
                return JSONResponse({"error": "Not authenticated"}, status_code=401)
        return await call_next(request)


def _cleanup_stale_jobs(db):
    """Mark all running jobs as failed on startup — they were interrupted by restart."""
    try:
        count = db.cleanup_stale_running_jobs()
        if count:
            log.info("Cleaned up stale running jobs", count=count)
    except Exception:
        pass
    # An import killed mid-flight (e.g. a service restart during an upgrade)
    # leaves its archive row stuck IMPORTING, which the per-archive lock then
    # makes permanently un-importable. Recover them on startup too.
    try:
        recovered = db.recover_stuck_importing()
        if recovered:
            log.info("Recovered stuck importing archives", count=recovered)
    except Exception:
        pass


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.log_level)

    db = ArchiveDB(settings.database_path)
    db.connect()

    # Share the DB connection with the scheduler to avoid having two
    # independent sqlite3 connections on the same file (which would
    # contend at the SQLite file-lock level causing "database is locked").
    scheduler = ArchiveScheduler(settings, db=db)

    # API Audit listener
    from glogarch.audit.listener import AuditSyslogListener
    audit_listener = AuditSyslogListener(settings.op_audit, db, settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Clean up stale running jobs from previous crashes/restarts
        _cleanup_stale_jobs(db)
        scheduler.start()
        await audit_listener.start()
        yield
        await audit_listener.stop()
        scheduler.stop()
        db.close()

    from glogarch import __version__
    # docs_url/redoc_url/openapi_url disabled: the interactive docs and the
    # OpenAPI schema sit at the app root (not under /api/), so APIAuthMiddleware
    # would not gate them — leaving them on would let an anonymous client
    # enumerate every endpoint. This is an internal admin tool, not a public API.
    app = FastAPI(
        title="jt-glogarch",
        description="Graylog Open Archive",
        version=__version__,
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    # Malformed JSON bodies must yield 400 (client error), not a 500 — see
    # OWASP A10 (Mishandling of Exceptional Conditions).
    import json as _json

    @app.exception_handler(_json.JSONDecodeError)
    async def _bad_json(_request, _exc):
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    # Session secret — persist across restarts
    secret_file = Path("/opt/jt-glogarch/.session_secret")
    if secret_file.exists():
        session_secret = secret_file.read_text().strip()
    else:
        session_secret = secrets.token_hex(32)
        try:
            secret_file.write_text(session_secret)
            secret_file.chmod(0o600)
        except Exception:
            pass

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(APIAuthMiddleware)
    # SameSite=strict + https_only(Secure) + HttpOnly(default) hardens the
    # session cookie against CSRF and interception — no cross-site nav needs it.
    app.add_middleware(SessionMiddleware, secret_key=session_secret,
                       same_site="strict", max_age=28800, https_only=True)

    app.state.db = db
    app.state.settings = settings
    app.state.scheduler = scheduler
    app.state.audit_listener = audit_listener

    # Mount static files
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    (STATIC_DIR / "css").mkdir(exist_ok=True)
    (STATIC_DIR / "js").mkdir(exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # Register routes
    from glogarch.web.routes.api import router as api_router
    from glogarch.web.routes.pages import router as pages_router

    app.include_router(api_router, prefix="/api")
    app.include_router(pages_router)

    return app
