"""TripNest AI application factory.

Run locally:  cd backend && uvicorn app.main:app --reload
API docs:     /docs (Swagger UI) and /redoc
"""
from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

from .config import settings
from .db import Base, SessionLocal, add_missing_columns, engine
from .models import Attraction
from .routers import catalog, discover
from .services import runtime, seed

VERSION = "1.0.0"
log = logging.getLogger("tripnest")

CSP = ("default-src 'self'; script-src 'self' https://cdnjs.cloudflare.com; "
       "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
       "font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https://tile.openstreetmap.org https://*.tile.openstreetmap.org https://upload.wikimedia.org https://thumb.wikimedia.org; "
       "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
DOCS_CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https://fastapi.tiangolo.com; "
            "frame-ancestors 'none'")
UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def startup() -> None:
    settings.validate()
    if settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(engine)  # production uses Alembic migrations instead
        add_missing_columns(engine)
    with SessionLocal() as db:
        seed.run(db)
        attrs = db.scalars(select(Attraction).options(selectinload(Attraction.destination))).all()
        specs = [runtime.spec(a) for a in attrs]
    runtime.load_or_train(specs)


def create_app() -> FastAPI:
    configure_logging()

    @asynccontextmanager
    async def lifespan(_app):
        startup()
        yield

    app = FastAPI(title="TripNest AI API", version=VERSION, lifespan=lifespan,
                  description="Tourist crowd prediction and smart destination recommendation for India. Crowd figures are "
                              "model predictions trained on demonstration data, not live visitor counts.")

    if settings.allowed_origins:
        app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=True,
                           allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
                           allow_headers=["Content-Type", "X-Requested-With", "Authorization"])

    @app.middleware("http")
    async def guard(request: Request, call_next):
        rid = uuid.uuid4().hex[:8]
        t0 = time.perf_counter()
        path = request.url.path
        # CSRF defence: state-changing API calls must carry a header that cross-site forms cannot set
        if (request.method in UNSAFE and path.startswith("/api/")
                and request.headers.get("x-requested-with") != "TripNest"
                and not request.headers.get("authorization", "").lower().startswith("bearer ")):
            resp = JSONResponse({"detail": "Missing X-Requested-With header"}, status_code=403)
        else:
            try:
                resp = await call_next(request)
            except Exception:  # never leak stack traces to clients
                log.exception("unhandled error rid=%s %s %s", rid, request.method, path)
                resp = JSONResponse({"detail": "Something went wrong on our side.", "request_id": rid}, status_code=500)
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Permissions-Policy"] = "geolocation=(self), camera=(), microphone=()"
        resp.headers["Content-Security-Policy"] = DOCS_CSP if path in ("/docs", "/redoc") else CSP
        if settings.is_production:
            resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        resp.headers["X-Request-ID"] = rid
        if path.startswith("/assets/"):
            resp.headers["Cache-Control"] = "no-cache"  # revalidate (ETag) so a redeploy is picked up at once
        if path.startswith("/api/"):
            log.info("rid=%s %s %s %s %.0fms", rid, request.method, path, resp.status_code,
                     (time.perf_counter() - t0) * 1000)
        return resp

    @app.get("/api/health", tags=["platform"])
    def health():
        try:
            with SessionLocal() as db:
                db.execute(text("SELECT 1"))
            db_status = "ok"
        except Exception:
            db_status = "error"
        m = runtime._state["model"]
        return {"status": "ok" if db_status == "ok" and m else "degraded", "version": VERSION, "database": db_status,
                "model": {"loaded": m is not None, "trained_at": m.info.get("trained_at") if m else None}}

    # Only the two core features are mounted. auth, planning, community, admin and legacy_extras are kept on disk, unmounted.
    for r in (discover.router, catalog.router):
        app.include_router(r)

    fe = settings.frontend_dir
    if (fe / "index.html").exists():
        app.mount("/assets", StaticFiles(directory=fe / "assets"), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa(full_path: str):
            if full_path.startswith("api/"):
                return JSONResponse({"detail": "Not found"}, status_code=404)
            return FileResponse(fe / "index.html", headers={"Cache-Control": "no-cache"})

    return app


app = create_app()
