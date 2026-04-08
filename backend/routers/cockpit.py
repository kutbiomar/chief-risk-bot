from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.deps import get_db
from backend.models.analytics import VarResult
from backend.models.portfolio import PortfolioSnapshot, Position
from backend.routers.auth import require_session
from backend.routers.risk import get_register
from backend.routers.var import _serialize as serialize_var
from backend.schemas.analytics import CockpitResponse
from backend.services.portfolio import summarize_positions
from backend.services.var import compute_var_for_snapshot

router = APIRouter(prefix="/cockpit", tags=["cockpit"])


@router.get("", response_model=CockpitResponse)
def get_cockpit(
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> CockpitResponse:
    _, user = auth
    snapshot = db.scalar(
        select(PortfolioSnapshot).where(
            PortfolioSnapshot.workspace_id == user.workspace_id,
            PortfolioSnapshot.is_current.is_(True),
        )
    )
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio snapshot not found")
    positions = db.scalars(select(Position).where(Position.snapshot_id == snapshot.id)).all()
    portfolio_summary = summarize_positions(positions)
    var_result = db.scalar(select(VarResult).where(VarResult.snapshot_id == snapshot.id).order_by(VarResult.computed_at.desc()))
    if var_result is None:
        var_result = compute_var_for_snapshot(db, snapshot)
        db.commit()
        db.refresh(var_result)
    return CockpitResponse(
        snapshot_id=snapshot.id,
        portfolio_summary=portfolio_summary,
        var_result=serialize_var(var_result),
        risk_register=get_register(auth, db),
    )
