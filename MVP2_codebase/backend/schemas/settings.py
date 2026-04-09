from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


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
    base_currency: str
    reporting_timezone: str
    liquidity_buffer_default: float


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
    base_currency: Optional[str] = None
    reporting_timezone: Optional[str] = None
    liquidity_buffer_default: Optional[float] = None


class ApiKeyCreateRequest(BaseModel):
    label: str
    key_type: str = "service"


class ApiKeyResponse(BaseModel):
    id: str
    label: str
    key_type: str
    key_prefix: str
    created_at: datetime


class ApiKeyCreateResponse(ApiKeyResponse):
    plain_text_key: str
