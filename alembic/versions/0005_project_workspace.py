"""Add production projects.

Revision ID: 0005_project_workspace
Revises: 0004_money_opportunity_mvp
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_project_workspace"
down_revision: str | Sequence[str] | None = "0004_money_opportunity_mvp"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("country", sa.String(100), nullable=False),
        sa.Column("language", sa.String(100), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("target_length", sa.String(50), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
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
    op.create_index("ix_projects_title", "projects", ["title"])
    op.create_index("ix_projects_status", "projects", ["status"])


def downgrade() -> None:
    op.drop_table("projects")
