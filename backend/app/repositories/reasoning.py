"""Reasoning persistence access."""

from __future__ import annotations

from backend.app.models.reasoning import (
    ReasoningResultModel,
    ReasoningRunModel,
    ReasoningSourceLinkModel,
    ReasoningValidationErrorModel,
)
from backend.app.repositories.base import Repository


class ReasoningRunRepository(Repository):
    """Database access boundary for reasoning runs."""

    def create(self, model: ReasoningRunModel) -> ReasoningRunModel:
        self.session.add(model)
        self.session.flush()
        return model

    def get_by_id(self, run_id: str) -> ReasoningRunModel | None:
        return self.session.get(ReasoningRunModel, run_id)

    def latest_success_by_input_hash(self, input_hash: str) -> ReasoningRunModel | None:
        query = (
            self.session.query(ReasoningRunModel)
            .filter(
                ReasoningRunModel.input_hash == input_hash,
                ReasoningRunModel.status == "SUCCEEDED",
            )
            .order_by(ReasoningRunModel.completed_at.desc())
        )
        return query.first()

    def list_by_topic(self, topic_id: str) -> list[ReasoningRunModel]:
        query = (
            self.session.query(ReasoningRunModel)
            .filter(ReasoningRunModel.topic_id == topic_id)
            .order_by(ReasoningRunModel.created_at.desc())
        )
        return list(query)

    def list_by_decision(self, decision_id: str) -> list[ReasoningRunModel]:
        query = (
            self.session.query(ReasoningRunModel)
            .filter(ReasoningRunModel.decision_id == decision_id)
            .order_by(ReasoningRunModel.created_at.desc())
        )
        return list(query)


class ReasoningResultRepository(Repository):
    """Database access boundary for reasoning results."""

    def create(self, model: ReasoningResultModel) -> ReasoningResultModel:
        self.session.add(model)
        self.session.flush()
        return model

    def get_by_id(self, result_id: str) -> ReasoningResultModel | None:
        return self.session.get(ReasoningResultModel, result_id)

    def get_by_run_id(self, run_id: str) -> ReasoningResultModel | None:
        query = self.session.query(ReasoningResultModel).filter(
            ReasoningResultModel.reasoning_run_id == run_id
        )
        return query.one_or_none()

    def latest_success_by_input_hash(
        self, input_hash: str
    ) -> ReasoningResultModel | None:
        query = (
            self.session.query(ReasoningResultModel)
            .filter(
                ReasoningResultModel.input_hash == input_hash,
                ReasoningResultModel.status == "SUCCEEDED",
            )
            .order_by(ReasoningResultModel.completed_at.desc())
        )
        return query.first()

    def list_by_topic(self, topic_id: str) -> list[ReasoningResultModel]:
        query = (
            self.session.query(ReasoningResultModel)
            .filter(ReasoningResultModel.topic_id == topic_id)
            .order_by(ReasoningResultModel.created_at.desc())
        )
        return list(query)

    def list_by_decision(self, decision_id: str) -> list[ReasoningResultModel]:
        query = (
            self.session.query(ReasoningResultModel)
            .filter(ReasoningResultModel.decision_id == decision_id)
            .order_by(ReasoningResultModel.created_at.desc())
        )
        return list(query)


class ReasoningSourceLinkRepository(Repository):
    """Database access boundary for reasoning trace links."""

    def create(self, model: ReasoningSourceLinkModel) -> ReasoningSourceLinkModel:
        self.session.add(model)
        self.session.flush()
        return model

    def list_by_result(self, result_id: str) -> list[ReasoningSourceLinkModel]:
        query = (
            self.session.query(ReasoningSourceLinkModel)
            .filter(ReasoningSourceLinkModel.reasoning_result_id == result_id)
            .order_by(ReasoningSourceLinkModel.created_at.asc())
        )
        return list(query)


class ReasoningValidationErrorRepository(Repository):
    """Database access boundary for validation failures."""

    def create(
        self, model: ReasoningValidationErrorModel
    ) -> ReasoningValidationErrorModel:
        self.session.add(model)
        self.session.flush()
        return model

    def list_by_run(self, run_id: str) -> list[ReasoningValidationErrorModel]:
        query = (
            self.session.query(ReasoningValidationErrorModel)
            .filter(ReasoningValidationErrorModel.reasoning_run_id == run_id)
            .order_by(ReasoningValidationErrorModel.created_at.asc())
        )
        return list(query)
