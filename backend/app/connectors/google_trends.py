"""Provider-backed Google Trends connector implementation."""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode
from uuid import NAMESPACE_URL, uuid5

from backend.app.connectors.base import BaseConnector
from backend.app.connectors.google_trends_providers import (
    GoogleTrendsBadRequestError,
    GoogleTrendsConfigurationRequiredError,
    GoogleTrendsDisabledError,
    GoogleTrendsProvider,
    GoogleTrendsProviderError,
    GoogleTrendsProviderUnavailableError,
    GoogleTrendsRateLimitError,
    GoogleTrendsTemporaryError,
    PytrendsClient,
    PytrendsGoogleTrendsProvider,
)
from backend.app.connectors.metadata import (
    ConnectorCapabilities,
    ConnectorCapability,
    ConnectorMetadata,
)
from backend.app.domain.trend_signal import TrendSignal

DAILY_TRENDS = "daily_trending_searches"
INTEREST_OVER_TIME = "interest_over_time"
RELATED_QUERIES = "related_queries"
RELATED_TOPICS = "related_topics"
SUPPORTED_TREND_TYPES = frozenset(
    {DAILY_TRENDS, INTEREST_OVER_TIME, RELATED_QUERIES, RELATED_TOPICS}
)

# Backward-compatible error name retained for callers importing the old base class.
GoogleTrendsError = GoogleTrendsProviderError


