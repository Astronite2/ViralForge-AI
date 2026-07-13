"""Create deterministic evidence inputs for the decision engine."""

from __future__ import annotations

from dataclasses import dataclass

from backend.app.core.config import settings
from backend.app.domain.content import Content
from backend.app.domain.trend_signal import TrendSignal
from backend.app.domain.unified_signal import UnifiedSignal
from backend.app.models.topic import Topic
from backend.app.services.unified_evidence_mapper import UnifiedEvidenceMapper
from backend.app.services.unified_signal_normalizer import UnifiedSignalNormalizer


@dataclass(frozen=True, slots=True)
class EvidenceFactory:
    """Build legacy engine input from a connector-neutral unified signal."""

    def build_content(
        self,
        topic: Topic,
        signal: UnifiedSignal | TrendSignal,
        *,
        signal_id: str,
        correlation_id: str,
        event_version: str,
    ) -> Content:
        unified = self._unified(signal, correlation_id, event_version)
        neutral_defaults = settings.neutral_factor_defaults
        factor_order = tuple(
            settings.evidence_factor_rules.get(
                unified.source,
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
        )
        mappings = UnifiedEvidenceMapper().map(unified, factor_order, neutral_defaults)
        decision_factors = {item.factor: item.value for item in mappings}
        decision_confidence = {item.factor: item.confidence for item in mappings}
        decision_reasons = {item.factor: item.reason for item in mappings}
        explicit_factors = [
            item.factor for item in mappings if not item.neutral_default
        ]
        neutral_factors = [item.factor for item in mappings if item.neutral_default]
        legacy_signal = self._legacy_signal(unified, signal)
        metadata = {
            "topic_id": topic.id,
            "topic_name": topic.display_name,
            "signal_id": signal_id,
            "correlation_id": correlation_id,
            "event_version": event_version,
            "decision_factors": decision_factors,
            "decision_confidence": decision_confidence,
            "decision_reasons": decision_reasons,
            "decision_factor_authority": "unified_signal",
            "explicit_decision_factors": explicit_factors,
            "neutral_decision_factors": neutral_factors,
            "evidence_mapping": {
                item.factor: {
                    "dimensions": list(item.dimensions),
                    "neutral_default": item.neutral_default,
                }
                for item in mappings
            },
            "source_signal": {
                "source": legacy_signal.source,
                "score": legacy_signal.score,
                "confidence": legacy_signal.confidence,
                "timestamp": legacy_signal.timestamp.isoformat(),
                "reason": legacy_signal.reason,
            },
            "unified_signal": unified.to_payload(),
        }
        source_url = unified.connector_metadata.get("source_url")
        return Content(
            id=signal_id,
            platform=unified.source,
            creator_name=unified.source.replace("_", " ").title(),
            creator_id=unified.source,
            title=topic.display_name,
            description=unified.reason,
            url=str(source_url) if source_url else "",
            language=unified.language,
            country=unified.geography,
            published_at=unified.observed_at,
            duration_seconds=None,
            content_type=unified.signal_type.value.lower(),
            metrics={"trend_score": legacy_signal.score},
            analysis={},
            signals=(legacy_signal,),
            metadata=metadata,
        )

    @staticmethod
    def _unified(
        signal: UnifiedSignal | TrendSignal,
        correlation_id: str,
        event_version: str,
    ) -> UnifiedSignal:
        if isinstance(signal, UnifiedSignal):
            return signal
        return UnifiedSignalNormalizer().normalize(
            signal,
            correlation_id=correlation_id,
            event_version=event_version,
        )[0]

    @staticmethod
    def _legacy_signal(
        unified: UnifiedSignal, signal: UnifiedSignal | TrendSignal
    ) -> TrendSignal:
        if isinstance(signal, TrendSignal):
            return signal
        return TrendSignal(
            source=unified.source,
            score=unified.normalized_value or 0.0,
            confidence=unified.confidence,
            timestamp=unified.observed_at,
            reason=unified.reason,
            metadata=unified.connector_metadata,
        )
