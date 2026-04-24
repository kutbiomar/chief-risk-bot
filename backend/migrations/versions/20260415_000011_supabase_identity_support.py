"""add supabase identity support

Revision ID: 20260415_000011
Revises: 20260413_000010
Create Date: 2026-04-15 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260415_000011"
down_revision = "20260413_000010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("auth_provider", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("auth_subject", sa.Text(), nullable=True))
        batch_op.create_unique_constraint("uq_users_auth_subject", ["auth_subject"])


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("uq_users_auth_subject", type_="unique")
        batch_op.drop_column("auth_subject")
        batch_op.drop_column("auth_provider")
