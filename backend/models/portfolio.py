from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base
from backend.models.common import TimestampMixin, uuid_pk


class Workspace(Base, TimestampMixin):
    __tablename__ = "workspaces"

    id: Mapped[str] = uuid_pk()
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    reporting_currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    timezone: Mapped[str] = mapped_column(Text, nullable=False, default="UTC")
    address: Mapped[Optional[str]] = mapped_column(Text)
    plan: Mapped[str] = mapped_column(Text, nullable=False, default="starter")
    seat_limit: Mapped[Optional[int]] = mapped_column(Integer)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class PortfolioSnapshot(Base, TimestampMixin):
    __tablename__ = "portfolio_snapshots"

    id: Mapped[str] = uuid_pk()
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    parent_snapshot_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("portfolio_snapshots.id"), index=True
    )
    uploaded_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[Optional[str]] = mapped_column(Text)
    raw_bytes: Mapped[Optional[bytes]] = mapped_column(LargeBinary)
    position_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_aum_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    enriched_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    positions: Mapped[list["Position"]] = relationship(back_populates="snapshot")


class Position(Base, TimestampMixin):
    __tablename__ = "positions"

    id: Mapped[str] = uuid_pk()
    snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("portfolio_snapshots.id"), nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    security_id: Mapped[Optional[str]] = mapped_column(Text)
    ticker: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(Text)
    position_currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    price_local: Mapped[Optional[float]] = mapped_column(Float)
    price_usd: Mapped[Optional[float]] = mapped_column(Float)
    market_value_local: Mapped[Optional[float]] = mapped_column(Float)
    market_value_usd: Mapped[Optional[float]] = mapped_column(Float)
    asset_class: Mapped[str] = mapped_column(Text, nullable=False)
    geo_region: Mapped[Optional[str]] = mapped_column(Text)
    sector: Mapped[Optional[str]] = mapped_column(Text)
    market_segment: Mapped[Optional[str]] = mapped_column(Text)
    custodian: Mapped[Optional[str]] = mapped_column(Text)
    price_source: Mapped[str] = mapped_column(Text, nullable=False, default="manual")
    beta_vs_spy: Mapped[Optional[float]] = mapped_column(Float)
    daily_return: Mapped[Optional[float]] = mapped_column(Float)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    override_value: Mapped[Optional[float]] = mapped_column(Float)
    override_by: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"))
    override_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    snapshot: Mapped[PortfolioSnapshot] = relationship(back_populates="positions")
