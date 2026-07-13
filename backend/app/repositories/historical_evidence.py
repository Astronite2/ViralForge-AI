"""Historical evidence persistence access."""

from __future__ import annotations

from backend.app.models.historical_evidence import HistoricalEvidenceModel
from backend.app.repositories.base import Repository


class HistoricalEvidenceRepository(Repository):
    """Database access boundary for historical evidence snapshots."""

    def create(self, model: HistoricalEvidenceModel) -> HistoricalEvidenceModel:
        self.session.add(model)
        self.session.flush()
        return model

    def list_by_topic(self, topic_id: str) -> list[HistoricalEvidenceModel]:
        query = (
            self.session.query(HistoricalEvidenceModel)
            .filter(HistoricalEvidenceModel.topic_id == topic_id)
            .order_by(HistoricalEvidenceModel.timestamp.desc())
        )
        return list(query)

    def list_by_observation(self, observation_id: str) -> list[HistoricalEvidenceModel]:
        query = (
            self.session.query(HistoricalEvidenceModel)
            .filter(HistoricalEvidenceModel.observation_id == observation_id)
            .order_by(HistoricalEvidenceModel.timestamp.desc())
        )
        return list(query)
