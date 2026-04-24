from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.deps import get_db
from backend.models.analytics import VarResult
from backend.models.portfolio import PortfolioSnapshot
from backend.routers.auth import require_cookie_csrf, require_session
from backend.schemas.analytics import VarContribution, VarResponse
from backend.services.var import compute_var_for_snapshot

router = APIRouter(prefix="/var", tags=["var"])


def _serialize(result: VarResult) -> VarResponse:
    return VarResponse(
        id=result.id,
        snapshot_id=result.snapshot_id,
        var_1d_95=result.var_1d_95,
        var_1d_99=result.var_1d_99,
        cvar_1d_95=result.cvar_1d_95,
        cvar_1d_99=result.cvar_1d_99,
        max_drawdown_1y=result.max_drawdown_1y,
        worst_scenario_date=result.worst_scenario_date,
        worst_scenario_loss=result.worst_scenario_loss,
        lookback_days=result.lookback_days,
        effective_lookback_days=result.effective_lookback_days,
        methodology=result.methodology,
        model_coverage_pct=result.model_coverage_pct,
        unmodeled_value_usd=result.unmodeled_value_usd,
        position_contributions=[VarContribution(**item) for item in json.loads(result.position_contributions_json)],
        assumptions=json.loads(result.assumptions_json),
        computed_at=result.computed_at,
    )


@router.post("/compute", response_model=VarResponse, dependencies=[Depends(require_cookie_csrf)])
def compute_var(
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> VarResponse:
    _, user = auth
    snapshot = db.scalar(
        select(PortfolioSnapshot).where(
            PortfolioSnapshot.workspace_id == user.workspace_id,
            PortfolioSnapshot.is_current.is_(True),
        )
    )
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio snapshot not found")
    result = compute_var_for_snapshot(db, snapshot)
    db.commit()
    db.refresh(result)
    return _serialize(result)
