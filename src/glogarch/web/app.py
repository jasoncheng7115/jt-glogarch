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


class APIAuthMiddleware(BaseHTTPMiddleware):
    """Protect /api/* endpoints — require session authentication.

    /api/health is exempt so external monitoring tools (Prometheus blackbox,
    k8s probes, Uptime Kuma) can poll it without credentials.
    """

    PUBLIC_API_PATHS = {"/api/health"}

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/api/") and request.url.path not in self.PUBLIC_API_PATHS:
            if not request.session.get("authenticated", False):
                return JSONResponse({"error": "Not authenticated"}, status_code=401)
        return await call_next(request)


def _cleanup_stale_jobs(db):
    """Mark all running jobs as failed on startup — they were interrupted by restart."""
    try:
        from datetime import datetime
        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        count = db.conn.execute(
            "UPDATE jobs SET status='failed', error_message='Interrupted by service restart', "
            "completed_at=? WHERE status='running'", (now,),
        ).rowcount
        db.conn.commit()
        if count:
            log.info("Cleaned up stale running jobs", count=count)
    except Exception:
        pass


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.log_level)

    db = ArchiveDB(settings.database_path)
    db.connect()

    scheduler = ArchiveScheduler(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Clean up stale running jobs from previous crashes/restarts
        _cleanup_stale_jobs(db)
        scheduler.start()
        yield
        scheduler.stop()
        db.close()

    app = FastAPI(
        title="jt-glogarch",
        description="Graylog Open Archive",
        version="1.3.1",
        lifespan=lifespan,
    )

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

    app.add_middleware(APIAuthMiddleware)
    app.add_middleware(SessionMiddleware, secret_key=session_secret,
                       same_site="lax", max_age=28800)

    app.state.db = db
    app.state.settings = settings
    app.state.scheduler = scheduler

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
