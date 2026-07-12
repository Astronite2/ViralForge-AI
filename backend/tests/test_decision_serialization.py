"""Decision schema serialization tests."""

from backend.app.schemas.decision import DecisionRead
from backend.app.services.decision import DecisionService


def test_decision_serializes_with_evidence_and_explanations() -> None:
    serialized = DecisionRead.model_validate(DecisionService().demo())

    payload = serialized.model_dump(mode="json")
    assert payload["decision_type"] in {"create", "review", "wait", "ignore"}
    assert len(payload["evidence"]) == 7
    assert len(payload["explanations"]) == 7
