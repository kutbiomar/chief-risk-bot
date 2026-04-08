"""add onboarding_progress table

Revision ID: 20260408_000003
Revises: 20260408_000002
Create Date: 2026-04-08
"""

from alembic import op
import sqlalchemy as sa

revision = "20260408_000003"
down_revision = "20260408_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "onboarding_progress",
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), primary_key=True),
        sa.Column("current_step", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_steps_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("total_steps", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("last_step_completed_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("onboarding_progress")
