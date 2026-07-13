"""Provider boundary for Google Trends transports."""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any, Protocol

from pytrends.request import TrendReq

from backend.app.connectors.errors import (
    ConnectorConfigurationRequiredError,
    ConnectorDisabledError,
    ConnectorProviderUnavailableError,
    ConnectorRateLimitError,
    ConnectorTransientError,
)

_DAILY_REGIONS = {
    "AR": "argentina",
    "AU": "australia",
    "AT": "austria",
    "BE": "belgium",
    "BR": "brazil",
    "CA": "canada",
    "CL": "chile",
    "CO": "colombia",
    "CZ": "czech_republic",
    "DK": "denmark",
    "EG": "egypt",
    "FI": "finland",
    "FR": "france",
    "DE": "germany",
    "GR": "greece",
    "HK": "hong_kong",
    "HU": "hungary",
    "IN": "india",
    "ID": "indonesia",
    "IE": "ireland",
    "IL": "israel",
    "IT": "italy",
    "JP": "japan",
    "KE": "kenya",
    "MY": "malaysia",
    "MX": "mexico",
    "NL": "netherlands",
    "NZ": "new_zealand",
    "NG": "nigeria",
    "NO": "norway",
    "PH": "philippines",
    "PL": "poland",
    "PT": "portugal",
    "RO": "romania",
    "RU": "russia",
    "SA": "saudi_arabia",
    "SG": "singapore",
    "ZA": "south_africa",
    "KR": "south_korea",
    "ES": "spain",
    "SE": "sweden",
    "CH": "switzerland",
    "TW": "taiwan",
    "TH": "thailand",
    "TR": "turkey",
    "UA": "ukraine",
    "GB": "united_kingdom",
    "US": "united_states",
    "VN": "vietnam",
}


class GoogleTrendsProviderError(RuntimeError):
    """Base class for Google Trends provider errors."""


class GoogleTrendsProviderUnavailableError(
    ConnectorProviderUnavailableError, GoogleTrendsProviderError
):
    """Provider endpoint or access mode is permanently unavailable."""


class GoogleTrendsRateLimitError(ConnectorRateLimitError, GoogleTrendsProviderError):
    """Provider temporarily rejected the request due to rate limiting."""


class GoogleTrendsTemporaryError(ConnectorTransientError, GoogleTrendsProviderError):
    """Provider or network is temporarily unavailable."""


class GoogleTrendsConfigurationRequiredError(
    ConnectorConfigurationRequiredError, GoogleTrendsProviderError
):
    """Official provider access has not been configured."""


class GoogleTrendsDisabledError(ConnectorDisabledError, GoogleTrendsProviderError):
    """Google Trends was intentionally disabled."""


class GoogleTrendsBadRequestError(ValueError, GoogleTrendsProviderError):
    """Provider rejected invalid request parameters."""


class GoogleTrendsProvider(Protocol):
    """Transport-neutral Google Trends provider contract."""

    provider_name: str
    experimental: bool

    def fetch_trending(self, *, geo: str, limit: int) -> list[Mapping[str, Any]]: ...

    def interest_over_time(
        self, *, query: str, geo: str, timeframe: str, category: int
    ) -> list[Mapping[str, Any]]: ...

    def related_queries(
        self, *, query: str, geo: str, timeframe: str, category: int, limit: int
    ) -> list[Mapping[str, Any]]: ...

    def related_topics(
        self, *, query: str, geo: str, timeframe: str, category: int, limit: int
    ) -> list[Mapping[str, Any]]: ...


class PytrendsClient(Protocol):
    """Small pytrends surface used by the experimental provider."""

    def trending_searches(self, pn: str) -> Any: ...

    def build_payload(
        self, kw_list: list[str], cat: int, timeframe: str, geo: str
    ) -> None: ...

    def interest_over_time(self) -> Any: ...

    def related_queries(self) -> Mapping[str, Any]: ...

    def related_topics(self) -> Mapping[str, Any]: ...


class DisabledGoogleTrendsProvider:
    """Explicit disabled provider used when the connector is switched off."""

    provider_name = "disabled"
    experimental = False

    def fetch_trending(self, *, geo: str, limit: int) -> list[Mapping[str, Any]]:
        raise GoogleTrendsDisabledError("Google Trends connector is disabled.")

    def interest_over_time(
        self, *, query: str, geo: str, timeframe: str, category: int
    ) -> list[Mapping[str, Any]]:
        raise GoogleTrendsDisabledError("Google Trends connector is disabled.")

    def related_queries(
        self, *, query: str, geo: str, timeframe: str, category: int, limit: int
    ) -> list[Mapping[str, Any]]:
        raise GoogleTrendsDisabledError("Google Trends connector is disabled.")

    def related_topics(
        self, *, query: str, geo: str, timeframe: str, category: int, limit: int
    ) -> list[Mapping[str, Any]]:
        raise GoogleTrendsDisabledError("Google Trends connector is disabled.")


