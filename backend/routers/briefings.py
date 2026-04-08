from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.deps import get_db
from backend.models.content import BriefingRun
from backend.models.portfolio import PortfolioSnapshot
from backend.routers.auth import require_session
from backend.schemas.auth import MessageResponse
from backend.schemas.content import BriefingListResponse, BriefingResponse
from backend.services.auth.session import utc_now
from backend.services.briefings import export_briefing_pdf, generate_briefing

router = APIRouter(prefix="/briefings", tags=["briefings"])


def _serialize(briefing: BriefingRun) -> BriefingResponse:
    return BriefingResponse(
        id=briefing.id,
        snapshot_id=briefing.snapshot_id,
        version=briefing.version,
        status=briefing.status,
        week_label=briefing.week_label,
        output=json.loads(briefing.output_json),
        pdf_path=briefing.pdf_path,
        created_at=briefing.created_at,
        published_at=briefing.published_at,
    )


@router.post("/generate", response_model=BriefingResponse)
def generate(
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> BriefingResponse:
    _, user = auth
    snapshot = db.scalar(
        select(PortfolioSnapshot).where(
            PortfolioSnapshot.workspace_id == user.workspace_id,
            PortfolioSnapshot.is_current.is_(True),
        )
    )
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio snapshot not found")
    try:
        briefing = generate_briefing(db, snapshot, user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    db.refresh(briefing)
    return _serialize(briefing)


@router.get("", response_model=BriefingListResponse)
def list_briefings(
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> BriefingListResponse:
    _, user = auth
    items = db.scalars(
        select(BriefingRun).where(BriefingRun.workspace_id == user.workspace_id).order_by(BriefingRun.created_at.desc())
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


@router.post("/{briefing_id}/publish", response_model=MessageResponse)
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
    path = export_briefing_pdf(db, briefing, user.workspace_id)
    db.commit()
    export_path = Path(path)
    filename = f"{briefing.week_label}_v{briefing.version}{export_path.suffix}"
    media_type = "application/pdf" if export_path.suffix.lower() == ".pdf" else "text/plain"
    return FileResponse(export_path, media_type=media_type, filename=filename)
