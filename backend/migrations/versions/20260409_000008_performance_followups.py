"""performance and integrity followups

Revision ID: 20260409_000008
Revises: 20260409_000007
Create Date: 2026-04-09
"""

from alembic import op


revision = "20260409_000008"
down_revision = "20260409_000007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("audit_events") as batch_op:
        batch_op.create_unique_constraint(
            "uq_audit_events_workspace_sequence",
            ["workspace_id", "sequence_no"],
        )
    op.create_index(
        "ix_asset_factor_exposures_snapshot_factor",
        "asset_factor_exposures",
        ["snapshot_id", "factor_key"],
    )
    op.create_index(
        "ix_risk_regimes_workspace_as_of_date",
        "risk_regimes",
        ["workspace_id", "as_of_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_risk_regimes_workspace_as_of_date", table_name="risk_regimes")
    op.drop_index("ix_asset_factor_exposures_snapshot_factor", table_name="asset_factor_exposures")
    with op.batch_alter_table("audit_events") as batch_op:
        batch_op.drop_constraint("uq_audit_events_workspace_sequence", type_="unique")
