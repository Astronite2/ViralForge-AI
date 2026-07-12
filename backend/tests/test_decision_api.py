"""Decision Engine endpoint tests."""

from fastapi.testclient import TestClient

from backend.app.main import app


def test_decision_demo_returns_traceable_response() -> None:
    response = TestClient(app).get("/decision/demo")

    assert response.status_code == 200
    payload = response.json()
    assert payload["evidence"]
    assert payload["explanations"]
