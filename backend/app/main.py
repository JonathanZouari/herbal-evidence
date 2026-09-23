import logging
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from threading import Lock

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from psycopg import errors as pg

from app import db
from app.api.v1 import router
from app.errors import AppError
from app.settings import get_settings

log = logging.getLogger("app")


def _error(status: int, code: str, message: str = "") -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message or code}}, status_code=status)


def create_app(open_pool: bool = True) -> FastAPI:
    s = get_settings()
    logging.basicConfig(level=s.log_level)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if open_pool:
            db.open_pool(s.database_url)
        yield
        if open_pool:
            db.close_pool()

    app = FastAPI(title="Herbal Evidence API", lifespan=lifespan,
                  docs_url=None if s.app_env == "production" else "/docs", redoc_url=None)

    # ponytail: in-memory per-IP sliding window; only correct with ONE backend replica. Move to the DB/proxy to scale out.
    hits: dict[str, deque] = defaultdict(deque)
    hits_lock = Lock()

    @app.middleware("http")
    async def guard(request: Request, call_next):
        # Railway's edge sets X-Real-IP; X-Forwarded-For's left-most entry is client-controlled, so don't trust it.
        ip = request.headers.get("x-real-ip") or (request.client.host if request.client else "?")
        now = time.monotonic()
        with hits_lock:
            q = hits[ip]
            while q and now - q[0] > 60:
                q.popleft()
            limited = len(q) >= s.ip_requests_per_minute
            if not limited:
                q.append(now)
        response = _error(429, "rate_limited") if limited else await call_next(request)
        response.headers.update({
            "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "Cache-Control": "no-store",
        })
        if s.app_env == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    # added after `guard` so it runs first (outermost): CORS headers also land on 429s
    app.add_middleware(CORSMiddleware, allow_origins=s.cors_origins, allow_credentials=False,
                       allow_methods=["GET", "POST", "PUT", "PATCH"], allow_headers=["Authorization", "Content-Type"])

    @app.exception_handler(AppError)
    async def app_error(_: Request, e: AppError):
        return _error(e.status, e.code, e.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, e: RequestValidationError):
        return JSONResponse({"error": {"code": "validation_error", "message": "invalid input",
                                       "fields": [".".join(map(str, x["loc"])) for x in e.errors()]}}, status_code=422)

    @app.exception_handler(pg.CheckViolation)
    async def check_violation(_: Request, e: pg.CheckViolation):
        return _error(409, "invalid_transition" if "transition" in str(e) else "constraint_violation")

    @app.exception_handler(Exception)
    async def unhandled(_: Request, e: Exception):
        log.exception("unhandled error")
        return _error(500, "internal_error")

    app.include_router(router)
    return app


app = create_app()
