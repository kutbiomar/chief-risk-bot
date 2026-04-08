from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.routers import (
    auth_router,
    briefings_router,
    cockpit_router,
    documents_router,
    health_router,
    ingest_router,
    market_router,
    onboarding_router,
    portfolio_router,
    risk_router,
    settings_router,
    var_router,
)


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(title=settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth_router, prefix="/api")
    app.include_router(briefings_router, prefix="/api")
    app.include_router(cockpit_router, prefix="/api")
    app.include_router(documents_router, prefix="/api")
    app.include_router(health_router, prefix="/api")
    app.include_router(ingest_router, prefix="/api")
    app.include_router(market_router, prefix="/api")
    app.include_router(onboarding_router, prefix="/api")
    app.include_router(portfolio_router, prefix="/api")
    app.include_router(risk_router, prefix="/api")
    app.include_router(settings_router, prefix="/api")
    app.include_router(var_router, prefix="/api")
    return app


app = create_app()
