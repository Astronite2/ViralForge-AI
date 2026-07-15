"""Research dossier API schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


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


class ResearchExpansionRequest(BaseModel):
    target_duration_minutes: int = Field(default=15, ge=1, le=20)
    focus_areas: list[str] = Field(default_factory=list, max_length=13)
    max_additional_sources: int = Field(default=25, ge=1, le=50)


class ResearchGapsRead(BaseModel):
    evidence_sufficiency: str
    missing_facts: int
    missing_sources: int
    missing_authoritative_sources: int
    unsupported_beats: list[str]
    proposed_focus_areas: list[str]
    proposed_search_queries: list[str]
    recommended_max_duration_minutes: int
    recommended_action: str
