"""Add source-grounded project scripts.

Revision ID: 0008_project_script
Revises: 0007_production_brief
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_project_script"
down_revision: str | Sequence[str] | None = "0007_production_brief"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_scripts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("current_step", sa.String(40), nullable=False),
        sa.Column("target_word_count", sa.Integer(), nullable=False),
        sa.Column("actual_word_count", sa.Integer(), nullable=False),
        sa.Column("estimated_duration_minutes", sa.Float(), nullable=True),
        sa.Column("evidence_sufficiency", sa.String(20), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("safe_error_message", sa.String(1000), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_project_script_project", "project_scripts", ["project_id"], unique=True
    )
    op.create_index("ix_project_script_status", "project_scripts", ["status"])


def downgrade() -> None:
    op.drop_table("project_scripts")
