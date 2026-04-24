from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base
from backend.models.common import TimestampMixin, uuid_pk


class Fund(Base, TimestampMixin):
    __tablename__ = "funds"

    id: Mapped[str] = uuid_pk()
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    type: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    manager_name: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    vintage_year: Mapped[Optional[int]] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(Text, nullable=False, default="USD")
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    commitments: Mapped[list["Commitment"]] = relationship(back_populates="fund")


class Commitment(Base, TimestampMixin):
    __tablename__ = "commitments"

    id: Mapped[str] = uuid_pk()
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    fund_id: Mapped[str] = mapped_column(ForeignKey("funds.id"), nullable=False, index=True)
    committed_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    commitment_currency: Mapped[str] = mapped_column(Text, nullable=False, default="USD")
    committed_amount_base: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    called_capital: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    called_capital_base: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    uncalled_capital: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    uncalled_capital_base: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    distributions_received: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    distributions_received_base: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    nav: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    nav_base: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    nav_date: Mapped[Optional[date]] = mapped_column(Date)
    nav_is_estimated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    remaining_fund_life_months: Mapped[Optional[int]] = mapped_column(Integer)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    fund: Mapped[Fund] = relationship(back_populates="commitments")


class CapitalEvent(Base, TimestampMixin):
    __tablename__ = "capital_events"

    id: Mapped[str] = uuid_pk()
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    fund_id: Mapped[str] = mapped_column(ForeignKey("funds.id"), nullable=False, index=True)
    commitment_id: Mapped[Optional[str]] = mapped_column(ForeignKey("commitments.id"), index=True)
    type: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(Text, nullable=False, default="USD")
    amount_base: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    notice_date: Mapped[Optional[date]] = mapped_column(Date)
    due_date: Mapped[Optional[date]] = mapped_column(Date, index=True)
    effective_date: Mapped[Optional[date]] = mapped_column(Date, index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    recall_period_days: Mapped[Optional[int]] = mapped_column(Integer)
    recall_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
