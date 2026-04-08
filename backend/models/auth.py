from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base
from backend.models.common import TimestampMixin, uuid_pk


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = uuid_pk()
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text, nullable=False, default="owner")
    scope: Mapped[str] = mapped_column(Text, nullable=False, default="All clients")
    totp_secret: Mapped[Optional[str]] = mapped_column(Text)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_active_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    disabled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class UserSession(Base, TimestampMixin):
    __tablename__ = "user_sessions"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    session_family_id: Mapped[str] = mapped_column(String(36), nullable=False)
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    csrf_secret: Mapped[str] = mapped_column(Text, nullable=False)
    device_info: Mapped[str] = mapped_column(Text, nullable=False)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class ApiKey(Base, TimestampMixin):
    __tablename__ = "api_keys"

    id: Mapped[str] = uuid_pk()
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    key_type: Mapped[str] = mapped_column(Text, nullable=False)
    key_prefix: Mapped[str] = mapped_column(Text, nullable=False)
    lookup_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    key_hash: Mapped[str] = mapped_column(Text, nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    rotated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class PasswordResetToken(Base, TimestampMixin):
    __tablename__ = "password_reset_tokens"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    invalidated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    requested_ip: Mapped[Optional[str]] = mapped_column(Text)


class AuthChallenge(Base, TimestampMixin):
    __tablename__ = "auth_challenges"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    challenge_type: Mapped[str] = mapped_column(Text, nullable=False)
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class WorkspaceSetting(Base):
    __tablename__ = "workspace_settings"

    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id"), primary_key=True, nullable=False
    )
    briefing_day: Mapped[str] = mapped_column(Text, nullable=False, default="Monday")
    briefing_time: Mapped[str] = mapped_column(Text, nullable=False, default="06:00")
    briefing_recipients: Mapped[str] = mapped_column(Text, nullable=False, default="")
    briefing_auto_publish: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    briefing_send_pdf: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    briefing_include_audit_footer: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    ai_model: Mapped[str] = mapped_column(Text, nullable=False, default="claude-opus-4-6")
    ai_risk_tone: Mapped[str] = mapped_column(Text, nullable=False, default="conservative")
    ai_custom_instructions: Mapped[Optional[str]] = mapped_column(Text)
    ai_allow_trade_actions: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sso_mode: Mapped[str] = mapped_column(Text, nullable=False, default="disabled")
    sso_google_hosted_domain: Mapped[Optional[str]] = mapped_column(Text)
    saml_entity_id: Mapped[Optional[str]] = mapped_column(Text)
    saml_sso_url: Mapped[Optional[str]] = mapped_column(Text)
    saml_x509_cert: Mapped[Optional[str]] = mapped_column(Text)
    saml_sp_entity_id: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
