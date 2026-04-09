"""position factor tag metadata

Revision ID: 20260409_000006
Revises: 20260409_000005
Create Date: 2026-04-09 17:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260409_000006"
down_revision = "20260409_000005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("positions", sa.Column("factor_country", sa.Text(), nullable=True))
    op.add_column("positions", sa.Column("factor_tag_source", sa.Text(), nullable=True))
    op.add_column("positions", sa.Column("factor_tag_confidence", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("positions", "factor_tag_confidence")
    op.drop_column("positions", "factor_tag_source")
    op.drop_column("positions", "factor_country")
