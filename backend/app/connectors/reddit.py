"""Reddit post connector using the official OAuth Data API provider."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from backend.app.connectors.base import BaseConnector
from backend.app.connectors.metadata import (
    ConnectorCapabilities,
    ConnectorCapability,
    ConnectorMetadata,
)
from backend.app.connectors.reddit_providers import RedditProvider
from backend.app.domain.content import Content
from backend.app.domain.trend_signal import TrendSignal

REDDIT_SORTS = frozenset({"relevance", "hot", "top", "new", "comments"})
REDDIT_TIME_FILTERS = frozenset({"hour", "day", "week", "month", "year", "all"})
_SUBREDDIT_PATTERN = re.compile(r"^[A-Za-z0-9_]{2,21}$")


class RedditConnector(BaseConnector[Content]):
    """Normalize Reddit post listings into platform-independent content."""

    _required_fields = (
        "id",
        "name",
        "title",
        "subreddit",
        "created_utc",
        "permalink",
        "query",
        "retrieval_mode",
        "provider",
        "provider_timestamp",
        "rank",
    )

    def __init__(
        self,
        provider: RedditProvider,
        *,
        default_subreddits: Sequence[str] = (),
        default_query: str = "",
        default_sort: str = "hot",
        default_time_filter: str = "week",
        default_limit: int = 25,
    ) -> None:
        self._provider = provider
        self._default_subreddits = self._subreddits(default_subreddits)
        self._default_query = default_query.strip()
        self._default_sort = self._sort(default_sort)
        self._default_time_filter = self._time_filter(default_time_filter)
        if not 1 <= default_limit <= 100:
            raise ValueError("Reddit default limit must be between 1 and 100")
        self._default_limit = default_limit

    @property
    def is_enabled(self) -> bool:
        return self._provider.is_enabled

    @property
    def metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            name="reddit",
            display_name="Reddit",
            version="1.0.0",
            provider=self._provider.provider_name,
            provider_experimental=self._provider.experimental,
            description="OAuth-backed Reddit post discovery and engagement signals.",
            capabilities=ConnectorCapabilities.of(
                ConnectorCapability.SEARCH,
                ConnectorCapability.COMMUNITIES,
                ConnectorCapability.AUTHORS,
                ConnectorCapability.ENGAGEMENT_METRICS,
                ConnectorCapability.KEYWORD_MONITORING,
                ConnectorCapability.TOPIC_MONITORING,
                ConnectorCapability.DATE_FILTERING,
                ConnectorCapability.FORECAST_INPUT,
                ConnectorCapability.CONTENT_DISCOVERY,
            ),
            supports_live_access=True,
            supports_fixture_access=True,
        )

    def diagnostics(self) -> Mapping[str, Any]:
        return self._provider.diagnostics()

    def fetch(self, **kwargs: Any) -> list[Mapping[str, Any]]:
        if not self.is_enabled:
            self._provider.search_posts(
                query="",
                subreddits=(),
                sort=self._default_sort,
                time_filter=self._default_time_filter,
                limit=self._default_limit,
            )
        query = str(kwargs.get("query", self._default_query)).strip()
        subreddits = self._subreddits(
            kwargs.get("subreddits", self._default_subreddits)
        )
        if not query:
            raise ValueError("Reddit query is required for post search")
        sort = self._sort(str(kwargs.get("sort", self._default_sort)))
        time_filter = self._time_filter(
            str(kwargs.get("time_filter", self._default_time_filter))
        )
        limit = int(kwargs.get("limit", self._default_limit))
        if not 1 <= limit <= 100:
            raise ValueError("Reddit limit must be between 1 and 100")
        result = self._provider.search_posts(
            query=query,
            subreddits=subreddits,
            sort=sort,
            time_filter=time_filter,
            limit=limit,
        )
        raw_items: list[Mapping[str, Any]] = []
        for rank, post in enumerate(result.items[:limit], start=1):
            raw_items.append(
                {
                    **dict(post),
                    "query": query,
                    "retrieval_mode": (
                        "subreddit_search" if subreddits else "keyword_search"
                    ),
                    "requested_subreddits": list(subreddits),
                    "sort": sort,
                    "time_filter": time_filter,
                    "rank": rank,
                    "provider": self._provider.provider_name,
                    "provider_timestamp": result.retrieved_at,
                    "fixture_backed": result.fixture_backed,
                    "rate_limit": {
                        "remaining": result.rate_limit.remaining,
                        "used": result.rate_limit.used,
                        "reset_seconds": result.rate_limit.reset_seconds,
                    },
                }
            )
        return raw_items

    def normalize(self, raw_content: Mapping[str, Any]) -> Content:
        self.validate(raw_content)
        published_at = self._timestamp(raw_content["created_utc"])
        provider_timestamp = self._timestamp(raw_content["provider_timestamp"])
        author = self._optional_string(raw_content.get("author")) or "[deleted]"
        score = self._optional_number(raw_content.get("score"))
        comment_count = self._optional_number(raw_content.get("num_comments"))
        upvote_ratio = self._optional_ratio(raw_content.get("upvote_ratio"))
        awards_count = self._optional_number(raw_content.get("total_awards_received"))
        rank = int(raw_content["rank"])
        metrics: dict[str, float] = {"rank": float(rank)}
        for key, value in (
            ("score", score),
            ("comment_count", comment_count),
            ("upvote_ratio", upvote_ratio),
            ("awards_count", awards_count),
        ):
            if value is not None:
                metrics[key] = value

        age_hours = max(
            (provider_timestamp - published_at).total_seconds() / 3600.0, 0.0
        )
        metrics["post_age_hours"] = round(age_hours, 4)
        engagement = self._engagement(score, comment_count, upvote_ratio, rank)
        freshness = round(1.0 / (1.0 + age_hours / 24.0), 4)
        metrics["engagement_rate"] = engagement
        metadata = {
            "source_item_id": str(raw_content["id"]),
            "fullname": str(raw_content["name"]),
            "subreddit": str(raw_content["subreddit"]),
            "query": str(raw_content["query"]),
            "retrieval_mode": str(raw_content["retrieval_mode"]),
            "requested_subreddits": list(raw_content.get("requested_subreddits", [])),
            "sort": str(raw_content.get("sort", "")),
            "time_filter": str(raw_content.get("time_filter", "")),
            "rank": rank,
            "score": score,
            "comment_count": comment_count,
            "upvote_ratio": upvote_ratio,
            "awards_count": awards_count,
            "engagement": engagement,
            "freshness": freshness,
            "source_url": self._permalink(raw_content["permalink"]),
            "outbound_url": self._optional_string(raw_content.get("url")),
            "post_type": self._post_type(raw_content),
            "over_18": bool(raw_content.get("over_18", False)),
            "spoiler": bool(raw_content.get("spoiler", False)),
            "stickied": bool(raw_content.get("stickied", False)),
            "provider": str(raw_content["provider"]),
            "provider_timestamp": provider_timestamp.isoformat(),
            "fixture_backed": bool(raw_content.get("fixture_backed", False)),
            "rate_limit": dict(raw_content.get("rate_limit", {})),
            "signal_type": "DISCUSSION_VELOCITY",
        }
        signal = TrendSignal(
            source="reddit",
            score=engagement,
            confidence=self._confidence(score, comment_count, upvote_ratio),
            timestamp=published_at,
            reason=(
                "Reddit post engagement observed for "
                f"{raw_content['title']} in r/{raw_content['subreddit']}; "
                "this single post does not establish a platform-wide trend."
            ),
            metadata=metadata,
        )
        return Content(
            id=f"reddit:{raw_content['id']}",
            platform="reddit",
            creator_name=author,
            creator_id=author,
            title=str(raw_content["title"]).strip(),
            description=self._excerpt(raw_content.get("selftext")),
            url=metadata["source_url"],
            language=None,
            country=None,
            published_at=published_at,
            duration_seconds=None,
            content_type=metadata["post_type"],
            metrics=metrics,
            analysis={},
            signals=(signal,),
            metadata=metadata,
        )

    def validate(self, raw_content: Mapping[str, Any]) -> None:
        missing = [field for field in self._required_fields if field not in raw_content]
        if missing:
            raise ValueError(
                "Reddit payload is missing required fields: " + ", ".join(missing)
            )
        for field in ("id", "name", "title", "subreddit", "permalink"):
            if not str(raw_content[field]).strip():
                raise ValueError(f"Reddit payload {field} cannot be empty")
        if not str(raw_content["name"]).startswith("t3_"):
            raise ValueError("Reddit payload must describe a post")
        self._timestamp(raw_content["created_utc"])
        self._timestamp(raw_content["provider_timestamp"])
        self._optional_number(raw_content.get("score"))
        self._optional_number(raw_content.get("num_comments"))
        self._optional_number(raw_content.get("total_awards_received"))
        self._optional_ratio(raw_content.get("upvote_ratio"))

    @staticmethod
    def _engagement(
        score: float | None,
        comments: float | None,
        ratio: float | None,
        rank: int,
    ) -> float:
        dimensions = [1.0 / max(rank, 1)]
        if score is not None:
            dimensions.append(score / (score + 100.0) if score >= 0 else 0.0)
        if comments is not None:
            dimensions.append(comments / (comments + 50.0))
        if ratio is not None:
            dimensions.append(ratio)
        return round(sum(dimensions) / len(dimensions), 4)

    @staticmethod
    def _confidence(
        score: float | None, comments: float | None, ratio: float | None
    ) -> float:
        present = sum(value is not None for value in (score, comments, ratio))
        return round(0.45 + present * 0.1, 4)

    @staticmethod
    def _timestamp(value: object) -> datetime:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=UTC)
            return value.astimezone(UTC)
        if isinstance(value, int | float) and not isinstance(value, bool):
            return datetime.fromtimestamp(float(value), tz=UTC)
        if isinstance(value, str):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.replace(tzinfo=parsed.tzinfo or UTC).astimezone(UTC)
        raise ValueError("Reddit timestamp is invalid")

    @staticmethod
    def _optional_number(value: object) -> float | None:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError("Reddit metric must be numeric when present")
        if not math.isfinite(float(value)):
            raise ValueError("Reddit metric must be finite")
        return float(value)

    @classmethod
    def _optional_ratio(cls, value: object) -> float | None:
        ratio = cls._optional_number(value)
        if ratio is not None and not 0 <= ratio <= 1:
            raise ValueError("Reddit upvote_ratio must be between 0 and 1")
        return ratio

    @staticmethod
    def _optional_string(value: object) -> str | None:
        if value is None or not str(value).strip() or str(value) == "[removed]":
            return None
        return str(value).strip()

    @classmethod
    def _excerpt(cls, value: object) -> str | None:
        text = cls._optional_string(value)
        return text[:500] if text else None

    @staticmethod
    def _permalink(value: object) -> str:
        permalink = str(value).strip()
        return (
            f"https://www.reddit.com{permalink}"
            if permalink.startswith("/")
            else permalink
        )

    @staticmethod
    def _post_type(raw_content: Mapping[str, Any]) -> str:
        if bool(raw_content.get("is_self")):
            return "text_post"
        if bool(raw_content.get("is_video")):
            return "video_post"
        return "link_post"

    @staticmethod
    def _sort(value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in REDDIT_SORTS:
            raise ValueError(f"Unsupported Reddit sort: {value}")
        return normalized

    @staticmethod
    def _time_filter(value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in REDDIT_TIME_FILTERS:
            raise ValueError(f"Unsupported Reddit time filter: {value}")
        return normalized

    @staticmethod
    def _subreddits(value: object) -> tuple[str, ...]:
        if value is None or value == "":
            return ()
        values = value.split(",") if isinstance(value, str) else value
        if not isinstance(values, Sequence):
            raise ValueError("Reddit subreddits must be a sequence")
        result: list[str] = []
        for item in values:
            subreddit = str(item).strip().removeprefix("r/")
            if not _SUBREDDIT_PATTERN.fullmatch(subreddit):
                raise ValueError(f"Invalid subreddit name: {subreddit}")
            if subreddit not in result:
                result.append(subreddit)
        return tuple(result)
