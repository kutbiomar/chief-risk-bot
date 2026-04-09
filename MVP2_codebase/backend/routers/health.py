from __future__ import annotations

from fastapi import APIRouter

from ..config import get_settings
from ..schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def healthcheck() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(status="ok", environment=settings.environment, app_name=settings.app_name)
