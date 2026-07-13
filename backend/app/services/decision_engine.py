"""Deterministic, explainable content decision engine."""

from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from backend.app.core.decision_config import DecisionConfig
from backend.app.domain.content import Content
from backend.app.domain.decision import Decision
from backend.app.domain.decision_enums import DecisionType, SignalStrength
from backend.app.domain.decision_explanation import DecisionExplanation
from backend.app.domain.evidence import Evidence
from backend.app.domain.trend_signal import TrendSignal


class DecisionEngine:
    """Create traceable recommendations with configurable weighted scoring."""

    _factor_labels = {
        "trend_momentum": "Trend Momentum",
        "audience_demand": "Audience Demand",
        "revenue_potential": "Revenue Potential",
        "competition": "Competition",
        "evergreen": "Evergreen",
        "platform_fit": "Platform Fit",
        "confidence": "Confidence",
    }

    def evaluate(
        self,
        content: Content,
        signals: Iterable[TrendSignal],
        configuration: DecisionConfig | None = None,
    ) -> Decision:
        """Evaluate content and retain all factor evidence and explanations."""
        config = configuration or DecisionConfig()
        signal_values = tuple(signals)
        timestamp = datetime.now(UTC)
        evidence = tuple(
            self._build_evidence(content, signal_values, config, factor, timestamp)
            for factor in config.weights
        )
        score = round(sum(item.contribution for item in evidence), 2)
        confidence = round(
            sum(item.confidence for item in evidence) / len(evidence) * 100, 2
        )
        decision_type = self._decision_type(score, config)
        explanations = tuple(self._explanation(item) for item in evidence)
        return Decision(
            id=str(uuid5(NAMESPACE_URL, f"{content.id}:{config.version}:{score}")),
            topic_id=str(
                self._metadata_value(content.metadata, "topic_id", content.id)
            ),
            topic_name=str(
                self._metadata_value(content.metadata, "topic_name", content.title)
            ),
            decision_type=decision_type,
            score=score,
            confidence=confidence,
            summary=self._summary(decision_type, score),
            recommended_action=self._recommended_action(decision_type),
            created_at=timestamp,
            engine_version=config.version,
            event_version=str(
                self._metadata_value(content.metadata, "event_version", "v1")
            ),
            correlation_id=str(
                self._metadata_value(content.metadata, "correlation_id", "")
            ),
            weights_snapshot=dict(config.weights),
            evidence=evidence,
            explanations=explanations,
        )

    def _build_evidence(
        self,
        content: Content,
        signals: tuple[TrendSignal, ...],
        config: DecisionConfig,
        factor: str,
        timestamp: datetime,
    ) -> Evidence:
        raw_value = self._raw_value(content, signals, factor)
        normalized_value = self._normalized_value(raw_value, factor)
        confidence = self._confidence(content, signals, factor)
        weight = config.weights[factor]
        contribution = round(normalized_value * weight * 100, 2)
        return Evidence(
            id=str(uuid5(NAMESPACE_URL, f"{content.id}:{factor}:{raw_value}")),
            source=self._source(signals, factor),
            factor=self._factor_labels[factor],
            weight=weight,
            raw_value=raw_value,
            normalized_value=normalized_value,
            contribution=contribution,
            confidence=confidence,
            reason=self._reason(content, factor, normalized_value),
            timestamp=timestamp,
            signal_id=str(self._metadata_value(content.metadata, "signal_id", "")),
            correlation_id=str(
                self._metadata_value(content.metadata, "correlation_id", "")
            ),
        )

    def _raw_value(
        self, content: Content, signals: tuple[TrendSignal, ...], factor: str
    ) -> float:
        values = self._factor_mapping(content.metadata, "decision_factors")
        if (
            content.metadata.get("decision_factor_authority") == "unified_signal"
            and factor in values
        ):
            return self._as_float(values[factor])
        opportunity = self._factor_mapping(content.metadata, "opportunity_dimensions")
        if opportunity:
            mapped = {
                "trend_momentum": "growth",
                "audience_demand": "demand",
                "revenue_potential": "monetization",
                "competition": "competition",
                "evergreen": "evergreen",
                "platform_fit": "platform_fit",
                "confidence": "confidence",
            }
            opportunity_key = mapped.get(factor)
            if opportunity_key is not None and opportunity_key in opportunity:
                return self._as_float(opportunity[opportunity_key])
        if factor == "trend_momentum" and signals:
            return self._average(signal.score for signal in signals)
        if factor == "confidence":
            opportunity_confidence = self._metadata_value(
                content.metadata, "opportunity_confidence", None
            )
            if isinstance(opportunity_confidence, (int, float)):
                return float(opportunity_confidence)
            if "confidence" in values:
                return self._as_float(values["confidence"])
            return (
                self._average(signal.confidence for signal in signals)
                if signals
                else 0.0
            )
        return self._as_float(values.get(factor, content.metrics.get(factor, 0.0)))

    def _confidence(
        self, content: Content, signals: tuple[TrendSignal, ...], factor: str
    ) -> float:
        values = self._factor_mapping(content.metadata, "decision_confidence")
        if (
            content.metadata.get("decision_factor_authority") == "unified_signal"
            and factor in values
        ):
            return self._clamp(self._as_float(values[factor]))
        opportunity = self._factor_mapping(content.metadata, "opportunity_dimensions")
        if (
            factor
            in {
                "trend_momentum",
                "audience_demand",
                "revenue_potential",
                "competition",
                "evergreen",
                "platform_fit",
            }
            and opportunity
        ):
            opportunity_confidence = self._metadata_value(
                content.metadata, "opportunity_confidence", None
            )
            if isinstance(opportunity_confidence, (int, float)):
                return self._clamp(float(opportunity_confidence) / 100.0)
        if factor == "trend_momentum" and signals:
            return self._clamp(self._average(signal.confidence for signal in signals))
        return self._clamp(self._as_float(values.get(factor, 0.5)))

    def _reason(self, content: Content, factor: str, normalized_value: float) -> str:
        reasons = self._factor_mapping(content.metadata, "decision_reasons")
        configured_reason = reasons.get(factor)
        if isinstance(configured_reason, str) and configured_reason:
            return configured_reason
        strength = self._signal_strength(normalized_value).replace("_", " ")
        return f"{self._factor_labels[factor]} is {strength}."

    def _source(self, signals: tuple[TrendSignal, ...], factor: str) -> str:
        if signals:
            return ", ".join(sorted({signal.source for signal in signals}))
        return "content_metadata"

    def _normalized_value(self, raw_value: float, factor: str) -> float:
        normalized = self._clamp(raw_value / 100 if raw_value > 1 else raw_value)
        return round(1 - normalized if factor == "competition" else normalized, 4)

    @staticmethod
    def _explanation(evidence: Evidence) -> DecisionExplanation:
        """Create the user-facing explanation without losing evidence details."""
        return DecisionExplanation(
            factor=evidence.factor,
            weight=evidence.weight,
            contribution=evidence.contribution,
            confidence=evidence.confidence,
            reason=evidence.reason,
        )

    @staticmethod
    def _factor_mapping(metadata: Mapping[str, Any], key: str) -> Mapping[str, Any]:
        value = metadata.get(key, {})
        return value if isinstance(value, Mapping) else {}

    @staticmethod
    def _metadata_value(metadata: Mapping[str, Any], key: str, default: Any) -> Any:
        value = metadata.get(key, default)
        return value

    @staticmethod
    def _average(values: Iterable[float]) -> float:
        values_tuple = tuple(values)
        return sum(values_tuple) / len(values_tuple) if values_tuple else 0.0

    @staticmethod
    def _as_float(value: Any) -> float:
        return float(value) if isinstance(value, int | float) else 0.0

    @staticmethod
    def _clamp(value: float) -> float:
        return min(max(value, 0.0), 1.0)

    @staticmethod
    def _signal_strength(value: float) -> SignalStrength:
        if value < 0.2:
            return SignalStrength.VERY_LOW
        if value < 0.4:
            return SignalStrength.LOW
        if value < 0.6:
            return SignalStrength.MEDIUM
        if value < 0.8:
            return SignalStrength.HIGH
        return SignalStrength.VERY_HIGH

    @staticmethod
    def _decision_type(score: float, config: DecisionConfig) -> DecisionType:
        if score >= config.create_threshold:
            return DecisionType.CREATE
        if score >= config.review_threshold:
            return DecisionType.REVIEW
        if score >= config.wait_threshold:
            return DecisionType.WAIT
        return DecisionType.IGNORE

    @staticmethod
    def _summary(decision_type: DecisionType, score: float) -> str:
        return (
            f"Decision is {decision_type.value} with a deterministic score of "
            f"{score:.2f}."
        )

    @staticmethod
    def _recommended_action(decision_type: DecisionType) -> str:
        return {
            DecisionType.CREATE: "Create content.",
            DecisionType.REVIEW: "Review the opportunity before creating content.",
            DecisionType.WAIT: "Wait for stronger supporting signals.",
            DecisionType.IGNORE: "Ignore this opportunity for now.",
        }[decision_type]
