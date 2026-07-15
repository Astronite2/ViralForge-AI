# ruff: noqa: E501
"""Research gap, expansion, version, and stale-artifact coverage."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.models.production_brief import ProjectProductionBriefModel
from backend.app.models.project import ProjectModel
from backend.app.models.research import ProjectResearchDossierModel
from backend.app.models.script import ProjectScriptModel
from backend.app.research.expansion_service import ResearchExpansionService
from backend.app.research.gap_analyzer import ResearchGapAnalyzer
from backend.app.research.providers.base import SearchResult


def source(number: int, quality: str = "AUTHORITATIVE") -> dict[str, object]:
    return {
        "id": f"src{number}",
        "title": f"Source {number}",
        "url": f"https://university.edu/{number}",
        "publisher": "University",
        "domain": "university.edu",
        "excerpt": f"Supported evidence {number}",
        "source_type": "academic",
        "source_quality": quality,
        "authority_reason": "Academic domain",
        "publication_date": None,
        "retrieved_at": datetime.now(UTC).isoformat(),
        "relevance": 0.9,
    }


def fact(number: int) -> dict[str, object]:
    return {
        "id": f"fact{number}",
        "claim": f"Supported claim {number}",
        "supporting_source_ids": [f"src{number}"],
        "confidence": 0.8,
        "verification_status": "SUPPORTED",
        "notes": "Source-grounded",
    }


def payload(count: int = 1) -> dict[str, object]:
    return {
        "research_version": "research-v1",
        "key_facts": [fact(i) for i in range(count)],
        "interesting_facts": [],
        "sources": [source(i) for i in range(count)],
        "story_angles": [
            {
                "title": "Evidence angle",
                "description": "Follow evidence",
                "supporting_source_ids": ["src0"],
            }
        ],
        "visual_opportunities": [],
        "open_questions": ["What construction evidence survives?"],
        "limitations": ["Chronology needs expansion"],
    }


def brief_payload() -> dict[str, object]:
    return {
        "target_duration_minutes": 15,
        "selected_fact_ids": ["fact0"],
        "selected_source_ids": ["src0"],
        "key_story_beats": [
            {
                "name": "Context",
                "supporting_fact_ids": ["fact0"],
                "supporting_source_ids": ["src0"],
            },
            {
                "name": "Investigation",
                "supporting_fact_ids": [],
                "supporting_source_ids": [],
            },
        ],
    }


class FixtureProvider:
    name = "fixture"

    def search(self, query: str, *, limit: int) -> list[SearchResult]:
        identity = abs(hash(query)) % 100000
        return [
            SearchResult(
                title=f"Academic {identity}",
                url=f"https://archive.edu/{identity}",
                publisher="Archive University",
                excerpt=f"Documented evidence for {query}",
                source_type="peer_reviewed",
                retrieved_at=datetime.now(UTC),
                relevance=0.9,
            )
        ]


class FailedProvider:
    name = "failed"

    def search(self, query: str, *, limit: int) -> list[SearchResult]:
        raise RuntimeError("provider unavailable")


def records(session):
    project = ProjectModel(
        title="The Great Pyramid",
        country="United States",
        language="English",
        category="Documentary",
        target_length="15 minutes",
        status="SCRIPTING",
    )
    session.add(project)
    session.flush()
    dossier = ProjectResearchDossierModel(
        project_id=project.id,
        research_status="APPROVED",
        research_version="research-v1",
        progress=100,
        current_step="COMPLETE",
        sources_found=1,
        facts_verified=1,
        payload=payload(),
    )
    brief = ProjectProductionBriefModel(
        project_id=project.id,
        status="APPROVED",
        version="brief-v1",
        research_version_used="research-v1",
        current_step="COMPLETE",
        payload=brief_payload(),
    )
    script = ProjectScriptModel(
        project_id=project.id,
        status="NEEDS_REVIEW",
        version="script-v1",
        research_version_used="research-v1",
        production_brief_version_used="brief-v1",
        current_step="EVIDENCE_INSUFFICIENT",
        target_word_count=2175,
        actual_word_count=0,
        payload={},
    )
    session.add_all([dossier, brief, script])
    session.commit()
    return project, dossier, brief, script


def test_gap_analyzer_reports_focused_shortfall():
    result = ResearchGapAnalyzer().analyze(
        topic="The Great Pyramid",
        dossier=payload(),
        brief=brief_payload(),
        target_duration=15,
    )
    assert result["missing_facts"] == 11
    assert result["missing_sources"] == 6
    assert result["missing_authoritative_sources"] == 2
    assert result["unsupported_beats"] == ["Investigation"]
    assert "construction evidence" in result["proposed_focus_areas"]
    assert all(
        "The Great Pyramid" in query for query in result["proposed_search_queries"]
    )
    assert result["recommended_max_duration_minutes"] == 3


def test_expansion_merges_versions_and_marks_downstream_stale(session):
    project, dossier, brief, script = records(session)
    result = ResearchExpansionService(session, FixtureProvider()).run(
        project.id, target_duration=15, max_additional_sources=20
    )
    session.refresh(dossier)
    session.refresh(brief)
    session.refresh(script)
    assert result["new_dossier_version"] == "research-v2"
    assert result["sources_added"] > 0 and result["facts_added"] > 0
    assert dossier.research_status == "NEEDS_REVIEW"
    assert dossier.payload["expansion_history"][-1]["queries_executed"]
    assert brief.status == "STALE" and script.status == "STALE"
    assert brief.approved_at is None and script.approved_at is None


def test_failed_expansion_preserves_approved_dossier(session):
    project, dossier, brief, script = records(session)
    before = dossier.payload.copy()
    try:
        ResearchExpansionService(session, FailedProvider()).run(project.id)
    except RuntimeError:
        pass
    session.refresh(dossier)
    assert dossier.research_version == "research-v1"
    assert dossier.research_status == "APPROVED"
    assert dossier.payload == before
    assert brief.status == "APPROVED" and script.status == "NEEDS_REVIEW"


def test_gap_api(session):
    project, *_ = records(session)
    app.dependency_overrides[get_db] = lambda: session
    response = TestClient(app).get(f"/api/v1/projects/{project.id}/research/gaps")
    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["missing_facts"] == 11
