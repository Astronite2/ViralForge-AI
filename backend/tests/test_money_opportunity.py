"""Deterministic money opportunity, estimator, workflow, and API tests."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import backend.app.api.v1.money_opportunities as money_api
from backend.app.domain.content import Content
from backend.app.domain.trend_signal import TrendSignal
from backend.app.main import app
from backend.app.models.money_opportunity import MoneyOutcomeModel
from backend.app.schemas.money_opportunity import (
    ChannelProfileInput,
    MoneyAnalysisRequest,
    OutcomeCreate,
    OutcomeUpdate,
)
from backend.app.services.competition_analysis import CompetitionAnalyzer
from backend.app.services.evergreen_momentum import EvergreenMomentumAnalyzer
from backend.app.services.money_opportunity import MoneyOpportunityEngine
from backend.app.services.money_workflow import (
    MoneyWorkflowService,
    MoneyWorkflowUnavailable,
)
from backend.app.services.revenue_estimator import RevenueEstimator


def _contents(count: int = 15, *, dominant: bool = False) -> list[Content]:
    now = datetime(2026, 7, 14, tzinfo=UTC)
    result = []
    for index in range(count):
        published = now - timedelta(days=(index * 35 if index % 3 else index + 1))
        views = float(10_000 + index * 8_000)
        subscribers = float(1_000_000 if dominant else 25_000 + index * 2_000)
        result.append(
            Content(
                id=f"youtube:money-{index}",
                platform="youtube",
                creator_name=f"Channel {index}",
                creator_id=f"channel-{index}",
                title=f"Ancient Egypt engineering explained part {index}",
                description=None,
                url=f"https://youtube.com/watch?v=money-{index}",
                language="en",
                country="US",
                published_at=published,
                duration_seconds=720 + index * 10,
                content_type="video",
                metrics={
                    "view_count": views,
                    "subscriber_count": subscribers,
                    "view_velocity": views / max((now - published).days * 24, 1),
                    "engagement_rate": 0.04,
                },
                signals=(
                    TrendSignal(
                        source="youtube",
                        score=0.6,
                        confidence=0.8,
                        timestamp=published,
                        reason="YouTube comparison evidence.",
                    ),
                ),
                metadata={"video_id": f"money-{index}", "query": "Ancient Egypt"},
            )
        )
    return result


def test_money_engine_is_deterministic_bounded_and_traceable() -> None:
    engine = MoneyOpportunityEngine()
    kwargs = {
        "query": "Ancient Egypt",
        "angle": "How Ancient Egypt engineering really worked",
        "contents": _contents(),
    }
    first = engine.score(**kwargs)
    second = engine.score(**kwargs)
    assert first == second
    assert 0 <= first["money_score"] <= 100
    assert sum(first["weights"].values()) == pytest.approx(1, abs=0.001)
    assert all(
        "input" in item and "contribution" in item
        for item in first["calculation_trace"]
    )
    assert len(first["evidence_references"]) == 15
    assert "not guaranteed" in first["explanation"]


def test_weight_changes_and_production_penalty_affect_score() -> None:
    feasible = MoneyOpportunityEngine(weights={"production_feasibility": 1.0}).score(
        query="Ancient Egypt",
        angle="Simple explainer",
        contents=_contents(),
        angle_index=0,
    )
    difficult = MoneyOpportunityEngine(weights={"production_feasibility": 1.0}).score(
        query="Ancient Egypt",
        angle="Evidence documentary",
        contents=_contents(),
        angle_index=2,
    )
    assert feasible["money_score"] > difficult["money_score"]


def test_missing_evidence_has_low_confidence_and_no_view_estimate() -> None:
    result = MoneyOpportunityEngine().score(
        query="Ancient Egypt", angle="Ancient Egypt explained", contents=_contents(2)
    )
    assert result["confidence"] < 50
    assert result["estimated_views"]["basis"] == "unavailable"
    assert result["estimated_revenue"]["basis"] == "unavailable"


def test_unsafe_monetization_and_channel_fit() -> None:
    engine = MoneyOpportunityEngine()
    unsafe = engine.score(
        query="graphic weapon history",
        angle="Graphic weapon evidence",
        contents=_contents(),
    )
    no_profile = engine.score(
        query="Ancient Egypt", angle="History guide", contents=_contents()
    )
    fitted = engine.score(
        query="Ancient Egypt",
        angle="History guide",
        contents=_contents(),
        profile=ChannelProfileInput(
            niche="Ancient Egypt", maximum_production_hours_per_video=20
        ),
    )
    assert unsafe["monetization_safety"] < 100
    assert no_profile["channel_fit_score"] is None
    assert fitted["channel_fit_score"] == 100


def test_evergreen_and_trending_are_distinguished() -> None:
    analyzer = EvergreenMomentumAnalyzer()
    evergreen = analyzer.analyze(
        "Ancient Egypt", _contents(), observed_at=datetime(2026, 7, 14, tzinfo=UTC)
    )
    event = analyzer.analyze(
        "breaking election update",
        _contents(),
        observed_at=datetime(2026, 7, 14, tzinfo=UTC),
    )
    assert evergreen.evergreen_score > event.evergreen_score
    assert evergreen.opportunity_type != "temporary_event"


def test_competition_small_sample_dominance_and_freshness_gap() -> None:
    analyzer = CompetitionAnalyzer()
    small = analyzer.analyze(
        "Ancient Egypt", _contents(3), observed_at=datetime(2026, 7, 14, tzinfo=UTC)
    )
    dominant = analyzer.analyze(
        "Ancient Egypt",
        _contents(15, dominant=True),
        observed_at=datetime(2026, 7, 14, tzinfo=UTC),
    )
    assert small.confidence < 50
    assert "Insufficient sample" in small.market_gap
    assert dominant.metrics["large_channel_dominance"] == 1
    assert dominant.competition_score > small.competition_score


def test_revenue_estimator_benchmark_and_observed_ranges() -> None:
    estimator = RevenueEstimator()
    benchmark = estimator.estimate(
        query="Ancient Egypt", contents=_contents(), monetization_safety=100
    )
    assert benchmark.views.basis == "observed"
    assert benchmark.rpm.basis == "benchmark"
    assert benchmark.revenue.low <= benchmark.revenue.base <= benchmark.revenue.high
    assert all(
        value >= 0
        for value in (
            benchmark.revenue.low,
            benchmark.revenue.base,
            benchmark.revenue.high,
        )
    )
    assert any("configurable" in assumption for assumption in benchmark.assumptions)

    observed = [
        replace(item, metadata={**item.metadata, "rpm": 5 + index})
        for index, item in enumerate(_contents(3))
    ]
    evidence_backed = estimator.estimate(
        query="Ancient Egypt", contents=observed, monetization_safety=100
    )
    assert evidence_backed.rpm.basis == "observed"


class _FixtureYouTubeConnector:
    def __init__(self, contents: list[Content], *, fail: bool = False) -> None:
        self.contents = contents
        self.fail = fail

    def fetch(self, **_: Any) -> list[dict[str, int]]:
        if self.fail:
            raise RuntimeError("provider failed")
        return [{"index": index} for index in range(len(self.contents))]

    def validate(self, raw: dict[str, int]) -> None:
        if raw["index"] < 0:
            raise ValueError

    def normalize(self, raw: dict[str, int]) -> Content:
        return self.contents[raw["index"]]


def _workflow(session: Session, *, fail: bool = False) -> MoneyWorkflowService:
    return MoneyWorkflowService(
        session, connector=_FixtureYouTubeConnector(_contents(), fail=fail)  # type: ignore[arg-type]
    )


def test_workflow_analysis_brief_persistence_and_outcome(session: Session) -> None:
    service = _workflow(session)
    request = MoneyAnalysisRequest(query="Ancient Egypt", region="US", limit=15)
    analysis = service.analyze(request)
    loaded = service.get_analysis(analysis.analysis_id)
    assert len(analysis.opportunities) == 3
    assert [item.money_score for item in analysis.opportunities] == sorted(
        [item.money_score for item in analysis.opportunities], reverse=True
    )
    assert loaded.opportunities[0].calculation_trace
    brief = service.generate_brief(loaded.opportunities[0].id)
    assert brief.evidence_backed_facts_to_research
    assert all(
        item["verification_required"]
        for item in brief.evidence_backed_facts_to_research
    )
    outcome = service.create_outcome(
        loaded.opportunities[0].id, OutcomeCreate(production_hours=8)
    )
    updated = service.update_outcome(
        outcome.id,
        OutcomeUpdate(
            views_after_7_days=25_000,
            revenue=120,
            result_classification="met_expectation",
        ),
    )
    assert updated.views_after_7_days == 25_000
    assert session.query(MoneyOutcomeModel).count() == 1


def test_workflow_youtube_failure_has_no_google_dependency(session: Session) -> None:
    with pytest.raises(MoneyWorkflowUnavailable, match="YouTube evidence"):
        _workflow(session, fail=True).analyze(
            MoneyAnalysisRequest(query="Ancient Egypt", region="US", limit=15)
        )


def test_money_api_flow_and_validation(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = _workflow(session)
    monkeypatch.setattr(money_api, "_service", lambda _db: service)
    with TestClient(app) as client:
        invalid = client.post(
            "/api/v1/money-opportunities/analyze", json={"query": "x", "limit": 2}
        )
        response = client.post(
            "/api/v1/money-opportunities/analyze",
            json={"query": "Ancient Egypt", "region": "US", "limit": 15},
        )
        body = response.json()
        retrieved = client.get(f"/api/v1/money-opportunities/{body['analysis_id']}")
        opportunity_id = body["opportunities"][0]["id"]
        brief = client.post(f"/api/v1/money-opportunities/{opportunity_id}/brief")
        outcome = client.post(
            f"/api/v1/money-opportunities/{opportunity_id}/outcome",
            json={"publish_status": "planned"},
        )
    assert invalid.status_code == 422
    assert response.status_code == 201
    assert retrieved.status_code == 200
    assert brief.status_code == 200
    assert outcome.status_code == 201
    assert "api_key" not in response.text.lower()
    assert "guaranteed" in response.text.lower()
