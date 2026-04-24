from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .common import MutableTimestampMixin, TimestampMixin, uuid_pk


class WeeklyBriefing(Base, MutableTimestampMixin):
    __tablename__ = "weekly_briefings"

    id: Mapped[str] = uuid_pk()
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    generated_by: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="draft")
    week_label: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    output_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    model: Mapped[Optional[str]] = mapped_column(Text)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    published_by: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"))
    pdf_path: Mapped[Optional[str]] = mapped_column(Text)


class Document(Base, MutableTimestampMixin):
    __tablename__ = "documents"

    id: Mapped[str] = uuid_pk()
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    uploaded_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    fund_id: Mapped[Optional[str]] = mapped_column(ForeignKey("funds.id"), index=True)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    file_type: Mapped[str] = mapped_column(Text, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    provider_name: Mapped[Optional[str]] = mapped_column(Text, index=True)
    auto_category: Mapped[str] = mapped_column(Text, nullable=False, default="other", index=True)
    processing_status: Mapped[str] = mapped_column(Text, nullable=False, default="pending", index=True)
    extracted_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    reconciliation_flags: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    replaces_document_id: Mapped[Optional[str]] = mapped_column(ForeignKey("documents.id"))
    extraction_result_id: Mapped[Optional[str]] = mapped_column(ForeignKey("extraction_results.id"))
    needs_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class ExtractionResult(Base, TimestampMixin):
    __tablename__ = "extraction_results"

    id: Mapped[str] = uuid_pk()
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False, index=True)
    document_type: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    classification_confidence: Mapped[Optional[int]] = mapped_column(Integer)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    confidence_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    needs_review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    raw_text_truncated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    model: Mapped[str] = mapped_column(Text, nullable=False, default="claude")
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
