# Implementation Plan: Trend Analysis Dimension Skill

> **Status: ARCHIVED — Implementation complete (Groups 0–5 committed on development branch).**

## Overview

Extract analytical dimensions from 12 curated trend reports via a two-phase LLM pipeline running in `notebooks/6_trend_skill.ipynb`, then inject them dynamically into Scope and Supervisor prompts. The notebook is both the interactive tutorial and the runnable extraction tool. It also generates `trend_dimensions.py` via `%%writefile` cells.

---

## Group 1 — Dependencies & Project Structure

### 1.1 Add `pdfplumber` and `python-pptx` to `pyproject.toml`
- Add to `[project.dependencies]`
- Run `uv sync` to verify resolution
- **File**: `pyproject.toml`

### 1.2 Create `trend_knowledge/` directory
- Add a `.gitkeep` so the directory is tracked
- `dimensions.json` is committed here after extraction (see Group 2)

### 1.3 Create `notebooks/6_trend_skill.ipynb`
- New notebook following existing notebook structure
- Sections:
  1. Imports and environment setup
  2. Text extraction helpers (PDF + PPTX)
  3. Phase 1: per-document LLM dimension extraction
  4. Phase 2: cross-document synthesis
  5. Write `dimensions.json`
  6. `%%writefile` cells for `trend_dimensions.py`

---

## Group 2 — Document Extraction Pipeline (in Notebook 6)

### 2.1 Implement PDF text extraction helper
- **Notebook section**: "Text Extraction Helpers"
- Use `pdfplumber` to open each PDF and extract text per page
- Concatenate all pages into a single string per document
- Log a warning (not exception) for pages with no extractable text
- Return `{"filename": ..., "text": ..., "page_count": ...}`

### 2.2 Implement PPTX text extraction helper
- **Notebook section**: "Text Extraction Helpers"
- Use `python-pptx` to iterate slides; concatenate title + all text frame content
- Return `{"filename": ..., "text": ..., "slide_count": ...}`

### 2.3 Define Pydantic extraction schemas
- **Notebook section**: "Extraction Schemas"
- `Dimension(BaseModel)`: `name: str`, `description: str`, `examples: list[str]`
- `PerDocumentDimensions(BaseModel)`: `source_doc: str`, `dimensions: list[Dimension]`
- `UnifiedDimensionList(BaseModel)`: `dimensions: list[Dimension]`

### 2.4 Implement Phase 1 — per-document LLM extraction (12 calls)
- **Notebook section**: "Phase 1: Per-Document Extraction"
- For each of the 12 documents:
  - Truncate text to fit within context window if needed (e.g., first 15,000 tokens)
  - Call LLM with `model.with_structured_output(PerDocumentDimensions)`
  - **Phase 1 prompt** (key excerpt):
    > "You are analyzing a beauty industry trend report. Your task is NOT to summarize the report's findings. Instead, identify the **analytical dimensions** this report uses to structure its trend analysis — the lenses or angles through which it examines trends (e.g., by consumer demographic, by ingredient category, by geographic market, by distribution channel).
    >
    > For each dimension you identify:
    > - `name`: a short label (2–4 words)
    > - `description`: one sentence explaining what this dimension analyzes
    > - `examples`: 2–3 concrete examples from the document
    >
    > Return only dimensions that are genuinely used as a structural lens in this report. Ignore dimensions mentioned only in passing."
  - Collect all 12 `PerDocumentDimensions` results

### 2.5 Implement Phase 2 — cross-document synthesis (1 call)
- **Notebook section**: "Phase 2: Synthesis"
- Build a combined prompt that lists all 12 per-document dimension lists (formatted as JSON)
- Call LLM with `model.with_structured_output(UnifiedDimensionList)`
- **Phase 2 prompt** (key excerpt):
  > "You have received dimension lists extracted from {N} beauty industry trend reports. Each list describes the analytical lenses that one report uses to study trends.
  >
  > Your task: synthesize these into a single, unified, deduplicated list of **10–20 canonical dimensions**. Merge synonymous or highly overlapping entries into one (e.g., 'Consumer Age Groups' and 'Generational Segments' → 'Consumer Demographics'). Prefer broader, more reusable dimension names.
  >
  > For each canonical dimension:
  > - `name`: a short, reusable label (2–4 words)
  > - `description`: one sentence, generalized across all reports
  > - `examples`: 2–3 concrete examples that illustrate what this dimension covers"
- Result: `UnifiedDimensionList` with 10–20 deduplicated dimensions

### 2.6 Write `trend_knowledge/dimensions.json`
- Serialize `UnifiedDimensionList.dimensions` with metadata:
  ```json
  {
    "extraction_date": "<today>",
    "source_docs": ["file1.pdf", "file2.pptx", ...],
    "dimensions": [...]
  }
  ```
- Commit `dimensions.json` to the repository as a pre-generated artifact

---

## Group 3 — Dimension Loader Utility (via `%%writefile`)

### 3.1 Implement `load_trend_dimensions()` function
- **Notebook `%%writefile`**: `%%writefile ../src/deep_research_from_scratch/trend_dimensions.py`
- Locate `trend_knowledge/dimensions.json` relative to the repo root (use `Path(__file__)` traversal)
- Cache result in module-level variable (only reads disk once per process)
- Return `list[dict]` on success; log a warning and return `None` if file not found

