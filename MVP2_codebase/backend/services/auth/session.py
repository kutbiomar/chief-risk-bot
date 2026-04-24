from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...config import get_settings
from ...models.auth import UserSession
from ...models.identity import User

SESSION_COOKIE_NAME = "__crb_session"
CSRF_COOKIE_NAME = "__crb_csrf"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def make_opaque_token() -> str:
    return secrets.token_urlsafe(32)


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def create_session(db: Session, user: User, device_info: str) -> Tuple[UserSession, str]:
    settings = get_settings()
    raw_token = make_opaque_token()
    csrf_secret = make_opaque_token()
    session = UserSession(
        user_id=user.id,
        session_family_id=str(uuid4()),
        token_hash=sha256_hex(raw_token),
        csrf_secret=csrf_secret,
        device_info=device_info,
        last_seen_at=utc_now(),
        expires_at=utc_now() + timedelta(days=30),
    )
    db.add(session)
    db.flush()
    return session, raw_token


def get_session_by_token(db: Session, raw_token: str) -> Optional[UserSession]:
    token_hash = sha256_hex(raw_token)
    session = db.scalar(
        select(UserSession).where(
            UserSession.token_hash == token_hash,
            UserSession.revoked_at.is_(None),
        )
    )
    if session is None or ensure_utc(session.expires_at) <= utc_now():
        return None
    return session
