"""Project workspace API contracts."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjectStatus(StrEnum):
    CREATED = "CREATED"
    RESEARCHING = "RESEARCHING"
    RESEARCH_COMPLETE = "RESEARCH_COMPLETE"
    SCRIPTING = "SCRIPTING"
    SCRIPT_COMPLETE = "SCRIPT_COMPLETE"
    STORYBOARDING = "STORYBOARDING"
    ASSET_GENERATION = "ASSET_GENERATION"
    VOICE_GENERATION = "VOICE_GENERATION"
    VIDEO_RENDERING = "VIDEO_RENDERING"
    SEO = "SEO"
    READY = "READY"
    PUBLISHED = "PUBLISHED"


class ProjectCreate(BaseModel):
    title: str = Field(min_length=2, max_length=300)
    country: str = Field(min_length=2, max_length=100)
    language: str = Field(min_length=2, max_length=100)
    category: str = Field(min_length=2, max_length=100)
    target_length: str = Field(min_length=1, max_length=50)

    @field_validator("title", "country", "language", "category", "target_length")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    country: str
    language: str
    category: str
    target_length: str
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
