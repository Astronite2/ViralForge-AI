"""Deterministic YouTube money-opportunity scoring engine."""

import math
from statistics import median
from typing import Any

from backend.app.core.config import settings
from backend.app.domain.content import Content
from backend.app.schemas.money_opportunity import ChannelProfileInput
from backend.app.services.competition_analysis import CompetitionAnalyzer
from backend.app.services.evergreen_momentum import EvergreenMomentumAnalyzer
from backend.app.services.revenue_estimator import RevenueEstimator

_UNSAFE_TERMS = {"graphic", "violence", "weapon", "hate", "explicit", "drug", "suicide"}


class MoneyOpportunityEngine:
    """Rank relative attractiveness; this score is not a revenue guarantee."""

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self.weights = weights or settings.money_opportunity_weights
        if any(value < 0 for value in self.weights.values()) or not sum(
            self.weights.values()
        ):
            raise ValueError(
                "Money opportunity weights must be non-negative and non-empty"
            )
        self.competition = CompetitionAnalyzer()
        self.longevity = EvergreenMomentumAnalyzer()
        self.revenue = RevenueEstimator()

    def score(
        self,
        *,
        query: str,
        angle: str,
        contents: list[Content],
        profile: ChannelProfileInput | None = None,
        angle_index: int = 0,
    ) -> dict[str, Any]:
        competition = self.competition.analyze(query, contents)
        longevity = self.longevity.analyze(query, contents)
        view_counts = [float(item.metrics.get("view_count", 0)) for item in contents]
        engagement_rates = [
            float(item.metrics.get("engagement_rate", 0)) for item in contents
        ]
        durations = [
            float(item.duration_seconds or 0) / 60
            for item in contents
            if item.duration_seconds
        ]
        demand = self._log_score(median(view_counts) if view_counts else 0, 1_000_000)
        audience = round(
            100 * min((median(engagement_rates) if engagement_rates else 0) / 0.08, 1),
            1,
        )
        watch = round(100 * min((median(durations) if durations else 0) / 12, 1), 1)
        ctr = self._ctr_potential(angle)
        difficulty = min(
            42 + angle_index * 12 + (10 if "evidence" in angle.lower() else 0), 90
        )
        production_hours = round(4 + difficulty * 0.12, 1)
        unsafe_matches = sorted(
            term for term in _UNSAFE_TERMS if term in f"{query} {angle}".lower()
        )
        safety = max(100 - 25 * len(unsafe_matches), 20)
        category = self.revenue.category_for(query)
        advertiser = round(min(settings.rpm_benchmarks[category][1] / 12.0, 1) * 100, 1)
        channel_fit = self._channel_fit(query, production_hours, profile)
        sample_confidence = min(len(contents) / 15.0, 1.0) * 100
        evidence_confidence = round(
            (sample_confidence + competition.confidence + longevity.confidence) / 3, 1
        )
        values: dict[str, float | None] = {
            "demand": demand,
            "momentum": longevity.momentum_score,
            "competition_opportunity": 100 - competition.competition_score,
            "evergreen": longevity.evergreen_score,
            "advertiser_value": advertiser,
            "audience_value": audience,
            "watch_time_potential": watch,
            "click_through_potential": ctr,
            "production_feasibility": 100 - difficulty,
            "monetization_safety": safety,
            "evidence_confidence": evidence_confidence,
            "channel_fit": channel_fit,
        }
        active_weights = {
            name: weight
            for name, weight in self.weights.items()
            if values.get(name) is not None
        }
        weight_total = sum(active_weights.values())
        normalized_weights = {
            name: weight / weight_total for name, weight in active_weights.items()
        }
        trace = [
            {
                "factor": name,
                "input": values[name],
                "weight": round(weight, 4),
                "contribution": round(float(values[name]) * weight, 4),
            }
            for name, weight in normalized_weights.items()
        ]
        score = round(sum(float(item["contribution"]) for item in trace), 1)
        estimate = self.revenue.estimate(
            query=query,
            contents=contents,
            monetization_safety=safety,
            niche_category=category,
        )
        confidence = round(
            min((evidence_confidence * 0.65 + estimate.confidence * 0.35), 100), 1
        )
        evidence = list(competition.evidence)
        risks = [
            f"Potential advertiser-safety term: {term}." for term in unsafe_matches
        ]
        if not risks:
            risks = [
                "No obvious title-level advertiser-safety term detected; "
                "manual review is still required."
            ]
        limitations = [
            *estimate.limitations,
            "Money Score ranks relative opportunity attractiveness; "
            "it is not expected revenue.",
            "Competition analysis covers only the retrieved YouTube sample.",
        ]
        return {
            "topic": query,
            "proposed_video_angle": angle,
            "money_score": max(0.0, min(score, 100.0)),
            "confidence": confidence,
            "opportunity_type": longevity.opportunity_type,
            "demand_score": demand,
            "momentum_score": longevity.momentum_score,
            "competition_score": competition.competition_score,
            "evergreen_score": longevity.evergreen_score,
            "advertiser_value_score": advertiser,
            "audience_value_score": audience,
            "watch_time_potential": watch,
            "click_through_potential": ctr,
            "production_difficulty": difficulty,
            "monetization_safety": safety,
            "evidence_confidence": evidence_confidence,
            "channel_fit_score": channel_fit,
            "estimated_production_hours": production_hours,
            "estimated_views": estimate.views.payload(),
            "estimated_rpm": estimate.rpm.payload(),
            "estimated_revenue": estimate.revenue.payload(),
            "expected_opportunity_window": self._window(longevity.opportunity_type),
            "monetization_risks": risks,
            "evidence_summary": [
                competition.competitor_summary,
                competition.market_gap,
                *longevity.trace,
            ],
            "evidence_references": evidence,
            "explanation": (
                f"{angle}. Demand is {demand:.0f}/100, competition pressure is "
                f"{competition.competition_score:.0f}/100, and evergreen evidence is "
                f"{longevity.evergreen_score:.0f}/100. Revenue is an estimate, "
                "not guaranteed."
            ),
            "assumptions": list(estimate.assumptions),
            "limitations": limitations,
            "weights": {
                name: round(weight, 4) for name, weight in normalized_weights.items()
            },
            "calculation_trace": trace,
            "engine_version": settings.money_engine_version,
            "competition_details": {
                "saturation_level": competition.saturation_level,
                "market_gap": competition.market_gap,
                **competition.metrics,
            },
            "revenue_metadata": {
                "niche_category": category,
                "benchmark_version": estimate.benchmark_version,
                "estimate_confidence": estimate.confidence,
            },
            "input_values": values,
        }

    @staticmethod
    def _log_score(value: float, ceiling: float) -> float:
        return round(100 * min(math.log1p(max(value, 0)) / math.log1p(ceiling), 1), 1)

    @staticmethod
    def _ctr_potential(angle: str) -> float:
        length_score = 100 if 45 <= len(angle) <= 70 else 70 if len(angle) <= 90 else 45
        curiosity = (
            10
            if any(
                word in angle.lower() for word in ("why", "how", "myth", "overlooked")
            )
            else 0
        )
        return float(min(length_score + curiosity, 100))

    @staticmethod
    def _channel_fit(
        query: str, hours: float, profile: ChannelProfileInput | None
    ) -> float | None:
        if profile is None:
            return None
        score = 70.0
        if profile.niche and profile.niche.lower() in query.lower():
            score += 20
        if profile.maximum_production_hours_per_video is not None:
            score += 10 if hours <= profile.maximum_production_hours_per_video else -30
        if any(topic.lower() in query.lower() for topic in profile.excluded_topics):
            score = 0
        return max(0.0, min(score, 100.0))

    @staticmethod
    def _window(kind: str) -> str:
        return {
            "temporary_event": "Days to two weeks",
            "trending_now": "Two to six weeks",
            "trending_and_evergreen": (
                "Publish within four weeks; long-tail potential remains"
            ),
            "evergreen_opportunity": "One to three months",
        }.get(kind, "Uncertain; validate with additional evidence")
