"""Platform connector contract."""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any


class BaseConnector[TNormalized](ABC):
    """Interface implemented by external platform connectors."""

    @abstractmethod
    def fetch(self, **kwargs: Any) -> list[Mapping[str, Any]]:
        """Fetch raw payloads from a platform source."""
        raise NotImplementedError

    @abstractmethod
    def normalize(self, raw_content: Mapping[str, Any]) -> TNormalized:
        """Convert platform data into a shared domain object."""
        raise NotImplementedError

    @abstractmethod
    def validate(self, raw_content: Mapping[str, Any]) -> None:
        """Validate the platform payload before pipeline processing."""
        raise NotImplementedError
