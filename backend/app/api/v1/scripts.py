"""Source-grounded Script Writer endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.dependencies.database import get_db
from backend.app.models.production_brief import ProjectProductionBriefModel
from backend.app.models.project import ProjectModel
from backend.app.models.research import ProjectResearchDossierModel
from backend.app.models.script import ProjectScriptModel
from backend.app.schemas.script import ScriptRead, ScriptStartRead, ScriptStatusRead
from backend.app.workers.tasks import run_project_script

router = APIRouter(prefix="/api/v1/projects/{project_id}/script", tags=["script"])


def _project(project_id: str, db: Session) -> ProjectModel:
    item = db.get(ProjectModel, project_id)
    if item is None:
        raise HTTPException(404, "Project not found")
    return item


def _script(project_id: str, db: Session) -> ProjectScriptModel:
    item = db.query(ProjectScriptModel).filter_by(project_id=project_id).one_or_none()
    if item is None:
        raise HTTPException(404, "Script has not been started")
    return item


def _enqueue(
    project: ProjectModel, script: ProjectScriptModel, db: Session
) -> ScriptStartRead:
    project.status = "SCRIPTING"
    script.status = "PENDING"
    script.current_step = "INITIALIZING"
    script.safe_error_message = None
    db.commit()
    task = run_project_script.delay(project.id)
    return ScriptStartRead(project_id=project.id, task_id=task.id, status="PENDING")


@router.post("/start", response_model=ScriptStartRead)
def start(project_id: str, db: Session = Depends(get_db)) -> ScriptStartRead:
    project = _project(project_id, db)
    brief = (
        db.query(ProjectProductionBriefModel)
        .filter_by(project_id=project_id)
        .one_or_none()
    )
    dossier = (
        db.query(ProjectResearchDossierModel)
        .filter_by(project_id=project_id)
        .one_or_none()
    )
    if (
        project.status != "BRIEF_APPROVED"
        or brief is None
        or brief.status != "APPROVED"
        or (
            brief.research_version_used is not None
            and brief.research_version_used != dossier.research_version
        )
        or dossier is None
        or dossier.research_status != "APPROVED"
    ):
        raise HTTPException(409, "Approved research and Production Brief are required")
    if db.query(ProjectScriptModel).filter_by(project_id=project_id).count():
        raise HTTPException(409, "Script already exists")
    script = ProjectScriptModel(
        project_id=project_id,
        status="PENDING",
        version=settings.script_version,
        current_step="INITIALIZING",
        target_word_count=0,
        actual_word_count=0,
        payload={},
    )
    db.add(script)
    return _enqueue(project, script, db)


@router.get("/status", response_model=ScriptStatusRead)
def status(project_id: str, db: Session = Depends(get_db)) -> ScriptStatusRead:
    project = _project(project_id, db)
    script = _script(project_id, db)
    coverage = script.payload.get("evidence_coverage", {})
    return ScriptStatusRead(
        project_id=project.id,
        project_status=project.status,
        script_status=script.status,
        current_step=script.current_step,
        evidence_sufficiency=script.evidence_sufficiency,
        available_facts=coverage.get("available_facts", 0),
        required_facts=coverage.get("required_facts", 0),
        available_sources=coverage.get("available_sources", 0),
        required_sources=coverage.get("required_sources", 0),
        actual_word_count=script.actual_word_count,
        target_word_count=script.target_word_count,
        estimated_duration_minutes=script.estimated_duration_minutes,
        safe_error_message=script.safe_error_message,
        started_at=script.started_at,
        completed_at=script.completed_at,
    )


@router.get("", response_model=ScriptRead)
def get_script(project_id: str, db: Session = Depends(get_db)) -> ScriptRead:
    script = _script(project_id, db)
    if script.status not in {
        "COMPLETE",
        "NEEDS_REVIEW",
        "APPROVED",
        "REJECTED",
        "STALE",
    }:
        raise HTTPException(409, "Script is not ready")
    return ScriptRead(
        project_id=project_id,
        status=script.status,
        version=script.version,
        generated_at=script.generated_at,
        approved_at=script.approved_at,
        script=script.payload,
    )


@router.post("/approve", response_model=ScriptRead)
def approve(project_id: str, db: Session = Depends(get_db)) -> ScriptRead:
    project = _project(project_id, db)
    script = _script(project_id, db)
    if script.status != "COMPLETE":
        raise HTTPException(409, "Only a complete grounded script can be approved")
    dossier = (
        db.query(ProjectResearchDossierModel)
        .filter_by(project_id=project_id)
        .one_or_none()
    )
    brief = (
        db.query(ProjectProductionBriefModel)
        .filter_by(project_id=project_id)
        .one_or_none()
    )
    if (
        dossier is None
        or brief is None
        or script.research_version_used != dossier.research_version
        or script.production_brief_version_used != brief.version
    ):
        raise HTTPException(409, "Script is stale and must be regenerated")
    script.status = "APPROVED"
    script.approved_at = datetime.now(UTC)
    project.status = "SCRIPT_APPROVED"
    db.commit()
    return ScriptRead(
        project_id=project_id,
        status=script.status,
        version=script.version,
        generated_at=script.generated_at,
        approved_at=script.approved_at,
        script=script.payload,
    )


@router.post("/retry", response_model=ScriptStartRead)
def retry(project_id: str, db: Session = Depends(get_db)) -> ScriptStartRead:
    project = _project(project_id, db)
    script = _script(project_id, db)
    if script.status not in {"FAILED", "NEEDS_REVIEW"}:
        raise HTTPException(
            409, "Only failed or evidence-limited scripts can be retried"
        )
    return _enqueue(project, script, db)


@router.post("/regenerate", response_model=ScriptStartRead)
def regenerate(project_id: str, db: Session = Depends(get_db)) -> ScriptStartRead:
    project = _project(project_id, db)
    script = _script(project_id, db)
    if project.status not in {
        "SCRIPT_COMPLETE",
        "BRIEF_APPROVED",
    } or script.status not in {"COMPLETE", "NEEDS_REVIEW", "REJECTED", "STALE"}:
        raise HTTPException(409, "Script cannot be regenerated now")
    number = int(script.version.rsplit("-v", 1)[-1]) if "-v" in script.version else 1
    script.version = f"script-v{number+1}"
    script.payload = {}
    script.actual_word_count = 0
    return _enqueue(project, script, db)


@router.post("/reject", response_model=ScriptRead)
def reject(project_id: str, db: Session = Depends(get_db)) -> ScriptRead:
    project = _project(project_id, db)
    script = _script(project_id, db)
    if script.status not in {"COMPLETE", "NEEDS_REVIEW"}:
        raise HTTPException(409, "Script cannot be rejected now")
    script.status = "REJECTED"
    project.status = "BRIEF_APPROVED"
    db.commit()
    return ScriptRead(
        project_id=project_id,
        status=script.status,
        version=script.version,
        generated_at=script.generated_at,
        approved_at=script.approved_at,
        script=script.payload,
    )
