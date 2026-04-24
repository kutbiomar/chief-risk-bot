"""extraction artifacts for mvp2 e8

Revision ID: 20260409_000005
Revises: 20260409_000004
Create Date: 2026-04-09 18:45:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260409_000005"
down_revision = "20260409_000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "extraction_artifacts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("extraction_result_id", sa.String(length=36), sa.ForeignKey("extraction_results.id"), nullable=False),
        sa.Column("artifact_type", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_extraction_artifacts_extraction_result_id", "extraction_artifacts", ["extraction_result_id"])
    op.create_index("ix_extraction_artifacts_artifact_type", "extraction_artifacts", ["artifact_type"])


def downgrade() -> None:
    op.drop_index("ix_extraction_artifacts_artifact_type", table_name="extraction_artifacts")
    op.drop_index("ix_extraction_artifacts_extraction_result_id", table_name="extraction_artifacts")
    op.drop_table("extraction_artifacts")
