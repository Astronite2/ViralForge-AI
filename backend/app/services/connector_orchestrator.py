"""Connector orchestration service."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Iterable, Mapping
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.app.connectors.base import BaseConnector
from backend.app.connectors.errors import ConnectorAvailabilityError
from backend.app.connectors.registry import (
    ConnectorRegistry,
    build_default_connector_registry,
)
from backend.app.core.config import settings
from backend.app.db.session import SessionLocal
from backend.app.domain.connector_orchestration import (
    ConnectorExecutionReport,
    ConnectorOrchestrationReport,
)
from backend.app.domain.content import Content
from backend.app.domain.trend_signal import TrendSignal
from backend.app.repositories.content import ContentRepository
from backend.app.services.connector_status import ConnectorStatusStore
from backend.app.services.signal_decision import SignalDecisionService
from backend.app.services.unified_signal_normalizer import UnifiedSignalNormalizer
from backend.app.utils.events import SignalDetected
from backend.app.utils.idempotency import stable_signal_event_id

logger = logging.getLogger(__name__)


class ConnectorOrchestrator:
    """Execute enabled connectors and route normalized signals to the decision flow."""

    def __init__(
        self,
        registry: ConnectorRegistry | None = None,
        *,
        session_factory: Callable[[], Session] | None = None,
        signal_normalizer: UnifiedSignalNormalizer | None = None,
        status_store: ConnectorStatusStore | None = None,
    ) -> None:
        self.registry = registry or build_default_connector_registry()
        self.session_factory = session_factory or SessionLocal
        self.signal_normalizer = signal_normalizer or UnifiedSignalNormalizer()
        self.status_store = status_store or ConnectorStatusStore(
            use_redis=registry is None
        )

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
            self.status_store.record(
                connector_report,
                completed_at=datetime.now(UTC),
            )

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
        metadata = connector.metadata
        provider = metadata.provider
        provider_experimental = metadata.provider_experimental
        report_metadata = {
            "connector_version": metadata.version,
            "capabilities": metadata.capabilities.api_values(),
        }
        try:
            raw_items = connector.fetch(**kwargs)
        except ConnectorAvailabilityError as exc:
            duration_ms = int((time.perf_counter() - started_at) * 1000)
            logger.warning(
                "connector provider unavailable",
                extra={
                    "connector": connector_name,
                    "provider": provider,
                    "status": exc.report_status,
                    "error_code": exc.error_code,
                    "correlation_id": connector_correlation_id,
                },
            )
            return ConnectorExecutionReport(
                connector_name=connector_name,
                status=exc.report_status,
                items_fetched=0,
                items_processed=0,
                items_failed=0,
                decisions_created=0,
                duration_ms=duration_ms,
                errors=(exc.safe_message,),
                provider=provider,
                provider_experimental=provider_experimental,
                error_code=exc.error_code,
                **report_metadata,
            )
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
                provider=provider,
                provider_experimental=provider_experimental,
                error_code="unexpected_failure",
                **report_metadata,
            )

        items_processed = 0
        items_failed = 0
        decisions_created = 0
        errors: list[str] = []

        for raw_item in raw_items:
            try:
                connector.validate(raw_item)
                normalized = connector.normalize(raw_item)
                signals = self._signals_for_normalized(normalized)
                metadata = self._metadata_for_normalized(normalized, raw_item)
                unified_signals = self.signal_normalizer.normalize(
                    normalized,
                    event_version=settings.event_version,
                    correlation_id=connector_correlation_id,
                    connector_metadata={"raw_item": dict(raw_item)},
                )
                if len(unified_signals) != len(signals):
                    raise RuntimeError(
                        "Unified normalization must preserve embedded signal count"
                    )
                processed_signals: list[tuple[SignalDetected, str, str, bool]] = []
                with self.session_factory() as session:
                    with session.begin():
                        if isinstance(normalized, Content):
                            ContentRepository(session).save(normalized)
                        service = SignalDecisionService(session)
                        for signal_index, (signal, unified_signal) in enumerate(
                            zip(signals, unified_signals, strict=True)
                        ):
                            event_metadata = {
                                **metadata,
                                "event_version": settings.event_version,
                                "unified_signal": unified_signal.to_payload(),
                            }
                            event = SignalDetected(
                                signal=signal,
                                unified_signal=unified_signal,
                                metadata=event_metadata,
                                event_id=self._event_id(
                                    connector_name,
                                    normalized,
                                    signal_index=signal_index,
                                ),
                                correlation_id=connector_correlation_id,
                            )
                            result = service.process(event)
                            processed_signals.append(
                                (
                                    event,
                                    result.signal.id,
                                    result.decision.id,
                                    result.duplicate,
                                )
                            )
                for event, signal_id, decision_id, duplicate in processed_signals:
                    if not duplicate:
                        decisions_created += 1
                    logger.info(
                        "signal decision processed",
                        extra={
                            "connector": connector_name,
                            "correlation_id": connector_correlation_id,
                            "event_id": event.event_id,
                            "signal_id": signal_id,
                            "decision_id": decision_id,
                        },
                    )
                items_processed += 1
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
            provider=provider,
            provider_experimental=provider_experimental,
            error_code="item_failure" if errors else None,
            **report_metadata,
        )

    @staticmethod
    def _event_id(
        connector_name: str,
        normalized: TrendSignal | Content,
        *,
        signal_index: int,
    ) -> str:
        return stable_signal_event_id(
            connector_name,
            normalized,
            signal_index=signal_index,
        )

    @staticmethod
    def _signals_for_normalized(
        normalized: TrendSignal | Content,
    ) -> tuple[TrendSignal, ...]:
        if isinstance(normalized, TrendSignal):
            return (normalized,)
        if isinstance(normalized, Content):
            if normalized.signals:
                return normalized.signals
            raise TypeError("Content normalization must include at least one signal")
        raise TypeError("Connector normalization must return Content or TrendSignal")

    @staticmethod
    def _metadata_for_normalized(
        normalized: TrendSignal | Content, raw_item: Mapping[str, object]
    ) -> dict[str, object]:
        if isinstance(normalized, Content):
            return {
                "content": {
                    "id": normalized.id,
                    "platform": normalized.platform,
                    "creator_name": normalized.creator_name,
                    "creator_id": normalized.creator_id,
                    "title": normalized.title,
                    "description": normalized.description,
                    "url": normalized.url,
                    "language": normalized.language,
                    "country": normalized.country,
                    "published_at": normalized.published_at.isoformat(),
                    "duration_seconds": normalized.duration_seconds,
                    "content_type": normalized.content_type,
                    "metrics": dict(normalized.metrics),
                    "analysis": dict(normalized.analysis),
                    "metadata": dict(normalized.metadata),
                },
                "raw_item": dict(raw_item),
            }
        return {"raw_item": dict(raw_item)}

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
