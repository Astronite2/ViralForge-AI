"""Base schema for the ViralForge AI backend.

Revision ID: 0001_intelligence_flow
Revises:
Create Date: 2026-07-12 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_intelligence_flow"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
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
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "platforms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
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
        sa.UniqueConstraint("name", name="uq_platforms_name"),
    )
    op.create_index("ix_platforms_name", "platforms", ["name"])

    op.create_table(
        "channels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "platform_id",
            sa.Integer(),
            sa.ForeignKey("platforms.id"),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
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
    op.create_index("ix_channels_platform_id", "channels", ["platform_id"])
    op.create_index("ix_channels_external_id", "channels", ["external_id"])

    op.create_table(
        "videos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "channel_id",
            sa.Integer(),
            sa.ForeignKey("channels.id"),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
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
    op.create_index("ix_videos_channel_id", "videos", ["channel_id"])
    op.create_index("ix_videos_external_id", "videos", ["external_id"])

    op.create_table(
        "metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("video_id", sa.Integer(), sa.ForeignKey("videos.id"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
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
    op.create_index("ix_metrics_video_id", "metrics", ["video_id"])
    op.create_index("ix_metrics_name", "metrics", ["name"])

    op.create_table(
        "analyses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("video_id", sa.Integer(), sa.ForeignKey("videos.id"), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
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
    op.create_index("ix_analyses_video_id", "analyses", ["video_id"])
    op.create_index("ix_analyses_status", "analyses", ["status"])

    op.create_table(
        "content",
        sa.Column("id", sa.String(length=255), primary_key=True),
        sa.Column("platform", sa.String(length=100), nullable=False),
        sa.Column("creator_name", sa.String(length=255), nullable=False),
        sa.Column("creator_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("language", sa.String(length=32), nullable=True),
        sa.Column("country", sa.String(length=8), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("analysis", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
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
    op.create_index("ix_content_platform", "content", ["platform"])
    op.create_index("ix_content_creator_id", "content", ["creator_id"])
    op.create_index("ix_content_published_at", "content", ["published_at"])
    op.create_index("ix_content_content_type", "content", ["content_type"])

    op.create_table(
        "topics",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("normalized_key", sa.String(length=255), nullable=False),
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
        sa.UniqueConstraint("normalized_key", name="uq_topics_normalized_key"),
    )
    op.create_index("ix_topics_normalized_key", "topics", ["normalized_key"])

    op.create_table(
        "trend_signals",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("topic_id", sa.String(length=36), sa.ForeignKey("topics.id")),
        sa.Column("content_id", sa.String(length=255), sa.ForeignKey("content.id")),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("correlation_id", sa.String(length=36), nullable=False),
        sa.Column("raw_metadata", sa.JSON(), nullable=False),
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
    op.create_index("ix_trend_signals_topic_id", "trend_signals", ["topic_id"])
    op.create_index("ix_trend_signals_timestamp", "trend_signals", ["timestamp"])
    op.create_index(
        "ix_trend_signals_correlation_id", "trend_signals", ["correlation_id"]
    )
    op.create_index("ix_trend_signals_content_id", "trend_signals", ["content_id"])

    op.create_table(
        "decisions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "topic_id", sa.String(length=36), sa.ForeignKey("topics.id"), nullable=False
        ),
        sa.Column("topic_name", sa.String(length=255), nullable=False),
        sa.Column("decision_type", sa.String(length=32), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("recommended_action", sa.String(length=255), nullable=False),
        sa.Column("engine_version", sa.String(length=32), nullable=False),
        sa.Column("event_version", sa.String(length=32), nullable=False),
        sa.Column("correlation_id", sa.String(length=36), nullable=False),
        sa.Column("weights_snapshot", sa.JSON(), nullable=False),
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
    op.create_index("ix_decisions_topic_id", "decisions", ["topic_id"])
    op.create_index("ix_decisions_created_at", "decisions", ["created_at"])
    op.create_index("ix_decisions_correlation_id", "decisions", ["correlation_id"])

    op.create_table(
        "decision_explanations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "decision_id",
            sa.String(length=36),
            sa.ForeignKey("decisions.id"),
            nullable=False,
        ),
        sa.Column("factor", sa.String(length=100), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("contribution", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
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
        "ix_decision_explanations_decision_id",
        "decision_explanations",
        ["decision_id"],
    )

    op.create_table(
        "evidence",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "signal_id",
            sa.String(length=36),
            sa.ForeignKey("trend_signals.id"),
            nullable=False,
        ),
        sa.Column(
            "decision_id",
            sa.String(length=36),
            sa.ForeignKey("decisions.id"),
            nullable=False,
        ),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("factor", sa.String(length=100), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("raw_value", sa.Float(), nullable=False),
        sa.Column("normalized_value", sa.Float(), nullable=False),
        sa.Column("contribution", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.String(length=36), nullable=False),
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
    op.create_index("ix_evidence_signal_id", "evidence", ["signal_id"])
    op.create_index("ix_evidence_decision_id", "evidence", ["decision_id"])
    op.create_index("ix_evidence_correlation_id", "evidence", ["correlation_id"])

    op.create_table(
        "processed_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.String(length=36), nullable=False),
        sa.Column("decision_id", sa.String(length=36), nullable=True),
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
        sa.UniqueConstraint("event_id", name="uq_processed_events_event_id"),
        sa.ForeignKeyConstraint(["decision_id"], ["decisions.id"]),
    )
    op.create_index("ix_processed_events_event_id", "processed_events", ["event_id"])
    op.create_index(
        "ix_processed_events_correlation_id",
        "processed_events",
        ["correlation_id"],
    )

    op.create_table(
        "opportunities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "content_id",
            sa.String(length=255),
            sa.ForeignKey("content.id"),
            nullable=False,
        ),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("competition", sa.Float(), nullable=False),
        sa.Column("growth_rate", sa.Float(), nullable=False),
        sa.Column("recommended_action", sa.String(length=255), nullable=False),
        sa.Column("estimated_rpm", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
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
    op.create_index("ix_opportunities_content_id", "opportunities", ["content_id"])


def downgrade() -> None:
    op.drop_index("ix_opportunities_content_id", table_name="opportunities")
    op.drop_table("opportunities")

    op.drop_index("ix_processed_events_correlation_id", table_name="processed_events")
    op.drop_index("ix_processed_events_event_id", table_name="processed_events")
    op.drop_table("processed_events")

    op.drop_index("ix_evidence_correlation_id", table_name="evidence")
    op.drop_index("ix_evidence_decision_id", table_name="evidence")
    op.drop_index("ix_evidence_signal_id", table_name="evidence")
    op.drop_table("evidence")

    op.drop_index(
        "ix_decision_explanations_decision_id", table_name="decision_explanations"
    )
    op.drop_table("decision_explanations")

    op.drop_index("ix_decisions_correlation_id", table_name="decisions")
    op.drop_index("ix_decisions_created_at", table_name="decisions")
    op.drop_index("ix_decisions_topic_id", table_name="decisions")
    op.drop_table("decisions")

    op.drop_index("ix_trend_signals_content_id", table_name="trend_signals")
    op.drop_index("ix_trend_signals_correlation_id", table_name="trend_signals")
    op.drop_index("ix_trend_signals_timestamp", table_name="trend_signals")
    op.drop_index("ix_trend_signals_topic_id", table_name="trend_signals")
    op.drop_table("trend_signals")

    op.drop_index("ix_topics_normalized_key", table_name="topics")
    op.drop_table("topics")

    op.drop_index("ix_content_content_type", table_name="content")
    op.drop_index("ix_content_published_at", table_name="content")
    op.drop_index("ix_content_creator_id", table_name="content")
    op.drop_index("ix_content_platform", table_name="content")
    op.drop_table("content")

    op.drop_index("ix_analyses_status", table_name="analyses")
    op.drop_index("ix_analyses_video_id", table_name="analyses")
    op.drop_table("analyses")

    op.drop_index("ix_metrics_name", table_name="metrics")
    op.drop_index("ix_metrics_video_id", table_name="metrics")
    op.drop_table("metrics")

    op.drop_index("ix_videos_external_id", table_name="videos")
    op.drop_index("ix_videos_channel_id", table_name="videos")
    op.drop_table("videos")

    op.drop_index("ix_channels_external_id", table_name="channels")
    op.drop_index("ix_channels_platform_id", table_name="channels")
    op.drop_table("channels")

    op.drop_index("ix_platforms_name", table_name="platforms")
    op.drop_table("platforms")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
