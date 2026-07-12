"""Shared Pydantic schema configuration."""

from pydantic import BaseModel, ConfigDict


class Schema(BaseModel):
    """Base schema supporting ORM serialization."""

    model_config = ConfigDict(from_attributes=True)
