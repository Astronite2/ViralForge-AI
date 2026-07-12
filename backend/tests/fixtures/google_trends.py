"""Deterministic Google Trends fixture data."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

VALID_TREND: dict[str, Any] = {
    "query": "Ancient Egypt",
    "title": "Ancient Egypt",
    "url": "https://trends.google.com/trends/explore?q=Ancient%20Egypt",
    "published_at": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
    "rank": 1,
    "geo": "US",
}

MULTIPLE_VALID_TRENDS: tuple[dict[str, Any], ...] = (
    VALID_TREND,
    {
        "query": "AI video tools",
        "title": "AI video tools",
        "url": "https://trends.google.com/trends/explore?q=AI%20video%20tools",
        "published_at": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
        "rank": 2,
        "geo": "US",
    },
)

MALFORMED_TREND: dict[str, Any] = {
    "query": "",
    "title": "",
    "url": "https://trends.google.com/trends/explore?q=",
    "published_at": "invalid",
    "rank": 0,
    "geo": "US",
}


def trend_payloads() -> tuple[Mapping[str, Any], ...]:
    """Return a deterministic set of Google Trends payloads."""
    return MULTIPLE_VALID_TRENDS
