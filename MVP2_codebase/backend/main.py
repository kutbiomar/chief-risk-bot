from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .database import SessionLocal
from .routers import (
    alerts_router,
    auth_router,
    briefings_router,
    deals_router,
    documents_router,
    funds_router,
    health_router,
    settings_router,
)
from .services.bootstrap import ensure_demo_workspace


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if settings.environment == "development":
        with SessionLocal() as db:
            ensure_demo_workspace(db)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth_router, prefix="/api")
    app.include_router(funds_router, prefix="/api")
    app.include_router(deals_router, prefix="/api")
    app.include_router(documents_router, prefix="/api")
    app.include_router(briefings_router, prefix="/api")
    app.include_router(alerts_router, prefix="/api")
    app.include_router(settings_router, prefix="/api")
    app.include_router(health_router, prefix="/api")

    frontend_dir = Path(__file__).resolve().parents[1] / "frontend"
    if frontend_dir.exists():
        app.mount("/app", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

        @app.get("/", include_in_schema=False)
        def root() -> RedirectResponse:
            return RedirectResponse(url="/app/login.html")

    return app


app = create_app()
