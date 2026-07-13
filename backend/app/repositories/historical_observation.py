"""Historical observation persistence access."""

from __future__ import annotations

from backend.app.models.historical_observation import HistoricalObservationModel
from backend.app.repositories.base import Repository


class HistoricalObservationRepository(Repository):
    """Database access boundary for historical topic observations."""

    def get_by_id(self, observation_id: str) -> HistoricalObservationModel | None:
        return self.session.get(HistoricalObservationModel, observation_id)

    def get_by_hash(self, observation_hash: str) -> HistoricalObservationModel | None:
        query = self.session.query(HistoricalObservationModel).filter(
            HistoricalObservationModel.observation_hash == observation_hash
        )
        return query.one_or_none()

    def get_latest_for_topic(
        self,
        topic_id: str,
        *,
        source: str | None = None,
        connector_name: str | None = None,
    ) -> HistoricalObservationModel | None:
        query = self.session.query(HistoricalObservationModel).filter(
            HistoricalObservationModel.topic_id == topic_id
        )
        if source is not None:
            query = query.filter(HistoricalObservationModel.source == source)
        if connector_name is not None:
            query = query.filter(
                HistoricalObservationModel.connector_name == connector_name
            )
        return query.order_by(HistoricalObservationModel.observed_at.desc()).first()

    def list_by_topic(
        self, topic_id: str, limit: int, offset: int
    ) -> list[HistoricalObservationModel]:
        query = (
            self.session.query(HistoricalObservationModel)
            .filter(HistoricalObservationModel.topic_id == topic_id)
            .order_by(HistoricalObservationModel.observed_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(query)

    def create(self, model: HistoricalObservationModel) -> HistoricalObservationModel:
        self.session.add(model)
        self.session.flush()
        return model
