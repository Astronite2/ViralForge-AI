"""Read and advance production projects."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.dependencies.database import get_db
from backend.app.models.project import ProjectModel
from backend.app.schemas.project import ProjectCreate, ProjectRead, ProjectStatus

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


@router.post("/{project_id}/research/start", response_model=ProjectRead)
def start_research(project_id: str, db: Session = Depends(get_db)) -> ProjectModel:
    project = db.get(ProjectModel, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.status != ProjectStatus.CREATED.value:
        raise HTTPException(
            status_code=409,
            detail=f"Research cannot start from status {project.status}",
        )
    project.status = ProjectStatus.RESEARCHING.value
    db.commit()
    db.refresh(project)
    return project
