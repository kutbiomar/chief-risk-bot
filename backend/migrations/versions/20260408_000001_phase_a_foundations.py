"""phase a foundations

Revision ID: 20260408_000001
Revises:
Create Date: 2026-04-08
"""

from alembic import op
import sqlalchemy as sa


revision = "20260408_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False, unique=True),
        sa.Column("reporting_currency", sa.String(length=8), nullable=False),
        sa.Column("timezone", sa.Text(), nullable=False),
        sa.Column("address", sa.Text()),
        sa.Column("plan", sa.Text(), nullable=False),
        sa.Column("seat_limit", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("email", sa.Text(), nullable=False, unique=True),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text()),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("totp_secret", sa.Text()),
        sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_active_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("disabled_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("session_family_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("csrf_secret", sa.Text(), nullable=False),
        sa.Column("device_info", sa.Text(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_token_hash", "user_sessions", ["token_hash"])
    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("key_type", sa.Text(), nullable=False),
        sa.Column("key_prefix", sa.Text(), nullable=False),
        sa.Column("lookup_hash", sa.Text(), nullable=False, unique=True),
        sa.Column("key_hash", sa.Text(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("rotated_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_api_keys_workspace_id", "api_keys", ["workspace_id"])
    op.create_index("ix_api_keys_lookup_hash", "api_keys", ["lookup_hash"])
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column("invalidated_at", sa.DateTime(timezone=True)),
        sa.Column("requested_ip", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
    op.create_table(
        "auth_challenges",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("challenge_type", sa.Text(), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False, unique=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_auth_challenges_user_id", "auth_challenges", ["user_id"])
    op.create_table(
        "workspace_settings",
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), primary_key=True),
        sa.Column("briefing_day", sa.Text(), nullable=False),
        sa.Column("briefing_time", sa.Text(), nullable=False),
        sa.Column("briefing_recipients", sa.Text(), nullable=False),
        sa.Column("briefing_auto_publish", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("briefing_send_pdf", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("briefing_include_audit_footer", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ai_model", sa.Text(), nullable=False),
        sa.Column("ai_risk_tone", sa.Text(), nullable=False),
        sa.Column("ai_custom_instructions", sa.Text()),
        sa.Column("ai_allow_trade_actions", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sso_mode", sa.Text(), nullable=False),
        sa.Column("sso_google_hosted_domain", sa.Text()),
        sa.Column("saml_entity_id", sa.Text()),
        sa.Column("saml_sso_url", sa.Text()),
        sa.Column("saml_x509_cert", sa.Text()),
        sa.Column("saml_sp_entity_id", sa.Text()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "async_jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("job_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(length=36), sa.ForeignKey("users.id")),
        sa.Column("resource_type", sa.Text()),
        sa.Column("resource_id", sa.Text()),
        sa.Column("request_json", sa.Text()),
        sa.Column("result_json", sa.Text()),
        sa.Column("error_message", sa.Text()),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_children", sa.Integer()),
        sa.Column("succeeded_children", sa.Integer()),
        sa.Column("failed_children", sa.Integer()),
        sa.Column("progress_pct", sa.Integer()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_async_jobs_workspace_id", "async_jobs", ["workspace_id"])
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), sa.ForeignKey("users.id")),
        sa.Column("actor_type", sa.Text(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("subject_type", sa.Text(), nullable=False),
        sa.Column("subject_id", sa.Text(), nullable=False),
        sa.Column("detail_json", sa.Text(), nullable=False),
        sa.Column("ip_address", sa.Text()),
        sa.Column("device_info", sa.Text()),
        sa.Column("prev_hash", sa.Text(), nullable=False),
        sa.Column("event_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_events_workspace_id", "audit_events", ["workspace_id"])
    op.create_table(
        "portfolio_snapshots",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("parent_snapshot_id", sa.String(length=36), sa.ForeignKey("portfolio_snapshots.id")),
        sa.Column("uploaded_by", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.Text()),
        sa.Column("raw_bytes", sa.LargeBinary()),
        sa.Column("position_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_aum_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("enriched_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_portfolio_snapshots_workspace_id", "portfolio_snapshots", ["workspace_id"])
    op.create_index("ix_portfolio_snapshots_parent_snapshot_id", "portfolio_snapshots", ["parent_snapshot_id"])
    op.create_table(
        "positions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("snapshot_id", sa.String(length=36), sa.ForeignKey("portfolio_snapshots.id"), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("security_id", sa.Text()),
        sa.Column("ticker", sa.Text(), nullable=False),
        sa.Column("name", sa.Text()),
        sa.Column("position_currency", sa.String(length=8), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("price_local", sa.Float()),
        sa.Column("price_usd", sa.Float()),
        sa.Column("market_value_local", sa.Float()),
        sa.Column("market_value_usd", sa.Float()),
        sa.Column("asset_class", sa.Text(), nullable=False),
        sa.Column("geo_region", sa.Text()),
        sa.Column("sector", sa.Text()),
        sa.Column("market_segment", sa.Text()),
        sa.Column("custodian", sa.Text()),
        sa.Column("price_source", sa.Text(), nullable=False),
        sa.Column("beta_vs_spy", sa.Float()),
        sa.Column("daily_return", sa.Float()),
        sa.Column("notes", sa.Text()),
        sa.Column("override_value", sa.Float()),
        sa.Column("override_by", sa.String(length=36), sa.ForeignKey("users.id")),
        sa.Column("override_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_positions_snapshot_id", "positions", ["snapshot_id"])
    op.create_index("ix_positions_workspace_id", "positions", ["workspace_id"])


def downgrade() -> None:
    op.drop_index("ix_positions_workspace_id", table_name="positions")
    op.drop_index("ix_positions_snapshot_id", table_name="positions")
    op.drop_table("positions")
    op.drop_index("ix_portfolio_snapshots_parent_snapshot_id", table_name="portfolio_snapshots")
    op.drop_index("ix_portfolio_snapshots_workspace_id", table_name="portfolio_snapshots")
    op.drop_table("portfolio_snapshots")
    op.drop_index("ix_audit_events_workspace_id", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_async_jobs_workspace_id", table_name="async_jobs")
    op.drop_table("async_jobs")
    op.drop_table("workspace_settings")
    op.drop_index("ix_auth_challenges_user_id", table_name="auth_challenges")
    op.drop_table("auth_challenges")
    op.drop_index("ix_password_reset_tokens_user_id", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
    op.drop_index("ix_api_keys_lookup_hash", table_name="api_keys")
    op.drop_index("ix_api_keys_workspace_id", table_name="api_keys")
    op.drop_table("api_keys")
    op.drop_index("ix_user_sessions_token_hash", table_name="user_sessions")
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_table("users")
    op.drop_table("workspaces")
