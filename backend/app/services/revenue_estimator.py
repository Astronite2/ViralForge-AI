"""Conservative, explicitly sourced YouTube revenue-range estimation."""

from dataclasses import dataclass
from statistics import median

from backend.app.core.config import settings
from backend.app.domain.content import Content


@dataclass(frozen=True, slots=True)
class EstimateRange:
    low: float | None
    base: float | None
    high: float | None
    basis: str

    def payload(self) -> dict[str, float | str | None]:
        return {
            "low": self.low,
            "base": self.base,
            "high": self.high,
            "basis": self.basis,
        }


@dataclass(frozen=True, slots=True)
class RevenueEstimate:
    views: EstimateRange
    rpm: EstimateRange
    revenue: EstimateRange
    confidence: float
    assumptions: tuple[str, ...]
    limitations: tuple[str, ...]
    niche_category: str
    benchmark_version: str


class RevenueEstimator:
    """Estimate ranges without asserting future earnings or hidden channel history."""

    def estimate(
        self,
        *,
        query: str,
        contents: list[Content],
        monetization_safety: float,
        niche_category: str | None = None,
    ) -> RevenueEstimate:
        category = niche_category or self.category_for(query)
        observed_views = sorted(
            float(item.metrics["view_count"])
            for item in contents
            if item.metrics.get("view_count") is not None
        )
        if len(observed_views) >= 3:
            view_range = EstimateRange(
                low=self._round_count(self._percentile(observed_views, 0.25)),
                base=self._round_count(median(observed_views)),
                high=self._round_count(self._percentile(observed_views, 0.75)),
                basis="observed",
            )
            view_assumption = (
                "View range uses the retrieved YouTube comparison sample, "
                "not channel history."
            )
        else:
            view_range = EstimateRange(None, None, None, "unavailable")
            view_assumption = (
                "No view range is shown because fewer than three comparable "
                "videos were observed."
            )

        observed_rpm = sorted(
            float(item.metadata["rpm"])
            for item in contents
            if isinstance(item.metadata.get("rpm"), int | float)
            and float(item.metadata["rpm"]) >= 0
        )
        if len(observed_rpm) >= 3:
            rpm_range = EstimateRange(
                round(self._percentile(observed_rpm, 0.25), 2),
                round(median(observed_rpm), 2),
                round(self._percentile(observed_rpm, 0.75), 2),
                "observed",
            )
            rpm_assumption = "RPM range uses explicitly stored comparable observations."
        else:
            benchmark = settings.rpm_benchmarks.get(
                category, settings.rpm_benchmarks["general"]
            )
            safety_multiplier = max(min(monetization_safety / 100.0, 1.0), 0.0)
            rpm_range = EstimateRange(
                round(benchmark[0] * safety_multiplier, 2),
                round(benchmark[1] * safety_multiplier, 2),
                round(benchmark[2] * safety_multiplier, 2),
                "benchmark",
            )
            rpm_assumption = (
                f"RPM uses configurable {category} benchmark assumptions "
                f"({settings.revenue_benchmark_version}), adjusted by "
                "monetization safety."
            )

        if view_range.base is None or rpm_range.base is None:
            revenue_range = EstimateRange(None, None, None, "unavailable")
        else:
            revenue_range = EstimateRange(
                round(view_range.low * rpm_range.low / 1000, 0),
                round(view_range.base * rpm_range.base / 1000, 0),
                round(view_range.high * rpm_range.high / 1000, 0),
                (
                    "observed_views_benchmark_rpm"
                    if rpm_range.basis == "benchmark"
                    else "observed"
                ),
            )
        sample_confidence = min(len(observed_views) / 15.0, 1.0)
        rpm_confidence = 1.0 if rpm_range.basis == "observed" else 0.45
        confidence = round(100 * (0.7 * sample_confidence + 0.3 * rpm_confidence), 1)
        return RevenueEstimate(
            views=view_range,
            rpm=rpm_range,
            revenue=revenue_range,
            confidence=confidence,
            assumptions=(
                view_assumption,
                rpm_assumption,
                "Revenue equals views × RPM ÷ 1,000.",
            ),
            limitations=(
                "Estimates are ranges, not guaranteed earnings.",
                "Retrieved competitor performance may not represent this "
                "channel's results.",
                "Actual RPM varies by geography, season, viewer, format, and "
                "advertiser demand.",
            ),
            niche_category=category,
            benchmark_version=settings.revenue_benchmark_version,
        )

    @staticmethod
    def category_for(query: str) -> str:
        text = query.lower()
        categories = {
            "finance": ("finance", "invest", "money", "bank", "tax"),
            "business": ("business", "marketing", "sales", "entrepreneur"),
            "technology": ("technology", "software", "ai", "computer", "gadget"),
            "careers": ("career", "job", "resume", "interview"),
            "education": ("learn", "education", "science", "math", "course"),
            "history": ("history", "ancient", "empire", "archaeology"),
            "travel": ("travel", "hotel", "flight", "destination"),
            "gaming": ("gaming", "game", "xbox", "playstation"),
            "entertainment": ("celebrity", "movie", "music", "entertainment"),
        }
        return next(
            (
                category
                for category, words in categories.items()
                if any(word in text for word in words)
            ),
            "general",
        )

    @staticmethod
    def _percentile(values: list[float], fraction: float) -> float:
        return values[round((len(values) - 1) * fraction)]

    @staticmethod
    def _round_count(value: float) -> float:
        magnitude = 1000 if value >= 10_000 else 100
        return float(round(value / magnitude) * magnitude)
