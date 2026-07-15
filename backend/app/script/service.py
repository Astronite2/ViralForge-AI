# ruff: noqa: E501
"""Transactional source-grounded Script Writer workflow."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.production_brief import ProjectProductionBriefModel
from backend.app.models.project import ProjectModel
from backend.app.models.research import ProjectResearchDossierModel
from backend.app.models.script import ProjectScriptModel
from backend.app.script.context_builder import build_context
from backend.app.script.evidence_coverage import EvidenceCoverage
from backend.app.script.script_builder import ScriptBuilder
from backend.app.script.script_validator import validate_script


class ProjectScriptService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def run(self, project_id: str) -> dict[str, Any]:
        project = self.session.get(ProjectModel, project_id)
        if project is None:
            raise ValueError("Project not found")
        if project.status != "SCRIPTING":
            raise ValueError(f"Script Writer cannot run from status {project.status}")
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
        if (
            dossier is None
            or dossier.research_status != "APPROVED"
            or brief is None
            or brief.status != "APPROVED"
            or (
                brief.research_version_used is not None
                and brief.research_version_used != dossier.research_version
            )
        ):
            raise ValueError("Approved research and Production Brief are required")
        script = self._script(project_id)
        try:
            script.status = "GENERATING"
            script.current_step = "CHECKING_EVIDENCE"
            script.started_at = datetime.now(UTC)
            self.session.commit()
            duration = int(brief.payload.get("target_duration_minutes") or 15)
            target = duration * settings.script_words_per_minute
            coverage = EvidenceCoverage().evaluate(
                duration=duration, brief=brief.payload, dossier=dossier.payload
            )
            script.target_word_count = target
            script.evidence_sufficiency = coverage["status"]
            if coverage["status"] == "INSUFFICIENT" or (
                coverage["status"] == "LIMITED"
                and not settings.script_allow_limited_evidence
            ):
                script.status = "NEEDS_REVIEW"
                script.current_step = "EVIDENCE_INSUFFICIENT"
                script.payload = {
                    "evidence_coverage": coverage,
                    "full_script": "",
                    "sections": [],
                    "unsupported_claims": [],
                    "factual_warnings": [coverage["recommended_action"]],
                    "limitations": [
                        "No narration was generated because approved evidence cannot support the requested duration."
                    ],
                }
                script.completed_at = datetime.now(UTC)
                self.session.commit()
                return self._summary(project, script)
            script.current_step = "BUILDING_CONTEXT"
            self.session.commit()
            context = build_context(brief.payload, dossier.payload)
            script.current_step = "GENERATING_NARRATION"
            self.session.commit()
            payload = ScriptBuilder().build(
                project=project,
                brief=brief.payload,
                context=context,
                target_words=target,
                coverage=coverage,
            )
            script.current_step = "VALIDATING_CITATIONS"
            self.session.commit()
            validate_script(payload, brief.payload, dossier.payload)
            script.payload = payload
            script.research_version_used = dossier.research_version
            script.production_brief_version_used = brief.version
            script.actual_word_count = payload["actual_word_count"]
            script.estimated_duration_minutes = payload["estimated_duration_minutes"]
            script.status = "COMPLETE"
            script.current_step = "COMPLETE"
            script.generated_at = datetime.now(UTC)
            script.completed_at = datetime.now(UTC)
            project.status = "SCRIPT_COMPLETE"
            self.session.commit()
            return self._summary(project, script)
        except Exception as exc:
            self.session.rollback()
            script = self._script(project_id)
            script.status = "FAILED"
            script.current_step = "FAILED"
            script.safe_error_message = (
                str(exc)[:500]
                if isinstance(exc, ValueError)
                else "Script generation failed during evidence validation"
            )
            script.completed_at = datetime.now(UTC)
            self.session.commit()
            raise

    def _script(self, project_id: str) -> ProjectScriptModel:
        script = self.session.scalar(
            select(ProjectScriptModel).where(
                ProjectScriptModel.project_id == project_id
            )
        )
        if script is None:
            script = ProjectScriptModel(
                project_id=project_id,
                status="PENDING",
                version=settings.script_version,
                current_step="INITIALIZING",
                target_word_count=0,
                actual_word_count=0,
                payload={},
            )
            self.session.add(script)
            self.session.commit()
            self.session.refresh(script)
        return script

    @staticmethod
    def _summary(project: ProjectModel, script: ProjectScriptModel) -> dict[str, Any]:
        return {
            "project_id": project.id,
            "project_status": project.status,
            "script_status": script.status,
            "evidence_sufficiency": script.evidence_sufficiency,
            "actual_word_count": script.actual_word_count,
            "target_word_count": script.target_word_count,
            "estimated_duration_minutes": script.estimated_duration_minutes,
        }
