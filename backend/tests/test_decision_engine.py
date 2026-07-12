"""Deterministic Decision Engine tests."""

from datetime import UTC, datetime

from backend.app.core.decision_config import DecisionConfig
from backend.app.domain.content import Content
from backend.app.domain.decision_enums import DecisionType
from backend.app.domain.trend_signal import TrendSignal
from backend.app.services.decision_engine import DecisionEngine


def test_decision_engine_applies_configured_weighted_score() -> None:
    decision = DecisionEngine().evaluate(_content(), _signals(), DecisionConfig())

    assert decision.score == 65.5
    assert decision.decision_type is DecisionType.REVIEW


def test_decision_engine_retains_evidence_and_explanations() -> None:
    decision = DecisionEngine().evaluate(_content(), _signals())

    assert len(decision.evidence) == 7
    assert len(decision.explanations) == 7
    assert {evidence.factor for evidence in decision.evidence} == {
        "Trend Momentum",
        "Audience Demand",
        "Revenue Potential",
        "Competition",
        "Evergreen",
        "Platform Fit",
        "Confidence",
    }
    competition = next(
        evidence for evidence in decision.evidence if evidence.factor == "Competition"
    )
    assert competition.normalized_value == 0.8
    assert competition.contribution == 8.0


def _content() -> Content:
    return Content(
        id="decision-test",
        platform="test",
        creator_name="Test Creator",
        creator_id="creator-1",
        title="Test Content",
        description=None,
        url="https://example.com/test",
        language="en",
        country="US",
        published_at=datetime(2026, 1, 1, tzinfo=UTC),
        duration_seconds=None,
        content_type="video",
        metadata={
            "decision_factors": {
                "audience_demand": 0.5,
                "revenue_potential": 0.4,
                "competition": 0.2,
                "evergreen": 0.7,
                "platform_fit": 0.6,
            },
            "decision_confidence": {
                "audience_demand": 0.9,
                "revenue_potential": 0.9,
                "competition": 0.9,
                "evergreen": 0.9,
                "platform_fit": 0.9,
            },
        },
    )


def _signals() -> tuple[TrendSignal, ...]:
    return (
        TrendSignal(
            source="test_signal",
            score=0.8,
            confidence=0.9,
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            reason="Test signal.",
        ),
    )
