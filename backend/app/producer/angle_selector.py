# ruff: noqa: E501
"""Deterministic, evidence-bounded production-angle selection."""

from typing import Any


class AngleSelector:
    def candidates(self, dossier: dict[str, Any]) -> list[dict[str, Any]]:
        sources = {source["id"]: source for source in dossier.get("sources", [])}
        facts = [
            fact
            for section in ("key_facts", "interesting_facts")
            for fact in dossier.get(section, [])
            if fact.get("verification_status") != "UNVERIFIED"
        ]
        candidates = []
        for index, angle in enumerate(dossier.get("story_angles", [])[:5]):
            source_ids = [
                sid for sid in angle.get("supporting_source_ids", []) if sid in sources
            ]
            matching = [
                fact
                for fact in facts
                if set(fact.get("supporting_source_ids", [])) & set(source_ids)
            ]
            quality = max(
                (
                    self._quality(sources[sid].get("source_quality"))
                    for sid in source_ids
                ),
                default=0,
            )
            visual = any(
                set(item.get("supporting_source_ids", [])) & set(source_ids)
                for item in dossier.get("visual_opportunities", [])
            )
            evidence = min(100, quality + len(matching) * 8)
            difficulty = min(85, 48 + index * 7 + (8 if visual else 0))
            confidence = round(evidence * 0.7 + (75 if visual else 40) * 0.3, 1)
            candidates.append(
                {
                    "title": angle.get("title", "Evidence-led investigation"),
                    "angle": angle.get(
                        "description", "Investigate the strongest supported evidence."
                    ),
                    "viewer_promise": "Follow the surviving evidence and separate what it supports from what remains interpretation.",
                    "evidence_strength": evidence,
                    "visual_potential": 75 if visual else 40,
                    "evergreen_potential": 80,
                    "competition_risk": 50,
                    "production_difficulty": difficulty,
                    "monetization_safety": 90,
                    "confidence": confidence,
                    "supporting_fact_ids": [fact["id"] for fact in matching],
                    "supporting_source_ids": source_ids,
                    "rejection_reasons": (
                        [] if evidence >= 55 else ["Evidence coverage is limited."]
                    ),
                }
            )
        return sorted(
            candidates,
            key=lambda item: (
                -item["confidence"],
                item["production_difficulty"],
                item["title"],
            ),
        )

    @staticmethod
    def _quality(value: object) -> int:
        return {
            "PRIMARY": 90,
            "AUTHORITATIVE": 85,
            "REPUTABLE_SECONDARY": 70,
            "GENERAL_REFERENCE": 45,
            "COMMUNITY": 25,
            "LOW_CONFIDENCE": 10,
        }.get(str(value), 0)
