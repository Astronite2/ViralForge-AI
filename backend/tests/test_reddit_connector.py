"""Reddit OAuth provider, connector, and pipeline tests."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest
from sqlalchemy.orm import Session

from backend.app.connectors.metadata import ConnectorCapability
from backend.app.connectors.reddit import RedditConnector
from backend.app.connectors.reddit_providers import (
    DisabledRedditProvider,
    FixtureRedditProvider,
    OfficialRedditProvider,
    RedditAuthenticationError,
    RedditDisabledError,
    RedditMalformedResponseError,
    RedditRateLimitError,
    RedditTemporaryError,
)
from backend.app.connectors.registry import (
    ConnectorRegistry,
    build_reddit_provider,
)
from backend.app.core.config import settings
from backend.app.repositories.content import ContentRepository
from backend.app.repositories.decision import DecisionRepository
from backend.app.services.connector_orchestrator import ConnectorOrchestrator
from backend.app.services.connector_status import ConnectorStatusStore
from backend.app.services.unified_signal_normalizer import UnifiedSignalNormalizer


def _post(**overrides: Any) -> dict[str, Any]:
    return {
        "id": "abc123",
        "name": "t3_abc123",
        "title": "AI video generation workflow",
        "selftext": "A concise discussion of an AI video workflow.",
        "author": "example_author",
        "subreddit": "ArtificialInteligence",
        "created_utc": 1767225600,
        "score": 120,
        "num_comments": 24,
        "upvote_ratio": 0.91,
        "total_awards_received": 2,
        "permalink": "/r/ArtificialInteligence/comments/abc123/example/",
        "url": "https://example.com/article",
        "is_self": False,
        "is_video": False,
        "over_18": False,
        "spoiler": False,
        "stickied": False,
        **overrides,
    }


def _connector(*posts: Mapping[str, Any]) -> RedditConnector:
    return RedditConnector(provider=FixtureRedditProvider(posts))


def test_disabled_provider_makes_no_request() -> None:
    provider = DisabledRedditProvider()
    assert provider.diagnostics() == {
        "enabled": False,
        "authentication_ready": False,
    }
    with pytest.raises(RedditDisabledError):
        provider.search_posts(
            query="ai", subreddits=(), sort="hot", time_filter="week", limit=1
        )


def test_official_provider_acquires_token_and_searches() -> None:
    calls: list[tuple[str, str]] = []

    def requester(
        method: str,
        url: str,
        _headers: Mapping[str, str],
        _data: bytes | None,
        _timeout: float,
    ) -> tuple[int, Mapping[str, str], Mapping[str, Any]]:
        calls.append((method, url))
        if method == "POST":
            return 200, {}, {"access_token": "token", "expires_in": 3600}
        return (
            200,
            {"x-ratelimit-remaining": "99"},
            {"data": {"children": [{"kind": "t3", "data": _post()}]}},
        )

    provider = OfficialRedditProvider(
        client_id="client",
        client_secret="secret",
        user_agent="ViralForgeAI/0.1 test",
        requester=requester,
    )
    result = provider.search_posts(
        query="AI video",
        subreddits=("ArtificialInteligence",),
        sort="hot",
        time_filter="week",
        limit=5,
    )
    assert len(result.items) == 1
    assert result.rate_limit.remaining == 99
    assert calls[0][1] == OfficialRedditProvider.token_url
    assert "/r/ArtificialInteligence/search?" in calls[1][1]
    assert "secret" not in str(provider.diagnostics())


def test_missing_and_invalid_credentials_are_typed() -> None:
    missing = OfficialRedditProvider(
        client_id=None,
        client_secret=None,
        user_agent="ViralForgeAI/0.1 test",
        requester=lambda *_: (500, {}, {}),
    )
    with pytest.raises(Exception, match="client ID and client secret"):
        missing.search_posts(
            query="ai", subreddits=(), sort="hot", time_filter="week", limit=1
        )

    rejected = OfficialRedditProvider(
        client_id="bad",
        client_secret="bad",
        user_agent="ViralForgeAI/0.1 test",
        requester=lambda *_: (401, {}, {"error": "invalid_client"}),
    )
    with pytest.raises(RedditAuthenticationError):
        rejected.search_posts(
            query="ai", subreddits=(), sort="hot", time_filter="week", limit=1
        )


def test_expired_token_is_renewed() -> None:
    now = [100.0]
    token_calls = 0

    def requester(*args: Any) -> tuple[int, Mapping[str, str], Mapping[str, Any]]:
        nonlocal token_calls
        if args[0] == "POST":
            token_calls += 1
            return 200, {}, {"access_token": f"token-{token_calls}", "expires_in": 60}
        return 200, {}, {"data": {"children": []}}

    provider = OfficialRedditProvider(
        client_id="client",
        client_secret="secret",
        user_agent="ViralForgeAI/0.1 test",
        requester=requester,
        clock=lambda: now[0],
    )
    provider.search_posts(
        query="ai", subreddits=(), sort="hot", time_filter="week", limit=1
    )
    now[0] = 200.0
    provider.search_posts(
        query="ai", subreddits=(), sort="hot", time_filter="week", limit=1
    )
    assert token_calls == 2


@pytest.mark.parametrize(
    ("status", "error"),
    [(429, RedditRateLimitError), (503, RedditTemporaryError)],
)
def test_transient_failures_retry(status: int, error: type[Exception]) -> None:
    calls = 0

    def requester(*args: Any) -> tuple[int, Mapping[str, str], Mapping[str, Any]]:
        nonlocal calls
        calls += 1
        if args[0] == "POST":
            return 200, {}, {"access_token": "token", "expires_in": 3600}
        return status, {}, {}

    provider = OfficialRedditProvider(
        client_id="client",
        client_secret="secret",
        user_agent="ViralForgeAI/0.1 test",
        requester=requester,
        max_retries=2,
        backoff_seconds=0,
    )
    with pytest.raises(error):
        provider.search_posts(
            query="ai", subreddits=(), sort="hot", time_filter="week", limit=1
        )
    assert calls == 4  # one token request plus three bounded API attempts


def test_permanent_4xx_and_malformed_response_do_not_retry() -> None:
    calls = 0

    def forbidden(*args: Any) -> tuple[int, Mapping[str, str], Mapping[str, Any]]:
        nonlocal calls
        calls += 1
        if args[0] == "POST":
            return 200, {}, {"access_token": "token", "expires_in": 3600}
        return 403, {}, {}

    provider = OfficialRedditProvider(
        client_id="client",
        client_secret="secret",
        user_agent="ViralForgeAI/0.1 test",
        requester=forbidden,
    )
    with pytest.raises(Exception, match="denied"):
        provider.search_posts(
            query="ai", subreddits=(), sort="hot", time_filter="week", limit=1
        )
    assert calls == 2

    malformed = OfficialRedditProvider(
        client_id="client",
        client_secret="secret",
        user_agent="ViralForgeAI/0.1 test",
        requester=lambda method, *_: (
            (200, {}, {"access_token": "token", "expires_in": 3600})
            if method == "POST"
            else (200, {}, {"unexpected": True})
        ),
    )
    with pytest.raises(RedditMalformedResponseError):
        malformed.search_posts(
            query="ai", subreddits=(), sort="hot", time_filter="week", limit=1
        )


def test_timeout_is_retried_and_safely_reported() -> None:
    calls = 0

    def timeout(*_args: Any) -> tuple[int, Mapping[str, str], Mapping[str, Any]]:
        nonlocal calls
        calls += 1
        if calls == 1:
            return 200, {}, {"access_token": "token", "expires_in": 3600}
        raise TimeoutError

    provider = OfficialRedditProvider(
        client_id="client",
        client_secret="secret",
        user_agent="ViralForgeAI/0.1 test",
        requester=timeout,
        max_retries=1,
        backoff_seconds=0,
    )
    with pytest.raises(RedditTemporaryError, match="temporarily unreachable"):
        provider.search_posts(
            query="ai", subreddits=(), sort="hot", time_filter="week", limit=1
        )
    assert calls == 3


def test_fixture_and_connector_normalization_are_deterministic() -> None:
    connector = _connector(_post())
    first_raw = connector.fetch(
        query="AI video", subreddits=["ArtificialInteligence"], limit=5
    )
    second_raw = connector.fetch(
        query="AI video", subreddits=["ArtificialInteligence"], limit=5
    )
    first = connector.normalize(first_raw[0])
    second = connector.normalize(second_raw[0])
    assert first == second
    assert first.id == "reddit:abc123"
    assert first.metadata["fixture_backed"] is True
    assert first.metrics["comment_count"] == 24
    assert first.signals[0].metadata["signal_type"] == "DISCUSSION_VELOCITY"
    assert "platform-wide trend" in first.signals[0].reason


def test_multiple_subreddits_deleted_author_and_missing_metrics() -> None:
    connector = _connector(
        _post(author=None, score=None, num_comments=None, upvote_ratio=None)
    )
    raw = connector.fetch(query="ai", subreddits=["technology", "MachineLearning"])[0]
    content = connector.normalize(raw)
    assert raw["requested_subreddits"] == ["technology", "MachineLearning"]
    assert content.creator_name == "[deleted]"
    assert "score" not in content.metrics
    assert "comment_count" not in content.metrics
    assert content.metadata["score"] is None


def test_post_only_validation_and_no_comments_capability() -> None:
    connector = _connector(_post())
    raw = connector.fetch(query="ai")[0]
    with pytest.raises(ValueError, match="post"):
        connector.validate({**raw, "name": "t1_comment"})
    assert ConnectorCapability.COMMENTS not in connector.capabilities
    assert ConnectorCapability.COMMUNITIES in connector.capabilities


def test_reddit_pipeline_persists_idempotently(session: Session) -> None:
    registry = ConnectorRegistry()
    registry.register("reddit", _connector(_post()))
    orchestrator = ConnectorOrchestrator(
        registry=registry,
        session_factory=lambda: session,
        status_store=ConnectorStatusStore(use_redis=False),
    )
    first = orchestrator.run({"reddit": {"query": "AI video"}})
    second = orchestrator.run({"reddit": {"query": "AI video"}})
    assert first.connector_reports[0].status == "success"
    assert first.connector_reports[0].items_processed == 1
    assert second.connector_reports[0].decisions_created == 0
    assert len(ContentRepository(session).list()) == 1
    assert len(DecisionRepository(session).list(10, 0)) == 1

    content = _connector(_post()).normalize(_connector(_post()).fetch(query="ai")[0])
    unified = UnifiedSignalNormalizer().normalize(
        content, event_version="v1", correlation_id="reddit-test"
    )[0]
    assert unified.source == "reddit"
    assert unified.content_id == "reddit:abc123"
    assert unified.connector_metadata.get("youtube") is None


def test_disabled_orchestration_report_is_structured(session: Session) -> None:
    registry = ConnectorRegistry()
    registry.register("reddit", RedditConnector(provider=DisabledRedditProvider()))
    report = ConnectorOrchestrator(
        registry=registry,
        session_factory=lambda: session,
        status_store=ConnectorStatusStore(use_redis=False),
    ).run({"reddit": {"query": "ai"}}, enabled_connectors=("reddit",))
    item = report.connector_reports[0]
    assert item.status == "disabled"
    assert item.items_fetched == 0
    assert item.provider == "disabled"
    assert item.connector_version == "1.0.0"


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (RedditRateLimitError("rate limited"), "degraded", "rate_limited"),
        (
            RedditAuthenticationError("credentials rejected"),
            "unavailable",
            "provider_unavailable",
        ),
    ],
)
def test_reddit_availability_reports_are_structured(
    session: Session, error: Exception, status: str, code: str
) -> None:
    class FailingProvider(FixtureRedditProvider):
        provider_name = "reddit_data_api"

        def search_posts(self, **_: Any):
            raise error

    registry = ConnectorRegistry()
    registry.register("reddit", RedditConnector(provider=FailingProvider()))
    report = ConnectorOrchestrator(
        registry=registry,
        session_factory=lambda: session,
        status_store=ConnectorStatusStore(use_redis=False),
    ).run({"reddit": {"query": "ai"}}, enabled_connectors=("reddit",))
    item = report.connector_reports[0]
    assert item.status == status
    assert item.error_code == code
    assert item.errors == (str(error),)


def test_fixture_provider_is_blocked_from_application_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "reddit_enabled", True)
    monkeypatch.setattr(settings, "reddit_provider", "fixture")
    with pytest.raises(ValueError, match="test-only"):
        build_reddit_provider()
