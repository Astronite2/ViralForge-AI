"""Transactional project research workflow."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.project import ProjectModel
from backend.app.models.research import ProjectResearchDossierModel
from backend.app.research.dossier_builder import DossierBuilder
from backend.app.research.providers.base import ResearchSourceProvider
from backend.app.research.providers.web_search import CompositeResearchProvider
from backend.app.research.source_collector import SourceCollector

STEPS = {
    "INITIALIZING": 5,
    "GENERATING_QUERIES": 15,
    "SEARCHING_SOURCES": 35,
    "RANKING_SOURCES": 50,
    "EXTRACTING_FACTS": 65,
    "VERIFYING_FACTS": 75,
    "BUILDING_DOSSIER": 85,
    "SAVING": 95,
    "COMPLETE": 100,
    "FAILED": 0,
}


class ProjectResearchService:
    def __init__(
        self, session: Session, provider: ResearchSourceProvider | None = None
    ) -> None:
        self.session = session
        self.provider = provider or CompositeResearchProvider()

    def run(self, project_id: str) -> dict[str, object]:
        project = self.session.get(ProjectModel, project_id)
        if project is None:
            raise ValueError("Project not found")
        if project.status != "RESEARCHING":
            raise ValueError(f"Research cannot run from status {project.status}")
        dossier = self._get_or_create(project_id)
        try:
            dossier.research_status = "RUNNING"
            dossier.started_at = datetime.now(UTC)
            dossier.error_message = None
            self._step(dossier, "GENERATING_QUERIES")
            queries = self._queries(project.title)
            self._step(dossier, "SEARCHING_SOURCES")
            sources = SourceCollector(
                self.provider, max_sources=settings.research_max_sources
            ).collect(queries)
            if not sources:
                raise RuntimeError("No research sources were found")
            dossier.sources_found = len(sources)
            self._step(dossier, "RANKING_SOURCES")
            self._step(dossier, "EXTRACTING_FACTS")
            self._step(dossier, "VERIFYING_FACTS")
            self._step(dossier, "BUILDING_DOSSIER")
            payload = DossierBuilder().build(topic=project.title, sources=sources)
            dossier.facts_verified = len(payload["key_facts"]) + len(
                payload["interesting_facts"]
            )
            self._step(dossier, "SAVING")
            dossier.payload = payload
            dossier.research_status = "COMPLETE"
            dossier.current_step = "COMPLETE"
            dossier.progress = 100
            dossier.generated_at = datetime.now(UTC)
            dossier.completed_at = datetime.now(UTC)
            project.status = "RESEARCH_COMPLETE"
            self.session.commit()
            return {
                "project_id": project_id,
                "research_status": "COMPLETE",
                "sources_found": dossier.sources_found,
                "facts_verified": dossier.facts_verified,
            }
        except Exception as exc:
            self.session.rollback()
            dossier = self._get_or_create(project_id)
            dossier.research_status = "FAILED"
            dossier.current_step = "FAILED"
            dossier.progress = 0
            dossier.error_message = self._safe_error(exc)
            dossier.completed_at = datetime.now(UTC)
            self.session.commit()
            raise

    def _get_or_create(self, project_id: str) -> ProjectResearchDossierModel:
        dossier = self.session.scalar(
            select(ProjectResearchDossierModel).where(
                ProjectResearchDossierModel.project_id == project_id
            )
        )
        if dossier is None:
            dossier = ProjectResearchDossierModel(
                project_id=project_id,
                research_status="PENDING",
                research_version=settings.research_version,
                progress=5,
                current_step="INITIALIZING",
                sources_found=0,
                facts_verified=0,
                payload={},
            )
            self.session.add(dossier)
            self.session.commit()
            self.session.refresh(dossier)
        return dossier

    def _step(self, dossier: ProjectResearchDossierModel, step: str) -> None:
        dossier.current_step = step
        dossier.progress = STEPS[step]
        self.session.commit()

    @staticmethod
    def _queries(topic: str) -> list[str]:
        dimensions = [
            "overview",
            "history",
            "timeline dates",
            "key people",
            "locations",
            "myths misconceptions",
            "controversies",
            "archaeology evidence",
            "surprising facts",
            "frequently asked questions",
            "museum",
            "documentary visuals",
        ]
        return [
            f"{topic} {dimension}"
            for dimension in dimensions[: settings.research_max_search_queries]
        ]

    @staticmethod
    def _safe_error(exc: Exception) -> str:
        if isinstance(exc, (ValueError, RuntimeError)):
            return str(exc)[:500]
        return "Research failed while processing source evidence"
