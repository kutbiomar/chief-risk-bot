from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models.auth import WorkspaceSetting
from ..models.identity import User, Workspace
from .auth.password import hash_password


def ensure_demo_workspace(db: Session) -> None:
    settings = get_settings()
    workspace = db.get(Workspace, settings.demo_workspace_id)
    if workspace is None:
        db.add(
            Workspace(
                id=settings.demo_workspace_id,
                name="Demo Workspace",
                reporting_currency=settings.base_currency_default,
                timezone="UTC",
            )
        )

    user = db.get(User, settings.demo_user_id)
    if user is None:
        db.add(
            User(
                id=settings.demo_user_id,
                workspace_id=settings.demo_workspace_id,
                email=settings.demo_user_email,
                display_name="Demo User",
                role="admin",
                password_hash=hash_password(settings.demo_user_password),
            )
        )

    workspace_settings = db.get(WorkspaceSetting, settings.demo_workspace_id)
    if workspace_settings is None:
        db.add(
            WorkspaceSetting(
                workspace_id=settings.demo_workspace_id,
                briefing_day="Monday",
                briefing_time="06:00",
                briefing_recipients="",
                briefing_auto_publish=False,
                briefing_send_pdf=False,
                briefing_include_audit_footer=False,
                ai_model="deterministic-mvp2-briefing",
                ai_risk_tone="conservative",
                ai_allow_trade_actions=False,
                base_currency=settings.base_currency_default,
                reporting_timezone="UTC",
                liquidity_buffer_default=settings.liquidity_buffer_default,
                updated_at=datetime.now(timezone.utc),
            )
        )

    db.commit()


def get_or_create_workspace_settings(db: Session, workspace_id: str) -> WorkspaceSetting:
    settings = db.get(WorkspaceSetting, workspace_id)
    if settings is None:
        workspace = db.get(Workspace, workspace_id)
        settings = WorkspaceSetting(
            workspace_id=workspace_id,
            briefing_day="Monday",
            briefing_time="06:00",
            briefing_recipients="",
            briefing_auto_publish=False,
            briefing_send_pdf=False,
            briefing_include_audit_footer=False,
            ai_model="deterministic-mvp2-briefing",
            ai_risk_tone="conservative",
            ai_allow_trade_actions=False,
            base_currency=workspace.reporting_currency if workspace else "USD",
            reporting_timezone=workspace.timezone if workspace else "UTC",
            liquidity_buffer_default=get_settings().liquidity_buffer_default,
            updated_at=datetime.now(timezone.utc),
        )
        db.add(settings)
        db.flush()
    return settings
