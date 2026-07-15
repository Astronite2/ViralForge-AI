"""Read and advance production projects."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.dependencies.database import get_db
from backend.app.models.production_brief import ProjectProductionBriefModel
from backend.app.models.project import ProjectModel
from backend.app.models.research import ProjectResearchDossierModel
from backend.app.research.gap_analyzer import ResearchGapAnalyzer
from backend.app.schemas.project import ProjectCreate, ProjectRead, ProjectStatus
from backend.app.schemas.research import (
    ResearchDossierRead,
    ResearchExpansionRequest,
    ResearchGapsRead,
    ResearchStartRead,
    ResearchStatusRead,
)
from backend.app.workers.tasks import expand_project_research, run_project_research

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate, db: Session = Depends(get_db)
) -> ProjectModel:
    project = ProjectModel(**payload.model_dump(), status=ProjectStatus.CREATED.value)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: str, db: Session = Depends(get_db)) -> ProjectModel:
    project = db.get(ProjectModel, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/{project_id}/research/start", response_model=ResearchStartRead)
def start_research(project_id: str, db: Session = Depends(get_db)) -> ResearchStartRead:
    project = db.get(ProjectModel, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.status != ProjectStatus.CREATED.value:
        raise HTTPException(
            status_code=409,
            detail=f"Research cannot start from status {project.status}",
        )
    project.status = ProjectStatus.RESEARCHING.value
    dossier = ProjectResearchDossierModel(
        project_id=project.id,
        research_status="PENDING",
        research_version=settings.research_version,
        progress=5,
        current_step="INITIALIZING",
        sources_found=0,
        facts_verified=0,
        payload={},
    )
    db.add(dossier)
    db.commit()
    task = run_project_research.delay(project.id)
    return ResearchStartRead(project_id=project.id, task_id=task.id, status="PENDING")


def _research(
    project_id: str, db: Session
) -> tuple[ProjectModel, ProjectResearchDossierModel]:
    project = db.get(ProjectModel, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    dossier = (
        db.query(ProjectResearchDossierModel)
        .filter_by(project_id=project_id)
        .one_or_none()
    )
    if dossier is None:
        raise HTTPException(status_code=404, detail="Research has not been started")
    return project, dossier


@router.get("/{project_id}/research/status", response_model=ResearchStatusRead)
def research_status(
    project_id: str, db: Session = Depends(get_db)
) -> ResearchStatusRead:
    project, dossier = _research(project_id, db)
    return ResearchStatusRead(
        project_id=project.id,
        project_status=project.status,
        research_status=dossier.research_status,
        progress=dossier.progress,
        current_step=dossier.current_step,
        sources_found=dossier.sources_found,
        facts_verified=dossier.facts_verified,
        error_message=dossier.error_message,
        started_at=dossier.started_at,
        completed_at=dossier.completed_at,
    )


@router.get("/{project_id}/research", response_model=ResearchDossierRead)
def get_research(project_id: str, db: Session = Depends(get_db)) -> ResearchDossierRead:
    _, dossier = _research(project_id, db)
    if dossier.research_status not in {"COMPLETE", "NEEDS_REVIEW", "APPROVED"}:
        raise HTTPException(status_code=409, detail="Research dossier is not complete")
    return ResearchDossierRead(
        project_id=project_id,
        research_status=dossier.research_status,
        research_version=dossier.research_version,
        generated_at=dossier.generated_at,
        dossier=dossier.payload,
    )


@router.post("/{project_id}/research/retry", response_model=ResearchStartRead)
def retry_research(project_id: str, db: Session = Depends(get_db)) -> ResearchStartRead:
    project, dossier = _research(project_id, db)
    if dossier.research_status != "FAILED":
        raise HTTPException(
            status_code=409, detail="Only failed research can be retried"
        )
    project.status = ProjectStatus.RESEARCHING.value
    dossier.research_status = "PENDING"
    dossier.current_step = "INITIALIZING"
    dossier.progress = 5
    dossier.error_message = None
    db.commit()
    task = run_project_research.delay(project.id)
    return ResearchStartRead(project_id=project.id, task_id=task.id, status="PENDING")


@router.post("/{project_id}/research/approve", response_model=ResearchDossierRead)
def approve_research(
    project_id: str, db: Session = Depends(get_db)
) -> ResearchDossierRead:
    _, dossier = _research(project_id, db)
    if dossier.research_status not in {"COMPLETE", "NEEDS_REVIEW"}:
        raise HTTPException(
            status_code=409, detail="Research is not ready for approval"
        )
    dossier.research_status = "APPROVED"
    dossier.payload = {**dossier.payload, "research_status": "APPROVED"}
    db.commit()
    return ResearchDossierRead(
        project_id=project_id,
        research_status=dossier.research_status,
        research_version=dossier.research_version,
        generated_at=dossier.generated_at,
        dossier=dossier.payload,
    )


@router.get("/{project_id}/research/gaps", response_model=ResearchGapsRead)
def research_gaps(project_id: str, db: Session = Depends(get_db)) -> ResearchGapsRead:
    project, dossier = _research(project_id, db)
    brief = (
        db.query(ProjectProductionBriefModel)
        .filter_by(project_id=project_id)
        .one_or_none()
    )
    if brief is None:
        raise HTTPException(
            status_code=409, detail="Production Brief is required for gap analysis"
        )
    duration = int(
        "".join(character for character in project.target_length if character.isdigit())
        or 15
    )
    result = ResearchGapAnalyzer().analyze(
        topic=project.title,
        dossier=dossier.payload,
        brief=brief.payload,
        target_duration=duration,
    )
    return ResearchGapsRead(
        **{key: value for key, value in result.items() if key != "coverage"}
    )


@router.post("/{project_id}/research/expand", response_model=ResearchStartRead)
def expand_research(
    project_id: str, payload: ResearchExpansionRequest, db: Session = Depends(get_db)
) -> ResearchStartRead:
    project, dossier = _research(project_id, db)
    if dossier.research_status != "APPROVED":
        raise HTTPException(
            status_code=409, detail="Approved research is required for expansion"
        )
    brief = (
        db.query(ProjectProductionBriefModel)
        .filter_by(project_id=project_id)
        .one_or_none()
    )
    if brief is None:
        raise HTTPException(
            status_code=409, detail="Production Brief is required for gap analysis"
        )
    dossier.research_status = "RUNNING"
    dossier.current_step = "ANALYZING_GAPS"
    dossier.progress = 10
    dossier.completed_at = None
    db.commit()
    task = expand_project_research.delay(
        project_id,
        payload.focus_areas,
        payload.target_duration_minutes,
        payload.max_additional_sources,
    )
    return ResearchStartRead(project_id=project_id, task_id=task.id, status="RUNNING")
