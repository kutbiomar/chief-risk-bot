from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import Settings, get_settings
from .database import get_db_session
from .models.auth import ApiKey
from .models.identity import User
from .services.documents import parse_document
from .services.auth.password import verify_password
from .services.auth.session import SESSION_COOKIE_NAME, get_session_by_token, sha256_hex, utc_now


@dataclass
class CurrentUser:
    id: str
    workspace_id: str
    role: str = "admin"


def get_db() -> Generator[Session, None, None]:
    yield from get_db_session()


def get_app_settings() -> Settings:
    return get_settings()


def get_claude_client(settings: Settings = None):
    settings = settings or get_settings()
    if not settings.anthropic_api_key:
        return None
    try:
        import anthropic

        return anthropic.Anthropic(api_key=settings.anthropic_api_key)
    except Exception:
        return None


def get_document_processor():
    return parse_document


def _bearer_token(request: Request) -> Optional[str]:
    authorization = request.headers.get("Authorization")
    if not authorization:
        return None
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() != "bearer" or not value:
        return None
    return value


def _resolve_api_key_user(db: Session, raw_token: str) -> Optional[User]:
    key = db.scalar(
        select(ApiKey).where(ApiKey.lookup_hash == sha256_hex(raw_token), ApiKey.revoked_at.is_(None))
    )
    if key is None or not verify_password(raw_token, key.key_hash):
        return None
    user = db.scalar(
        select(User)
        .where(User.workspace_id == key.workspace_id, User.disabled_at.is_(None))
        .order_by(User.created_at.asc())
    )
    if user is None:
        return None
    key.last_used_at = utc_now()
    db.flush()
    return user


def _current_user_from_session(db: Session, raw_token: str) -> Optional[CurrentUser]:
    session = get_session_by_token(db, raw_token)
    if session is not None:
        user = db.get(User, session.user_id)
        if user is not None and user.disabled_at is None:
            session.last_seen_at = utc_now()
            db.flush()
            return CurrentUser(id=user.id, workspace_id=user.workspace_id, role=user.role)

    user = _resolve_api_key_user(db, raw_token)
    if user is not None:
        return CurrentUser(id=user.id, workspace_id=user.workspace_id, role=user.role)
    return None


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    x_user_id: Optional[str] = Header(default=None),
    x_workspace_id: Optional[str] = Header(default=None),
    x_role: Optional[str] = Header(default=None),
) -> CurrentUser:
    settings = get_settings()
    raw_token = request.cookies.get(SESSION_COOKIE_NAME) or _bearer_token(request)
    if raw_token:
        current = _current_user_from_session(db, raw_token)
        if current is not None:
            return current

    if settings.environment == "development" and settings.allow_dev_auth_headers and x_user_id and x_workspace_id:
        return CurrentUser(id=x_user_id, workspace_id=x_workspace_id, role=x_role or "admin")

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
