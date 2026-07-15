"""Project Script API contracts."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ScriptStartRead(BaseModel):
    project_id: str
    task_id: str
    status: str


class ScriptStatusRead(BaseModel):
    project_id: str
    project_status: str
    script_status: str
    current_step: str
    evidence_sufficiency: str | None
    available_facts: int
    required_facts: int
    available_sources: int
    required_sources: int
    actual_word_count: int
    target_word_count: int
    estimated_duration_minutes: float | None
    safe_error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None


class ScriptRead(BaseModel):
    project_id: str
    status: str
    version: str
    generated_at: datetime | None
    approved_at: datetime | None
    script: dict[str, Any]
