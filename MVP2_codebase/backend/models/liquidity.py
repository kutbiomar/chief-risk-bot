from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .common import TimestampMixin, uuid_pk


class LiquidityProjection(Base, TimestampMixin):
    __tablename__ = "liquidity_projections"

    id: Mapped[str] = uuid_pk()
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    projection_months: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    base_currency: Mapped[str] = mapped_column(Text, nullable=False)
    scenario: Mapped[str] = mapped_column(Text, nullable=False, default="base")
    liquidity_buffer: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    monthly_buckets: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    liquidity_gaps: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