class OfficialGoogleTrendsProvider:
    """Typed official-provider stub pending approved API access."""

    provider_name = "official"
    experimental = False

    def __init__(
        self,
        *,
        project_id: str | None = None,
        credentials_file: str | None = None,
        api_endpoint: str | None = None,
        access_enabled: bool = False,
    ) -> None:
        self.project_id = _clean(project_id)
        self.credentials_file = _clean(credentials_file)
        self.api_endpoint = _clean(api_endpoint)
        self.access_enabled = access_enabled

    @property
    def is_configured(self) -> bool:
        """Return whether approved-access configuration was supplied."""
        return bool(
            self.access_enabled
            and self.project_id
            and self.credentials_file
            and self.api_endpoint
        )

    def fetch_trending(self, *, geo: str, limit: int) -> list[Mapping[str, Any]]:
        self._raise_unavailable()

    def interest_over_time(
        self, *, query: str, geo: str, timeframe: str, category: int
    ) -> list[Mapping[str, Any]]:
        self._raise_unavailable()

    def related_queries(
        self, *, query: str, geo: str, timeframe: str, category: int, limit: int
    ) -> list[Mapping[str, Any]]:
        self._raise_unavailable()

    def related_topics(
        self, *, query: str, geo: str, timeframe: str, category: int, limit: int
    ) -> list[Mapping[str, Any]]:
        self._raise_unavailable()

    def _raise_unavailable(self) -> None:
        if not self.is_configured:
            raise GoogleTrendsConfigurationRequiredError(
                "Official Google Trends API access is not configured."
            )
        raise GoogleTrendsProviderUnavailableError(
            "Official Google Trends API access is configured, but this build "
            "does not include an approved-access client implementation."
        )


