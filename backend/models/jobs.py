from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base
from backend.models.common import TimestampMixin, uuid_pk


class AsyncJob(Base, TimestampMixin):
    __tablename__ = "async_jobs"

    id: Mapped[str] = uuid_pk()
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    job_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="queued")
    created_by: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"))
    resource_type: Mapped[Optional[str]] = mapped_column(Text)
    resource_id: Mapped[Optional[str]] = mapped_column(Text)
    request_json: Mapped[Optional[str]] = mapped_column(Text)
    result_json: Mapped[Optional[str]] = mapped_column(Text)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_children: Mapped[Optional[int]] = mapped_column(Integer)
    succeeded_children: Mapped[Optional[int]] = mapped_column(Integer)
    failed_children: Mapped[Optional[int]] = mapped_column(Integer)
    progress_pct: Mapped[Optional[int]] = mapped_column(Integer)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
