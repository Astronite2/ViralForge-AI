"""Knowledge-layer tests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi.testclient import TestClient

from backend.app.db.session import get_db
from backend.app.domain.knowledge import HistoricalObservation
from backend.app.domain.trend_signal import TrendSignal
from backend.app.main import app
from backend.app.repositories.historical_observation import (
    HistoricalObservationRepository,
)
from backend.app.repositories.opportunity_score import OpportunityScoreRepository
from backend.app.repositories.topic import TopicRepository
from backend.app.repositories.topic_relationship import TopicRelationshipRepository
from backend.app.repositories.trend_signal import TrendSignalRepository
from backend.app.services.historical_analytics import HistoricalAnalyticsService
from backend.app.services.knowledge_layer import KnowledgeLayerService
from backend.app.services.opportunity_engine import OpportunityEngine
from backend.app.services.signal_decision import SignalDecisionService
from backend.app.utils.events import SignalDetected


def test_knowledge_ingestion_merges_duplicates_and_scores_opportunity(
    session: Any,
) -> None:
    topic = TopicRepository(session).create("Ancient Egypt", "ancient egypt")
    signal = TrendSignalRepository(session).create(
        topic_id=topic.id,
        source="google_trends",
        score=0.8,
        confidence=0.9,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        reason="Google Trends reported increasing search interest for Ancient Egypt.",
        correlation_id="correlation-1",
        raw_metadata={"query": "Ancient Egypt"},
    )

    service = KnowledgeLayerService(session)
    first = service.ingest_observation(
        topic,
        signal,
        correlation_id="correlation-1",
        event_version="v1",
        metadata={"raw_item": {"query": "Ancient Egypt"}},
    )
    second = service.ingest_observation(
        topic,
        signal,
        correlation_id="correlation-1",
        event_version="v1",
        metadata={"raw_item": {"query": "Ancient Egypt"}},
    )

    assert first.duplicate is False
    assert second.duplicate is True
    assert (
        len(HistoricalObservationRepository(session).list_by_topic(topic.id, 10, 0))
        == 1
    )
    assert len(OpportunityScoreRepository(session).list_by_topic(topic.id)) == 1
    assert first.opportunity_score.score >= 0.0


def test_historical_analytics_and_opportunity_engine_are_deterministic() -> None:
    first = HistoricalObservation(
        id="obs-1",
        topic_id="topic-1",
        source="google_trends",
        connector_name="google_trends",
        observation_type="signal",
        observed_at=datetime(2026, 1, 1, tzinfo=UTC),
        correlation_id="correlation-1",
        observation_hash="hash-1",
        payload={"signal_score": 50.0},
        change_type="new",
    )
    second = HistoricalObservation(
        id="obs-2",
        topic_id="topic-1",
        source="youtube",
        connector_name="youtube",
        observation_type="content_signal",
        observed_at=datetime(2026, 1, 2, tzinfo=UTC),
        correlation_id="correlation-2",
        observation_hash="hash-2",
        payload={"signal_score": 75.0},
        change_type="increase",
    )

    analytics = HistoricalAnalyticsService().calculate((first, second))
    opportunity = OpportunityEngine().evaluate(
        "topic-1",
        second,
        analytics,
        correlation_id="correlation-2",
    )

    assert analytics.growth_rate > 0.0
    assert analytics.momentum > 0.0
    assert analytics.peak_detected is True
    assert opportunity.score >= 0.0
    assert "demand" in opportunity.dimensions
    assert "growth" in opportunity.explanations


def test_topic_graph_creation_and_query(session: Any) -> None:
    topic_repo = TopicRepository(session)
    source = topic_repo.create("Ancient Egypt", "ancient egypt")
    target = topic_repo.create("Pyramids", "pyramids")
    service = KnowledgeLayerService(session)

    service.record_relationship(
        source,
        target,
        "related",
        0.85,
        "Shared historical context.",
        correlation_id="correlation-graph",
    )

    relationships = TopicRelationshipRepository(session).list_by_topic(source.id)
    assert len(relationships) == 1
    assert relationships[0].relationship_type == "related"
    assert relationships[0].strength == 0.85


def test_history_and_graph_apis_return_persisted_knowledge(session: Any) -> None:
    topic_repo = TopicRepository(session)
    topic = topic_repo.create("Ancient Egypt", "ancient egypt")
    signal = TrendSignal(
        source="google_trends",
        score=0.8,
        confidence=0.9,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        reason="Google Trends reported increasing search interest for Ancient Egypt.",
    )
    event = SignalDetected(
        signal=signal,
        metadata={
            "raw_item": {"query": "Ancient Egypt"},
            "content": {
                "id": "youtube:video-1",
                "platform": "youtube",
                "content_type": "video",
            },
        },
        event_id="event-history",
        correlation_id="correlation-history",
    )
    result = SignalDecisionService(session).process(event)
    assert result.topic.id == topic.id

    service = KnowledgeLayerService(session)
    target = topic_repo.create("Pyramids", "pyramids")
    service.record_relationship(
        topic,
        target,
        "related",
        0.8,
        "Historical context overlap.",
        correlation_id="correlation-history",
    )

    app.dependency_overrides[get_db] = lambda: session
    try:
        with TestClient(app) as client:
            history_response = client.get(f"/api/v1/history/{topic.id}")
            assert history_response.status_code == 200
            history_payload = history_response.json()
            assert history_payload["observations"]
            assert history_payload["analytics"]["trend_age"] >= 0.0
            assert history_payload["opportunity_scores"]

            graph_response = client.get(f"/api/v1/topic-graph/{topic.id}")
            assert graph_response.status_code == 200
            graph_payload = graph_response.json()
            assert graph_payload["relationships"]
            assert graph_payload["relationships"][0]["relationship_type"] == "related"
    finally:
        app.dependency_overrides.clear()
