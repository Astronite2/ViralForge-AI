"""Build a conservative dossier solely from collected evidence."""

from datetime import UTC, datetime

from backend.app.core.config import settings
from backend.app.research.fact_validator import validate_fact


class DossierBuilder:
    def build(
        self, *, topic: str, sources: list[dict[str, object]]
    ) -> dict[str, object]:
        source_ids = {str(source["id"]) for source in sources}
        facts = []
        for source in sources[:12]:
            excerpt = str(source.get("excerpt", "")).strip()
            if not excerpt:
                continue
            quality = str(source.get("source_quality", "LOW_CONFIDENCE"))
            verification = (
                "SUPPORTED"
                if quality in {"PRIMARY", "AUTHORITATIVE"}
                else "PARTIALLY_SUPPORTED"
            )
            candidate = {
                "claim": excerpt,
                "supporting_source_ids": [source["id"]],
                "confidence": round(
                    0.45 + float(source.get("relevance", 0.5)) * 0.35, 2
                ),
                "verification_status": verification,
                "notes": (
                    "Authoritative source excerpt; verify against the full linked "
                    "source before scripting."
                    if verification == "SUPPORTED"
                    else "Search metadata or excerpt is an evidence lead, not full "
                    "verification; review the linked source before scripting."
                ),
            }
            validated = validate_fact(candidate, source_ids)
            if validated:
                facts.append(validated)
        authoritative = sum(
            source.get("source_quality") in {"PRIMARY", "AUTHORITATIVE"}
            for source in sources
        )
        limitations = [
            "Retrieved excerpts are evidence leads, not substitutes for reading "
            "the full sources.",
            "No quotations, dates, or statistics should enter a script without "
            "checking the linked source.",
        ]
        if authoritative < settings.research_min_authoritative_sources:
            limitations.append(
                f"Only {authoritative} authoritative sources were collected; the "
                "configured minimum is "
                f"{settings.research_min_authoritative_sources}."
            )
        angle_sources = [
            source
            for source in sources
            if source.get("source_quality")
            in {"PRIMARY", "AUTHORITATIVE", "REPUTABLE_SECONDARY"}
        ][:3]
        angles = [
            {
                "title": f"Investigate: {title}",
                "description": (
                    "Use the linked evidence as a starting point and contrast it "
                    "with authoritative sources."
                ),
                "supporting_source_ids": [str(source["id"])],
            }
            for source in angle_sources
            for title in [str(source["title"])]
        ]
        visuals = [
            {
                "description": f"Source-led visual research for {source['title']}",
                "supporting_source_ids": [str(source["id"])],
                "rights_note": "Check licensing and usage rights before production.",
            }
            for source in (angle_sources or sources[:2])[:4]
        ]
        summary = (
            f"Research for {topic} collected {len(sources)} traceable sources and "
            f"identified {len(facts)} excerpt-grounded evidence leads. Read the cited "
            "sources and resolve the listed limitations before scripting."
        )
        return {
            "executive_summary": summary,
            "audience_interest": (
                "Audience-interest claims require observed audience evidence and "
                "were not inferred from web sources."
            ),
            "why_this_topic_matters": (
                "The collected sources establish research directions; editorial "
                "significance requires review."
            ),
            "key_facts": facts[:6],
            "interesting_facts": facts[6:12],
            "timeline": [],
            "people": [],
            "locations": [],
            "myths_and_misconceptions": [],
            "controversies_or_uncertainties": [],
            "frequently_asked_questions": [],
            "story_angles": angles,
            "visual_opportunities": visuals,
            "open_questions": [
                "Which claims are confirmed by primary or institutional sources?",
                "Where do reputable sources disagree?",
                "Which visuals can be licensed for documentary use?",
            ],
            "sources": sources,
            "limitations": limitations,
            "generated_at": datetime.now(UTC).isoformat(),
            "research_version": settings.research_version,
            "research_status": "COMPLETE",
        }
