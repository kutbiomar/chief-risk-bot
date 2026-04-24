from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class LiquidityBucketResponse(BaseModel):
    month: str
    inflows: float
    outflows: float
    net: float
    cumulative: float


class LiquidityGapResponse(BaseModel):
    month: str
    gap_amount: float
    description: str


class LiquidityCashflowResponse(BaseModel):
    scenario: str
    base_currency: str
    projection_months: int
    liquidity_buffer: float
    monthly_buckets: list[LiquidityBucketResponse]
    liquidity_gaps: list[LiquidityGapResponse]


class LiquiditySummaryResponse(BaseModel):
    window_days: int
    buffer_target_usd: float
    cash_on_hand_usd: float
    next_call_due_date: Optional[str]
    next_call_amount_usd: float
    total_unfunded_usd: float
    expected_distributions_usd: float
    scheduled_outflows_usd: float
    recallable_pending_usd: float
    net_liquidity_usd: float
    projected_cash_usd: float
    buffer_gap_usd: float
    buffer_breach: bool
