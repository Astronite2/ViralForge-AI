"""Google Trends connector implementation."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from backend.app.connectors.base import BaseConnector
from backend.app.domain.trend_signal import TrendSignal


@dataclass(frozen=True, slots=True)
class GoogleTrendsFeedClient:
    """Fetch Google Trends RSS results without scraping HTML."""

    feed_url: str = "https://trends.google.com/trends/trendingsearches/daily/rss"
    timeout_seconds: float = 10.0

    def fetch(self, geo: str, limit: int) -> list[Mapping[str, Any]]:
        """Return normalized RSS entries from the Google Trends feed."""
        url = f"{self.feed_url}?{urlencode({'geo': geo})}"
        request = Request(url, headers={"User-Agent": "ViralForgeAI/1.0"})

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = response.read()
        except URLError as exc:  # pragma: no cover - network failure path
            raise RuntimeError("Unable to fetch Google Trends feed") from exc

        return self._parse_feed(payload, geo=geo, limit=limit)

    @staticmethod
    def _parse_feed(payload: bytes, *, geo: str, limit: int) -> list[Mapping[str, Any]]:
        root = ElementTree.fromstring(payload)
        channel = root.find("channel")
        if channel is None:
            return []

        items = channel.findall("item")[:limit]
        feed_items: list[Mapping[str, Any]] = []
        for index, item in enumerate(items, start=1):
            title = GoogleTrendsFeedClient._text(item, "title")
            link = GoogleTrendsFeedClient._text(item, "link")
            published_at = GoogleTrendsFeedClient._published_at(item)
            feed_items.append(
                {
                    "query": title,
                    "title": title,
                    "url": link,
                    "published_at": published_at,
                    "rank": index,
                    "geo": geo,
                    "source": "google_trends",
                }
            )
        return feed_items

    @staticmethod
    def _text(element: ElementTree.Element, tag_name: str) -> str:
        child = element.find(tag_name)
        if child is None or child.text is None:
            return ""
        return child.text.strip()

    @staticmethod
    def _published_at(element: ElementTree.Element) -> datetime:
        pub_date = GoogleTrendsFeedClient._text(element, "pubDate")
        if not pub_date:
            return datetime.now(UTC)
        value = parsedate_to_datetime(pub_date)
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


class GoogleTrendsConnector(BaseConnector[TrendSignal]):
    """Connector for Google Trends signal polling."""

    def __init__(
        self,
        fetcher: Callable[[str, int], list[Mapping[str, Any]]] | None = None,
        *,
        default_geo: str = "US",
        default_limit: int = 10,
    ) -> None:
        self._fetcher = fetcher or GoogleTrendsFeedClient().fetch
        self._default_geo = default_geo
        self._default_limit = default_limit

    def fetch(self, **kwargs: Any) -> list[Mapping[str, Any]]:
        geo = str(kwargs.get("geo", self._default_geo))
        limit = int(kwargs.get("limit", self._default_limit))
        return self._fetcher(geo, limit)

    def normalize(self, raw_content: Mapping[str, Any]) -> TrendSignal:
        self.validate(raw_content)
        rank = int(raw_content["rank"])
        title = str(raw_content["title"])
        geo = str(raw_content["geo"])
        published_at = self._as_datetime(raw_content["published_at"])
        score = round(1.0 / max(rank, 1), 4)
        confidence = round(max(0.7, 1.0 - ((rank - 1) * 0.03)), 2)
        return TrendSignal(
            source="google_trends",
            score=score,
            confidence=confidence,
            timestamp=published_at,
            reason=(
                "Google Trends reported increasing search interest for "
                f"{title} in {geo}."
            ),
        )

    def validate(self, raw_content: Mapping[str, Any]) -> None:
        required_fields = ("query", "title", "url", "published_at", "rank", "geo")
        missing_fields = [
            field for field in required_fields if field not in raw_content
        ]
        if missing_fields:
            raise ValueError(
                "Google Trends payload is missing required fields: "
                + ", ".join(missing_fields)
            )

        if not str(raw_content["title"]).strip():
            raise ValueError("Google Trends payload title cannot be empty")
        if not str(raw_content["url"]).strip():
            raise ValueError("Google Trends payload url cannot be empty")
        if int(raw_content["rank"]) < 1:
            raise ValueError("Google Trends payload rank must be positive")

    @staticmethod
    def _as_datetime(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        raise ValueError("published_at must be an ISO 8601 timestamp or datetime")
