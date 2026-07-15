"""Deterministic evidence-gap analysis for documentary research expansion."""

from typing import Any

from backend.app.script.evidence_coverage import EvidenceCoverage

CATEGORIES = (
    "historical context",
    "chronology",
    "construction evidence",
    "material evidence",
    "archaeological findings",
    "documented measurements",
    "key people and dynasties",
    "site geography",
    "competing scholarly interpretations",
    "myths and misconceptions",
    "modern experiments and reconstructions",
    "visual evidence",
    "unresolved questions",
)


class ResearchGapAnalyzer:
    def analyze(
        self,
        *,
        topic: str,
        dossier: dict[str, Any],
        brief: dict[str, Any],
        target_duration: int,
        focus_areas: list[str] | None = None,
    ) -> dict[str, Any]:
        coverage = EvidenceCoverage().evaluate(
            duration=target_duration, brief=brief, dossier=dossier
        )
        unsupported = [
            str(beat.get("name", f"Narrative beat {index + 1}"))
            for index, beat in enumerate(brief.get("key_story_beats", []))
            if not (
                beat.get("supporting_fact_ids") and beat.get("supporting_source_ids")
            )
        ]
        chosen = self._focus(dossier, unsupported, focus_areas)
        return {
            "evidence_sufficiency": coverage["status"],
            "missing_facts": max(
                0, coverage["required_facts"] - coverage["available_facts"]
            ),
            "missing_sources": max(
                0, coverage["required_sources"] - coverage["available_sources"]
            ),
            "missing_authoritative_sources": max(
                0,
                coverage["required_authoritative_sources"]
                - coverage["available_authoritative_sources"],
            ),
            "unsupported_beats": unsupported,
            "proposed_focus_areas": chosen,
            "proposed_search_queries": [f"{topic} {area}" for area in chosen],
            "recommended_max_duration_minutes": coverage[
                "recommended_max_duration_minutes"
            ],
            "recommended_action": coverage["recommended_action"],
            "coverage": coverage,
        }

    @staticmethod
    def _focus(
        dossier: dict[str, Any], unsupported: list[str], requested: list[str] | None
    ) -> list[str]:
        if requested:
            allowed = {item.lower(): item for item in CATEGORIES}
            return [
                allowed[item.lower()] for item in requested if item.lower() in allowed
            ][:12]
        text = " ".join(
            [
                *[str(item) for item in unsupported],
                *[str(item) for item in dossier.get("open_questions", [])],
                *[str(item) for item in dossier.get("limitations", [])],
            ]
        ).lower()
        selected = [
            area for area in CATEGORIES if any(word in text for word in area.split())
        ]
        return list(dict.fromkeys([*selected, *CATEGORIES[:9]]))[:12]
