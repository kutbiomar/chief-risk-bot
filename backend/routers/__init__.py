from backend.routers.auth import router as auth_router
from backend.routers.briefings import router as briefings_router
from backend.routers.cockpit import router as cockpit_router
from backend.routers.documents import router as documents_router
from backend.routers.health import router as health_router
from backend.routers.ingest import router as ingest_router
from backend.routers.market import router as market_router
from backend.routers.onboarding import router as onboarding_router
from backend.routers.portfolio import router as portfolio_router
from backend.routers.risk import router as risk_router
from backend.routers.settings import router as settings_router
from backend.routers.var import router as var_router

__all__ = [
    "auth_router",
    "briefings_router",
    "cockpit_router",
    "documents_router",
    "health_router",
    "ingest_router",
    "market_router",
    "onboarding_router",
    "portfolio_router",
    "risk_router",
    "settings_router",
    "var_router",
]
