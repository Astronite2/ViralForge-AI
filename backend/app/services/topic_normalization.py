"""Deterministic topic normalization and lookup."""

from __future__ import annotations

import re

from backend.app.models.topic import Topic
from backend.app.repositories.topic import TopicRepository


class TopicNormalizationService:
    """Normalize display names and reuse topics by normalized key."""

    _whitespace_pattern = re.compile(r"\s+")

    def __init__(self, repository: TopicRepository) -> None:
        self.repository = repository

    def normalize_display_name(self, value: str) -> tuple[str, str]:
        display_name = self._collapse_whitespace(value)
        normalized_key = display_name.lower()
        return display_name, normalized_key

    def resolve(self, value: str) -> Topic:
        display_name, normalized_key = self.normalize_display_name(value)
        return self.repository.get_or_create(display_name, normalized_key)

    @classmethod
    def _collapse_whitespace(cls, value: str) -> str:
        return cls._whitespace_pattern.sub(" ", value.strip())
