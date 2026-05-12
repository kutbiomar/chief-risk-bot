from __future__ import annotations

import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.deps import get_db
from backend.models.auth import ApiKey, User, UserSession, WorkspaceSetting
from backend.models.portfolio import Workspace
from backend.routers.auth import ADMIN_ROLES, require_cookie_csrf, require_roles, require_session
from backend.schemas.auth import MessageResponse
from backend.schemas.content import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyResponse,
    SettingsPatchRequest,
    SettingsResponse,
)
from backend.services.auth.password import hash_password
from backend.services.auth.session import utc_now
from backend.services.scheduler import get_scheduler_manager

router = APIRouter(prefix="/settings", tags=["settings"])


class InviteMemberRequest(BaseModel):
    email: str
    role: str = "viewer"


class MemberRoleRequest(BaseModel):
    role: str


def _get_or_create_settings(db: Session, workspace_id: str) -> WorkspaceSetting:
    settings = db.get(WorkspaceSetting, workspace_id)
    if settings is None:
        settings = WorkspaceSetting(workspace_id=workspace_id, updated_at=utc_now())
        db.add(settings)
        db.flush()
    return settings


def _serialize_settings(settings: WorkspaceSetting) -> SettingsResponse:
    return SettingsResponse(
        briefing_day=settings.briefing_day,
        briefing_time=settings.briefing_time,
        briefing_recipients=settings.briefing_recipients,
        briefing_auto_publish=settings.briefing_auto_publish,
        briefing_send_pdf=settings.briefing_send_pdf,
        briefing_include_audit_footer=settings.briefing_include_audit_footer,
        reporting_currency=settings.reporting_currency,
        ai_model=settings.ai_model,
        ai_risk_tone=settings.ai_risk_tone,
        ai_custom_instructions=settings.ai_custom_instructions,
        ai_allow_trade_actions=settings.ai_allow_trade_actions,
    )


