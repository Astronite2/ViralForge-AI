# ruff: noqa: E501
"""Transactional Executive Producer workflow."""

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.production_brief import ProjectProductionBriefModel
from backend.app.models.project import ProjectModel
from backend.app.models.research import ProjectResearchDossierModel
from backend.app.producer.angle_selector import AngleSelector
from backend.app.producer.brief_builder import BriefBuilder
from backend.app.producer.brief_validator import ensure_fact_ids, validate_brief
from backend.app.producer.profitability_recheck import ProfitabilityRecheck


class ExecutiveProducerService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def run(self, project_id: str) -> dict[str, Any]:
        project = self.session.get(ProjectModel, project_id)
        if project is None:
            raise ValueError("Project not found")
        if project.status != "PRODUCING_BRIEF":
            raise ValueError(f"Producer cannot run from status {project.status}")
        dossier_model = self.session.scalar(
            select(ProjectResearchDossierModel).where(
                ProjectResearchDossierModel.project_id == project_id
            )
        )
        if dossier_model is None or dossier_model.research_status != "APPROVED":
            raise ValueError("Approved research is required")
        brief = self._brief(project_id)
        try:
            brief.status = "GENERATING"
            brief.current_step = "GENERATING_ANGLES"
            brief.started_at = datetime.now(UTC)
            self.session.commit()
            dossier = ensure_fact_ids(deepcopy(dossier_model.payload))
            dossier_model.payload = dossier
            candidates = AngleSelector().candidates(dossier)
            brief.candidate_angles_generated = len(candidates)
            if not candidates:
                payload = self._rejection(project, dossier)
                brief.status = "REJECTED"
                brief.recommendation = "REJECT"
                brief.payload = payload
                brief.current_step = "REJECTED"
                brief.completed_at = datetime.now(UTC)
                project.status = "PROJECT_REJECTED"
                self.session.commit()
                return self._summary(project, brief)
            selected = candidates[0]
            brief.current_step = "RECHECKING_PROFITABILITY"
            self.session.commit()
            viability = ProfitabilityRecheck().evaluate(selected, dossier)
            payload = BriefBuilder().build(
                project=project,
                dossier=dossier,
                candidates=candidates,
                selected=selected,
                viability=viability,
            )
            brief.current_step = "VALIDATING_EVIDENCE"
            self.session.commit()
            validate_brief(payload, dossier)
            rejected = viability["recommendation"] == "REJECT"
            brief.status = (
                "REJECTED"
                if rejected
                else (
                    "COMPLETE"
                    if viability["recommendation"] == "PROCEED"
                    else "NEEDS_REVIEW"
                )
            )
            brief.current_step = "REJECTED" if rejected else "COMPLETE"
            brief.selected_angle = selected["title"]
            brief.recommendation = viability["recommendation"]
            brief.revised_money_score = viability["revised_money_score"]
            brief.revised_confidence = viability["revised_confidence"]
            brief.payload = payload
            brief.generated_at = datetime.now(UTC)
            brief.completed_at = datetime.now(UTC)
            project.status = "PROJECT_REJECTED" if rejected else "BRIEF_COMPLETE"
            self.session.commit()
            return self._summary(project, brief)
        except Exception as exc:
            self.session.rollback()
            brief = self._brief(project_id)
            brief.status = "FAILED"
            brief.current_step = "FAILED"
            brief.safe_error_message = (
                str(exc)[:500]
                if isinstance(exc, ValueError)
                else "Executive Producer failed while validating the approved evidence"
            )
            brief.completed_at = datetime.now(UTC)
            self.session.commit()
            raise

    def _brief(self, project_id: str) -> ProjectProductionBriefModel:
        brief = self.session.scalar(
            select(ProjectProductionBriefModel).where(
                ProjectProductionBriefModel.project_id == project_id
            )
        )
        if brief is None:
            brief = ProjectProductionBriefModel(
                project_id=project_id,
                status="PENDING",
                version=settings.production_brief_version,
                current_step="INITIALIZING",
                candidate_angles_generated=0,
                payload={},
            )
            self.session.add(brief)
            self.session.commit()
            self.session.refresh(brief)
        return brief

    @staticmethod
    def _rejection(project: ProjectModel, dossier: dict[str, Any]) -> dict[str, Any]:
        return {
            "title": project.title,
            "recommendation": "REJECT",
            "candidate_angles": [],
            "rejection_reasons": [
                "The approved dossier contains no defensible source-grounded production angle."
            ],
            "selected_fact_ids": [],
            "selected_source_ids": [],
            "limitations": dossier.get("limitations", []),
        }

    @staticmethod
    def _summary(
        project: ProjectModel, brief: ProjectProductionBriefModel
    ) -> dict[str, Any]:
        return {
            "project_id": project.id,
            "project_status": project.status,
            "brief_status": brief.status,
            "candidate_angles_generated": brief.candidate_angles_generated,
            "selected_angle": brief.selected_angle,
            "recommendation": brief.recommendation,
            "revised_money_score": brief.revised_money_score,
        }
