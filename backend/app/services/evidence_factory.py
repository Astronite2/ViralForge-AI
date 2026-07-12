"""Create deterministic evidence inputs for the decision engine."""

from __future__ import annotations

from dataclasses import dataclass

from backend.app.core.config import settings
from backend.app.domain.content import Content
from backend.app.domain.trend_signal import TrendSignal
from backend.app.models.topic import Topic


@dataclass(frozen=True, slots=True)
class EvidenceFactory:
    """Build engine inputs from a normalized trend signal."""

    def build_content(
        self,
        topic: Topic,
        signal: TrendSignal,
        *,
        signal_id: str,
        correlation_id: str,
        event_version: str,
    ) -> Content:
        topic_name = topic.display_name
        neutral_defaults = settings.neutral_factor_defaults
        factor_order = settings.evidence_factor_rules.get(
            settings.google_trends_source_name,
            [
                "trend_momentum",
                "audience_demand",
                "confidence",
                "revenue_potential",
                "competition",
                "evergreen",
                "platform_fit",
            ],
        )
        decision_factors: dict[str, float] = {}
        decision_confidence: dict[str, float] = {}
        decision_reasons: dict[str, str] = {}
        for factor in factor_order:
            factor_value, factor_confidence, reason = self._factor_values(
                factor, topic_name, signal, neutral_defaults
            )
            decision_factors[factor] = factor_value
            decision_confidence[factor] = factor_confidence
            decision_reasons[factor] = reason
        metadata = {
            "topic_id": topic.id,
            "topic_name": topic.display_name,
            "signal_id": signal_id,
            "correlation_id": correlation_id,
            "event_version": event_version,
            "decision_factors": decision_factors,
            "decision_confidence": decision_confidence,
            "decision_reasons": decision_reasons,
            "source_signal": {
                "source": signal.source,
                "score": signal.score,
                "confidence": signal.confidence,
                "timestamp": signal.timestamp.isoformat(),
                "reason": signal.reason,
            },
        }
        return Content(
            id=signal_id,
            platform=settings.google_trends_source_name,
            creator_name="Google Trends",
            creator_id=settings.google_trends_source_name,
            title=topic.display_name,
            description=signal.reason,
            url="https://trends.google.com",
            language=None,
            country=None,
            published_at=signal.timestamp,
            duration_seconds=None,
            content_type="trend_signal",
            metrics={"trend_score": signal.score},
            analysis={},
            signals=(signal,),
            metadata=metadata,
        )

    def _factor_values(
        self,
        factor: str,
        topic_name: str,
        signal: TrendSignal,
        neutral_defaults: dict[str, float],
    ) -> tuple[float, float, str]:
        if factor == "trend_momentum":
            return (
                round(signal.score * 100, 2),
                signal.confidence,
                f"Google Trends reported increasing search interest for {topic_name}.",
            )
        if factor == "audience_demand":
            return (
                round(signal.score * 100, 2),
                signal.confidence,
                (
                    "Google Trends interest suggests growing audience demand "
                    f"for {topic_name}."
                ),
            )
        if factor == "confidence":
            return (
                round(signal.confidence * 100, 2),
                signal.confidence,
                (
                    "Google Trends signal confidence supports evaluation "
                    f"for {topic_name}."
                ),
            )
        neutral_value = neutral_defaults[factor]
        return (
            neutral_value,
            neutral_value / 100,
            (
                "Using the configured neutral default for "
                f"{factor.replace('_', ' ')} for {topic_name}."
            ),
        )
