"""Documented MediaWiki API search provider."""

import json
import re
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from backend.app.core.config import settings
from backend.app.research.providers.base import ResearchProviderError, SearchResult


class WikipediaSearchProvider:
    """Search Wikipedia for discovery using its documented API."""

    name = "wikipedia_mediawiki"
    api_url = "https://en.wikipedia.org/w/api.php"

    def search(self, query: str, *, limit: int) -> list[SearchResult]:
        params = urlencode(
            {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": min(limit, 10),
                "format": "json",
                "utf8": "1",
            }
        )
        request = Request(
            f"{self.api_url}?{params}",
            headers={"User-Agent": "ViralForgeAI/0.1 research"},
        )
        try:
            with urlopen(
                request, timeout=min(settings.research_timeout_seconds, 30)
            ) as response:  # noqa: S310
                payload = json.load(response)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ResearchProviderError(
                "Research source provider is unavailable"
            ) from exc
        rows = payload.get("query", {}).get("search", [])
        now = datetime.now(UTC)
        results = []
        for rank, row in enumerate(rows):
            title = str(row.get("title", "")).strip()
            excerpt = re.sub(r"<[^>]+>", "", str(row.get("snippet", ""))).strip()
            page_id = row.get("pageid")
            if not title or not excerpt or page_id is None:
                continue
            results.append(
                SearchResult(
                    title=title,
                    url=f"https://en.wikipedia.org/?curid={page_id}",
                    publisher="Wikipedia",
                    excerpt=excerpt[:600],
                    source_type="encyclopedia",
                    retrieved_at=now,
                    relevance=max(0.1, round(1.0 - rank * 0.08, 2)),
                )
            )
        return results


class CrossrefSearchProvider:
    """Discover scholarly literature through Crossref's documented REST API."""

    name = "crossref"
    api_url = "https://api.crossref.org/works"

    def search(self, query: str, *, limit: int) -> list[SearchResult]:
        params = urlencode(
            {
                "query": query,
                "rows": min(limit, 5),
                "select": "DOI,title,abstract,published,container-title,URL",
            }
        )
        request = Request(
            f"{self.api_url}?{params}",
            headers={"User-Agent": "ViralForgeAI/0.1 (mailto:research@localhost)"},
        )
        try:
            with urlopen(
                request, timeout=min(settings.research_timeout_seconds, 30)
            ) as response:  # noqa: S310
                payload = json.load(response)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ResearchProviderError(
                "Scholarly source provider is unavailable"
            ) from exc
        now = datetime.now(UTC)
        results = []
        for rank, row in enumerate(payload.get("message", {}).get("items", [])):
            titles = row.get("title") or []
            title = str(titles[0]).strip() if titles else ""
            abstract = re.sub(r"<[^>]+>", "", str(row.get("abstract", ""))).strip()
            containers = row.get("container-title") or []
            publisher = (
                str(containers[0]).strip()
                if containers
                else "Crossref-indexed publication"
            )
            url = str(row.get("URL", "")).strip()
            if not title or not abstract or not url:
                continue
            date_parts = row.get("published", {}).get("date-parts", [])
            publication_date = (
                "-".join(str(part) for part in date_parts[0]) if date_parts else None
            )
            results.append(
                SearchResult(
                    title=title,
                    url=url,
                    publisher=publisher,
                    excerpt=abstract[:600],
                    source_type="peer_reviewed",
                    retrieved_at=now,
                    publication_date=publication_date,
                    relevance=max(0.1, round(0.9 - rank * 0.08, 2)),
                )
            )
        return results


class MetMuseumSearchProvider:
    """Retrieve first-party object evidence from The Met Collection API."""

    name = "met_museum"
    api_url = "https://collectionapi.metmuseum.org/public/collection/v1"

    def search(self, query: str, *, limit: int) -> list[SearchResult]:
        dimensions = (
            "overview",
            "history",
            "timeline dates",
            "key people",
            "locations",
            "myths misconceptions",
            "controversies",
            "archaeology evidence",
            "surprising facts",
            "frequently asked questions",
            "museum",
            "documentary visuals",
        )
        collection_query = query
        for dimension in dimensions:
            suffix = f" {dimension}"
            if collection_query.lower().endswith(suffix):
                collection_query = collection_query[: -len(suffix)]
                break
        try:
            search_request = Request(
                f"{self.api_url}/search?{urlencode({'q': collection_query})}",
                headers={"User-Agent": "ViralForgeAI/0.1 research"},
            )
            with urlopen(
                search_request, timeout=min(settings.research_timeout_seconds, 30)
            ) as response:  # noqa: S310
                object_ids = (json.load(response).get("objectIDs") or [])[
                    : min(limit, 3)
                ]
            results = []
            now = datetime.now(UTC)
            for rank, object_id in enumerate(object_ids):
                request = Request(
                    f"{self.api_url}/objects/{object_id}",
                    headers={"User-Agent": "ViralForgeAI/0.1 research"},
                )
                with urlopen(
                    request, timeout=min(settings.research_timeout_seconds, 30)
                ) as response:  # noqa: S310
                    item = json.load(response)
                title = str(item.get("title", "")).strip()
                url = str(item.get("objectURL", "")).strip()
                details = [
                    item.get("objectName"),
                    item.get("period"),
                    item.get("dynasty"),
                    item.get("objectDate"),
                    item.get("geographyType"),
                    item.get("city"),
                    item.get("country"),
                    item.get("medium"),
                ]
                excerpt = "; ".join(str(value).strip() for value in details if value)
                if title and url and excerpt:
                    results.append(
                        SearchResult(
                            title=title,
                            url=url,
                            publisher="The Metropolitan Museum of Art",
                            excerpt=excerpt[:600],
                            source_type="museum_collection",
                            retrieved_at=now,
                            relevance=max(0.1, round(0.95 - rank * 0.08, 2)),
                        )
                    )
            return results
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ResearchProviderError(
                "Museum source provider is unavailable"
            ) from exc


class CompositeResearchProvider:
    """Combine independent documented providers while tolerating partial failure."""

    name = "wikipedia_crossref"

    def __init__(self) -> None:
        self.providers = (
            MetMuseumSearchProvider(),
            CrossrefSearchProvider(),
            WikipediaSearchProvider(),
        )

    def search(self, query: str, *, limit: int) -> list[SearchResult]:
        results: list[SearchResult] = []
        errors = 0
        for provider in self.providers:
            try:
                provider_limit = 3 if provider.name == "met_museum" else 2
                results.extend(provider.search(query, limit=provider_limit))
            except ResearchProviderError:
                errors += 1
        if errors == len(self.providers):
            raise ResearchProviderError("All research source providers are unavailable")
        return results[:limit]
