# Research workspace

ViralForge project research runs asynchronously through `backend.app.workers.tasks.run_project_research`. Starting research creates a persistent versioned dossier, moves the project to `RESEARCHING`, and enqueues the task. Only a successful save moves the project to `RESEARCH_COMPLETE`.

## Provider and grounding

The default provider combines The Metropolitan Museum of Art's public Collection API, the documented Crossref scholarly works API, and MediaWiki search. Museum records provide first-party collection metadata; Crossref results are retained only when an indexed abstract is available; Wikipedia is classified as `GENERAL_REFERENCE`, not authoritative. Wikipedia is suitable for orientation and its source-diversity limitation remains visible. Providers store short excerpts, URLs, publishers, domains, retrieval times and relevance—not full copyrighted pages. No API key is required or logged.

Source quality is deterministic: government domains are `PRIMARY`; academic, museum and recognized institutional domains are `AUTHORITATIVE`; dated named publishers are `REPUTABLE_SECONDARY`; Wikipedia is `GENERAL_REFERENCE`; community sites are `COMMUNITY`; sources without authority signals are `LOW_CONFIDENCE`.

Every fact has source IDs, confidence and one of `SUPPORTED`, `PARTIALLY_SUPPORTED`, `CONFLICTING`, or `UNVERIFIED`. Unverified facts and unknown citation IDs are rejected. The deterministic fallback only promotes retrieved excerpts and explicitly requires full-source verification before scripting. It does not use model memory.

## Configuration

Research limits are controlled by `RESEARCH_MAX_SEARCH_QUERIES`, `RESEARCH_MAX_SOURCES`, `RESEARCH_MIN_AUTHORITATIVE_SOURCES`, `RESEARCH_TIMEOUT_SECONDS`, and `RESEARCH_MAX_RETRIES`. Never commit provider keys.

## Run

Create a project, POST `/api/v1/projects/{id}/research/start`, poll `/research/status`, then GET `/research`. Completed or review-needed dossiers can be approved with POST `/research/approve`. Failed research can be retried with POST `/research/retry`.

## Limitations

MediaWiki-only research will usually lack the configured minimum of institutional sources. The UI reports this rather than elevating source quality. Extracted snippets are research leads, not final quotations. Script generation is intentionally outside this milestone.