### 3.2 Implement `format_dimensions_for_prompt()` function
- **Notebook `%%writefile`**: same file as 3.1
- Accept the output of `load_trend_dimensions()`
- Return a compact Markdown bulleted block:
  ```
  - **Consumer Demographics**: Analyze trends by age group, ethnicity, income... (e.g., Gen Z, Black consumers, luxury vs. mass)
  - **Ingredient & Technology Innovation**: Track new ingredients gaining traction... (e.g., biofermentation, AI-personalized skincare)
  ```
- Return empty string `""` if input is `None` (enables graceful degradation in callers)

---

## Group 4 — Scope Node Integration

### 4.1 Update `transform_messages_into_research_topic_prompt` in `prompts.py`
- **File**: `notebooks/1_scoping.ipynb` → `%%writefile` cell for `prompts.py`
- Add `{trend_dimensions}` placeholder
- Add a conditional section after the existing guidelines:
  > "**Expert analytical dimensions (when available):** The following dimensions are used by industry experts when studying trends in this domain. In the research brief, enumerate the most relevant ones so researchers know which angles to investigate:
  > {trend_dimensions}
  > (If no dimensions are listed above, proceed without this guidance.)"

### 4.2 Update `generate_research_brief` node in `research_agent_scope.py`
- **File**: `notebooks/1_scoping.ipynb` → `%%writefile` cell for `research_agent_scope.py`
- Import `load_trend_dimensions`, `format_dimensions_for_prompt` from `trend_dimensions`
- At node entry: call `format_dimensions_for_prompt(load_trend_dimensions())`
- Pass result as `trend_dimensions=...` in the prompt `.format()` call
- Empty string when dimensions unavailable → prompt section renders as no-op

---

## Group 5 — Supervisor Node Integration

### 5.1 Update `lead_researcher_prompt` in `prompts.py`
- **File**: `notebooks/4_research_supervisor.ipynb` → `%%writefile` cell for `prompts.py`
- Add `{trend_dimensions}` placeholder
- Add section instructing the supervisor to use dimensions when decomposing sub-tasks:
  > "**Expert analytical dimensions (when available):** When decomposing the research question into parallel sub-tasks, consider structuring ConductResearch calls around these expert dimensions:
  > {trend_dimensions}
  > Adapt them to the research question — not all dimensions apply to every topic. Do not create more sub-tasks than your concurrency limit allows."

### 5.2 Update `supervisor` node in `multi_agent_supervisor.py`
- **File**: `notebooks/4_research_supervisor.ipynb` → `%%writefile` cell for `multi_agent_supervisor.py`
- Import `load_trend_dimensions`, `format_dimensions_for_prompt` from `trend_dimensions`
- At node entry: call `format_dimensions_for_prompt(load_trend_dimensions())`
- Pass result as `trend_dimensions=...` in `lead_researcher_prompt.format()`

---

## Group 6 — Testing & Validation

### 6.1 Write unit tests for `trend_dimensions.py`
- **File**: `tests/test_trend_dimensions.py`
- Test `load_trend_dimensions()` with a mock `dimensions.json` in a temp directory
- Test graceful `None` return when file is missing (no exception raised)
- Test `format_dimensions_for_prompt()` output: correct Markdown bullets, each dimension present
- Test `format_dimensions_for_prompt(None)` returns `""`

### 6.2 Write unit tests for extraction helpers
- **File**: `tests/test_trend_extraction.py`
- Test PDF extraction helper with a minimal programmatic test PDF (use `pdfplumber` test fixtures or `reportlab`)
- Test PPTX extraction helper with a minimal `python-pptx`-generated test file
- Test graceful handling of an empty PDF / empty PPTX (no crash, empty string returned)

### 6.3 Run all existing tests
- `uv run pytest tests/` — all pre-existing tests must pass without regression

### 6.4 Manual notebook validation — extraction
- Run all Group 2 cells in `notebooks/6_trend_skill.ipynb`
- Verify: `dimensions.json` written with 10–20 entries, each having `name`, `description`, `examples`
- Inspect Phase 1 outputs per document: confirm dimensions are structural (not content summaries)
- Inspect Phase 2 output: confirm deduplication occurred (no near-synonymous entries)

### 6.5 Manual agent validation — Scope
- Open `notebooks/1_scoping.ipynb`
- Run with a beauty research question (e.g., "What are the major haircare trends in 2026?")
- Inspect `ResearchQuestion` brief: verify it enumerates 3+ analytical dimensions

### 6.6 Manual agent validation — Supervisor
- Open `notebooks/4_research_supervisor.ipynb` or `notebooks/5_full_agent.ipynb`
- Run with a beauty research question
- Inspect `ConductResearch` tool calls: verify they are structured around different dimensions, not just generic sub-topics

### 6.7 Lint check
- `ruff check src/` — no errors in regenerated files

### 6.8 Graceful degradation test
- Temporarily rename `trend_knowledge/dimensions.json`
- Run full pipeline — verify no crash, only a logged warning; research proceeds as before

### 6.9 Update specs and commit
- Update `specs/roadmap.md` to add trend dimension skill phase
- Commit `dimensions.json` + all code changes to `development` branch
- Open PR `development` → `main`
