"""Deterministic unified-signal to decision-factor mapping."""

from __future__ import annotations

from dataclasses import dataclass

from backend.app.domain.unified_signal import UnifiedSignal


@dataclass(frozen=True, slots=True)
class UnifiedEvidenceFactor:
    """One traceable input for the existing Decision Engine factor contract."""

    factor: str
    value: float
    confidence: float
    reason: str
    dimensions: tuple[str, ...]
    neutral_default: bool


@dataclass(frozen=True, slots=True)
class UnifiedEvidenceMapper:
    """Map explicit unified dimensions without connector-specific branches."""

    _factor_dimensions = {
        "trend_momentum": ("velocity", "acceleration", "popularity", "freshness"),
        "audience_demand": ("popularity", "engagement", "sentiment"),
        "revenue_potential": ("monetization",),
        "competition": ("competition",),
        "evergreen": ("evergreen",),
        "platform_fit": ("platform_fit", "engagement"),
    }

    def map(
        self,
        signal: UnifiedSignal,
        factor_order: tuple[str, ...],
        neutral_defaults: dict[str, float],
    ) -> tuple[UnifiedEvidenceFactor, ...]:
        """Return mappings in the Decision Engine's stable factor order."""
        return tuple(
            self._map_factor(signal, factor, neutral_defaults)
            for factor in factor_order
        )

    def _map_factor(
        self,
        signal: UnifiedSignal,
        factor: str,
        neutral_defaults: dict[str, float],
    ) -> UnifiedEvidenceFactor:
        if factor == "confidence":
            return UnifiedEvidenceFactor(
                factor=factor,
                value=round(signal.confidence * 100.0, 2),
                confidence=signal.confidence,
                reason=(
                    f"Unified {signal.signal_type.value} confidence supplied by "
                    f"{signal.source}."
                ),
                dimensions=("confidence",),
                neutral_default=False,
            )

        candidates = self._factor_dimensions.get(factor, ())
        for dimension in candidates:
            value = getattr(signal, dimension)
            if value is None:
                continue
            reason = (
                f"Unified dimension {dimension} from {signal.source} maps to "
                f"{factor.replace('_', ' ')}."
            )
            if (
                factor == "audience_demand"
                and dimension != "sentiment"
                and signal.sentiment is not None
            ):
                relationship = (
                    "conflicts with" if signal.sentiment < 0.5 else "supports"
                )
                reason = f"{reason[:-1]}; sentiment {relationship} this evidence."
            return UnifiedEvidenceFactor(
                factor=factor,
                value=round(value * 100.0, 2),
                confidence=signal.confidence,
                reason=reason,
                dimensions=(dimension,),
                neutral_default=False,
            )

        neutral_value = neutral_defaults[factor]
        return UnifiedEvidenceFactor(
            factor=factor,
            value=neutral_value,
            confidence=neutral_value / 100.0,
            reason=(
                "Using the configured neutral default for "
                f"{factor.replace('_', ' ')} because the unified signal did not "
                "provide a mapped dimension."
            ),
            dimensions=(),
            neutral_default=True,
        )
