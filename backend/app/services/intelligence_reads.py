"""Read-only intelligence query service."""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.models.decision import DecisionModel
from backend.app.models.topic import Topic
from backend.app.models.trend_signal import TrendSignalModel
from backend.app.repositories.decision import DecisionRepository
from backend.app.repositories.topic import TopicRepository
from backend.app.repositories.trend_signal import TrendSignalRepository
from backend.app.schemas.decision import (
    DecisionExplanationRead,
    DecisionRead,
    EvidenceRead,
)
from backend.app.schemas.topic import TopicRead
from backend.app.schemas.trend_signal import TrendSignalRead


class IntelligenceReadService:
    """Translate persisted intelligence objects into API schemas."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.topic_repository = TopicRepository(session)
        self.signal_repository = TrendSignalRepository(session)
        self.decision_repository = DecisionRepository(session)

    def list_topics(self, limit: int, offset: int) -> list[TopicRead]:
        return [
            self._topic_read(topic)
            for topic in self.topic_repository.list(limit, offset)
        ]

    def get_topic(self, topic_id: str) -> TopicRead | None:
        topic = self.topic_repository.get_by_id(topic_id)
        return self._topic_read(topic) if topic is not None else None

    def list_signals(self, limit: int, offset: int) -> list[TrendSignalRead]:
        return [
            self._signal_read(signal)
            for signal in self.signal_repository.list(limit, offset)
        ]

    def get_signal(self, signal_id: str) -> TrendSignalRead | None:
        signal = self.signal_repository.get_by_id(signal_id)
        return self._signal_read(signal) if signal is not None else None

    def list_decisions(self, limit: int, offset: int) -> list[DecisionRead]:
        return [
            self._decision_read(decision)
            for decision in self.decision_repository.list(limit, offset)
        ]

    def get_decision(self, decision_id: str) -> DecisionRead | None:
        decision = self.decision_repository.get_by_id(decision_id)
        return self._decision_read(decision) if decision is not None else None

    def list_topic_decisions(
        self, topic_id: str, limit: int, offset: int
    ) -> list[DecisionRead]:
        return [
            self._decision_read(decision)
            for decision in self.decision_repository.list_by_topic(
                topic_id, limit, offset
            )
        ]

    def _topic_read(self, topic: Topic) -> TopicRead:
        return TopicRead.model_validate(topic)

    def _signal_read(self, signal: TrendSignalModel) -> TrendSignalRead:
        topic_name = signal.topic.display_name if signal.topic is not None else ""
        payload = {
            "id": signal.id,
            "topic_id": signal.topic_id,
            "topic_name": topic_name,
            "source": signal.source,
            "score": signal.score,
            "confidence": signal.confidence,
            "reason": signal.reason,
            "timestamp": signal.timestamp,
            "correlation_id": signal.correlation_id,
            "created_at": signal.created_at,
            "raw_metadata": signal.raw_metadata,
        }
        return TrendSignalRead.model_validate(payload)

    def _decision_read(self, decision: DecisionModel) -> DecisionRead:
        payload = {
            "id": decision.id,
            "topic_id": decision.topic_id,
            "topic_name": decision.topic_name,
            "decision_type": decision.decision_type,
            "score": decision.score,
            "confidence": decision.confidence,
            "summary": decision.summary,
            "recommended_action": decision.recommended_action,
            "created_at": decision.created_at,
            "engine_version": decision.engine_version,
            "event_version": decision.event_version,
            "correlation_id": decision.correlation_id,
            "weights_snapshot": decision.weights_snapshot,
            "evidence": [
                EvidenceRead.model_validate(
                    {
                        "id": evidence.id,
                        "source": evidence.source,
                        "factor": evidence.factor,
                        "raw_value": evidence.raw_value,
                        "normalized_value": evidence.normalized_value,
                        "weight": evidence.weight,
                        "contribution": evidence.contribution,
                        "confidence": evidence.confidence,
                        "reason": evidence.reason,
                        "timestamp": evidence.timestamp,
                        "signal_id": evidence.signal_id,
                    }
                )
                for evidence in decision.evidence
            ],
            "explanations": [
                DecisionExplanationRead.model_validate(
                    {
                        "factor": explanation.factor,
                        "weight": explanation.weight,
                        "contribution": explanation.contribution,
                        "confidence": explanation.confidence,
                        "reason": explanation.reason,
                    }
                )
                for explanation in decision.explanations
            ],
        }
        return DecisionRead.model_validate(payload)
