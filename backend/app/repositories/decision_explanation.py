"""Decision explanation persistence access."""

from __future__ import annotations

from backend.app.domain.decision_explanation import DecisionExplanation
from backend.app.models.decision_explanation import DecisionExplanationModel
from backend.app.repositories.base import Repository


class DecisionExplanationRepository(Repository):
    """Database access boundary for decision explanations."""

    def create(
        self, decision_id: str, explanation: DecisionExplanation
    ) -> DecisionExplanationModel:
        model = DecisionExplanationModel(
            decision_id=decision_id,
            factor=explanation.factor,
            weight=explanation.weight,
            contribution=explanation.contribution,
            confidence=explanation.confidence,
            reason=explanation.reason,
        )
        self.session.add(model)
        self.session.flush()
        return model

    def list_by_decision(self, decision_id: str) -> list[DecisionExplanationModel]:
        query = (
            self.session.query(DecisionExplanationModel)
            .filter(DecisionExplanationModel.decision_id == decision_id)
            .order_by(DecisionExplanationModel.id)
        )
        return list(query)
