"""Knowledge-layer orchestration and historical persistence."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.domain.evidence import Evidence
from backend.app.domain.knowledge import HistoricalAnalytics, HistoricalObservation
from backend.app.models.historical_evidence import HistoricalEvidenceModel
from backend.app.models.historical_observation import HistoricalObservationModel
from backend.app.models.opportunity_score import OpportunityScoreModel
from backend.app.models.topic import Topic
from backend.app.models.topic_relationship import TopicRelationshipModel
from backend.app.models.trend_signal import TrendSignalModel
from backend.app.repositories.historical_evidence import HistoricalEvidenceRepository
from backend.app.repositories.historical_observation import (
    HistoricalObservationRepository,
)
from backend.app.repositories.opportunity_score import OpportunityScoreRepository
from backend.app.repositories.topic_relationship import TopicRelationshipRepository
from backend.app.services.historical_analytics import HistoricalAnalyticsService
from backend.app.services.opportunity_engine import OpportunityEngine
from backend.app.utils.idempotency import stable_observation_hash


@dataclass(frozen=True, slots=True)
class KnowledgeIngestionResult:
    """Result of ingesting one observation into the knowledge layer."""

    observation: HistoricalObservationModel
    analytics: HistoricalAnalytics
    opportunity_score: OpportunityScoreModel
    duplicate: bool


@dataclass(frozen=True, slots=True)
class KnowledgeHistory:
    """Historical topic memory exposed to the API."""

    observations: tuple[HistoricalObservationModel, ...]
    analytics: HistoricalAnalytics
    opportunity_scores: tuple[OpportunityScoreModel, ...]
    evidence_history: tuple[HistoricalEvidenceModel, ...]


@dataclass
class KnowledgeLayerService:
    """Persist and query historical topic knowledge."""

    session: Session

    def __post_init__(self) -> None:
        self.observation_repository = HistoricalObservationRepository(self.session)
        self.evidence_repository = HistoricalEvidenceRepository(self.session)
        self.opportunity_repository = OpportunityScoreRepository(self.session)
        self.relationship_repository = TopicRelationshipRepository(self.session)
        self.analytics_service = HistoricalAnalyticsService()
        self.opportunity_engine = OpportunityEngine()

    def ingest_observation(
        self,
        topic: Topic,
        signal: TrendSignalModel,
        *,
        correlation_id: str,
        event_version: str,
        metadata: Mapping[str, object] | None = None,
    ) -> KnowledgeIngestionResult:
        payload = self._payload(signal, metadata)
        observation_hash = stable_observation_hash(
            topic.id,
            signal.source,
            signal,
            event_version=event_version,
            content=self._content(metadata),
        )
        existing = self.observation_repository.get_by_hash(observation_hash)
        if existing is not None:
            analytics = self.analytics_service.calculate(
                self.observation_repository.list_by_topic(
                    topic.id, settings.knowledge_history_limit, 0
                )
            )
            opportunity = self.opportunity_repository.get_by_observation(existing.id)
            if opportunity is None:
                opportunity = self._create_opportunity(
                    topic, existing, analytics, correlation_id=correlation_id
                )
            return KnowledgeIngestionResult(
                observation=existing,
                analytics=analytics,
                opportunity_score=opportunity,
                duplicate=True,
            )

        previous = self.observation_repository.get_latest_for_topic(
            topic.id,
            source=signal.source,
            connector_name=signal.source,
        )
        change_type = self._change_type(previous, signal.score)
        model = HistoricalObservationModel(
            id=str(uuid4()),
            topic_id=topic.id,
            source=signal.source,
            connector_name=signal.source,
            observation_type=(
                "content_signal" if self._content_present(metadata) else "signal"
            ),
            observed_at=signal.timestamp,
            correlation_id=correlation_id,
            observation_hash=observation_hash,
            payload=payload,
            change_type=change_type,
            signal_id=signal.id,
            content_id=self._content_id(metadata),
            previous_observation_id=previous.id if previous is not None else None,
        )
        self.observation_repository.create(model)
        analytics = self.analytics_service.calculate(
            self.observation_repository.list_by_topic(
                topic.id, settings.knowledge_history_limit, 0
            )
        )
        opportunity = self._create_opportunity(
            topic, model, analytics, correlation_id=correlation_id
        )
        return KnowledgeIngestionResult(
            observation=model,
            analytics=analytics,
            opportunity_score=opportunity,
            duplicate=False,
        )

    def record_evidence_history(
        self,
        topic: Topic,
        observation: HistoricalObservationModel,
        evidence_models: tuple[Evidence, ...],
        *,
        correlation_id: str,
    ) -> tuple[HistoricalEvidenceModel, ...]:
        records: list[HistoricalEvidenceModel] = []
        existing = {
            record.evidence_id
            for record in self.evidence_repository.list_by_topic(topic.id)
        }
        for evidence in evidence_models:
            if evidence.id in existing:
                continue
            record = HistoricalEvidenceModel(
                id=str(uuid4()),
                topic_id=topic.id,
                observation_id=observation.id,
                evidence_id=evidence.id,
                signal_id=evidence.signal_id,
                source=evidence.source,
                factor=evidence.factor,
                weight=evidence.weight,
                raw_value=evidence.raw_value,
                normalized_value=evidence.normalized_value,
                contribution=evidence.contribution,
                confidence=evidence.confidence,
                reason=evidence.reason,
                timestamp=evidence.timestamp,
                correlation_id=correlation_id,
            )
            self.evidence_repository.create(record)
            records.append(record)
        return tuple(records)

    def record_relationship(
        self,
        source_topic: Topic,
        target_topic: Topic,
        relationship_type: str,
        strength: float,
        reason: str,
        *,
        correlation_id: str,
    ) -> TopicRelationshipModel:
        existing = self.relationship_repository.get(
            source_topic.id, target_topic.id, relationship_type
        )
        if existing is not None:
            existing.strength = strength
            existing.reason = reason
            existing.correlation_id = correlation_id
            self.session.flush()
            return existing
        model = TopicRelationshipModel(
            id=str(uuid4()),
            source_topic_id=source_topic.id,
            target_topic_id=target_topic.id,
            relationship_type=relationship_type,
            strength=strength,
            reason=reason,
            correlation_id=correlation_id,
        )
        return self.relationship_repository.create(model)

    def history_for_topic(self, topic_id: str) -> KnowledgeHistory:
        observations = tuple(
            self.observation_repository.list_by_topic(
                topic_id, settings.knowledge_history_limit, 0
            )
        )
        analytics = self.analytics_service.calculate(observations)
        opportunities = tuple(self.opportunity_repository.list_by_topic(topic_id))
        evidence_history = tuple(self.evidence_repository.list_by_topic(topic_id))
        return KnowledgeHistory(
            observations=observations,
            analytics=analytics,
            opportunity_scores=opportunities,
            evidence_history=evidence_history,
        )

    def graph_for_topic(self, topic_id: str) -> tuple[TopicRelationshipModel, ...]:
        return tuple(self.relationship_repository.list_by_topic(topic_id))

    def _create_opportunity(
        self,
        topic: Topic,
        observation: HistoricalObservationModel,
        analytics: HistoricalAnalytics,
        *,
        correlation_id: str,
    ) -> OpportunityScoreModel:
        latest_observation = HistoricalObservation(
            id=observation.id,
            topic_id=observation.topic_id,
            source=observation.source,
            connector_name=observation.connector_name,
            observation_type=observation.observation_type,
            observed_at=observation.observed_at,
            correlation_id=observation.correlation_id,
            observation_hash=observation.observation_hash,
            payload=observation.payload,
            change_type=observation.change_type,
            signal_id=observation.signal_id,
            content_id=observation.content_id,
            previous_observation_id=observation.previous_observation_id,
        )
        score = self.opportunity_engine.evaluate(
            topic.id,
            latest_observation,
            analytics,
            correlation_id=correlation_id,
        )
        model = OpportunityScoreModel(
            id=score.id,
            topic_id=topic.id,
            observation_id=observation.id,
            score=score.score,
            confidence=score.confidence,
            version=score.version,
            dimensions=score.dimensions,
            explanations=score.explanations,
            correlation_id=correlation_id,
        )
        return self.opportunity_repository.create(model)

    @staticmethod
    def _payload(
        signal: TrendSignalModel, metadata: Mapping[str, object] | None
    ) -> dict[str, object]:
        content = metadata.get("content") if metadata is not None else None
        return {
            "signal": {
                "source": signal.source,
                "score": signal.score,
                "confidence": signal.confidence,
                "timestamp": signal.timestamp.isoformat(),
                "reason": signal.reason,
            },
            "event_version": (
                metadata.get("event_version") if metadata is not None else None
            ),
            "unified_signal": (
                KnowledgeLayerService._json_safe(metadata.get("unified_signal", {}))
                if metadata is not None
                else {}
            ),
            "signal_score": round(signal.score * 100.0, 2),
            "signal_confidence": round(signal.confidence * 100.0, 2),
            "content": (
                KnowledgeLayerService._json_safe(content)
                if isinstance(content, Mapping)
                else {}
            ),
            "raw_item": (
                KnowledgeLayerService._json_safe(metadata.get("raw_item", {}))
                if metadata is not None
                else {}
            ),
            "content_type": (
                content.get("content_type") if isinstance(content, Mapping) else None
            ),
        }

    @staticmethod
    def _change_type(previous: HistoricalObservationModel | None, score: float) -> str:
        if previous is None:
            return "new"
        previous_score = KnowledgeLayerService._signal_score(previous.payload)
        delta = score - previous_score
        if delta > 5.0:
            return "increase"
        if delta < -5.0:
            return "decrease"
        return "stable"

    @staticmethod
    def _signal_score(payload: Mapping[str, object]) -> float:
        value = payload.get("signal_score")
        if isinstance(value, (int, float)):
            return float(value)
        return 0.0

    @staticmethod
    def _content_id(metadata: Mapping[str, object] | None) -> str | None:
        if metadata is None:
            return None
        content = metadata.get("content")
        if isinstance(content, Mapping):
            identifier = content.get("id")
            if identifier is not None:
                return str(identifier)
        return None

    @staticmethod
    def _content_present(metadata: Mapping[str, object] | None) -> bool:
        if metadata is None:
            return False
        content = metadata.get("content")
        return isinstance(content, Mapping) and bool(content)

    @staticmethod
    def _content(metadata: Mapping[str, object] | None) -> Mapping[str, object] | None:
        if metadata is None:
            return None
        content = metadata.get("content")
        if isinstance(content, Mapping):
            return content
        return None

    @staticmethod
    def _json_safe(value: object) -> object:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, Mapping):
            return {
                str(key): KnowledgeLayerService._json_safe(item)
                for key, item in value.items()
            }
        if isinstance(value, (tuple, list)):
            return [KnowledgeLayerService._json_safe(item) for item in value]
        return value