class PytrendsGoogleTrendsProvider:
    """Experimental provider wrapping all unofficial pytrends calls."""

    provider_name = "pytrends"
    experimental = True

    def __init__(
        self,
        client_factory: Callable[[], PytrendsClient] | None = None,
        *,
        language: str = "en-US",
        retries: int = 2,
        backoff_seconds: float = 1.0,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if retries < 0:
            raise ValueError("retries cannot be negative")
        if backoff_seconds < 0:
            raise ValueError("backoff_seconds cannot be negative")
        self._language = language
        self._client_factory = client_factory or (
            lambda: TrendReq(hl=self._language, tz=0, timeout=(5, 15))
        )
        self._retries = retries
        self._backoff_seconds = backoff_seconds
        self._sleeper = sleeper

    def fetch_trending(self, *, geo: str, limit: int) -> list[Mapping[str, Any]]:
        region = _DAILY_REGIONS.get(geo)
        if region is None:
            raise GoogleTrendsBadRequestError(
                f"Daily trending searches do not support region {geo}"
            )

        def operation(client: PytrendsClient) -> list[Mapping[str, Any]]:
            frame = client.trending_searches(pn=region)
            return [
                {"query": str(value).strip(), "rank": rank}
                for rank, value in enumerate(_first_column_values(frame)[:limit], 1)
                if str(value).strip()
            ]

        return self._execute(operation)

    def interest_over_time(
        self, *, query: str, geo: str, timeframe: str, category: int
    ) -> list[Mapping[str, Any]]:
        def operation(client: PytrendsClient) -> list[Mapping[str, Any]]:
            client.build_payload([query], cat=category, timeframe=timeframe, geo=geo)
            frame = client.interest_over_time()
            if _is_empty(frame) or query not in getattr(frame, "columns", ()):
                return []
            return [
                {"timestamp": timestamp, "interest_score": row[query]}
                for timestamp, row in frame.iterrows()
                if row[query] is not None
            ]

        return self._execute(operation)

    def related_queries(
        self, *, query: str, geo: str, timeframe: str, category: int, limit: int
    ) -> list[Mapping[str, Any]]:
        return self._related(
            query=query,
            geo=geo,
            timeframe=timeframe,
            category=category,
            limit=limit,
            topics=False,
        )

    def related_topics(
        self, *, query: str, geo: str, timeframe: str, category: int, limit: int
    ) -> list[Mapping[str, Any]]:
        return self._related(
            query=query,
            geo=geo,
            timeframe=timeframe,
            category=category,
            limit=limit,
            topics=True,
        )

    def _related(
        self,
        *,
        query: str,
        geo: str,
        timeframe: str,
        category: int,
        limit: int,
        topics: bool,
    ) -> list[Mapping[str, Any]]:
        def operation(client: PytrendsClient) -> list[Mapping[str, Any]]:
            client.build_payload([query], cat=category, timeframe=timeframe, geo=geo)
            response = client.related_topics() if topics else client.related_queries()
            groups = response.get(query) if response else None
            if not isinstance(groups, Mapping):
                return []
            results: list[Mapping[str, Any]] = []
            for relationship in ("top", "rising"):
                frame = groups.get(relationship)
                for row in _records(frame):
                    title = str(
                        row.get("query") or row.get("topic_title") or ""
                    ).strip()
                    if not title:
                        continue
                    results.append(
                        {
                            "title": title,
                            "value": row.get("value", 0),
                            "relationship": relationship,
                        }
                    )
                    if len(results) >= limit:
                        return results
            return results

        return self._execute(operation)

    def _execute(
        self, operation: Callable[[PytrendsClient], list[Mapping[str, Any]]]
    ) -> list[Mapping[str, Any]]:
        for attempt in range(self._retries + 1):
            try:
                return operation(self._client_factory())
            except GoogleTrendsBadRequestError:
                raise
            except Exception as exc:
                converted = self._classify_error(exc)
                if isinstance(
                    converted,
                    (GoogleTrendsProviderUnavailableError, GoogleTrendsBadRequestError),
                ):
                    raise converted from exc
                if attempt >= self._retries:
                    raise converted from exc
                self._sleeper(self._backoff_seconds * (2**attempt))
        return []  # pragma: no cover

    @staticmethod
    def _classify_error(exc: Exception) -> Exception:
        if isinstance(
            exc,
            (
                GoogleTrendsProviderUnavailableError,
                GoogleTrendsRateLimitError,
                GoogleTrendsTemporaryError,
                GoogleTrendsBadRequestError,
            ),
        ):
            return exc
        response = getattr(exc, "response", None)
        status = getattr(response, "status_code", None)
        name = type(exc).__name__.lower()
        if status == 404:
            return GoogleTrendsProviderUnavailableError(
                "Experimental pytrends provider is unavailable (HTTP 404)."
            )
        if status == 429 or "toomanyrequests" in name or "ratelimit" in name:
            return GoogleTrendsRateLimitError(
                "Experimental pytrends provider is rate limited."
            )
        if status is not None and 400 <= status < 500:
            return GoogleTrendsBadRequestError(
                f"Google Trends provider rejected the request with HTTP {status}."
            )
        return GoogleTrendsTemporaryError(
            "Experimental pytrends provider is temporarily unavailable."
        )


class FixtureGoogleTrendsProvider:
    """Deterministic provider for tests; never selected by production config."""

    provider_name = "fixture"
    experimental = False

    def __init__(
        self,
        *,
        trending: tuple[str, ...] = ("Ancient Egypt", "AI video tools"),
        interest: tuple[tuple[datetime, float], ...] = (
            (datetime(2026, 1, 1, tzinfo=UTC), 40.0),
            (datetime(2026, 1, 2, tzinfo=UTC), 70.0),
        ),
        queries: tuple[tuple[str, float, str], ...] = (
            ("Ancient Egypt documentary", 80.0, "top"),
        ),
        topics: tuple[tuple[str, float, str], ...] = (("History", 75.0, "top"),),
    ) -> None:
        self._trending = trending
        self._interest = interest
        self._queries = queries
        self._topics = topics

    def fetch_trending(self, *, geo: str, limit: int) -> list[Mapping[str, Any]]:
        return [
            {"query": query, "rank": rank}
            for rank, query in enumerate(self._trending[:limit], 1)
        ]

    def interest_over_time(
        self, *, query: str, geo: str, timeframe: str, category: int
    ) -> list[Mapping[str, Any]]:
        return [
            {"timestamp": timestamp, "interest_score": score}
            for timestamp, score in self._interest
        ]

    def related_queries(
        self, *, query: str, geo: str, timeframe: str, category: int, limit: int
    ) -> list[Mapping[str, Any]]:
        return self._related(self._queries, limit)

    def related_topics(
        self, *, query: str, geo: str, timeframe: str, category: int, limit: int
    ) -> list[Mapping[str, Any]]:
        return self._related(self._topics, limit)

    @staticmethod
    def _related(
        values: tuple[tuple[str, float, str], ...], limit: int
    ) -> list[Mapping[str, Any]]:
        return [
            {"title": title, "value": value, "relationship": relationship}
            for title, value, relationship in values[:limit]
        ]


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _is_empty(frame: Any) -> bool:
    return frame is None or bool(getattr(frame, "empty", False))


def _first_column_values(frame: Any) -> list[Any]:
    if _is_empty(frame):
        return []
    values = getattr(frame, "values", None)
    if values is not None:
        return [row[0] for row in values.tolist() if row]
    records = _records(frame)
    return [next(iter(record.values())) for record in records if record]


def _records(frame: Any) -> list[dict[str, Any]]:
    if frame is None or bool(getattr(frame, "empty", False)):
        return []
    converter = getattr(frame, "to_dict", None)
    if converter is None:
        return []
    return [dict(record) for record in converter("records")]
