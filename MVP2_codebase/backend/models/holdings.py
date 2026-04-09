from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .common import MutableTimestampMixin, uuid_pk


class Holding(Base, MutableTimestampMixin):
    __tablename__ = "holdings"

    id: Mapped[str] = uuid_pk()
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    fund_id: Mapped[Optional[str]] = mapped_column(ForeignKey("funds.id"), index=True)
    commitment_id: Mapped[Optional[str]] = mapped_column(ForeignKey("commitments.id"), index=True)
    asset_name: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    asset_type: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    geo_region: Mapped[Optional[str]] = mapped_column(Text, index=True)
    sector: Mapped[Optional[str]] = mapped_column(Text, index=True)
    currency: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6))
    unit_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6))
    current_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    current_value_base: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    current_value_fx_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 8))
    current_value_date: Mapped[Optional[date]] = mapped_column(Date)
    current_value_source: Mapped[str] = mapped_column(Text, nullable=False, default="estimated")
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
