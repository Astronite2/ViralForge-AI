# Research expansion workflow

Research expansion is the recovery path for a Script Writer evidence gate that reports `INSUFFICIENT`. It does not lower duration thresholds or pad narration.

The gap analyzer compares approved facts, selected sources, authoritative-source count, and supported Production Brief beats with the versioned duration thresholds. It proposes focused searches across historical context, chronology, construction and material evidence, archaeology, measurements, people, geography, scholarly interpretations, experiments, myths, visual evidence, and unresolved questions.

`POST /api/v1/projects/{id}/research/expand` runs asynchronously. It uses the documented Met Collection, Crossref, and MediaWiki APIs, tolerates partial provider failure, canonicalizes URLs, and deterministically classifies source quality. Search excerpts remain evidence leads; full-source review is required before recording. It does not bypass paywalls or access controls.

Successful expansion increments `research-vN`, records an audit entry, clears approval, and marks the Production Brief and Script `STALE`. Briefs record `research_version_used`; Scripts record both upstream versions. Stale artifacts cannot be approved. On failure, the previous dossier and downstream states are restored.

Manual flow:

1. Choose **Expand Research** from an insufficient Script.
2. Review gaps and start expansion.
3. Review and approve the expanded dossier.
4. Regenerate and approve the Production Brief.
5. Regenerate and approve Script only if citation and duration checks pass.

When credible evidence remains insufficient, use the recommended shorter duration. Storyboard remains unimplemented.
