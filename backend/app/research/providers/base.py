"""Research search provider contract."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


class ResearchProviderError(RuntimeError):
    """Safe search-provider failure."""


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    publisher: str
    excerpt: str
    source_type: str
    retrieved_at: datetime
    publication_date: str | None = None
    relevance: float = 0.5


class ResearchSourceProvider(Protocol):
    name: str

    def search(self, query: str, *, limit: int) -> list[SearchResult]: ...
