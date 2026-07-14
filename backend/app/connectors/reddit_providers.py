"""OAuth-only provider boundary for Reddit's documented Data API."""

from __future__ import annotations

import base64
import json
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from backend.app.connectors.errors import (
    ConnectorConfigurationRequiredError,
    ConnectorDisabledError,
    ConnectorProviderUnavailableError,
    ConnectorRateLimitError,
    ConnectorTransientError,
)


class RedditProviderError(RuntimeError):
    """Base Reddit provider error."""


class RedditDisabledError(ConnectorDisabledError, RedditProviderError):
    """Reddit is intentionally disabled."""


class RedditConfigurationError(
    ConnectorConfigurationRequiredError, RedditProviderError
):
    """OAuth configuration is incomplete or invalid."""


class RedditAuthenticationError(ConnectorProviderUnavailableError, RedditProviderError):
    """Reddit rejected the configured OAuth identity."""


class RedditForbiddenError(ConnectorProviderUnavailableError, RedditProviderError):
    """Reddit denied access to the requested resource."""


class RedditRequestError(ConnectorProviderUnavailableError, RedditProviderError):
    """Reddit permanently rejected a documented API request."""


class RedditRateLimitError(ConnectorRateLimitError, RedditProviderError):
    """Reddit rate-limited the provider."""


class RedditTemporaryError(ConnectorTransientError, RedditProviderError):
    """Reddit or the network is temporarily unavailable."""


class RedditMalformedResponseError(
    ConnectorProviderUnavailableError, RedditProviderError
):
    """Reddit returned a response outside the documented listing shape."""


@dataclass(frozen=True, slots=True)
class RedditRateLimit:
    remaining: float | None = None
    used: float | None = None
    reset_seconds: float | None = None


@dataclass(frozen=True, slots=True)
class RedditProviderResult:
    items: tuple[Mapping[str, Any], ...]
    retrieved_at: datetime
    rate_limit: RedditRateLimit = RedditRateLimit()
    fixture_backed: bool = False


class RedditProvider(Protocol):
    provider_name: str
    experimental: bool

    @property
    def is_enabled(self) -> bool: ...

    @property
    def authentication_ready(self) -> bool: ...

    def search_posts(
        self,
        *,
        query: str,
        subreddits: Sequence[str],
        sort: str,
        time_filter: str,
        limit: int,
    ) -> RedditProviderResult: ...

    def diagnostics(self) -> Mapping[str, Any]: ...


class DisabledRedditProvider:
    provider_name = "disabled"
    experimental = False
    is_enabled = False
    authentication_ready = False

    def search_posts(self, **_: Any) -> RedditProviderResult:
        raise RedditDisabledError("Reddit connector is disabled by configuration.")

    def diagnostics(self) -> Mapping[str, Any]:
        return {"enabled": False, "authentication_ready": False}


JsonRequester = Callable[
    [str, str, Mapping[str, str], bytes | None, float],
    tuple[int, Mapping[str, str], Mapping[str, Any]],
]


