"""Validate citations and uncertainty boundaries after generation."""

from typing import Any


class ScriptValidationError(ValueError):
    pass


UNCERTAINTY_TERMS = (
    "disputed",
    "researchers disagree",
    "does not settle",
    "one interpretation suggests",
    "remains uncertain",
)


def validate_script(
    payload: dict[str, Any], brief: dict[str, Any], dossier: dict[str, Any]
) -> None:
    fact_map = {
        fact["id"]: fact
        for section in ("key_facts", "interesting_facts")
        for fact in dossier.get(section, [])
    }
    source_ids = {source["id"] for source in dossier.get("sources", [])}
    selected_facts = set(brief.get("selected_fact_ids", []))
    selected_sources = set(brief.get("selected_source_ids", []))
    mapped_segments = {item["segment_id"] for item in payload.get("citation_map", [])}
    for section in payload.get("sections", []):
        if section.get("is_factual") and section.get("id") not in mapped_segments:
            raise ScriptValidationError("Factual segment has no citation mapping")
    for citation in payload.get("citation_map", []):
        facts = set(citation.get("fact_ids", []))
        sources = set(citation.get("source_ids", []))
        if facts - set(fact_map) or facts - selected_facts:
            raise ScriptValidationError("Citation uses an unknown or unselected fact")
        if sources - source_ids or sources - selected_sources:
            raise ScriptValidationError("Citation uses an unknown or unselected source")
        for fact_id in facts:
            fact = fact_map[fact_id]
            status = fact.get("verification_status")
            if status == "UNVERIFIED":
                raise ScriptValidationError("Unverified fact used")
            if status == "CONFLICTING" and not any(
                term in citation.get("text_excerpt", "").lower()
                for term in UNCERTAINTY_TERMS
            ):
                raise ScriptValidationError("Conflicting fact is not qualified")
