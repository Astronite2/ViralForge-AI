"""Connector orchestration tests."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from backend.app.connectors.base import BaseConnector
from backend.app.connectors.registry import ConnectorRegistry
from backend.app.domain.trend_signal import TrendSignal
from backend.app.repositories.decision import DecisionRepository
from backend.app.repositories.topic import TopicRepository
from backend.app.repositories.trend_signal import TrendSignalRepository
from backend.app.services.connector_orchestrator import ConnectorOrchestrator


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
