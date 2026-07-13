"""AI reasoning persistence schema.

Revision ID: 0003_ai_reasoning
Revises: 0002_knowledge_layer
Create Date: 2026-07-13 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_ai_reasoning"
down_revision: str | Sequence[str] | None = "0002_knowledge_layer"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _json_type() -> sa.types.TypeEngine[object]:
    return sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.create_table(
        "reasoning_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("reasoning_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "topic_id",
            sa.String(length=36),
            sa.ForeignKey("topics.id"),
            nullable=True,
        ),
        sa.Column(
            "decision_id",
            sa.String(length=36),
            sa.ForeignKey("decisions.id"),
            nullable=True,
        ),
        sa.Column(
            "opportunity_id",
            sa.String(length=36),
            sa.ForeignKey("opportunity_scores.id"),
            nullable=True,
        ),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("prompt_version", sa.String(length=32), nullable=False),
        sa.Column("context_version", sa.String(length=32), nullable=False),
        sa.Column("input_hash", sa.String(length=128), nullable=False),
        sa.Column(
            "force_refresh",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "retry_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.Float(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
        "ix_reasoning_runs_reasoning_type", "reasoning_runs", ["reasoning_type"]
    )
    op.create_index("ix_reasoning_runs_status", "reasoning_runs", ["status"])
    op.create_index("ix_reasoning_runs_topic_id", "reasoning_runs", ["topic_id"])
    op.create_index("ix_reasoning_runs_decision_id", "reasoning_runs", ["decision_id"])
    op.create_index(
        "ix_reasoning_runs_opportunity_id", "reasoning_runs", ["opportunity_id"]
    )
    op.create_index("ix_reasoning_runs_provider", "reasoning_runs", ["provider"])
    op.create_index("ix_reasoning_runs_model", "reasoning_runs", ["model"])
    op.create_index(
        "ix_reasoning_runs_prompt_version", "reasoning_runs", ["prompt_version"]
    )
    op.create_index(
        "ix_reasoning_runs_context_version", "reasoning_runs", ["context_version"]
    )
    op.create_index("ix_reasoning_runs_input_hash", "reasoning_runs", ["input_hash"])
    op.create_index(
        "ix_reasoning_runs_completed_at", "reasoning_runs", ["completed_at"]
    )
    op.create_index(
        "ix_reasoning_runs_correlation_id", "reasoning_runs", ["correlation_id"]
    )

    op.create_table(
        "reasoning_results",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "reasoning_run_id",
            sa.String(length=36),
            sa.ForeignKey("reasoning_runs.id"),
            nullable=False,
        ),
        sa.Column("reasoning_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "topic_id",
            sa.String(length=36),
            sa.ForeignKey("topics.id"),
            nullable=True,
        ),
        sa.Column(
            "decision_id",
            sa.String(length=36),
            sa.ForeignKey("decisions.id"),
            nullable=True,
        ),
        sa.Column(
            "opportunity_id",
            sa.String(length=36),
            sa.ForeignKey("opportunity_scores.id"),
            nullable=True,
        ),
        sa.Column("executive_summary", sa.String(length=2000), nullable=False),
        sa.Column("why_now", sa.String(length=2000), nullable=False),
        sa.Column("why_this_topic", sa.String(length=2000), nullable=False),
        sa.Column("why_this_platform", sa.String(length=2000), nullable=False),
        sa.Column("what_changed", sa.String(length=2000), nullable=False),
        sa.Column("supporting_evidence", _json_type(), nullable=False),
        sa.Column("conflicting_evidence", _json_type(), nullable=False),
        sa.Column("caveats", _json_type(), nullable=False),
        sa.Column("confidence_assessment", sa.String(length=2000), nullable=False),
        sa.Column("recommended_execution", _json_type(), nullable=False),
        sa.Column("alternative_topics", _json_type(), nullable=False),
        sa.Column("source_references", _json_type(), nullable=False),
        sa.Column("model_provider", sa.String(length=32), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("prompt_version", sa.String(length=32), nullable=False),
        sa.Column("context_version", sa.String(length=32), nullable=False),
        sa.Column("input_hash", sa.String(length=128), nullable=False),
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
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("correlation_id", sa.String(length=36), nullable=False),
        sa.Column("raw_output", _json_type(), nullable=False),
        sa.UniqueConstraint("reasoning_run_id", name="uq_reasoning_results_run_id"),
    )
    op.create_index(
        "ix_reasoning_results_reasoning_run_id",
        "reasoning_results",
        ["reasoning_run_id"],
    )
    op.create_index(
        "ix_reasoning_results_reasoning_type", "reasoning_results", ["reasoning_type"]
    )
    op.create_index("ix_reasoning_results_status", "reasoning_results", ["status"])
    op.create_index("ix_reasoning_results_topic_id", "reasoning_results", ["topic_id"])
    op.create_index(
        "ix_reasoning_results_decision_id", "reasoning_results", ["decision_id"]
    )
    op.create_index(
        "ix_reasoning_results_opportunity_id",
        "reasoning_results",
        ["opportunity_id"],
    )
    op.create_index(
        "ix_reasoning_results_model_provider",
        "reasoning_results",
        ["model_provider"],
    )
    op.create_index(
        "ix_reasoning_results_model_name", "reasoning_results", ["model_name"]
    )
    op.create_index(
        "ix_reasoning_results_prompt_version",
        "reasoning_results",
        ["prompt_version"],
    )
    op.create_index(
        "ix_reasoning_results_context_version",
        "reasoning_results",
        ["context_version"],
    )
    op.create_index(
        "ix_reasoning_results_input_hash", "reasoning_results", ["input_hash"]
    )
    op.create_index(
        "ix_reasoning_results_completed_at", "reasoning_results", ["completed_at"]
    )
    op.create_index(
        "ix_reasoning_results_correlation_id",
        "reasoning_results",
        ["correlation_id"],
    )

    op.create_table(
        "reasoning_source_links",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "reasoning_result_id",
            sa.String(length=36),
            sa.ForeignKey("reasoning_results.id"),
            nullable=False,
        ),
        sa.Column("link_type", sa.String(length=64), nullable=False),
        sa.Column(
            "evidence_id",
            sa.String(length=36),
            sa.ForeignKey("evidence.id"),
            nullable=True,
        ),
        sa.Column(
            "topic_id",
            sa.String(length=36),
            sa.ForeignKey("topics.id"),
            nullable=True,
        ),
        sa.Column(
            "decision_id",
            sa.String(length=36),
            sa.ForeignKey("decisions.id"),
            nullable=True,
        ),
        sa.Column(
            "opportunity_id",
            sa.String(length=36),
            sa.ForeignKey("opportunity_scores.id"),
            nullable=True,
        ),
        sa.Column("claim", sa.String(length=2000), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
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
        "ix_reasoning_source_links_reasoning_result_id",
        "reasoning_source_links",
        ["reasoning_result_id"],
    )
    op.create_index(
        "ix_reasoning_source_links_link_type",
        "reasoning_source_links",
        ["link_type"],
    )
    op.create_index(
        "ix_reasoning_source_links_evidence_id",
        "reasoning_source_links",
        ["evidence_id"],
    )
    op.create_index(
        "ix_reasoning_source_links_topic_id", "reasoning_source_links", ["topic_id"]
    )
    op.create_index(
        "ix_reasoning_source_links_decision_id",
        "reasoning_source_links",
        ["decision_id"],
    )
    op.create_index(
        "ix_reasoning_source_links_opportunity_id",
        "reasoning_source_links",
        ["opportunity_id"],
    )
    op.create_index(
        "ix_reasoning_source_links_correlation_id",
        "reasoning_source_links",
        ["correlation_id"],
    )

    op.create_table(
        "reasoning_validation_errors",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "reasoning_run_id",
            sa.String(length=36),
            sa.ForeignKey("reasoning_runs.id"),
            nullable=False,
        ),
        sa.Column("field", sa.String(length=128), nullable=False),
        sa.Column("message", sa.String(length=2000), nullable=False),
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
        "ix_reasoning_validation_errors_reasoning_run_id",
        "reasoning_validation_errors",
        ["reasoning_run_id"],
    )
    op.create_index(
        "ix_reasoning_validation_errors_field",
        "reasoning_validation_errors",
        ["field"],
    )
    op.create_index(
        "ix_reasoning_validation_errors_correlation_id",
        "reasoning_validation_errors",
        ["correlation_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_reasoning_validation_errors_correlation_id",
        table_name="reasoning_validation_errors",
    )
    op.drop_index(
        "ix_reasoning_validation_errors_field",
        table_name="reasoning_validation_errors",
    )
    op.drop_index(
        "ix_reasoning_validation_errors_reasoning_run_id",
        table_name="reasoning_validation_errors",
    )
    op.drop_table("reasoning_validation_errors")

    op.drop_index(
        "ix_reasoning_source_links_correlation_id",
        table_name="reasoning_source_links",
    )
    op.drop_index(
        "ix_reasoning_source_links_opportunity_id",
        table_name="reasoning_source_links",
    )
    op.drop_index(
        "ix_reasoning_source_links_decision_id",
        table_name="reasoning_source_links",
    )
    op.drop_index(
        "ix_reasoning_source_links_topic_id",
        table_name="reasoning_source_links",
    )
    op.drop_index(
        "ix_reasoning_source_links_evidence_id",
        table_name="reasoning_source_links",
    )
    op.drop_index(
        "ix_reasoning_source_links_link_type",
        table_name="reasoning_source_links",
    )
    op.drop_index(
        "ix_reasoning_source_links_reasoning_result_id",
        table_name="reasoning_source_links",
    )
    op.drop_table("reasoning_source_links")

    op.drop_index("ix_reasoning_results_correlation_id", table_name="reasoning_results")
    op.drop_index("ix_reasoning_results_completed_at", table_name="reasoning_results")
    op.drop_index("ix_reasoning_results_input_hash", table_name="reasoning_results")
    op.drop_index(
        "ix_reasoning_results_context_version", table_name="reasoning_results"
    )
    op.drop_index("ix_reasoning_results_prompt_version", table_name="reasoning_results")
    op.drop_index("ix_reasoning_results_model_name", table_name="reasoning_results")
    op.drop_index("ix_reasoning_results_model_provider", table_name="reasoning_results")
    op.drop_index("ix_reasoning_results_opportunity_id", table_name="reasoning_results")
    op.drop_index("ix_reasoning_results_decision_id", table_name="reasoning_results")
    op.drop_index("ix_reasoning_results_topic_id", table_name="reasoning_results")
    op.drop_index("ix_reasoning_results_status", table_name="reasoning_results")
    op.drop_index("ix_reasoning_results_reasoning_type", table_name="reasoning_results")
    op.drop_index(
        "ix_reasoning_results_reasoning_run_id", table_name="reasoning_results"
    )
    op.drop_table("reasoning_results")

    op.drop_index("ix_reasoning_runs_correlation_id", table_name="reasoning_runs")
    op.drop_index("ix_reasoning_runs_completed_at", table_name="reasoning_runs")
    op.drop_index("ix_reasoning_runs_input_hash", table_name="reasoning_runs")
    op.drop_index("ix_reasoning_runs_context_version", table_name="reasoning_runs")
    op.drop_index("ix_reasoning_runs_prompt_version", table_name="reasoning_runs")
    op.drop_index("ix_reasoning_runs_model", table_name="reasoning_runs")
    op.drop_index("ix_reasoning_runs_provider", table_name="reasoning_runs")
    op.drop_index("ix_reasoning_runs_opportunity_id", table_name="reasoning_runs")
    op.drop_index("ix_reasoning_runs_decision_id", table_name="reasoning_runs")
    op.drop_index("ix_reasoning_runs_topic_id", table_name="reasoning_runs")
    op.drop_index("ix_reasoning_runs_status", table_name="reasoning_runs")
    op.drop_index("ix_reasoning_runs_reasoning_type", table_name="reasoning_runs")
    op.drop_table("reasoning_runs")
