# ruff: noqa: E501
"""Focused, transactional research expansion with audit and stale-artifact handling."""

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.production_brief import ProjectProductionBriefModel
from backend.app.models.project import ProjectModel
from backend.app.models.research import ProjectResearchDossierModel
from backend.app.models.script import ProjectScriptModel
from backend.app.producer.brief_validator import ensure_fact_ids
from backend.app.research.dossier_builder import DossierBuilder
from backend.app.research.gap_analyzer import ResearchGapAnalyzer
from backend.app.research.providers.base import ResearchSourceProvider
from backend.app.research.providers.web_search import CompositeResearchProvider
from backend.app.research.source_collector import SourceCollector


def next_version(value: str, prefix: str) -> str:
    try:
        number = int(value.rsplit("-v", 1)[1])
    except (IndexError, ValueError):
        number = 1
    return f"{prefix}-v{number + 1}"


class ResearchExpansionService:
    def __init__(
        self, session: Session, provider: ResearchSourceProvider | None = None
    ) -> None:
        self.session = session
        self.provider = provider or CompositeResearchProvider()

    def run(
        self,
        project_id: str,
        *,
        focus_areas: list[str] | None = None,
        target_duration: int = 15,
        max_additional_sources: int = 25,
    ) -> dict[str, Any]:
        project = self.session.get(ProjectModel, project_id)
        dossier = self.session.scalar(
            select(ProjectResearchDossierModel).where(
                ProjectResearchDossierModel.project_id == project_id
            )
        )
        brief = self.session.scalar(
            select(ProjectProductionBriefModel).where(
                ProjectProductionBriefModel.project_id == project_id
            )
        )
        if project is None or dossier is None:
            raise ValueError("Existing research dossier is required")
        if dossier.research_status not in {"APPROVED", "RUNNING"}:
            raise ValueError("Approved research is required for expansion")
        if brief is None:
            raise ValueError("Production Brief is required for gap analysis")
        snapshot = {
            "payload": deepcopy(dossier.payload),
            "version": dossier.research_version,
            "status": (
                "APPROVED"
                if dossier.research_status == "RUNNING"
                else dossier.research_status
            ),
            "sources": dossier.sources_found,
            "facts": dossier.facts_verified,
            "project_status": project.status,
        }
        try:
            dossier.research_status = "RUNNING"
            dossier.current_step = "ANALYZING_GAPS"
            dossier.progress = 15
            dossier.started_at = datetime.now(UTC)
            dossier.error_message = None
            self.session.commit()
            existing = ensure_fact_ids(deepcopy(snapshot["payload"]))
            gaps = ResearchGapAnalyzer().analyze(
                topic=project.title,
                dossier=existing,
                brief=brief.payload,
                target_duration=target_duration,
                focus_areas=focus_areas,
            )
            dossier.current_step = "SEARCHING_SOURCES"
            dossier.progress = 35
            self.session.commit()
            collected = SourceCollector(
                self.provider, max_sources=max_additional_sources
            ).collect(gaps["proposed_search_queries"])
            known_urls = {
                str(source.get("url", "")).split("#", 1)[0].rstrip("/").lower()
                for source in existing.get("sources", [])
            }
            new_sources = [
                source
                for source in collected
                if str(source.get("url", "")).split("#", 1)[0].rstrip("/").lower()
                not in known_urls
            ]
            dossier.current_step = "EXTRACTING_FACTS"
            dossier.progress = 65
            self.session.commit()
            addition = ensure_fact_ids(
                DossierBuilder().build(topic=project.title, sources=new_sources)
            )
            existing_claims = {
                str(fact.get("claim", "")).strip().lower()
                for fact in self._facts(existing)
            }
            new_facts = [
                fact
                for fact in self._facts(addition)
                if str(fact.get("claim", "")).strip().lower() not in existing_claims
                and set(fact.get("supporting_source_ids", []))
                <= {str(source["id"]) for source in new_sources}
            ]
            merged = self._merge(existing, addition, new_sources, new_facts)
            version = next_version(snapshot["version"], "research")
            audit = {
                "expansion_reason": "Script evidence coverage was insufficient",
                "requested_target_duration": target_duration,
                "identified_gaps": gaps,
                "queries_executed": gaps["proposed_search_queries"],
                "sources_added": [source["id"] for source in new_sources],
                "facts_added": [fact["id"] for fact in new_facts],
                "facts_rejected": len(self._facts(addition)) - len(new_facts),
                "unresolved_gaps": [],
                "timestamp": datetime.now(UTC).isoformat(),
            }
            merged["expansion_history"] = [
                *existing.get("expansion_history", []),
                audit,
            ]
            merged["research_version"] = version
            merged["research_status"] = "NEEDS_REVIEW"
            dossier.payload = merged
            dossier.research_version = version
            dossier.research_status = "NEEDS_REVIEW"
            dossier.current_step = "COMPLETE"
            dossier.progress = 100
            dossier.sources_found = len(merged["sources"])
            dossier.facts_verified = len(self._facts(merged))
            dossier.generated_at = datetime.now(UTC)
            dossier.completed_at = datetime.now(UTC)
            project.status = "RESEARCH_COMPLETE"
            self._stale(project_id)
            self.session.commit()
            return {
                "project_id": project_id,
                "research_status": "NEEDS_REVIEW",
                "previous_dossier_version": snapshot["version"],
                "new_dossier_version": version,
                "sources_added": len(new_sources),
                "facts_added": len(new_facts),
                "authoritative_sources_added": sum(
                    source.get("source_quality") in {"PRIMARY", "AUTHORITATIVE"}
                    for source in new_sources
                ),
                "unresolved_gaps": audit["unresolved_gaps"],
            }
        except Exception as exc:
            self.session.rollback()
            dossier = self.session.scalar(
                select(ProjectResearchDossierModel).where(
                    ProjectResearchDossierModel.project_id == project_id
                )
            )
            project = self.session.get(ProjectModel, project_id)
            if dossier is not None and project is not None:
                dossier.payload = snapshot["payload"]
                dossier.research_version = snapshot["version"]
                dossier.research_status = snapshot["status"]
                dossier.sources_found = snapshot["sources"]
                dossier.facts_verified = snapshot["facts"]
                dossier.current_step = "EXPANSION_FAILED"
                dossier.error_message = (
                    str(exc)[:500]
                    if isinstance(exc, (ValueError, RuntimeError))
                    else "Research expansion failed; the approved dossier was preserved"
                )
                project.status = snapshot["project_status"]
                self.session.commit()
            raise

    def _stale(self, project_id: str) -> None:
        brief = self.session.scalar(
            select(ProjectProductionBriefModel).where(
                ProjectProductionBriefModel.project_id == project_id
            )
        )
        script = self.session.scalar(
            select(ProjectScriptModel).where(
                ProjectScriptModel.project_id == project_id
            )
        )
        if brief:
            brief.status = "STALE"
            brief.approved_at = None
        if script:
            script.status = "STALE"
            script.approved_at = None

    @staticmethod
    def _facts(payload: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            fact
            for key in ("key_facts", "interesting_facts")
            for fact in payload.get(key, [])
            if fact.get("verification_status") != "UNVERIFIED"
        ]

    @staticmethod
    def _merge(
        existing: dict[str, Any],
        addition: dict[str, Any],
        sources: list[dict[str, Any]],
        facts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        merged = deepcopy(existing)
        merged["sources"] = [*existing.get("sources", []), *sources]
        merged["key_facts"] = [*existing.get("key_facts", []), *facts]
        for key in ("story_angles", "visual_opportunities", "limitations"):
            merged[key] = list(
                {
                    str(item): item
                    for item in [*existing.get(key, []), *addition.get(key, [])]
                }.values()
            )
        return merged
