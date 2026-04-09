from __future__ import annotations

from datetime import datetime
from typing import Optional, Union

from pydantic import BaseModel


class SnapshotResponse(BaseModel):
    snapshot_id: str
    source: str
    position_count: int
    total_aum_usd: float
    created_at: datetime
    parent_snapshot_id: Optional[str] = None


class SummaryBucket(BaseModel):
    label: str
    market_value_usd: float
    pct_of_portfolio: float
    position_count: int
    top_holdings: list[dict[str, Union[float, str]]]


class CustodianBucket(BaseModel):
    label: str
    market_value_usd: float
    pct_of_portfolio: float
    position_count: int


class PortfolioSummaryResponse(BaseModel):
    snapshot_id: str
    total_aum_usd: float
    liquidity_score_pct: float
    hhi_concentration: float
    top_five_concentration_pct: float
    asset_class: list[SummaryBucket]
    geo_region: list[SummaryBucket]
    sector: list[SummaryBucket]
    market_segment: list[SummaryBucket]
    custodian_distribution: list[CustodianBucket]


class PositionResponse(BaseModel):
    id: str
    snapshot_id: str
    ticker: str
    name: Optional[str] = None
    quantity: float
    market_value_usd: Optional[float] = None
    asset_class: str
    geo_region: Optional[str] = None
    sector: Optional[str] = None
    market_segment: Optional[str] = None
    factor_asset_class: Optional[str] = None
    factor_sector: Optional[str] = None
    factor_subsector: Optional[str] = None
    factor_country: Optional[str] = None
    factor_region: Optional[str] = None
    factor_market_segment: Optional[str] = None
    factor_tag_source: Optional[str] = None
    factor_tag_confidence: Optional[float] = None
    custodian: Optional[str] = None
    notes: Optional[str] = None


class PositionListResponse(BaseModel):
    snapshot_id: str
    total: int
    items: list[PositionResponse]


class PositionCreateRequest(BaseModel):
    ticker: str
    name: Optional[str] = None
    quantity: float
    market_value_usd: Optional[float] = None
    price_usd: Optional[float] = None
    position_currency: str = "USD"
    asset_class: str
    geo_region: Optional[str] = None
    sector: Optional[str] = None
    market_segment: Optional[str] = None
    factor_asset_class: Optional[str] = None
    factor_sector: Optional[str] = None
    factor_subsector: Optional[str] = None
    factor_country: Optional[str] = None
    factor_region: Optional[str] = None
    factor_market_segment: Optional[str] = None
    factor_tag_source: Optional[str] = None
    factor_tag_confidence: Optional[float] = None
    custodian: Optional[str] = None
    notes: Optional[str] = None


class PositionUpdateRequest(BaseModel):
    name: Optional[str] = None
    quantity: Optional[float] = None
    market_value_usd: Optional[float] = None
    price_usd: Optional[float] = None
    position_currency: Optional[str] = None
    asset_class: Optional[str] = None
    geo_region: Optional[str] = None
    sector: Optional[str] = None
    market_segment: Optional[str] = None
    factor_asset_class: Optional[str] = None
    factor_sector: Optional[str] = None
    factor_subsector: Optional[str] = None
    factor_country: Optional[str] = None
    factor_region: Optional[str] = None
    factor_market_segment: Optional[str] = None
    factor_tag_source: Optional[str] = None
    factor_tag_confidence: Optional[float] = None
    custodian: Optional[str] = None
    notes: Optional[str] = None


class PositionMutationResponse(BaseModel):
    snapshot_id: str
    position_id: str
    parent_snapshot_id: Optional[str] = None
