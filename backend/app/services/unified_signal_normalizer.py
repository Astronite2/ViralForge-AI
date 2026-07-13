"""Deterministic conversion into connector-neutral unified signals."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from backend.app.domain.content import Content
from backend.app.domain.trend_signal import TrendSignal
from backend.app.domain.unified_signal import SignalType, UnifiedSignal


class UnifiedSignalNormalizationError(ValueError):
    """Base error for invalid unified-signal input."""


class UnsupportedSignalInputError(UnifiedSignalNormalizationError):
    """Raised when a value cannot be converted into unified signals."""


class MalformedSignalError(UnifiedSignalNormalizationError):
    """Raised when required signal data is missing or outside its contract."""


class UnifiedSignalNormalizer:
    """Adapt existing connector output to the unified internal model."""

    _topic_pattern = re.compile(
        r"for\s+(?P<topic>.+?)(?:\s+in\s+[A-Za-z0-9_-]+[.!?]?$|[.!?]\s*$|\s*$)",
        re.IGNORECASE,
    )
    _dimensions = (
        "popularity",
        "velocity",
        "acceleration",
        "engagement",
        "sentiment",
        "freshness",
        "competition",
        "monetization",
        "evergreen",
        "platform_fit",
    )

    def normalize(
        self,
        value: TrendSignal | Content | UnifiedSignal,
        *,
        event_version: str,
        correlation_id: str,
        connector_metadata: Mapping[str, Any] | None = None,
    ) -> tuple[UnifiedSignal, ...]:
        """Convert a legacy signal, content object, or unified signal."""
        if isinstance(value, UnifiedSignal):
            self._validate_unified(value)
            if value.event_version != event_version:
                raise MalformedSignalError(
                    "Unified signal event_version does not match its event"
                )
            if value.correlation_id != correlation_id:
                raise MalformedSignalError(
                    "Unified signal correlation_id does not match its event"
                )
            return (value,)
        if isinstance(value, TrendSignal):
            return (
                self._from_trend_signal(
                    value,
                    event_version=event_version,
                    correlation_id=correlation_id,
                    connector_metadata=connector_metadata,
                ),
            )
        if isinstance(value, Content):
            if not value.signals:
                raise MalformedSignalError(
                    "Content must contain at least one embedded TrendSignal"
                )
            return tuple(
                self._from_trend_signal(
                    signal,
                    event_version=event_version,
                    correlation_id=correlation_id,
                    connector_metadata={
                        **dict(value.metadata),
                        **dict(connector_metadata or {}),
                    },
                    content=value,
                )
                for signal in value.signals
            )
        raise UnsupportedSignalInputError(
            f"Unsupported normalized connector output: {type(value).__name__}"
        )

    def _from_trend_signal(
        self,
        signal: TrendSignal,
        *,
        event_version: str,
        correlation_id: str,
        connector_metadata: Mapping[str, Any] | None,
        content: Content | None = None,
    ) -> UnifiedSignal:
        self._validate_legacy(signal, event_version, correlation_id)
        metadata = {
            **dict(connector_metadata or {}),
            **dict(signal.metadata),
        }
        signal_type = self._signal_type(signal.source, metadata)
        dimensions = {
            name: self._dimension(metadata.get(name), name) for name in self._dimensions
        }
        dimensions["popularity"] = (
            dimensions["popularity"]
            if dimensions["popularity"] is not None
            else signal.score
        )
        if content is not None:
            engagement = self._dimension(
                content.metrics.get("engagement_rate"), "engagement"
            )
            if engagement is not None:
                dimensions["engagement"] = engagement

        topic_name = (
            content.title
            if content is not None
            else self._first_string(metadata, "topic_name", "query", "title")
            or self._topic_from_reason(signal.reason)
        )
        geography = (
            content.country
            if content is not None
            else self._first_string(metadata, "region", "geo", "geography")
        )
        language = (
            content.language
            if content is not None
            else self._first_string(metadata, "language")
        )
        source_item_id = self._first_string(
            metadata, "source_item_id", "signal_id", "video_id", "id"
        )
        raw_value: float | str | bool | None = self._raw_value(
            signal, metadata, content
        )
        evidence_references = self._evidence_references(metadata)
        values: dict[str, Any] = {
            "topic_id": self._first_string(metadata, "topic_id"),
            "topic_name": topic_name,
            "source": signal.source,
            "signal_type": signal_type,
            "observed_at": self._as_datetime(signal.timestamp),
            "confidence": signal.confidence,
            **dimensions,
            "geography": geography,
            "language": language,
            "raw_value": raw_value,
            "normalized_value": signal.score,
            "reason": signal.reason,
            "evidence_references": evidence_references,
            "connector_metadata": metadata,
            "event_version": event_version,
            "correlation_id": correlation_id,
            "source_item_id": source_item_id,
            "content_id": content.id if content is not None else None,
        }
        normalization_id = str(uuid5(NAMESPACE_URL, self._canonical_json(values)))
        unified = UnifiedSignal(normalization_id=normalization_id, **values)
        self._validate_unified(unified)
        return unified

    def _validate_legacy(
        self, signal: TrendSignal, event_version: str, correlation_id: str
    ) -> None:
        if not signal.source.strip():
            raise MalformedSignalError("Signal source cannot be empty")
        if not signal.reason.strip():
            raise MalformedSignalError("Signal reason cannot be empty")
        self._unit_interval(signal.score, "score")
        self._unit_interval(signal.confidence, "confidence")
        self._as_datetime(signal.timestamp)
        if not event_version.strip():
            raise MalformedSignalError("event_version cannot be empty")
        if not correlation_id.strip():
            raise MalformedSignalError("correlation_id cannot be empty")

    def _validate_unified(self, signal: UnifiedSignal) -> None:
        if not signal.normalization_id.strip():
            raise MalformedSignalError("normalization_id cannot be empty")
        if not signal.source.strip() or not signal.reason.strip():
            raise MalformedSignalError("source and reason cannot be empty")
        self._unit_interval(signal.confidence, "confidence")
        if signal.normalized_value is not None:
            self._unit_interval(signal.normalized_value, "normalized_value")
        for name in self._dimensions:
            value = getattr(signal, name)
            if value is not None:
                self._unit_interval(value, name)
        self._as_datetime(signal.observed_at)

    @staticmethod
    def _signal_type(source: str, metadata: Mapping[str, Any]) -> SignalType:
        explicit = metadata.get("signal_type")
        if explicit is not None:
            try:
                return SignalType(str(explicit))
            except ValueError as exc:
                raise MalformedSignalError(
                    f"Unsupported signal_type: {explicit}"
                ) from exc
        if source == "google_trends":
            return SignalType.SEARCH_TREND
        if source == "youtube":
            return SignalType.CONTENT_PERFORMANCE
        return SignalType.AUDIENCE_DEMAND

    @classmethod
    def _dimension(cls, value: Any, name: str) -> float | None:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise MalformedSignalError(f"{name} must be numeric when provided")
        return cls._unit_interval(float(value), name)

    @staticmethod
    def _unit_interval(value: float, name: str) -> float:
        if not 0.0 <= float(value) <= 1.0:
            raise MalformedSignalError(f"{name} must be between 0 and 1")
        return float(value)

    @staticmethod
    def _as_datetime(value: datetime) -> datetime:
        if not isinstance(value, datetime):
            raise MalformedSignalError("observed_at must be a datetime")
        if value.tzinfo is None:
            raise MalformedSignalError("observed_at must include a timezone")
        return value.astimezone(UTC)

    @classmethod
    def _topic_from_reason(cls, reason: str) -> str | None:
        match = cls._topic_pattern.search(reason.strip())
        if match is not None:
            return match.group("topic").strip()
        return reason.strip() or None

    @staticmethod
    def _first_string(metadata: Mapping[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = metadata.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
        return None

    @staticmethod
    def _evidence_references(metadata: Mapping[str, Any]) -> tuple[str, ...]:
        value = metadata.get("evidence_references", ())
        if value is None:
            return ()
        if not isinstance(value, (tuple, list)):
            raise MalformedSignalError("evidence_references must be a list")
        return tuple(str(item) for item in value)

    @staticmethod
    def _raw_value(
        signal: TrendSignal, metadata: Mapping[str, Any], content: Content | None
    ) -> float | str | bool | None:
        explicit = metadata.get("raw_value")
        if isinstance(explicit, (str, int, float, bool)):
            return explicit
        if content is not None:
            views = content.metrics.get("view_count")
            if isinstance(views, int | float):
                return float(views)
        interest = metadata.get("interest_score")
        if isinstance(interest, int | float):
            return float(interest)
        return signal.score

    @staticmethod
    def _canonical_json(values: Mapping[str, Any]) -> str:
        return json.dumps(values, sort_keys=True, default=str, separators=(",", ":"))
