"""Versioned topic routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.dependencies.database import get_db
from backend.app.schemas.decision import DecisionRead
from backend.app.schemas.topic import TopicRead
from backend.app.services.intelligence_reads import IntelligenceReadService

router = APIRouter(prefix="/api/v1/topics", tags=["topics-v1"])


def _service(db: Session) -> IntelligenceReadService:
    return IntelligenceReadService(db)


@router.get("", response_model=list[TopicRead])
def list_topics(
    limit: int = Query(default=settings.pagination_default_limit, ge=1),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[TopicRead]:
    return _service(db).list_topics(min(limit, settings.pagination_max_limit), offset)


@router.get("/{topic_id}", response_model=TopicRead)
def get_topic(topic_id: str, db: Session = Depends(get_db)) -> TopicRead:
    topic = _service(db).get_topic(topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    return topic


@router.get("/{topic_id}/decisions", response_model=list[DecisionRead])
def list_topic_decisions(
    topic_id: str,
    limit: int = Query(default=settings.pagination_default_limit, ge=1),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[DecisionRead]:
    return _service(db).list_topic_decisions(
        topic_id, min(limit, settings.pagination_max_limit), offset
    )
