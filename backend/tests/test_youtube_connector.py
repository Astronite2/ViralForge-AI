"""YouTube connector tests."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from backend.app.connectors.registry import build_default_connector_registry
from backend.app.connectors.youtube import (
    YouTubeApiError,
    YouTubeConnector,
    YouTubeQuotaError,
    YouTubeResponseError,
)
from backend.app.domain.content import Content
from backend.app.repositories.decision import DecisionRepository
from backend.app.services.connector_orchestrator import ConnectorOrchestrator


class _FakeYouTubeClient:
    def __init__(
        self,
        *,
        search_pages: list[Mapping[str, Any]] | None = None,
        videos_response: Mapping[str, Any] | None = None,
        channels_response: Mapping[str, Any] | None = None,
        search_error: Exception | None = None,
    ) -> None:
        self.search_pages = search_pages or []
        self.videos_response = videos_response or {"items": []}
        self.channels_response = channels_response or {"items": []}
        self.search_error = search_error
        self.search_calls: list[dict[str, Any]] = []
        self.videos_calls: list[list[str]] = []
        self.channels_calls: list[list[str]] = []

    def search(
        self,
        *,
        query: str,
        region: str,
        limit: int,
        page_token: str | None = None,
    ) -> Mapping[str, Any]:
        if self.search_error is not None:
            raise self.search_error
        self.search_calls.append(
            {
                "query": query,
                "region": region,
                "limit": limit,
                "page_token": page_token,
            }
        )
        if not self.search_pages:
            return {"items": []}
        index = len(self.search_calls) - 1
        if index < len(self.search_pages):
            return self.search_pages[index]
        return {"items": []}

    def videos(self, video_ids: list[str]) -> Mapping[str, Any]:
        self.videos_calls.append(list(video_ids))
        return self.videos_response

    def channels(self, channel_ids: list[str]) -> Mapping[str, Any]:
        self.channels_calls.append(list(channel_ids))
        return self.channels_response


def test_youtube_connector_normalizes_video_item() -> None:
    connector = YouTubeConnector(
        client=_FakeYouTubeClient(
            search_pages=[
                {
                    "items": [
                        {
                            "id": {"videoId": "video-1"},
                            "snippet": {
                                "title": "Ancient Egypt Documentary",
                                "description": "A recent documentary.",
                                "channelId": "channel-1",
                                "channelTitle": "History Hub",
                                "publishedAt": "2026-01-01T00:00:00Z",
                                "defaultLanguage": "en",
                            },
                        }
                    ]
                }
            ],
            videos_response={
                "items": [
                    {
                        "id": "video-1",
                        "snippet": {
                            "title": "Ancient Egypt Documentary",
                            "description": "A recent documentary.",
                            "publishedAt": "2026-01-01T00:00:00Z",
                        },
                        "contentDetails": {"duration": "PT10M30S"},
                        "statistics": {
                            "viewCount": "1000",
                            "likeCount": "100",
                            "commentCount": "10",
                        },
                    }
                ]
            },
            channels_response={
                "items": [
                    {
                        "id": "channel-1",
                        "snippet": {"title": "History Hub"},
                        "statistics": {"subscriberCount": "250000"},
                    }
                ]
            },
        )
    )

    raw_items = connector.fetch(query="Ancient Egypt", region="US", limit=1)
    content = connector.normalize(raw_items[0])

    assert isinstance(content, Content)
    assert content.id == "youtube:video-1"
    assert content.platform == "youtube"
    assert content.creator_name == "History Hub"
    assert content.metrics["view_count"] == 1000.0
    assert content.metrics["view_velocity"] > 0.0
    assert content.metadata["query"] == "Ancient Egypt"
    assert content.metadata["region"] == "US"
    assert content.metadata["subscriber_count"] == 250000
    assert content.signals[0].source == "youtube"
    assert "Ancient Egypt Documentary" in content.signals[0].reason


def test_youtube_connector_handles_missing_statistics() -> None:
    connector = YouTubeConnector(
        client=_FakeYouTubeClient(
            search_pages=[
                {
                    "items": [
                        {
                            "id": {"videoId": "video-2"},
                            "snippet": {
                                "title": "Hidden Stats Video",
                                "description": "Stats are hidden.",
                                "channelId": "channel-2",
                                "channelTitle": "Hidden Channel",
                                "publishedAt": "2026-01-01T00:00:00Z",
                            },
                        }
                    ]
                }
            ],
            videos_response={
                "items": [
                    {
                        "id": "video-2",
                        "snippet": {
                            "title": "Hidden Stats Video",
                            "description": "Stats are hidden.",
                            "publishedAt": "2026-01-01T00:00:00Z",
                        },
                        "contentDetails": {"duration": "PT5M"},
                        "statistics": {"viewCount": "300"},
                    }
                ]
            },
            channels_response={
                "items": [
                    {
                        "id": "channel-2",
                        "snippet": {"title": "Hidden Channel"},
                        "statistics": {"hiddenSubscriberCount": True},
                    }
                ]
            },
        )
    )

    raw_items = connector.fetch(query="Hidden Stats", region="US", limit=1)
    content = connector.normalize(raw_items[0])

    assert content.metrics["like_count"] == 0.0
    assert content.metrics["comment_count"] == 0.0
    assert content.metadata["subscriber_count"] is None
    assert content.metadata["subscriber_count_hidden"] is True


def test_youtube_connector_rejects_malformed_api_response() -> None:
    connector = YouTubeConnector(
        client=_FakeYouTubeClient(
            search_pages=[
                {
                    "items": [
                        {
                            "snippet": {
                                "title": "Malformed",
                                "channelId": "channel-3",
                                "channelTitle": "Channel",
                                "publishedAt": "2026-01-01T00:00:00Z",
                            }
                        }
                    ]
                }
            ]
        )
    )

    with pytest.raises(YouTubeResponseError):
        connector.fetch(query="Malformed", region="US", limit=1)


def test_youtube_connector_surfaces_api_failure() -> None:
    connector = YouTubeConnector(
        client=_FakeYouTubeClient(search_error=YouTubeApiError("boom"))
    )

    with pytest.raises(YouTubeApiError, match="boom"):
        connector.fetch(query="Failure", region="US", limit=1)


def test_youtube_connector_surfaces_quota_failure() -> None:
    connector = YouTubeConnector(
        client=_FakeYouTubeClient(search_error=YouTubeQuotaError("quota exhausted"))
    )

    with pytest.raises(YouTubeQuotaError, match="quota exhausted"):
        connector.fetch(query="Failure", region="US", limit=1)


def test_youtube_connector_supports_result_limiting_and_pagination() -> None:
    connector = YouTubeConnector(
        client=_FakeYouTubeClient(
            search_pages=[
                {
                    "items": [
                        {
                            "id": {"videoId": "video-1"},
                            "snippet": {
                                "title": "First",
                                "channelId": "channel-1",
                                "channelTitle": "Channel 1",
                                "publishedAt": "2026-01-01T00:00:00Z",
                            },
                        }
                    ],
                    "nextPageToken": "page-2",
                },
                {
                    "items": [
                        {
                            "id": {"videoId": "video-2"},
                            "snippet": {
                                "title": "Second",
                                "channelId": "channel-2",
                                "channelTitle": "Channel 2",
                                "publishedAt": "2026-01-01T00:00:00Z",
                            },
                        }
                    ]
                },
            ],
            videos_response={
                "items": [
                    {
                        "id": "video-1",
                        "snippet": {
                            "title": "First",
                            "publishedAt": "2026-01-01T00:00:00Z",
                        },
                        "contentDetails": {"duration": "PT1M"},
                        "statistics": {"viewCount": "10"},
                    },
                    {
                        "id": "video-2",
                        "snippet": {
                            "title": "Second",
                            "publishedAt": "2026-01-01T00:00:00Z",
                        },
                        "contentDetails": {"duration": "PT1M"},
                        "statistics": {"viewCount": "20"},
                    },
                ]
            },
            channels_response={
                "items": [
                    {
                        "id": "channel-1",
                        "snippet": {"title": "Channel 1"},
                        "statistics": {"subscriberCount": "10"},
                    },
                    {
                        "id": "channel-2",
                        "snippet": {"title": "Channel 2"},
                        "statistics": {"subscriberCount": "20"},
                    },
                ]
            },
        )
    )

    raw_items = connector.fetch(query="Pagination", region="US", limit=2)

    assert len(raw_items) == 2
    assert connector._client.search_calls[0]["page_token"] is None  # type: ignore[attr-defined]
    assert connector._client.search_calls[1]["page_token"] == "page-2"  # type: ignore[attr-defined]
    assert connector._client.videos_calls == [["video-1", "video-2"]]  # type: ignore[attr-defined]
    assert connector._client.channels_calls == [["channel-1", "channel-2"]]  # type: ignore[attr-defined]


def test_default_registry_registers_youtube_when_key_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "backend.app.connectors.registry.settings.youtube_api_key", "configured-key"
    )

    registry = build_default_connector_registry()

    assert "youtube" in registry.names()


def test_orchestrator_processes_youtube_content_and_remains_idempotent(
    session: Any,
) -> None:
    connector = YouTubeConnector(
        client=_FakeYouTubeClient(
            search_pages=[
                {
                    "items": [
                        {
                            "id": {"videoId": "video-3"},
                            "snippet": {
                                "title": "Ancient Egypt",
                                "description": "Trending history content.",
                                "channelId": "channel-3",
                                "channelTitle": "History Hub",
                                "publishedAt": "2026-01-01T00:00:00Z",
                            },
                        }
                    ]
                }
            ],
            videos_response={
                "items": [
                    {
                        "id": "video-3",
                        "snippet": {
                            "title": "Ancient Egypt",
                            "description": "Trending history content.",
                            "publishedAt": "2026-01-01T00:00:00Z",
                        },
                        "contentDetails": {"duration": "PT12M"},
                        "statistics": {
                            "viewCount": "2000",
                            "likeCount": "150",
                            "commentCount": "25",
                        },
                    }
                ]
            },
            channels_response={
                "items": [
                    {
                        "id": "channel-3",
                        "snippet": {"title": "History Hub"},
                        "statistics": {"subscriberCount": "50000"},
                    }
                ]
            },
        )
    )

    registry = build_default_connector_registry()
    registry.register("youtube", connector)
    orchestrator = ConnectorOrchestrator(
        registry=registry,
        session_factory=lambda: session,
    )

    connector_kwargs = {
        "youtube": {"query": "Ancient Egypt", "region": "US", "limit": 1}
    }
    first = orchestrator.run(connector_kwargs, enabled_connectors=("youtube",))
    second = orchestrator.run(connector_kwargs, enabled_connectors=("youtube",))

    assert first.connector_reports[0].decisions_created == 1
    assert second.connector_reports[0].decisions_created == 0
    assert len(DecisionRepository(session).list(10, 0)) == 1
