"""Deterministic historical analytics for topic memory."""

from __future__ import annotations

import statistics
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime

from backend.app.domain.knowledge import HistoricalAnalytics, HistoricalObservation


@dataclass(frozen=True, slots=True)
class HistoricalAnalyticsService:
    """Compute deterministic trend analytics from historical observations."""

    def calculate(
        self, observations: Iterable[HistoricalObservation]
    ) -> HistoricalAnalytics:
        ordered = tuple(
            sorted(
                observations,
                key=lambda observation: observation.observed_at,
            )
        )
        if not ordered:
            return HistoricalAnalytics(
                growth_rate=0.0,
                acceleration=0.0,
                momentum=0.0,
                peak_detected=False,
                decline_detected=False,
                freshness=0.0,
                trend_age=0.0,
                historical_volatility=0.0,
                connector_contributions={},
                timeline=(),
            )

        scores = [self._signal_score(observation.payload) for observation in ordered]
        first_score = scores[0]
        last_score = scores[-1]
        growth_rate = self._growth_rate(first_score, last_score)
        acceleration = self._acceleration(scores)
        momentum = self._momentum(scores)
        peak_detected = last_score >= max(scores)
        decline_detected = self._decline(scores)
        freshness = self._freshness(ordered[-1].observed_at)
        trend_age = self._trend_age_hours(
            ordered[0].observed_at,
            ordered[-1].observed_at,
        )
        historical_volatility = self._volatility(scores)
        connector_contributions = self._connector_contributions(ordered, scores)
        timeline = tuple(
            self._timeline_entry(observation, score)
            for observation, score in zip(ordered, scores, strict=False)
        )
        return HistoricalAnalytics(
            growth_rate=growth_rate,
            acceleration=acceleration,
            momentum=momentum,
            peak_detected=peak_detected,
            decline_detected=decline_detected,
            freshness=freshness,
            trend_age=trend_age,
            historical_volatility=historical_volatility,
            connector_contributions=connector_contributions,
            timeline=timeline,
        )

    @staticmethod
    def _signal_score(payload: Mapping[str, object]) -> float:
        value = payload.get("signal_score")
        if isinstance(value, (int, float)):
            return max(0.0, min(float(value), 100.0))
        signal = payload.get("signal")
        if isinstance(signal, Mapping):
            raw_score = signal.get("score")
            if isinstance(raw_score, (int, float)):
                return max(0.0, min(float(raw_score) * 100.0, 100.0))
        return 0.0

    @staticmethod
    def _growth_rate(first: float, last: float) -> float:
        if first == 0.0:
            return round(last / 100.0, 4)
        return round((last - first) / abs(first), 4)

    @staticmethod
    def _acceleration(scores: list[float]) -> float:
        if len(scores) < 3:
            return 0.0
        midpoint = len(scores) // 2
        first_slope = scores[midpoint - 1] - scores[0]
        second_slope = scores[-1] - scores[midpoint]
        return round((second_slope - first_slope) / 100.0, 4)

    @staticmethod
    def _momentum(scores: list[float]) -> float:
        weights = (0.5, 0.3, 0.2)
        recent = tuple(scores[-3:])
        if not recent:
            return 0.0
        selected_weights = weights[: len(recent)]
        weighted_sum = sum(
            score * weight
            for score, weight in zip(recent, selected_weights, strict=False)
        )
        return round(weighted_sum / sum(selected_weights) / 100.0, 4)

    @staticmethod
    def _decline(scores: list[float]) -> bool:
        if len(scores) < 2:
            return False
        recent_average = (
            statistics.fmean(scores[-3:])
            if len(scores) >= 3
            else statistics.fmean(scores)
        )
        return scores[-1] < recent_average * 0.85

    @staticmethod
    def _freshness(observed_at: datetime) -> float:
        age_hours = (
            datetime.now(UTC) - observed_at.astimezone(UTC)
        ).total_seconds() / 3600.0
        return round(max(0.0, 1.0 - min(age_hours / 168.0, 1.0)), 4)

    @staticmethod
    def _trend_age_hours(started_at: datetime, latest_at: datetime) -> float:
        return round(
            max(
                0.0,
                (latest_at.astimezone(UTC) - started_at.astimezone(UTC)).total_seconds()
                / 3600.0,
            ),
            4,
        )

    @staticmethod
    def _volatility(scores: list[float]) -> float:
        if len(scores) < 2:
            return 0.0
        return round(statistics.pstdev(scores) / 100.0, 4)

    @staticmethod
    def _connector_contributions(
        observations: tuple[HistoricalObservation, ...], scores: list[float]
    ) -> dict[str, float]:
        contributions: dict[str, list[float]] = {}
        for observation, score in zip(observations, scores, strict=False):
            contributions.setdefault(observation.connector_name, []).append(score)
        return {
            connector_name: round(statistics.fmean(values), 2)
            for connector_name, values in contributions.items()
        }

    @staticmethod
    def _timeline_entry(
        observation: HistoricalObservation, score: float
    ) -> dict[str, object]:
        return {
            "observation_id": observation.id,
            "observed_at": observation.observed_at.isoformat(),
            "source": observation.source,
            "connector_name": observation.connector_name,
            "observation_type": observation.observation_type,
            "score": round(score, 2),
            "change_type": observation.change_type,
        }
