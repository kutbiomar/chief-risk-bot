from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.deps import get_db
from backend.models.content import BriefingRun
from backend.models.portfolio import PortfolioSnapshot
from backend.routers.auth import require_cookie_csrf, require_session
from backend.schemas.auth import MessageResponse
from backend.schemas.content import BriefingListResponse, BriefingResponse
from backend.services.auth.session import utc_now
from backend.services.briefings import PdfExportUnavailableError, export_briefing_pdf, generate_briefing

router = APIRouter(prefix="/briefings", tags=["briefings"])


VALID_SCOPES = {"full", "daily", "risk", "assets", "liquidity", "scenarios"}


def _safe_parse_output(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _serialize(briefing: BriefingRun, scope: str = "full") -> BriefingResponse:
    return BriefingResponse(
        id=briefing.id,
        snapshot_id=briefing.snapshot_id,
        version=briefing.version,
        status=briefing.status,
        week_label=briefing.week_label,
        output=_safe_parse_output(briefing.output_json),
        scope=scope,
        pdf_path=briefing.pdf_path,
        created_at=briefing.created_at,
        published_at=briefing.published_at,
    )


def _enforce_generation_limits(db: Session, workspace_id: str) -> None:
    settings = get_settings()
    if not settings.ai_generation_enabled:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI briefing generation is temporarily disabled")

    today = datetime.now(timezone.utc).date()
    start = datetime.combine(today, time.min, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    daily_count = db.scalar(
        select(func.count(BriefingRun.id)).where(
            BriefingRun.workspace_id == workspace_id,
            BriefingRun.created_at >= start,
            BriefingRun.created_at < end,
        )
    ) or 0
    if settings.briefing_daily_quota > 0 and daily_count >= settings.briefing_daily_quota:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily briefing generation quota reached for this workspace.",
        )

    if settings.anthropic_daily_token_cap > 0:
        token_total = db.scalar(
            select(func.coalesce(func.sum(BriefingRun.input_tokens + BriefingRun.output_tokens), 0)).where(
                BriefingRun.created_at >= start,
                BriefingRun.created_at < end,
            )
        ) or 0
        if token_total >= settings.anthropic_daily_token_cap:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Global AI generation budget is exhausted for today.",
            )


@router.post("/generate", response_model=BriefingResponse, dependencies=[Depends(require_cookie_csrf)])
def generate(
    scope: str = Query(default="full"),
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> BriefingResponse:
    _, user = auth
    resolved_scope = scope if scope in VALID_SCOPES else "full"
    snapshot = db.scalar(
        select(PortfolioSnapshot).where(
            PortfolioSnapshot.workspace_id == user.workspace_id,
            PortfolioSnapshot.is_current.is_(True),
        )
    )
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio snapshot not found")
    _enforce_generation_limits(db, user.workspace_id)
    try:
        briefing = generate_briefing(db, snapshot, user.id, scope=resolved_scope)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    db.refresh(briefing)
    return _serialize(briefing, scope=resolved_scope)


@router.get("", response_model=BriefingListResponse)
def list_briefings(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> BriefingListResponse:
    _, user = auth
    items = db.scalars(
        select(BriefingRun)
        .where(BriefingRun.workspace_id == user.workspace_id)
        .order_by(BriefingRun.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return BriefingListResponse(items=[_serialize(item) for item in items])


@router.get("/{briefing_id}", response_model=BriefingResponse)
def get_briefing(
    briefing_id: str,
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> BriefingResponse:
    _, user = auth
    briefing = db.get(BriefingRun, briefing_id)
    if briefing is None or briefing.workspace_id != user.workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Briefing not found")
    return _serialize(briefing)


@router.post(
    "/{briefing_id}/publish",
    response_model=MessageResponse,
    dependencies=[Depends(require_cookie_csrf)],
)
def publish_briefing(
    briefing_id: str,
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> MessageResponse:
    _, user = auth
    briefing = db.get(BriefingRun, briefing_id)
    if briefing is None or briefing.workspace_id != user.workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Briefing not found")
    briefing.status = "published"
    briefing.published_at = utc_now()
    briefing.published_by = user.id
    db.commit()
    return MessageResponse(detail="Briefing published")


@router.get("/{briefing_id}/export/pdf")
def export_pdf(
    briefing_id: str,
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> FileResponse:
    _, user = auth
    briefing = db.get(BriefingRun, briefing_id)
    if briefing is None or briefing.workspace_id != user.workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Briefing not found")
    try:
        path = export_briefing_pdf(db, briefing, user.workspace_id)
    except PdfExportUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    db.commit()
    export_path = Path(path)
    filename = f"{briefing.week_label}_v{briefing.version}{export_path.suffix}"
    media_type = "application/pdf" if export_path.suffix.lower() == ".pdf" else "text/plain"
    return FileResponse(export_path, media_type=media_type, filename=filename)
