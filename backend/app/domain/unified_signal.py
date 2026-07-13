"""Connector-neutral intelligence signal model."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any


class SignalType(StrEnum):
    """Stable categories understood by the unified intelligence pipeline."""

    SEARCH_TREND = "SEARCH_TREND"
    CONTENT_PERFORMANCE = "CONTENT_PERFORMANCE"
    DISCUSSION_VELOCITY = "DISCUSSION_VELOCITY"
    NEWS_MOMENTUM = "NEWS_MOMENTUM"
    AUDIENCE_DEMAND = "AUDIENCE_DEMAND"
    COMPETITION = "COMPETITION"
    SENTIMENT = "SENTIMENT"
    PLATFORM_FIT = "PLATFORM_FIT"
    MONETIZATION = "MONETIZATION"
    FRESHNESS = "FRESHNESS"


@dataclass(frozen=True, slots=True)
class UnifiedSignal:
    """Complete, traceable signal representation used inside the platform."""

    normalization_id: str
    topic_id: str | None
    topic_name: str | None
    source: str
    signal_type: SignalType
    observed_at: datetime
    confidence: float
    popularity: float | None
    velocity: float | None
    acceleration: float | None
    engagement: float | None
    sentiment: float | None
    freshness: float | None
    competition: float | None
    monetization: float | None
    evergreen: float | None
    platform_fit: float | None
    geography: str | None
    language: str | None
    raw_value: float | str | bool | None
    normalized_value: float | None
    reason: str
    evidence_references: tuple[str, ...]
    connector_metadata: Mapping[str, Any]
    event_version: str
    correlation_id: str
    source_item_id: str | None
    content_id: str | None

    def to_payload(self) -> dict[str, Any]:
        """Return an explicit JSON-compatible representation, including nulls."""
        return {
            "normalization_id": self.normalization_id,
            "topic_id": self.topic_id,
            "topic_name": self.topic_name,
            "source": self.source,
            "signal_type": self.signal_type.value,
            "observed_at": self.observed_at.isoformat(),
            "confidence": self.confidence,
            "popularity": self.popularity,
            "velocity": self.velocity,
            "acceleration": self.acceleration,
            "engagement": self.engagement,
            "sentiment": self.sentiment,
            "freshness": self.freshness,
            "competition": self.competition,
            "monetization": self.monetization,
            "evergreen": self.evergreen,
            "platform_fit": self.platform_fit,
            "geography": self.geography,
            "language": self.language,
            "raw_value": self.raw_value,
            "normalized_value": self.normalized_value,
            "reason": self.reason,
            "evidence_references": list(self.evidence_references),
            "connector_metadata": _json_safe(self.connector_metadata),
            "event_version": self.event_version,
            "correlation_id": self.correlation_id,
            "source_item_id": self.source_item_id,
            "content_id": self.content_id,
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> UnifiedSignal:
        """Restore a unified signal from an event or persisted JSON payload."""
        return cls(
            normalization_id=str(payload["normalization_id"]),
            topic_id=_optional_string(payload.get("topic_id")),
            topic_name=_optional_string(payload.get("topic_name")),
            source=str(payload["source"]),
            signal_type=SignalType(str(payload["signal_type"])),
            observed_at=datetime.fromisoformat(
                str(payload["observed_at"]).replace("Z", "+00:00")
            ),
            confidence=float(payload["confidence"]),
            popularity=_optional_float(payload.get("popularity")),
            velocity=_optional_float(payload.get("velocity")),
            acceleration=_optional_float(payload.get("acceleration")),
            engagement=_optional_float(payload.get("engagement")),
            sentiment=_optional_float(payload.get("sentiment")),
            freshness=_optional_float(payload.get("freshness")),
            competition=_optional_float(payload.get("competition")),
            monetization=_optional_float(payload.get("monetization")),
            evergreen=_optional_float(payload.get("evergreen")),
            platform_fit=_optional_float(payload.get("platform_fit")),
            geography=_optional_string(payload.get("geography")),
            language=_optional_string(payload.get("language")),
            raw_value=payload.get("raw_value"),
            normalized_value=_optional_float(payload.get("normalized_value")),
            reason=str(payload["reason"]),
            evidence_references=tuple(
                str(item) for item in payload.get("evidence_references", ())
            ),
            connector_metadata=dict(payload.get("connector_metadata", {})),
            event_version=str(payload["event_version"]),
            correlation_id=str(payload["correlation_id"]),
            source_item_id=_optional_string(payload.get("source_item_id")),
            content_id=_optional_string(payload.get("content_id")),
        )


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError("Unified signal dimension must be numeric or null")
    return float(value)


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    result = str(value).strip()
    return result or None


def _json_safe(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    return value
