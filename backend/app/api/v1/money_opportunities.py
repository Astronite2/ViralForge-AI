"""YouTube money-opportunity workflow endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.dependencies.database import get_db
from backend.app.schemas.money_opportunity import (
    MoneyAnalysisRead,
    MoneyAnalysisRequest,
    OutcomeCreate,
    OutcomeRead,
    OutcomeUpdate,
    ProductionBriefRead,
)
from backend.app.services.money_workflow import (
    MoneyWorkflowNotFound,
    MoneyWorkflowService,
    MoneyWorkflowUnavailable,
)

router = APIRouter(
    prefix="/api/v1/money-opportunities", tags=["money-opportunities-v1"]
)


def _service(db: Session) -> MoneyWorkflowService:
    return MoneyWorkflowService(db)


@router.post(
    "/analyze", response_model=MoneyAnalysisRead, status_code=status.HTTP_201_CREATED
)
def analyze_money_opportunities(
    request: MoneyAnalysisRequest, db: Session = Depends(get_db)
) -> MoneyAnalysisRead:
    try:
        return _service(db).analyze(request)
    except MoneyWorkflowUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/{analysis_id}", response_model=MoneyAnalysisRead)
def get_money_analysis(
    analysis_id: str, db: Session = Depends(get_db)
) -> MoneyAnalysisRead:
    try:
        return _service(db).get_analysis(analysis_id)
    except MoneyWorkflowNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{opportunity_id}/brief", response_model=ProductionBriefRead)
def generate_production_brief(
    opportunity_id: str, db: Session = Depends(get_db)
) -> ProductionBriefRead:
    try:
        return _service(db).generate_brief(opportunity_id)
    except MoneyWorkflowNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{opportunity_id}/outcome", response_model=OutcomeRead, status_code=201)
def create_outcome(
    opportunity_id: str,
    request: OutcomeCreate,
    db: Session = Depends(get_db),
) -> OutcomeRead:
    try:
        return _service(db).create_outcome(opportunity_id, request)
    except MoneyWorkflowNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/outcomes/{outcome_id}", response_model=OutcomeRead)
def update_outcome(
    outcome_id: str,
    request: OutcomeUpdate,
    db: Session = Depends(get_db),
) -> OutcomeRead:
    try:
        return _service(db).update_outcome(outcome_id, request)
    except MoneyWorkflowNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
