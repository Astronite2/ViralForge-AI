# ruff: noqa: E501
"""Strict production-brief evidence validation."""

import hashlib
from typing import Any


class BriefValidationError(ValueError):
    """Brief references evidence outside the approved dossier."""


def ensure_fact_ids(dossier: dict[str, Any]) -> dict[str, Any]:
    """Add stable identities to legacy dossier facts without changing claims."""
    for section in ("key_facts", "interesting_facts"):
        for fact in dossier.get(section, []):
            if "id" not in fact:
                identity = f"{fact.get('claim','')}|{'|'.join(fact.get('supporting_source_ids', []))}"
                fact["id"] = (
                    "fact_" + hashlib.sha256(identity.encode()).hexdigest()[:12]
                )
    return dossier


def validate_brief(payload: dict[str, Any], dossier: dict[str, Any]) -> None:
    facts = {
        fact["id"]: fact
        for section in ("key_facts", "interesting_facts")
        for fact in dossier.get(section, [])
    }
    sources = {source["id"] for source in dossier.get("sources", [])}
    selected_facts = payload.get("selected_fact_ids", [])
    selected_sources = payload.get("selected_source_ids", [])
    unknown_facts = set(selected_facts) - set(facts)
    unknown_sources = set(selected_sources) - sources
    if unknown_facts:
        raise BriefValidationError(f"Unknown fact IDs: {sorted(unknown_facts)}")
    if unknown_sources:
        raise BriefValidationError(f"Unknown source IDs: {sorted(unknown_sources)}")
    for fact_id in selected_facts:
        status = facts[fact_id].get("verification_status")
        if status == "UNVERIFIED":
            raise BriefValidationError(f"Unverified fact selected: {fact_id}")
        if status == "CONFLICTING" and not facts[fact_id].get("notes"):
            raise BriefValidationError(f"Conflicting fact is not qualified: {fact_id}")
    for beat in payload.get("key_story_beats", []):
        if beat.get("supporting_fact_ids") and not beat.get("supporting_source_ids"):
            raise BriefValidationError("Story beat facts require source references")
        if set(beat.get("supporting_fact_ids", [])) - set(selected_facts):
            raise BriefValidationError("Story beat uses an unselected fact")
        if set(beat.get("supporting_source_ids", [])) - set(selected_sources):
            raise BriefValidationError("Story beat uses an unselected source")
