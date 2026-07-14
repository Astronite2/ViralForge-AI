"""Production project workflow tests."""

from fastapi.testclient import TestClient

from backend.app.db.session import get_db
from backend.app.main import create_application


def _client(session):
    app = create_application()
    app.dependency_overrides[get_db] = lambda: session
    return TestClient(app)


def test_create_get_and_start_research(session) -> None:
    client = _client(session)
    response = client.post(
        "/api/v1/projects",
        json={
            "title": "The Great Pyramid",
            "country": "United States",
            "language": "English",
            "category": "Documentary",
            "target_length": "15 Minutes",
        },
    )
    assert response.status_code == 201
    project = response.json()
    assert project["status"] == "CREATED"
    assert client.get(f"/api/v1/projects/{project['id']}").json() == project
    started = client.post(f"/api/v1/projects/{project['id']}/research/start")
    assert started.status_code == 200
    assert started.json()["status"] == "RESEARCHING"


def test_project_validation_and_transition_guards(session) -> None:
    client = _client(session)
    assert client.post("/api/v1/projects", json={}).status_code == 422
    assert client.get("/api/v1/projects/missing").status_code == 404
    created = client.post(
        "/api/v1/projects",
        json={
            "title": "History",
            "country": "United States",
            "language": "English",
            "category": "Documentary",
            "target_length": "15 Minutes",
        },
    ).json()
    url = f"/api/v1/projects/{created['id']}/research/start"
    assert client.post(url).status_code == 200
    repeated = client.post(url)
    assert repeated.status_code == 409
    assert repeated.json()["detail"] == "Research cannot start from status RESEARCHING"
