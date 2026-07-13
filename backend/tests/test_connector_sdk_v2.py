"""Connector SDK v2 metadata, registry, and discovery API tests."""

from fastapi.testclient import TestClient

from backend.app.connectors.google_trends import GoogleTrendsConnector
from backend.app.connectors.google_trends_providers import FixtureGoogleTrendsProvider
from backend.app.connectors.metadata import (
    ConnectorCapabilities,
    ConnectorCapability,
)
from backend.app.connectors.registry import ConnectorRegistry
from backend.app.connectors.youtube import YouTubeConnector
from backend.app.main import app


def test_capabilities_are_deduplicated_and_platform_ordered() -> None:
    capabilities = ConnectorCapabilities(
        values=[
            ConnectorCapability.CONTENT_DISCOVERY,
            ConnectorCapability.SEARCH,
            ConnectorCapability.SEARCH,
        ]
    )
    assert capabilities.api_values() == ("SEARCH", "CONTENT_DISCOVERY")
    assert capabilities.supports("SEARCH")
    assert "UNKNOWN" not in capabilities
    assert ConnectorCapabilities().api_values() == ()


def test_connector_metadata_serializes_without_credentials() -> None:
    metadata = YouTubeConnector(api_key="super-secret-api-key").metadata
    payload = metadata.model_dump(mode="json")
    assert payload["provider"] == "youtube_data_api"
    assert "super-secret-api-key" not in str(payload)
    assert "COMMENTS" not in metadata.capabilities.api_values()
    assert "MONETIZATION_SIGNALS" not in metadata.capabilities.api_values()


def test_google_trends_declares_only_implemented_capabilities() -> None:
    metadata = GoogleTrendsConnector(provider=FixtureGoogleTrendsProvider()).metadata
    assert metadata.provider == "fixture"
    assert metadata.supports_fixture_access is True
    assert "TRENDING" in metadata.capabilities
    assert "HISTORICAL" in metadata.capabilities
    assert "COMMENTS" not in metadata.capabilities


def test_registry_filters_and_checks_capability_deterministically() -> None:
    registry = ConnectorRegistry()
    registry.register("youtube", YouTubeConnector(api_key="test"))
    registry.register(
        "google_trends",
        GoogleTrendsConnector(provider=FixtureGoogleTrendsProvider()),
    )
    assert registry.names() == ("google_trends", "youtube")
    matches = registry.filter_by_capability("SEARCH")
    assert tuple(item.metadata.name for item in matches) == ("youtube",)
    assert registry.supports_capability("google_trends", "TRENDING")


def test_registry_rejects_unknown_capability() -> None:
    registry = ConnectorRegistry()
    try:
        registry.filter_by_capability("NOT_REAL")
    except ValueError as exc:
        assert "NOT_REAL" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("unknown capabilities must be rejected")


def test_connector_discovery_and_capability_catalog_api() -> None:
    with TestClient(app) as client:
        listing = client.get("/api/v1/connectors")
        catalog = client.get("/api/v1/connectors/capabilities")
        filtered = client.get("/api/v1/connectors?capability=SEARCH")
        unknown = client.get("/api/v1/connectors?capability=NOT_REAL")

    assert listing.status_code == 200
    assert [item["name"] for item in listing.json()] == ["google_trends", "youtube"]
    assert all("runtime_status" in item for item in listing.json())
    assert "COMMENTS" in [item["value"] for item in catalog.json()]
    assert [item["name"] for item in filtered.json()] == ["youtube"]
    assert unknown.status_code == 422
    assert "api_key" not in listing.text.lower()
    assert "credential" not in listing.text.lower()
