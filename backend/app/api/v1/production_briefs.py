"""Executive Producer workflow endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.dependencies.database import get_db
from backend.app.models.production_brief import ProjectProductionBriefModel
from backend.app.models.project import ProjectModel
from backend.app.models.research import ProjectResearchDossierModel
from backend.app.models.script import ProjectScriptModel
from backend.app.research.expansion_service import next_version
from backend.app.schemas.production_brief import (
    ProductionBriefRead,
    ProductionBriefStartRead,
    ProductionBriefStatusRead,
)
from backend.app.workers.tasks import run_executive_producer

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/production-brief", tags=["production-brief"]
)


def _project(project_id: str, db: Session) -> ProjectModel:
    project = db.get(ProjectModel, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _brief(project_id: str, db: Session) -> ProjectProductionBriefModel:
    brief = (
        db.query(ProjectProductionBriefModel)
        .filter_by(project_id=project_id)
        .one_or_none()
    )
    if brief is None:
        raise HTTPException(
            status_code=404, detail="Production brief has not been started"
        )
    return brief


@router.post("/start", response_model=ProductionBriefStartRead)
def start(project_id: str, db: Session = Depends(get_db)) -> ProductionBriefStartRead:
    project = _project(project_id, db)
    dossier = (
        db.query(ProjectResearchDossierModel)
        .filter_by(project_id=project_id)
        .one_or_none()
    )
    if (
        project.status != "RESEARCH_COMPLETE"
        or dossier is None
        or dossier.research_status != "APPROVED"
    ):
        raise HTTPException(
            status_code=409,
            detail="Approved research is required before producing a brief",
        )
    if db.query(ProjectProductionBriefModel).filter_by(project_id=project_id).count():
        raise HTTPException(status_code=409, detail="Production brief already exists")
    project.status = "PRODUCING_BRIEF"
    db.add(
        ProjectProductionBriefModel(
            project_id=project_id,
            status="PENDING",
            version=settings.production_brief_version,
            current_step="INITIALIZING",
            candidate_angles_generated=0,
            payload={},
            research_version_used=dossier.research_version,
        )
    )
    db.commit()
    task = run_executive_producer.delay(project_id)
    return ProductionBriefStartRead(
        project_id=project_id, task_id=task.id, status="PENDING"
    )


@router.get("/status", response_model=ProductionBriefStatusRead)
def get_status(
    project_id: str, db: Session = Depends(get_db)
) -> ProductionBriefStatusRead:
    project = _project(project_id, db)
    brief = _brief(project_id, db)
    return ProductionBriefStatusRead(
        project_id=project_id,
        project_status=project.status,
        brief_status=brief.status,
        current_step=brief.current_step,
        candidate_angles_generated=brief.candidate_angles_generated,
        selected_angle=brief.selected_angle,
        recommendation=brief.recommendation,
        revised_money_score=brief.revised_money_score,
        safe_error_message=brief.safe_error_message,
        started_at=brief.started_at,
        completed_at=brief.completed_at,
    )


@router.get("", response_model=ProductionBriefRead)
def get_brief(project_id: str, db: Session = Depends(get_db)) -> ProductionBriefRead:
    brief = _brief(project_id, db)
    if brief.status not in {
        "COMPLETE",
        "NEEDS_REVIEW",
        "APPROVED",
        "REJECTED",
        "STALE",
    }:
        raise HTTPException(status_code=409, detail="Production brief is not complete")
    return ProductionBriefRead(
        project_id=project_id,
        status=brief.status,
        version=brief.version,
        generated_at=brief.generated_at,
        approved_at=brief.approved_at,
        brief=brief.payload,
    )


@router.post("/approve", response_model=ProductionBriefRead)
def approve(project_id: str, db: Session = Depends(get_db)) -> ProductionBriefRead:
    project = _project(project_id, db)
    brief = _brief(project_id, db)
    dossier = (
        db.query(ProjectResearchDossierModel)
        .filter_by(project_id=project_id)
        .one_or_none()
    )
    if (
        brief.status not in {"COMPLETE", "NEEDS_REVIEW"}
        or dossier is None
        or brief.research_version_used != dossier.research_version
    ):
        raise HTTPException(
            status_code=409, detail="Production brief is not ready for approval"
        )
    brief.status = "APPROVED"
    brief.approved_at = datetime.now(UTC)
    project.status = "BRIEF_APPROVED"
    db.commit()
    return ProductionBriefRead(
        project_id=project_id,
        status=brief.status,
        version=brief.version,
        generated_at=brief.generated_at,
        approved_at=brief.approved_at,
        brief=brief.payload,
    )


@router.post("/regenerate", response_model=ProductionBriefStartRead)
def regenerate(
    project_id: str, db: Session = Depends(get_db)
) -> ProductionBriefStartRead:
    project = _project(project_id, db)
    brief = _brief(project_id, db)
    dossier = (
        db.query(ProjectResearchDossierModel)
        .filter_by(project_id=project_id)
        .one_or_none()
    )
    script = db.query(ProjectScriptModel).filter_by(project_id=project_id).one_or_none()
    if dossier is None or dossier.research_status != "APPROVED":
        raise HTTPException(409, "Approved expanded research is required")
    if script is not None and script.status in {"PENDING", "GENERATING"}:
        raise HTTPException(409, "Script generation is currently running")
    brief.version = next_version(brief.version, "brief")
    brief.status = "PENDING"
    brief.current_step = "INITIALIZING"
    brief.payload = {}
    brief.approved_at = None
    brief.research_version_used = dossier.research_version
    if script is not None:
        script.status = "STALE"
        script.approved_at = None
    project.status = "PRODUCING_BRIEF"
    db.commit()
    task = run_executive_producer.delay(project_id)
    return ProductionBriefStartRead(
        project_id=project_id, task_id=task.id, status="PENDING"
    )


@router.post("/retry", response_model=ProductionBriefStartRead)
def retry(project_id: str, db: Session = Depends(get_db)) -> ProductionBriefStartRead:
    project = _project(project_id, db)
    brief = _brief(project_id, db)
    if brief.status != "FAILED":
        raise HTTPException(
            status_code=409, detail="Only failed production briefs can be retried"
        )
    project.status = "PRODUCING_BRIEF"
    brief.status = "PENDING"
    brief.current_step = "INITIALIZING"
    brief.safe_error_message = None
    db.commit()
    task = run_executive_producer.delay(project_id)
    return ProductionBriefStartRead(
        project_id=project_id, task_id=task.id, status="PENDING"
    )


@router.post("/reject", response_model=ProductionBriefRead)
def reject(project_id: str, db: Session = Depends(get_db)) -> ProductionBriefRead:
    project = _project(project_id, db)
    brief = _brief(project_id, db)
    if brief.status not in {"COMPLETE", "NEEDS_REVIEW"}:
        raise HTTPException(
            status_code=409, detail="Production brief cannot be rejected now"
        )
    brief.status = "REJECTED"
    brief.recommendation = "REJECT"
    brief.payload = {
        **brief.payload,
        "recommendation": "REJECT",
        "rejection_reasons": [
            *brief.payload.get("rejection_reasons", []),
            "Project rejected during Executive Producer review.",
        ],
    }
    project.status = "PROJECT_REJECTED"
    db.commit()
    return ProductionBriefRead(
        project_id=project_id,
        status=brief.status,
        version=brief.version,
        generated_at=brief.generated_at,
        approved_at=brief.approved_at,
        brief=brief.payload,
    )
