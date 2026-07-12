"""Metric API schemas."""

from backend.app.schemas.base import Schema


class MetricRead(Schema):
    id: int
    video_id: int
    name: str
    value: float
