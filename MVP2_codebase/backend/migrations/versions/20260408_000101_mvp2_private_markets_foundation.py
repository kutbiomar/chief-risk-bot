"""mvp2 private markets foundation

Revision ID: 20260408_000101
Revises:
Create Date: 2026-04-08 19:15:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260408_000101"
down_revision = None
branch_labels = None
depends_on = None


TENANT_TABLES = (
    "funds",
    "commitments",
    "extraction_results",
    "documents",
    "capital_events",
    "holdings",
    "deals",
    "deal_documents",
    "reconciliation_flags",
    "liquidity_projections",
    "fx_rates",
    "weekly_briefings",
    "cell_audit_events",
)


def _enable_postgres_rls(table_name: str) -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(f'ALTER TABLE "{table_name}" ENABLE ROW LEVEL SECURITY')


def _create_workspace_policy(table_name: str) -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(
        f"""
        CREATE POLICY {table_name}_workspace_isolation ON "{table_name}"
        USING (
            workspace_id = current_setting('app.current_workspace_id', true)::uuid
            OR workspace_id IS NULL
        )
        WITH CHECK (
            workspace_id = current_setting('app.current_workspace_id', true)::uuid
            OR workspace_id IS NULL
        )
        """
    )


def _drop_workspace_policy(table_name: str) -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(f'DROP POLICY IF EXISTS {table_name}_workspace_isolation ON "{table_name}"')


def _supports_alter_fk() -> bool:
    bind = op.get_bind()
    return bind.dialect.name != "sqlite"


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("reporting_currency", sa.Text(), nullable=False, server_default="USD"),
        sa.Column("timezone", sa.Text(), nullable=False, server_default="UTC"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
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
        sa.Column("role", sa.Text(), nullable=False, server_default="admin"),
        sa.Column("scope", sa.Text(), nullable=False, server_default="All clients"),
        sa.Column("totp_secret", sa.Text()),
        sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_active_at", sa.DateTime(timezone=True)),
        sa.Column("disabled_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_workspace_id", "users", ["workspace_id"])

    op.create_table(
        "workspace_settings",
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), primary_key=True),
        sa.Column("briefing_day", sa.Text(), nullable=False, server_default="Monday"),
        sa.Column("briefing_time", sa.Text(), nullable=False, server_default="06:00"),
        sa.Column("briefing_recipients", sa.Text(), nullable=False, server_default=""),
        sa.Column("briefing_auto_publish", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("briefing_send_pdf", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("briefing_include_audit_footer", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ai_model", sa.Text(), nullable=False, server_default="claude-sonnet"),
        sa.Column("ai_risk_tone", sa.Text(), nullable=False, server_default="conservative"),
        sa.Column("ai_custom_instructions", sa.Text()),
        sa.Column("ai_allow_trade_actions", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("base_currency", sa.Text(), nullable=False, server_default="USD"),
        sa.Column("reporting_timezone", sa.Text(), nullable=False, server_default="UTC"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "funds",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("manager_name", sa.Text(), nullable=False),
        sa.Column("vintage_year", sa.Integer()),
        sa.Column("fund_size", sa.Numeric(18, 2)),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("jurisdiction", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_funds_workspace_id", "funds", ["workspace_id"])
    op.create_index("ix_funds_name", "funds", ["name"])
    op.create_index("ix_funds_type", "funds", ["type"])
    op.create_index("ix_funds_manager_name", "funds", ["manager_name"])

    op.create_table(
        "commitments",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("fund_id", sa.String(length=36), sa.ForeignKey("funds.id"), nullable=False),
        sa.Column("committed_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("commitment_currency", sa.Text(), nullable=False),
        sa.Column("committed_amount_base", sa.Numeric(18, 2)),
        sa.Column("committed_amount_fx_rate", sa.Numeric(18, 8)),
        sa.Column("called_capital", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("called_capital_base", sa.Numeric(18, 2)),
        sa.Column("called_capital_fx_rate", sa.Numeric(18, 8)),
        sa.Column("uncalled_capital", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("uncalled_capital_base", sa.Numeric(18, 2)),
        sa.Column("uncalled_capital_fx_rate", sa.Numeric(18, 8)),
        sa.Column("nav", sa.Numeric(18, 2)),
        sa.Column("nav_base", sa.Numeric(18, 2)),
        sa.Column("nav_fx_rate", sa.Numeric(18, 8)),
        sa.Column("nav_date", sa.Date()),
        sa.Column("nav_is_estimated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("nav_confidence_pct", sa.Numeric(5, 2)),
        sa.Column("distributions_received", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("distributions_received_base", sa.Numeric(18, 2)),
        sa.Column("distributions_received_fx_rate", sa.Numeric(18, 8)),
        sa.Column("management_fee_rate", sa.Numeric(8, 4)),
        sa.Column("carry_rate", sa.Numeric(8, 4)),
        sa.Column("remaining_fund_life_months", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_commitments_workspace_id", "commitments", ["workspace_id"])
    op.create_index("ix_commitments_fund_id", "commitments", ["fund_id"])

    op.create_table(
        "extraction_results",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=True),
        sa.Column("document_type", sa.Text(), nullable=False),
        sa.Column("classification_confidence", sa.Integer()),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("extracted_json", sa.JSON(), nullable=False),
        sa.Column("confidence_json", sa.JSON(), nullable=False),
        sa.Column("needs_review_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("raw_text_truncated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_extraction_results_workspace_id", "extraction_results", ["workspace_id"])
    op.create_index("ix_extraction_results_document_type", "extraction_results", ["document_type"])

    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("uploaded_by_user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("fund_id", sa.String(length=36), sa.ForeignKey("funds.id")),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("file_type", sa.Text(), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("provider_name", sa.Text()),
        sa.Column("auto_category", sa.Text(), nullable=False, server_default="other"),
        sa.Column("processing_status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("extracted_data", sa.JSON(), nullable=False),
        sa.Column("reconciliation_flags", sa.JSON(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("replaces_document_id", sa.String(length=36), sa.ForeignKey("documents.id")),
        sa.Column("extraction_result_id", sa.String(length=36), sa.ForeignKey("extraction_results.id")),
        sa.Column("needs_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_documents_workspace_id", "documents", ["workspace_id"])
    op.create_index("ix_documents_uploaded_by_user_id", "documents", ["uploaded_by_user_id"])
    op.create_index("ix_documents_fund_id", "documents", ["fund_id"])
    op.create_index("ix_documents_provider_name", "documents", ["provider_name"])
    op.create_index("ix_documents_auto_category", "documents", ["auto_category"])
    op.create_index("ix_documents_processing_status", "documents", ["processing_status"])

    if _supports_alter_fk():
        op.create_foreign_key(
            "fk_extraction_results_document_id_documents",
            "extraction_results",
            "documents",
            ["document_id"],
            ["id"],
        )

    op.create_table(
        "capital_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("fund_id", sa.String(length=36), sa.ForeignKey("funds.id"), nullable=False),
        sa.Column("commitment_id", sa.String(length=36), sa.ForeignKey("commitments.id")),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("amount_base", sa.Numeric(18, 2)),
        sa.Column("amount_fx_rate", sa.Numeric(18, 8)),
        sa.Column("notice_date", sa.Date()),
        sa.Column("due_date", sa.Date()),
        sa.Column("effective_date", sa.Date()),
        sa.Column("source_document_id", sa.String(length=36), sa.ForeignKey("documents.id")),
        sa.Column("notes", sa.Text()),
        sa.Column("is_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("recall_period_days", sa.Integer()),
        sa.Column("recall_expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_capital_events_workspace_id", "capital_events", ["workspace_id"])
    op.create_index("ix_capital_events_fund_id", "capital_events", ["fund_id"])
    op.create_index("ix_capital_events_commitment_id", "capital_events", ["commitment_id"])
    op.create_index("ix_capital_events_type", "capital_events", ["type"])
    op.create_index("ix_capital_events_due_date", "capital_events", ["due_date"])
    op.create_index("ix_capital_events_effective_date", "capital_events", ["effective_date"])
    op.create_index("ix_capital_events_source_document_id", "capital_events", ["source_document_id"])

    op.create_table(
        "holdings",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("fund_id", sa.String(length=36), sa.ForeignKey("funds.id")),
        sa.Column("commitment_id", sa.String(length=36), sa.ForeignKey("commitments.id")),
        sa.Column("asset_name", sa.Text(), nullable=False),
        sa.Column("asset_type", sa.Text(), nullable=False),
        sa.Column("geo_region", sa.Text()),
        sa.Column("sector", sa.Text()),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6)),
        sa.Column("unit_cost", sa.Numeric(18, 6)),
        sa.Column("current_value", sa.Numeric(18, 2)),
        sa.Column("current_value_base", sa.Numeric(18, 2)),
        sa.Column("current_value_fx_rate", sa.Numeric(18, 8)),
        sa.Column("current_value_date", sa.Date()),
        sa.Column("current_value_source", sa.Text(), nullable=False, server_default="estimated"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_holdings_workspace_id", "holdings", ["workspace_id"])
    op.create_index("ix_holdings_fund_id", "holdings", ["fund_id"])
    op.create_index("ix_holdings_commitment_id", "holdings", ["commitment_id"])
    op.create_index("ix_holdings_asset_name", "holdings", ["asset_name"])
    op.create_index("ix_holdings_asset_type", "holdings", ["asset_type"])
    op.create_index("ix_holdings_geo_region", "holdings", ["geo_region"])
    op.create_index("ix_holdings_sector", "holdings", ["sector"])

    op.create_table(
        "deals",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("stage", sa.Text(), nullable=False),
        sa.Column("asset_type", sa.Text()),
        sa.Column("target_commitment", sa.Numeric(18, 2)),
        sa.Column("target_commitment_currency", sa.Text()),
        sa.Column("target_commitment_base", sa.Numeric(18, 2)),
        sa.Column("target_commitment_fx_rate", sa.Numeric(18, 8)),
        sa.Column("target_close_date", sa.Date()),
        sa.Column("lead_analyst_id", sa.String(length=36), sa.ForeignKey("users.id")),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_deals_workspace_id", "deals", ["workspace_id"])
    op.create_index("ix_deals_name", "deals", ["name"])
    op.create_index("ix_deals_stage", "deals", ["stage"])
    op.create_index("ix_deals_target_close_date", "deals", ["target_close_date"])
    op.create_index("ix_deals_lead_analyst_id", "deals", ["lead_analyst_id"])

    op.create_table(
        "deal_documents",
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("deal_id", sa.String(length=36), sa.ForeignKey("deals.id"), nullable=False),
        sa.Column("document_id", sa.String(length=36), sa.ForeignKey("documents.id"), nullable=False),
        sa.PrimaryKeyConstraint("deal_id", "document_id"),
    )
    op.create_index("ix_deal_documents_workspace_id", "deal_documents", ["workspace_id"])

    op.create_table(
        "reconciliation_flags",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("document_id", sa.String(length=36), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.Text()),
        sa.Column("field_name", sa.Text(), nullable=False),
        sa.Column("document_value", sa.Text()),
        sa.Column("system_value", sa.Text()),
        sa.Column("variance_pct", sa.Numeric(8, 4)),
        sa.Column("severity", sa.Text(), nullable=False, server_default="medium"),
        sa.Column("flagged_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_by", sa.String(length=36), sa.ForeignKey("users.id")),
        sa.Column("resolution_notes", sa.Text()),
        sa.Column("status", sa.Text(), nullable=False, server_default="open"),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_reconciliation_flags_workspace_id", "reconciliation_flags", ["workspace_id"])
    op.create_index("ix_reconciliation_flags_document_id", "reconciliation_flags", ["document_id"])
    op.create_index("ix_reconciliation_flags_entity_type", "reconciliation_flags", ["entity_type"])
    op.create_index("ix_reconciliation_flags_entity_id", "reconciliation_flags", ["entity_id"])

    op.create_table(
        "liquidity_projections",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("projection_months", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("base_currency", sa.Text(), nullable=False),
        sa.Column("scenario", sa.Text(), nullable=False, server_default="base"),
        sa.Column("liquidity_buffer", sa.Numeric(18, 2)),
        sa.Column("monthly_buckets", sa.JSON(), nullable=False),
        sa.Column("liquidity_gaps", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_liquidity_projections_workspace_id", "liquidity_projections", ["workspace_id"])

    op.create_table(
        "fx_rates",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id")),
        sa.Column("base_currency", sa.Text(), nullable=False),
        sa.Column("quote_currency", sa.Text(), nullable=False),
        sa.Column("rate", sa.Numeric(18, 8), nullable=False),
        sa.Column("rate_date", sa.Date(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False, server_default="ecb"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("workspace_id", "base_currency", "quote_currency", "rate_date"),
    )
    op.create_index("ix_fx_rates_workspace_id", "fx_rates", ["workspace_id"])

    op.create_table(
        "weekly_briefings",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("generated_by", sa.String(length=36), sa.ForeignKey("users.id")),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.Text(), nullable=False, server_default="draft"),
        sa.Column("week_label", sa.Text(), nullable=False),
        sa.Column("output_json", sa.JSON(), nullable=False),
        sa.Column("model", sa.Text()),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("published_by", sa.String(length=36), sa.ForeignKey("users.id")),
        sa.Column("pdf_path", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_weekly_briefings_workspace_id", "weekly_briefings", ["workspace_id"])
    op.create_index("ix_weekly_briefings_week_label", "weekly_briefings", ["week_label"])

    op.create_table(
        "cell_audit_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.Text(), nullable=False),
        sa.Column("field_name", sa.Text(), nullable=False),
        sa.Column("old_value", sa.Text()),
        sa.Column("new_value", sa.Text()),
        sa.Column("changed_by", sa.String(length=36), sa.ForeignKey("users.id")),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_cell_audit_events_workspace_id", "cell_audit_events", ["workspace_id"])
    op.create_index("ix_cell_audit_events_entity_type", "cell_audit_events", ["entity_type"])
    op.create_index("ix_cell_audit_events_entity_id", "cell_audit_events", ["entity_id"])

    for table_name in TENANT_TABLES:
        _enable_postgres_rls(table_name)
        _create_workspace_policy(table_name)


def downgrade() -> None:
    for table_name in reversed(TENANT_TABLES):
        _drop_workspace_policy(table_name)

    op.drop_index("ix_cell_audit_events_entity_id", table_name="cell_audit_events")
    op.drop_index("ix_cell_audit_events_entity_type", table_name="cell_audit_events")
    op.drop_index("ix_cell_audit_events_workspace_id", table_name="cell_audit_events")
    op.drop_table("cell_audit_events")

    op.drop_index("ix_weekly_briefings_week_label", table_name="weekly_briefings")
    op.drop_index("ix_weekly_briefings_workspace_id", table_name="weekly_briefings")
    op.drop_table("weekly_briefings")

    op.drop_index("ix_fx_rates_workspace_id", table_name="fx_rates")
    op.drop_table("fx_rates")

    op.drop_index("ix_liquidity_projections_workspace_id", table_name="liquidity_projections")
    op.drop_table("liquidity_projections")

    op.drop_index("ix_reconciliation_flags_entity_id", table_name="reconciliation_flags")
    op.drop_index("ix_reconciliation_flags_entity_type", table_name="reconciliation_flags")
    op.drop_index("ix_reconciliation_flags_document_id", table_name="reconciliation_flags")
    op.drop_index("ix_reconciliation_flags_workspace_id", table_name="reconciliation_flags")
    op.drop_table("reconciliation_flags")

    op.drop_index("ix_deal_documents_workspace_id", table_name="deal_documents")
    op.drop_table("deal_documents")

    op.drop_index("ix_deals_lead_analyst_id", table_name="deals")
    op.drop_index("ix_deals_target_close_date", table_name="deals")
    op.drop_index("ix_deals_stage", table_name="deals")
    op.drop_index("ix_deals_name", table_name="deals")
    op.drop_index("ix_deals_workspace_id", table_name="deals")
    op.drop_table("deals")

    op.drop_index("ix_holdings_sector", table_name="holdings")
    op.drop_index("ix_holdings_geo_region", table_name="holdings")
    op.drop_index("ix_holdings_asset_type", table_name="holdings")
    op.drop_index("ix_holdings_asset_name", table_name="holdings")
    op.drop_index("ix_holdings_commitment_id", table_name="holdings")
    op.drop_index("ix_holdings_fund_id", table_name="holdings")
    op.drop_index("ix_holdings_workspace_id", table_name="holdings")
    op.drop_table("holdings")

    op.drop_index("ix_capital_events_source_document_id", table_name="capital_events")
    op.drop_index("ix_capital_events_effective_date", table_name="capital_events")
    op.drop_index("ix_capital_events_due_date", table_name="capital_events")
    op.drop_index("ix_capital_events_type", table_name="capital_events")
    op.drop_index("ix_capital_events_commitment_id", table_name="capital_events")
    op.drop_index("ix_capital_events_fund_id", table_name="capital_events")
    op.drop_index("ix_capital_events_workspace_id", table_name="capital_events")
    op.drop_table("capital_events")

    if _supports_alter_fk():
        op.drop_constraint("fk_extraction_results_document_id_documents", "extraction_results", type_="foreignkey")

    op.drop_index("ix_documents_processing_status", table_name="documents")
    op.drop_index("ix_documents_auto_category", table_name="documents")
    op.drop_index("ix_documents_provider_name", table_name="documents")
    op.drop_index("ix_documents_fund_id", table_name="documents")
    op.drop_index("ix_documents_uploaded_by_user_id", table_name="documents")
    op.drop_index("ix_documents_workspace_id", table_name="documents")
    op.drop_table("documents")

    op.drop_index("ix_extraction_results_document_type", table_name="extraction_results")
    op.drop_index("ix_extraction_results_workspace_id", table_name="extraction_results")
    op.drop_table("extraction_results")

    op.drop_index("ix_commitments_fund_id", table_name="commitments")
    op.drop_index("ix_commitments_workspace_id", table_name="commitments")
    op.drop_table("commitments")

    op.drop_index("ix_funds_manager_name", table_name="funds")
    op.drop_index("ix_funds_type", table_name="funds")
    op.drop_index("ix_funds_name", table_name="funds")
    op.drop_index("ix_funds_workspace_id", table_name="funds")
    op.drop_table("funds")
    op.drop_table("workspace_settings")
    op.drop_index("ix_users_workspace_id", table_name="users")
    op.drop_table("users")
    op.drop_table("workspaces")
