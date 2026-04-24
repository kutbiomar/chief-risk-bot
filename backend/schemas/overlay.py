from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class FactorScoreResponse(BaseModel):
    factor_key: str
    factor_type: str
    label: str
    score: float
    direction: str
    z_score: float
    primary_driver: str
    confidence: float
    sentiment_modifier: float
    signal_payload_json: str
    as_of_date: date


class RegimeResponse(BaseModel):
    regime: str
    trigger_signal: str
    vix_level: float
    credit_spread_bps: float
    methodology_note: str
    as_of_date: date
    created_at: datetime


class TriangulationPositionResponse(BaseModel):
    ticker: str
    name: str
    aum_exposed_usd: float


class TriangulationFactorResponse(BaseModel):
    factor_key: str
    label: str
    factor_type: str
    risk_score: float
    direction: str
    aum_exposed_usd: float
    exposure_pct: float
    weighted_risk: float
    top_positions: list[TriangulationPositionResponse]


class AumTriangulationResponse(BaseModel):
    as_of_date: date
    composite_score: float
    aum_at_risk_usd: float
    factors: list[TriangulationFactorResponse]
    top_risk_contributors: list[TriangulationFactorResponse]


class StressDriverResponse(BaseModel):
    factor_key: str
    label: str
    impact_usd: float


class StressScenarioResponse(BaseModel):
    scenario_key: str
    name: str
    description: str
    severity: str
    estimated_impact_usd: float
    estimated_impact_pct: float
    top_drivers: list[StressDriverResponse]


class OverlayAlertResponse(BaseModel):
    kind: str
    severity: str
    headline: str
    description: str
    rule: str
    value: float
    threshold: float


class OverlayStressResponse(BaseModel):
    as_of_date: date
    regime: str
    scenarios: list[StressScenarioResponse]
    alerts: list[OverlayAlertResponse]


class OverlayRunResponse(BaseModel):
    job_id: str
    snapshot_id: str
    status: str
    regime: str
    composite_score: float
    factor_count: int
    stress_count: int
    alert_count: int
    as_of_date: str
    var_1d_95: float
