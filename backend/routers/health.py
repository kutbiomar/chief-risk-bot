from __future__ import annotations

import json
from datetime import datetime, timezone
from time import perf_counter
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.deps import get_db
from backend.schemas.health import DependencyHealth, HealthResponse, ObservabilitySnapshot
from backend.services.observability import metrics_snapshot

router = APIRouter(tags=["health"])


def _timed_check(fn) -> tuple[bool, str, float]:  # noqa: ANN001
    started = perf_counter()
    try:
        detail = fn()
        elapsed = max((perf_counter() - started) * 1000.0, 0.0)
        return True, str(detail), elapsed
    except Exception as exc:  # noqa: BLE001
        elapsed = max((perf_counter() - started) * 1000.0, 0.0)
        return False, str(exc), elapsed


def _check_database(db: Session) -> str:
    db.execute(text("SELECT 1"))
    return "Database reachable"


def _check_supabase_auth() -> str:
    settings = get_settings()
    if settings.auth_mode != "supabase":
        return "Supabase auth disabled"
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError("Supabase auth configuration missing")
    request = Request(
        f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users?{urlencode({'page': 1, 'per_page': 1})}",
        headers={
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "apikey": settings.supabase_service_role_key,
        },
        method="GET",
    )
    with urlopen(request, timeout=4) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if "users" not in payload:
        raise RuntimeError("Unexpected Supabase auth response")
    return "Supabase auth admin API reachable"


def _check_supabase_storage() -> str:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return "Supabase storage not configured"
    bucket = settings.supabase_storage_bucket
    if not bucket:
        raise RuntimeError("Supabase storage bucket missing")
    request = Request(
        f"{settings.supabase_url.rstrip('/')}/storage/v1/bucket/{bucket}",
        headers={
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "apikey": settings.supabase_service_role_key,
        },
        method="GET",
    )
    with urlopen(request, timeout=4) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if str(payload.get("name", "")) != bucket:
        raise RuntimeError("Supabase storage bucket lookup failed")
    return f"Supabase storage bucket '{bucket}' reachable"


def _check_anthropic() -> str:
    settings = get_settings()
    if not settings.anthropic_api_key:
        return "Anthropic API key not configured"
    request = Request(
        "https://api.anthropic.com/v1/models",
        headers={
            "x-api-key": settings.anthropic_api_key,
            "anthropic-version": "2023-06-01",
        },
        method="GET",
    )
    with urlopen(request, timeout=4):
        pass
    return "Anthropic API reachable"


def _check_fred() -> str:
    settings = get_settings()
    if not settings.fred_api_key:
        return "FRED API key not configured"
    query = urlencode({"series_id": "VIXCLS", "api_key": settings.fred_api_key, "file_type": "json"})
    request = Request(
        f"https://api.stlouisfed.org/fred/series?{query}",
        method="GET",
    )
    with urlopen(request, timeout=4):
        pass
    return "FRED API reachable"


def _component_status(*, ok: bool, detail: str, latency_ms: float, failure_is_degraded: bool = False) -> DependencyHealth:
    if ok:
        return DependencyHealth(status="ok", detail=detail, latency_ms=round(latency_ms, 2))
    return DependencyHealth(
        status="degraded" if failure_is_degraded else "fail",
        detail=detail,
        latency_ms=round(latency_ms, 2),
    )


@router.get("/health", response_model=HealthResponse)
def healthcheck(db: Session = Depends(get_db)) -> HealthResponse:
    settings = get_settings()
    components: dict[str, DependencyHealth] = {}

    db_ok, db_detail, db_ms = _timed_check(lambda: _check_database(db))
    components["database"] = _component_status(ok=db_ok, detail=db_detail, latency_ms=db_ms)

    auth_ok, auth_detail, auth_ms = _timed_check(_check_supabase_auth)
    if settings.auth_mode == "supabase":
        components["supabase_auth"] = _component_status(ok=auth_ok, detail=auth_detail, latency_ms=auth_ms)
    else:
        components["supabase_auth"] = DependencyHealth(status="skipped", detail=auth_detail, latency_ms=round(auth_ms, 2))

    storage_ok, storage_detail, storage_ms = _timed_check(_check_supabase_storage)
    if settings.supabase_url and settings.supabase_service_role_key:
        components["supabase_storage"] = _component_status(ok=storage_ok, detail=storage_detail, latency_ms=storage_ms)
    else:
        components["supabase_storage"] = DependencyHealth(
            status="skipped",
            detail=storage_detail,
            latency_ms=round(storage_ms, 2),
        )

    anthropic_ok, anthropic_detail, anthropic_ms = _timed_check(_check_anthropic)
    anthropic_configured = bool(settings.anthropic_api_key)
    components["anthropic"] = (
        _component_status(ok=anthropic_ok, detail=anthropic_detail, latency_ms=anthropic_ms, failure_is_degraded=True)
        if anthropic_configured
        else DependencyHealth(status="skipped", detail=anthropic_detail, latency_ms=round(anthropic_ms, 2))
    )

    fred_ok, fred_detail, fred_ms = _timed_check(_check_fred)
    fred_configured = bool(settings.fred_api_key)
    components["fred"] = (
        _component_status(ok=fred_ok, detail=fred_detail, latency_ms=fred_ms, failure_is_degraded=True)
        if fred_configured
        else DependencyHealth(status="skipped", detail=fred_detail, latency_ms=round(fred_ms, 2))
    )

    statuses = {component.status for component in components.values()}
    overall_status = "ok"
    if "fail" in statuses:
        overall_status = "fail"
    elif "degraded" in statuses:
        overall_status = "degraded"

    snapshot = metrics_snapshot()
    return HealthResponse(
        status=overall_status,
        environment=settings.environment,
        checked_at=datetime.now(tz=timezone.utc).isoformat(),
        components=components,
        metrics=ObservabilitySnapshot(**snapshot),
    )
