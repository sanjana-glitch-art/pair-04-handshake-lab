"""
Builds the FastAPI app for one Handshake service.

The six services share this code base (models, security, messaging) but
each container mounts only its own routers:

    student      /auth, /students, /preferences, /saved, /uploads/pictures
    company      /auth/company/signup, /employer/profile, /uploads/pictures
    job          /jobs, /employer/jobs
    application  /applications, /employer/applications
    event        /events, /employer/events
    assistant    /assistant

app.main still mounts everything in one process for local development
and the test suite.
"""

import os
import time
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ..database import ensure_indexes, get_database
from ..observability import log_event, new_trace_id, reset_trace_id, set_trace_id


def _cors_origins() -> list[str]:
    configured = os.getenv("CORS_ORIGINS", "")
    defaults = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:9040", "http://127.0.0.1:9040"]
    return [origin.strip() for origin in configured.split(",") if origin.strip()] or defaults


def create_app(service: str, routers: list[APIRouter], description: str = "") -> FastAPI:
    os.environ.setdefault("SERVICE_NAME", service)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        try:
            ensure_indexes()
        except Exception as error:  # Mongo may still be starting; readiness will report it.
            log_event("could not create indexes yet", error=str(error))
        yield

    app = FastAPI(
        lifespan=lifespan,
        title=f"Pair 4 Handshake {service} service" if service != "all" else "Pair 4 Handshake API",
        description=description or f"Pair 4 Handshake {service} service",
        version="2.0.0",
    )

    for router in routers:
        app.include_router(router)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Trace-Id"],
    )

    @app.middleware("http")
    async def trace_requests(request: Request, call_next):
        """
        Accepts or creates a trace_id, logs one line per request, and
        returns the id in X-Trace-Id.
        """

        trace_id = request.headers.get("x-trace-id") or new_trace_id()
        sampled = request.headers.get("x-trace-sample") == "1" or request.url.path.startswith("/assistant")
        tokens = set_trace_id(trace_id, sampled)
        started = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            log_event("request failed", method=request.method, path=request.url.path)
            reset_trace_id(tokens)
            raise

        elapsed = (time.perf_counter() - started) * 1000
        response.headers["X-Trace-Id"] = trace_id
        if not request.url.path.startswith("/health"):
            log_event("request", method=request.method, path=request.url.path,
                      status=response.status_code, ms=round(elapsed, 1))
        reset_trace_id(tokens)
        return response

    @app.get("/", tags=["Health"])
    def root():
        return {"message": f"Pair 4 Handshake {service} service is running"}

    @app.get("/health", tags=["Health"])
    def health():
        """
        Liveness: the process is up.
        """

        return {"status": "healthy", "service": service}

    @app.get("/health/ready", tags=["Health"])
    def ready():
        """
        Readiness: MongoDB answers a ping.
        """

        try:
            get_database().command("ping")
        except Exception:
            return JSONResponse(status_code=503, content={"status": "unhealthy", "service": service, "database": "unreachable"})
        return {"status": "healthy", "service": service, "database": "connected"}

    @app.get("/health/db", tags=["Health"], include_in_schema=False)
    def health_db():
        return ready()

    return app
