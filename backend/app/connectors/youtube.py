"""YouTube Data API v3 connector implementation."""

from __future__ import annotations

import json
import logging
import math
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from backend.app.connectors.base import BaseConnector
from backend.app.core.config import settings
from backend.app.domain.content import Content
from backend.app.domain.trend_signal import TrendSignal

logger = logging.getLogger(__name__)


class YouTubeConnectorError(RuntimeError):
    """Base error for YouTube connector failures."""


class YouTubeConnectorDisabledError(YouTubeConnectorError):
    """Raised when the connector is disabled by configuration."""


class YouTubeApiError(YouTubeConnectorError):
    """Raised when the YouTube Data API request fails."""


class YouTubeQuotaError(YouTubeApiError):
    """Raised when the API indicates quota exhaustion."""


class YouTubeResponseError(YouTubeApiError):
    """Raised when the API response is malformed."""


@dataclass(frozen=True, slots=True)
class YouTubeDataApiClient:
    """Minimal YouTube Data API v3 client using urllib."""

    api_key: str
    base_url: str = settings.youtube_api_base_url
    timeout_seconds: float = settings.youtube_timeout_seconds

    def search(
        self,
        *,
        query: str,
        region: str,
        limit: int,
        page_token: str | None = None,
    ) -> Mapping[str, Any]:
        params: dict[str, object] = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "order": "date",
            "maxResults": min(limit, 50),
            "regionCode": region,
            "key": self.api_key,
        }
        if page_token is not None:
            params["pageToken"] = page_token
        return self._request_json("search", params)

    def videos(self, video_ids: Sequence[str]) -> Mapping[str, Any]:
        params = {
            "part": "snippet,contentDetails,statistics",
            "id": ",".join(video_ids),
            "key": self.api_key,
        }
        return self._request_json("videos", params)

    def channels(self, channel_ids: Sequence[str]) -> Mapping[str, Any]:
        params = {
            "part": "snippet,statistics",
            "id": ",".join(channel_ids),
            "key": self.api_key,
        }
        return self._request_json("channels", params)

    def _request_json(
        self, endpoint: str, params: Mapping[str, object]
    ) -> Mapping[str, Any]:
        url = f"{self.base_url.rstrip('/')}/{endpoint}?{urlencode(params)}"
        request = Request(url, headers={"User-Agent": "ViralForgeAI/1.0"})
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = response.read()
        except HTTPError as exc:
            logger.exception(
                "YouTube API request failed",
                extra={"endpoint": endpoint, "status_code": exc.code},
            )
            raise self._http_error(endpoint, exc) from exc
        except URLError as exc:  # pragma: no cover - network failure path
            logger.exception(
                "YouTube API network failure",
                extra={"endpoint": endpoint},
            )
            raise YouTubeApiError("Unable to reach the YouTube Data API") from exc

        try:
            parsed = json.loads(payload.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise YouTubeResponseError("YouTube API returned invalid JSON") from exc
        if not isinstance(parsed, dict):
            raise YouTubeResponseError("YouTube API response must be an object")
        return parsed

    def _http_error(self, endpoint: str, exc: HTTPError) -> YouTubeApiError:
        body = exc.read().decode("utf-8", errors="replace")
        reason = self._extract_reason(body)
        message = f"YouTube API request to {endpoint} failed with HTTP {exc.code}"
        if reason:
            message = f"{message}: {reason}"
        if exc.code == 403 and "quota" in reason.lower():
            return YouTubeQuotaError(message)
        return YouTubeApiError(message)

    @staticmethod
    def _extract_reason(body: str) -> str:
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            return body.strip()
        if not isinstance(parsed, dict):
            return body.strip()
        error = parsed.get("error")
        if isinstance(error, dict):
            message = str(error.get("message", "")).strip()
            errors = error.get("errors")
            if isinstance(errors, list) and errors:
                first = errors[0]
                if isinstance(first, dict):
                    reason = str(first.get("reason", "")).strip()
                    if reason:
                        return f"{message} ({reason})" if message else reason
            return message
        return body.strip()


class YouTubeConnector(BaseConnector[Content]):
    """Connector for the YouTube Data API v3."""

    _required_fields = (
        "video_id",
        "title",
        "description",
        "channel_id",
        "channel_title",
        "published_at",
        "view_count",
        "like_count",
        "comment_count",
        "duration_seconds",
        "subscriber_count",
        "query",
        "region",
        "source_url",
    )

    def __init__(
        self,
        api_key: str | None = None,
        *,
        client: YouTubeDataApiClient | None = None,
        default_region: str | None = None,
        default_limit: int | None = None,
        search_fetcher: Callable[..., Mapping[str, Any]] | None = None,
        videos_fetcher: Callable[..., Mapping[str, Any]] | None = None,
        channels_fetcher: Callable[..., Mapping[str, Any]] | None = None,
    ) -> None:
        raw_api_key = settings.youtube_api_key if api_key is None else api_key
        self._api_key = (
            raw_api_key.strip()
            if isinstance(raw_api_key, str) and raw_api_key.strip()
            else None
        )
        self._client = client
        self._default_region = default_region or settings.youtube_default_region
        self._default_limit = (
            default_limit
            if default_limit is not None
            else settings.youtube_default_limit
        )
        self._search_fetcher = search_fetcher
        self._videos_fetcher = videos_fetcher
        self._channels_fetcher = channels_fetcher

    @property
    def is_enabled(self) -> bool:
        """Return whether the connector can make live API requests."""
        return self._client is not None or self._api_key is not None

    def fetch(self, **kwargs: Any) -> list[Mapping[str, Any]]:
        if not self.is_enabled:
            logger.info(
                "YouTube connector disabled because no API key is configured",
                extra={"source": "youtube"},
            )
            return []

        query = str(kwargs.get("query", "")).strip()
        if not query:
            raise ValueError("YouTube query is required")
        region = self._normalize_region(kwargs.get("region", self._default_region))
        limit = int(kwargs.get("limit", self._default_limit))
        if limit < 1:
            raise ValueError("YouTube limit must be positive")

        search_items = self._collect_search_items(
            query=query,
            region=region,
            limit=limit,
        )
        if not search_items:
            return []

        video_ids = [self._video_id(item) for item in search_items]
        video_map = self._video_lookup(video_ids)
        channel_ids = [self._channel_id(item) for item in search_items]
        channel_map = self._channel_lookup(channel_ids)

        raw_items: list[Mapping[str, Any]] = []
        for rank, search_item in enumerate(search_items, start=1):
            video_id = self._video_id(search_item)
            video_item = video_map.get(video_id, {})
            channel_id = self._channel_id(search_item)
            channel_item = channel_map.get(channel_id, {})
            raw_items.append(
                self._build_raw_item(
                    search_item=search_item,
                    video_item=video_item,
                    channel_item=channel_item,
                    query=query,
                    region=region,
                    rank=rank,
                )
            )
        return raw_items

    def normalize(self, raw_content: Mapping[str, Any]) -> Content:
        self.validate(raw_content)
        published_at = self._as_datetime(raw_content["published_at"])
        view_count = self._optional_int(raw_content.get("view_count")) or 0
        like_count = self._optional_int(raw_content.get("like_count"))
        comment_count = self._optional_int(raw_content.get("comment_count"))
        duration_seconds = self._optional_int(raw_content.get("duration_seconds"))
        subscriber_count = self._optional_int(raw_content.get("subscriber_count"))
        freshness_hours = self._freshness_hours(published_at)
        view_velocity = round(view_count / max(freshness_hours, 1.0), 4)
        engagement_rate = round(
            ((like_count or 0) + (comment_count or 0)) / max(view_count, 1), 4
        )
        channel_size_adjusted_performance = round(
            view_velocity / max(math.sqrt(float(subscriber_count or 1)), 1.0), 4
        )
        metrics = {
            "view_count": float(view_count),
            "like_count": float(like_count or 0),
            "comment_count": float(comment_count or 0),
            "subscriber_count": float(subscriber_count or 0),
            "view_velocity": view_velocity,
            "engagement_rate": engagement_rate,
            "channel_size_adjusted_performance": channel_size_adjusted_performance,
            "freshness_hours": round(freshness_hours, 4),
        }
        metadata = {
            "video_id": str(raw_content["video_id"]),
            "channel_id": str(raw_content["channel_id"]),
            "channel_title": str(raw_content["channel_title"]),
            "query": str(raw_content["query"]),
            "region": str(raw_content["region"]),
            "source_url": str(raw_content["source_url"]),
            "view_count": view_count,
            "like_count": like_count,
            "comment_count": comment_count,
            "subscriber_count": subscriber_count,
            "subscriber_count_hidden": subscriber_count is None,
            "view_velocity": view_velocity,
            "engagement_rate": engagement_rate,
            "channel_size_adjusted_performance": channel_size_adjusted_performance,
            "freshness_hours": round(freshness_hours, 4),
            "thumbnail_url": raw_content.get("thumbnail_url"),
        }
        signal_score = self._signal_score(metrics)
        signal_confidence = self._signal_confidence(raw_content)
        signal = TrendSignal(
            source="youtube",
            score=signal_score,
            confidence=signal_confidence,
            timestamp=published_at,
            reason=(
                "YouTube reported increasing engagement for "
                f"{raw_content['title']} in {raw_content['region']}."
            ),
        )
        return Content(
            id=f"youtube:{raw_content['video_id']}",
            platform="youtube",
            creator_name=str(raw_content["channel_title"]),
            creator_id=str(raw_content["channel_id"]),
            title=str(raw_content["title"]),
            description=self._optional_string(raw_content.get("description")),
            url=str(raw_content["source_url"]),
            language=self._optional_string(raw_content.get("language")),
            country=str(raw_content["region"]),
            published_at=published_at,
            duration_seconds=duration_seconds,
            content_type="video",
            metrics=metrics,
            analysis={},
            signals=(signal,),
            metadata=metadata,
        )

    def validate(self, raw_content: Mapping[str, Any]) -> None:
        missing_fields = [
            field for field in self._required_fields if field not in raw_content
        ]
        if missing_fields:
            raise ValueError(
                "YouTube payload is missing required fields: "
                + ", ".join(missing_fields)
            )
        if not str(raw_content["video_id"]).strip():
            raise ValueError("YouTube payload video_id cannot be empty")
        if not str(raw_content["title"]).strip():
            raise ValueError("YouTube payload title cannot be empty")
        if not str(raw_content["channel_id"]).strip():
            raise ValueError("YouTube payload channel_id cannot be empty")
        if not str(raw_content["channel_title"]).strip():
            raise ValueError("YouTube payload channel_title cannot be empty")
        if not str(raw_content["source_url"]).strip():
            raise ValueError("YouTube payload source_url cannot be empty")
        self._as_datetime(raw_content["published_at"])
        self._optional_int(raw_content.get("view_count"))
        self._optional_int(raw_content.get("like_count"))
        self._optional_int(raw_content.get("comment_count"))
        self._optional_int(raw_content.get("duration_seconds"))
        self._optional_int(raw_content.get("subscriber_count"))

    def _collect_search_items(
        self, *, query: str, region: str, limit: int
    ) -> list[Mapping[str, Any]]:
        search_results: list[Mapping[str, Any]] = []
        page_token: str | None = None
        while len(search_results) < limit:
            page_size = min(50, limit - len(search_results))
            search_response = self._search_page(
                query=query,
                region=region,
                limit=page_size,
                page_token=page_token,
            )
            items = search_response.get("items", [])
            if not isinstance(items, list):
                raise YouTubeResponseError(
                    "YouTube search response items must be a list"
                )
            for item in items:
                if isinstance(item, Mapping):
                    search_results.append(item)
                if len(search_results) >= limit:
                    break
            page_token = search_response.get("nextPageToken")
            if not page_token or not items:
                break
            page_token = str(page_token)
        return search_results[:limit]

    def _search_page(
        self,
        *,
        query: str,
        region: str,
        limit: int,
        page_token: str | None,
    ) -> Mapping[str, Any]:
        if self._search_fetcher is not None:
            return self._search_fetcher(
                query=query,
                region=region,
                limit=limit,
                page_token=page_token,
            )
        if self._client is not None:
            return self._client.search(
                query=query,
                region=region,
                limit=limit,
                page_token=page_token,
            )
        if self._api_key is None:
            raise YouTubeConnectorDisabledError(
                "YouTube connector is disabled without an API key"
            )
        return YouTubeDataApiClient(self._api_key).search(
            query=query,
            region=region,
            limit=limit,
            page_token=page_token,
        )

    def _video_lookup(self, video_ids: Sequence[str]) -> dict[str, Mapping[str, Any]]:
        video_map: dict[str, Mapping[str, Any]] = {}
        for batch in self._batched(video_ids, 50):
            response = self._videos_page(batch)
            items = response.get("items", [])
            if not isinstance(items, list):
                raise YouTubeResponseError(
                    "YouTube videos response items must be a list"
                )
            for item in items:
                if isinstance(item, Mapping) and "id" in item:
                    video_map[str(item["id"])] = item
        return video_map

    def _videos_page(self, video_ids: Sequence[str]) -> Mapping[str, Any]:
        if self._videos_fetcher is not None:
            return self._videos_fetcher(video_ids=tuple(video_ids))
        if self._client is not None:
            return self._client.videos(video_ids)
        if self._api_key is None:
            raise YouTubeConnectorDisabledError(
                "YouTube connector is disabled without an API key"
            )
        return YouTubeDataApiClient(self._api_key).videos(video_ids)

    def _channel_lookup(
        self, channel_ids: Sequence[str]
    ) -> dict[str, Mapping[str, Any]]:
        channel_map: dict[str, Mapping[str, Any]] = {}
        filtered = [channel_id for channel_id in channel_ids if channel_id]
        for batch in self._batched(filtered, 50):
            response = self._channels_page(batch)
            items = response.get("items", [])
            if not isinstance(items, list):
                raise YouTubeResponseError(
                    "YouTube channels response items must be a list"
                )
            for item in items:
                if isinstance(item, Mapping) and "id" in item:
                    channel_map[str(item["id"])] = item
        return channel_map

    def _channels_page(self, channel_ids: Sequence[str]) -> Mapping[str, Any]:
        if self._channels_fetcher is not None:
            return self._channels_fetcher(channel_ids=tuple(channel_ids))
        if self._client is not None:
            return self._client.channels(channel_ids)
        if self._api_key is None:
            raise YouTubeConnectorDisabledError(
                "YouTube connector is disabled without an API key"
            )
        return YouTubeDataApiClient(self._api_key).channels(channel_ids)

    def _build_raw_item(
        self,
        *,
        search_item: Mapping[str, Any],
        video_item: Mapping[str, Any],
        channel_item: Mapping[str, Any],
        query: str,
        region: str,
        rank: int,
    ) -> Mapping[str, Any]:
        snippet = self._mapping(search_item.get("snippet"))
        video_snippet = self._mapping(video_item.get("snippet"))
        video_statistics = self._mapping(video_item.get("statistics"))
        content_details = self._mapping(video_item.get("contentDetails"))
        channel_snippet = self._mapping(channel_item.get("snippet"))
        channel_statistics = self._mapping(channel_item.get("statistics"))
        video_id = self._video_id(search_item)
        title = str(video_snippet.get("title") or snippet.get("title") or "")
        description = str(
            video_snippet.get("description") or snippet.get("description") or ""
        )
        channel_id = self._channel_id(search_item)
        channel_title = str(
            channel_snippet.get("title") or snippet.get("channelTitle") or ""
        )
        published_at = self._published_at(video_snippet or snippet)
        view_count = self._optional_int(video_statistics.get("viewCount"))
        like_count = self._optional_int(video_statistics.get("likeCount"))
        comment_count = self._optional_int(video_statistics.get("commentCount"))
        duration_seconds = self._duration_seconds(content_details.get("duration"))
        subscriber_count = None
        if not channel_statistics.get("hiddenSubscriberCount"):
            subscriber_count = self._optional_int(
                channel_statistics.get("subscriberCount")
            )
        return {
            "video_id": video_id,
            "title": title,
            "description": description,
            "channel_id": channel_id,
            "channel_title": channel_title,
            "published_at": published_at,
            "view_count": view_count,
            "like_count": like_count,
            "comment_count": comment_count,
            "duration_seconds": duration_seconds,
            "subscriber_count": subscriber_count,
            "query": query,
            "region": region,
            "source_url": f"https://www.youtube.com/watch?v={video_id}",
            "rank": rank,
            "thumbnail_url": self._thumbnail_url(video_snippet or snippet),
            "language": video_snippet.get("defaultAudioLanguage")
            or snippet.get("defaultAudioLanguage")
            or snippet.get("defaultLanguage"),
        }

    @staticmethod
    def _video_id(search_item: Mapping[str, Any]) -> str:
        identifier = search_item.get("id")
        if isinstance(identifier, Mapping):
            video_id = identifier.get("videoId")
            if video_id is not None:
                return str(video_id)
        video_id = search_item.get("video_id")
        if video_id is not None:
            return str(video_id)
        raise YouTubeResponseError("YouTube search item is missing video_id")

    @staticmethod
    def _channel_id(search_item: Mapping[str, Any]) -> str:
        snippet = search_item.get("snippet")
        if isinstance(snippet, Mapping) and snippet.get("channelId") is not None:
            return str(snippet["channelId"])
        channel_id = search_item.get("channel_id")
        if channel_id is not None:
            return str(channel_id)
        raise YouTubeResponseError("YouTube search item is missing channel_id")

    @staticmethod
    def _mapping(value: Any) -> Mapping[str, Any]:
        if value is None:
            return {}
        if not isinstance(value, Mapping):
            raise YouTubeResponseError("YouTube API response section must be a mapping")
        return value

    @staticmethod
    def _published_at(value: Mapping[str, Any]) -> datetime:
        published_at = value.get("publishedAt")
        if published_at is None:
            raise YouTubeResponseError("YouTube video is missing publishedAt")
        if isinstance(published_at, datetime):
            if published_at.tzinfo is None:
                return published_at.replace(tzinfo=UTC)
            return published_at.astimezone(UTC)
        if isinstance(published_at, str):
            parsed = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC)
        raise YouTubeResponseError("YouTube publishedAt must be a timestamp")

    @staticmethod
    def _thumbnail_url(value: Mapping[str, Any]) -> str | None:
        thumbnails = value.get("thumbnails")
        if not isinstance(thumbnails, Mapping):
            return None
        default = thumbnails.get("default")
        if isinstance(default, Mapping) and default.get("url") is not None:
            return str(default["url"])
        return None

    @staticmethod
    def _duration_seconds(duration: Any) -> int | None:
        if duration is None:
            return None
        if isinstance(duration, int):
            return duration
        if not isinstance(duration, str):
            raise YouTubeResponseError("YouTube duration must be a string or int")
        match = re.fullmatch(
            r"P(?:(?P<days>\d+)D)?T"
            r"(?:(?P<hours>\d+)H)?"
            r"(?:(?P<minutes>\d+)M)?"
            r"(?:(?P<seconds>\d+)S)?",
            duration,
        )
        if match is None:
            raise YouTubeResponseError("YouTube duration is not ISO 8601 compliant")
        days = int(match.group("days") or 0)
        hours = int(match.group("hours") or 0)
        minutes = int(match.group("minutes") or 0)
        seconds = int(match.group("seconds") or 0)
        return ((days * 24 + hours) * 60 + minutes) * 60 + seconds

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise YouTubeResponseError("YouTube statistics must be integers") from exc

    @staticmethod
    def _optional_string(value: Any) -> str | None:
        return str(value) if value is not None else None

    @staticmethod
    def _as_datetime(value: Any) -> datetime:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=UTC)
            return value.astimezone(UTC)
        if isinstance(value, str):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC)
        raise YouTubeResponseError("YouTube published_at must be a timestamp")

    @staticmethod
    def _normalize_region(value: Any) -> str:
        region = str(value).strip().upper()
        if not region:
            raise ValueError("YouTube region cannot be empty")
        return region

    @staticmethod
    def _freshness_hours(published_at: datetime) -> float:
        now = datetime.now(UTC)
        delta = now - published_at.astimezone(UTC)
        return max(delta.total_seconds() / 3600.0, 0.0)

    @staticmethod
    def _signal_score(metrics: Mapping[str, float]) -> float:
        view_velocity = metrics.get("view_velocity", 0.0)
        engagement_rate = metrics.get("engagement_rate", 0.0)
        score = (view_velocity / 1000.0) + (engagement_rate * 5.0)
        return round(max(0.0, min(score, 1.0)), 4)

    @staticmethod
    def _signal_confidence(raw_content: Mapping[str, Any]) -> float:
        signals = sum(
            1
            for field in (
                "view_count",
                "like_count",
                "comment_count",
                "duration_seconds",
                "subscriber_count",
            )
            if raw_content.get(field) is not None
        )
        return round(min(1.0, 0.55 + (signals * 0.09)), 2)

    @staticmethod
    def _batched(items: Sequence[str], batch_size: int) -> list[tuple[str, ...]]:
        return [
            tuple(items[index : index + batch_size])
            for index in range(0, len(items), batch_size)
        ]
