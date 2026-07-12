"""Content normalizer tests."""

from datetime import UTC, datetime
from typing import Any

from backend.app.pipeline.normalizer import ContentNormalizer


def test_normalizer_creates_platform_independent_content(
    raw_content: dict[str, Any],
) -> None:
    content = ContentNormalizer().normalize(raw_content)

    assert content.id == "youtube:abc123"
    assert content.platform == "youtube"
    assert content.published_at == datetime(2026, 1, 1, tzinfo=UTC)
    assert content.metrics == {"views": 100.0}
