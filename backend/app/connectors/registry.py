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
from backend.app.connectors.metadata import (
    ConnectorCapability,
    ConnectorMetadata,
)
from backend.app.connectors.reddit import RedditConnector
from backend.app.connectors.reddit_providers import (
    DisabledRedditProvider,
    OfficialRedditProvider,
    RedditProvider,
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
        """Return registered connector names deterministically."""
        return tuple(sorted(self._connectors))

    def items(self) -> tuple[tuple[str, BaseConnector[Any]], ...]:
        """Return registered connector pairs."""
        return tuple((name, self._connectors[name]) for name in self.names())

    def list_metadata(self) -> tuple[ConnectorMetadata, ...]:
        return tuple(connector.metadata for _, connector in self.items())

    def filter_by_capability(
        self, capability: ConnectorCapability | str
    ) -> tuple[BaseConnector[Any], ...]:
        member = ConnectorCapability(capability)
        return tuple(
            connector
            for _, connector in self.items()
            if connector.capabilities.supports(member)
        )

    def supports_capability(
        self, name: str, capability: ConnectorCapability | str
    ) -> bool:
        return self.get(name).capabilities.supports(ConnectorCapability(capability))


def build_default_connector_registry(
    *, include_disabled: bool = False
) -> ConnectorRegistry:
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
    if settings.youtube_api_key or include_disabled:
        registry.register(
            settings.youtube_source_name,
            YouTubeConnector(api_key=settings.youtube_api_key),
        )
    reddit_ready = bool(
        settings.reddit_enabled
        and settings.reddit_client_id
        and settings.reddit_client_secret
    )
    if reddit_ready or include_disabled:
        registry.register(settings.reddit_source_name, build_reddit_connector())
    return registry


def build_reddit_connector() -> RedditConnector:
    """Build Reddit without permitting fixture selection from configuration."""
    return RedditConnector(
        provider=build_reddit_provider(),
        default_subreddits=settings.reddit_default_subreddits,
        default_query=settings.reddit_default_query,
        default_sort=settings.reddit_default_sort,
        default_time_filter=settings.reddit_default_time_filter,
        default_limit=settings.reddit_default_limit,
    )


def build_reddit_provider() -> RedditProvider:
    provider_name = settings.reddit_provider.strip().lower()
    if provider_name == "fixture":
        raise ValueError(
            "FixtureRedditProvider is test-only and cannot be selected by "
            "application configuration"
        )
    if provider_name != "official":
        raise ValueError(f"Unsupported REDDIT_PROVIDER: {provider_name}")
    if not settings.reddit_enabled:
        return DisabledRedditProvider()
    return OfficialRedditProvider(
        client_id=settings.reddit_client_id,
        client_secret=settings.reddit_client_secret,
        user_agent=settings.reddit_user_agent,
        timeout_seconds=settings.reddit_timeout_seconds,
        max_retries=settings.reddit_max_retries,
        backoff_seconds=settings.reddit_backoff_seconds,
    )


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
