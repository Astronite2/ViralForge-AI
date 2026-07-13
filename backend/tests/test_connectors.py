"""Connector SDK tests."""

from collections.abc import Mapping
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
    connector = GoogleTrendsConnector(client_factory=lambda: object())  # type: ignore[arg-type]

    registry.register("google_trends", connector)

    assert registry.get("google_trends") is connector
    assert registry.names() == ("google_trends",)


def test_default_registry_includes_google_trends() -> None:
    registry = build_default_connector_registry()

    assert "google_trends" in registry.names()


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
