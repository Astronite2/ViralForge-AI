"""Connector orchestration report models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class ConnectorExecutionReport:
    """Execution summary for one connector."""

    connector_name: str
    status: str
    items_fetched: int
    items_processed: int
    items_failed: int
    decisions_created: int
    duration_ms: int
    errors: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class ConnectorOrchestrationReport:
    """Execution summary for one orchestration run."""

    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    duration_ms: int = 0
    connector_reports: tuple[ConnectorExecutionReport, ...] = field(
        default_factory=tuple
    )
