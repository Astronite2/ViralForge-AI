"""Pipeline stage contracts."""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from backend.app.domain.content import Content


class ContentStage(ABC):
    """A stage that transforms normalized content."""

    @abstractmethod
    def process(self, content: Content) -> Content:
        """Process content and return a new normalized object."""


class RawContentValidator(ABC):
    """A stage that validates connector payloads before normalization."""

    @abstractmethod
    def validate(self, raw_content: Mapping[str, Any]) -> None:
        """Validate a raw connector payload."""
