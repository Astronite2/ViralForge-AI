"""Connector SDK tests."""

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from backend.app.connectors.base import BaseConnector
from backend.app.connectors.google_trends import GoogleTrendsConnector
from backend.app.connectors.registry import (
    ConnectorRegistry,
    build_default_connector_registry,
)
from backend.app.domain.trend_signal import TrendSignal


def test_registry_resolves_registered_connectors() -> None:
    registry = ConnectorRegistry()
    connector = GoogleTrendsConnector(fetcher=lambda geo, limit: [])

    registry.register("google_trends", connector)

    assert registry.get("google_trends") is connector
    assert registry.names() == ("google_trends",)


def test_default_registry_includes_google_trends() -> None:
    registry = build_default_connector_registry()

    assert "google_trends" in registry.names()


def test_google_trends_connector_normalizes_trending_item() -> None:
    connector = GoogleTrendsConnector(fetcher=lambda geo, limit: [])
    raw_item: dict[str, Any] = {
        "query": "AI video tools",
        "title": "AI video tools",
        "url": "https://trends.google.com/trends/explore?q=AI%20video%20tools",
        "published_at": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
        "rank": 1,
        "geo": "US",
    }

    connector.validate(raw_item)
    signal = connector.normalize(raw_item)

    assert isinstance(signal, TrendSignal)
    assert signal.source == "google_trends"
    assert signal.score == 1.0
    assert signal.confidence == 1.0
    assert signal.timestamp == datetime(2026, 1, 1, tzinfo=UTC)


def test_connector_base_is_pluggable() -> None:
    class StubConnector(BaseConnector[TrendSignal]):
        def fetch(self, **kwargs: Any) -> list[Mapping[str, Any]]:
            return []

        def normalize(self, raw_content: Mapping[str, Any]) -> TrendSignal:
            raise NotImplementedError

        def validate(self, raw_content: Mapping[str, Any]) -> None:
            return None

    registry = ConnectorRegistry()
    registry.register("stub", StubConnector())

    assert registry.get("stub").__class__.__name__ == "StubConnector"
