"""AI reasoning application service."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.domain.reasoning import (
    ReasoningContext,
    ReasoningPromptBundle,
    ReasoningRequest,
    ReasoningStatus,
    ReasoningType,
    ReasoningValidationIssue,
)
from backend.app.models.reasoning import (
    ReasoningResultModel,
    ReasoningRunModel,
    ReasoningSourceLinkModel,
    ReasoningValidationErrorModel,
)
from backend.app.reasoning.errors import (
    ReasoningConfigurationError,
    ReasoningDisabledError,
    ReasoningTransientProviderError,
    ReasoningValidationError,
)
from backend.app.reasoning.prompts.change_summary_v1 import (
    build_prompt as build_change_prompt,
)
from backend.app.reasoning.prompts.decision_explanation_v1 import (
    build_prompt as build_decision_prompt,
)
from backend.app.reasoning.prompts.execution_strategy_v1 import (
    build_prompt as build_execution_prompt,
)
from backend.app.reasoning.prompts.opportunity_comparison_v1 import (
    build_prompt as build_comparison_prompt,
)
from backend.app.reasoning.providers.base import ReasoningProvider
from backend.app.reasoning.providers.factory import build_reasoning_provider
from backend.app.repositories.decision import DecisionRepository
from backend.app.repositories.evidence import EvidenceRepository
from backend.app.repositories.opportunity_score import OpportunityScoreRepository
from backend.app.repositories.reasoning import (
    ReasoningResultRepository,
    ReasoningRunRepository,
    ReasoningSourceLinkRepository,
    ReasoningValidationErrorRepository,
)
from backend.app.repositories.topic import TopicRepository
from backend.app.schemas.reasoning import (
    ReasoningResultRead,
    ReasoningRunRead,
)
from backend.app.services.reasoning_context import ReasoningContextBuilder
from backend.app.services.reasoning_validator import ReasoningValidator
from backend.app.utils.events import (
    ReasoningCompleted,
    ReasoningEventEmitter,
    ReasoningFailed,
    ReasoningRequested,
    ReasoningValidationFailed,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ReasoningExecutionResult:
    """Structured result returned by the reasoning service."""

    run: ReasoningRunRead
    result: ReasoningResultRead | None
    cached: bool = False


class ReasoningService:
    """Execute AI reasoning above the deterministic intelligence stack."""

    def __init__(
        self,
        session: Session,
        *,
        provider: ReasoningProvider | None = None,
        context_builder: ReasoningContextBuilder | None = None,
        validator: ReasoningValidator | None = None,
        event_emitter: ReasoningEventEmitter | None = None,
    ) -> None:
        self.session = session
        self.provider = provider
        self.context_builder = context_builder or ReasoningContextBuilder(session)
        self.validator = validator or ReasoningValidator(session)
        self.event_emitter = event_emitter
        self.run_repository = ReasoningRunRepository(session)
        self.result_repository = ReasoningResultRepository(session)
        self.source_link_repository = ReasoningSourceLinkRepository(session)
        self.validation_error_repository = ReasoningValidationErrorRepository(session)
        self.topic_repository = TopicRepository(session)
        self.decision_repository = DecisionRepository(session)
        self.evidence_repository = EvidenceRepository(session)
        self.opportunity_repository = OpportunityScoreRepository(session)

    def explain_decision(
        self, decision_id: str, *, force_refresh: bool = False
    ) -> ReasoningExecutionResult:
        """Explain one deterministic decision."""
        decision = self.decision_repository.get_by_id(decision_id)
        if decision is None:
            raise ValueError("Decision not found")
        request = self._build_request(
            reasoning_type=ReasoningType.DECISION_EXPLANATION,
            decision_id=decision_id,
            topic_id=decision.topic_id,
            force_refresh=force_refresh,
        )
        return self._execute(request)

    def compare_opportunities(
        self,
        *,
        topic_ids: list[str] | None = None,
        opportunity_ids: list[str] | None = None,
        force_refresh: bool = False,
    ) -> ReasoningExecutionResult:
        """Compare two or more topics or opportunities."""
        request = self._build_request(
            reasoning_type=ReasoningType.OPPORTUNITY_COMPARISON,
            topic_ids=tuple(topic_ids or ()),
            opportunity_ids=tuple(opportunity_ids or ()),
            force_refresh=force_refresh,
        )
        return self._execute(request)

    def execution_strategy(
        self,
        decision_id: str,
        *,
        target_platform: str | None = None,
        force_refresh: bool = False,
    ) -> ReasoningExecutionResult:
        """Suggest an execution strategy for one decision."""
        decision = self.decision_repository.get_by_id(decision_id)
        if decision is None:
            raise ValueError("Decision not found")
        request = self._build_request(
            reasoning_type=ReasoningType.EXECUTION_STRATEGY,
            decision_id=decision_id,
            topic_id=decision.topic_id,
            target_platform=target_platform,
            force_refresh=force_refresh,
        )
        return self._execute(request)

    def change_summary(
        self,
        topic_id: str,
        *,
        previous_decision_id: str | None = None,
        current_decision_id: str | None = None,
        force_refresh: bool = False,
    ) -> ReasoningExecutionResult:
        """Summarize change since the previous decision or reasoning result."""
        if self.topic_repository.get_by_id(topic_id) is None:
            raise ValueError("Topic not found")
        request = self._build_request(
            reasoning_type=ReasoningType.CHANGE_SUMMARY,
            topic_id=topic_id,
            previous_decision_id=previous_decision_id,
            current_decision_id=current_decision_id,
            force_refresh=force_refresh,
        )
        return self._execute(request)

    def get_result(self, result_id: str) -> ReasoningResultRead | None:
        result = self.result_repository.get_by_id(result_id)
        if result is None:
            return None
        return self._read_result(result)

    def list_by_decision(self, decision_id: str) -> list[ReasoningResultRead]:
        return [
            self._read_result(result)
            for result in self.result_repository.list_by_decision(decision_id)
        ]

    def list_by_topic(self, topic_id: str) -> list[ReasoningResultRead]:
        return [
            self._read_result(result)
            for result in self.result_repository.list_by_topic(topic_id)
        ]

    def _execute(self, request: ReasoningRequest) -> ReasoningExecutionResult:
        self._ensure_available()
        context = self.context_builder.build(request)
        input_hash = self._input_hash(request, context)

        cached = (
            self.result_repository.latest_success_by_input_hash(input_hash)
            if not request.force_refresh
            else None
        )
        if cached is not None:
            run = cached.run
            return ReasoningExecutionResult(
                run=self._read_run(run),
                result=self._read_result(cached),
                cached=True,
            )

        run = self._create_run(request, input_hash)
        self._emit(
            ReasoningRequested(
                reasoning_run_id=run.id,
                reasoning_type=request.reasoning_type.value,
                topic_id=run.topic_id,
                decision_id=run.decision_id,
                correlation_id=request.correlation_id,
                model=request.model_name,
                prompt_version=request.prompt_version,
                status=run.status,
            )
        )

        provider = self.provider or build_reasoning_provider()

        result: ReasoningResultRead | None = None
        last_provider_error: Exception | None = None
        retries = 0
        for attempt in range(settings.ai_max_retries + 1):
            try:
                provider_response = provider.generate_reasoning(context, request)
                result = self._build_result(
                    run=run,
                    request=request,
                    provider_response=provider_response,
                    input_hash=input_hash,
                )
                validation_issues = self.validator.validate(context, result)
                if validation_issues:
                    self._persist_validation_failure(
                        run,
                        request,
                        validation_issues,
                        provider_response.latency_ms,
                    )
                    self._emit(
                        ReasoningValidationFailed(
                            reasoning_run_id=run.id,
                            reasoning_type=request.reasoning_type.value,
                            topic_id=run.topic_id,
                            decision_id=run.decision_id,
                            correlation_id=request.correlation_id,
                            model=request.model_name,
                            prompt_version=request.prompt_version,
                            status=ReasoningStatus.VALIDATION_FAILED.value,
                        )
                    )
                    raise ReasoningValidationError(
                        "; ".join(issue.message for issue in validation_issues)
                    )
                self._persist_success(run, result, provider_response, retries)
                self._emit(
                    ReasoningCompleted(
                        reasoning_run_id=run.id,
                        reasoning_type=request.reasoning_type.value,
                        topic_id=run.topic_id,
                        decision_id=run.decision_id,
                        correlation_id=request.correlation_id,
                        model=request.model_name,
                        prompt_version=request.prompt_version,
                        status=ReasoningStatus.SUCCEEDED.value,
                    )
                )
                return ReasoningExecutionResult(
                    run=self._read_run(run),
                    result=result,
                    cached=False,
                )
            except ReasoningValidationError:
                raise
            except ReasoningTransientProviderError as exc:
                last_provider_error = exc
                retries = attempt
                if attempt < settings.ai_max_retries:
                    logger.info(
                        "reasoning retry scheduled",
                        extra={
                            "reasoning_run_id": run.id,
                            "reasoning_type": request.reasoning_type.value,
                            "correlation_id": request.correlation_id,
                        },
                    )
                    continue
                self._persist_failure(
                    run,
                    request,
                    str(exc),
                    retries,
                    status=ReasoningStatus.FAILED,
                )
                self._emit(
                    ReasoningFailed(
                        reasoning_run_id=run.id,
                        reasoning_type=request.reasoning_type.value,
                        topic_id=run.topic_id,
                        decision_id=run.decision_id,
                        correlation_id=request.correlation_id,
                        model=request.model_name,
                        prompt_version=request.prompt_version,
                        status=ReasoningStatus.FAILED.value,
                    )
                )
                raise
            except ValidationError as exc:
                last_provider_error = exc
                retries = attempt
                if attempt < settings.ai_max_retries:
                    logger.info(
                        "reasoning retry scheduled",
                        extra={
                            "reasoning_run_id": run.id,
                            "reasoning_type": request.reasoning_type.value,
                            "correlation_id": request.correlation_id,
                        },
                    )
                    continue
                self._persist_failure(
                    run,
                    request,
                    str(exc),
                    retries,
                    status=ReasoningStatus.FAILED,
                )
                self._emit(
                    ReasoningFailed(
                        reasoning_run_id=run.id,
                        reasoning_type=request.reasoning_type.value,
                        topic_id=run.topic_id,
                        decision_id=run.decision_id,
                        correlation_id=request.correlation_id,
                        model=request.model_name,
                        prompt_version=request.prompt_version,
                        status=ReasoningStatus.FAILED.value,
                    )
                )
                raise
        if last_provider_error is not None:
            raise last_provider_error
        raise RuntimeError("Reasoning execution failed")

    def _ensure_available(self) -> None:
        if not settings.ai_reasoning_enabled:
            raise ReasoningDisabledError("AI reasoning is disabled")
        if not (settings.ai_api_key or settings.openai_api_key):
            raise ReasoningConfigurationError("AI reasoning API key is missing")
        if not settings.ai_model:
            raise ReasoningConfigurationError("AI reasoning model is missing")

    def _build_prompt(
        self,
        reasoning_type: ReasoningType,
        context: ReasoningContext,
        request: ReasoningRequest,
    ) -> ReasoningPromptBundle:
        if reasoning_type == ReasoningType.DECISION_EXPLANATION:
            return build_decision_prompt(context, request)
        if reasoning_type == ReasoningType.OPPORTUNITY_COMPARISON:
            return build_comparison_prompt(context, request)
        if reasoning_type == ReasoningType.EXECUTION_STRATEGY:
            return build_execution_prompt(context, request)
        if reasoning_type == ReasoningType.CHANGE_SUMMARY:
            return build_change_prompt(context, request)
        raise ValueError(f"Unsupported reasoning type: {reasoning_type}")

    def _build_request(
        self,
        *,
        reasoning_type: ReasoningType,
        decision_id: str | None = None,
        topic_id: str | None = None,
        opportunity_id: str | None = None,
        topic_ids: tuple[str, ...] = (),
        opportunity_ids: tuple[str, ...] = (),
        previous_decision_id: str | None = None,
        current_decision_id: str | None = None,
        target_platform: str | None = None,
        force_refresh: bool = False,
    ) -> ReasoningRequest:
        request = ReasoningRequest(
            reasoning_type=reasoning_type,
            prompt_version=settings.ai_reasoning_prompt_version,
            context_version=settings.reasoning_context_version,
            model_provider=settings.ai_provider,
            model_name=settings.ai_model,
            messages=(),
            correlation_id=str(uuid4()),
            decision_id=decision_id,
            topic_id=topic_id,
            opportunity_id=opportunity_id,
            topic_ids=topic_ids,
            opportunity_ids=opportunity_ids,
            previous_decision_id=previous_decision_id,
            current_decision_id=current_decision_id,
            target_platform=target_platform,
            force_refresh=force_refresh,
            max_output_tokens=settings.ai_max_output_tokens,
            max_context_tokens=settings.ai_max_context_tokens,
            temperature=settings.ai_temperature,
        )
        context = self.context_builder.build(request)
        bundle = self._build_prompt(reasoning_type, context, request)
        return ReasoningRequest(
            reasoning_type=request.reasoning_type,
            prompt_version=request.prompt_version,
            context_version=request.context_version,
            model_provider=request.model_provider,
            model_name=request.model_name,
            messages=bundle.messages,
            correlation_id=request.correlation_id,
            decision_id=request.decision_id,
            topic_id=request.topic_id,
            opportunity_id=request.opportunity_id,
            topic_ids=request.topic_ids,
            opportunity_ids=request.opportunity_ids,
            previous_decision_id=request.previous_decision_id,
            current_decision_id=request.current_decision_id,
            target_platform=request.target_platform,
            force_refresh=request.force_refresh,
            max_output_tokens=request.max_output_tokens,
            max_context_tokens=request.max_context_tokens,
            temperature=request.temperature,
        )

    def _create_run(
        self, request: ReasoningRequest, input_hash: str
    ) -> ReasoningRunModel:
        run = ReasoningRunModel(
            id=str(uuid4()),
            reasoning_type=request.reasoning_type.value,
            status=ReasoningStatus.RUNNING.value,
            topic_id=request.topic_id,
            decision_id=request.decision_id,
            opportunity_id=request.opportunity_id,
            provider=request.model_provider,
            model=request.model_name,
            prompt_version=request.prompt_version,
            context_version=request.context_version,
            input_hash=input_hash,
            force_refresh=request.force_refresh,
            retry_count=0,
            latency_ms=None,
            input_tokens=None,
            output_tokens=None,
            total_tokens=None,
            estimated_cost=None,
            correlation_id=request.correlation_id,
        )
        self.run_repository.create(run)
        self.session.commit()
        return run

    def _build_result(
        self,
        *,
        run: ReasoningRunModel,
        request: ReasoningRequest,
        provider_response: object,
        input_hash: str,
    ) -> ReasoningResultRead:
        response = provider_response.raw_json
        result_id = str(uuid4())
        payload = {
            "id": result_id,
            "reasoning_run_id": run.id,
            "topic_id": run.topic_id,
            "decision_id": run.decision_id,
            "opportunity_id": run.opportunity_id,
            "reasoning_type": request.reasoning_type,
            "status": ReasoningStatus.SUCCEEDED,
            "model_provider": provider_response.provider,
            "model_name": provider_response.model,
            "prompt_version": request.prompt_version,
            "context_version": request.context_version,
            "input_hash": input_hash,
            "created_at": datetime.now(UTC),
            "completed_at": datetime.now(UTC),
            "correlation_id": request.correlation_id,
            "raw_output": response,
            **response,
        }
        result = ReasoningResultRead.model_validate(payload)
        return result

    def _persist_success(
        self,
        run: ReasoningRunModel,
        result: ReasoningResultRead,
        provider_response: object,
        retry_count: int,
    ) -> None:
        run.status = ReasoningStatus.SUCCEEDED.value
        run.retry_count = retry_count
        run.latency_ms = provider_response.latency_ms
        run.input_tokens = provider_response.input_tokens
        run.output_tokens = provider_response.output_tokens
        run.total_tokens = provider_response.total_tokens
        run.estimated_cost = provider_response.estimated_cost
        run.completed_at = result.completed_at
        self.session.flush()

        result_model = ReasoningResultModel(
            id=result.id,
            reasoning_run_id=run.id,
            reasoning_type=result.reasoning_type.value,
            status=result.status.value,
            topic_id=result.topic_id,
            decision_id=result.decision_id,
            opportunity_id=result.opportunity_id,
            executive_summary=result.executive_summary,
            why_now=result.why_now,
            why_this_topic=result.why_this_topic,
            why_this_platform=result.why_this_platform,
            what_changed=result.what_changed,
            supporting_evidence=[
                item.model_dump() for item in result.supporting_evidence
            ],
            conflicting_evidence=[
                item.model_dump() for item in result.conflicting_evidence
            ],
            caveats=list(result.caveats),
            confidence_assessment=result.confidence_assessment,
            recommended_execution=dict(result.recommended_execution),
            alternative_topics=[
                item.model_dump() for item in result.alternative_topics
            ],
            source_references=[item.model_dump() for item in result.source_references],
            model_provider=result.model_provider,
            model_name=result.model_name,
            prompt_version=result.prompt_version,
            context_version=result.context_version,
            input_hash=result.input_hash,
            completed_at=result.completed_at,
            correlation_id=result.correlation_id,
            raw_output=result.raw_output,
        )
        self.result_repository.create(result_model)
        self._persist_source_links(result_model, result)
        self.session.commit()

    def _persist_source_links(
        self, result: ReasoningResultModel, reasoning_result: ReasoningResultRead
    ) -> None:
        for evidence in reasoning_result.source_references:
            self.source_link_repository.create(
                ReasoningSourceLinkModel(
                    id=str(uuid4()),
                    reasoning_result_id=result.id,
                    link_type="source_reference",
                    evidence_id=evidence.evidence_id,
                    topic_id=reasoning_result.topic_id,
                    decision_id=reasoning_result.decision_id,
                    opportunity_id=reasoning_result.opportunity_id,
                    claim=evidence.claim,
                    source=evidence.source,
                    confidence=evidence.confidence,
                    correlation_id=reasoning_result.correlation_id,
                )
            )

    def _persist_validation_failure(
        self,
        run: ReasoningRunModel,
        request: ReasoningRequest,
        issues: list[ReasoningValidationIssue],
        latency_ms: int,
    ) -> None:
        run.status = ReasoningStatus.VALIDATION_FAILED.value
        run.latency_ms = latency_ms
        run.completed_at = datetime.now(UTC)
        self.session.flush()
        for issue in issues:
            self.validation_error_repository.create(
                ReasoningValidationErrorModel(
                    id=str(uuid4()),
                    reasoning_run_id=run.id,
                    field=issue.field,
                    message=issue.message,
                    correlation_id=request.correlation_id,
                )
            )
        self.session.commit()

    def _persist_failure(
        self,
        run: ReasoningRunModel,
        request: ReasoningRequest,
        message: str,
        retry_count: int,
        *,
        status: ReasoningStatus,
    ) -> None:
        run.status = status.value
        run.retry_count = retry_count
        run.completed_at = datetime.now(UTC)
        self.session.flush()
        self.validation_error_repository.create(
            ReasoningValidationErrorModel(
                id=str(uuid4()),
                reasoning_run_id=run.id,
                field="provider",
                message=message,
                correlation_id=request.correlation_id,
            )
        )
        self.session.commit()

    def _read_result(self, result: ReasoningResultModel) -> ReasoningResultRead:
        payload = {
            "id": result.id,
            "reasoning_run_id": result.reasoning_run_id,
            "topic_id": result.topic_id,
            "decision_id": result.decision_id,
            "opportunity_id": result.opportunity_id,
            "reasoning_type": result.reasoning_type,
            "status": result.status,
            "executive_summary": result.executive_summary,
            "why_now": result.why_now,
            "why_this_topic": result.why_this_topic,
            "why_this_platform": result.why_this_platform,
            "what_changed": result.what_changed,
            "supporting_evidence": result.supporting_evidence,
            "conflicting_evidence": result.conflicting_evidence,
            "caveats": result.caveats,
            "confidence_assessment": result.confidence_assessment,
            "recommended_execution": result.recommended_execution,
            "alternative_topics": result.alternative_topics,
            "source_references": result.source_references,
            "model_provider": result.model_provider,
            "model_name": result.model_name,
            "prompt_version": result.prompt_version,
            "context_version": result.context_version,
            "input_hash": result.input_hash,
            "created_at": result.created_at,
            "completed_at": result.completed_at,
            "correlation_id": result.correlation_id,
            "raw_output": result.raw_output,
        }
        return ReasoningResultRead.model_validate(payload)

    def _read_run(self, run: ReasoningRunModel) -> ReasoningRunRead:
        payload = {
            "id": run.id,
            "reasoning_type": run.reasoning_type,
            "status": run.status,
            "topic_id": run.topic_id,
            "decision_id": run.decision_id,
            "opportunity_id": run.opportunity_id,
            "provider": run.provider,
            "model": run.model,
            "prompt_version": run.prompt_version,
            "context_version": run.context_version,
            "input_hash": run.input_hash,
            "force_refresh": run.force_refresh,
            "retry_count": run.retry_count,
            "latency_ms": run.latency_ms,
            "input_tokens": run.input_tokens,
            "output_tokens": run.output_tokens,
            "total_tokens": run.total_tokens,
            "estimated_cost": run.estimated_cost,
            "created_at": run.created_at,
            "completed_at": run.completed_at,
            "correlation_id": run.correlation_id,
        }
        return ReasoningRunRead.model_validate(payload)

    def _input_hash(self, request: ReasoningRequest, context: ReasoningContext) -> str:
        payload = {
            "reasoning_type": request.reasoning_type.value,
            "topic_id": request.topic_id,
            "decision_id": request.decision_id,
            "opportunity_id": request.opportunity_id,
            "topic_ids": list(request.topic_ids),
            "opportunity_ids": list(request.opportunity_ids),
            "previous_decision_id": request.previous_decision_id,
            "current_decision_id": request.current_decision_id,
            "target_platform": request.target_platform,
            "context_version": request.context_version,
            "prompt_version": request.prompt_version,
            "model_provider": request.model_provider,
            "model_name": request.model_name,
            "context": self._json_safe(asdict(context)),
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()

    @staticmethod
    def _json_safe(value: object) -> object:
        if isinstance(value, dict):
            return {
                str(key): ReasoningService._json_safe(item)
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple)):
            return [ReasoningService._json_safe(item) for item in value]
        if isinstance(value, datetime):
            return value.isoformat()
        if hasattr(value, "value"):
            return value.value
        return value

    def _emit(self, event: object) -> None:
        if self.event_emitter is not None:
            self.event_emitter.emit(event)
