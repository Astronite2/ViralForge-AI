"""Historical knowledge routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.dependencies.database import get_db
from backend.app.schemas.knowledge import TopicHistoryRead
from backend.app.services.knowledge_reads import KnowledgeReadService

router = APIRouter(prefix="/api/v1/history", tags=["history"])


def _service(db: Session) -> KnowledgeReadService:
    return KnowledgeReadService(db)


@router.get("/{topic_id}", response_model=TopicHistoryRead)
def get_history(topic_id: str, db: Session = Depends(get_db)) -> TopicHistoryRead:
    history = _service(db).get_history(topic_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    return TopicHistoryRead.model_validate(
        {
            "topic_id": history["topic"].id,
            "topic_name": history["topic"].display_name,
            "observations": history["observations"],
            "analytics": history["analytics"],
            "evidence_history": history["evidence_history"],
            "opportunity_scores": history["opportunity_scores"],
        }
    )
