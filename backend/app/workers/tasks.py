"""Celery task module for polling and signal processing."""

import logging
from collections.abc import Mapping
from typing import Any

from redis.exceptions import RedisError
from sqlalchemy.exc import OperationalError

from backend.app.core.config import settings
from backend.app.db.session import SessionLocal
from backend.app.services.connector_orchestrator import ConnectorOrchestrator
from backend.app.services.signal_decision import SignalDecisionService
from backend.app.utils.events import SignalDetected
from backend.app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="backend.app.workers.tasks.process_signal_detected",
    max_retries=settings.processing_retry_limit,
    default_retry_delay=settings.processing_retry_delay_seconds,
)
def process_signal_detected(self: Any, payload: Mapping[str, Any]) -> dict[str, Any]:
    """Process one signal event inside a single database transaction."""
    event = SignalDetected.from_payload(payload)
    logger.info(
        "SignalDetected processing started",
        extra={
            "task_id": self.request.id,
            "event_id": event.event_id,
            "correlation_id": event.correlation_id,
            "source": event.signal.source,
        },
    )
    try:
        with SessionLocal() as session:
            service = SignalDecisionService(session)
            result = service.process(event)
            return {
                "decision_id": result.decision.id,
                "topic_id": result.topic.id,
                "signal_id": result.signal.id,
                "correlation_id": result.decision_event.correlation_id,
                "duplicate": result.duplicate,
            }
    except (OperationalError, RedisError, ConnectionError) as exc:
        logger.info(
            "retry scheduled",
            extra={
                "task_id": self.request.id,
                "event_id": event.event_id,
                "correlation_id": event.correlation_id,
            },
        )
        raise self.retry(exc=exc) from exc
    except ValueError as exc:
        logger.error(
            "processing failed",
            extra={
                "task_id": self.request.id,
                "event_id": event.event_id,
                "correlation_id": event.correlation_id,
                "reason": str(exc),
            },
        )
        return {"status": "validation_failed", "event_id": event.event_id}


@celery_app.task(
    bind=True,
    name="backend.app.workers.tasks.poll_google_trends",
    max_retries=settings.processing_retry_limit,
    default_retry_delay=settings.processing_retry_delay_seconds,
)
def poll_google_trends(
    self: Any, *, geo: str = "US", limit: int | None = None
) -> dict[str, Any]:
    """Poll Google Trends, enqueue signal tasks, and return a batch summary."""
    batch_limit = limit if limit is not None else settings.polling_batch_size
    logger.info(
        "Google Trends polling started",
        extra={
            "task_id": self.request.id,
            "correlation_id": "",
            "source": "google_trends",
        },
    )
    report = ConnectorOrchestrator().run(
        {
            settings.google_trends_source_name: {
                "geo": geo,
                "limit": batch_limit,
            }
        },
        enabled_connectors=(settings.google_trends_source_name,),
    )

    logger.info(
        "Google Trends polling completed",
        extra={
            "task_id": self.request.id,
            "source": "google_trends",
            "connector_reports": len(report.connector_reports),
        },
    )
    return _report_payload(report)


def _report_payload(report: Any) -> dict[str, Any]:
    return {
        "started_at": report.started_at.isoformat(),
        "completed_at": report.completed_at.isoformat(),
        "duration_ms": report.duration_ms,
        "connector_reports": [
            {
                "connector_name": connector.connector_name,
                "status": connector.status,
                "items_fetched": connector.items_fetched,
                "items_processed": connector.items_processed,
                "items_failed": connector.items_failed,
                "decisions_created": connector.decisions_created,
                "duration_ms": connector.duration_ms,
                "errors": list(connector.errors),
            }
            for connector in report.connector_reports
        ],
    }
