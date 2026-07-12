"""Decision persistence access."""

from __future__ import annotations

from backend.app.domain.decision import Decision
from backend.app.models.decision import DecisionModel
from backend.app.repositories.base import Repository


class DecisionRepository(Repository):
    """Database access boundary for decisions."""

    def create(self, topic_id: str, decision: Decision) -> DecisionModel:
        model = DecisionModel(
            id=decision.id,
            topic_id=topic_id,
            topic_name=decision.topic_name,
            decision_type=decision.decision_type.value,
            score=decision.score,
            confidence=decision.confidence,
            summary=decision.summary,
            recommended_action=decision.recommended_action,
            engine_version=decision.engine_version,
            event_version=decision.event_version,
            correlation_id=decision.correlation_id,
            weights_snapshot=decision.weights_snapshot,
        )
        self.session.add(model)
        self.session.flush()
        return model

    def get_by_id(self, decision_id: str) -> DecisionModel | None:
        return self.session.get(DecisionModel, decision_id)

    def list(self, limit: int, offset: int) -> list[DecisionModel]:
        query = (
            self.session.query(DecisionModel)
            .order_by(DecisionModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(query)

    def list_by_topic(
        self, topic_id: str, limit: int, offset: int
    ) -> list[DecisionModel]:
        query = (
            self.session.query(DecisionModel)
            .filter(DecisionModel.topic_id == topic_id)
            .order_by(DecisionModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(query)
