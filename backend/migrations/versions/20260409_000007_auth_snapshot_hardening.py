"""auth and snapshot hardening

Revision ID: 20260409_000007
Revises: 20260409_000006
Create Date: 2026-04-09
"""

from alembic import op
import sqlalchemy as sa


revision = "20260409_000007"
down_revision = "20260409_000006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("api_keys") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.String(length=36), nullable=True))
        batch_op.create_index("ix_api_keys_user_id", ["user_id"])

    op.execute(
        """
        UPDATE api_keys
        SET user_id = (
            SELECT users.id
            FROM users
            WHERE users.workspace_id = api_keys.workspace_id
            ORDER BY users.created_at ASC
            LIMIT 1
        )
        WHERE user_id IS NULL
        """
    )

    with op.batch_alter_table("api_keys") as batch_op:
        batch_op.alter_column("user_id", nullable=False)
        batch_op.create_foreign_key("fk_api_keys_user_id_users", "users", ["user_id"], ["id"])

    op.create_index(
        "uq_portfolio_snapshots_one_current_per_workspace",
        "portfolio_snapshots",
        ["workspace_id"],
        unique=True,
        sqlite_where=sa.text("is_current = 1"),
        postgresql_where=sa.text("is_current = true"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_portfolio_snapshots_one_current_per_workspace",
        table_name="portfolio_snapshots",
    )

    with op.batch_alter_table("api_keys") as batch_op:
        batch_op.drop_constraint("fk_api_keys_user_id_users", type_="foreignkey")
        batch_op.drop_index("ix_api_keys_user_id")
        batch_op.drop_column("user_id")
