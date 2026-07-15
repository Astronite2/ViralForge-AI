"""Executive Producer evidence, scoring, workflow, and API tests."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from backend.app.db.session import get_db
from backend.app.main import create_application
from backend.app.models.production_brief import ProjectProductionBriefModel
from backend.app.models.project import ProjectModel
from backend.app.models.research import ProjectResearchDossierModel
from backend.app.producer.angle_selector import AngleSelector
from backend.app.producer.brief_validator import (
    BriefValidationError,
    ensure_fact_ids,
    validate_brief,
)
from backend.app.producer.profitability_recheck import ProfitabilityRecheck
from backend.app.producer.service import ExecutiveProducerService


def dossier_payload(strong=True):
    quality = "AUTHORITATIVE" if strong else "GENERAL_REFERENCE"
    return ensure_fact_ids(
        {
            "research_version": "research-v1",
            "key_facts": [
                {
                    "claim": "A surviving mortar specimen is catalogued by the museum.",
                    "supporting_source_ids": ["src1"],
                    "confidence": 0.9 if strong else 0.45,
                    "verification_status": "SUPPORTED",
                    "notes": "Museum record",
                }
            ],
            "interesting_facts": [],
            "sources": [
                {
                    "id": "src1",
                    "title": "Specimen of Mortar",
                    "source_quality": quality,
                    "url": "https://museum.example/1",
                }
            ],
            "story_angles": [
                {
                    "title": "Construction-material evidence",
                    "description": "Follow what surviving material can establish.",
                    "supporting_source_ids": ["src1"],
                }
            ],
            "visual_opportunities": [
                {
                    "description": "Museum artifact",
                    "supporting_source_ids": ["src1"],
                    "rights_note": "Clear rights",
                }
            ],
            "myths_and_misconceptions": [],
            "controversies_or_uncertainties": [],
            "limitations": ["Read the full record."],
        }
    )


def setup_project(session, *, approved=True, status="PRODUCING_BRIEF", strong=True):
    project = ProjectModel(
        title="The Great Pyramid",
        country="United States",
        language="English",
        category="Documentary",
        target_length="15 Minutes",
        status=status,
    )
    session.add(project)
    session.flush()
    session.add(
        ProjectResearchDossierModel(
            project_id=project.id,
            research_status="APPROVED" if approved else "COMPLETE",
            research_version="research-v1",
            progress=100,
            current_step="COMPLETE",
            sources_found=1,
            facts_verified=1,
            payload=dossier_payload(strong),
            generated_at=datetime.now(UTC),
        )
    )
    session.commit()
    session.refresh(project)
    return project


def test_angle_ordering_and_profitability_are_deterministic() -> None:
    dossier = dossier_payload()
    first = AngleSelector().candidates(dossier)
    assert first == AngleSelector().candidates(dossier)
    assert first[0]["evidence_strength"] >= 85
    result = ProfitabilityRecheck().evaluate(first[0], dossier)
    assert 0 <= result["revised_money_score"] <= 100
    assert result["recommendation"] in {"PROCEED", "PROCEED_WITH_CAUTION"}
    assert result["calculation_trace"]


def test_validator_rejects_unknown_and_unverified_evidence() -> None:
    dossier = dossier_payload()
    fact_id = dossier["key_facts"][0]["id"]
    valid = {
        "selected_fact_ids": [fact_id],
        "selected_source_ids": ["src1"],
        "key_story_beats": [
            {"supporting_fact_ids": [fact_id], "supporting_source_ids": ["src1"]}
        ],
    }
    validate_brief(valid, dossier)
    with pytest.raises(BriefValidationError, match="Unknown fact"):
        validate_brief({**valid, "selected_fact_ids": ["invented"]}, dossier)
    with pytest.raises(BriefValidationError, match="Unknown source"):
        validate_brief({**valid, "selected_source_ids": ["invented"]}, dossier)
    dossier["key_facts"][0]["verification_status"] = "UNVERIFIED"
    with pytest.raises(BriefValidationError, match="Unverified"):
        validate_brief(valid, dossier)


def test_service_generates_persists_and_transitions(session) -> None:
    project = setup_project(session)
    result = ExecutiveProducerService(session).run(project.id)
    session.refresh(project)
    assert result["brief_status"] in {"COMPLETE", "NEEDS_REVIEW"}
    assert project.status == "BRIEF_COMPLETE"
    brief = (
        session.query(ProjectProductionBriefModel)
        .filter_by(project_id=project.id)
        .one()
    )
    assert brief.payload["selected_fact_ids"]
    assert brief.payload["key_story_beats"]
    assert brief.payload["calculation_trace"]
    dossier = (
        session.query(ProjectResearchDossierModel)
        .filter_by(project_id=project.id)
        .one()
    )
    fact_id = dossier.payload["key_facts"][0]["id"]
    assert fact_id in brief.payload["selected_fact_ids"]


def test_service_rejects_missing_angles(session) -> None:
    project = setup_project(session)
    dossier = (
        session.query(ProjectResearchDossierModel)
        .filter_by(project_id=project.id)
        .one()
    )
    dossier.payload = {**dossier.payload, "story_angles": []}
    session.commit()
    result = ExecutiveProducerService(session).run(project.id)
    session.refresh(project)
    assert result["brief_status"] == "REJECTED"
    assert project.status == "PROJECT_REJECTED"


def test_service_requires_approved_research_and_valid_state(session) -> None:
    project = setup_project(session, approved=False)
    with pytest.raises(ValueError, match="Approved research"):
        ExecutiveProducerService(session).run(project.id)
    other = setup_project(session, status="RESEARCH_COMPLETE")
    with pytest.raises(ValueError, match="RESEARCH_COMPLETE"):
        ExecutiveProducerService(session).run(other.id)


def test_api_start_status_retrieve_and_approve(session, monkeypatch) -> None:
    project = setup_project(session, status="RESEARCH_COMPLETE")
    monkeypatch.setattr(
        "backend.app.api.v1.production_briefs.run_executive_producer.delay",
        lambda _id: type("Task", (), {"id": "producer-task"})(),
    )
    app = create_application()
    app.dependency_overrides[get_db] = lambda: session
    client = TestClient(app)
    started = client.post(f"/api/v1/projects/{project.id}/production-brief/start")
    assert started.json()["task_id"] == "producer-task"
    assert (
        client.get(f"/api/v1/projects/{project.id}/production-brief/status").json()[
            "brief_status"
        ]
        == "PENDING"
    )
    ExecutiveProducerService(session).run(project.id)
    fetched = client.get(f"/api/v1/projects/{project.id}/production-brief")
    assert fetched.status_code == 200
    approved = client.post(f"/api/v1/projects/{project.id}/production-brief/approve")
    assert approved.json()["status"] == "APPROVED"
    session.refresh(project)
    assert project.status == "BRIEF_APPROVED"
    assert (
        client.post(
            f"/api/v1/projects/{project.id}/production-brief/approve"
        ).status_code
        == 409
    )


def test_api_guards_missing_and_unapproved(session) -> None:
    client = TestClient(create_application())
    client.app.dependency_overrides[get_db] = lambda: session
    assert (
        client.post("/api/v1/projects/missing/production-brief/start").status_code
        == 404
    )
    project = setup_project(session, approved=False, status="RESEARCH_COMPLETE")
    assert (
        client.post(f"/api/v1/projects/{project.id}/production-brief/start").status_code
        == 409
    )
