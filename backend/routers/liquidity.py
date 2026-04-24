from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.deps import get_db
from backend.routers.auth import require_session
from backend.schemas.liquidity import LiquidityCashflowResponse, LiquiditySummaryResponse
from backend.services.liquidity import DEFAULT_BUFFER_USD, generate_cash_flow_ladder, get_liquidity_summary

router = APIRouter(prefix="/liquidity", tags=["liquidity"])


@router.get("/cashflow", response_model=LiquidityCashflowResponse)
def get_cashflow(
    months: int = Query(default=24, ge=1, le=36),
    scenario: str = Query(default="base", pattern="^(base|stress)$"),
    buffer_target_usd: float = Query(default=float(DEFAULT_BUFFER_USD), ge=0),
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> LiquidityCashflowResponse:
    _, user = auth
    return LiquidityCashflowResponse.model_validate(
        generate_cash_flow_ladder(
            user.workspace_id,
            db,
            scenario=scenario,
            projection_months=months,
            liquidity_buffer=Decimal(str(buffer_target_usd)),
        )
    )


@router.get("/summary", response_model=LiquiditySummaryResponse)
def summary(
    days: int = Query(default=90, ge=30, le=365),
    buffer_target_usd: float = Query(default=float(DEFAULT_BUFFER_USD), ge=0),
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> LiquiditySummaryResponse:
    _, user = auth
    return LiquiditySummaryResponse.model_validate(
        get_liquidity_summary(
            user.workspace_id,
            db,
            days=days,
            liquidity_buffer=Decimal(str(buffer_target_usd)),
        )
    )
