from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, PrimaryKeyConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .common import MutableTimestampMixin, uuid_pk


class Deal(Base, MutableTimestampMixin):
    __tablename__ = "deals"

    id: Mapped[str] = uuid_pk()
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    stage: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    asset_type: Mapped[Optional[str]] = mapped_column(Text)
    target_commitment: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    target_commitment_currency: Mapped[Optional[str]] = mapped_column(Text)
    target_commitment_base: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    target_commitment_fx_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 8))
    target_close_date: Mapped[Optional[date]] = mapped_column(Date, index=True)
    lead_analyst_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class DealDocument(Base):
    __tablename__ = "deal_documents"
    __table_args__ = (PrimaryKeyConstraint("deal_id", "document_id"),)

    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    deal_id: Mapped[str] = mapped_column(ForeignKey("deals.id"), nullable=False)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False)
