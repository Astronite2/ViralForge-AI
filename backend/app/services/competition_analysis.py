"""Transparent competition analysis over normalized YouTube content."""

from dataclasses import dataclass
from datetime import UTC, datetime
from statistics import median

from backend.app.domain.content import Content


@dataclass(frozen=True, slots=True)
class CompetitionResult:
    competition_score: float
    confidence: float
    saturation_level: str
    market_gap: str
    competitor_summary: str
    evidence: tuple[dict[str, object], ...]
    metrics: dict[str, float | int | None]


class CompetitionAnalyzer:
    """Calculate competition without treating a small sample as a market census."""

    def analyze(
        self,
        query: str,
        contents: list[Content],
        *,
        observed_at: datetime | None = None,
    ) -> CompetitionResult:
        now = observed_at or datetime.now(UTC)
        views = [
            float(item.metrics["view_count"])
            for item in contents
            if "view_count" in item.metrics
        ]
        subscribers = [
            float(item.metrics["subscriber_count"])
            for item in contents
            if item.metrics.get("subscriber_count", 0) > 0
        ]
        ratios = [
            float(item.metrics["view_count"]) / float(item.metrics["subscriber_count"])
            for item in contents
            if item.metrics.get("subscriber_count", 0) > 0
            and "view_count" in item.metrics
        ]
        ages = [
            max((now - item.published_at).total_seconds() / 86400, 0)
            for item in contents
        ]
        large_dominance = (
            sum(item.metrics.get("subscriber_count", 0) >= 500_000 for item in contents)
            / len(contents)
            if contents
            else 0.0
        )
        similarities = [self._similarity(query, item.title) for item in contents]
        recent_share = sum(age <= 30 for age in ages) / len(ages) if ages else 0.0
        sample_pressure = min(len(contents) / 20.0, 1.0)
        similarity_pressure = (
            sum(similarities) / len(similarities) if similarities else 0.0
        )
        score = round(
            100
            * (
                0.35 * sample_pressure
                + 0.25 * similarity_pressure
                + 0.20 * recent_share
                + 0.20 * large_dominance
            ),
            1,
        )
        confidence = round(min(len(contents) / 15.0, 1.0) * 100, 1)
        freshness_gap = round((1.0 - recent_share) * 100, 1)
        saturation = (
            "high" if score >= 70 else "medium" if score >= 40 else "low_or_uncertain"
        )
        if len(contents) < 8:
            market_gap = "Insufficient sample to claim low competition."
        elif freshness_gap >= 60:
            market_gap = "Older competing results suggest a possible freshness gap."
        elif large_dominance >= 0.6:
            market_gap = (
                "Results are dominated by large channels; differentiation is required."
            )
        else:
            market_gap = "No strong freshness gap is visible in the retrieved sample."
        return CompetitionResult(
            competition_score=score,
            confidence=confidence,
            saturation_level=saturation,
            market_gap=market_gap,
            competitor_summary=(
                f"{len(contents)} retrieved videos; median views "
                f"{self._median(views):,.0f}; "
                f"large-channel share {large_dominance:.0%}."
            ),
            evidence=tuple(
                {
                    "content_id": item.id,
                    "title": item.title,
                    "url": item.url,
                    "view_count": item.metrics.get("view_count"),
                    "subscriber_count": item.metrics.get("subscriber_count"),
                    "published_at": item.published_at.isoformat(),
                }
                for item in contents
            ),
            metrics={
                "sample_size": len(contents),
                "median_views": self._median(views),
                "median_channel_size": self._median(subscribers),
                "median_view_to_subscriber_ratio": self._median(ratios),
                "median_age_days": self._median(ages),
                "recent_upload_share": round(recent_share, 4),
                "title_similarity": round(similarity_pressure, 4),
                "large_channel_dominance": round(large_dominance, 4),
                "content_freshness_gap": freshness_gap,
            },
        )

    @staticmethod
    def _similarity(query: str, title: str) -> float:
        query_words = {word for word in query.lower().split() if len(word) > 2}
        title_words = {word for word in title.lower().split() if len(word) > 2}
        return (
            len(query_words & title_words) / len(query_words | title_words)
            if query_words | title_words
            else 0.0
        )

    @staticmethod
    def _median(values: list[float]) -> float:
        return round(median(values), 2) if values else 0.0
