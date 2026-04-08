from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base
from backend.models.common import TimestampMixin


class OnboardingProgress(Base, TimestampMixin):
    __tablename__ = "onboarding_progress"

    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), primary_key=True)
    current_step: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_steps_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    total_steps: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    last_step_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    notes: Mapped[Optional[str]] = mapped_column(Text)
