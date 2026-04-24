from .alerts import router as alerts_router
from .auth import router as auth_router
from .briefings import router as briefings_router
from .deals import router as deals_router
from .documents import router as documents_router
from .funds import router as funds_router
from .health import router as health_router
from .settings import router as settings_router

__all__ = [
    "alerts_router",
    "auth_router",
    "briefings_router",
    "deals_router",
    "documents_router",
    "funds_router",
    "health_router",
    "settings_router",
]
