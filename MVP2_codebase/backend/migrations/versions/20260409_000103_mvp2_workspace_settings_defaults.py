"""mvp2 workspace settings defaults

Revision ID: 20260409_000103
Revises: 20260408_000102
Create Date: 2026-04-09 08:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260409_000103"
down_revision = "20260408_000102"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workspace_settings",
        sa.Column("liquidity_buffer_default", sa.Numeric(18, 2), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("workspace_settings", "liquidity_buffer_default")
