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
from backend.schemas.analytics import CockpitResponse, OverlayFactorSummary, OverlaySummaryResponse
from backend.services.overlay.alert_engine import compute_overlay_alerts
from backend.services.overlay import ensure_overlay_state
from backend.services.overlay.stress_scenarios import compute_stress_scenarios
from backend.services.liquidity import get_liquidity_summary
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
    overlay_state = ensure_overlay_state(db, snapshot)
    triangulation = overlay_state["triangulation"]
    overlay_alerts = compute_overlay_alerts(triangulation, overlay_state["regime"], var_result)
    risk_register = get_register(auth, db) + [
        {
            "kind": item["kind"],
            "severity": item["severity"],
            "headline": item["headline"],
            "rule": item["rule"],
            "description": item["description"],
        }
        for item in overlay_alerts
    ]
    portfolio_summary["liquidity_summary"] = get_liquidity_summary(user.workspace_id, db)
    return CockpitResponse(
        snapshot_id=snapshot.id,
        portfolio_summary=portfolio_summary,
        var_result=serialize_var(var_result),
        risk_register=risk_register,
        overlay_summary=OverlaySummaryResponse(
            regime=overlay_state["regime"].regime,
            composite_score=triangulation["composite_score"],
            top_risk_factors=[
                OverlayFactorSummary(
                    factor_key=item["factor_key"],
                    label=item["label"],
                    score=item["risk_score"],
                    direction=item["direction"],
                    aum_exposed_usd=item["aum_exposed_usd"],
                )
                for item in triangulation["top_risk_contributors"][:5]
            ],
            as_of_date=overlay_state["as_of_date"],
        ),
    )
