"""Deterministic Google Trends fixture data."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

VALID_TREND: dict[str, Any] = {
    "id": "3aa817eb-c30a-50fc-a0f4-1e33a224ba1d",
    "query": "Ancient Egypt",
    "title": "Ancient Egypt",
    "url": "https://trends.google.com/trends/explore?q=Ancient%20Egypt",
    "source_url": "https://trends.google.com/trends/explore?q=Ancient%20Egypt",
    "published_at": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
    "rank": 1,
    "geo": "US",
    "trend_type": "daily_trending_searches",
    "timeframe": "today 3-m",
    "interest_score": 100,
    "related_queries": [],
    "related_topics": [],
    "category": 0,
    "language": "en-US",
}

MULTIPLE_VALID_TRENDS: tuple[dict[str, Any], ...] = (
    VALID_TREND,
    {
        "id": "61d3845d-0556-5a82-a4b4-460417e9dc6a",
        "query": "AI video tools",
        "title": "AI video tools",
        "url": "https://trends.google.com/trends/explore?q=AI%20video%20tools",
        "source_url": "https://trends.google.com/trends/explore?q=AI%20video%20tools",
        "published_at": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
        "rank": 2,
        "geo": "US",
        "trend_type": "daily_trending_searches",
        "timeframe": "today 3-m",
        "interest_score": 95,
        "related_queries": [],
        "related_topics": [],
        "category": 0,
        "language": "en-US",
    },
)

MALFORMED_TREND: dict[str, Any] = {
    "id": "malformed",
    "query": "",
    "title": "",
    "url": "https://trends.google.com/trends/explore?q=",
    "published_at": "invalid",
    "rank": 0,
    "geo": "US",
    "trend_type": "daily_trending_searches",
    "timeframe": "today 3-m",
    "interest_score": -1,
    "source_url": "",
    "category": 0,
    "language": "en-US",
}


def trend_payloads() -> tuple[Mapping[str, Any], ...]:
    """Return a deterministic set of Google Trends payloads."""
    return MULTIPLE_VALID_TRENDS
