"""Normalized content read endpoints."""

from fastapi import APIRouter

from backend.app.schemas.content import ContentRead
from backend.app.services.video import ContentService

router = APIRouter(prefix="/content", tags=["content"])
service = ContentService()


@router.get("", response_model=list[ContentRead])
def list_content() -> list[ContentRead]:
    """Return normalized content placeholders."""
    return service.list_content()


@router.get("/{content_id}", response_model=ContentRead)
def get_content(content_id: str) -> ContentRead:
    """Return a normalized content placeholder."""
    return service.get_content(content_id)
