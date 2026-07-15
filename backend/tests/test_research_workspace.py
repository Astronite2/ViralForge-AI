"""Source collection, grounding, dossier, service, and research API tests."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from backend.app.db.session import get_db
from backend.app.main import create_application
from backend.app.models.project import ProjectModel
from backend.app.models.research import ProjectResearchDossierModel
from backend.app.research.dossier_builder import DossierBuilder
from backend.app.research.fact_validator import validate_fact
from backend.app.research.providers.base import ResearchProviderError, SearchResult
from backend.app.research.service import ProjectResearchService
from backend.app.research.source_collector import (
    SourceCollector,
    SourceQuality,
    classify_source,
)


class FixtureProvider:
    name = "fixture"

    def search(self, query: str, *, limit: int) -> list[SearchResult]:
        return [
            SearchResult(
                title="Great Pyramid",
                url="https://www.si.edu/pyramid",
                publisher="Smithsonian",
                excerpt=(
                    "The Great Pyramid was constructed during Egypt's Fourth Dynasty."
                ),
                source_type="museum",
                retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
                relevance=0.9,
            )
        ]


class FailingProvider:
    name = "failure"

    def search(self, query: str, *, limit: int) -> list[SearchResult]:
        raise ResearchProviderError("provider unavailable")


def _project(session, status="RESEARCHING"):
    project = ProjectModel(
        title="The Great Pyramid",
        country="United States",
        language="English",
        category="Documentary",
        target_length="15 Minutes",
        status=status,
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def test_quality_classification_and_deduplication() -> None:
    source = FixtureProvider().search("pyramid", limit=5)[0]
    quality, reason = classify_source(source)
    assert quality == SourceQuality.AUTHORITATIVE
    assert "academic" in reason.lower() or "institution" in reason.lower()
    collected = SourceCollector(FixtureProvider(), max_sources=2).collect(
        ["one", "two"]
    )
    assert len(collected) == 1
    assert collected[0]["source_quality"] == "AUTHORITATIVE"
    assert "api" not in str(collected).lower()


def test_low_quality_source_is_not_misrepresented() -> None:
    result = SearchResult(
        title="Post",
        url="https://unknown.example/post",
        publisher="",
        excerpt="claim",
        source_type="blog",
        retrieved_at=datetime.now(UTC),
    )
    quality, reason = classify_source(result)
    assert quality == SourceQuality.LOW_CONFIDENCE
    assert "no deterministic" in reason.lower()


def test_fact_grounding_rejects_missing_or_invented_citations() -> None:
    supported = {
        "claim": "A claim",
        "supporting_source_ids": ["src_1"],
        "confidence": 0.8,
        "verification_status": "SUPPORTED",
    }
    assert validate_fact(supported, {"src_1"}) == supported
    assert (
        validate_fact({**supported, "supporting_source_ids": ["invented"]}, {"src_1"})
        is None
    )
    assert (
        validate_fact({**supported, "verification_status": "UNVERIFIED"}, {"src_1"})
        is None
    )


def test_dossier_is_deterministic_and_cited() -> None:
    sources = SourceCollector(FixtureProvider(), max_sources=3).collect(["pyramid"])
    dossier = DossierBuilder().build(topic="The Great Pyramid", sources=sources)
    assert dossier["key_facts"][0]["supporting_source_ids"] == [sources[0]["id"]]
    assert dossier["timeline"] == []
    assert dossier["limitations"]
    assert "internal knowledge" not in str(dossier)


def test_successful_and_failed_research_state(session) -> None:
    project = _project(session)
    result = ProjectResearchService(session, FixtureProvider()).run(project.id)
    session.refresh(project)
    assert result["research_status"] == "COMPLETE"
    assert project.status == "RESEARCH_COMPLETE"
    dossier = (
        session.query(ProjectResearchDossierModel)
        .filter_by(project_id=project.id)
        .one()
    )
    assert dossier.facts_verified == 1

    failed_project = _project(session)
    try:
        ProjectResearchService(session, FailingProvider()).run(failed_project.id)
    except ResearchProviderError:
        pass
    failed = (
        session.query(ProjectResearchDossierModel)
        .filter_by(project_id=failed_project.id)
        .one()
    )
    assert failed.research_status == "FAILED"
    assert failed_project.status == "RESEARCHING"


def test_invalid_state_rejected(session) -> None:
    project = _project(session, "CREATED")
    try:
        ProjectResearchService(session, FixtureProvider()).run(project.id)
    except ValueError as exc:
        assert "CREATED" in str(exc)
    else:
        raise AssertionError("invalid state accepted")


def test_status_dossier_and_approval_api(session, monkeypatch) -> None:
    app = create_application()
    app.dependency_overrides[get_db] = lambda: session
    monkeypatch.setattr(
        "backend.app.api.v1.projects.run_project_research.delay",
        lambda _id: type("Task", (), {"id": "task-1"})(),
    )
    client = TestClient(app)
    project = client.post(
        "/api/v1/projects",
        json={
            "title": "The Great Pyramid",
            "country": "United States",
            "language": "English",
            "category": "Documentary",
            "target_length": "15 Minutes",
        },
    ).json()
    assert (
        client.post(f"/api/v1/projects/{project['id']}/research/start").status_code
        == 200
    )
    assert (
        client.get(f"/api/v1/projects/{project['id']}/research/status").json()[
            "research_status"
        ]
        == "PENDING"
    )
    assert client.get(f"/api/v1/projects/{project['id']}/research").status_code == 409
    ProjectResearchService(session, FixtureProvider()).run(project["id"])
    dossier = client.get(f"/api/v1/projects/{project['id']}/research")
    assert dossier.status_code == 200
    assert dossier.json()["dossier"]["key_facts"][0]["supporting_source_ids"]
    approved = client.post(f"/api/v1/projects/{project['id']}/research/approve")
    assert approved.json()["research_status"] == "APPROVED"
    assert (
        client.post(f"/api/v1/projects/{project['id']}/research/approve").status_code
        == 409
    )
