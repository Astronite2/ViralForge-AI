"""Google Trends provider-boundary and degraded orchestration tests."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.app.connectors.base import BaseConnector
from backend.app.connectors.google_trends import GoogleTrendsConnector
from backend.app.connectors.google_trends_providers import (
    FixtureGoogleTrendsProvider,
    GoogleTrendsConfigurationRequiredError,
    GoogleTrendsProviderUnavailableError,
    GoogleTrendsRateLimitError,
    OfficialGoogleTrendsProvider,
    PytrendsGoogleTrendsProvider,
)
from backend.app.connectors.registry import (
    ConnectorRegistry,
    build_google_trends_provider,
)
from backend.app.core.config import settings
from backend.app.domain.connector_orchestration import ConnectorExecutionReport
from backend.app.domain.content import Content
from backend.app.domain.trend_signal import TrendSignal
from backend.app.main import app
from backend.app.repositories.content import ContentRepository
from backend.app.repositories.trend_signal import TrendSignalRepository
from backend.app.services.connector_orchestrator import ConnectorOrchestrator
from backend.app.services.connector_status import (
    ConnectorRuntimeStatus,
    ConnectorStatusStore,
)


class _Values:
    def __init__(self, values: list[list[str]]) -> None:
        self._values = values

    def tolist(self) -> list[list[str]]:
        return self._values


class _Frame:
    empty = False

    def __init__(self, values: list[list[str]]) -> None:
        self.values = _Values(values)


class _PytrendsClient:
    def __init__(self, failures: list[Exception] | None = None) -> None:
        self.failures = failures or []
        self.calls = 0

    def trending_searches(self, pn: str) -> _Frame:
        self.calls += 1
        if self.failures:
            raise self.failures.pop(0)
        return _Frame([["Ancient Egypt"]])

    def build_payload(
        self, kw_list: list[str], cat: int, timeframe: str, geo: str
    ) -> None:
        return None

    def interest_over_time(self) -> Any:
        return None

    def related_queries(self) -> Mapping[str, Any]:
        return {}

    def related_topics(self) -> Mapping[str, Any]:
        return {}


class _HttpFailure(Exception):
    def __init__(self, status_code: int) -> None:
        self.response = type("Response", (), {"status_code": status_code})()


class _YouTubeFixtureConnector(BaseConnector[Content]):
    def fetch(self, **kwargs: Any) -> list[Mapping[str, Any]]:
        return [{"id": "youtube:provider-test", "title": "Roman History"}]

    def validate(self, raw_content: Mapping[str, Any]) -> None:
        if not raw_content.get("id"):
            raise ValueError("id required")

    def normalize(self, raw_content: Mapping[str, Any]) -> Content:
        observed_at = datetime(2026, 1, 1, tzinfo=UTC)
        signal = TrendSignal(
            source="youtube",
            score=0.8,
            confidence=0.9,
            timestamp=observed_at,
            reason="YouTube reported increasing engagement for Roman History in US.",
        )
        return Content(
            id=str(raw_content["id"]),
            platform="youtube",
            creator_name="History Hub",
            creator_id="channel-1",
            title=str(raw_content["title"]),
            description=None,
            url="https://youtube.com/watch?v=provider-test",
            language="en",
            country="US",
            published_at=observed_at,
            duration_seconds=60,
            content_type="video",
            metrics={"view_count": 100.0},
            signals=(signal,),
        )


def test_official_provider_requires_explicit_access_configuration() -> None:
    provider = OfficialGoogleTrendsProvider()

    assert provider.is_configured is False
    with pytest.raises(
        GoogleTrendsConfigurationRequiredError, match="not configured"
    ) as error:
        provider.fetch_trending(geo="US", limit=10)

    assert error.value.error_code == "configuration_required"


def test_disabled_configuration_selects_disabled_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "google_trends_enabled", False)

    provider = build_google_trends_provider()

    assert provider.provider_name == "disabled"


def test_fixture_provider_cannot_be_selected_by_application_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "google_trends_enabled", True)
    monkeypatch.setattr(settings, "google_trends_provider", "fixture")

    with pytest.raises(ValueError, match="test-only"):
        build_google_trends_provider()


def test_pytrends_provider_success_uses_mock_client() -> None:
    client = _PytrendsClient()
    provider = PytrendsGoogleTrendsProvider(client_factory=lambda: client)

    result = provider.fetch_trending(geo="US", limit=1)

    assert result == [{"query": "Ancient Egypt", "rank": 1}]
    assert client.calls == 1
    assert provider.experimental is True


def test_pytrends_404_is_unavailable_without_retry_storm() -> None:
    client = _PytrendsClient([_HttpFailure(404), _HttpFailure(404)])
    delays: list[float] = []
    provider = PytrendsGoogleTrendsProvider(
        client_factory=lambda: client,
        retries=5,
        sleeper=delays.append,
    )

    with pytest.raises(GoogleTrendsProviderUnavailableError, match="HTTP 404") as error:
        provider.fetch_trending(geo="US", limit=1)

    assert error.value.error_code == "provider_unavailable"
    assert client.calls == 1
    assert delays == []


def test_pytrends_429_is_translated_to_rate_limited() -> None:
    client = _PytrendsClient([_HttpFailure(429)])
    provider = PytrendsGoogleTrendsProvider(
        client_factory=lambda: client,
        retries=0,
    )

    with pytest.raises(GoogleTrendsRateLimitError, match="rate limited") as error:
        provider.fetch_trending(geo="US", limit=1)

    assert error.value.error_code == "rate_limited"


def test_pytrends_transient_failure_retries_with_backoff() -> None:
    client = _PytrendsClient([ConnectionError("temporary")])
    delays: list[float] = []
    provider = PytrendsGoogleTrendsProvider(
        client_factory=lambda: client,
        retries=1,
        backoff_seconds=0.5,
        sleeper=delays.append,
    )

    result = provider.fetch_trending(geo="US", limit=1)

    assert result[0]["query"] == "Ancient Egypt"
    assert client.calls == 2
    assert delays == [0.5]


def test_fixture_provider_is_deterministic() -> None:
    provider = FixtureGoogleTrendsProvider()

    first = provider.fetch_trending(geo="US", limit=2)
    second = provider.fetch_trending(geo="US", limit=2)

    assert first == second
    assert provider.provider_name == "fixture"


def test_unavailable_google_does_not_stop_youtube_or_persist_fake_signals(
    session: Any,
) -> None:
    client = _PytrendsClient([_HttpFailure(404)])
    google = GoogleTrendsConnector(
        provider=PytrendsGoogleTrendsProvider(
            client_factory=lambda: client,
            retries=2,
            sleeper=lambda _: None,
        )
    )
    registry = ConnectorRegistry()
    registry.register("google_trends", google)
    registry.register("youtube", _YouTubeFixtureConnector())

    report = ConnectorOrchestrator(
        registry=registry,
        session_factory=lambda: session,
    ).run(enabled_connectors=("google_trends", "youtube"))

    google_report, youtube_report = report.connector_reports
    assert google_report.status == "unavailable"
    assert google_report.error_code == "provider_unavailable"
    assert google_report.items_fetched == 0
    assert youtube_report.status == "success"
    assert youtube_report.items_processed == 1
    assert ContentRepository(session).get("youtube:provider-test") is not None
    assert {signal.source for signal in TrendSignalRepository(session).list(10, 0)} == {
        "youtube"
    }


def test_latest_unavailable_run_overrides_old_successful_observation() -> None:
    ConnectorStatusStore.clear_local()
    store = ConnectorStatusStore(use_redis=False)
    timestamp = datetime.now(UTC)
    store.record(
        ConnectorExecutionReport(
            connector_name="google_trends",
            status="success",
            items_fetched=1,
            items_processed=1,
            items_failed=0,
            decisions_created=1,
            duration_ms=1,
            provider="pytrends",
            provider_experimental=True,
        ),
        completed_at=timestamp,
    )
    store.record(
        ConnectorExecutionReport(
            connector_name="google_trends",
            status="unavailable",
            items_fetched=0,
            items_processed=0,
            items_failed=0,
            decisions_created=0,
            duration_ms=1,
            errors=("Experimental pytrends provider is unavailable (HTTP 404).",),
            provider="pytrends",
            provider_experimental=True,
            error_code="provider_unavailable",
        ),
        completed_at=timestamp,
    )

    google = store.list_statuses()[0]

    assert google.status == "unavailable"
    assert google.last_success_at == timestamp
    assert google.error_code == "provider_unavailable"
    ConnectorStatusStore.clear_local()


def test_connector_status_api_serializes_runtime_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = ConnectorRuntimeStatus(
        connector_name="google_trends",
        status="unavailable",
        enabled=True,
        provider="pytrends",
        provider_experimental=True,
        last_run_at=datetime(2026, 1, 1, tzinfo=UTC),
        last_success_at=None,
        error_code="provider_unavailable",
        message="Experimental pytrends provider is unavailable (HTTP 404).",
    )
    monkeypatch.setattr(
        ConnectorStatusStore,
        "list_statuses",
        lambda self: (runtime,),
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/connectors/status")

    assert response.status_code == 200
    assert response.json()[0]["status"] == "unavailable"
    assert response.json()[0]["provider_experimental"] is True
