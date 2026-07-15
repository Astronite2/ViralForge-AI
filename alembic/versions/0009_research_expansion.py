"""Track upstream artifact versions for safe regeneration.

Revision ID: 0009_research_expansion
Revises: 0008_project_script
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_research_expansion"
down_revision: str | Sequence[str] | None = "0008_project_script"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "project_production_briefs",
        sa.Column("research_version_used", sa.String(32), nullable=True),
    )
    op.add_column(
        "project_scripts",
        sa.Column("research_version_used", sa.String(32), nullable=True),
    )
    op.add_column(
        "project_scripts",
        sa.Column("production_brief_version_used", sa.String(32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("project_scripts", "production_brief_version_used")
    op.drop_column("project_scripts", "research_version_used")
    op.drop_column("project_production_briefs", "research_version_used")
