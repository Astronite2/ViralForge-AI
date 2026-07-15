"""Executive Producer API contracts."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ProductionBriefStartRead(BaseModel):
    project_id: str
    task_id: str
    status: str


class ProductionBriefStatusRead(BaseModel):
    project_id: str
    project_status: str
    brief_status: str
    current_step: str
    candidate_angles_generated: int
    selected_angle: str | None
    recommendation: str | None
    revised_money_score: float | None
    safe_error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None


class ProductionBriefRead(BaseModel):
    project_id: str
    status: str
    version: str
    generated_at: datetime | None
    approved_at: datetime | None
    brief: dict[str, Any]
