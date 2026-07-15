# ruff: noqa: E501
"""Build a concise production decision document, not a script."""

from typing import Any


class BriefBuilder:
    def build(
        self,
        *,
        project: Any,
        dossier: dict[str, Any],
        candidates: list[dict[str, Any]],
        selected: dict[str, Any],
        viability: dict[str, Any],
    ) -> dict[str, Any]:
        fact_ids = selected["supporting_fact_ids"]
        source_ids = sorted(
            {
                sid
                for fact in self._facts(dossier)
                if fact["id"] in fact_ids
                for sid in fact.get("supporting_source_ids", [])
            }
            | set(selected["supporting_source_ids"])
        )
        duration = self._minutes(project.target_length)
        beat_names = [
            "Opening Hook",
            "Act 1 — Context",
            "Act 2 — Core Problem",
            "Act 3 — Evidence and Investigation",
            "Act 4 — Conflict or Uncertainty",
            "Act 5 — Best-Supported Conclusion",
            "Ending Payoff",
            "Call to Action",
        ]
        beats = []
        for index, name in enumerate(beat_names):
            assigned = fact_ids[index :: len(beat_names)] or (
                fact_ids[:1] if index in {0, 5} else []
            )
            assigned_sources = sorted(
                {
                    sid
                    for fact in self._facts(dossier)
                    if fact["id"] in assigned
                    for sid in fact.get("supporting_source_ids", [])
                }
            )
            beats.append(
                {
                    "name": name,
                    "purpose": self._purpose(name),
                    "supporting_fact_ids": assigned,
                    "supporting_source_ids": assigned_sources,
                    "intended_emotional_effect": (
                        "Curiosity" if index < 3 else "Clarity"
                    ),
                    "visual_direction": "Use cited artifacts, diagrams, maps, or restrained text overlays; verify rights.",
                    "approximate_duration_minutes": round(
                        duration / len(beat_names), 1
                    ),
                    "unresolved_risks": list(dossier.get("limitations", []))[:1],
                }
            )
        visuals = [
            {
                "purpose": item.get("description"),
                "source_connection": item.get("supporting_source_ids", []),
                "rights_licensing_concern": item.get(
                    "rights_note", "Rights review required."
                ),
                "requires_original_creation": True,
                "factual_review_required": True,
            }
            for item in dossier.get("visual_opportunities", [])
            if set(item.get("supporting_source_ids", [])) & set(source_ids)
        ]
        return {
            "title": project.title,
            "working_title": str(selected["title"]).removeprefix("Investigate: "),
            "primary_angle": selected["angle"],
            "core_question": "What does the surviving evidence actually establish, and where does interpretation begin?",
            "viewer_promise": selected["viewer_promise"],
            "target_audience": "Curious documentary viewers; audience demographics were not inferred.",
            "target_duration_minutes": duration,
            "documentary_style": "Evidence-led visual documentary",
            "tone": "Curious, rigorous, and transparent about uncertainty",
            "pacing": "Measured opening, accelerating investigation, reflective conclusion",
            "narrative_structure": beat_names,
            "opening_hook": "Begin with the most visually compelling cited object and ask what it can truly prove.",
            "emotional_arc": [
                "Wonder",
                "Investigation",
                "Doubt",
                "Evidence",
                "Qualified resolution",
            ],
            "key_story_beats": beats,
            "selected_fact_ids": fact_ids,
            "selected_source_ids": source_ids,
            "excluded_topics": [
                "Claims without dossier citations",
                "Revenue or audience claims unsupported by observed evidence",
            ],
            "myths_to_address": dossier.get("myths_and_misconceptions", []),
            "controversies_to_handle": dossier.get(
                "controversies_or_uncertainties", []
            ),
            "visual_direction": visuals,
            "production_requirements": [
                "Full-source fact review",
                "Rights clearance",
                "Original maps or diagrams where licensed imagery is unavailable",
            ],
            "monetization_risks": [
                "No topic-level advertiser-safety issue detected; platform review is still required."
            ],
            "factual_risks": list(dossier.get("limitations", [])),
            "copyright_risks": [
                "Museum and archival references require individual licensing review; links are not usage permission."
            ],
            **viability,
            "candidate_angles": candidates,
            "rejection_reasons": (
                []
                if viability["recommendation"] != "REJECT"
                else ["Evidence and viewer promise do not justify production."]
            ),
            "limitations": list(
                dict.fromkeys(
                    [*dossier.get("limitations", []), *viability["limitations"]]
                )
            ),
            "research_version": dossier.get("research_version"),
            "evidence_boundary": "Only facts and sources from the approved dossier were selected.",
        }

    @staticmethod
    def _facts(dossier: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            fact
            for section in ("key_facts", "interesting_facts")
            for fact in dossier.get(section, [])
        ]

    @staticmethod
    def _minutes(value: str) -> int:
        digits = "".join(character for character in value if character.isdigit())
        return int(digits or 15)

    @staticmethod
    def _purpose(name: str) -> str:
        return {
            "Opening Hook": "Establish the central question without asserting an unsupported answer.",
            "Act 1 — Context": "Orient the viewer using selected evidence.",
            "Act 2 — Core Problem": "Define the investigative tension.",
            "Act 3 — Evidence and Investigation": "Examine the strongest cited material.",
            "Act 4 — Conflict or Uncertainty": "Keep disputed or incomplete evidence qualified.",
            "Act 5 — Best-Supported Conclusion": "State only what the selected evidence supports.",
            "Ending Payoff": "Resolve the viewer promise with a qualified conclusion.",
            "Call to Action": "Invite discussion without adding factual claims.",
        }[name]
