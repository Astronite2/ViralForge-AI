"""Shared in-process event contracts."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from backend.app.core.config import settings
from backend.app.domain.decision_calculated import DecisionCalculated
from backend.app.domain.reasoning import ReasoningStatus
from backend.app.domain.trend_signal import TrendSignal
from backend.app.domain.unified_signal import UnifiedSignal


@dataclass(frozen=True, slots=True)
class SignalDetected:
    """Event emitted when a connector normalizes a signal."""

    signal: TrendSignal
    metadata: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    event_version: str = field(default_factory=lambda: settings.event_version)
    unified_signal: UnifiedSignal | None = None

    def to_payload(self) -> dict[str, Any]:
        """Serialize the event for task payloads."""
        payload = {
            "event_id": self.event_id,
            "signal": {
                "source": self.signal.source,
                "score": self.signal.score,
                "confidence": self.signal.confidence,
                "timestamp": self.signal.timestamp.isoformat(),
                "reason": self.signal.reason,
                "metadata": dict(self.signal.metadata),
            },
            "metadata": self.metadata,
            "occurred_at": self.occurred_at.isoformat(),
            "correlation_id": self.correlation_id,
            "event_version": self.event_version,
        }
        if self.unified_signal is not None:
            payload["unified_signal"] = self.unified_signal.to_payload()
        return payload

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "SignalDetected":
        """Deserialize an event payload."""
        signal_payload = payload["signal"]
        return cls(
            event_id=str(payload["event_id"]),
            signal=TrendSignal(
                source=str(signal_payload["source"]),
                score=float(signal_payload["score"]),
                confidence=float(signal_payload["confidence"]),
                timestamp=datetime.fromisoformat(
                    str(signal_payload["timestamp"]).replace("Z", "+00:00")
                ),
                reason=str(signal_payload["reason"]),
                metadata=dict(signal_payload.get("metadata", {})),
            ),
            unified_signal=(
                UnifiedSignal.from_payload(payload["unified_signal"])
                if isinstance(payload.get("unified_signal"), Mapping)
                else None
            ),
            occurred_at=datetime.fromisoformat(
                str(payload["occurred_at"]).replace("Z", "+00:00")
            ),
            metadata=dict(payload.get("metadata", {})),
            correlation_id=str(payload["correlation_id"]),
            event_version=str(payload["event_version"]),
        )


class SignalEventEmitter:
    """Protocol-like base for signal event emission."""

    def emit(self, event: SignalDetected) -> None:
        """Publish a signal event."""
        raise NotImplementedError


class DecisionEventEmitter:
    """Protocol-like base for decision event emission."""

    def emit(self, event: DecisionCalculated) -> None:
        """Publish a decision event."""
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class ReasoningRequested:
    """Event emitted when reasoning starts."""

    reasoning_run_id: str
    reasoning_type: str
    topic_id: str | None
    decision_id: str | None
    correlation_id: str
    model: str
    prompt_version: str
    status: str = ReasoningStatus.PENDING.value
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    event_version: str = field(default_factory=lambda: settings.event_version)


@dataclass(frozen=True, slots=True)
class ReasoningCompleted:
    """Event emitted when reasoning completes successfully."""

    reasoning_run_id: str
    reasoning_type: str
    topic_id: str | None
    decision_id: str | None
    correlation_id: str
    model: str
    prompt_version: str
    status: str = ReasoningStatus.SUCCEEDED.value
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    event_version: str = field(default_factory=lambda: settings.event_version)


@dataclass(frozen=True, slots=True)
class ReasoningFailed:
    """Event emitted when reasoning fails."""

    reasoning_run_id: str
    reasoning_type: str
    topic_id: str | None
    decision_id: str | None
    correlation_id: str
    model: str
    prompt_version: str
    status: str = ReasoningStatus.FAILED.value
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    event_version: str = field(default_factory=lambda: settings.event_version)


@dataclass(frozen=True, slots=True)
class ReasoningValidationFailed:
    """Event emitted when reasoning output fails grounding validation."""

    reasoning_run_id: str
    reasoning_type: str
    topic_id: str | None
    decision_id: str | None
    correlation_id: str
    model: str
    prompt_version: str
    status: str = ReasoningStatus.VALIDATION_FAILED.value
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    event_version: str = field(default_factory=lambda: settings.event_version)


class InMemorySignalEventEmitter(SignalEventEmitter):
    """Collect signal events for tests and local orchestration."""

    def __init__(self) -> None:
        self.events: list[SignalDetected] = []

    def emit(self, event: SignalDetected) -> None:
        self.events.append(event)


class InMemoryDecisionEventEmitter(DecisionEventEmitter):
    """Collect decision events for tests and local orchestration."""

    def __init__(self) -> None:
        self.events: list[DecisionCalculated] = []

    def emit(self, event: DecisionCalculated) -> None:
        self.events.append(event)


class ReasoningEventEmitter:
    """Protocol-like base for reasoning event emission."""

    def emit(self, event: object) -> None:
        """Publish a reasoning event."""
        raise NotImplementedError


class InMemoryReasoningEventEmitter(ReasoningEventEmitter):
    """Collect reasoning events for tests and local orchestration."""

    def __init__(self) -> None:
        self.events: list[object] = []

    def emit(self, event: object) -> None:
        self.events.append(event)


def decision_calculated_to_payload(event: DecisionCalculated) -> dict[str, Any]:
    """Serialize a decision event for logs or transport."""
    return {
        "event_id": event.event_id,
        "decision_id": event.decision_id,
        "topic_id": event.topic_id,
        "topic_name": event.topic_name,
        "score": event.score,
        "confidence": event.confidence,
        "occurred_at": event.occurred_at.isoformat(),
        "correlation_id": event.correlation_id,
        "engine_version": event.engine_version,
        "event_version": event.event_version,
    }