class GoogleTrendsConnector(BaseConnector[TrendSignal]):
    """Normalize data supplied by a configured Google Trends provider."""

    def __init__(
        self,
        provider: GoogleTrendsProvider | None = None,
        *,
        client_factory: Callable[[], PytrendsClient] | None = None,
        default_geo: str = "US",
        default_timeframe: str = "today 7-d",
        max_results: int = 10,
        retries: int = 2,
        backoff_seconds: float = 1.0,
        language: str = "en-US",
        sleeper: Callable[[float], None] = time.sleep,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        if max_results < 1:
            raise ValueError("max_results must be positive")
        self._provider = provider or PytrendsGoogleTrendsProvider(
            client_factory=client_factory,
            language=language,
            retries=retries,
            backoff_seconds=backoff_seconds,
            sleeper=sleeper,
        )
        self._default_geo = self._validate_geo(default_geo)
        self._default_timeframe = self._validate_timeframe(default_timeframe)
        self._max_results = max_results
        self._language = language
        self._now = now or (lambda: datetime.now(UTC))

    @property
    def provider_name(self) -> str:
        """Expose provider identity for reports and dashboard status."""
        return self._provider.provider_name

    @property
    def provider_experimental(self) -> bool:
        """Return whether the selected provider uses unofficial APIs."""
        return self._provider.experimental

    @property
    def is_enabled(self) -> bool:
        return self.provider_name != "disabled"

    @property
    def metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            name="google_trends",
            display_name="Google Trends",
            version="2.0.0",
            provider=self.provider_name,
            provider_experimental=self.provider_experimental,
            description="Search-interest trends and related topic discovery.",
            capabilities=ConnectorCapabilities.of(
                ConnectorCapability.TRENDING,
                ConnectorCapability.HISTORICAL,
                ConnectorCapability.AUDIENCE_SIGNALS,
                ConnectorCapability.GEO_FILTERING,
                ConnectorCapability.DATE_FILTERING,
                ConnectorCapability.TOPIC_MONITORING,
                ConnectorCapability.FORECAST_INPUT,
                ConnectorCapability.CONTENT_DISCOVERY,
            ),
            supports_live_access=self.provider_name in {"pytrends", "official"},
            supports_fixture_access=True,
        )

    def fetch(self, **kwargs: Any) -> list[Mapping[str, Any]]:
        """Fetch one supported trend view through the configured provider."""
        options = self._fetch_options(kwargs)
        return self._fetch_provider(**options)

    def normalize(self, raw_content: Mapping[str, Any]) -> TrendSignal:
        """Convert a provider-neutral record into the shared signal contract."""
        self.validate(raw_content)
        title = str(raw_content["title"]).strip()
        region = str(raw_content["geo"])
        timestamp = self._as_datetime(raw_content["published_at"])
        interest_score = self._score(raw_content["interest_score"])
        trend_type = str(raw_content["trend_type"])
        rank = int(raw_content.get("rank", 1))
        confidence = self._confidence(trend_type, rank, raw_content)
        metadata = {
            "signal_id": str(raw_content["id"]),
            "trend_type": trend_type,
            "region": region,
            "timeframe": str(raw_content["timeframe"]),
            "interest_score": interest_score,
            "related_queries": list(raw_content.get("related_queries", [])),
            "related_topics": list(raw_content.get("related_topics", [])),
            "source_url": str(raw_content["source_url"]),
            "category": int(raw_content["category"]),
            "language": str(raw_content["language"]),
            "provider": str(raw_content.get("provider", self.provider_name)),
            "provider_experimental": bool(
                raw_content.get("provider_experimental", self.provider_experimental)
            ),
        }
        if "timeline" in raw_content:
            metadata["timeline"] = list(raw_content["timeline"])
        return TrendSignal(
            source="google_trends",
            score=round(interest_score / 100.0, 4),
            confidence=confidence,
            timestamp=timestamp,
            reason=(
                f"Google Trends {trend_type.replace('_', ' ')} identified "
                f"increasing search interest for {title} in {region}."
            ),
            metadata=metadata,
        )

    def validate(self, raw_content: Mapping[str, Any]) -> None:
        """Validate a provider-neutral record before ingestion."""
        required = (
            "id",
            "query",
            "title",
            "published_at",
            "geo",
            "trend_type",
            "timeframe",
            "interest_score",
            "source_url",
            "category",
            "language",
        )
        missing = [field for field in required if field not in raw_content]
        if missing:
            raise ValueError(
                "Google Trends payload is missing required fields: "
                + ", ".join(missing)
            )
        if not str(raw_content["title"]).strip():
            raise ValueError("Google Trends payload title cannot be empty")
        if str(raw_content["trend_type"]) not in SUPPORTED_TREND_TYPES:
            raise ValueError("Google Trends payload has an unsupported trend_type")
        self._score(raw_content["interest_score"])
        self._as_datetime(raw_content["published_at"])

    def _fetch_provider(
        self,
        *,
        trend_type: str,
        query: str | None,
        geo: str,
        timeframe: str,
        category: int,
        limit: int,
        language: str,
    ) -> list[Mapping[str, Any]]:
        if trend_type == DAILY_TRENDS:
            values = self._provider.fetch_trending(geo=geo, limit=limit)
            return self._daily(values, geo, timeframe, category, limit, language)

        assert query is not None
        if trend_type == INTEREST_OVER_TIME:
            values = self._provider.interest_over_time(
                query=query,
                geo=geo,
                timeframe=timeframe,
                category=category,
            )
            return self._interest(values, query, geo, timeframe, category, language)
        values = (
            self._provider.related_queries(
                query=query,
                geo=geo,
                timeframe=timeframe,
                category=category,
                limit=limit,
            )
            if trend_type == RELATED_QUERIES
            else self._provider.related_topics(
                query=query,
                geo=geo,
                timeframe=timeframe,
                category=category,
                limit=limit,
            )
        )
        return self._related(
            values,
            query=query,
            trend_type=trend_type,
            geo=geo,
            timeframe=timeframe,
            category=category,
            limit=limit,
            language=language,
        )

    def _daily(
        self,
        values: list[Mapping[str, Any]],
        geo: str,
        timeframe: str,
        category: int,
        limit: int,
        language: str,
    ) -> list[Mapping[str, Any]]:
        default_timestamp = self._day_timestamp()
        results: list[Mapping[str, Any]] = []
        for fallback_rank, item in enumerate(values[:limit], 1):
            title = str(item.get("query") or item.get("title") or "").strip()
            if not title:
                continue
            rank = int(item.get("rank", fallback_rank))
            score = self._score(
                item.get("interest_score", max(1, 100 - ((rank - 1) * 5)))
            )
            timestamp = self._as_datetime(item.get("timestamp", default_timestamp))
            results.append(
                self._record(
                    query=title,
                    title=title,
                    trend_type=DAILY_TRENDS,
                    geo=geo,
                    timeframe=timeframe,
                    category=category,
                    language=language,
                    timestamp=timestamp,
                    interest_score=score,
                    rank=rank,
                )
            )
        return results

    def _interest(
        self,
        values: list[Mapping[str, Any]],
        query: str,
        geo: str,
        timeframe: str,
        category: int,
        language: str,
    ) -> list[Mapping[str, Any]]:
        timeline = [
            {
                "timestamp": self._as_datetime(item["timestamp"]).isoformat(),
                "interest_score": self._score(item["interest_score"]),
            }
            for item in values
            if item.get("timestamp") is not None
            and item.get("interest_score") is not None
        ]
        if not timeline:
            return []
        latest = timeline[-1]
        record = self._record(
            query=query,
            title=query,
            trend_type=INTEREST_OVER_TIME,
            geo=geo,
            timeframe=timeframe,
            category=category,
            language=language,
            timestamp=self._as_datetime(latest["timestamp"]),
            interest_score=latest["interest_score"],
            rank=1,
        )
        return [{**record, "timeline": timeline}]

    def _related(
        self,
        values: list[Mapping[str, Any]],
        *,
        query: str,
        trend_type: str,
        geo: str,
        timeframe: str,
        category: int,
        limit: int,
        language: str,
    ) -> list[Mapping[str, Any]]:
        timestamp = self._day_timestamp()
        results: list[Mapping[str, Any]] = []
        for item in values[:limit]:
            title = str(item.get("title") or item.get("query") or "").strip()
            if not title:
                continue
            value = item.get("value", 0)
            score = 100 if str(value).lower() == "breakout" else self._score(value)
            relationship = str(item.get("relationship", "top"))
            results.append(
                self._record(
                    query=query,
                    title=title,
                    trend_type=trend_type,
                    geo=geo,
                    timeframe=timeframe,
                    category=category,
                    language=language,
                    timestamp=timestamp,
                    interest_score=score,
                    rank=len(results) + 1,
                    related_queries=[title] if trend_type == RELATED_QUERIES else [],
                    related_topics=[title] if trend_type == RELATED_TOPICS else [],
                )
                | {"relationship": relationship}
            )
        return results

    def _record(
        self,
        *,
        query: str,
        title: str,
        trend_type: str,
        geo: str,
        timeframe: str,
        category: int,
        language: str,
        timestamp: datetime,
        interest_score: float,
        rank: int,
        related_queries: list[str] | None = None,
        related_topics: list[str] | None = None,
    ) -> dict[str, Any]:
        timestamp = self._as_datetime(timestamp)
        source_url = "https://trends.google.com/trends/explore?" + urlencode(
            {"q": query, "geo": geo, "date": timeframe, "cat": category}
        )
        identity = "|".join(
            (
                self.provider_name,
                trend_type,
                query.casefold(),
                title.casefold(),
                geo,
                timeframe,
                str(category),
                timestamp.isoformat(),
            )
        )
        return {
            "id": str(uuid5(NAMESPACE_URL, identity)),
            "query": query,
            "title": title,
            "published_at": timestamp,
            "geo": geo,
            "trend_type": trend_type,
            "timeframe": timeframe,
            "interest_score": interest_score,
            "related_queries": related_queries or [],
            "related_topics": related_topics or [],
            "source_url": source_url,
            "url": source_url,
            "category": category,
            "language": language,
            "rank": rank,
            "source": "google_trends",
            "provider": self.provider_name,
            "provider_experimental": self.provider_experimental,
        }

    def _fetch_options(self, kwargs: Mapping[str, Any]) -> dict[str, Any]:
        trend_type = str(kwargs.get("trend_type", DAILY_TRENDS)).strip().lower()
        if trend_type not in SUPPORTED_TREND_TYPES:
            supported = ", ".join(sorted(SUPPORTED_TREND_TYPES))
            raise GoogleTrendsBadRequestError(
                f"Unsupported trend_type {trend_type!r}; expected one of {supported}"
            )
        query_value = kwargs.get("query", kwargs.get("keyword"))
        query = str(query_value).strip() if query_value is not None else None
        if trend_type != DAILY_TRENDS and not query:
            raise GoogleTrendsBadRequestError(
                f"query is required for trend_type {trend_type}"
            )
        geo = self._validate_geo(str(kwargs.get("geo", self._default_geo)))
        timeframe = self._validate_timeframe(
            str(kwargs.get("timeframe", self._default_timeframe))
        )
        try:
            category = int(kwargs.get("category", 0))
            limit = int(kwargs.get("limit", self._max_results))
        except (TypeError, ValueError) as exc:
            raise GoogleTrendsBadRequestError(
                "category and limit must be integers"
            ) from exc
        if category < 0:
            raise GoogleTrendsBadRequestError("category cannot be negative")
        if limit < 1 or limit > self._max_results:
            raise GoogleTrendsBadRequestError(
                f"limit must be between 1 and {self._max_results}"
            )
        language = str(kwargs.get("language", self._language)).strip()
        if not language:
            raise GoogleTrendsBadRequestError("language cannot be empty")
        return {
            "trend_type": trend_type,
            "query": query,
            "geo": geo,
            "timeframe": timeframe,
            "category": category,
            "limit": limit,
            "language": language,
        }

    def _day_timestamp(self) -> datetime:
        return (
            self._now()
            .astimezone(UTC)
            .replace(hour=0, minute=0, second=0, microsecond=0)
        )

    @staticmethod
    def _validate_geo(value: str) -> str:
        geo = value.strip().upper()
        if not geo or len(geo) > 5 or not geo.replace("-", "").isalpha():
            raise GoogleTrendsBadRequestError("geo must be an ISO region code")
        return geo

    @staticmethod
    def _validate_timeframe(value: str) -> str:
        timeframe = value.strip()
        if not timeframe or len(timeframe) > 64:
            raise GoogleTrendsBadRequestError("timeframe cannot be empty")
        return timeframe

    @staticmethod
    def _score(value: Any) -> float:
        try:
            score = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("interest_score must be numeric") from exc
        if score < 0:
            raise ValueError("interest_score cannot be negative")
        return round(min(score, 100.0), 2)

    @staticmethod
    def _confidence(
        trend_type: str, rank: int, raw_content: Mapping[str, Any]
    ) -> float:
        if trend_type == DAILY_TRENDS:
            return round(max(0.65, 0.96 - ((max(rank, 1) - 1) * 0.02)), 2)
        if trend_type == INTEREST_OVER_TIME:
            points = len(raw_content.get("timeline", []))
            return round(min(0.95, 0.72 + (min(points, 23) * 0.01)), 2)
        return 0.75 if raw_content.get("relationship") == "top" else 0.7

    @staticmethod
    def _as_datetime(value: Any) -> datetime:
        if isinstance(value, datetime):
            result = value
        elif isinstance(value, str):
            result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        elif hasattr(value, "to_pydatetime"):
            result = value.to_pydatetime()
        else:
            raise ValueError("published_at must be an ISO 8601 timestamp or datetime")
        if result.tzinfo is None:
            return result.replace(tzinfo=UTC)
        return result.astimezone(UTC)


__all__ = [
    "DAILY_TRENDS",
    "INTEREST_OVER_TIME",
    "RELATED_QUERIES",
    "RELATED_TOPICS",
    "GoogleTrendsBadRequestError",
    "GoogleTrendsConfigurationRequiredError",
    "GoogleTrendsConnector",
    "GoogleTrendsDisabledError",
    "GoogleTrendsError",
    "GoogleTrendsProviderUnavailableError",
    "GoogleTrendsRateLimitError",
    "GoogleTrendsTemporaryError",
]
