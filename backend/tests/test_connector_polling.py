"""Connector polling service tests."""

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from backend.app.connectors.base import BaseConnector
from backend.app.connectors.registry import ConnectorRegistry
from backend.app.domain.content import Content
from backend.app.domain.trend_signal import TrendSignal
from backend.app.pipeline.pipeline import ContentPipeline
from backend.app.services.connector_polling import ConnectorPollingService
from backend.app.utils.events import InMemorySignalEventEmitter


def test_polling_service_emits_signal_detected_events() -> None:
    class SignalConnector(BaseConnector[TrendSignal]):
        def fetch(self, **kwargs: Any) -> list[Mapping[str, Any]]:
            return [
                {
                    "query": "AI video tools",
                    "title": "AI video tools",
                    "url": "https://example.com",
                    "published_at": datetime(2026, 1, 1, tzinfo=UTC),
                    "rank": 1,
                    "geo": "US",
                }
            ]

        def normalize(self, raw_content: Mapping[str, Any]) -> TrendSignal:
            return TrendSignal(
                source="google_trends",
                score=1.0,
                confidence=0.9,
                timestamp=datetime(2026, 1, 1, tzinfo=UTC),
                reason="Trending search.",
            )

        def validate(self, raw_content: Mapping[str, Any]) -> None:
            return None

    registry = ConnectorRegistry()
    registry.register("google_trends", SignalConnector())
    emitter = InMemorySignalEventEmitter()

    result = ConnectorPollingService(
        registry, content_pipeline=ContentPipeline(), event_emitter=emitter
    ).poll_connector("google_trends")

    assert len(result.signals) == 1
    assert len(result.events) == 1
    assert tuple(emitter.events) == result.events
    assert result.events[0].signal.source == "google_trends"


def test_polling_service_routes_content_through_existing_pipeline() -> None:
    class ContentConnector(BaseConnector[Content]):
        def fetch(self, **kwargs: Any) -> list[Mapping[str, Any]]:
            return [
                {
                    "id": "content-1",
                    "platform": "youtube",
                    "creator_name": "Creator",
                    "creator_id": "creator-1",
                    "title": "A title",
                    "description": "Description",
                    "url": "https://example.com",
                    "language": "en",
                    "country": "US",
                    "published_at": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
                    "duration_seconds": 60,
                    "content_type": "video",
                    "metrics": {"views": 100.0},
                    "analysis": {},
                    "metadata": {},
                }
            ]

        def normalize(self, raw_content: Mapping[str, Any]) -> Content:
            return Content(
                id="content-1",
                platform="youtube",
                creator_name="Creator",
                creator_id="creator-1",
                title="A title",
                description="Description",
                url="https://example.com",
                language="en",
                country="US",
                published_at=datetime(2026, 1, 1, tzinfo=UTC),
                duration_seconds=60,
                content_type="video",
                metrics={"views": 100.0},
                analysis={},
                metadata={},
            )

        def validate(self, raw_content: Mapping[str, Any]) -> None:
            return None

    registry = ConnectorRegistry()
    registry.register("youtube", ContentConnector())

    result = ConnectorPollingService(
        registry, content_pipeline=ContentPipeline(), event_emitter=None
    ).poll_connector("youtube")

    assert len(result.pipeline_results) == 1
    assert result.pipeline_results[0].content.metadata["title_length"] == 7
    assert not result.signals
    assert not result.events
