"""Deterministic reasoning context builder."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.domain.reasoning import (
    ReasoningContext,
    ReasoningEvidenceReference,
    ReasoningRequest,
    ReasoningType,
)
from backend.app.models.decision import DecisionModel
from backend.app.models.evidence import EvidenceModel
from backend.app.models.historical_evidence import HistoricalEvidenceModel
from backend.app.models.historical_observation import HistoricalObservationModel
from backend.app.models.opportunity_score import OpportunityScoreModel
from backend.app.models.topic import Topic
from backend.app.models.topic_relationship import TopicRelationshipModel
from backend.app.models.trend_signal import TrendSignalModel
from backend.app.repositories.decision import DecisionRepository
from backend.app.repositories.evidence import EvidenceRepository
from backend.app.repositories.historical_evidence import HistoricalEvidenceRepository
from backend.app.repositories.historical_observation import (
    HistoricalObservationRepository,
)
from backend.app.repositories.opportunity_score import OpportunityScoreRepository
from backend.app.repositories.topic import TopicRepository
from backend.app.repositories.topic_relationship import TopicRelationshipRepository
from backend.app.repositories.trend_signal import TrendSignalRepository

if TYPE_CHECKING:
    from backend.app.domain.knowledge import HistoricalObservation


@dataclass
class ReasoningContextBuilder:
    """Build deterministic reasoning inputs from persisted records."""

    session: Session

    def __post_init__(self) -> None:
        self.topic_repository = TopicRepository(self.session)
        self.signal_repository = TrendSignalRepository(self.session)
        self.decision_repository = DecisionRepository(self.session)
        self.evidence_repository = EvidenceRepository(self.session)
        self.history_repository = HistoricalObservationRepository(self.session)
        self.history_evidence_repository = HistoricalEvidenceRepository(self.session)
        self.opportunity_repository = OpportunityScoreRepository(self.session)
        self.relationship_repository = TopicRelationshipRepository(self.session)

    def build(self, request: ReasoningRequest) -> ReasoningContext:
        """Build the requested reasoning context."""
        if request.reasoning_type == ReasoningType.OPPORTUNITY_COMPARISON:
            return self._comparison_context(request)
        if request.reasoning_type == ReasoningType.CHANGE_SUMMARY:
            return self._change_context(request)
        return self._single_context(request)

    def _single_context(self, request: ReasoningRequest) -> ReasoningContext:
        topic = self._resolve_topic(request.topic_id)
        decision = self._resolve_decision(request.decision_id)
        opportunity = self._resolve_opportunity(
            request.opportunity_id,
            topic.id if topic is not None else None,
        )
        return self._context_for_topic(
            request=request,
            topic=topic,
            decision=decision,
            opportunity=opportunity,
        )

    def _comparison_context(self, request: ReasoningRequest) -> ReasoningContext:
        topic_ids = self._comparison_topic_ids(request)
        snapshots = [
            self._topic_snapshot(self._resolve_topic(topic_id), request)
            for topic_id in topic_ids
        ]
        topic = {
            "topic_ids": [snapshot["topic"]["id"] for snapshot in snapshots],
            "topic_names": [
                snapshot["topic"]["display_name"] for snapshot in snapshots
            ],
            "topic_snapshots": snapshots,
        }
        facts = {
            "comparison_focus": "topic_comparison",
            "target_platform": request.target_platform,
            "topic_count": len(snapshots),
            "max_comparison_topics": settings.ai_max_comparison_topics,
            "topic_snapshots": snapshots,
        }
        scores = {
            "topic_scores": [
                {
                    "topic_id": snapshot["topic"]["id"],
                    "opportunity_score": snapshot["scores"]["opportunity"].get("score"),
                    "decision_score": snapshot["scores"]["decision"].get("score"),
                }
                for snapshot in snapshots
            ]
        }
        evidence = tuple(
            evidence for snapshot in snapshots for evidence in snapshot["evidence"]
        )
        uncertainty = {
            "missing_platform_coverage": [
                snapshot["topic"]["id"]
                for snapshot in snapshots
                if not snapshot["facts"]["latest_signals"]
            ],
            "notes": (
                "Comparison is limited to the supplied topics and persisted evidence."
            ),
        }
        traceability = {
            "topic_ids": [snapshot["topic"]["id"] for snapshot in snapshots],
            "decision_ids": [
                snapshot["traceability"].get("decision_id") for snapshot in snapshots
            ],
            "opportunity_ids": [
                snapshot["traceability"].get("opportunity_id") for snapshot in snapshots
            ],
        }
        missing_data = tuple(
            sorted(
                {item for snapshot in snapshots for item in snapshot["missing_data"]}
            )
        )
        contradictions = tuple(
            sorted(
                {item for snapshot in snapshots for item in snapshot["contradictions"]}
            )
        )
        return ReasoningContext(
            context_version=settings.reasoning_context_version,
            reasoning_type=request.reasoning_type,
            topic=topic,
            facts=facts,
            scores=scores,
            evidence=evidence,
            uncertainty=uncertainty,
            missing_data=missing_data,
            contradictions=contradictions,
            traceability=traceability,
        )

    def _change_context(self, request: ReasoningRequest) -> ReasoningContext:
        topic = self._resolve_topic(request.topic_id)
        current_decision = self._resolve_decision(request.current_decision_id)
        previous_decision = self._resolve_decision(request.previous_decision_id)
        opportunity = self._resolve_opportunity(
            request.opportunity_id,
            topic.id if topic is not None else None,
        )
        return self._context_for_topic(
            request=request,
            topic=topic,
            decision=current_decision or previous_decision,
            opportunity=opportunity,
            previous_decision=previous_decision,
            current_decision=current_decision,
        )

    def _context_for_topic(
        self,
        *,
        request: ReasoningRequest,
        topic: Topic | None,
        decision: DecisionModel | None,
        opportunity: OpportunityScoreModel | None,
        previous_decision: DecisionModel | None = None,
        current_decision: DecisionModel | None = None,
    ) -> ReasoningContext:
        if topic is None:
            raise ValueError("Reasoning context requires a topic")

        observations = tuple(
            self.history_repository.list_by_topic(
                topic.id, settings.ai_max_historical_observations, 0
            )
        )
        latest_signals = tuple(
            self.signal_repository.list_by_topic(
                topic.id, settings.ai_max_evidence_items, 0
            )
        )
        relationships = tuple(
            self.relationship_repository.list_by_topic(topic.id)[
                : settings.knowledge_graph_limit
            ]
        )
        decision_evidence = (
            tuple(self.evidence_repository.list_by_decision(decision.id))
            if decision is not None
            else ()
        )
        historical_evidence = tuple(
            self.history_evidence_repository.list_by_topic(topic.id)
        )
        evidence_refs = self._evidence_references(
            decision_evidence or historical_evidence
        )
        analytics = self._analytics_from_observations(observations)
        latest_opportunity = opportunity or self.opportunity_repository.latest_by_topic(
            topic.id
        )
        latest_decision = decision or self._latest_decision(topic.id)
        topic_data = self._topic_data(
            topic, observations, latest_signals, relationships
        )
        facts = {
            "topic_name": topic.display_name,
            "topic_aliases": topic_data["topic_aliases"],
            "topic_relationships": topic_data["relationships"],
            "latest_signals": topic_data["latest_signals"],
            "historical_signal_timeline": topic_data["historical_signal_timeline"],
            "opportunity": self._opportunity_data(latest_opportunity),
            "decision": self._decision_data(latest_decision),
            "platform_metadata": {
                "target_platform": request.target_platform,
                "supported_platforms": [signal.source for signal in latest_signals],
            },
            "neutral_defaults_used": settings.neutral_factor_defaults,
            "data_freshness_timestamps": topic_data["data_freshness_timestamps"],
        }
        scores = {
            "historical": asdict(analytics),
            "opportunity": self._opportunity_scores(latest_opportunity),
            "decision": self._decision_scores(latest_decision),
        }
        uncertainty = {
            "missing_platform_coverage": self._missing_platforms(
                latest_signals, request.target_platform
            ),
            "freshness_note": (
                "Evidence is grounded in the latest persisted signals and observations."
            ),
        }
        missing_data = tuple(
            sorted(
                set(topic_data["missing_data"])
                | set(self._missing_data_from_decision(decision))
                | set(self._missing_data_from_opportunity(latest_opportunity))
            )
        )
        contradictions = tuple(
            sorted(
                {
                    *topic_data["contradictions"],
                    *self._contradictions_from_analytics(analytics),
                }
            )
        )
        traceability = {
            "topic_id": topic.id,
            "decision_id": latest_decision.id if latest_decision is not None else None,
            "opportunity_id": (
                latest_opportunity.id if latest_opportunity is not None else None
            ),
            "signal_ids": [signal.id for signal in latest_signals],
            "observation_ids": [observation.id for observation in observations],
            "evidence_ids": [evidence.evidence_id for evidence in evidence_refs],
            "correlation_id": self._correlation_id(
                topic, latest_signals, latest_decision
            ),
            "engine_version": (
                latest_decision.engine_version if latest_decision is not None else None
            ),
            "event_version": (
                latest_decision.event_version if latest_decision is not None else None
            ),
            "context_version": settings.reasoning_context_version,
            "prompt_version": settings.ai_reasoning_prompt_version,
        }
        return ReasoningContext(
            context_version=settings.reasoning_context_version,
            reasoning_type=request.reasoning_type,
            topic=topic_data["topic"],
            facts=facts,
            scores=scores,
            evidence=evidence_refs,
            uncertainty=uncertainty,
            missing_data=missing_data,
            contradictions=contradictions,
            traceability=traceability,
        )

    def _topic_snapshot(
        self, topic: Topic, request: ReasoningRequest
    ) -> dict[str, object]:
        context = self._context_for_topic(
            request=request,
            topic=topic,
            decision=self._latest_decision(topic.id),
            opportunity=self.opportunity_repository.latest_by_topic(topic.id),
        )
        return {
            "topic": context.topic,
            "facts": context.facts,
            "scores": context.scores,
            "evidence": list(context.evidence),
            "uncertainty": context.uncertainty,
            "missing_data": list(context.missing_data),
            "contradictions": list(context.contradictions),
            "traceability": context.traceability,
        }

    def _resolve_topic(self, topic_id: str | None) -> Topic | None:
        if topic_id is None:
            return None
        return self.topic_repository.get_by_id(topic_id)

    def _resolve_decision(self, decision_id: str | None) -> DecisionModel | None:
        if decision_id is None:
            return None
        return self.decision_repository.get_by_id(decision_id)

    def _resolve_opportunity(
        self,
        opportunity_id: str | None,
        topic_id: str | None,
    ) -> OpportunityScoreModel | None:
        if opportunity_id is not None:
            return self.opportunity_repository.get_by_id(opportunity_id)
        if topic_id is None:
            return None
        return self.opportunity_repository.latest_by_topic(topic_id)

    def _latest_decision(self, topic_id: str) -> DecisionModel | None:
        decisions = self.decision_repository.list_by_topic(topic_id, 1, 0)
        return decisions[0] if decisions else None

    def _comparison_topic_ids(self, request: ReasoningRequest) -> tuple[str, ...]:
        if request.topic_ids:
            return request.topic_ids[: settings.ai_max_comparison_topics]
        if request.opportunity_ids:
            topic_ids: list[str] = []
            for opportunity_id in request.opportunity_ids[
                : settings.ai_max_comparison_topics
            ]:
                opportunity = self.opportunity_repository.get_by_id(opportunity_id)
                if opportunity is not None:
                    topic_ids.append(opportunity.topic_id)
            return tuple(topic_ids)
        raise ValueError("Comparison reasoning requires topic_ids or opportunity_ids")

    def _topic_data(
        self,
        topic: Topic,
        observations: tuple[HistoricalObservationModel, ...],
        latest_signals: tuple[TrendSignalModel, ...],
        relationships: tuple[TopicRelationshipModel, ...],
    ) -> dict[str, object]:
        topic_aliases = self._topic_aliases(topic, latest_signals, observations)
        return {
            "topic": {
                "id": topic.id,
                "display_name": topic.display_name,
                "normalized_key": topic.normalized_key,
                "created_at": topic.created_at.isoformat(),
            },
            "topic_aliases": topic_aliases,
            "relationships": [
                self._relationship_data(relationship) for relationship in relationships
            ],
            "latest_signals": [self._signal_data(signal) for signal in latest_signals],
            "historical_signal_timeline": [
                self._observation_data(observation) for observation in observations
            ],
            "data_freshness_timestamps": {
                "latest_signal_at": (
                    latest_signals[0].created_at.isoformat() if latest_signals else None
                ),
                "latest_observation_at": (
                    observations[0].observed_at.isoformat() if observations else None
                ),
            },
            "missing_data": self._missing_topic_data(
                topic, latest_signals, observations
            ),
            "contradictions": self._topic_contradictions(observations),
        }

    def _topic_aliases(
        self,
        topic: Topic,
        latest_signals: tuple[TrendSignalModel, ...],
        observations: tuple[HistoricalObservationModel, ...],
    ) -> list[str]:
        aliases = {topic.display_name, topic.normalized_key}
        for signal in latest_signals:
            aliases.add(signal.reason)
        for observation in observations:
            raw_item = observation.payload.get("raw_item")
            if isinstance(raw_item, dict):
                query = raw_item.get("query")
                if isinstance(query, str):
                    aliases.add(query)
        return sorted(alias for alias in aliases if alias)

    def _relationship_data(
        self, relationship: TopicRelationshipModel
    ) -> dict[str, object]:
        return {
            "id": relationship.id,
            "source_topic_id": relationship.source_topic_id,
            "target_topic_id": relationship.target_topic_id,
            "relationship_type": relationship.relationship_type,
            "strength": relationship.strength,
            "reason": relationship.reason,
            "correlation_id": relationship.correlation_id,
            "created_at": relationship.created_at.isoformat(),
        }

    def _signal_data(self, signal: TrendSignalModel) -> dict[str, object]:
        return {
            "id": signal.id,
            "topic_id": signal.topic_id,
            "source": signal.source,
            "score": signal.score,
            "confidence": signal.confidence,
            "reason": signal.reason,
            "timestamp": signal.timestamp.isoformat(),
            "correlation_id": signal.correlation_id,
            "created_at": signal.created_at.isoformat(),
        }

    def _observation_data(
        self, observation: HistoricalObservationModel
    ) -> dict[str, object]:
        return {
            "id": observation.id,
            "source": observation.source,
            "connector_name": observation.connector_name,
            "observation_type": observation.observation_type,
            "observed_at": observation.observed_at.isoformat(),
            "change_type": observation.change_type,
            "correlation_id": observation.correlation_id,
        }

    def _analytics_from_observations(
        self, observations: tuple[HistoricalObservationModel, ...]
    ) -> Any:
        from backend.app.services.historical_analytics import HistoricalAnalyticsService

        converted = tuple(
            self._domain_observation(observation) for observation in observations
        )
        return HistoricalAnalyticsService().calculate(converted)

    def _domain_observation(
        self, observation: HistoricalObservationModel
    ) -> HistoricalObservation:
        from backend.app.domain.knowledge import HistoricalObservation

        return HistoricalObservation(
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

    def _evidence_references(
        self, evidence_models: tuple[EvidenceModel | HistoricalEvidenceModel, ...]
    ) -> tuple[ReasoningEvidenceReference, ...]:
        references = [
            ReasoningEvidenceReference(
                evidence_id=str(
                    getattr(evidence, "evidence_id", getattr(evidence, "id", ""))
                ),
                source=str(getattr(evidence, "source", "")),
                factor=evidence.factor,
                claim=evidence.reason,
                contribution=evidence.contribution,
                confidence=evidence.confidence,
            )
            for evidence in evidence_models[: settings.ai_max_evidence_items]
        ]
        return tuple(references)

    def _opportunity_data(
        self, opportunity: OpportunityScoreModel | None
    ) -> dict[str, object]:
        if opportunity is None:
            return {"status": "missing"}
        return {
            "id": opportunity.id,
            "topic_id": opportunity.topic_id,
            "observation_id": opportunity.observation_id,
            "score": opportunity.score,
            "confidence": opportunity.confidence,
            "version": opportunity.version,
            "dimensions": opportunity.dimensions,
            "explanations": opportunity.explanations,
            "correlation_id": opportunity.correlation_id,
            "created_at": opportunity.created_at.isoformat(),
        }

    def _decision_data(self, decision: DecisionModel | None) -> dict[str, object]:
        if decision is None:
            return {"status": "missing"}
        return {
            "id": decision.id,
            "topic_id": decision.topic_id,
            "topic_name": decision.topic_name,
            "decision_type": decision.decision_type,
            "score": decision.score,
            "confidence": decision.confidence,
            "summary": decision.summary,
            "recommended_action": decision.recommended_action,
            "engine_version": decision.engine_version,
            "event_version": decision.event_version,
            "correlation_id": decision.correlation_id,
            "weights_snapshot": decision.weights_snapshot,
            "created_at": decision.created_at.isoformat(),
        }

    def _opportunity_scores(
        self, opportunity: OpportunityScoreModel | None
    ) -> dict[str, float]:
        return opportunity.dimensions if opportunity is not None else {}

    def _decision_scores(self, decision: DecisionModel | None) -> dict[str, float]:
        if decision is None:
            return {}
        return {
            "decision_score": decision.score,
            "decision_confidence": decision.confidence,
        }

    def _missing_topic_data(
        self,
        topic: Topic,
        latest_signals: tuple[TrendSignalModel, ...],
        observations: tuple[HistoricalObservationModel, ...],
    ) -> list[str]:
        missing = []
        if not latest_signals:
            missing.append(f"no latest signals for {topic.id}")
        if not observations:
            missing.append(f"no historical observations for {topic.id}")
        return missing

    def _topic_contradictions(
        self, observations: tuple[HistoricalObservationModel, ...]
    ) -> list[str]:
        if len(observations) < 2:
            return []
        scores = [self._signal_score(observation) for observation in observations]
        if max(scores) - min(scores) > 25.0:
            return ["historical observations show materially different signal levels"]
        return []

    def _missing_data_from_decision(self, decision: DecisionModel | None) -> list[str]:
        if decision is None:
            return ["decision missing"]
        return []

    def _missing_data_from_opportunity(
        self, opportunity: OpportunityScoreModel | None
    ) -> list[str]:
        if opportunity is None:
            return ["opportunity missing"]
        return []

    def _missing_platforms(
        self,
        latest_signals: tuple[TrendSignalModel, ...],
        target_platform: str | None,
    ) -> list[str]:
        if target_platform is None:
            return []
        present = {signal.source for signal in latest_signals}
        if target_platform not in present:
            return [f"no evidence for platform {target_platform}"]
        return []

    def _contradictions_from_analytics(self, analytics: Any) -> list[str]:
        contradictions: list[str] = []
        if getattr(analytics, "decline_detected", False):
            contradictions.append("historical trend is in decline")
        if getattr(analytics, "historical_volatility", 0.0) > 0.5:
            contradictions.append("historical volatility is high")
        return contradictions

    def _correlation_id(
        self,
        topic: Topic,
        latest_signals: tuple[TrendSignalModel, ...],
        decision: DecisionModel | None,
    ) -> str | None:
        if latest_signals:
            return latest_signals[0].correlation_id
        if decision is not None:
            return decision.correlation_id
        return None

    def _signal_score(self, observation: HistoricalObservationModel) -> float:
        value = observation.payload.get("signal_score")
        return float(value) if isinstance(value, (int, float)) else 0.0
