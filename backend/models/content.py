from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base
from backend.models.common import TimestampMixin, uuid_pk


class BriefingRun(Base, TimestampMixin):
    __tablename__ = "briefing_runs"

    id: Mapped[str] = uuid_pk()
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("portfolio_snapshots.id"), nullable=False, index=True)
    var_result_id: Mapped[str] = mapped_column(ForeignKey("var_results.id"), nullable=False)
    generated_by: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="draft")
    week_label: Mapped[str] = mapped_column(Text, nullable=False)
    output_json: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    published_by: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"))
    pdf_path: Mapped[Optional[str]] = mapped_column(Text)


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[str] = uuid_pk()
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    uploaded_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    file_type: Mapped[str] = mapped_column(Text, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(Text, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    folder: Mapped[str] = mapped_column(Text, nullable=False)
    tag: Mapped[Optional[str]] = mapped_column(Text)
    page_count: Mapped[Optional[int]] = mapped_column(Integer)
    malware_scan_status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    extraction_status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    extraction_result_id: Mapped[Optional[str]] = mapped_column(ForeignKey("extraction_results.id"))
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class ExtractionResult(Base, TimestampMixin):
    __tablename__ = "extraction_results"

    id: Mapped[str] = uuid_pk()
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False, index=True)
    positions_json: Mapped[str] = mapped_column(Text, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_json: Mapped[str] = mapped_column(Text, nullable=False)
    needs_review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    raw_text_truncated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    extracted_row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    model: Mapped[str] = mapped_column(Text, nullable=False, default="deterministic-demo-parser")
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
