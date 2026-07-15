"""Add Executive Producer briefs.

Revision ID: 0007_production_brief
Revises: 0006_research_dossier
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_production_brief"
down_revision: str | Sequence[str] | None = "0006_research_dossier"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_production_briefs",
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
        sa.Column("candidate_angles_generated", sa.Integer(), nullable=False),
        sa.Column("selected_angle", sa.String(500), nullable=True),
        sa.Column("recommendation", sa.String(40), nullable=True),
        sa.Column("revised_money_score", sa.Float(), nullable=True),
        sa.Column("revised_confidence", sa.Float(), nullable=True),
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
        "ix_production_brief_project",
        "project_production_briefs",
        ["project_id"],
        unique=True,
    )
    op.create_index(
        "ix_production_brief_status", "project_production_briefs", ["status"]
    )


def downgrade() -> None:
    op.drop_table("project_production_briefs")
