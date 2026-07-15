# ruff: noqa: E501
"""Transparent post-research production viability check."""

from typing import Any


class ProfitabilityRecheck:
    def evaluate(
        self, candidate: dict[str, Any], dossier: dict[str, Any]
    ) -> dict[str, Any]:
        evidence = float(candidate["evidence_strength"])
        visual = float(candidate["visual_potential"])
        evergreen = float(candidate["evergreen_potential"])
        safety = float(candidate["monetization_safety"])
        difficulty = float(candidate["production_difficulty"])
        source_count = len(dossier.get("sources", []))
        authority_count = sum(
            source.get("source_quality") in {"PRIMARY", "AUTHORITATIVE"}
            for source in dossier.get("sources", [])
        )
        production_hours = round(6 + difficulty * 0.18, 1)
        values = {
            "evidence_quality": evidence,
            "visual_potential": visual,
            "evergreen_strength": evergreen,
            "monetization_safety": safety,
            "production_feasibility": 100 - difficulty,
        }
        weights = {
            "evidence_quality": 0.30,
            "visual_potential": 0.15,
            "evergreen_strength": 0.20,
            "monetization_safety": 0.15,
            "production_feasibility": 0.20,
        }
        trace = [
            {
                "factor": key,
                "input": value,
                "weight": weights[key],
                "contribution": round(value * weights[key], 2),
            }
            for key, value in values.items()
        ]
        score = round(max(0, min(100, sum(item["contribution"] for item in trace))), 1)
        confidence = round(
            min(
                100,
                evidence * 0.65
                + min(source_count / 20, 1) * 20
                + min(authority_count / 3, 1) * 15,
            ),
            1,
        )
        recommendation = (
            "PROCEED"
            if score >= 70 and confidence >= 65
            else (
                "PROCEED_WITH_CAUTION"
                if score >= 55
                else "RESEARCH_MORE" if evidence >= 35 else "REJECT"
            )
        )
        return {
            "revised_money_score": score,
            "revised_confidence": confidence,
            "estimated_production_hours": production_hours,
            "production_difficulty": difficulty,
            "recommendation": recommendation,
            "calculation_trace": trace,
            "assumptions": [
                "Score measures relative production attractiveness, not guaranteed revenue.",
                "No competitor or advertiser value was invented where the dossier lacked evidence.",
            ],
            "limitations": list(dossier.get("limitations", [])),
        }
