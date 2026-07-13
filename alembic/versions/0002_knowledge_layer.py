"""Knowledge layer schema.

Revision ID: 0002_knowledge_layer
Revises: 0001_intelligence_flow
Create Date: 2026-07-13 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_knowledge_layer"
down_revision: str | Sequence[str] | None = "0001_intelligence_flow"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "historical_observations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "topic_id",
            sa.String(length=36),
            sa.ForeignKey("topics.id"),
            nullable=False,
        ),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("connector_name", sa.String(length=100), nullable=False),
        sa.Column("observation_type", sa.String(length=100), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.String(length=36), nullable=False),
        sa.Column("observation_hash", sa.String(length=128), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("change_type", sa.String(length=50), nullable=False),
        sa.Column(
            "signal_id",
            sa.String(length=36),
            sa.ForeignKey("trend_signals.id"),
            nullable=True,
        ),
        sa.Column(
            "content_id",
            sa.String(length=255),
            sa.ForeignKey("content.id"),
            nullable=True,
        ),
        sa.Column(
            "previous_observation_id",
            sa.String(length=36),
            sa.ForeignKey("historical_observations.id"),
            nullable=True,
        ),
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
        sa.UniqueConstraint("observation_hash", name="uq_historical_observations_hash"),
    )
    op.create_index(
        "ix_historical_observations_topic_id",
        "historical_observations",
        ["topic_id"],
    )
    op.create_index(
        "ix_historical_observations_source",
        "historical_observations",
        ["source"],
    )
    op.create_index(
        "ix_historical_observations_connector_name",
        "historical_observations",
        ["connector_name"],
    )
    op.create_index(
        "ix_historical_observations_observed_at",
        "historical_observations",
        ["observed_at"],
    )
    op.create_index(
        "ix_historical_observations_correlation_id",
        "historical_observations",
        ["correlation_id"],
    )
    op.create_index(
        "ix_historical_observations_signal_id",
        "historical_observations",
        ["signal_id"],
    )
    op.create_index(
        "ix_historical_observations_content_id",
        "historical_observations",
        ["content_id"],
    )
    op.create_index(
        "ix_historical_observations_observation_hash",
        "historical_observations",
        ["observation_hash"],
    )

    op.create_table(
        "historical_evidence",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "topic_id",
            sa.String(length=36),
            sa.ForeignKey("topics.id"),
            nullable=False,
        ),
        sa.Column(
            "observation_id",
            sa.String(length=36),
            sa.ForeignKey("historical_observations.id"),
            nullable=False,
        ),
        sa.Column(
            "evidence_id",
            sa.String(length=36),
            sa.ForeignKey("evidence.id"),
            nullable=False,
        ),
        sa.Column(
            "signal_id",
            sa.String(length=36),
            sa.ForeignKey("trend_signals.id"),
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
        sa.UniqueConstraint("evidence_id", name="uq_historical_evidence_evidence_id"),
    )
    op.create_index(
        "ix_historical_evidence_topic_id",
        "historical_evidence",
        ["topic_id"],
    )
    op.create_index(
        "ix_historical_evidence_observation_id",
        "historical_evidence",
        ["observation_id"],
    )
    op.create_index(
        "ix_historical_evidence_evidence_id",
        "historical_evidence",
        ["evidence_id"],
    )
    op.create_index(
        "ix_historical_evidence_signal_id",
        "historical_evidence",
        ["signal_id"],
    )
    op.create_index(
        "ix_historical_evidence_correlation_id",
        "historical_evidence",
        ["correlation_id"],
    )

    op.create_table(
        "topic_relationships",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "source_topic_id",
            sa.String(length=36),
            sa.ForeignKey("topics.id"),
            nullable=False,
        ),
        sa.Column(
            "target_topic_id",
            sa.String(length=36),
            sa.ForeignKey("topics.id"),
            nullable=False,
        ),
        sa.Column("relationship_type", sa.String(length=32), nullable=False),
        sa.Column("strength", sa.Float(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
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
        sa.UniqueConstraint(
            "source_topic_id",
            "target_topic_id",
            "relationship_type",
            name="uq_topic_relationships_edge",
        ),
    )
    op.create_index(
        "ix_topic_relationships_source_topic_id",
        "topic_relationships",
        ["source_topic_id"],
    )
    op.create_index(
        "ix_topic_relationships_target_topic_id",
        "topic_relationships",
        ["target_topic_id"],
    )
    op.create_index(
        "ix_topic_relationships_relationship_type",
        "topic_relationships",
        ["relationship_type"],
    )
    op.create_index(
        "ix_topic_relationships_correlation_id",
        "topic_relationships",
        ["correlation_id"],
    )

    op.create_table(
        "opportunity_scores",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "topic_id",
            sa.String(length=36),
            sa.ForeignKey("topics.id"),
            nullable=False,
        ),
        sa.Column(
            "observation_id",
            sa.String(length=36),
            sa.ForeignKey("historical_observations.id"),
            nullable=True,
        ),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("dimensions", sa.JSON(), nullable=False),
        sa.Column("explanations", sa.JSON(), nullable=False),
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
    op.create_index(
        "ix_opportunity_scores_topic_id", "opportunity_scores", ["topic_id"]
    )
    op.create_index(
        "ix_opportunity_scores_observation_id",
        "opportunity_scores",
        ["observation_id"],
    )
    op.create_index("ix_opportunity_scores_score", "opportunity_scores", ["score"])
    op.create_index(
        "ix_opportunity_scores_correlation_id",
        "opportunity_scores",
        ["correlation_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_opportunity_scores_correlation_id", table_name="opportunity_scores"
    )
    op.drop_index("ix_opportunity_scores_score", table_name="opportunity_scores")
    op.drop_index(
        "ix_opportunity_scores_observation_id", table_name="opportunity_scores"
    )
    op.drop_index("ix_opportunity_scores_topic_id", table_name="opportunity_scores")
    op.drop_table("opportunity_scores")

    op.drop_index(
        "ix_topic_relationships_correlation_id", table_name="topic_relationships"
    )
    op.drop_index(
        "ix_topic_relationships_relationship_type", table_name="topic_relationships"
    )
    op.drop_index(
        "ix_topic_relationships_target_topic_id", table_name="topic_relationships"
    )
    op.drop_index(
        "ix_topic_relationships_source_topic_id", table_name="topic_relationships"
    )
    op.drop_table("topic_relationships")

    op.drop_index(
        "ix_historical_evidence_correlation_id", table_name="historical_evidence"
    )
    op.drop_index("ix_historical_evidence_signal_id", table_name="historical_evidence")
    op.drop_index(
        "ix_historical_evidence_evidence_id", table_name="historical_evidence"
    )
    op.drop_index(
        "ix_historical_evidence_observation_id", table_name="historical_evidence"
    )
    op.drop_index("ix_historical_evidence_topic_id", table_name="historical_evidence")
    op.drop_table("historical_evidence")

    op.drop_index(
        "ix_historical_observations_observation_hash",
        table_name="historical_observations",
    )
    op.drop_index(
        "ix_historical_observations_content_id", table_name="historical_observations"
    )
    op.drop_index(
        "ix_historical_observations_signal_id", table_name="historical_observations"
    )
    op.drop_index(
        "ix_historical_observations_correlation_id",
        table_name="historical_observations",
    )
    op.drop_index(
        "ix_historical_observations_observed_at", table_name="historical_observations"
    )
    op.drop_index(
        "ix_historical_observations_connector_name",
        table_name="historical_observations",
    )
    op.drop_index(
        "ix_historical_observations_source", table_name="historical_observations"
    )
    op.drop_index(
        "ix_historical_observations_topic_id", table_name="historical_observations"
    )
    op.drop_table("historical_observations")
