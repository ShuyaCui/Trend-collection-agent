# Design: Trend Research Decomposition in `transform_messages_into_research_topic_prompt`

## Objective

Revise `transform_messages_into_research_topic_prompt` so that when a user is searching about the trend of something, the LLM generates a research brief that decomposes the original topic into several numbered sub-questions, each targeting a distinct analytical dimension from the pre-loaded `trend_dimensions` knowledge base.

## Context

- `transform_messages_into_research_topic_prompt` lives in `src/deep_research_from_scratch/prompts.py` (directly maintained, not auto-generated).
- The prompt already has a `{trend_dimensions}` placeholder at the end.
- `_build_scope_dimensions_section()` in `research_agent_scope.py` (generated from notebook `notebooks/1_scoping.ipynb`, cell 8) builds content for `{trend_dimensions}`.
- `trend_dimensions.py` loads analytical dimensions from `trend_knowledge/dimensions.json`.
- `ResearchQuestion` schema returns a single `research_brief: str` field — no schema change needed.

## Scope

- Modify `transform_messages_into_research_topic_prompt` in `prompts.py` only. **The second `{trend_dimensions}` placeholder at line 281 (inside `lead_researcher_prompt`) is intentionally left unchanged** — it serves a separate purpose in the research supervisor and is out of scope.
- Modify `_build_scope_dimensions_section()` in notebook `1_scoping.ipynb` cell 8 (which regenerates `research_agent_scope.py`). The existing function-level "7. Expert Analytical Dimensions" label injected at runtime is **retired** and replaced by the new static guideline 7 in the prompt body.

## Non-Goals

- No changes to `ResearchQuestion` schema.
- No new LLM call for trend detection (handled by the prompt conditional).
- No changes to `trend_dimensions.py` or `dimensions.json`.

## Design

### Change 1: `prompts.py` — Add Guideline 7

Add a new guideline section before `{trend_dimensions}`:

```
7. Trend Research Decomposition
- If the user's request is about researching a trend (e.g., "what is the trend in X",
  "how is X trending", "latest trends in X"), decompose the research brief into 4–6
  numbered sub-questions, each targeting a distinct analytical dimension.
- Select the most relevant dimensions from the list below and prefix each sub-question
  with the dimension name in brackets: "[Dimension Name] ..."
- Each sub-question must be specific and actionable, incorporating all user-stated details.
- If the topic is NOT trend-related, produce a single unified research brief without decomposition.

{trend_dimensions}
```

### Change 2: `research_agent_scope.py` (notebook 1, cell 8) — Simplify `_build_scope_dimensions_section()`

Since the decomposition instructions now live in the prompt body, the function only needs to provide the dimension list:

```python
def _build_scope_dimensions_section() -> str:
    """Build the analytical dimensions list for trend decomposition in the scope prompt."""
    dims = format_dimensions_for_prompt(load_trend_dimensions())
    if not dims:
        return ""
    return f"Available analytical dimensions for trend decomposition:\n{dims}"
```

## Data Flow

**Trend query:**

1. `{trend_dimensions}` receives labeled dimension list from `_build_scope_dimensions_section()`
2. LLM reads guideline 7 and detects trend intent
3. LLM selects 4–6 most relevant dimensions
4. LLM produces `research_brief` as numbered sub-questions prefixed with `[Dimension Name]`

**Non-trend query:**

1. `{trend_dimensions}` receives labeled dimension list
2. LLM reads guideline 7 and detects non-trend intent
3. LLM produces single unified `research_brief` (unchanged behavior)

**No dimensions file:**

1. `_build_scope_dimensions_section()` returns `""` → `{trend_dimensions}` is empty
2. Guideline 7 still present but no dimension list → LLM falls back to single brief

## Acceptance Criteria

- [ ] Trend query (e.g., "what is the trend in skincare in Asia") produces a `research_brief` with 4–6 numbered sub-questions prefixed by `[Dimension Name]`.
- [ ] Non-trend query (e.g., "find me the best coffee shops in Tokyo") produces a single unified brief without numbered sub-questions.
- [ ] Edge-case / ambiguous query (e.g., "how has skincare evolved in Asia"): LLM judgment determines whether to decompose — no hard rule; LLM may or may not treat as trend-related. This is acceptable — the guideline says "e.g." and the LLM interprets intent.
- [ ] When `dimensions.json` is absent **or malformed/empty** (any failure mode in `load_trend_dimensions()`), `_build_scope_dimensions_section()` returns `""`, `{trend_dimensions}` is blank, guideline 7 still appears but the LLM produces a single brief without dimension decomposition (graceful degradation, no error).
- [ ] The 4–6 dimension count is **soft guidance** — the LLM may return 3 or 7 sub-questions depending on topic fit. No hard enforcement.
- [ ] No new tests are required for this change (the prompt is exercised by end-to-end runs; unit tests for LLM output quality are out of scope).
- [ ] Existing tests pass (run `uv run pytest tests/` to verify).

## Files Changed

| File                                                     | Change                                                                            |
| -------------------------------------------------------- | --------------------------------------------------------------------------------- |
| `src/deep_research_from_scratch/prompts.py`              | Add guideline 7 with trend decomposition instructions before `{trend_dimensions}` |
| `notebooks/1_scoping.ipynb` (cell 8)                     | Simplify `_build_scope_dimensions_section()` to return dimension list only        |
| `src/deep_research_from_scratch/research_agent_scope.py` | Auto-regenerated from notebook cell 8                                             |
