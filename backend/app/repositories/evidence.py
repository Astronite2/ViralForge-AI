"""Evidence persistence access."""

from __future__ import annotations

from backend.app.domain.evidence import Evidence
from backend.app.models.evidence import EvidenceModel
from backend.app.repositories.base import Repository


class EvidenceRepository(Repository):
    """Database access boundary for decision evidence."""

    def create(
        self, decision_id: str, signal_id: str, evidence: Evidence
    ) -> EvidenceModel:
        model = EvidenceModel(
            id=evidence.id,
            signal_id=signal_id,
            decision_id=decision_id,
            source=evidence.source,
            factor=evidence.factor,
            weight=evidence.weight,
            raw_value=evidence.raw_value,
            normalized_value=evidence.normalized_value,
            contribution=evidence.contribution,
            confidence=evidence.confidence,
            reason=evidence.reason,
            timestamp=evidence.timestamp,
            correlation_id=evidence.correlation_id,
        )
        self.session.add(model)
        self.session.flush()
        return model

    def list_by_decision(self, decision_id: str) -> list[EvidenceModel]:
        query = (
            self.session.query(EvidenceModel)
            .filter(EvidenceModel.decision_id == decision_id)
            .order_by(EvidenceModel.id)
        )
        return list(query)

    def get_by_id(self, evidence_id: str) -> EvidenceModel | None:
        return self.session.get(EvidenceModel, evidence_id)
