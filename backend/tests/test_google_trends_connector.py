"""Google Trends connector tests using pytrends-compatible test doubles."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from backend.app.connectors.google_trends import (
    DAILY_TRENDS,
    INTEREST_OVER_TIME,
    RELATED_QUERIES,
    RELATED_TOPICS,
    GoogleTrendsBadRequestError,
    GoogleTrendsConnector,
    GoogleTrendsRateLimitError,
)
from backend.app.connectors.registry import ConnectorRegistry
from backend.app.repositories.trend_signal import TrendSignalRepository
from backend.app.services.connector_orchestrator import ConnectorOrchestrator

NOW = datetime(2026, 1, 2, 12, 30, tzinfo=UTC)


class Values:
    def __init__(self, rows: list[list[Any]]) -> None:
        self._rows = rows

    def tolist(self) -> list[list[Any]]:
        return self._rows


class Frame:
    def __init__(
        self,
        records: list[dict[str, Any]] | None = None,
        *,
        values: list[list[Any]] | None = None,
        indexed_rows: list[tuple[datetime, dict[str, Any]]] | None = None,
    ) -> None:
        self._records = records or []
        self._indexed_rows = indexed_rows or []
        self.values = Values(values or [])
        sample = self._records[0] if self._records else {}
        if self._indexed_rows:
            sample = self._indexed_rows[0][1]
        self.columns = tuple(sample)
        self.empty = not (self._records or values or self._indexed_rows)

    def to_dict(self, orient: str) -> list[dict[str, Any]]:
        assert orient == "records"
        return self._records

    def iterrows(self) -> Any:
        yield from self._indexed_rows


class FakePytrends:
    def __init__(self) -> None:
        self.daily: Frame = Frame(values=[["AI video tools"], ["Ancient Egypt"]])
        self.interest: Frame = Frame()
        self.query_response: dict[str, Any] = {}
        self.topic_response: dict[str, Any] = {}
        self.failures: list[Exception] = []
        self.daily_calls = 0
        self.payloads: list[dict[str, Any]] = []

    def _maybe_fail(self) -> None:
        if self.failures:
            raise self.failures.pop(0)

    def trending_searches(self, pn: str) -> Frame:
        self.daily_calls += 1
        assert pn == "united_states"
        self._maybe_fail()
        return self.daily

    def build_payload(
        self, kw_list: list[str], cat: int, timeframe: str, geo: str
    ) -> None:
        self._maybe_fail()
        self.payloads.append(
            {"kw_list": kw_list, "cat": cat, "timeframe": timeframe, "geo": geo}
        )

    def interest_over_time(self) -> Frame:
        self._maybe_fail()
        return self.interest

    def related_queries(self) -> dict[str, Any]:
        self._maybe_fail()
        return self.query_response

    def related_topics(self) -> dict[str, Any]:
        self._maybe_fail()
        return self.topic_response


def connector(client: FakePytrends, **kwargs: Any) -> GoogleTrendsConnector:
    return GoogleTrendsConnector(
        client_factory=lambda: client,
        now=lambda: NOW,
        sleeper=kwargs.pop("sleeper", lambda _: None),
        **kwargs,
    )


def test_successful_daily_fetch_and_normalization() -> None:
    client = FakePytrends()
    google = connector(client)

    records = google.fetch(geo="us", limit=2)
    signal = google.normalize(records[0])

    assert [record["title"] for record in records] == [
        "AI video tools",
        "Ancient Egypt",
    ]
    assert signal.source == "google_trends"
    assert signal.score == 1.0
    assert signal.confidence == 0.96
    assert signal.timestamp == datetime(2026, 1, 2, tzinfo=UTC)


def test_empty_result_is_returned_without_error() -> None:
    client = FakePytrends()
    client.daily = Frame()

    assert connector(client).fetch() == []


def test_temporary_failure_retries_with_exponential_backoff() -> None:
    client = FakePytrends()
    client.failures = [ConnectionError("temporary"), TimeoutError("slow")]
    delays: list[float] = []

    records = connector(
        client, retries=2, backoff_seconds=0.25, sleeper=delays.append
    ).fetch(limit=1)

    assert len(records) == 1
    assert client.daily_calls == 3
    assert delays == [0.25, 0.5]


def test_rate_limit_is_retried_then_reported_cleanly() -> None:
    client = FakePytrends()

    class RateLimited(Exception):
        response = type("Response", (), {"status_code": 429})()

    client.failures = [RateLimited(), RateLimited()]
    delays: list[float] = []

    with pytest.raises(GoogleTrendsRateLimitError, match="rate limit"):
        connector(client, retries=1, backoff_seconds=1, sleeper=delays.append).fetch()

    assert delays == [1]
    assert client.daily_calls == 2


def test_bad_request_is_not_retried() -> None:
    client = FakePytrends()

    class BadRequest(Exception):
        response = type("Response", (), {"status_code": 400})()

    client.failures = [BadRequest()]
    delays: list[float] = []

    with pytest.raises(GoogleTrendsBadRequestError, match="HTTP 400"):
        connector(client, retries=3, sleeper=delays.append).fetch()

    assert delays == []
    assert client.daily_calls == 1


def test_interest_over_time_honors_filters() -> None:
    client = FakePytrends()
    client.interest = Frame(
        indexed_rows=[
            (datetime(2026, 1, 1), {"AI": 30, "isPartial": False}),
            (datetime(2026, 1, 2), {"AI": 75, "isPartial": False}),
        ]
    )

    records = connector(client).fetch(
        trend_type=INTEREST_OVER_TIME,
        query="AI",
        geo="EG",
        timeframe="today 1-m",
        category=5,
    )
    signal = connector(client).normalize(records[0])

    assert client.payloads == [
        {"kw_list": ["AI"], "cat": 5, "timeframe": "today 1-m", "geo": "EG"}
    ]
    assert signal.score == 0.75
    assert len(signal.metadata["timeline"]) == 2


@pytest.mark.parametrize(
    ("trend_type", "response_attribute", "metadata_key"),
    [
        (RELATED_QUERIES, "query_response", "related_queries"),
        (RELATED_TOPICS, "topic_response", "related_topics"),
    ],
)
def test_related_views_are_supported(
    trend_type: str, response_attribute: str, metadata_key: str
) -> None:
    client = FakePytrends()
    setattr(
        client,
        response_attribute,
        {
            "AI": {
                "top": Frame(records=[{"query": "AI tools", "value": 88}]),
                "rising": Frame(records=[{"query": "AI video", "value": "Breakout"}]),
            }
        },
    )

    records = connector(client).fetch(trend_type=trend_type, query="AI", limit=2)
    signals = [connector(client).normalize(record) for record in records]

    assert [signal.score for signal in signals] == [0.88, 1.0]
    assert signals[0].metadata[metadata_key] == ["AI tools"]


def test_metadata_is_complete() -> None:
    client = FakePytrends()
    raw = connector(client).fetch(limit=1)[0]

    metadata = connector(client).normalize(raw).metadata

    assert metadata == {
        "signal_id": raw["id"],
        "trend_type": DAILY_TRENDS,
        "region": "US",
        "timeframe": "today 7-d",
        "interest_score": 100.0,
        "related_queries": [],
        "related_topics": [],
        "source_url": raw["source_url"],
        "category": 0,
        "language": "en-US",
        "provider": "pytrends",
        "provider_experimental": True,
    }


def test_ids_are_deterministic_for_identical_results() -> None:
    client = FakePytrends()
    google = connector(client)

    first = google.fetch(limit=2)
    second = google.fetch(limit=2)

    assert [item["id"] for item in first] == [item["id"] for item in second]


def test_related_ids_are_deterministic_for_identical_results() -> None:
    client = FakePytrends()
    client.query_response = {
        "AI": {"top": Frame(records=[{"query": "AI tools", "value": 88}])}
    }
    moments = iter(
        [
            datetime(2026, 1, 2, 9, tzinfo=UTC),
            datetime(2026, 1, 2, 18, tzinfo=UTC),
        ]
    )
    google = GoogleTrendsConnector(
        client_factory=lambda: client,
        now=lambda: next(moments),
        sleeper=lambda _: None,
    )

    first = google.fetch(trend_type=RELATED_QUERIES, query="AI")
    second = google.fetch(trend_type=RELATED_QUERIES, query="AI")

    assert first[0]["id"] == second[0]["id"]


def test_invalid_inputs_fail_before_pytrends_is_called() -> None:
    client = FakePytrends()
    google = connector(client)

    with pytest.raises(GoogleTrendsBadRequestError, match="query is required"):
        google.fetch(trend_type=RELATED_QUERIES)
    with pytest.raises(GoogleTrendsBadRequestError, match="limit"):
        google.fetch(limit=1000)

    assert client.daily_calls == 0


def test_connector_orchestrator_persists_google_signal_as_active(session: Any) -> None:
    client = FakePytrends()
    registry = ConnectorRegistry()
    registry.register("google_trends", connector(client))

    report = ConnectorOrchestrator(
        registry=registry, session_factory=lambda: session
    ).run(
        {"google_trends": {"limit": 1}},
        enabled_connectors=("google_trends",),
    )

    connector_report = report.connector_reports[0]
    assert connector_report.status == "success"
    assert connector_report.items_processed == 1
    assert connector_report.decisions_created == 1
    assert TrendSignalRepository(session).list(10, 0)[0].source == "google_trends"


def test_rate_limit_never_crashes_connector_orchestrator(session: Any) -> None:
    client = FakePytrends()
    client.failures = [GoogleTrendsRateLimitError("limited")]
    registry = ConnectorRegistry()
    registry.register("google_trends", connector(client, retries=0))

    report = ConnectorOrchestrator(
        registry=registry, session_factory=lambda: session
    ).run(enabled_connectors=("google_trends",))

    assert report.connector_reports[0].status == "degraded"
    assert report.connector_reports[0].error_code == "rate_limited"
    assert report.connector_reports[0].errors == ("limited",)
