from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .common import MutableTimestampMixin, uuid_pk


class Workspace(Base, MutableTimestampMixin):
    __tablename__ = "workspaces"

    id: Mapped[str] = uuid_pk()
    name: Mapped[str] = mapped_column(Text, nullable=False)
    reporting_currency: Mapped[str] = mapped_column(Text, nullable=False, default="USD")
    timezone: Mapped[str] = mapped_column(Text, nullable=False, default="UTC")
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class User(Base, MutableTimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = uuid_pk()
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text, nullable=False, default="admin")
    scope: Mapped[str] = mapped_column(Text, nullable=False, default="All clients")
    totp_secret: Mapped[Optional[str]] = mapped_column(Text)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_active_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    disabled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
