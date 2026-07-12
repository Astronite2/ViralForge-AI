"""Analysis API schemas."""

from backend.app.schemas.base import Schema


class AnalysisRead(Schema):
    id: int
    video_id: int
    status: str
