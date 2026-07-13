"""Unified Signal Engine conversion and evidence tests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from backend.app.connectors.google_trends import GoogleTrendsConnector
from backend.app.domain.content import Content
from backend.app.domain.trend_signal import TrendSignal
from backend.app.domain.unified_signal import SignalType, UnifiedSignal
from backend.app.models.topic import Topic
from backend.app.repositories.historical_observation import (
    HistoricalObservationRepository,
)
from backend.app.services.decision_engine import DecisionEngine
from backend.app.services.evidence_factory import EvidenceFactory
from backend.app.services.signal_decision import SignalDecisionService
from backend.app.services.unified_evidence_mapper import UnifiedEvidenceMapper
from backend.app.services.unified_signal_normalizer import (
    MalformedSignalError,
    UnifiedSignalNormalizer,
)
from backend.app.utils.events import SignalDetected
from backend.app.utils.idempotency import stable_signal_event_id

OBSERVED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def legacy_signal(**overrides: Any) -> TrendSignal:
    values: dict[str, Any] = {
        "source": "google_trends",
        "score": 0.8,
        "confidence": 0.9,
        "timestamp": OBSERVED_AT,
        "reason": (
            "Google Trends reported increasing search interest for Ancient Egypt "
            "in US."
        ),
        "metadata": {
            "signal_id": "google:ancient-egypt",
            "interest_score": 80,
            "region": "US",
            "language": "en-US",
        },
    }
    values.update(overrides)
    return TrendSignal(**values)


def unified_signal(**overrides: Any) -> UnifiedSignal:
    values: dict[str, Any] = {
        "normalization_id": "unified-1",
        "topic_id": "topic-1",
        "topic_name": "Ancient Egypt",
        "source": "test",
        "signal_type": SignalType.AUDIENCE_DEMAND,
        "observed_at": OBSERVED_AT,
        "confidence": 0.9,
        "popularity": None,
        "velocity": None,
        "acceleration": None,
        "engagement": None,
        "sentiment": None,
        "freshness": None,
        "competition": None,
        "monetization": None,
        "evergreen": None,
        "platform_fit": None,
        "geography": None,
        "language": None,
        "raw_value": None,
        "normalized_value": 0.8,
        "reason": "Audience demand observed for Ancient Egypt.",
        "evidence_references": (),
        "connector_metadata": {},
        "event_version": "v1",
        "correlation_id": "correlation-1",
        "source_item_id": None,
        "content_id": None,
    }
    values.update(overrides)
    return UnifiedSignal(**values)


def test_google_trends_converts_to_search_trend() -> None:
    connector = GoogleTrendsConnector(client_factory=lambda: object())  # type: ignore[arg-type]
    raw = {
        "id": "google-item-1",
        "query": "Ancient Egypt",
        "title": "Ancient Egypt",
        "published_at": OBSERVED_AT,
        "geo": "US",
        "trend_type": "daily_trending_searches",
        "timeframe": "today 3-m",
        "interest_score": 80,
        "related_queries": [],
        "related_topics": [],
        "source_url": "https://trends.google.com/trends/explore?q=Ancient+Egypt",
        "category": 0,
        "language": "en-US",
        "rank": 1,
    }

    signal = connector.normalize(raw)
    unified = UnifiedSignalNormalizer().normalize(
        signal, event_version="v1", correlation_id="correlation-1"
    )[0]

    assert unified.signal_type is SignalType.SEARCH_TREND
    assert unified.topic_name == "Ancient Egypt"
    assert unified.popularity == signal.score
    assert unified.raw_value == 80.0
    assert unified.source_item_id == "google-item-1"
    assert unified.geography == "US"


def test_youtube_content_converts_embedded_signals() -> None:
    signal = TrendSignal(
        source="youtube",
        score=0.72,
        confidence=0.85,
        timestamp=OBSERVED_AT,
        reason="YouTube reported increasing engagement for Ancient Egypt in US.",
    )
    content = Content(
        id="youtube:video-1",
        platform="youtube",
        creator_name="History Hub",
        creator_id="channel-1",
        title="Ancient Egypt",
        description=None,
        url="https://youtube.com/watch?v=video-1",
        language="en",
        country="US",
        published_at=OBSERVED_AT,
        duration_seconds=120,
        content_type="video",
        metrics={"view_count": 1000.0, "engagement_rate": 0.11},
        signals=(signal,),
        metadata={"video_id": "video-1", "source_url": "https://youtube.com"},
    )

    unified = UnifiedSignalNormalizer().normalize(
        content, event_version="v1", correlation_id="correlation-1"
    )[0]

    assert unified.signal_type is SignalType.CONTENT_PERFORMANCE
    assert unified.content_id == "youtube:video-1"
    assert unified.source_item_id == "video-1"
    assert unified.engagement == 0.11
    assert unified.raw_value == 1000.0
    assert unified.language == "en"


def test_missing_dimensions_remain_explicit_nulls() -> None:
    unified = UnifiedSignalNormalizer().normalize(
        legacy_signal(metadata={}),
        event_version="v1",
        correlation_id="correlation-1",
    )[0]

    payload = unified.to_payload()

    assert payload["velocity"] is None
    assert payload["sentiment"] is None
    assert payload["competition"] is None
    assert payload["monetization"] is None
    assert payload["source_item_id"] is None


def test_malformed_signal_rejected_with_typed_error() -> None:
    with pytest.raises(MalformedSignalError, match="score must be between"):
        UnifiedSignalNormalizer().normalize(
            legacy_signal(score=1.5),
            event_version="v1",
            correlation_id="correlation-1",
        )

    empty_content = Content(
        id="youtube:empty",
        platform="youtube",
        creator_name="Channel",
        creator_id="channel",
        title="Empty",
        description=None,
        url="https://youtube.com",
        language=None,
        country=None,
        published_at=OBSERVED_AT,
        duration_seconds=None,
        content_type="video",
    )
    with pytest.raises(MalformedSignalError, match="at least one"):
        UnifiedSignalNormalizer().normalize(
            empty_content,
            event_version="v1",
            correlation_id="correlation-1",
        )


def test_normalization_and_legacy_idempotency_are_deterministic() -> None:
    signal = legacy_signal()
    normalizer = UnifiedSignalNormalizer()

    first = normalizer.normalize(
        signal, event_version="v1", correlation_id="correlation-1"
    )[0]
    second = normalizer.normalize(
        signal, event_version="v1", correlation_id="correlation-1"
    )[0]

    assert first == second
    assert stable_signal_event_id("google_trends", signal) == stable_signal_event_id(
        "google_trends", signal
    )


def test_evidence_mapping_uses_explicit_dimensions_and_conflict_reason() -> None:
    signal = unified_signal(
        popularity=0.8,
        velocity=0.7,
        engagement=0.6,
        sentiment=0.2,
        competition=0.3,
        monetization=0.9,
        evergreen=0.4,
        platform_fit=0.75,
    )
    factors = UnifiedEvidenceMapper().map(
        signal,
        (
            "trend_momentum",
            "audience_demand",
            "revenue_potential",
            "competition",
            "evergreen",
            "platform_fit",
            "confidence",
        ),
        {
            "revenue_potential": 50.0,
            "competition": 50.0,
            "evergreen": 50.0,
            "platform_fit": 50.0,
        },
    )
    mapped = {item.factor: item for item in factors}

    assert mapped["trend_momentum"].value == 70.0
    assert mapped["trend_momentum"].dimensions == ("velocity",)
    assert mapped["audience_demand"].value == 80.0
    assert "sentiment conflicts" in mapped["audience_demand"].reason
    assert mapped["competition"].value == 30.0
    assert mapped["revenue_potential"].value == 90.0


def test_absent_dimensions_use_visible_neutral_defaults() -> None:
    topic = Topic(
        id="topic-1",
        display_name="Ancient Egypt",
        normalized_key="ancient egypt",
    )
    content = EvidenceFactory().build_content(
        topic,
        unified_signal(),
        signal_id="signal-1",
        correlation_id="correlation-1",
        event_version="v1",
    )
    decision = DecisionEngine().evaluate(content, content.signals)
    competition = next(
        item for item in decision.evidence if item.factor == "Competition"
    )

    assert competition.raw_value == 50.0
    assert competition.normalized_value == 0.5
    assert "unified signal did not provide" in competition.reason
    assert "competition" in content.metadata["neutral_decision_factors"]


def test_duplicate_unified_event_is_processed_once(session: Any) -> None:
    signal = legacy_signal()
    unified = UnifiedSignalNormalizer().normalize(
        signal, event_version="v1", correlation_id="correlation-1"
    )[0]
    event = SignalDetected(
        signal=signal,
        unified_signal=unified,
        event_id="unified-event-1",
        correlation_id="correlation-1",
    )
    service = SignalDecisionService(session)

    first = service.process(event)
    second = service.process(event)

    assert first.duplicate is False
    assert second.duplicate is True
    observations = HistoricalObservationRepository(session).list_by_topic(
        first.topic.id, 10, 0
    )
    assert len(observations) == 1
    assert observations[0].payload["unified_signal"]["signal_type"] == "SEARCH_TREND"


def test_unified_signal_survives_event_serialization() -> None:
    signal = legacy_signal()
    unified = UnifiedSignalNormalizer().normalize(
        signal, event_version="v1", correlation_id="correlation-1"
    )[0]
    event = SignalDetected(
        signal=signal,
        unified_signal=unified,
        event_id="serialized-event",
        correlation_id="correlation-1",
    )

    restored = SignalDetected.from_payload(event.to_payload())

    assert restored.unified_signal == unified
