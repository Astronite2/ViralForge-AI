"""Celery task module for polling and signal processing."""

import logging
from collections.abc import Mapping
from typing import Any

from redis.exceptions import RedisError
from sqlalchemy.exc import OperationalError

from backend.app.core.config import settings
from backend.app.db.session import SessionLocal
from backend.app.domain.reasoning import ReasoningType
from backend.app.reasoning.errors import (
    ReasoningConfigurationError,
    ReasoningDisabledError,
    ReasoningTransientProviderError,
    ReasoningValidationError,
)
from backend.app.services.connector_orchestrator import ConnectorOrchestrator
from backend.app.services.reasoning import ReasoningService
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
    self: Any, *, geo: str | None = None, limit: int | None = None
) -> dict[str, Any]:
    """Poll Google Trends, enqueue signal tasks, and return a batch summary."""
    batch_limit = limit if limit is not None else settings.polling_batch_size
    region = geo or settings.google_trends_default_geo
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
                "geo": region,
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



@celery_app.task(
    bind=True,
    name="backend.app.workers.tasks.poll_youtube",
    max_retries=settings.processing_retry_limit,
    default_retry_delay=settings.processing_retry_delay_seconds,
)
def poll_youtube(
    self: Any,
    *,
    query: str,
    region: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Poll YouTube, process normalized content, and return a batch summary."""
    search_query = query.strip()
    if not search_query:
        raise ValueError("YouTube query is required")

    batch_limit = (
        limit if limit is not None else settings.youtube_default_limit
    )
    search_region = region or settings.youtube_default_region

    logger.info(
        "YouTube polling started",
        extra={
            "task_id": self.request.id,
            "correlation_id": "",
            "source": settings.youtube_source_name,
            "query": search_query,
        },
    )

    report = ConnectorOrchestrator().run(
        {
            settings.youtube_source_name: {
                "query": search_query,
                "region": search_region,
                "limit": batch_limit,
            }
        },
        enabled_connectors=(settings.youtube_source_name,),
    )

    logger.info(
        "YouTube polling completed",
        extra={
            "task_id": self.request.id,
            "source": settings.youtube_source_name,
            "query": search_query,
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
                "provider": connector.provider,
                "provider_experimental": connector.provider_experimental,
                "error_code": connector.error_code,
            }
            for connector in report.connector_reports
        ],
    }


@celery_app.task(
    bind=True,
    name="backend.app.workers.tasks.run_reasoning_request",
    max_retries=settings.ai_max_retries,
    default_retry_delay=settings.processing_retry_delay_seconds,
)
def run_reasoning_request(self: Any, payload: Mapping[str, Any]) -> dict[str, Any]:
    """Run one reasoning request through the service layer."""
    reasoning_type = str(payload.get("reasoning_type", ""))
    logger.info(
        "reasoning task started",
        extra={
            "task_id": self.request.id,
            "reasoning_type": reasoning_type,
            "correlation_id": str(payload.get("correlation_id", "")),
        },
    )
    try:
        with SessionLocal() as session:
            service = ReasoningService(session)
            if reasoning_type == ReasoningType.DECISION_EXPLANATION.value:
                result = service.explain_decision(
                    str(payload["decision_id"]),
                    force_refresh=bool(payload.get("force_refresh", False)),
                )
            elif reasoning_type == ReasoningType.OPPORTUNITY_COMPARISON.value:
                result = service.compare_opportunities(
                    topic_ids=list(payload.get("topic_ids") or []),
                    opportunity_ids=list(payload.get("opportunity_ids") or []),
                    force_refresh=bool(payload.get("force_refresh", False)),
                )
            elif reasoning_type == ReasoningType.EXECUTION_STRATEGY.value:
                result = service.execution_strategy(
                    str(payload["decision_id"]),
                    target_platform=payload.get("target_platform") or None,
                    force_refresh=bool(payload.get("force_refresh", False)),
                )
            elif reasoning_type == ReasoningType.CHANGE_SUMMARY.value:
                result = service.change_summary(
                    str(payload["topic_id"]),
                    previous_decision_id=payload.get("previous_decision_id") or None,
                    current_decision_id=payload.get("current_decision_id") or None,
                    force_refresh=bool(payload.get("force_refresh", False)),
                )
            else:
                raise ValueError(f"Unsupported reasoning type: {reasoning_type}")
            return {
                "result_id": result.result.id if result.result is not None else None,
                "run_id": result.run.id,
                "cached": result.cached,
            }
    except (
        OperationalError,
        RedisError,
        ConnectionError,
        ReasoningTransientProviderError,
    ) as exc:
        logger.info(
            "reasoning retry scheduled",
            extra={
                "task_id": self.request.id,
                "reasoning_type": reasoning_type,
                "correlation_id": str(payload.get("correlation_id", "")),
            },
        )
        raise self.retry(exc=exc) from exc
    except (
        ReasoningDisabledError,
        ReasoningConfigurationError,
        ReasoningValidationError,
        ValueError,
        KeyError,
    ) as exc:
        logger.error(
            "reasoning task failed",
            extra={
                "task_id": self.request.id,
                "reasoning_type": reasoning_type,
                "correlation_id": str(payload.get("correlation_id", "")),
                "reason": str(exc),
            },
        )
        return {
            "status": "failed",
            "reasoning_type": reasoning_type,
            "error": str(exc),
        }
