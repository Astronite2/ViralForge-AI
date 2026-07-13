"""Deterministic opportunity scoring engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid5

from backend.app.core.opportunity_config import OpportunityConfig
from backend.app.domain.knowledge import (
    HistoricalAnalytics,
    HistoricalObservation,
    OpportunityScore,
)


@dataclass(frozen=True, slots=True)
class OpportunityEngine:
    """Compute deterministic opportunity scores from historical analytics."""

    def evaluate(
        self,
        topic_id: str,
        latest_observation: HistoricalObservation,
        analytics: HistoricalAnalytics,
        *,
        correlation_id: str,
        version: str | None = None,
        configuration: OpportunityConfig | None = None,
    ) -> OpportunityScore:
        config = configuration or OpportunityConfig()
        engine_version = version or config.version
        dimensions = self._dimensions(latest_observation, analytics)
        score = round(
            sum(dimensions[name] * weight for name, weight in config.weights.items()),
            2,
        )
        confidence = round(
            min(
                100.0,
                50.0
                + (analytics.freshness * 20.0)
                + min(len(analytics.timeline), 10) * 3.0,
            ),
            2,
        )
        explanations = self._explanations(analytics, latest_observation, dimensions)
        return OpportunityScore(
            id=str(
                uuid5(
                    NAMESPACE_URL,
                    f"{topic_id}:{latest_observation.id}:{engine_version}:{score}",
                )
            ),
            topic_id=topic_id,
            observation_id=latest_observation.id,
            score=score,
            confidence=confidence,
            version=engine_version,
            dimensions=dimensions,
            explanations=explanations,
            correlation_id=correlation_id,
            created_at=datetime.now(UTC),
        )

    @staticmethod
    def _dimensions(
        latest_observation: HistoricalObservation, analytics: HistoricalAnalytics
    ) -> dict[str, float]:
        latest_score = OpportunityEngine._signal_score(latest_observation)
        observations_count = max(len(analytics.timeline), 1)
        unique_connectors = max(len(analytics.connector_contributions), 1)
        demand = latest_score
        growth = max(0.0, min(100.0, 50.0 + (analytics.growth_rate * 50.0)))
        competition = max(
            0.0, min(100.0, 100.0 - (analytics.historical_volatility * 100.0))
        )
        evergreen = max(
            0.0,
            min(100.0, 100.0 - min(analytics.trend_age / 168.0, 1.0) * 30.0),
        )
        platform_fit = max(0.0, min(100.0, 40.0 + (unique_connectors * 15.0)))
        monetization = max(
            0.0,
            min(100.0, (demand * 0.4) + (growth * 0.3) + ((100.0 - competition) * 0.3)),
        )
        freshness = analytics.freshness * 100.0
        novelty = max(
            0.0,
            min(
                100.0,
                100.0 - (observations_count - 1) * 10.0 + (analytics.momentum * 20.0),
            ),
        )
        return {
            "demand": round(demand, 2),
            "growth": round(growth, 2),
            "competition": round(competition, 2),
            "evergreen": round(evergreen, 2),
            "platform_fit": round(platform_fit, 2),
            "monetization": round(monetization, 2),
            "freshness": round(freshness, 2),
            "novelty": round(novelty, 2),
        }

    @staticmethod
    def _signal_score(observation: HistoricalObservation) -> float:
        payload = observation.payload
        signal_score = payload.get("signal_score")
        if isinstance(signal_score, (int, float)):
            return float(signal_score)
        signal = payload.get("signal")
        if isinstance(signal, dict):
            score = signal.get("score")
            if isinstance(score, (int, float)):
                return float(score) * 100.0
        return 0.0

    @staticmethod
    def _explanations(
        analytics: HistoricalAnalytics,
        latest_observation: HistoricalObservation,
        dimensions: dict[str, float],
    ) -> dict[str, str]:
        return {
            "demand": (
                f"Demand tracks the latest observation score of "
                f"{dimensions['demand']:.2f}."
            ),
            "growth": (
                f"Growth reflects historical growth rate {analytics.growth_rate:.4f}."
            ),
            "competition": ("Competition declines as historical volatility stays low."),
            "evergreen": (
                f"Evergreen strength accounts for trend age {analytics.trend_age:.2f}h."
            ),
            "platform_fit": (
                "Platform fit increases with "
                f"{len(analytics.connector_contributions)} connectors."
            ),
            "monetization": (
                f"Monetization combines demand, growth, and competition for "
                f"{latest_observation.topic_id}."
            ),
            "freshness": (
                "Freshness decays as the latest observation ages; "
                f"current freshness is {analytics.freshness:.4f}."
            ),
            "novelty": (
                f"Novelty decreases as more observations accumulate; current count is "
                f"{len(analytics.timeline)}."
            ),
        }
