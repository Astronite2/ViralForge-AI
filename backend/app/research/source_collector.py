"""Normalize, classify, deduplicate, and rank research sources."""

import hashlib
from dataclasses import asdict
from enum import StrEnum
from urllib.parse import urlparse

from backend.app.research.providers.base import ResearchSourceProvider, SearchResult


class SourceQuality(StrEnum):
    PRIMARY = "PRIMARY"
    AUTHORITATIVE = "AUTHORITATIVE"
    REPUTABLE_SECONDARY = "REPUTABLE_SECONDARY"
    GENERAL_REFERENCE = "GENERAL_REFERENCE"
    COMMUNITY = "COMMUNITY"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"


def classify_source(result: SearchResult) -> tuple[SourceQuality, str]:
    domain = urlparse(result.url).netloc.lower().removeprefix("www.")
    if domain.endswith(".gov") or ".gov." in domain:
        return SourceQuality.PRIMARY, "Official government domain"
    if domain.endswith(".edu") or ".ac." in domain:
        return SourceQuality.AUTHORITATIVE, "University or academic domain"
    if any(token in domain for token in ("museum", "si.edu", "unesco.org")):
        return SourceQuality.AUTHORITATIVE, "Recognized museum or institution"
    if result.source_type in {"journal", "peer_reviewed"}:
        return SourceQuality.AUTHORITATIVE, "Scholarly publication metadata"
    if domain.endswith("wikipedia.org"):
        return SourceQuality.GENERAL_REFERENCE, "General reference used for discovery"
    if any(token in domain for token in ("reddit.com", "forum", "quora.com")):
        return SourceQuality.COMMUNITY, "Community-authored content"
    if result.publisher and result.publication_date:
        return SourceQuality.REPUTABLE_SECONDARY, "Named publisher and publication date"
    return SourceQuality.LOW_CONFIDENCE, "No deterministic authority signal detected"


class SourceCollector:
    def __init__(self, provider: ResearchSourceProvider, *, max_sources: int) -> None:
        self.provider = provider
        self.max_sources = max_sources

    def collect(self, queries: list[str]) -> list[dict[str, object]]:
        unique: dict[str, SearchResult] = {}
        for query in queries:
            for result in self.provider.search(query, limit=5):
                key = result.url.split("#", 1)[0].rstrip("/").lower()
                current = unique.get(key)
                if current is None or result.relevance > current.relevance:
                    unique[key] = result
                if len(unique) >= self.max_sources:
                    break
            if len(unique) >= self.max_sources:
                break
        normalized = []
        for result in unique.values():
            quality, reason = classify_source(result)
            domain = urlparse(result.url).netloc.lower().removeprefix("www.")
            source_id = "src_" + hashlib.sha256(result.url.encode()).hexdigest()[:12]
            normalized.append(
                {
                    "id": source_id,
                    **asdict(result),
                    "retrieved_at": result.retrieved_at.isoformat(),
                    "domain": domain,
                    "source_quality": quality.value,
                    "authority_reason": reason,
                }
            )
        order = {quality.value: rank for rank, quality in enumerate(SourceQuality)}
        return sorted(
            normalized,
            key=lambda item: (
                order[str(item["source_quality"])],
                -float(item["relevance"]),
                str(item["title"]),
            ),
        )[: self.max_sources]
