from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel


class VarContribution(BaseModel):
    ticker: str
    security_id: Optional[str] = None
    contribution_pct: float
    contribution_usd: float
    method: str


class VarResponse(BaseModel):
    id: str
    snapshot_id: str
    var_1d_95: float
    var_1d_99: float
    cvar_1d_95: float
    cvar_1d_99: float
    max_drawdown_1y: float
    worst_scenario_date: date
    worst_scenario_loss: float
    lookback_days: int
    effective_lookback_days: int
    methodology: str
    model_coverage_pct: float
    unmodeled_value_usd: float
    position_contributions: list[VarContribution]
    assumptions: dict[str, Any]
    computed_at: datetime


class RiskScoreResponse(BaseModel):
    id: str
    agent: str
    dimension: str
    status: str
    score: Optional[int] = None
    severity: Optional[str] = None
    headline: Optional[str] = None
    reasoning: Optional[str] = None
    evidence: list[str]
    conversation_prompt: Optional[str] = None
    model: Optional[str] = None


class RiskFlagResponse(BaseModel):
    id: str
    rule: str
    severity: str
    ticker: Optional[str] = None
    value: float
    threshold: float
    description: str


class RiskRunResponse(BaseModel):
    job_id: str
    snapshot_id: str
    warnings: list[str]
    scores: list[RiskScoreResponse]
    flags: list[RiskFlagResponse]


class CockpitResponse(BaseModel):
    snapshot_id: str
    portfolio_summary: dict[str, Any]
    var_result: VarResponse
    risk_register: list[dict[str, Any]]
