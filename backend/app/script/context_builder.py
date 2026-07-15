"""Restrict script context to selected, approved evidence."""

from typing import Any


def build_context(brief: dict[str, Any], dossier: dict[str, Any]) -> dict[str, Any]:
    selected_facts = set(brief.get("selected_fact_ids", []))
    selected_sources = set(brief.get("selected_source_ids", []))
    facts = [
        fact
        for section in ("key_facts", "interesting_facts")
        for fact in dossier.get(section, [])
        if fact.get("id") in selected_facts
        and fact.get("verification_status") != "UNVERIFIED"
    ]
    sources = [
        source
        for source in dossier.get("sources", [])
        if source.get("id") in selected_sources
    ]
    return {
        "facts": sorted(facts, key=lambda fact: fact["id"]),
        "sources": sorted(sources, key=lambda source: source["id"]),
        "beats": brief.get("key_story_beats", []),
        "limitations": dossier.get("limitations", []),
    }
