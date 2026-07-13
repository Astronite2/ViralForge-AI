"""Connector orchestration tests."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from backend.app.connectors.base import BaseConnector
from backend.app.connectors.registry import ConnectorRegistry
from backend.app.domain.content import Content
from backend.app.domain.trend_signal import TrendSignal
from backend.app.repositories.content import ContentRepository
from backend.app.repositories.decision import DecisionRepository
from backend.app.repositories.topic import TopicRepository
from backend.app.repositories.trend_signal import TrendSignalRepository
from backend.app.services.connector_orchestrator import ConnectorOrchestrator
from backend.app.services.signal_decision import SignalDecisionService


class _FakeSignalConnector(BaseConnector[TrendSignal]):
    def __init__(
        self,
        raw_items: list[Mapping[str, Any]] | None = None,
        *,
        fetch_error: Exception | None = None,
        normalize_error: Exception | None = None,
    ) -> None:
        self.raw_items = raw_items or []
        self.fetch_error = fetch_error
        self.normalize_error = normalize_error

    def fetch(self, **kwargs: Any) -> list[Mapping[str, Any]]:
        if self.fetch_error is not None:
            raise self.fetch_error
        return list(self.raw_items)

    def normalize(self, raw_content: Mapping[str, Any]) -> TrendSignal:
        if self.normalize_error is not None:
            raise self.normalize_error
        return TrendSignal(
            source="google_trends",
            score=1.0,
            confidence=1.0,
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            reason=(
                "Google Trends reported increasing search interest for "
                f"{raw_content['title']} in US."
            ),
        )

    def validate(self, raw_content: Mapping[str, Any]) -> None:
        required = ("query", "title", "url", "published_at", "rank", "geo")
        missing = [field for field in required if field not in raw_content]
        if missing:
            raise ValueError(f"missing: {', '.join(missing)}")
        if not str(raw_content["title"]).strip():
            raise ValueError("title cannot be empty")


class _FakeContentConnector(BaseConnector[Content]):
    def __init__(self, raw_items: list[Mapping[str, Any]]) -> None:
        self.raw_items = raw_items

    def fetch(self, **kwargs: Any) -> list[Mapping[str, Any]]:
        return list(self.raw_items)

    def normalize(self, raw_content: Mapping[str, Any]) -> Content:
        signal = TrendSignal(
            source="youtube",
            score=0.8,
            confidence=0.9,
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            reason=f"YouTube activity increased for {raw_content['title']}.",
        )
        return Content(
            id=str(raw_content["id"]),
            platform="youtube",
            creator_name="History Hub",
            creator_id="channel-1",
            title=str(raw_content["title"]),
            description=None,
            url="https://youtube.com/watch?v=transaction-test",
            language="en",
            country="US",
            published_at=datetime(2026, 1, 1, tzinfo=UTC),
            duration_seconds=60,
            content_type="video",
            metrics={"view_count": float(raw_content["view_count"])},
            signals=(signal,),
        )

    def validate(self, raw_content: Mapping[str, Any]) -> None:
        if not raw_content.get("id"):
            raise ValueError("id is required")


def test_successful_connector_run_creates_decision(session: Any) -> None:
    registry = ConnectorRegistry()
    registry.register(
        "google_trends",
        _FakeSignalConnector(
            raw_items=[
                {
                    "query": "Ancient Egypt",
                    "title": "Ancient Egypt",
                    "url": "https://example.com",
                    "published_at": datetime(2026, 1, 1, tzinfo=UTC),
                    "rank": 1,
                    "geo": "US",
                }
            ]
        ),
    )

    report = ConnectorOrchestrator(
        registry=registry, session_factory=lambda: session
    ).run(enabled_connectors=("google_trends",))

    assert report.connector_reports[0].status == "success"
    assert report.connector_reports[0].items_processed == 1
    assert report.connector_reports[0].decisions_created == 1
    assert len(DecisionRepository(session).list(10, 0)) == 1
    assert len(TopicRepository(session).list(10, 0)) == 1
    assert len(TrendSignalRepository(session).list(10, 0)) == 1


def test_empty_connector_result(session: Any) -> None:
    registry = ConnectorRegistry()
    registry.register("google_trends", _FakeSignalConnector(raw_items=[]))

    report = ConnectorOrchestrator(
        registry=registry, session_factory=lambda: session
    ).run(enabled_connectors=("google_trends",))

    assert report.connector_reports[0].status == "empty"
    assert report.connector_reports[0].items_fetched == 0
    assert report.connector_reports[0].items_processed == 0
    assert report.connector_reports[0].decisions_created == 0


def test_connector_fetch_failure_is_isolated(session: Any) -> None:
    registry = ConnectorRegistry()
    registry.register(
        "failing",
        _FakeSignalConnector(fetch_error=RuntimeError("fetch failed")),
    )
    registry.register(
        "google_trends",
        _FakeSignalConnector(
            raw_items=[
                {
                    "query": "Ancient Egypt",
                    "title": "Ancient Egypt",
                    "url": "https://example.com",
                    "published_at": datetime(2026, 1, 1, tzinfo=UTC),
                    "rank": 1,
                    "geo": "US",
                }
            ]
        ),
    )

    report = ConnectorOrchestrator(
        registry=registry, session_factory=lambda: session
    ).run(enabled_connectors=("failing", "google_trends"))

    failing, succeeding = report.connector_reports
    assert failing.status == "failed"
    assert failing.errors == ("fetch failed",)
    assert succeeding.status == "success"
    assert succeeding.decisions_created == 1
    assert len(DecisionRepository(session).list(10, 0)) == 1


def test_invalid_raw_item_is_reported_without_stopping_batch(session: Any) -> None:
    registry = ConnectorRegistry()
    registry.register(
        "google_trends",
        _FakeSignalConnector(
            raw_items=[
                {
                    "query": "",
                    "title": "",
                    "url": "https://example.com",
                    "published_at": datetime(2026, 1, 1, tzinfo=UTC),
                    "rank": 1,
                    "geo": "US",
                }
            ]
        ),
    )

    report = ConnectorOrchestrator(
        registry=registry, session_factory=lambda: session
    ).run(enabled_connectors=("google_trends",))

    connector_report = report.connector_reports[0]
    assert connector_report.status == "failed"
    assert connector_report.items_failed == 1
    assert connector_report.decisions_created == 0


def test_one_failed_connector_does_not_stop_another(session: Any) -> None:
    registry = ConnectorRegistry()
    registry.register(
        "broken",
        _FakeSignalConnector(fetch_error=RuntimeError("boom")),
    )
    registry.register(
        "healthy",
        _FakeSignalConnector(
            raw_items=[
                {
                    "query": "Ancient Egypt",
                    "title": "Ancient Egypt",
                    "url": "https://example.com",
                    "published_at": datetime(2026, 1, 1, tzinfo=UTC),
                    "rank": 1,
                    "geo": "US",
                }
            ]
        ),
    )

    report = ConnectorOrchestrator(
        registry=registry, session_factory=lambda: session
    ).run(enabled_connectors=("broken", "healthy"))

    assert report.connector_reports[0].status == "failed"
    assert report.connector_reports[1].status == "success"
    assert len(DecisionRepository(session).list(10, 0)) == 1


def test_repeated_event_remains_idempotent(session: Any) -> None:
    raw_item = {
        "query": "Ancient Egypt",
        "title": "Ancient Egypt",
        "url": "https://example.com",
        "published_at": datetime(2026, 1, 1, tzinfo=UTC),
        "rank": 1,
        "geo": "US",
    }
    registry = ConnectorRegistry()
    registry.register("google_trends", _FakeSignalConnector(raw_items=[raw_item]))
    orchestrator = ConnectorOrchestrator(
        registry=registry, session_factory=lambda: session
    )

    first = orchestrator.run(enabled_connectors=("google_trends",))
    second = orchestrator.run(enabled_connectors=("google_trends",))

    assert first.connector_reports[0].decisions_created == 1
    assert second.connector_reports[0].decisions_created == 0
    assert len(DecisionRepository(session).list(10, 0)) == 1


def test_content_and_decision_processing_share_one_transaction(
    session: Any, monkeypatch: Any
) -> None:
    connector = _FakeContentConnector(
        [{"id": "youtube:rollback", "title": "Rollback", "view_count": 100}]
    )
    registry = ConnectorRegistry()
    registry.register("youtube", connector)

    def fail_after_content_save(service: SignalDecisionService, event: Any) -> Any:
        assert ContentRepository(service.session).get("youtube:rollback") is not None
        raise RuntimeError("decision failure")

    monkeypatch.setattr(SignalDecisionService, "process", fail_after_content_save)
    report = ConnectorOrchestrator(
        registry=registry, session_factory=lambda: session
    ).run(enabled_connectors=("youtube",))

    assert report.connector_reports[0].status == "failed"
    assert ContentRepository(session).get("youtube:rollback") is None


def test_reingested_content_updates_existing_row(session: Any) -> None:
    connector = _FakeContentConnector(
        [{"id": "youtube:update", "title": "Original", "view_count": 100}]
    )
    registry = ConnectorRegistry()
    registry.register("youtube", connector)
    orchestrator = ConnectorOrchestrator(
        registry=registry, session_factory=lambda: session
    )

    first = orchestrator.run(enabled_connectors=("youtube",))
    connector.raw_items = [
        {"id": "youtube:update", "title": "Updated", "view_count": 250}
    ]
    second = orchestrator.run(enabled_connectors=("youtube",))

    stored = ContentRepository(session).get("youtube:update")
    assert first.connector_reports[0].decisions_created == 1
    assert second.connector_reports[0].decisions_created == 1
    assert len(ContentRepository(session).list()) == 1
    assert stored is not None
    assert stored.title == "Updated"
    assert stored.metrics == {"view_count": 250.0}


def test_multiple_connector_types_share_unified_orchestration(session: Any) -> None:
    registry = ConnectorRegistry()
    registry.register(
        "google_trends",
        _FakeSignalConnector(
            raw_items=[
                {
                    "query": "Ancient Egypt",
                    "title": "Ancient Egypt",
                    "url": "https://example.com/trend",
                    "published_at": datetime(2026, 1, 1, tzinfo=UTC),
                    "rank": 1,
                    "geo": "US",
                }
            ]
        ),
    )
    registry.register(
        "youtube",
        _FakeContentConnector(
            [{"id": "youtube:multi", "title": "Roman History", "view_count": 100}]
        ),
    )

    report = ConnectorOrchestrator(
        registry=registry, session_factory=lambda: session
    ).run(enabled_connectors=("google_trends", "youtube"))

    assert [item.status for item in report.connector_reports] == [
        "success",
        "success",
    ]
    assert len(DecisionRepository(session).list(10, 0)) == 2
    assert ContentRepository(session).get("youtube:multi") is not None
