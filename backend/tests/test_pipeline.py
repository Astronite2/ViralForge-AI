"""Content pipeline tests."""

from typing import Any

from backend.app.pipeline.pipeline import ContentPipeline


def test_pipeline_processes_normalized_content(raw_content: dict[str, Any]) -> None:
    result = ContentPipeline().process(raw_content)

    assert result.persisted_content is None
    assert result.content.metadata["title_length"] == len(raw_content["title"])
    assert result.content.analysis["status"] == "pending"
    assert len(result.content.signals) == 1
    assert result.opportunity.score == 0.0


def test_pipeline_processes_pre_normalized_content(raw_content: dict[str, Any]) -> None:
    from backend.app.pipeline.normalizer import ContentNormalizer

    content = ContentNormalizer().normalize(raw_content)
    result = ContentPipeline().process_normalized(content)

    assert result.content.metadata["title_length"] == len(raw_content["title"])
