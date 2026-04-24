from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Date, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base
from backend.models.common import TimestampMixin, uuid_pk


class FactorScore(Base, TimestampMixin):
    __tablename__ = "factor_scores"

    id: Mapped[str] = uuid_pk()
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    factor_key: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    factor_type: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    direction: Mapped[str] = mapped_column(Text, nullable=False)
    z_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    primary_driver: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    sentiment_modifier: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    signal_payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)


class AssetFactorExposure(Base, TimestampMixin):
    __tablename__ = "asset_factor_exposures"
    __table_args__ = (
        Index("ix_asset_factor_exposures_snapshot_factor", "snapshot_id", "factor_key"),
    )

    id: Mapped[str] = uuid_pk()
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("portfolio_snapshots.id"), nullable=False, index=True)
    position_id: Mapped[str] = mapped_column(ForeignKey("positions.id"), nullable=False, index=True)
    factor_key: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    factor_type: Mapped[str] = mapped_column(Text, nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False, default="inferred")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.6)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)


class ProxyBasket(Base, TimestampMixin):
    __tablename__ = "proxy_baskets"

    id: Mapped[str] = uuid_pk()
    basket_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    factor_key: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    asset_class: Mapped[str] = mapped_column(Text, nullable=False)
    sector: Mapped[Optional[str]] = mapped_column(Text)
    region: Mapped[Optional[str]] = mapped_column(Text)
    market_segment: Mapped[Optional[str]] = mapped_column(Text)
    proxy_tickers_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    proxy_weights_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    illiquidity_scalar: Mapped[float] = mapped_column(Float, nullable=False, default=1.2)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class StressScenario(Base, TimestampMixin):
    __tablename__ = "stress_scenarios"

    id: Mapped[str] = uuid_pk()
    scenario_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(default=0)
    shock_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class RiskRegime(Base, TimestampMixin):
    __tablename__ = "risk_regimes"
    __table_args__ = (
        Index("ix_risk_regimes_workspace_as_of_date", "workspace_id", "as_of_date"),
    )

    id: Mapped[str] = uuid_pk()
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    snapshot_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("portfolio_snapshots.id"), index=True
    )
    regime: Mapped[str] = mapped_column(String(16), nullable=False)
    trigger_signal: Mapped[str] = mapped_column(Text, nullable=False)
    vix_level: Mapped[float] = mapped_column(Float, nullable=False)
    credit_spread_bps: Mapped[float] = mapped_column(Float, nullable=False)
    methodology_note: Mapped[str] = mapped_column(Text, nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
