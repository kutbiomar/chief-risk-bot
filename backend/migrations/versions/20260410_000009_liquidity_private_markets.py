"""liquidity private markets foundation

Revision ID: 20260410_000009
Revises: 20260409_000008
Create Date: 2026-04-10 10:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260410_000009"
down_revision = "20260409_000008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "funds",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("manager_name", sa.Text(), nullable=False),
        sa.Column("vintage_year", sa.Integer()),
        sa.Column("currency", sa.Text(), nullable=False, server_default="USD"),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
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
        sa.Column("commitment_currency", sa.Text(), nullable=False, server_default="USD"),
        sa.Column("committed_amount_base", sa.Numeric(18, 2)),
        sa.Column("called_capital", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("called_capital_base", sa.Numeric(18, 2)),
        sa.Column("uncalled_capital", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("uncalled_capital_base", sa.Numeric(18, 2)),
        sa.Column("distributions_received", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("distributions_received_base", sa.Numeric(18, 2)),
        sa.Column("nav", sa.Numeric(18, 2)),
        sa.Column("nav_base", sa.Numeric(18, 2)),
        sa.Column("nav_date", sa.Date()),
        sa.Column("nav_is_estimated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("remaining_fund_life_months", sa.Integer()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_commitments_workspace_id", "commitments", ["workspace_id"])
    op.create_index("ix_commitments_fund_id", "commitments", ["fund_id"])

    op.create_table(
        "capital_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("fund_id", sa.String(length=36), sa.ForeignKey("funds.id"), nullable=False),
        sa.Column("commitment_id", sa.String(length=36), sa.ForeignKey("commitments.id")),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False, server_default="USD"),
        sa.Column("amount_base", sa.Numeric(18, 2)),
        sa.Column("notice_date", sa.Date()),
        sa.Column("due_date", sa.Date()),
        sa.Column("effective_date", sa.Date()),
        sa.Column("notes", sa.Text()),
        sa.Column("is_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("recall_period_days", sa.Integer()),
        sa.Column("recall_expires_at", sa.DateTime(timezone=True)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_capital_events_workspace_id", "capital_events", ["workspace_id"])
    op.create_index("ix_capital_events_fund_id", "capital_events", ["fund_id"])
    op.create_index("ix_capital_events_commitment_id", "capital_events", ["commitment_id"])
    op.create_index("ix_capital_events_type", "capital_events", ["type"])
    op.create_index("ix_capital_events_due_date", "capital_events", ["due_date"])
    op.create_index("ix_capital_events_effective_date", "capital_events", ["effective_date"])


def downgrade() -> None:
    op.drop_index("ix_capital_events_effective_date", table_name="capital_events")
    op.drop_index("ix_capital_events_due_date", table_name="capital_events")
    op.drop_index("ix_capital_events_type", table_name="capital_events")
    op.drop_index("ix_capital_events_commitment_id", table_name="capital_events")
    op.drop_index("ix_capital_events_fund_id", table_name="capital_events")
    op.drop_index("ix_capital_events_workspace_id", table_name="capital_events")
    op.drop_table("capital_events")

    op.drop_index("ix_commitments_fund_id", table_name="commitments")
    op.drop_index("ix_commitments_workspace_id", table_name="commitments")
    op.drop_table("commitments")

    op.drop_index("ix_funds_manager_name", table_name="funds")
    op.drop_index("ix_funds_type", table_name="funds")
    op.drop_index("ix_funds_name", table_name="funds")
    op.drop_index("ix_funds_workspace_id", table_name="funds")
    op.drop_table("funds")
