"""workspace reporting currency default chf

Revision ID: 20260413_000010
Revises: 20260410_000009
Create Date: 2026-04-13 16:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260413_000010"
down_revision = "20260410_000009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workspace_settings",
        sa.Column("reporting_currency", sa.Text(), nullable=False, server_default="CHF"),
    )


def downgrade() -> None:
    op.drop_column("workspace_settings", "reporting_currency")
