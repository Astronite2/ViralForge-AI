# Executive Producer

The Executive Producer converts an approved Research Dossier into a concise production decision. Research records what sources support; the Production Brief decides which angle, evidence, structure, visuals, and risks should guide a future Script Writer. It does not generate narration.

## Evidence boundary

Legacy dossier facts receive deterministic IDs derived from their claim and existing citation IDs. The Producer can select only fact and source IDs in the approved dossier. Unknown IDs, unverified facts, unqualified conflicting facts, and story beats without selected citations fail validation. Limitations remain visible.

## Angle selection

Candidates originate from dossier story angles. They are ranked deterministically by source quality, matching supported facts, visual potential, production difficulty, and confidence. AI may later improve creative wording, but cannot change references, validation, or profitability scoring.

## Profitability recheck

The revised score is relative production attractiveness, not predicted earnings: evidence quality 30%, visual potential 15%, evergreen strength 20%, monetization safety 15%, and production feasibility 20%. Confidence depends on evidence strength, source count, and authoritative-source coverage. Recommendations are `PROCEED`, `PROCEED_WITH_CAUTION`, `RESEARCH_MORE`, or `REJECT`.

## Workflow and risks

POST `/api/v1/projects/{id}/production-brief/start`, poll `/status`, inspect the completed brief, then approve or reject it. Approval changes the project to `BRIEF_APPROVED` and unlocks—but does not generate—the Script stage. The brief carries factual, monetization, copyright, licensing, production, and evidence limitations.

## Limitations

The fallback is deterministic and evidence-only. Competition, revenue, demographics, and advertiser demand are not invented when absent. Production-hour estimates are planning heuristics. All museum, archive, and third-party visuals require rights review.
