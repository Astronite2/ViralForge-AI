"""Add project research dossiers.

Revision ID: 0006_research_dossier
Revises: 0005_project_workspace
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_research_dossier"
down_revision: str | Sequence[str] | None = "0005_project_workspace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_research_dossiers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("research_status", sa.String(32), nullable=False),
        sa.Column("research_version", sa.String(32), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("current_step", sa.String(40), nullable=False),
        sa.Column("sources_found", sa.Integer(), nullable=False),
        sa.Column("facts_verified", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.String(1000), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
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
        "ix_research_project_id",
        "project_research_dossiers",
        ["project_id"],
        unique=True,
    )
    op.create_index(
        "ix_research_status", "project_research_dossiers", ["research_status"]
    )


def downgrade() -> None:
    op.drop_table("project_research_dossiers")
