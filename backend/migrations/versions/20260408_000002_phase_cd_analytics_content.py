"""phase c/d analytics and content tables

Revision ID: 20260408_000002
Revises: 20260408_000001
Create Date: 2026-04-08 11:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260408_000002"
down_revision = "20260408_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "price_cache",
        sa.Column("ticker", sa.Text(), primary_key=True),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("price_local", sa.Float(), nullable=False),
        sa.Column("price_usd", sa.Float(), nullable=False),
        sa.Column("daily_return_local", sa.Float(), nullable=False),
        sa.Column("daily_return_usd", sa.Float(), nullable=False),
        sa.Column("weekly_return_usd", sa.Float(), nullable=False),
        sa.Column("history_json", sa.Text(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ttl_hours", sa.Integer(), nullable=False),
    )
    op.create_table(
        "fx_cache",
        sa.Column("pair", sa.Text(), primary_key=True),
        sa.Column("base_currency", sa.String(length=8), nullable=False),
        sa.Column("quote_currency", sa.String(length=8), nullable=False),
        sa.Column("spot_rate", sa.Float(), nullable=False),
        sa.Column("history_json", sa.Text(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ttl_hours", sa.Integer(), nullable=False),
    )
    op.create_table(
        "macro_cache",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_macro_cache_workspace_id", "macro_cache", ["workspace_id"])
    op.create_table(
        "var_results",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("snapshot_id", sa.String(length=36), sa.ForeignKey("portfolio_snapshots.id"), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("var_1d_95", sa.Float(), nullable=False),
        sa.Column("var_1d_99", sa.Float(), nullable=False),
        sa.Column("cvar_1d_95", sa.Float(), nullable=False),
        sa.Column("cvar_1d_99", sa.Float(), nullable=False),
        sa.Column("max_drawdown_1y", sa.Float(), nullable=False),
        sa.Column("worst_scenario_date", sa.Date(), nullable=False),
        sa.Column("worst_scenario_loss", sa.Float(), nullable=False),
        sa.Column("lookback_days", sa.Integer(), nullable=False),
        sa.Column("effective_lookback_days", sa.Integer(), nullable=False),
        sa.Column("methodology", sa.Text(), nullable=False),
        sa.Column("model_coverage_pct", sa.Float(), nullable=False),
        sa.Column("unmodeled_value_usd", sa.Float(), nullable=False),
        sa.Column("position_contributions_json", sa.Text(), nullable=False),
        sa.Column("assumptions_json", sa.Text(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_var_results_snapshot_id", "var_results", ["snapshot_id"])
    op.create_index("ix_var_results_workspace_id", "var_results", ["workspace_id"])
    op.create_table(
        "risk_scores",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("snapshot_id", sa.String(length=36), sa.ForeignKey("portfolio_snapshots.id"), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("async_job_id", sa.String(length=36), sa.ForeignKey("async_jobs.id"), nullable=False),
        sa.Column("agent", sa.Text(), nullable=False),
        sa.Column("dimension", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("score", sa.Integer()),
        sa.Column("severity", sa.Text()),
        sa.Column("headline", sa.Text()),
        sa.Column("reasoning", sa.Text()),
        sa.Column("evidence_json", sa.Text(), nullable=False),
        sa.Column("conversation_prompt", sa.Text()),
        sa.Column("data_sources_json", sa.Text(), nullable=False),
        sa.Column("model", sa.Text()),
        sa.Column("prompt_version", sa.Text()),
        sa.Column("input_tokens", sa.Integer()),
        sa.Column("output_tokens", sa.Integer()),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_risk_scores_snapshot_id", "risk_scores", ["snapshot_id"])
    op.create_index("ix_risk_scores_workspace_id", "risk_scores", ["workspace_id"])
    op.create_index("ix_risk_scores_async_job_id", "risk_scores", ["async_job_id"])
    op.create_table(
        "risk_flags",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("snapshot_id", sa.String(length=36), sa.ForeignKey("portfolio_snapshots.id"), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("rule", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("ticker", sa.Text()),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_risk_flags_snapshot_id", "risk_flags", ["snapshot_id"])
    op.create_index("ix_risk_flags_workspace_id", "risk_flags", ["workspace_id"])
    op.create_table(
        "extraction_results",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("positions_json", sa.Text(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("confidence_json", sa.Text(), nullable=False),
        sa.Column("needs_review_count", sa.Integer(), nullable=False),
        sa.Column("raw_text_truncated", sa.Boolean(), nullable=False),
        sa.Column("extracted_row_count", sa.Integer(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_extraction_results_document_id", "extraction_results", ["document_id"])
    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("uploaded_by", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("file_type", sa.Text(), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.Text(), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("folder", sa.Text(), nullable=False),
        sa.Column("tag", sa.Text()),
        sa.Column("page_count", sa.Integer()),
        sa.Column("malware_scan_status", sa.Text(), nullable=False),
        sa.Column("extraction_status", sa.Text(), nullable=False),
        sa.Column("extraction_result_id", sa.String(length=36), sa.ForeignKey("extraction_results.id")),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_documents_workspace_id", "documents", ["workspace_id"])
    op.create_table(
        "briefing_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("snapshot_id", sa.String(length=36), sa.ForeignKey("portfolio_snapshots.id"), nullable=False),
        sa.Column("var_result_id", sa.String(length=36), sa.ForeignKey("var_results.id"), nullable=False),
        sa.Column("generated_by", sa.String(length=36), sa.ForeignKey("users.id")),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("week_label", sa.Text(), nullable=False),
        sa.Column("output_json", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("published_by", sa.String(length=36), sa.ForeignKey("users.id")),
        sa.Column("pdf_path", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_briefing_runs_workspace_id", "briefing_runs", ["workspace_id"])


def downgrade() -> None:
    op.drop_index("ix_briefing_runs_workspace_id", table_name="briefing_runs")
    op.drop_table("briefing_runs")
    op.drop_index("ix_documents_workspace_id", table_name="documents")
    op.drop_table("documents")
    op.drop_index("ix_extraction_results_document_id", table_name="extraction_results")
    op.drop_table("extraction_results")
    op.drop_index("ix_risk_flags_workspace_id", table_name="risk_flags")
    op.drop_index("ix_risk_flags_snapshot_id", table_name="risk_flags")
    op.drop_table("risk_flags")
    op.drop_index("ix_risk_scores_async_job_id", table_name="risk_scores")
    op.drop_index("ix_risk_scores_workspace_id", table_name="risk_scores")
    op.drop_index("ix_risk_scores_snapshot_id", table_name="risk_scores")
    op.drop_table("risk_scores")
    op.drop_index("ix_var_results_workspace_id", table_name="var_results")
    op.drop_index("ix_var_results_snapshot_id", table_name="var_results")
    op.drop_table("var_results")
    op.drop_index("ix_macro_cache_workspace_id", table_name="macro_cache")
    op.drop_table("macro_cache")
    op.drop_table("fx_cache")
    op.drop_table("price_cache")
