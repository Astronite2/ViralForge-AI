"""Daily YouTube opportunity analysis, selection, and outcome workflow."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.app.connectors.youtube import YouTubeConnector
from backend.app.core.config import settings
from backend.app.domain.connector_orchestration import ConnectorExecutionReport
from backend.app.domain.content import Content
from backend.app.models.money_opportunity import (
    MoneyAnalysisModel,
    MoneyOpportunityModel,
    MoneyOutcomeModel,
    ProductionBriefModel,
)
from backend.app.repositories.content import ContentRepository
from backend.app.schemas.money_opportunity import (
    MoneyAnalysisRead,
    MoneyAnalysisRequest,
    MoneyOpportunityRead,
    OutcomeCreate,
    OutcomeRead,
    OutcomeUpdate,
    ProductionBriefRead,
)
from backend.app.services.connector_status import ConnectorStatusStore
from backend.app.services.money_opportunity import MoneyOpportunityEngine
from backend.app.services.video_brief import VideoBriefService


class MoneyWorkflowError(RuntimeError):
    pass


class MoneyWorkflowUnavailable(MoneyWorkflowError):
    pass


class MoneyWorkflowNotFound(MoneyWorkflowError):
    pass


class MoneyWorkflowService:
    def __init__(
        self,
        session: Session,
        *,
        connector: YouTubeConnector | None = None,
        engine: MoneyOpportunityEngine | None = None,
        brief_service: VideoBriefService | None = None,
        status_store: ConnectorStatusStore | None = None,
    ) -> None:
        self.session = session
        self.connector = connector or YouTubeConnector(api_key=settings.youtube_api_key)
        self.engine = engine or MoneyOpportunityEngine()
        self.brief_service = brief_service or VideoBriefService()
        self.status_store = status_store or ConnectorStatusStore(
            use_redis=connector is None
        )

    def analyze(self, request: MoneyAnalysisRequest) -> MoneyAnalysisRead:
        try:
            raw_items = self.connector.fetch(
                query=request.query, region=request.region, limit=request.limit
            )
        except Exception as exc:
            self._record_status("failed", 0, 0, "youtube_unavailable")
            raise MoneyWorkflowUnavailable(
                "YouTube evidence could not be retrieved for this analysis."
            ) from exc
        if not raw_items:
            self._record_status("empty", 0, 0, None)
            raise MoneyWorkflowUnavailable(
                "YouTube returned no comparable videos; no opportunity score "
                "was created."
            )
        contents: list[Content] = []
        for raw in raw_items:
            try:
                self.connector.validate(raw)
                contents.append(self.connector.normalize(raw))
            except (TypeError, ValueError):
                continue
        if len(contents) < 3:
            raise MoneyWorkflowUnavailable(
                "Fewer than three valid YouTube comparisons were available."
            )
        analysis_id = str(uuid4())
        analysis = MoneyAnalysisModel(
            id=analysis_id,
            query=request.query,
            region=request.region.upper(),
            status="completed",
            request_payload=request.model_dump(mode="json"),
            channel_profile=(
                request.channel_profile.model_dump(mode="json")
                if request.channel_profile
                else None
            ),
        )
        self.session.add(analysis)
        content_repository = ContentRepository(self.session)
        for content in contents:
            content_repository.save(content)
        candidates = self._angles(request.query)
        scored = [
            self.engine.score(
                query=request.query,
                angle=angle,
                contents=contents,
                profile=request.channel_profile,
                angle_index=index,
            )
            for index, angle in enumerate(candidates)
        ]
        scored.sort(
            key=lambda item: (
                -float(item["money_score"]),
                str(item["proposed_video_angle"]),
            )
        )
        models: list[MoneyOpportunityModel] = []
        for rank, payload in enumerate(scored, start=1):
            opportunity_id = str(uuid4())
            public_payload = {
                **payload,
                "id": opportunity_id,
                "analysis_id": analysis_id,
                "rank": rank,
            }
            model = MoneyOpportunityModel(
                id=opportunity_id,
                analysis_id=analysis_id,
                rank=rank,
                topic=request.query,
                money_score=float(payload["money_score"]),
                confidence=float(payload["confidence"]),
                payload=public_payload,
            )
            self.session.add(model)
            models.append(model)
        self.session.commit()
        self._record_status("success", len(raw_items), len(contents), None)
        self.session.refresh(analysis)
        return self._analysis_read(analysis, models)

    def get_analysis(self, analysis_id: str) -> MoneyAnalysisRead:
        analysis = self.session.get(MoneyAnalysisModel, analysis_id)
        if analysis is None:
            raise MoneyWorkflowNotFound("Money opportunity analysis was not found.")
        opportunities = (
            self.session.query(MoneyOpportunityModel)
            .filter(MoneyOpportunityModel.analysis_id == analysis_id)
            .order_by(MoneyOpportunityModel.rank)
            .all()
        )
        return self._analysis_read(analysis, opportunities)

    def generate_brief(self, opportunity_id: str) -> ProductionBriefRead:
        opportunity = self._opportunity(opportunity_id)
        existing = (
            self.session.query(ProductionBriefModel)
            .filter(ProductionBriefModel.opportunity_id == opportunity_id)
            .one_or_none()
        )
        if existing is None:
            brief_id = str(uuid4())
            payload = {
                "id": brief_id,
                "opportunity_id": opportunity_id,
                **self.brief_service.generate(dict(opportunity.payload)),
            }
            existing = ProductionBriefModel(
                id=brief_id, opportunity_id=opportunity_id, payload=payload
            )
            self.session.add(existing)
            self.session.commit()
        return ProductionBriefRead.model_validate(existing.payload)

    def create_outcome(
        self, opportunity_id: str, request: OutcomeCreate
    ) -> OutcomeRead:
        opportunity = self._opportunity(opportunity_id)
        existing = (
            self.session.query(MoneyOutcomeModel)
            .filter(MoneyOutcomeModel.recommendation_id == opportunity_id)
            .one_or_none()
        )
        if existing is not None:
            return OutcomeRead.model_validate(existing)
        outcome = MoneyOutcomeModel(
            id=str(uuid4()),
            recommendation_id=opportunity_id,
            selected_topic=opportunity.topic,
            money_score_at_selection=opportunity.money_score,
            result_classification="pending",
            **request.model_dump(),
        )
        self.session.add(outcome)
        self.session.commit()
        self.session.refresh(outcome)
        return OutcomeRead.model_validate(outcome)

    def update_outcome(self, outcome_id: str, request: OutcomeUpdate) -> OutcomeRead:
        outcome = self.session.get(MoneyOutcomeModel, outcome_id)
        if outcome is None:
            raise MoneyWorkflowNotFound("Outcome record was not found.")
        for field, value in request.model_dump(exclude_unset=True).items():
            setattr(outcome, field, value)
        self.session.commit()
        self.session.refresh(outcome)
        return OutcomeRead.model_validate(outcome)

    def _opportunity(self, opportunity_id: str) -> MoneyOpportunityModel:
        opportunity = self.session.get(MoneyOpportunityModel, opportunity_id)
        if opportunity is None:
            raise MoneyWorkflowNotFound("Money opportunity was not found.")
        return opportunity

    @staticmethod
    def _analysis_read(
        analysis: MoneyAnalysisModel, opportunities: list[MoneyOpportunityModel]
    ) -> MoneyAnalysisRead:
        return MoneyAnalysisRead(
            analysis_id=analysis.id,
            query=analysis.query,
            region=analysis.region,
            status=analysis.status,
            created_at=analysis.created_at or datetime.now(UTC),
            opportunities=[
                MoneyOpportunityRead.model_validate(item.payload)
                for item in opportunities
            ],
        )

    @staticmethod
    def _angles(query: str) -> tuple[str, ...]:
        return (
            f"How {query} works: an evidence-led visual explainer",
            f"{query}: overlooked methods and practical lessons",
            f"{query} myths versus evidence",
        )

    def _record_status(
        self,
        status: str,
        items_fetched: int,
        items_processed: int,
        error_code: str | None,
    ) -> None:
        metadata = getattr(self.connector, "metadata", None)
        self.status_store.record(
            ConnectorExecutionReport(
                connector_name=settings.youtube_source_name,
                status=status,
                items_fetched=items_fetched,
                items_processed=items_processed,
                items_failed=max(items_fetched - items_processed, 0),
                decisions_created=0,
                duration_ms=0,
                errors=(("YouTube evidence retrieval failed.",) if error_code else ()),
                provider=(metadata.provider if metadata else "youtube_data_api"),
                provider_experimental=(
                    metadata.provider_experimental if metadata else False
                ),
                error_code=error_code,
                connector_version=(metadata.version if metadata else "2.0.0"),
                capabilities=(metadata.capabilities.api_values() if metadata else ()),
            ),
            completed_at=datetime.now(UTC),
        )
