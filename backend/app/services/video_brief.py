"""Evidence-linked deterministic fallback production brief generator."""

from typing import Any


class VideoBriefService:
    """Create a usable brief even when AI reasoning is disabled or unavailable."""

    def generate(self, opportunity: dict[str, Any]) -> dict[str, Any]:
        topic = str(opportunity["topic"])
        angle = str(opportunity["proposed_video_angle"])
        evidence = list(opportunity.get("evidence_references", []))[:8]
        duration = "12–16 minutes"
        facts = [
            {
                "research_prompt": (
                    "Verify the claims and context behind competitor title: "
                    f"{item.get('title', 'Untitled')}"
                ),
                "source_url": item.get("url"),
                "content_id": item.get("content_id"),
                "verification_required": True,
            }
            for item in evidence
        ]
        if not facts:
            facts = [
                {
                    "research_prompt": (
                        "Find primary and reputable secondary sources for " f"{topic}."
                    ),
                    "source_url": None,
                    "content_id": None,
                    "verification_required": True,
                }
            ]
        return {
            "recommended_title_options": [
                angle,
                f"{topic}: What Most Videos Miss",
                f"How {topic} Really Works — An Evidence-Led Guide",
            ],
            "primary_angle": angle,
            "target_viewer": f"Curious YouTube viewers actively searching for {topic}.",
            "viewer_promise": (
                "A clear, well-sourced explanation that adds a distinct angle "
                "to current results."
            ),
            "hook_options": [
                f"Most explanations of {topic} skip one crucial detail.",
                f"The popular version of {topic} is only part of the story.",
            ],
            "suggested_duration": duration,
            "section_outline": [
                "Cold open and viewer promise",
                "What current videos establish",
                "The overlooked mechanism or evidence",
                "Examples and counterarguments",
                "Practical conclusion and next question",
            ],
            "evidence_backed_facts_to_research": facts,
            "thumbnail_concepts": [
                "One clear subject plus a contrasting overlooked detail",
                "Before/after or myth/evidence split composition",
            ],
            "thumbnail_text_options": [
                "WHAT THEY MISSED",
                "THE REAL METHOD",
                "MYTH vs EVIDENCE",
            ],
            "keywords": list(
                dict.fromkeys(
                    [topic, *topic.lower().split(), "explained", "documentary"]
                )
            ),
            "description_outline": [
                "One-sentence viewer benefit",
                "Two-sentence evidence-led synopsis",
                "Source and further-reading section",
                "Disclosure that estimates and claims were independently verified",
            ],
            "monetization_risks": list(opportunity.get("monetization_risks", [])),
            "copyright_risks": [
                "Do not reuse competitor footage, thumbnails, scripts, or music "
                "without rights.",
                "License every visual and audio asset; cite research without "
                "copying expression.",
            ],
            "production_difficulty": opportunity["production_difficulty"],
            "estimated_production_hours": opportunity["estimated_production_hours"],
            "publishing_recommendation": opportunity["expected_opportunity_window"],
            "limitations": [
                "Creative options are deterministic fallback drafts, not "
                "factual claims.",
                "Every factual statement must be independently verified before "
                "publication.",
                "The brief does not guarantee views, monetization, or revenue.",
            ],
        }
