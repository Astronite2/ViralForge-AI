"""Research dossier API schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ResearchStartRead(BaseModel):
    project_id: str
    task_id: str
    status: str


class ResearchStatusRead(BaseModel):
    project_id: str
    project_status: str
    research_status: str
    progress: int
    current_step: str
    sources_found: int
    facts_verified: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None


class ResearchDossierRead(BaseModel):
    project_id: str
    research_status: str
    research_version: str
    generated_at: datetime | None
    dossier: dict[str, Any]
