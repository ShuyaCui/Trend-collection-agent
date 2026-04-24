# Validation: Trend Analysis Dimension Skill

## Success Criteria

The feature is considered complete and ready to merge when **all** of the following are verified.

---

## Functional Validation

### V1 — Document Text Extraction

- [ ] PDF extraction helper correctly extracts text from all PDF files in `history_trend_report/`
- [ ] PPTX extraction helper correctly extracts text from all PPTX files in `history_trend_report/`
- [ ] Extraction failures (empty pages, scanned images) are logged as warnings without crashing
- [ ] All 12 documents produce non-empty extracted text

### V2 — Phase 1: Per-Document LLM Extraction

- [ ] Each of the 12 documents produces a `PerDocumentDimensions` result (12 structured outputs)
- [ ] Each result contains at least 3 named dimensions with non-empty `description` and `examples`
- [ ] Dimensions are structural/methodological (e.g., "Consumer Demographics") — not content summaries (e.g., "Gen Z prefers...")
- [ ] Long documents are truncated gracefully before the LLM call (no context window overflow)

### V3 — Phase 2: Synthesis

- [ ] The synthesis LLM call receives all 12 per-document dimension lists
- [ ] Output `UnifiedDimensionList` contains between 10 and 20 dimensions
- [ ] No two dimensions in the unified list are near-synonymous (deduplication was applied)
- [ ] Each unified dimension has `name`, `description`, and at least 2 `examples`

### V4 — `dimensions.json` artifact

- [ ] `trend_knowledge/dimensions.json` is written correctly after running Notebook 6 extraction cells
- [ ] JSON is valid and matches the expected schema (`extraction_date`, `source_docs`, `dimensions`)
- [ ] File is committed to the repository (no re-extraction required on fresh clone)

### V5 — Dimension Loader Utility

- [ ] `load_trend_dimensions()` returns the correct list when `dimensions.json` exists
- [ ] `load_trend_dimensions()` returns `None` with a logged warning when file is missing (no exception)
- [ ] `format_dimensions_for_prompt()` returns a compact Markdown bulleted list
- [ ] `format_dimensions_for_prompt(None)` returns `""` (graceful degradation)
- [ ] Module-level cache prevents repeated disk reads within the same process

### V6 — Scope Node Enrichment

- [ ] `transform_messages_into_research_topic_prompt` contains the `{trend_dimensions}` placeholder
- [ ] When `dimensions.json` exists: the generated `ResearchQuestion` brief enumerates 3+ analytical dimensions
- [ ] When `dimensions.json` is missing: Scope node logs a warning and produces a brief without dimension section (no crash)

### V7 — Supervisor Node Enrichment

- [ ] `lead_researcher_prompt` contains the `{trend_dimensions}` placeholder
- [ ] When `dimensions.json` exists: `ConductResearch` calls show dimension-based decomposition (different calls target different dimensions)
- [ ] When `dimensions.json` is missing: Supervisor logs a warning and issues calls without dimension guidance (no crash)
- [ ] Supervisor respects `max_concurrent_researchers` limit — does not create one ConductResearch call per dimension blindly

---

## Backward Compatibility

### V8 — No Regression

- [ ] Renaming `trend_knowledge/dimensions.json` produces only a logged warning; pipeline completes normally
- [ ] All existing LangGraph entry points still compile:
  - `research_agent_full.py:agent`
  - `research_agent.py:researcher_agent`
  - `multi_agent_supervisor.py:supervisor_agent`
  - `research_agent_scope.py:scope_research`
- [ ] Researcher agent toolset is unchanged (no new tool added, no existing tool removed)
- [ ] Non-beauty research queries still produce valid research briefs and supervisor decomposition

---

## Code Quality

### V9 — Lint & Style

- [ ] `ruff check src/` passes with no errors after running all `%%writefile` cells
- [ ] New code follows existing conventions: Google-style docstrings, isort import order, no unused imports

### V10 — Notebook Workflow

- [ ] `notebooks/6_trend_skill.ipynb` contains:
  - Extraction cells (Groups 2–3 of plan) that can be run top-to-bottom
  - `%%writefile` cells that regenerate `src/deep_research_from_scratch/trend_dimensions.py`
- [ ] `notebooks/1_scoping.ipynb` updated `%%writefile` cells for `research_agent_scope.py` and `prompts.py`
- [ ] `notebooks/4_research_supervisor.ipynb` updated `%%writefile` cells for `multi_agent_supervisor.py` and `prompts.py`
- [ ] No direct edits to `src/` files exist outside of `%%writefile` generation

### V11 — Tests

- [ ] `tests/test_trend_dimensions.py` covers: load with valid file, load with missing file, format output shape, format with `None` input
- [ ] `tests/test_trend_extraction.py` covers: PDF extraction, PPTX extraction, empty file handling
- [ ] All tests pass: `uv run pytest tests/`
- [ ] Tests mock external LLM calls (no live API calls in test suite)

---

## Merge Checklist

Before merging `development` → `main`:

1. All V1–V11 checks pass
2. Spec files present in `specs/2026-04-23-trend-skill/` (requirements, plan, validation)
3. `specs/roadmap.md` updated with trend dimension skill phase
4. `trend_knowledge/dimensions.json` committed (pre-generated artifact)
5. Changes committed to `development` branch with descriptive commit message
6. PR opened from `development` → `main` for human review

---

## Validation Steps (Execution Order)

1. `uv sync` — verify new dependencies (`pdfplumber`, `python-pptx`) resolve (V dependencies)
2. Run Notebook 6 extraction cells — verify `dimensions.json` produced with 10–20 entries (V1–V4)
3. `uv run pytest tests/test_trend_dimensions.py -v` — loader unit tests pass (V5, V11)
4. `uv run pytest tests/test_trend_extraction.py -v` — extraction helper tests pass (V1, V11)
5. `uv run pytest tests/ -v` — all pre-existing tests pass (V8)
6. `ruff check src/` — no lint errors (V9)
7. Run `notebooks/1_scoping.ipynb` with a beauty query — inspect brief for dimension enumeration (V6)
8. Run `notebooks/4_research_supervisor.ipynb` with a beauty query — inspect `ConductResearch` calls for dimension decomposition (V7)
9. Rename `dimensions.json` → run full pipeline → confirm only warning logged, no crash (V8 graceful degradation)
10. Restore `dimensions.json` → run end-to-end `notebooks/5_full_agent.ipynb` → confirm enriched decomposition in final output (V6 + V7)
