from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel


class FundCreateRequest(BaseModel):
    name: str
    type: str
    manager_name: str
    vintage_year: Optional[int] = None
    fund_size: Optional[Decimal] = None
    currency: str
    jurisdiction: Optional[str] = None


class FundUpdateRequest(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    manager_name: Optional[str] = None
    vintage_year: Optional[int] = None
    fund_size: Optional[Decimal] = None
    currency: Optional[str] = None
    jurisdiction: Optional[str] = None


class FundResponse(BaseModel):
    id: str
    name: str
    type: str
    manager_name: str
    vintage_year: Optional[int] = None
    fund_size: Optional[Decimal] = None
    currency: str
    jurisdiction: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class FundListResponse(BaseModel):
    total: int
    items: list[FundResponse]


class CommitmentCreateRequest(BaseModel):
    fund_id: str
    committed_amount: Decimal
    commitment_currency: str
    committed_amount_base: Optional[Decimal] = None
    committed_amount_fx_rate: Optional[Decimal] = None
    called_capital: Decimal = Decimal("0")
    called_capital_base: Optional[Decimal] = None
    called_capital_fx_rate: Optional[Decimal] = None
    uncalled_capital: Decimal = Decimal("0")
    uncalled_capital_base: Optional[Decimal] = None
    uncalled_capital_fx_rate: Optional[Decimal] = None
    nav: Optional[Decimal] = None
    nav_base: Optional[Decimal] = None
    nav_fx_rate: Optional[Decimal] = None
    nav_date: Optional[date] = None
    nav_is_estimated: bool = False
    nav_confidence_pct: Optional[Decimal] = None
    distributions_received: Decimal = Decimal("0")
    distributions_received_base: Optional[Decimal] = None
    distributions_received_fx_rate: Optional[Decimal] = None
    management_fee_rate: Optional[Decimal] = None
    carry_rate: Optional[Decimal] = None
    remaining_fund_life_months: Optional[int] = None


class CommitmentUpdateRequest(BaseModel):
    committed_amount: Optional[Decimal] = None
    commitment_currency: Optional[str] = None
    committed_amount_base: Optional[Decimal] = None
    committed_amount_fx_rate: Optional[Decimal] = None
    called_capital: Optional[Decimal] = None
    called_capital_base: Optional[Decimal] = None
    called_capital_fx_rate: Optional[Decimal] = None
    uncalled_capital: Optional[Decimal] = None
    uncalled_capital_base: Optional[Decimal] = None
    uncalled_capital_fx_rate: Optional[Decimal] = None
    nav: Optional[Decimal] = None
    nav_base: Optional[Decimal] = None
    nav_fx_rate: Optional[Decimal] = None
    nav_date: Optional[date] = None
    nav_is_estimated: Optional[bool] = None
    nav_confidence_pct: Optional[Decimal] = None
    distributions_received: Optional[Decimal] = None
    distributions_received_base: Optional[Decimal] = None
    distributions_received_fx_rate: Optional[Decimal] = None
    management_fee_rate: Optional[Decimal] = None
    carry_rate: Optional[Decimal] = None
    remaining_fund_life_months: Optional[int] = None


class CommitmentResponse(BaseModel):
    id: str
    fund_id: str
    committed_amount: Decimal
    commitment_currency: str
    committed_amount_base: Optional[Decimal] = None
    called_capital: Decimal
    called_capital_base: Optional[Decimal] = None
    uncalled_capital: Decimal
    uncalled_capital_base: Optional[Decimal] = None
    nav: Optional[Decimal] = None
    nav_base: Optional[Decimal] = None
    nav_date: Optional[date] = None
    nav_is_estimated: bool
    nav_confidence_pct: Optional[Decimal] = None
    distributions_received: Decimal
    distributions_received_base: Optional[Decimal] = None
    management_fee_rate: Optional[Decimal] = None
    carry_rate: Optional[Decimal] = None
    remaining_fund_life_months: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class CommitmentListResponse(BaseModel):
    total: int
    items: list[CommitmentResponse]


class CapitalEventCreateRequest(BaseModel):
    fund_id: str
    commitment_id: Optional[str] = None
    type: str
    amount: Decimal
    currency: str
    amount_base: Optional[Decimal] = None
    amount_fx_rate: Optional[Decimal] = None
    notice_date: Optional[date] = None
    due_date: Optional[date] = None
    effective_date: Optional[date] = None
    source_document_id: Optional[str] = None
    notes: Optional[str] = None
    is_confirmed: bool = False
    recall_period_days: Optional[int] = None
    recall_expires_at: Optional[datetime] = None


class CapitalEventUpdateRequest(BaseModel):
    commitment_id: Optional[str] = None
    type: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    amount_base: Optional[Decimal] = None
    amount_fx_rate: Optional[Decimal] = None
    notice_date: Optional[date] = None
    due_date: Optional[date] = None
    effective_date: Optional[date] = None
    source_document_id: Optional[str] = None
    notes: Optional[str] = None
    is_confirmed: Optional[bool] = None
    recall_period_days: Optional[int] = None
    recall_expires_at: Optional[datetime] = None


class CapitalEventResponse(BaseModel):
    id: str
    fund_id: str
    commitment_id: Optional[str] = None
    type: str
    amount: Decimal
    currency: str
    amount_base: Optional[Decimal] = None
    notice_date: Optional[date] = None
    due_date: Optional[date] = None
    effective_date: Optional[date] = None
    source_document_id: Optional[str] = None
    notes: Optional[str] = None
    is_confirmed: bool
    recall_period_days: Optional[int] = None
    recall_expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class CapitalEventListResponse(BaseModel):
    total: int
    items: list[CapitalEventResponse]


class HoldingCreateRequest(BaseModel):
    fund_id: Optional[str] = None
    commitment_id: Optional[str] = None
    asset_name: str
    asset_type: str
    geo_region: Optional[str] = None
    sector: Optional[str] = None
    currency: str
    quantity: Optional[Decimal] = None
    unit_cost: Optional[Decimal] = None
    current_value: Optional[Decimal] = None
    current_value_base: Optional[Decimal] = None
    current_value_fx_rate: Optional[Decimal] = None
    current_value_date: Optional[date] = None
    current_value_source: str = "estimated"


class HoldingUpdateRequest(BaseModel):
    fund_id: Optional[str] = None
    commitment_id: Optional[str] = None
    asset_name: Optional[str] = None
    asset_type: Optional[str] = None
    geo_region: Optional[str] = None
    sector: Optional[str] = None
    currency: Optional[str] = None
    quantity: Optional[Decimal] = None
    unit_cost: Optional[Decimal] = None
    current_value: Optional[Decimal] = None
    current_value_base: Optional[Decimal] = None
    current_value_fx_rate: Optional[Decimal] = None
    current_value_date: Optional[date] = None
    current_value_source: Optional[str] = None


class HoldingResponse(BaseModel):
    id: str
    fund_id: Optional[str] = None
    commitment_id: Optional[str] = None
    asset_name: str
    asset_type: str
    geo_region: Optional[str] = None
    sector: Optional[str] = None
    currency: str
    quantity: Optional[Decimal] = None
    unit_cost: Optional[Decimal] = None
    current_value: Optional[Decimal] = None
    current_value_base: Optional[Decimal] = None
    current_value_date: Optional[date] = None
    current_value_source: str
    created_at: datetime
    updated_at: datetime


class HoldingListResponse(BaseModel):
    total: int
    items: list[HoldingResponse]


class DealCreateRequest(BaseModel):
    name: str
    stage: str
    asset_type: Optional[str] = None
    target_commitment: Optional[Decimal] = None
    target_commitment_currency: Optional[str] = None
    target_commitment_base: Optional[Decimal] = None
    target_commitment_fx_rate: Optional[Decimal] = None
    target_close_date: Optional[date] = None
    lead_analyst_id: Optional[str] = None
    notes: Optional[str] = None


class DealUpdateRequest(BaseModel):
    name: Optional[str] = None
    stage: Optional[str] = None
    asset_type: Optional[str] = None
    target_commitment: Optional[Decimal] = None
    target_commitment_currency: Optional[str] = None
    target_commitment_base: Optional[Decimal] = None
    target_commitment_fx_rate: Optional[Decimal] = None
    target_close_date: Optional[date] = None
    lead_analyst_id: Optional[str] = None
    notes: Optional[str] = None


class DealResponse(BaseModel):
    id: str
    name: str
    stage: str
    asset_type: Optional[str] = None
    target_commitment: Optional[Decimal] = None
    target_commitment_currency: Optional[str] = None
    target_commitment_base: Optional[Decimal] = None
    target_close_date: Optional[date] = None
    lead_analyst_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DealListResponse(BaseModel):
    total: int
    items: list[DealResponse]


class SummaryBucket(BaseModel):
    label: str
    value_base: Decimal
    pct_of_total: float
    item_count: int


class PortfolioSummaryResponse(BaseModel):
    total_committed_base: Decimal
    total_called_base: Decimal
    total_uncalled_base: Decimal
    total_distributions_base: Decimal
    by_fund_type: list[SummaryBucket]
    upcoming_calls: list[dict[str, Any]]
    recent_distributions: list[dict[str, Any]]


class LiquidityProjectionResponse(BaseModel):
    scenario: str
    base_currency: str
    projection_months: int
    monthly_buckets: list[dict[str, Any]]
    liquidity_gaps: list[dict[str, Any]]


class AlertResponse(BaseModel):
    rule: str
    severity: str
    entity_id: Optional[str] = None
    entity_type: str
    message: str
    created_at: datetime


class AlertListResponse(BaseModel):
    total: int
    items: list[AlertResponse]
