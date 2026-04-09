from __future__ import annotations

import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_db
from ..models.auth import ApiKey, WorkspaceSetting
from ..models.identity import Workspace
from ..routers.auth import require_session
from ..schemas.settings import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyResponse,
    SettingsPatchRequest,
    SettingsResponse,
)
from ..services.auth.password import hash_password
from ..services.auth.session import utc_now
from ..services.bootstrap import get_or_create_workspace_settings

router = APIRouter(prefix="/settings", tags=["settings"])


def _serialize_settings(settings: WorkspaceSetting) -> SettingsResponse:
    return SettingsResponse(
        briefing_day=settings.briefing_day,
        briefing_time=settings.briefing_time,
        briefing_recipients=settings.briefing_recipients,
        briefing_auto_publish=settings.briefing_auto_publish,
        briefing_send_pdf=settings.briefing_send_pdf,
        briefing_include_audit_footer=settings.briefing_include_audit_footer,
        ai_model=settings.ai_model,
        ai_risk_tone=settings.ai_risk_tone,
        ai_custom_instructions=settings.ai_custom_instructions,
        ai_allow_trade_actions=settings.ai_allow_trade_actions,
        base_currency=settings.base_currency,
        reporting_timezone=settings.reporting_timezone,
        liquidity_buffer_default=float(settings.liquidity_buffer_default or 0),
    )


@router.get("", response_model=SettingsResponse)
def get_settings_endpoint(
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> SettingsResponse:
    _, user = auth
    settings = get_or_create_workspace_settings(db, user.workspace_id)
    db.commit()
    return _serialize_settings(settings)


@router.patch("", response_model=SettingsResponse)
def patch_settings(
    payload: SettingsPatchRequest,
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> SettingsResponse:
    _, user = auth
    settings = get_or_create_workspace_settings(db, user.workspace_id)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(settings, field, value)
    if payload.base_currency is not None or payload.reporting_timezone is not None:
        workspace = db.get(Workspace, user.workspace_id)
        if workspace is not None:
            if payload.base_currency is not None:
                workspace.reporting_currency = payload.base_currency
            if payload.reporting_timezone is not None:
                workspace.timezone = payload.reporting_timezone
    settings.updated_at = utc_now()
    db.commit()
    db.refresh(settings)
    return _serialize_settings(settings)


@router.get("/api-keys", response_model=list[ApiKeyResponse])
def list_api_keys(
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> list[ApiKeyResponse]:
    _, user = auth
    keys = db.scalars(
        select(ApiKey).where(ApiKey.workspace_id == user.workspace_id, ApiKey.revoked_at.is_(None))
    ).all()
    return [
        ApiKeyResponse(
            id=key.id,
            label=key.label,
            key_type=key.key_type,
            key_prefix=key.key_prefix,
            created_at=key.created_at,
        )
        for key in keys
    ]


@router.post("/api-keys", response_model=ApiKeyCreateResponse)
def create_api_key(
    payload: ApiKeyCreateRequest,
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> ApiKeyCreateResponse:
    _, user = auth
    plain = f"crb_{secrets.token_urlsafe(24)}"
    key = ApiKey(
        workspace_id=user.workspace_id,
        label=payload.label,
        key_type=payload.key_type,
        key_prefix=plain[:10],
        lookup_hash=hashlib.sha256(plain.encode("utf-8")).hexdigest(),
        key_hash=hash_password(plain),
    )
    db.add(key)
    db.commit()
    db.refresh(key)
    return ApiKeyCreateResponse(
        id=key.id,
        label=key.label,
        key_type=key.key_type,
        key_prefix=key.key_prefix,
        created_at=key.created_at,
        plain_text_key=plain,
    )


@router.delete("/api-keys/{key_id}", response_model=dict)
def delete_api_key(
    key_id: str,
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> dict:
    _, user = auth
    key = db.get(ApiKey, key_id)
    if key is None or key.workspace_id != user.workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    key.revoked_at = utc_now()
    db.commit()
    return {"detail": "API key revoked"}
