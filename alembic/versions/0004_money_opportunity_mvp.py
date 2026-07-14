"""Money opportunity MVP persistence.

Revision ID: 0004_money_opportunity_mvp
Revises: 0003_ai_reasoning
Create Date: 2026-07-14 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_money_opportunity_mvp"
down_revision: str | Sequence[str] | None = "0003_ai_reasoning"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column[object]]:
    return [
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
    ]


def upgrade() -> None:
    op.create_table(
        "money_opportunity_analyses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("query", sa.String(200), nullable=False),
        sa.Column("region", sa.String(8), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("request_payload", sa.JSON(), nullable=False),
        sa.Column("channel_profile", sa.JSON(), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_money_analysis_query", "money_opportunity_analyses", ["query"])
    op.create_index(
        "ix_money_analysis_status", "money_opportunity_analyses", ["status"]
    )

    op.create_table(
        "money_opportunity_recommendations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "analysis_id",
            sa.String(36),
            sa.ForeignKey("money_opportunity_analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("topic", sa.String(300), nullable=False),
        sa.Column("money_score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        *_timestamps(),
    )
    op.create_index(
        "ix_money_recommendation_analysis",
        "money_opportunity_recommendations",
        ["analysis_id"],
    )
    op.create_index(
        "ix_money_recommendation_topic", "money_opportunity_recommendations", ["topic"]
    )
    op.create_index(
        "ix_money_recommendation_score",
        "money_opportunity_recommendations",
        ["money_score"],
    )

    op.create_table(
        "money_production_briefs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "opportunity_id",
            sa.String(36),
            sa.ForeignKey("money_opportunity_recommendations.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("payload", sa.JSON(), nullable=False),
        *_timestamps(),
    )
    op.create_index(
        "ix_money_brief_opportunity",
        "money_production_briefs",
        ["opportunity_id"],
        unique=True,
    )

    op.create_table(
        "money_opportunity_outcomes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "recommendation_id",
            sa.String(36),
            sa.ForeignKey("money_opportunity_recommendations.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("selected_topic", sa.String(300), nullable=False),
        sa.Column("money_score_at_selection", sa.Float(), nullable=False),
        sa.Column("publish_status", sa.String(32), nullable=False),
        sa.Column("youtube_video_id", sa.String(64), nullable=True),
        sa.Column("publication_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("production_hours", sa.Float(), nullable=True),
        sa.Column("cost", sa.Float(), nullable=True),
        sa.Column("views_after_24_hours", sa.Integer(), nullable=True),
        sa.Column("views_after_7_days", sa.Integer(), nullable=True),
        sa.Column("views_after_30_days", sa.Integer(), nullable=True),
        sa.Column("watch_time_hours", sa.Float(), nullable=True),
        sa.Column("ctr", sa.Float(), nullable=True),
        sa.Column("subscribers_gained", sa.Integer(), nullable=True),
        sa.Column("rpm", sa.Float(), nullable=True),
        sa.Column("revenue", sa.Float(), nullable=True),
        sa.Column("user_notes", sa.String(4000), nullable=True),
        sa.Column("result_classification", sa.String(32), nullable=False),
        *_timestamps(),
    )
    op.create_index(
        "ix_money_outcome_recommendation",
        "money_opportunity_outcomes",
        ["recommendation_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("money_opportunity_outcomes")
    op.drop_table("money_production_briefs")
    op.drop_table("money_opportunity_recommendations")
    op.drop_table("money_opportunity_analyses")
