"""TikTok connector placeholder."""

from collections.abc import Mapping
from typing import Any

from backend.app.connectors.base import BaseConnector
from backend.app.domain.content import Content


class TikTokConnector(BaseConnector[Content]):
    """Connector placeholder for TikTok."""

    def fetch(self, **kwargs: Any) -> list[Mapping[str, Any]]:
        raise NotImplementedError

    def normalize(self, raw_content: Mapping[str, Any]) -> Content:
        raise NotImplementedError

    def validate(self, raw_content: Mapping[str, Any]) -> None:
        raise NotImplementedError
