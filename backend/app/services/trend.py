"""Trend signal query service."""

from backend.app.schemas.trend_signal import TrendSignalRead


class TrendService:
    """Application service for placeholder signal read operations."""

    def list_signals(self) -> list[TrendSignalRead]:
        """Return placeholder signals until query persistence is enabled."""
        return []
