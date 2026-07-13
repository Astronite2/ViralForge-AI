"""Signal-to-decision application service."""

from __future__ import annotations

import logging
import re
from contextlib import contextmanager
from dataclasses import dataclass, replace

from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from backend.app.core.decision_config import DecisionConfig
from backend.app.domain.decision_calculated import DecisionCalculated
from backend.app.models.decision import DecisionModel
from backend.app.models.evidence import EvidenceModel
from backend.app.models.processed_event import ProcessedEventModel
from backend.app.models.topic import Topic
from backend.app.models.trend_signal import TrendSignalModel
from backend.app.repositories.decision import DecisionRepository
from backend.app.repositories.decision_explanation import DecisionExplanationRepository
from backend.app.repositories.evidence import EvidenceRepository
from backend.app.repositories.processed_event import ProcessedEventRepository
from backend.app.repositories.topic import TopicRepository
from backend.app.repositories.trend_signal import TrendSignalRepository
from backend.app.services.decision_engine import DecisionEngine
from backend.app.services.evidence_factory import EvidenceFactory
from backend.app.services.knowledge_layer import (
    KnowledgeIngestionResult,
    KnowledgeLayerService,
)
from backend.app.services.topic_normalization import TopicNormalizationService
from backend.app.utils.events import DecisionEventEmitter, SignalDetected

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SignalDecisionResult:
    """Result of processing one signal event."""

    topic: Topic
    signal: TrendSignalModel
    decision: DecisionModel
    evidence: tuple[EvidenceModel, ...]
    processed_event: ProcessedEventModel
    decision_event: DecisionCalculated
    duplicate: bool = False


