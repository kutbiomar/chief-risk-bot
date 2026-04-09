from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.deps import get_db
from backend.models.portfolio import PortfolioSnapshot
from backend.routers.auth import require_cookie_csrf, require_session
from backend.schemas.overlay import (
    AumTriangulationResponse,
    FactorScoreResponse,
    OverlayRunResponse,
    OverlayStressResponse,
    RegimeResponse,
    StressScenarioResponse,
    TriangulationFactorResponse,
)
from backend.services.overlay.alert_engine import compute_overlay_alerts
from backend.services.overlay.pipeline import run_overlay_for_snapshot
from backend.services.overlay.stress_scenarios import compute_stress_scenarios
from backend.services.overlay import ensure_overlay_state
from backend.services.var import compute_var_for_snapshot

router = APIRouter(prefix="/overlay", tags=["overlay"])


def _resolve_current_snapshot(db: Session, workspace_id: str) -> PortfolioSnapshot:
    snapshot = db.scalar(
        select(PortfolioSnapshot).where(
            PortfolioSnapshot.workspace_id == workspace_id,
            PortfolioSnapshot.is_current.is_(True),
        )
    )
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio snapshot not found")
    return snapshot


@router.get("/factors", response_model=list[FactorScoreResponse])
def get_factors(
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> list[FactorScoreResponse]:
    _, user = auth
    snapshot = _resolve_current_snapshot(db, user.workspace_id)
    overlay_state = ensure_overlay_state(db, snapshot)
    db.commit()
    return [
        FactorScoreResponse(
            factor_key=row.factor_key,
            factor_type=row.factor_type,
            label=row.label,
            score=row.score,
            direction=row.direction,
            z_score=row.z_score,
            primary_driver=row.primary_driver,
            confidence=row.confidence,
            sentiment_modifier=row.sentiment_modifier,
            signal_payload_json=row.signal_payload_json,
            as_of_date=row.as_of_date,
        )
        for row in overlay_state["factor_scores"]
    ]


@router.get("/regime", response_model=RegimeResponse)
def get_regime(
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> RegimeResponse:
    _, user = auth
    snapshot = _resolve_current_snapshot(db, user.workspace_id)
    overlay_state = ensure_overlay_state(db, snapshot)
    db.commit()
    regime = overlay_state["regime"]
    return RegimeResponse(
        regime=regime.regime,
        trigger_signal=regime.trigger_signal,
        vix_level=regime.vix_level,
        credit_spread_bps=regime.credit_spread_bps,
        methodology_note=regime.methodology_note,
        as_of_date=regime.as_of_date,
        created_at=regime.created_at,
    )


@router.get("/aum-triangulation", response_model=AumTriangulationResponse)
def get_aum_triangulation(
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> AumTriangulationResponse:
    _, user = auth
    snapshot = _resolve_current_snapshot(db, user.workspace_id)
    overlay_state = ensure_overlay_state(db, snapshot)
    db.commit()
    triangulation = overlay_state["triangulation"]
    factor_rows = [TriangulationFactorResponse(**row) for row in triangulation["factors"]]
    top_rows = [TriangulationFactorResponse(**row) for row in triangulation["top_risk_contributors"]]
    return AumTriangulationResponse(
        as_of_date=overlay_state["as_of_date"],
        composite_score=triangulation["composite_score"],
        aum_at_risk_usd=triangulation["aum_at_risk_usd"],
        factors=factor_rows,
        top_risk_contributors=top_rows,
    )


@router.get("/stress", response_model=OverlayStressResponse)
def get_overlay_stress(
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> OverlayStressResponse:
    _, user = auth
    snapshot = _resolve_current_snapshot(db, user.workspace_id)
    overlay_state = ensure_overlay_state(db, snapshot)
    var_result = compute_var_for_snapshot(db, snapshot)
    stress = compute_stress_scenarios(db, overlay_state["triangulation"])
    alerts = compute_overlay_alerts(overlay_state["triangulation"], overlay_state["regime"], var_result)
    db.commit()
    return OverlayStressResponse(
        as_of_date=overlay_state["as_of_date"],
        regime=overlay_state["regime"].regime,
        scenarios=[StressScenarioResponse(**row) for row in stress],
        alerts=alerts,
    )


@router.post("/run", response_model=OverlayRunResponse, dependencies=[Depends(require_cookie_csrf)])
def run_overlay(
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> OverlayRunResponse:
    _, user = auth
    snapshot = _resolve_current_snapshot(db, user.workspace_id)
    result = run_overlay_for_snapshot(db, snapshot, created_by=user.id)
    db.commit()
    return OverlayRunResponse(job_id=result.job.id, status=result.job.status, **result.summary)
