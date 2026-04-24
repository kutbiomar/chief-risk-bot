from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .common import MutableTimestampMixin, uuid_pk


class CapitalEvent(Base, MutableTimestampMixin):
    __tablename__ = "capital_events"

    id: Mapped[str] = uuid_pk()
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    fund_id: Mapped[str] = mapped_column(ForeignKey("funds.id"), nullable=False, index=True)
    commitment_id: Mapped[Optional[str]] = mapped_column(ForeignKey("commitments.id"), index=True)
    type: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(Text, nullable=False)
    amount_base: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    amount_fx_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 8))
    notice_date: Mapped[Optional[date]] = mapped_column(Date)
    due_date: Mapped[Optional[date]] = mapped_column(Date, index=True)
    effective_date: Mapped[Optional[date]] = mapped_column(Date, index=True)
    source_document_id: Mapped[Optional[str]] = mapped_column(ForeignKey("documents.id"), index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    recall_period_days: Mapped[Optional[int]] = mapped_column(Integer)
    recall_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
