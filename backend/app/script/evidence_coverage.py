# ruff: noqa: E501
"""Versioned duration-to-evidence sufficiency gate."""

from typing import Any

THRESHOLDS = ((5, 4, 3, 1), (10, 8, 5, 2), (15, 12, 7, 3), (20, 16, 9, 4))


class EvidenceCoverage:
    def evaluate(
        self, *, duration: int, brief: dict[str, Any], dossier: dict[str, Any]
    ) -> dict[str, Any]:
        threshold = next(
            (row for row in THRESHOLDS if duration <= row[0]), THRESHOLDS[-1]
        )
        _, required_facts, required_sources, required_authority = threshold
        fact_map = {
            fact["id"]: fact
            for section in ("key_facts", "interesting_facts")
            for fact in dossier.get(section, [])
        }
        source_map = {source["id"]: source for source in dossier.get("sources", [])}
        facts = [
            fact_map[fid]
            for fid in brief.get("selected_fact_ids", [])
            if fid in fact_map
            and fact_map[fid].get("verification_status") != "UNVERIFIED"
        ]
        sources = [
            source_map[sid]
            for sid in brief.get("selected_source_ids", [])
            if sid in source_map
        ]
        authoritative = sum(
            source.get("source_quality") in {"PRIMARY", "AUTHORITATIVE"}
            for source in sources
        )
        beats = brief.get("key_story_beats", [])
        supported_beats = sum(
            bool(beat.get("supporting_fact_ids") and beat.get("supporting_source_ids"))
            for beat in beats
        )
        unsupported_beats = len(beats) - supported_beats
        ratios = [
            len(facts) / required_facts,
            len(sources) / required_sources,
            authoritative / required_authority,
        ]
        status = (
            "SUFFICIENT"
            if min(ratios) >= 1 and supported_beats >= 3
            else (
                "LIMITED"
                if min(ratios) >= 0.75 and supported_beats >= 2
                else "INSUFFICIENT"
            )
        )
        shorter = max(
            (
                minutes
                for minutes, facts_needed, sources_needed, auth_needed in THRESHOLDS
                if len(facts) >= facts_needed
                and len(sources) >= sources_needed
                and authoritative >= auth_needed
            ),
            default=0,
        )
        action = (
            "Generate the evidence-bounded script."
            if status == "SUFFICIENT"
            else f"Expand approved research or reduce the target to {shorter or 3} minutes."
        )
        return {
            "target_duration_minutes": duration,
            "required_facts": required_facts,
            "available_facts": len(facts),
            "required_sources": required_sources,
            "available_sources": len(sources),
            "required_authoritative_sources": required_authority,
            "available_authoritative_sources": authoritative,
            "supported_narrative_beats": supported_beats,
            "unsupported_narrative_beats": unsupported_beats,
            "evidence_diversity": len(
                {source.get("source_quality") for source in sources}
            ),
            "status": status,
            "recommended_action": action,
            "recommended_max_duration_minutes": shorter or 3,
        }
