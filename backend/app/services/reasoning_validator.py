"""Grounded validation for AI reasoning outputs."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend.app.domain.reasoning import (
    ReasoningContext,
    ReasoningEvidenceReference,
    ReasoningValidationIssue,
)
from backend.app.models.decision import DecisionModel
from backend.app.models.evidence import EvidenceModel
from backend.app.models.historical_evidence import HistoricalEvidenceModel
from backend.app.models.opportunity_score import OpportunityScoreModel
from backend.app.models.topic import Topic
from backend.app.repositories.decision import DecisionRepository
from backend.app.repositories.evidence import EvidenceRepository
from backend.app.repositories.historical_evidence import HistoricalEvidenceRepository
from backend.app.repositories.opportunity_score import OpportunityScoreRepository
from backend.app.repositories.topic import TopicRepository
from backend.app.schemas.reasoning import ReasoningResultRead


@dataclass
class ReasoningValidator:
    """Validate that reasoning output is grounded in persisted data."""

    session: Session

    def __post_init__(self) -> None:
        self.topic_repository = TopicRepository(self.session)
        self.decision_repository = DecisionRepository(self.session)
        self.evidence_repository = EvidenceRepository(self.session)
        self.historical_evidence_repository = HistoricalEvidenceRepository(self.session)
        self.opportunity_repository = OpportunityScoreRepository(self.session)

    def validate(
        self, context: ReasoningContext, result: ReasoningResultRead
    ) -> list[ReasoningValidationIssue]:
        """Return structured validation issues for any grounding mismatch."""
        issues: list[ReasoningValidationIssue] = []
        topic = self._topic(result.topic_id)
        if result.topic_id is not None and topic is None:
            issues.append(
                ReasoningValidationIssue(
                    field="topic_id",
                    message="Referenced topic does not exist",
                )
            )

        decision = self._decision(result.decision_id)
        if result.decision_id is not None and decision is None:
            issues.append(
                ReasoningValidationIssue(
                    field="decision_id",
                    message="Referenced decision does not exist",
                )
            )

        opportunity = self._opportunity(result.opportunity_id)
        if result.opportunity_id is not None and opportunity is None:
            issues.append(
                ReasoningValidationIssue(
                    field="opportunity_id",
                    message="Referenced opportunity does not exist",
                )
            )

        evidence_index = self._evidence_index(context)
        issues.extend(
            self._validate_evidence_list(
                "supporting_evidence", result.supporting_evidence, evidence_index
            )
        )
        issues.extend(
            self._validate_evidence_list(
                "conflicting_evidence", result.conflicting_evidence, evidence_index
            )
        )
        issues.extend(
            self._validate_evidence_list(
                "source_references", result.source_references, evidence_index
            )
        )
        issues.extend(self._validate_alternatives(result, context))
        issues.extend(self._validate_recommendation(result, decision))
        issues.extend(self._validate_coverage(result, context))
        return issues

    def _validate_evidence_list(
        self,
        field: str,
        items: list[ReasoningEvidenceReference],
        evidence_index: dict[str, EvidenceModel | HistoricalEvidenceModel],
    ) -> list[ReasoningValidationIssue]:
        issues: list[ReasoningValidationIssue] = []
        for item in items:
            evidence = evidence_index.get(item.evidence_id)
            if evidence is None:
                issues.append(
                    ReasoningValidationIssue(
                        field=field,
                        message=f"Evidence {item.evidence_id} does not exist",
                    )
                )
                continue
            if abs(item.contribution - evidence.contribution) > 0.01:
                issues.append(
                    ReasoningValidationIssue(
                        field=field,
                        message=f"Evidence {item.evidence_id} contribution mismatch",
                    )
                )
            if abs(item.confidence - evidence.confidence) > 0.01:
                issues.append(
                    ReasoningValidationIssue(
                        field=field,
                        message=f"Evidence {item.evidence_id} confidence mismatch",
                    )
                )
            if item.source != evidence.source:
                issues.append(
                    ReasoningValidationIssue(
                        field=field,
                        message=f"Evidence {item.evidence_id} source mismatch",
                    )
                )
        return issues

    def _validate_alternatives(
        self, result: ReasoningResultRead, context: ReasoningContext
    ) -> list[ReasoningValidationIssue]:
        issues: list[ReasoningValidationIssue] = []
        topic_scores = self._topic_score_lookup(context)
        for comparison in result.alternative_topics:
            if comparison.topic_id not in topic_scores:
                issues.append(
                    ReasoningValidationIssue(
                        field="alternative_topics",
                        message=f"Topic {comparison.topic_id} was not grounded",
                    )
                )
                continue
            opportunity_score, decision_score = topic_scores[comparison.topic_id]
            if abs(comparison.opportunity_score - opportunity_score) > 0.01:
                issues.append(
                    ReasoningValidationIssue(
                        field="alternative_topics",
                        message=(
                            f"Topic {comparison.topic_id} opportunity score mismatch"
                        ),
                    )
                )
            if abs(comparison.decision_score - decision_score) > 0.01:
                issues.append(
                    ReasoningValidationIssue(
                        field="alternative_topics",
                        message=f"Topic {comparison.topic_id} decision score mismatch",
                    )
                )
        return issues

    def _validate_recommendation(
        self, result: ReasoningResultRead, decision: DecisionModel | None
    ) -> list[ReasoningValidationIssue]:
        if decision is None:
            return []
        recommended_action = result.recommended_execution.get("recommended_action")
        if isinstance(recommended_action, str) and recommended_action:
            deterministic_action = decision.recommended_action
            if recommended_action != deterministic_action and "alternative" not in (
                result.recommended_execution.get("caveat", "").lower()
                if isinstance(result.recommended_execution.get("caveat"), str)
                else ""
            ):
                return [
                    ReasoningValidationIssue(
                        field="recommended_execution",
                        message="Recommended action contradicts deterministic decision",
                    )
                ]
        return []

    def _validate_coverage(
        self, result: ReasoningResultRead, context: ReasoningContext
    ) -> list[ReasoningValidationIssue]:
        issues: list[ReasoningValidationIssue] = []
        supported_platforms = context.facts.get("platform_metadata", {})
        target_platform = ""
        if isinstance(supported_platforms, dict):
            value = supported_platforms.get("target_platform")
            if isinstance(value, str):
                target_platform = value
            platforms = supported_platforms.get("supported_platforms", [])
        else:
            platforms = []
        if target_platform and target_platform not in platforms:
            if target_platform.lower() not in result.why_this_platform.lower():
                issues.append(
                    ReasoningValidationIssue(
                        field="why_this_platform",
                        message="Claimed platform coverage is unsupported",
                    )
                )
        if context.missing_data and not result.caveats:
            issues.append(
                ReasoningValidationIssue(
                    field="caveats",
                    message="Missing data must be disclosed in caveats",
                )
            )
        if context.contradictions and not result.conflicting_evidence:
            issues.append(
                ReasoningValidationIssue(
                    field="conflicting_evidence",
                    message="Contradictions must remain visible",
                )
            )
        return issues

    def _evidence_index(
        self, context: ReasoningContext
    ) -> dict[str, EvidenceModel | HistoricalEvidenceModel]:
        evidence_ids = [evidence.evidence_id for evidence in context.evidence]
        index: dict[str, EvidenceModel | HistoricalEvidenceModel] = {}
        for evidence_id in evidence_ids:
            evidence = self.evidence_repository.get_by_id(evidence_id)
            if evidence is not None:
                index[evidence_id] = evidence
                continue
            historical = self._historical_evidence(evidence_id)
            if historical is not None:
                index[evidence_id] = historical
        return index

    def _historical_evidence(self, evidence_id: str) -> HistoricalEvidenceModel | None:
        query = self.session.query(HistoricalEvidenceModel).filter(
            HistoricalEvidenceModel.evidence_id == evidence_id
        )
        return query.one_or_none()

    def _topic(self, topic_id: str | None) -> Topic | None:
        if topic_id is None:
            return None
        return self.topic_repository.get_by_id(topic_id)

    def _decision(self, decision_id: str | None) -> DecisionModel | None:
        return (
            self.decision_repository.get_by_id(decision_id)
            if decision_id is not None
            else None
        )

    def _opportunity(self, opportunity_id: str | None) -> OpportunityScoreModel | None:
        return (
            self.opportunity_repository.get_by_id(opportunity_id)
            if opportunity_id is not None
            else None
        )

    def _topic_score_lookup(
        self, context: ReasoningContext
    ) -> dict[str, tuple[float, float]]:
        lookup: dict[str, tuple[float, float]] = {}
        topic_snapshots = context.facts.get("topic_snapshots")
        if not isinstance(topic_snapshots, list):
            return lookup
        for snapshot in topic_snapshots:
            if not isinstance(snapshot, dict):
                continue
            topic = snapshot.get("topic", {})
            scores = snapshot.get("scores", {})
            if not isinstance(topic, dict) or not isinstance(scores, dict):
                continue
            topic_id = topic.get("id")
            if not isinstance(topic_id, str):
                continue
            opportunity = scores.get("opportunity", {})
            decision = scores.get("decision", {})
            opportunity_score = (
                float(opportunity.get("score", 0.0))
                if isinstance(opportunity, dict)
                else 0.0
            )
            decision_score = (
                float(decision.get("score", 0.0)) if isinstance(decision, dict) else 0.0
            )
            lookup[topic_id] = (opportunity_score, decision_score)
        return lookup
