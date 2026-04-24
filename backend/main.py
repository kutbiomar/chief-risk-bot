from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging
import os
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.routers import (
    auth_router,
    briefings_router,
    cockpit_router,
    documents_router,
    health_router,
    ingest_router,
    liquidity_router,
    market_router,
    onboarding_router,
    overlay_router,
    portfolio_router,
    risk_router,
    settings_router,
    var_router,
)
from backend.services.observability import (
    configure_json_logging,
    finish_request_observation,
    monotonic_ms,
    record_request_metrics,
    start_request_observation,
)
from backend.services.scheduler import get_scheduler_manager


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_json_logging()
    manager = get_scheduler_manager()
    app.state.scheduler_manager = manager
    scheduler_allowed = not bool(os.environ.get("PYTEST_CURRENT_TEST"))
    if scheduler_allowed:
        manager.start()
    try:
        yield
    finally:
        if scheduler_allowed:
            manager.shutdown()


def create_app() -> FastAPI:
    settings = get_settings()
    settings.validate_runtime()

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    logger = logging.getLogger("chiefriskbot.request")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_observability(request: Request, call_next):  # noqa: ANN001
        request_id = request.headers.get("x-request-id") or str(uuid4())
        request_started = monotonic_ms()
        observation_token = start_request_observation()
        response = None
        try:
            response = await call_next(request)
        finally:
            observation = finish_request_observation(observation_token)
            elapsed_ms = max(monotonic_ms() - request_started, 0.0)
            status_code = response.status_code if response is not None else 500
            record_request_metrics(
                status_code=status_code,
                duration_ms=elapsed_ms,
                db_query_count=observation["db_query_count"],
                db_query_ms=observation["db_query_ms"],
            )
            logger.info(
                "request_complete",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "latency_ms": round(elapsed_ms, 2),
                    "db_query_count": int(observation["db_query_count"]),
                    "db_query_ms": round(observation["db_query_ms"], 2),
                },
            )
        if response is not None:
            response.headers["X-Request-ID"] = request_id
            response.headers.setdefault("X-Content-Type-Options", "nosniff")
            response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
            response.headers.setdefault("X-Frame-Options", "DENY")
            if settings.environment != "development":
                response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains; preload")
        return response

    app.include_router(auth_router, prefix="/api")
    app.include_router(briefings_router, prefix="/api")
    app.include_router(cockpit_router, prefix="/api")
    app.include_router(documents_router, prefix="/api")
    app.include_router(health_router, prefix="/api")
    app.include_router(ingest_router, prefix="/api")
    app.include_router(liquidity_router, prefix="/api")
    app.include_router(market_router, prefix="/api")
    app.include_router(onboarding_router, prefix="/api")
    app.include_router(overlay_router, prefix="/api")
    app.include_router(portfolio_router, prefix="/api")
    app.include_router(risk_router, prefix="/api")
    app.include_router(settings_router, prefix="/api")
    app.include_router(var_router, prefix="/api")

    return app


app = create_app()
