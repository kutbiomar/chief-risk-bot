from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.deps import get_db
from backend.routers.auth import require_session
from backend.schemas.liquidity import LiquidityCashflowResponse, LiquiditySummaryResponse
from backend.services.liquidity import DEFAULT_BUFFER_USD, generate_cash_flow_ladder, get_liquidity_summary

router = APIRouter(prefix="/liquidity", tags=["liquidity"])


@router.get("")
def overview(
    months: int = Query(default=24, ge=1, le=36),
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> dict:
    _, user = auth
    summary_payload = get_liquidity_summary(user.workspace_id, db)
    cashflow_payload = generate_cash_flow_ladder(user.workspace_id, db, projection_months=months)
    cash = float(summary_payload["cash_on_hand_usd"])
    semi_liquid = float(summary_payload["expected_distributions_usd"]) + float(summary_payload["recallable_pending_usd"])
    illiquid = float(summary_payload["total_unfunded_usd"])
    monthly_outflow = max(float(summary_payload["scheduled_outflows_usd"]) / 3.0, 1.0)
    upcoming_events = [
        {
            "date": summary_payload["next_call_due_date"],
            "description": "Next capital call",
            "type": "outflow",
            "source": "Private markets",
            "amount": -float(summary_payload["next_call_amount_usd"]),
        },
        {
            "date": "Next 90 days",
            "description": "Expected distributions",
            "type": "inflow",
            "source": "Private markets",
            "amount": float(summary_payload["expected_distributions_usd"]),
        },
        {
            "date": "Next 90 days",
            "description": "Scheduled outflows",
            "type": "outflow",
            "source": "Portfolio commitments",
            "amount": -float(summary_payload["scheduled_outflows_usd"]),
        },
    ]
    return {
        **summary_payload,
        "buckets": [
            {"label": "Liquid", "value": cash, "pct": 0},
            {"label": "Semi-liquid", "value": semi_liquid, "pct": 0},
            {"label": "Illiquid", "value": illiquid, "pct": 0},
        ],
        "runway_months": cash / monthly_outflow,
        "cash_runway_months": cash / monthly_outflow,
        "burn_rate_basis": "scheduled outflows",
        "cash_flows": cashflow_payload["monthly_buckets"],
        "upcoming_events": [event for event in upcoming_events if event["amount"]],
    }


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
