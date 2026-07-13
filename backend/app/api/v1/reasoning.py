"""AI reasoning API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.app.dependencies.database import get_db
from backend.app.reasoning.errors import (
    ReasoningConfigurationError,
    ReasoningDisabledError,
)
from backend.app.schemas.reasoning import (
    ChangeSummaryReasoningRequest,
    DecisionExplanationReasoningRequest,
    ExecutionStrategyReasoningRequest,
    OpportunityComparisonReasoningRequest,
    ReasoningDisabledRead,
    ReasoningResultRead,
)
from backend.app.services.reasoning import ReasoningService

router = APIRouter(prefix="/api/v1/reasoning", tags=["reasoning"])


def _service(db: Session) -> ReasoningService:
    return ReasoningService(db)


def _disabled_response(detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content=ReasoningDisabledRead(
            status="disabled",
            provider=None,
            model=None,
            detail=detail,
        ).model_dump(),
    )


@router.post("/decision-explanation", response_model=ReasoningResultRead)
def explain_decision(
    payload: DecisionExplanationReasoningRequest, db: Session = Depends(get_db)
) -> ReasoningResultRead | JSONResponse:
    service = _service(db)
    try:
        execution = service.explain_decision(
            payload.decision_id, force_refresh=payload.force_refresh
        )
        assert execution.result is not None
        return execution.result
    except (ReasoningDisabledError, ReasoningConfigurationError) as exc:
        return _disabled_response(str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/opportunity-comparison", response_model=ReasoningResultRead)
def compare_opportunities(
    payload: OpportunityComparisonReasoningRequest, db: Session = Depends(get_db)
) -> ReasoningResultRead | JSONResponse:
    service = _service(db)
    try:
        execution = service.compare_opportunities(
            topic_ids=payload.topic_ids,
            opportunity_ids=payload.opportunity_ids,
            force_refresh=payload.force_refresh,
        )
        assert execution.result is not None
        return execution.result
    except (ReasoningDisabledError, ReasoningConfigurationError) as exc:
        return _disabled_response(str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/execution-strategy", response_model=ReasoningResultRead)
def execution_strategy(
    payload: ExecutionStrategyReasoningRequest, db: Session = Depends(get_db)
) -> ReasoningResultRead | JSONResponse:
    service = _service(db)
    try:
        execution = service.execution_strategy(
            payload.decision_id,
            target_platform=payload.target_platform,
            force_refresh=payload.force_refresh,
        )
        assert execution.result is not None
        return execution.result
    except (ReasoningDisabledError, ReasoningConfigurationError) as exc:
        return _disabled_response(str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/change-summary", response_model=ReasoningResultRead)
def change_summary(
    payload: ChangeSummaryReasoningRequest, db: Session = Depends(get_db)
) -> ReasoningResultRead | JSONResponse:
    service = _service(db)
    try:
        execution = service.change_summary(
            payload.topic_id,
            previous_decision_id=payload.previous_decision_id,
            current_decision_id=payload.current_decision_id,
            force_refresh=payload.force_refresh,
        )
        assert execution.result is not None
        return execution.result
    except (ReasoningDisabledError, ReasoningConfigurationError) as exc:
        return _disabled_response(str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{reasoning_result_id}", response_model=ReasoningResultRead)
def get_reasoning_result(
    reasoning_result_id: str, db: Session = Depends(get_db)
) -> ReasoningResultRead:
    result = _service(db).get_result(reasoning_result_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Reasoning result not found")
    return result


@router.get("/by-decision/{decision_id}", response_model=list[ReasoningResultRead])
def list_by_decision(
    decision_id: str, db: Session = Depends(get_db)
) -> list[ReasoningResultRead]:
    service = _service(db)
    if service.decision_repository.get_by_id(decision_id) is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    return service.list_by_decision(decision_id)


@router.get("/by-topic/{topic_id}", response_model=list[ReasoningResultRead])
def list_by_topic(
    topic_id: str, db: Session = Depends(get_db)
) -> list[ReasoningResultRead]:
    service = _service(db)
    if service.topic_repository.get_by_id(topic_id) is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    return service.list_by_topic(topic_id)
