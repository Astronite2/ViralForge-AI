"""Connector registry and default connector factory."""

from collections.abc import Iterable
from typing import Any

from backend.app.connectors.base import BaseConnector
from backend.app.connectors.google_trends import GoogleTrendsConnector
from backend.app.connectors.google_trends_providers import (
    DisabledGoogleTrendsProvider,
    GoogleTrendsProvider,
    OfficialGoogleTrendsProvider,
    PytrendsGoogleTrendsProvider,
)
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
    registry.register(
        "google_trends",
        GoogleTrendsConnector(
            provider=build_google_trends_provider(),
            default_geo=settings.google_trends_default_geo,
            default_timeframe=settings.google_trends_default_timeframe,
            max_results=settings.google_trends_max_results,
            retries=settings.google_trends_retries,
            backoff_seconds=settings.google_trends_backoff_seconds,
        ),
    )
    if settings.youtube_api_key:
        registry.register(
            settings.youtube_source_name,
            YouTubeConnector(api_key=settings.youtube_api_key),
        )
    return registry


def build_google_trends_provider() -> GoogleTrendsProvider:
    """Select the configured provider without registering test fixtures."""
    if not settings.google_trends_enabled:
        return DisabledGoogleTrendsProvider()

    provider_name = settings.google_trends_provider.strip().lower()
    if provider_name == "pytrends":
        return PytrendsGoogleTrendsProvider(
            retries=settings.google_trends_retries,
            backoff_seconds=settings.google_trends_backoff_seconds,
        )
    if provider_name == "official":
        return OfficialGoogleTrendsProvider(
            project_id=settings.google_trends_official_project_id,
            credentials_file=settings.google_trends_official_credentials_file,
            api_endpoint=settings.google_trends_official_api_endpoint,
            access_enabled=settings.google_trends_official_access_enabled,
        )
    if provider_name == "fixture":
        raise ValueError(
            "FixtureGoogleTrendsProvider is test-only and cannot be selected by "
            "application configuration"
        )
    raise ValueError(f"Unsupported GOOGLE_TRENDS_PROVIDER: {provider_name}")
