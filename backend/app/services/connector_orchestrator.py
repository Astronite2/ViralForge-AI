"""Connector orchestration service."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable, Iterable, Mapping
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid4, uuid5

from sqlalchemy.orm import Session

from backend.app.connectors.base import BaseConnector
from backend.app.connectors.registry import (
    ConnectorRegistry,
    build_default_connector_registry,
)
from backend.app.db.session import SessionLocal
from backend.app.domain.connector_orchestration import (
    ConnectorExecutionReport,
    ConnectorOrchestrationReport,
)
from backend.app.domain.trend_signal import TrendSignal
from backend.app.services.signal_decision import SignalDecisionService
from backend.app.utils.events import SignalDetected

logger = logging.getLogger(__name__)


class ConnectorOrchestrator:
    """Execute enabled connectors and route normalized signals to the decision flow."""

    def __init__(
        self,
        registry: ConnectorRegistry | None = None,
        *,
        session_factory: Callable[[], Session] | None = None,
    ) -> None:
        self.registry = registry or build_default_connector_registry()
        self.session_factory = session_factory or SessionLocal

    def run(
        self,
        connector_kwargs: Mapping[str, Mapping[str, object]] | None = None,
        *,
        enabled_connectors: Iterable[str] | None = None,
    ) -> ConnectorOrchestrationReport:
        """Execute the selected connectors and return a structured report."""
        started_at = datetime.now(UTC)
        orchestration_started = time.perf_counter()
        kwargs_by_connector = connector_kwargs or {}
        connector_names = tuple(enabled_connectors or self.registry.names())
        connector_reports = []

        for connector_name in connector_names:
            connector = self.registry.get(connector_name)
            connector_report = self._run_connector(
                connector_name,
                connector,
                dict(kwargs_by_connector.get(connector_name, {})),
            )
            connector_reports.append(connector_report)

        completed_at = datetime.now(UTC)
        duration_ms = int((time.perf_counter() - orchestration_started) * 1000)
        return ConnectorOrchestrationReport(
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            connector_reports=tuple(connector_reports),
        )

    def _run_connector(
        self,
        connector_name: str,
        connector: BaseConnector[TrendSignal],
        kwargs: Mapping[str, object],
    ) -> ConnectorExecutionReport:
        started_at = time.perf_counter()
        connector_correlation_id = str(uuid4())
        logger.info(
            "connector execution started",
            extra={
                "connector": connector_name,
                "correlation_id": connector_correlation_id,
            },
        )
        try:
            raw_items = connector.fetch(**kwargs)
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started_at) * 1000)
            logger.exception(
                "connector fetch failed",
                extra={
                    "connector": connector_name,
                    "correlation_id": connector_correlation_id,
                },
            )
            return ConnectorExecutionReport(
                connector_name=connector_name,
                status="failed",
                items_fetched=0,
                items_processed=0,
                items_failed=0,
                decisions_created=0,
                duration_ms=duration_ms,
                errors=(str(exc),),
            )

        items_processed = 0
        items_failed = 0
        decisions_created = 0
        errors: list[str] = []

        for raw_item in raw_items:
            try:
                connector.validate(raw_item)
                normalized = connector.normalize(raw_item)
                if not isinstance(normalized, TrendSignal):
                    raise TypeError("Connector normalization must return TrendSignal")
                event = SignalDetected(
                    signal=normalized,
                    event_id=self._event_id(connector_name, raw_item),
                    correlation_id=connector_correlation_id,
                )
                with self.session_factory() as session:
                    result = SignalDecisionService(session).process(event)
                items_processed += 1
                if not result.duplicate:
                    decisions_created += 1
                logger.info(
                    "signal decision processed",
                    extra={
                        "connector": connector_name,
                        "correlation_id": connector_correlation_id,
                        "event_id": event.event_id,
                        "signal_id": result.signal.id,
                        "decision_id": result.decision.id,
                    },
                )
            except Exception as exc:
                items_failed += 1
                errors.append(str(exc))
                logger.exception(
                    "connector item failed",
                    extra={
                        "connector": connector_name,
                        "correlation_id": connector_correlation_id,
                    },
                )
                continue

        duration_ms = int((time.perf_counter() - started_at) * 1000)
        status = self._status(raw_items, items_processed, items_failed, errors)
        logger.info(
            "connector execution completed",
            extra={
                "connector": connector_name,
                "correlation_id": connector_correlation_id,
                "items_fetched": len(raw_items),
                "items_processed": items_processed,
                "items_failed": items_failed,
                "decisions_created": decisions_created,
            },
        )
        return ConnectorExecutionReport(
            connector_name=connector_name,
            status=status,
            items_fetched=len(raw_items),
            items_processed=items_processed,
            items_failed=items_failed,
            decisions_created=decisions_created,
            duration_ms=duration_ms,
            errors=tuple(errors),
        )

    @staticmethod
    def _event_id(connector_name: str, raw_item: Mapping[str, object]) -> str:
        canonical = json.dumps(
            raw_item, sort_keys=True, default=str, separators=(",", ":")
        )
        return str(uuid5(NAMESPACE_URL, f"{connector_name}:{canonical}"))

    @staticmethod
    def _status(
        raw_items: list[Mapping[str, object]],
        items_processed: int,
        items_failed: int,
        errors: list[str],
    ) -> str:
        if not raw_items:
            return "empty"
        if items_failed == 0:
            return "success"
        if items_processed > 0:
            return "partial"
        return "failed" if errors else "empty"
