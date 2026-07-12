"""Celery task module for polling and signal processing."""

import logging
from collections.abc import Mapping
from typing import Any
from uuid import uuid4

from redis.exceptions import RedisError
from sqlalchemy.exc import OperationalError

from backend.app.connectors.registry import build_default_connector_registry
from backend.app.core.config import settings
from backend.app.db.session import SessionLocal
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
    connector = build_default_connector_registry().get(
        settings.google_trends_source_name
    )
    batch_limit = limit if limit is not None else settings.polling_batch_size
    correlation_id = str(uuid4())
    logger.info(
        "Google Trends polling started",
        extra={
            "task_id": self.request.id,
            "correlation_id": correlation_id,
            "source": "google_trends",
        },
    )
    try:
        raw_items = connector.fetch(geo=geo, limit=batch_limit)
    except RuntimeError as exc:
        logger.info(
            "retry scheduled",
            extra={
                "task_id": self.request.id,
                "correlation_id": correlation_id,
                "source": "google_trends",
            },
        )
        raise self.retry(exc=exc) from exc

    emitted = 0
    for raw_item in raw_items:
        try:
            connector.validate(raw_item)
            signal = connector.normalize(raw_item)
        except ValueError as exc:
            logger.error(
                "processing failed",
                extra={
                    "task_id": self.request.id,
                    "correlation_id": correlation_id,
                    "source": "google_trends",
                    "reason": str(exc),
                },
            )
            continue

        event = SignalDetected(signal=signal, correlation_id=correlation_id)
        try:
            process_signal_detected.delay(event.to_payload())
        except (RedisError, ConnectionError, OperationalError) as exc:
            logger.info(
                "retry scheduled",
                extra={
                    "task_id": self.request.id,
                    "correlation_id": correlation_id,
                    "event_id": event.event_id,
                    "source": signal.source,
                },
            )
            raise self.retry(exc=exc) from exc
        emitted += 1
        logger.info(
            "SignalDetected emitted",
            extra={
                "task_id": self.request.id,
                "correlation_id": correlation_id,
                "event_id": event.event_id,
                "source": signal.source,
            },
        )

    logger.info(
        "Google Trends polling completed",
        extra={
            "task_id": self.request.id,
            "correlation_id": correlation_id,
            "source": "google_trends",
            "signals_fetched": len(raw_items),
            "signals_emitted": emitted,
        },
    )
    return {
        "status": "queued",
        "correlation_id": correlation_id,
        "signals_fetched": len(raw_items),
        "signals_emitted": emitted,
    }
