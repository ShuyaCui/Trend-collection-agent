# Tasks: page-level-image-discovery-mcp

## Phase A — Foundations and Contracts

### Group A1 — Confirm Integration Boundary

- [ ] Document that Notebook 2 is the primary implementation surface for discovery/enrichment logic.
- [ ] Confirm Notebook 4 and Notebook 5 only require compatibility updates, not architecture rewrites.
- [ ] Record runtime dependencies for browser MCP and fetch/html fallback availability.

Deliverable:

- Clear implementation boundary notes in change artifacts and code comments.

### Group A2 — Image Metadata Contract

- [ ] Define optional `ImageResult` extension fields for discovery context, asset facts, and material linking.
- [ ] Specify backward-compatibility rules so existing consumers can ignore new fields safely.
- [ ] Define serialization contract for `images_metadata.json` with required vs optional fields.

Deliverable:

- Versioned metadata field contract captured in notebook-generated schema/helpers.

### Group A3 — Matching Catalog Inputs

- [ ] Define catalog loading contract for `material_library/color.json`, `texture.json`, `decoration.json`, and `style.json`.
- [ ] Define normalized in-memory lookup shape for dimension matching.
- [ ] Define behavior when one or more catalog files are missing or malformed.

Deliverable:

- Deterministic catalog loader with graceful degradation behavior.

## Phase B — Discovery, Enrichment, and Linking

### Group B1 — Page Discovery Extractors

- [ ] Implement browser-first page extractor for title, img src, alt, figcaption, og:image, and nearby text.
- [ ] Implement fetch/html fallback extractor with equivalent output shape.
- [ ] Add page-level timeout, retry, and fallback routing logic.

Deliverable:

- Unified extractor interface returning normalized candidate records.

### Group B2 — Candidate Normalization and Dedupe

- [ ] Resolve relative image URLs against source page.
- [ ] Normalize URLs and strip bounded tracking parameters.
- [ ] Drop malformed or unsupported URL schemes.
- [ ] Deduplicate candidates by normalized URL + source page.
- [ ] Preserve discovery provenance fields for auditability.

Deliverable:

- Stable, deduplicated candidate list per query.

### Group B3 — Asset Enrichment

- [ ] Fetch/download image assets with bounded timeout.
- [ ] Extract content type, dimensions, and file size where available.
- [ ] Add optional dominant color extraction path with bounded runtime.
- [ ] Preserve candidates on fetch failure without blocking the run.

Deliverable:

- Enriched candidate list with asset facts and partial-failure resilience.

### Group B4 — Material Linking Engine

- [ ] Build per-dimension candidate lexicons from catalog names/keywords.
- [ ] Implement deterministic evidence scoring from alt/caption/nearby/page-title signals.
- [ ] Add optional color-signal boosting using dominant colors.
- [ ] Emit `material_library_links` with confidence and evidence fields.
- [ ] Enforce catalog-constrained linking (no generated taxonomy labels).

Deliverable:

- Bounded per-image links across color/texture/decoration/style dimensions.

### Group B5 — Merge and State Threading

- [ ] Merge MCP-discovered images with Tavily-provided images.
- [ ] Define collision rules that prefer richer metadata on URL overlap.
- [ ] Preserve merged images through researcher state, compression, supervisor aggregation, and full-agent output.

Deliverable:

- End-to-end state propagation without regressions in existing flow.

### Group B6 — Report Selection and Persistence

- [ ] Add ranking/selection logic to prioritize stronger material-linked images when capped.
- [ ] Persist full enriched metadata into `images_metadata.json`.
- [ ] Ensure report writer continues using local relative image paths when available.

Deliverable:

- Report-ready image set and complete metadata sidecar per session.

## Phase C — Validation, Documentation, and Readiness

### Group C1 — Unit Validation

- [ ] Add tests for extractor output shape and fallback behavior.
- [ ] Add tests for URL normalization, dedupe keys, and malformed URL handling.
- [ ] Add tests for metadata precedence (`alt` > explicit title > page title; `figcaption` > nearby text).
- [ ] Add tests for material link scoring, confidence levels, and evidence capture.
- [ ] Add tests for catalog-constrained linking and no-match behavior.

Deliverable:

- Deterministic unit test coverage for all core helpers.

### Group C2 — Integration and Regression Validation

- [ ] Add integration tests for Tavily+MCP merge and state propagation.
- [ ] Add integration tests for `images_metadata.json` persistence with enriched fields.
- [ ] Add regression tests ensuring Tavily-only flow still succeeds when MCP is unavailable.
- [ ] Validate report generation remains non-blocking under partial download/linking failures.

Deliverable:

- End-to-end validation of enriched image pipeline behavior.

### Group C3 — Quality and Workflow Checks

- [ ] Run lint and targeted validation for generated source files.
- [ ] Verify notebook source-of-truth boundaries are respected (no direct `src/` edits).
- [ ] Update feature notes if scope or assumptions changed during implementation.
- [ ] Prepare follow-up execution via `/opsx:apply` with ordered task execution notes.

Deliverable:

- Apply-ready implementation checklist and clean handoff.

## Completion Criteria

- [ ] All Phase A/B/C groups completed.
- [ ] Validation evidence recorded for unit + integration + regression coverage.
- [ ] Metadata schema changes documented and backward compatibility verified.
- [ ] Feature is ready to execute through `/opsx:apply` without unresolved design ambiguity.
