"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab

from backend.app.core.config import settings

celery_app = Celery("viralforge", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "poll-google-trends": {
            "task": "backend.app.workers.tasks.poll_google_trends",
            "schedule": crontab(
                minute=f"*/{settings.google_trends_poll_interval_minutes}"
            ),
        }
    },
)
