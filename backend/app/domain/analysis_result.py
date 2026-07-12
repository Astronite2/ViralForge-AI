"""Analysis result domain object."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """Outcome produced by a future analysis workflow."""

    status: str
    summary: str
