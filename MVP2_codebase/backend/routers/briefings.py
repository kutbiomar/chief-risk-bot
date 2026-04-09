from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import CurrentUser, get_current_user, get_db
from ..models.content import WeeklyBriefing
from ..services.briefings import export_briefing_pdf, generate_briefing, publish_briefing

router = APIRouter(prefix="/briefings", tags=["briefings"])


class BriefingResponse(BaseModel):
    id: str
    version: int
    status: str
    week_label: str
    output: dict[str, Any]
    pdf_path: Optional[str] = None
    created_at: Any
    published_at: Optional[Any] = None


class BriefingListResponse(BaseModel):
    total: int
    items: list[BriefingResponse]


class MessageResponse(BaseModel):
    detail: str


def _serialize(briefing: WeeklyBriefing) -> BriefingResponse:
    return BriefingResponse(
        id=briefing.id,
        version=briefing.version,
        status=briefing.status,
        week_label=briefing.week_label,
        output=briefing.output_json,
        pdf_path=briefing.pdf_path,
        created_at=briefing.created_at,
        published_at=briefing.published_at,
    )


def _get_briefing_or_404(db: Session, workspace_id: str, briefing_id: str) -> WeeklyBriefing:
    briefing = db.scalar(
        select(WeeklyBriefing).where(
            WeeklyBriefing.id == briefing_id,
            WeeklyBriefing.workspace_id == workspace_id,
        )
    )
    if briefing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Briefing not found")
    return briefing


@router.post("/generate", response_model=BriefingResponse)
def generate(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BriefingResponse:
    briefing = generate_briefing(db, user.workspace_id, user.id)
    db.commit()
    db.refresh(briefing)
    return _serialize(briefing)


@router.get("", response_model=BriefingListResponse)
def list_briefings(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BriefingListResponse:
    items = db.scalars(
        select(WeeklyBriefing)
        .where(WeeklyBriefing.workspace_id == user.workspace_id)
        .order_by(WeeklyBriefing.created_at.desc())
    ).all()
    return BriefingListResponse(total=len(items), items=[_serialize(item) for item in items])


@router.get("/{briefing_id}", response_model=BriefingResponse)
def get_briefing(
    briefing_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BriefingResponse:
    briefing = _get_briefing_or_404(db, user.workspace_id, briefing_id)
    return _serialize(briefing)


@router.post("/{briefing_id}/publish", response_model=MessageResponse)
def publish(
    briefing_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    briefing = _get_briefing_or_404(db, user.workspace_id, briefing_id)
    publish_briefing(briefing, user.id)
    db.commit()
    return MessageResponse(detail="Briefing published")


@router.get("/{briefing_id}/export/pdf")
def export_pdf(
    briefing_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    briefing = _get_briefing_or_404(db, user.workspace_id, briefing_id)
    path = export_briefing_pdf(db, briefing, user.workspace_id)
    db.commit()
    export_path = Path(path)
    media_type = "application/pdf" if export_path.suffix.lower() == ".pdf" else "text/html"
    return FileResponse(
        export_path,
        media_type=media_type,
        filename=f"{briefing.week_label}_v{briefing.version}{export_path.suffix}",
    )
