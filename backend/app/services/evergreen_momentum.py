"""Deterministic evergreen and current-momentum analysis."""

from dataclasses import dataclass
from datetime import UTC, datetime
from statistics import median

from backend.app.domain.content import Content

_EVENT_TERMS = {"today", "breaking", "election", "live", "2026", "news", "update"}


@dataclass(frozen=True, slots=True)
class LongevityResult:
    evergreen_score: float
    momentum_score: float
    opportunity_type: str
    confidence: float
    trace: tuple[str, ...]


class EvergreenMomentumAnalyzer:
    def analyze(
        self,
        query: str,
        contents: list[Content],
        *,
        observed_at: datetime | None = None,
    ) -> LongevityResult:
        now = observed_at or datetime.now(UTC)
        ages = [
            max((now - item.published_at).total_seconds() / 86400, 0)
            for item in contents
        ]
        velocities = [float(item.metrics.get("view_velocity", 0)) for item in contents]
        views = [float(item.metrics.get("view_count", 0)) for item in contents]
        successful_threshold = median(views) if views else 0
        older_success = (
            sum(
                age >= 90 and view >= successful_threshold
                for age, view in zip(ages, views, strict=True)
            )
            / len(contents)
            if contents
            else 0.0
        )
        event_specific = any(term in query.lower().split() for term in _EVENT_TERMS)
        age_spread = min((max(ages) - min(ages)) / 365.0, 1.0) if ages else 0.0
        evergreen = round(
            100
            * (0.55 * older_success + 0.30 * age_spread + 0.15 * (not event_specific)),
            1,
        )
        recent = [
            velocity
            for velocity, age in zip(velocities, ages, strict=True)
            if age <= 30
        ]
        recent_share = len(recent) / len(contents) if contents else 0.0
        velocity_strength = min((median(recent) if recent else 0) / 10_000.0, 1.0)
        momentum = round(100 * (0.55 * velocity_strength + 0.45 * recent_share), 1)
        if event_specific and momentum >= 55:
            kind = "temporary_event"
        elif evergreen >= 60 and momentum >= 50:
            kind = "trending_and_evergreen"
        elif evergreen >= 60:
            kind = "evergreen_opportunity"
        elif momentum >= 50:
            kind = "trending_now"
        else:
            kind = "uncertain"
        return LongevityResult(
            evergreen_score=evergreen,
            momentum_score=momentum,
            opportunity_type=kind,
            confidence=round(min(len(contents) / 15.0, 1.0) * 100, 1),
            trace=(
                f"Older successful video share: {older_success:.0%}.",
                f"Recent upload share: {recent_share:.0%}.",
                f"Event-specific wording detected: {event_specific}.",
            ),
        )
