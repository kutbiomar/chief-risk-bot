from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class BriefingResponse(BaseModel):
    id: str
    snapshot_id: str
    version: int
    status: str
    week_label: str
    output: dict[str, Any]
    pdf_path: Optional[str] = None
    created_at: datetime
    published_at: Optional[datetime] = None


class BriefingListResponse(BaseModel):
    items: list[BriefingResponse]


class SettingsResponse(BaseModel):
    briefing_day: str
    briefing_time: str
    briefing_recipients: str
    briefing_auto_publish: bool
    briefing_send_pdf: bool
    briefing_include_audit_footer: bool
    ai_model: str
    ai_risk_tone: str
    ai_custom_instructions: Optional[str] = None
    ai_allow_trade_actions: bool


class SettingsPatchRequest(BaseModel):
    briefing_day: Optional[str] = None
    briefing_time: Optional[str] = None
    briefing_recipients: Optional[str] = None
    briefing_auto_publish: Optional[bool] = None
    briefing_send_pdf: Optional[bool] = None
    briefing_include_audit_footer: Optional[bool] = None
    ai_model: Optional[str] = None
    ai_risk_tone: Optional[str] = None
    ai_custom_instructions: Optional[str] = None
    ai_allow_trade_actions: Optional[bool] = None


class ApiKeyCreateRequest(BaseModel):
    label: str
    key_type: str


class ApiKeyResponse(BaseModel):
    id: str
    label: str
    key_type: str
    key_prefix: str
    created_at: datetime


class ApiKeyCreateResponse(ApiKeyResponse):
    plain_text_key: str


class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size_bytes: int
    folder: str
    tag: Optional[str] = None
    malware_scan_status: str
    extraction_status: str
    extraction_result_id: Optional[str] = None
    created_at: datetime


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    folder_counts: dict[str, int]


class DocumentTagRequest(BaseModel):
    tag: str


class ExtractionResponse(BaseModel):
    id: str
    positions: list[dict[str, Any]]
    confidence: list[dict[str, Any]]
    needs_review_count: int
    raw_text_truncated: bool
