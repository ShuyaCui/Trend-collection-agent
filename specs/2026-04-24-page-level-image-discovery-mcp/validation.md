# Validation: Page-Level Image Discovery MCP

## Success Criteria

The feature is complete when page-discovered images can be extracted from Tavily-hit pages, downloaded locally into the report image directory, and referenced by the final report without regressing the existing text-only path.

---

## Functional Validation

### V1 — Page Inspection

- [ ] Tavily-selected source pages are inspected with browser / Playwright MCP first.
- [ ] When browser inspection fails, fetch / HTTP inspection is attempted for the same page.
- [ ] A failure in both inspection paths does not fail the entire research run.

### V2 — Metadata Extraction

- [ ] Page-discovered images are normalized into `ImageResult` records.
- [ ] `source_page` is populated from the inspected page URL.
- [ ] `title` and `description` are populated from page-derived context when available.
- [ ] Relative image URLs are resolved to absolute URLs correctly.

### V3 — Merge Behavior

- [ ] Page-discovered images merge with Tavily-provided images without duplicate regressions.
- [ ] The pipeline still behaves correctly when Tavily returns no top-level images but page discovery finds valid images.
- [ ] The pipeline still behaves correctly when page discovery finds no valid images.

### V4 — State and Report Flow

- [ ] Page-derived images survive researcher compression and supervisor aggregation.
- [ ] Downloaded files land under `reports/<session_id>/images/`.
- [ ] `images_metadata.json` preserves page attribution metadata.
- [ ] Final report Markdown can reference local paths for page-discovered images.

---

## Automated Test Requirements

### V5 — Unit Coverage

- [ ] Automated tests cover URL normalization and relative-path resolution.
- [ ] Automated tests cover metadata precedence for `alt`, `figcaption`, and page title.
- [ ] Automated tests cover browser-to-fetch fallback behavior using mocks or fixtures.

### V6 — Integration Coverage

- [ ] Automated tests cover merged image propagation from discovery output into report/download inputs.
- [ ] Automated tests confirm no-regression behavior for text-only or no-image scenarios.

---

## Code Quality

### V7 — Notebook Workflow

- [ ] All implementation changes are made in notebooks and regenerate `src/` outputs correctly.
- [ ] No direct edits remain in generated production files.

### V8 — Lint and Targeted Validation

- [ ] `ruff check src/` passes after regeneration.
- [ ] Targeted automated tests for the modified flow pass.

---

## Merge Checklist

1. Browser-first MCP inspection and fetch / HTTP fallback are both implemented or explicitly stubbed with tests.
2. Page-derived image metadata is preserved through download and report generation.
3. Automated tests for normalization, fallback, and pipeline wiring pass.
4. Existing image-fetching behavior remains backward-compatible when page discovery is unavailable.
5. Notebook outputs are regenerated and linted.
6. Spec artifacts are committed before or alongside implementation work, per repository workflow.

## Validation Steps

1. Regenerate affected source files from notebooks 2, 4, and 5.
2. Run targeted automated tests for the page discovery and image pipeline path.
3. Run `ruff check src/`.
4. Execute a representative research query that has page-embedded images not exposed by Tavily's top-level image list.
5. Verify downloaded images exist in the report directory and that the report references local image paths.
6. Execute a no-image or MCP-failure scenario and verify the run still completes successfully.
