# Source-grounded Script Writer

Script generation requires an approved Research Dossier, approved Production Brief, and project status `BRIEF_APPROVED`. The Script Writer never expands thin evidence into padded narration.

## Evidence gate

Version 1 requires 4 facts/3 sources/1 authoritative source for up to five minutes; 8/5/2 for ten minutes; 12/7/3 for fifteen minutes; and 16/9/4 for twenty minutes. Supported narrative beats and evidence diversity are also reported. `INSUFFICIENT` produces a persistent coverage report and no narration. `LIMITED` is blocked unless explicitly configured.

## Grounding and citations

The script context contains only facts and sources selected by the approved brief. Every factual section has a separate citation-map entry with segment, fact IDs, source IDs, and verification status. Unknown, unselected, unverified, fabricated, uncited, or unqualified conflicting evidence fails deterministic validation. IDs never appear in spoken prose.

## Structure and review

The deterministic fallback produces an opening, introduction, evidence-led acts, transitions, qualified conclusion, call to action, visual cues, production notes, retention devices, and warnings. It does not add dates, statistics, quotations, demographics, or claims outside approved evidence. `SCRIPT_WORDS_PER_MINUTE` defaults to 145. Approval changes the project to `SCRIPT_APPROVED` and unlocks—but does not generate—the Storyboard stage.

## Limitations

Without a configured AI provider, narration is a conservative structured draft and may be shorter than the target. Full-source review, editorial polish, pronunciation review, and rights clearance remain mandatory.