class SignalDecisionService:
    """Process one signal event into a persisted decision."""

    _topic_pattern = re.compile(
        r"for\s+(?P<topic>.+?)(?:\s+in\s+[A-Za-z0-9_-]+[.!?]?$|[.!?]\s*$|\s*$)",
        re.IGNORECASE,
    )

    def __init__(
        self,
        session: Session,
        *,
        decision_engine: DecisionEngine | None = None,
        decision_config: DecisionConfig | None = None,
        event_emitter: DecisionEventEmitter | None = None,
    ) -> None:
        self.session = session
        self.decision_engine = decision_engine or DecisionEngine()
        self.decision_config = decision_config or DecisionConfig()
        self.event_emitter = event_emitter
        self.topic_repository = TopicRepository(session)
        self.trend_signal_repository = TrendSignalRepository(session)
        self.evidence_repository = EvidenceRepository(session)
        self.decision_repository = DecisionRepository(session)
        self.decision_explanation_repository = DecisionExplanationRepository(session)
        self.processed_event_repository = ProcessedEventRepository(session)
        self.topic_normalization = TopicNormalizationService(self.topic_repository)
        self.evidence_factory = EvidenceFactory()
        self.knowledge_layer = KnowledgeLayerService(session)

    def process(self, event: SignalDetected) -> SignalDecisionResult:
        """Persist a signal, evaluate it, and emit a decision event."""
        logger.info(
            "SignalDetected processing started",
            extra={
                "event_id": event.event_id,
                "correlation_id": event.correlation_id,
                "source": event.signal.source,
            },
        )
        has_outer_transaction = self.session.in_transaction()
        try:
            with self._transaction(has_outer_transaction):
                topic_name = self._topic_candidate(event.signal.reason)
                topic = self.topic_normalization.resolve(topic_name)
                logger.info(
                    "topic resolved",
                    extra={
                        "correlation_id": event.correlation_id,
                        "source": event.signal.source,
                        "topic_id": topic.id,
                        "topic_name": topic.display_name,
                    },
                )
                signal = self.trend_signal_repository.create(
                    topic_id=topic.id,
                    content_id=self._content_id(event.metadata),
                    source=event.signal.source,
                    score=event.signal.score,
                    confidence=event.signal.confidence,
                    timestamp=event.signal.timestamp,
                    reason=event.signal.reason,
                    correlation_id=event.correlation_id,
                    raw_metadata={
                        "event_id": event.event_id,
                        "event_version": event.event_version,
                        "occurred_at": event.occurred_at.isoformat(),
                    },
                )
                logger.info(
                    "signal persisted",
                    extra={
                        "correlation_id": event.correlation_id,
                        "event_id": event.event_id,
                        "signal_id": signal.id,
                        "topic_id": topic.id,
                        "source": signal.source,
                    },
                )
                knowledge = self.knowledge_layer.ingest_observation(
                    topic,
                    signal,
                    correlation_id=event.correlation_id,
                    event_version=event.event_version,
                    metadata=event.metadata,
                )
                engine_content = self.evidence_factory.build_content(
                    topic,
                    event.signal,
                    signal_id=signal.id,
                    correlation_id=event.correlation_id,
                    event_version=event.event_version,
                )
                engine_content = replace(
                    engine_content,
                    metadata=self._decision_metadata(
                        engine_content.metadata,
                        knowledge,
                    ),
                )
                decision = self.decision_engine.evaluate(
                    engine_content,
                    (event.signal,),
                    self.decision_config,
                )
                logger.info(
                    "decision calculated",
                    extra={
                        "correlation_id": event.correlation_id,
                        "signal_id": signal.id,
                        "topic_id": topic.id,
                        "decision_id": decision.id,
                        "source": signal.source,
                    },
                )
                decision_model = self.decision_repository.create(topic.id, decision)
                evidence_models = tuple(
                    self.evidence_repository.create(
                        decision_model.id, signal.id, evidence
                    )
                    for evidence in decision.evidence
                )
                self.session.flush()
                logger.info(
                    "evidence generated",
                    extra={
                        "correlation_id": event.correlation_id,
                        "signal_id": signal.id,
                        "topic_id": topic.id,
                        "decision_id": decision_model.id,
                        "count": len(evidence_models),
                    },
                )
                historical_evidence = self.knowledge_layer.record_evidence_history(
                    topic,
                    knowledge.observation,
                    decision.evidence,
                    correlation_id=event.correlation_id,
                )
                explanation_count = len(decision.explanations)
                for explanation in decision.explanations:
                    self.decision_explanation_repository.create(
                        decision_model.id, explanation
                    )
                processed_event = (
                    self.processed_event_repository.create_processed_record(
                        event_id=event.event_id,
                        event_type=type(event).__name__,
                        correlation_id=event.correlation_id,
                        decision_id=decision_model.id,
                    )
                )
                logger.info(
                    "decision persisted",
                    extra={
                        "correlation_id": event.correlation_id,
                        "event_id": event.event_id,
                        "signal_id": signal.id,
                        "topic_id": topic.id,
                        "decision_id": decision_model.id,
                        "explanations": explanation_count,
                        "historical_evidence": len(historical_evidence),
                    },
                )
        except (IntegrityError, OperationalError):
            logger.exception(
                "transaction rolled back",
                extra={
                    "event_id": event.event_id,
                    "correlation_id": event.correlation_id,
                    "source": event.signal.source,
                },
            )
            if not has_outer_transaction:
                self.session.rollback()
            existing_after = self.processed_event_repository.get_by_event_id(
                event.event_id
            )
            if existing_after is not None and existing_after.decision_id is not None:
                decision = self.decision_repository.get_by_id(
                    existing_after.decision_id
                )
                if decision is not None:
                    signal = self._first_signal_for_decision(decision.id)
                    topic = self._topic_for_decision(decision.topic_id)
                    decision_event = self._decision_event(decision)
                    return SignalDecisionResult(
                        topic=topic,
                        signal=signal,
                        decision=decision,
                        evidence=tuple(
                            self.evidence_repository.list_by_decision(decision.id)
                        ),
                        processed_event=existing_after,
                        decision_event=decision_event,
                        duplicate=True,
                    )
            raise
        except Exception:
            logger.exception(
                "processing failed",
                extra={
                    "event_id": event.event_id,
                    "correlation_id": event.correlation_id,
                    "source": event.signal.source,
                },
            )
            if not has_outer_transaction:
                self.session.rollback()
            raise

        decision_event = self._decision_event(decision_model)
        if self.event_emitter is not None:
            self.event_emitter.emit(decision_event)
            logger.info(
                "DecisionCalculated emitted",
                extra={
                    "event_id": decision_event.event_id,
                    "correlation_id": decision_event.correlation_id,
                    "decision_id": decision_event.decision_id,
                    "topic_id": decision_event.topic_id,
                    "task_id": "",
                },
            )

        return SignalDecisionResult(
            topic=topic,
            signal=signal,
            decision=decision_model,
            evidence=tuple(
                self.evidence_repository.list_by_decision(decision_model.id)
            ),
            processed_event=processed_event,
            decision_event=decision_event,
        )

    def _topic_candidate(self, reason: str) -> str:
        match = self._topic_pattern.search(reason.strip())
        if match is not None:
            return match.group("topic").strip()
        return reason.strip()

    @staticmethod
    def _content_id(metadata: dict[str, object]) -> str | None:
        content = metadata.get("content")
        if not isinstance(content, dict):
            return None
        identifier = content.get("id")
        return str(identifier) if identifier is not None else None

    @staticmethod
    def _decision_metadata(
        base_metadata: dict[str, object],
        knowledge: KnowledgeIngestionResult,
    ) -> dict[str, object]:
        return {
            **base_metadata,
            "opportunity_score": knowledge.opportunity_score.score,
            "opportunity_confidence": knowledge.opportunity_score.confidence,
            "opportunity_version": knowledge.opportunity_score.version,
            "opportunity_dimensions": dict(knowledge.opportunity_score.dimensions),
            "opportunity_explanations": dict(knowledge.opportunity_score.explanations),
            "historical_observation_id": knowledge.observation.id,
            "historical_observation_hash": knowledge.observation.observation_hash,
            "historical_trend_age": knowledge.analytics.trend_age,
            "historical_growth_rate": knowledge.analytics.growth_rate,
            "historical_acceleration": knowledge.analytics.acceleration,
            "historical_momentum": knowledge.analytics.momentum,
            "historical_volatility": knowledge.analytics.historical_volatility,
            "historical_freshness": knowledge.analytics.freshness,
            "historical_peak_detected": knowledge.analytics.peak_detected,
            "historical_decline_detected": knowledge.analytics.decline_detected,
            "historical_connector_contributions": dict(
                knowledge.analytics.connector_contributions
            ),
        }

    def _decision_event(self, decision: DecisionModel) -> DecisionCalculated:
        return DecisionCalculated(
            decision_id=decision.id,
            topic_id=decision.topic_id,
            topic_name=decision.topic_name,
            score=decision.score,
            confidence=decision.confidence,
            correlation_id=decision.correlation_id,
            engine_version=decision.engine_version,
            event_version=decision.event_version,
        )

    def _topic_for_decision(self, topic_id: str) -> Topic:
        topic = self.topic_repository.get_by_id(topic_id)
        if topic is None:
            raise RuntimeError("Decision references a missing topic")
        return topic

    def _first_signal_for_decision(self, decision_id: str) -> TrendSignalModel:
        evidence = self.evidence_repository.list_by_decision(decision_id)
        if not evidence:
            raise RuntimeError("Decision references no evidence")
        signal = self.session.get(TrendSignalModel, evidence[0].signal_id)
        if signal is None:
            raise RuntimeError("Decision references a missing signal")
        return signal

    @contextmanager
    def _transaction(self, has_outer_transaction: bool):
        if has_outer_transaction:
            with self.session.begin_nested():
                yield
            return
        with self.session.begin():
            yield