@router.get("", response_model=SettingsResponse)
def get_settings_endpoint(
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> SettingsResponse:
    _, user = auth
    settings = _get_or_create_settings(db, user.workspace_id)
    db.commit()
    return _serialize_settings(settings)


@router.patch("", response_model=SettingsResponse, dependencies=[Depends(require_cookie_csrf)])
def patch_settings(
    payload: SettingsPatchRequest,
    auth=Depends(require_roles(*ADMIN_ROLES)),
    db: Session = Depends(get_db),
) -> SettingsResponse:
    _, user = auth
    settings = _get_or_create_settings(db, user.workspace_id)
    _PATCHABLE = {
        "briefing_day", "briefing_time", "briefing_recipients", "briefing_auto_publish",
        "briefing_send_pdf", "briefing_include_audit_footer",
        "reporting_currency",
        "ai_model", "ai_risk_tone", "ai_custom_instructions", "ai_allow_trade_actions",
    }
    for field, value in payload.model_dump(exclude_none=True).items():
        if field in _PATCHABLE:
            setattr(settings, field, value)
    settings.updated_at = utc_now()
    db.commit()
    db.refresh(settings)
    get_scheduler_manager().sync_workspace_job(user.workspace_id)
    return _serialize_settings(settings)


@router.put("", response_model=SettingsResponse, dependencies=[Depends(require_cookie_csrf)])
def put_settings(
    payload: SettingsPatchRequest,
    auth=Depends(require_roles(*ADMIN_ROLES)),
    db: Session = Depends(get_db),
) -> SettingsResponse:
    return patch_settings(payload, auth, db)


@router.get("/api-keys", response_model=list[ApiKeyResponse])
def list_api_keys(
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> list[ApiKeyResponse]:
    _, user = auth
    keys = db.scalars(select(ApiKey).where(ApiKey.workspace_id == user.workspace_id, ApiKey.revoked_at.is_(None))).all()
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


@router.post("/api-keys", response_model=ApiKeyCreateResponse, dependencies=[Depends(require_cookie_csrf)])
def create_api_key(
    payload: ApiKeyCreateRequest,
    auth=Depends(require_roles(*ADMIN_ROLES)),
    db: Session = Depends(get_db),
) -> ApiKeyCreateResponse:
    _, user = auth
    plain = f"crb_{secrets.token_urlsafe(24)}"
    lookup_hash = hashlib.sha256(plain.encode("utf-8")).hexdigest()
    key = ApiKey(
        workspace_id=user.workspace_id,
        user_id=user.id,
        label=payload.label,
        key_type=payload.key_type,
        key_prefix=plain[:10],
        lookup_hash=lookup_hash,
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


@router.delete("/api-keys/{key_id}", response_model=dict, dependencies=[Depends(require_cookie_csrf)])
def delete_api_key(
    key_id: str,
    auth=Depends(require_roles(*ADMIN_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    _, user = auth
    key = db.get(ApiKey, key_id)
    if key is None or key.workspace_id != user.workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    key.revoked_at = utc_now()
    db.commit()
    return {"detail": "API key revoked"}


@router.get("/members")
def list_members(
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> dict:
    _, user = auth
    members = db.scalars(select(User).where(User.workspace_id == user.workspace_id, User.disabled_at.is_(None))).all()
    return {
        "items": [
            {
                "id": member.id,
                "email": member.email,
                "display_name": member.display_name,
                "role": member.role,
                "last_active_at": member.last_active_at.isoformat() if member.last_active_at else None,
                "is_current_user": member.id == user.id,
            }
            for member in members
        ],
        "invites": [],
    }


@router.post("/members/invite", dependencies=[Depends(require_cookie_csrf)])
def invite_member(
    payload: InviteMemberRequest,
    auth=Depends(require_roles(*ADMIN_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    # Roadmap: replace this MVP placeholder with persisted invites, expiry, email, and accept flow.
    _, user = auth
    return {
        "id": f"pending-{payload.email}",
        "email": payload.email,
        "role": payload.role,
        "status": "pending",
        "workspace_id": user.workspace_id,
    }


@router.put("/members/{member_id}", dependencies=[Depends(require_cookie_csrf)])
def update_member(
    member_id: str,
    payload: MemberRoleRequest,
    auth=Depends(require_roles(*ADMIN_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    _, user = auth
    member = db.get(User, member_id)
    if member is None or member.workspace_id != user.workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    member.role = payload.role
    db.commit()
    return {"detail": "Member updated"}


@router.delete("/members/{member_id}", response_model=MessageResponse, dependencies=[Depends(require_cookie_csrf)])
def delete_member(
    member_id: str,
    auth=Depends(require_roles(*ADMIN_ROLES)),
    db: Session = Depends(get_db),
) -> MessageResponse:
    _, user = auth
    if member_id == user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot remove your own account")
    member = db.get(User, member_id)
    if member is None or member.workspace_id != user.workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    member.disabled_at = utc_now()
    db.commit()
    return MessageResponse(detail="Member removed")


@router.delete("/invites/{invite_id}", response_model=MessageResponse, dependencies=[Depends(require_cookie_csrf)])
def cancel_invite(invite_id: str, auth=Depends(require_roles(*ADMIN_ROLES))) -> MessageResponse:
    # Roadmap: enforce workspace ownership once invites are persisted.
    return MessageResponse(detail="Invite cancelled")


@router.get("/security")
def get_security(
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> dict:
    session, user = auth
    sessions = db.scalars(
        select(UserSession).where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
    ).all()
    return {
        "totp_enabled": user.totp_enabled,
        "sessions": [
            {
                "id": item.id,
                "device_info": item.device_info,
                "last_seen_at": item.last_seen_at.isoformat() if item.last_seen_at else None,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "current": session is not None and item.id == session.id,
            }
            for item in sessions
        ],
        "login_history": [],
    }


@router.delete("/sessions/{session_id}", response_model=MessageResponse, dependencies=[Depends(require_cookie_csrf)])
def revoke_session(
    session_id: str,
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> MessageResponse:
    _, user = auth
    session = db.get(UserSession, session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    session.revoked_at = utc_now()
    db.commit()
    return MessageResponse(detail="Session revoked")


@router.get("/billing-portal")
def billing_portal(auth=Depends(require_session), db: Session = Depends(get_db)) -> dict:
    # Roadmap: hide this or replace it with a configured Stripe billing portal integration.
    _, user = auth
    workspace = db.get(Workspace, user.workspace_id)
    return {
        "url": "https://billing.stripe.com/p/login/test",
        "plan": workspace.plan if workspace is not None else "starter",
    }
