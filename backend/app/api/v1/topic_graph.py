"""Topic graph routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.dependencies.database import get_db
from backend.app.schemas.knowledge import TopicGraphRead
from backend.app.services.knowledge_reads import KnowledgeReadService

router = APIRouter(prefix="/api/v1/topic-graph", tags=["topic-graph"])


def _service(db: Session) -> KnowledgeReadService:
    return KnowledgeReadService(db)


@router.get("/{topic_id}", response_model=TopicGraphRead)
def get_topic_graph(topic_id: str, db: Session = Depends(get_db)) -> TopicGraphRead:
    graph = _service(db).get_topic_graph(topic_id)
    if graph is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    return TopicGraphRead.model_validate(
        {
            "topic_id": graph["topic"].id,
            "topic_name": graph["topic"].display_name,
            "relationships": graph["relationships"],
        }
    )
