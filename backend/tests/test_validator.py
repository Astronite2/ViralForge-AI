"""Content validator tests."""

from typing import Any

import pytest

from backend.app.pipeline.validator import ContentValidator


def test_validator_accepts_complete_content(raw_content: dict[str, Any]) -> None:
    ContentValidator().validate(raw_content)


def test_validator_rejects_missing_required_field(raw_content: dict[str, Any]) -> None:
    del raw_content["title"]

    with pytest.raises(ValueError, match="title"):
        ContentValidator().validate(raw_content)
