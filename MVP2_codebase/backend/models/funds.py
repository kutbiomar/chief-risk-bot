from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .common import MutableTimestampMixin, uuid_pk


class Fund(Base, MutableTimestampMixin):
    __tablename__ = "funds"

    id: Mapped[str] = uuid_pk()
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    type: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    manager_name: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    vintage_year: Mapped[Optional[int]] = mapped_column(Integer)
    fund_size: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(Text, nullable=False)
    jurisdiction: Mapped[Optional[str]] = mapped_column(Text)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    commitments: Mapped[list["Commitment"]] = relationship(back_populates="fund")


class Commitment(Base, MutableTimestampMixin):
    __tablename__ = "commitments"

    id: Mapped[str] = uuid_pk()
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    fund_id: Mapped[str] = mapped_column(ForeignKey("funds.id"), nullable=False, index=True)
    committed_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    commitment_currency: Mapped[str] = mapped_column(Text, nullable=False)
    committed_amount_base: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    committed_amount_fx_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 8))
    called_capital: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    called_capital_base: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    called_capital_fx_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 8))
    uncalled_capital: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    uncalled_capital_base: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    uncalled_capital_fx_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 8))
    nav: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    nav_base: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    nav_fx_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 8))
    nav_date: Mapped[Optional[date]] = mapped_column(Date)
    nav_is_estimated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    nav_confidence_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    distributions_received: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )
    distributions_received_base: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    distributions_received_fx_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 8))
    management_fee_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    carry_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    remaining_fund_life_months: Mapped[Optional[int]] = mapped_column(Integer)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    fund: Mapped["Fund"] = relationship(back_populates="commitments")
