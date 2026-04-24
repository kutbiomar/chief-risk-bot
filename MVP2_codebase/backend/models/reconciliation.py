from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .common import TimestampMixin, uuid_pk


class ReconciliationFlag(Base, TimestampMixin):
    __tablename__ = "reconciliation_flags"

    id: Mapped[str] = uuid_pk()
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    entity_id: Mapped[Optional[str]] = mapped_column(Text, index=True)
    field_name: Mapped[str] = mapped_column(Text, nullable=False)
    document_value: Mapped[Optional[str]] = mapped_column(Text)
    system_value: Mapped[Optional[str]] = mapped_column(Text)
    variance_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    severity: Mapped[str] = mapped_column(Text, nullable=False, default="medium")
    flagged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_by: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"))
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="open")
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
