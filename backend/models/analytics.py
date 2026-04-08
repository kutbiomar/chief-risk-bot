from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base
from backend.models.common import TimestampMixin, uuid_pk


class PriceCache(Base):
    __tablename__ = "price_cache"

    ticker: Mapped[str] = mapped_column(Text, primary_key=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    price_local: Mapped[float] = mapped_column(Float, nullable=False)
    price_usd: Mapped[float] = mapped_column(Float, nullable=False)
    daily_return_local: Mapped[float] = mapped_column(Float, nullable=False)
    daily_return_usd: Mapped[float] = mapped_column(Float, nullable=False)
    weekly_return_usd: Mapped[float] = mapped_column(Float, nullable=False)
    history_json: Mapped[str] = mapped_column(Text, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ttl_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=4)


class FxCache(Base):
    __tablename__ = "fx_cache"

    pair: Mapped[str] = mapped_column(Text, primary_key=True)
    base_currency: Mapped[str] = mapped_column(String(8), nullable=False)
    quote_currency: Mapped[str] = mapped_column(String(8), nullable=False)
    spot_rate: Mapped[float] = mapped_column(Float, nullable=False)
    history_json: Mapped[str] = mapped_column(Text, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ttl_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=4)


class MacroCache(Base):
    __tablename__ = "macro_cache"

    id: Mapped[str] = uuid_pk()
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RiskScore(Base, TimestampMixin):
    __tablename__ = "risk_scores"

    id: Mapped[str] = uuid_pk()
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("portfolio_snapshots.id"), nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    async_job_id: Mapped[str] = mapped_column(ForeignKey("async_jobs.id"), nullable=False, index=True)
    agent: Mapped[str] = mapped_column(Text, nullable=False)
    dimension: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[Optional[int]] = mapped_column(Integer)
    severity: Mapped[Optional[str]] = mapped_column(Text)
    headline: Mapped[Optional[str]] = mapped_column(Text)
    reasoning: Mapped[Optional[str]] = mapped_column(Text)
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    conversation_prompt: Mapped[Optional[str]] = mapped_column(Text)
    data_sources_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    model: Mapped[Optional[str]] = mapped_column(Text)
    prompt_version: Mapped[Optional[str]] = mapped_column(Text)
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer)
    error_message: Mapped[Optional[str]] = mapped_column(Text)


class RiskFlag(Base, TimestampMixin):
    __tablename__ = "risk_flags"

    id: Mapped[str] = uuid_pk()
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("portfolio_snapshots.id"), nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    rule: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    ticker: Mapped[Optional[str]] = mapped_column(Text)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)


class VarResult(Base):
    __tablename__ = "var_results"

    id: Mapped[str] = uuid_pk()
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("portfolio_snapshots.id"), nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    var_1d_95: Mapped[float] = mapped_column(Float, nullable=False)
    var_1d_99: Mapped[float] = mapped_column(Float, nullable=False)
    cvar_1d_95: Mapped[float] = mapped_column(Float, nullable=False)
    cvar_1d_99: Mapped[float] = mapped_column(Float, nullable=False)
    max_drawdown_1y: Mapped[float] = mapped_column(Float, nullable=False)
    worst_scenario_date: Mapped[date] = mapped_column(Date, nullable=False)
    worst_scenario_loss: Mapped[float] = mapped_column(Float, nullable=False)
    lookback_days: Mapped[int] = mapped_column(Integer, nullable=False, default=252)
    effective_lookback_days: Mapped[int] = mapped_column(Integer, nullable=False)
    methodology: Mapped[str] = mapped_column(Text, nullable=False, default="historical_simulation")
    model_coverage_pct: Mapped[float] = mapped_column(Float, nullable=False)
    unmodeled_value_usd: Mapped[float] = mapped_column(Float, nullable=False)
    position_contributions_json: Mapped[str] = mapped_column(Text, nullable=False)
    assumptions_json: Mapped[str] = mapped_column(Text, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