class OfficialRedditProvider:
    """Confidential-client OAuth provider for Reddit's documented Data API."""

    provider_name = "reddit_data_api"
    experimental = False
    is_enabled = True
    token_url = "https://www.reddit.com/api/v1/access_token"
    api_base_url = "https://oauth.reddit.com"

    def __init__(
        self,
        *,
        client_id: str | None,
        client_secret: str | None,
        user_agent: str,
        timeout_seconds: float = 20.0,
        max_retries: int = 2,
        backoff_seconds: float = 1.0,
        requester: JsonRequester | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._client_id = (client_id or "").strip()
        self._client_secret = (client_secret or "").strip()
        self._user_agent = user_agent.strip()
        self._timeout = timeout_seconds
        self._max_retries = max_retries
        self._backoff = backoff_seconds
        self._requester = requester or _request_json
        self._sleeper = sleeper
        self._clock = clock
        self._access_token: str | None = None
        self._token_expires_at = 0.0
        self._validate_configuration()

    @property
    def authentication_ready(self) -> bool:
        return bool(self._client_id and self._client_secret)

    def diagnostics(self) -> Mapping[str, Any]:
        return {
            "enabled": True,
            "authentication_ready": self.authentication_ready,
            "oauth_flow": "client_credentials",
        }

    def search_posts(
        self,
        *,
        query: str,
        subreddits: Sequence[str],
        sort: str,
        time_filter: str,
        limit: int,
    ) -> RedditProviderResult:
        scopes = tuple(subreddits) or ("",)
        collected: dict[str, Mapping[str, Any]] = {}
        latest_rate = RedditRateLimit()
        for subreddit in scopes:
            path = f"/r/{subreddit}/search" if subreddit else "/search"
            params: dict[str, object] = {
                "q": query,
                "sort": sort,
                "t": time_filter,
                "limit": limit,
                "type": "link",
                "raw_json": 1,
            }
            if subreddit:
                params["restrict_sr"] = "on"
            payload, headers = self._authorized_get(path, params)
            for item in self._listing_items(payload):
                item_id = str(item.get("id", "")).strip()
                if item_id and item_id not in collected:
                    collected[item_id] = item
                if len(collected) >= limit:
                    break
            latest_rate = _rate_limit(headers)
            if len(collected) >= limit:
                break
        return RedditProviderResult(
            items=tuple(collected.values()),
            retrieved_at=datetime.now(UTC),
            rate_limit=latest_rate,
        )

    def _authorized_get(
        self, path: str, params: Mapping[str, object]
    ) -> tuple[Mapping[str, Any], Mapping[str, str]]:
        renewed = False
        while True:
            token = self._token()
            status, headers, payload = self._request_with_retries(
                "GET",
                f"{self.api_base_url}{path}?{urlencode(params)}",
                {
                    "Authorization": f"Bearer {token}",
                    "User-Agent": self._user_agent,
                    "Accept": "application/json",
                },
                None,
            )
            if status == 401 and not renewed:
                self._access_token = None
                renewed = True
                continue
            self._raise_for_status(status)
            return payload, headers

    def _token(self) -> str:
        if not self.authentication_ready:
            raise RedditConfigurationError(
                "Reddit OAuth client ID and client secret are required."
            )
        if self._access_token and self._clock() < self._token_expires_at - 30:
            return self._access_token
        basic = base64.b64encode(
            f"{self._client_id}:{self._client_secret}".encode()
        ).decode()
        status, _, payload = self._request_with_retries(
            "POST",
            self.token_url,
            {
                "Authorization": f"Basic {basic}",
                "User-Agent": self._user_agent,
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            urlencode({"grant_type": "client_credentials"}).encode(),
        )
        if status in {400, 401}:
            raise RedditAuthenticationError("Reddit OAuth credentials were rejected.")
        self._raise_for_status(status)
        token = payload.get("access_token")
        expires_in = payload.get("expires_in")
        if (
            not isinstance(token, str)
            or not token.strip()
            or not isinstance(expires_in, int | float)
        ):
            raise RedditMalformedResponseError(
                "Reddit OAuth returned an invalid token response."
            )
        self._access_token = token
        self._token_expires_at = self._clock() + float(expires_in)
        return token

    def _request_with_retries(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        data: bytes | None,
    ) -> tuple[int, Mapping[str, str], Mapping[str, Any]]:
        for attempt in range(self._max_retries + 1):
            try:
                status, response_headers, payload = self._requester(
                    method, url, headers, data, self._timeout
                )
            except (TimeoutError, URLError) as exc:
                if attempt >= self._max_retries:
                    raise RedditTemporaryError(
                        "Reddit Data API is temporarily unreachable."
                    ) from exc
                self._sleeper(self._backoff * (2**attempt))
                continue
            if status == 429 or status >= 500:
                if attempt < self._max_retries:
                    self._sleeper(self._backoff * (2**attempt))
                    continue
                if status == 429:
                    raise RedditRateLimitError(
                        "Reddit Data API rate limit was reached."
                    )
                raise RedditTemporaryError(
                    "Reddit Data API is temporarily unavailable."
                )
            return status, response_headers, payload
        raise AssertionError("retry loop exhausted")  # pragma: no cover

    @staticmethod
    def _listing_items(payload: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
        data = payload.get("data")
        children = data.get("children") if isinstance(data, Mapping) else None
        if not isinstance(children, list):
            raise RedditMalformedResponseError(
                "Reddit Data API returned an invalid listing response."
            )
        items: list[Mapping[str, Any]] = []
        for child in children:
            if not isinstance(child, Mapping) or child.get("kind") != "t3":
                continue
            post = child.get("data")
            if isinstance(post, Mapping):
                items.append(post)
        return tuple(items)

    @staticmethod
    def _raise_for_status(status: int) -> None:
        if 200 <= status < 300:
            return
        if status == 401:
            raise RedditAuthenticationError("Reddit OAuth authorization failed.")
        if status == 403:
            raise RedditForbiddenError("Reddit denied access to the requested data.")
        if status == 429:
            raise RedditRateLimitError("Reddit Data API rate limit was reached.")
        if 400 <= status < 500:
            raise RedditRequestError("Reddit rejected the Data API request.")
        raise RedditTemporaryError("Reddit Data API is temporarily unavailable.")

    def _validate_configuration(self) -> None:
        if not self._user_agent or len(self._user_agent) < 5:
            raise RedditConfigurationError(
                "A descriptive Reddit User-Agent is required."
            )
        if any(character in self._user_agent for character in "\r\n"):
            raise RedditConfigurationError(
                "Reddit User-Agent contains unsafe characters."
            )
        if self._timeout <= 0 or self._max_retries < 0 or self._backoff < 0:
            raise RedditConfigurationError(
                "Reddit retry and timeout settings are invalid."
            )


class FixtureRedditProvider:
    """Deterministic provider for tests only."""

    provider_name = "fixture"
    experimental = False
    is_enabled = True
    authentication_ready = True

    def __init__(self, items: Sequence[Mapping[str, Any]] = ()) -> None:
        self._items = tuple(dict(item) for item in items)

    def search_posts(self, **_: Any) -> RedditProviderResult:
        return RedditProviderResult(
            items=self._items,
            retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
            fixture_backed=True,
        )

    def diagnostics(self) -> Mapping[str, Any]:
        return {
            "enabled": True,
            "authentication_ready": True,
            "fixture_backed": True,
        }


def _request_json(
    method: str,
    url: str,
    headers: Mapping[str, str],
    data: bytes | None,
    timeout: float,
) -> tuple[int, Mapping[str, str], Mapping[str, Any]]:
    request = Request(url, data=data, headers=dict(headers), method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            status = response.status
            response_headers = dict(response.headers.items())
            body = response.read()
    except HTTPError as exc:
        status = exc.code
        response_headers = dict(exc.headers.items()) if exc.headers else {}
        body = exc.read()
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RedditMalformedResponseError(
            "Reddit Data API returned malformed JSON."
        ) from exc
    if not isinstance(payload, Mapping):
        raise RedditMalformedResponseError(
            "Reddit Data API response must be a JSON object."
        )
    return status, response_headers, payload


def _rate_limit(headers: Mapping[str, str]) -> RedditRateLimit:
    lower = {key.lower(): value for key, value in headers.items()}
    return RedditRateLimit(
        remaining=_optional_float(lower.get("x-ratelimit-remaining")),
        used=_optional_float(lower.get("x-ratelimit-used")),
        reset_seconds=_optional_float(lower.get("x-ratelimit-reset")),
    )


def _optional_float(value: object) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
