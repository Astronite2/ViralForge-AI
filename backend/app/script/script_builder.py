# ruff: noqa: E501
"""Deterministic narration draft from approved evidence only."""

from typing import Any

from backend.app.script.retention_planner import retention_devices

ACTS = [
    "Act 1 — Context",
    "Act 2 — Core Question",
    "Act 3 — Evidence and Investigation",
    "Act 4 — Conflict or Alternative Interpretation",
    "Act 5 — Best-Supported Conclusion",
]


class ScriptBuilder:
    def build(
        self,
        *,
        project: Any,
        brief: dict[str, Any],
        context: dict[str, Any],
        target_words: int,
        coverage: dict[str, Any],
    ) -> dict[str, Any]:
        opening = str(
            brief.get("opening_hook")
            or "What can the surviving evidence actually establish?"
        )
        introduction = f"This documentary follows the approved evidence behind {project.title}. We will separate what the cited material supports from interpretation, and we will keep unresolved questions qualified."
        sections = []
        citations = []
        source_map = {source["id"]: source for source in context["sources"]}
        for index, fact in enumerate(context["facts"]):
            segment_id = f"evidence-{index+1}"
            status = fact.get("verification_status", "SUPPORTED")
            qualifier = (
                "The surviving evidence does not settle every interpretation. "
                if status == "CONFLICTING"
                else ""
            )
            text = f"{qualifier}{fact['claim']} This evidence is included because it appears in the approved dossier. Its source should be reviewed in full before recording, and it does not by itself support claims beyond the wording presented here."
            source_ids = [
                sid
                for sid in fact.get("supporting_source_ids", [])
                if sid in source_map
            ]
            sections.append(
                {
                    "id": segment_id,
                    "heading": ACTS[index % len(ACTS)],
                    "narration": text,
                    "transition": "With that evidence established, we can test the next part of the documentary question.",
                    "is_factual": True,
                    "fact_ids": [fact["id"]],
                    "source_ids": source_ids,
                    "visual_cue": "Show the cited source or an original explanatory visual after rights review.",
                    "production_note": "Verify the full linked source and pronunciation before recording.",
                }
            )
            citations.append(
                {
                    "segment_id": segment_id,
                    "text_excerpt": text[:240],
                    "fact_ids": [fact["id"]],
                    "source_ids": source_ids,
                    "verification_status": status,
                }
            )
        ending = "The approved evidence gives us a bounded conclusion, not permission to overstate what remains uncertain. The strongest next step is to return to the cited material and distinguish evidence from storytelling framing."
        cta = "Which part of the evidence should a future investigation examine more closely?"
        full = self._full(opening, introduction, sections, ending, cta)
        minimum_words = round(target_words * 0.9)
        if len(full.split()) < minimum_words:
            for index, section in enumerate(sections):
                source = (
                    source_map.get(section["source_ids"][0])
                    if section["source_ids"]
                    else None
                )
                if source:
                    provenance = (
                        f"The dossier traces this evidence to {source.get('title', 'the cited record')} "
                        f"from {source.get('publisher', source.get('domain', 'the linked publisher'))}. "
                        "Consulting that complete record is necessary to preserve its context and evidentiary limits."
                    )
                    section["narration"] = f"{section['narration']} {provenance}"
                    citations[index]["text_excerpt"] = section["narration"][:240]
                    full = self._full(opening, introduction, sections, ending, cta)
                    if len(full.split()) >= minimum_words:
                        break
        full = self._full(opening, introduction, sections, ending, cta)
        actual = len(full.split())
        return {
            "title": project.title,
            "script_type": "documentary",
            "target_duration_minutes": coverage["target_duration_minutes"],
            "target_word_count": target_words,
            "actual_word_count": actual,
            "estimated_duration_minutes": round(actual / 145, 1),
            "opening_hook": opening,
            "introduction": introduction,
            "sections": sections,
            "ending": ending,
            "call_to_action": cta,
            "full_script": full,
            "citation_map": citations,
            "fact_usage_map": {
                fact["id"]: [f"evidence-{index+1}"]
                for index, fact in enumerate(context["facts"])
            },
            "source_usage_map": {
                source["id"]: [
                    citation["segment_id"]
                    for citation in citations
                    if source["id"] in citation["source_ids"]
                ]
                for source in context["sources"]
            },
            "unsupported_claims": [],
            "disputed_claims": [
                fact["id"]
                for fact in context["facts"]
                if fact.get("verification_status") == "CONFLICTING"
            ],
            "factual_warnings": [
                "Read every linked source in full before recording.",
                "The deterministic fallback may be shorter than the target narration length; it never pads thin evidence.",
            ],
            "production_notes": [
                "Narration is a structured evidence draft; editorial polish remains required."
            ],
            "pronunciation_notes": [
                "Confirm all names and locations against authoritative sources."
            ],
            "visual_cues": [section["visual_cue"] for section in sections],
            "retention_devices": retention_devices(),
            "limitations": context["limitations"],
            "evidence_coverage": coverage,
            "research_version_used": brief.get("research_version_used"),
        }

    @staticmethod
    def _full(
        opening: str,
        introduction: str,
        sections: list[dict[str, Any]],
        ending: str,
        cta: str,
    ) -> str:
        return "\n\n".join(
            [
                opening,
                introduction,
                *[
                    f"{section['heading']}\n{section['narration']}\n{section['transition']}"
                    for section in sections
                ],
                ending,
                cta,
            ]
        )
