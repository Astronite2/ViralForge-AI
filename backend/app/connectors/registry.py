"""Connector registry and default connector factory."""

from collections.abc import Iterable
from typing import Any

from backend.app.connectors.base import BaseConnector
from backend.app.connectors.google_trends import GoogleTrendsConnector
from backend.app.connectors.youtube import YouTubeConnector
from backend.app.core.config import settings


class ConnectorRegistry:
    """Registry for pluggable connector instances."""

    def __init__(self) -> None:
        self._connectors: dict[str, BaseConnector[Any]] = {}

    def register(self, name: str, connector: BaseConnector[Any]) -> None:
        """Register or replace a connector by name."""
        self._connectors[name] = connector

    def register_many(
        self, connectors: Iterable[tuple[str, BaseConnector[Any]]]
    ) -> None:
        """Register multiple connectors."""
        for name, connector in connectors:
            self.register(name, connector)

    def get(self, name: str) -> BaseConnector[Any]:
        """Return a registered connector."""
        try:
            return self._connectors[name]
        except KeyError as exc:
            raise KeyError(f"Unknown connector: {name}") from exc

    def names(self) -> tuple[str, ...]:
        """Return registered connector names in insertion order."""
        return tuple(self._connectors.keys())

    def items(self) -> tuple[tuple[str, BaseConnector[Any]], ...]:
        """Return registered connector pairs."""
        return tuple(self._connectors.items())


def build_default_connector_registry() -> ConnectorRegistry:
    """Create the default registry with the Google Trends connector."""
    registry = ConnectorRegistry()
    registry.register("google_trends", GoogleTrendsConnector())
    if settings.youtube_api_key:
        registry.register(
            settings.youtube_source_name,
            YouTubeConnector(api_key=settings.youtube_api_key),
        )
    return registry
