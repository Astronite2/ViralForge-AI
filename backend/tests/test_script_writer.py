"""Evidence-gated source-grounded Script Writer tests."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from backend.app.db.session import get_db
from backend.app.main import create_application
from backend.app.models.production_brief import ProjectProductionBriefModel
from backend.app.models.project import ProjectModel
from backend.app.models.research import ProjectResearchDossierModel
from backend.app.models.script import ProjectScriptModel
from backend.app.script.context_builder import build_context
from backend.app.script.evidence_coverage import EvidenceCoverage
from backend.app.script.script_builder import ScriptBuilder
from backend.app.script.script_validator import ScriptValidationError, validate_script
from backend.app.script.service import ProjectScriptService


def evidence(count=12, sources=7, authoritative=3):
    source_rows = [
        {
            "id": f"src{i}",
            "title": f"Source {i}",
            "source_quality": (
                "AUTHORITATIVE" if i < authoritative else "GENERAL_REFERENCE"
            ),
        }
        for i in range(sources)
    ]
    facts = [
        {
            "id": f"fact{i}",
            "claim": f"Approved evidence statement {i}.",
            "supporting_source_ids": [f"src{i%sources}"],
            "confidence": 0.8,
            "verification_status": "SUPPORTED",
            "notes": "Approved",
        }
        for i in range(count)
    ]
    dossier = {
        "key_facts": facts[:6],
        "interesting_facts": facts[6:],
        "sources": source_rows,
        "limitations": ["Read full sources."],
    }
    beats = [
        {
            "name": f"Beat {i}",
            "supporting_fact_ids": [f"fact{i}"],
            "supporting_source_ids": [f"src{i%sources}"],
        }
        for i in range(min(count, 8))
    ]
    brief = {
        "opening_hook": "What does the approved evidence establish?",
        "target_duration_minutes": 15,
        "selected_fact_ids": [f"fact{i}" for i in range(count)],
        "selected_source_ids": [f"src{i}" for i in range(sources)],
        "key_story_beats": beats,
    }
    return dossier, brief


def setup(session, *, count=12, sources=7, authoritative=3, status="SCRIPTING"):
    dossier, brief = evidence(count, sources, authoritative)
    project = ProjectModel(
        title="The Great Pyramid",
        country="US",
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
            research_status="APPROVED",
            research_version="research-v1",
            progress=100,
            current_step="COMPLETE",
            sources_found=sources,
            facts_verified=count,
            payload=dossier,
        )
    )
    session.add(
        ProjectProductionBriefModel(
            project_id=project.id,
            status="APPROVED",
            version="producer-v1",
            current_step="COMPLETE",
            candidate_angles_generated=3,
            payload=brief,
            approved_at=datetime.now(UTC),
        )
    )
    session.commit()
    session.refresh(project)
    return project, dossier, brief


@pytest.mark.parametrize(
    ("duration", "facts", "sources", "authority"),
    [(5, 4, 3, 1), (10, 8, 5, 2), (15, 12, 7, 3)],
)
def test_evidence_thresholds(duration, facts, sources, authority):
    dossier, brief = evidence(facts, sources, authority)
    brief["target_duration_minutes"] = duration
    assert (
        EvidenceCoverage().evaluate(duration=duration, brief=brief, dossier=dossier)[
            "status"
        ]
        == "SUFFICIENT"
    )


def test_insufficient_evidence_recommends_shorter_video():
    dossier, brief = evidence(1, 1, 1)
    report = EvidenceCoverage().evaluate(duration=15, brief=brief, dossier=dossier)
    assert report["status"] == "INSUFFICIENT"
    assert report["available_facts"] == 1
    assert "reduce" in report["recommended_action"].lower()


def test_context_contains_only_selected_approved_evidence():
    dossier, brief = evidence()
    brief["selected_fact_ids"] = ["fact2"]
    brief["selected_source_ids"] = ["src2"]
    context = build_context(brief, dossier)
    assert [fact["id"] for fact in context["facts"]] == ["fact2"]
    assert [source["id"] for source in context["sources"]] == ["src2"]


def test_validator_rejects_unknown_and_uncited_segments():
    dossier, brief = evidence()
    context = build_context(brief, dossier)
    payload = ScriptBuilder().build(
        project=type("P", (), {"title": "Pyramid"})(),
        brief=brief,
        context=context,
        target_words=2175,
        coverage={"target_duration_minutes": 15},
    )
    validate_script(payload, brief, dossier)
    payload["citation_map"][0]["fact_ids"] = ["invented"]
    with pytest.raises(ScriptValidationError):
        validate_script(payload, brief, dossier)
    payload = ScriptBuilder().build(
        project=type("P", (), {"title": "Pyramid"})(),
        brief=brief,
        context=context,
        target_words=2175,
        coverage={"target_duration_minutes": 15},
    )
    payload["citation_map"] = []
    with pytest.raises(ScriptValidationError, match="no citation"):
        validate_script(payload, brief, dossier)


def test_service_blocks_thin_great_pyramid_evidence_without_narration(session):
    project, _, _ = setup(session, count=1, sources=1, authoritative=1)
    result = ProjectScriptService(session).run(project.id)
    script = session.query(ProjectScriptModel).filter_by(project_id=project.id).one()
    assert result["script_status"] == "NEEDS_REVIEW"
    assert script.evidence_sufficiency == "INSUFFICIENT"
    assert script.payload["full_script"] == ""
    session.refresh(project)
    assert project.status == "SCRIPTING"


def test_service_generates_grounded_script_and_transitions(session):
    project, dossier, brief = setup(session)
    result = ProjectScriptService(session).run(project.id)
    script = session.query(ProjectScriptModel).filter_by(project_id=project.id).one()
    assert result["script_status"] == "COMPLETE"
    assert script.actual_word_count > 0
    assert script.payload["citation_map"]
    validate_script(script.payload, brief, dossier)
    session.refresh(project)
    assert project.status == "SCRIPT_COMPLETE"


def test_five_minute_fallback_is_within_word_tolerance(session):
    project, dossier, brief = setup(session)
    stored = (
        session.query(ProjectProductionBriefModel)
        .filter_by(project_id=project.id)
        .one()
    )
    stored.payload = {**stored.payload, "target_duration_minutes": 5}
    session.commit()
    ProjectScriptService(session).run(project.id)
    script = session.query(ProjectScriptModel).filter_by(project_id=project.id).one()
    tolerance = script.target_word_count * 0.10
    assert abs(script.actual_word_count - script.target_word_count) <= tolerance
    validate_script(script.payload, brief, dossier)


def test_service_requires_approved_prerequisites(session):
    project, _, _ = setup(session, status="BRIEF_APPROVED")
    with pytest.raises(ValueError, match="BRIEF_APPROVED"):
        ProjectScriptService(session).run(project.id)


def test_script_api_start_status_retrieve_approve(session, monkeypatch):
    project, _, _ = setup(session, status="BRIEF_APPROVED")
    monkeypatch.setattr(
        "backend.app.api.v1.scripts.run_project_script.delay",
        lambda _id: type("Task", (), {"id": "script-task"})(),
    )
    app = create_application()
    app.dependency_overrides[get_db] = lambda: session
    client = TestClient(app)
    assert (
        client.post(f"/api/v1/projects/{project.id}/script/start").json()["task_id"]
        == "script-task"
    )
    ProjectScriptService(session).run(project.id)
    assert client.get(f"/api/v1/projects/{project.id}/script").status_code == 200
    approved = client.post(f"/api/v1/projects/{project.id}/script/approve")
    assert approved.json()["status"] == "APPROVED"
    session.refresh(project)
    assert project.status == "SCRIPT_APPROVED"
