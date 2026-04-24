# Plan — LangSmith → Langfuse Migration

> **Status: ARCHIVED — Implementation complete as of 2026-04-24. All automated validation gates passed.**

Task groups are ordered by dependency: infrastructure first, then tracing, then evaluation, then documentation, then final validation.

---

## Group 0 — Dependency and environment setup

0.1. Replace `langsmith` with `langfuse` in `pyproject.toml` dependencies.

0.2. Run `uv sync` to update `uv.lock` and install Langfuse.

0.3. Update `.env` / `.env.example` to replace LangSmith env vars with Langfuse env vars:
- Remove: `LANGSMITH_API_KEY`, `LANGSMITH_TRACING`, `LANGSMITH_PROJECT`
- Add: `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`

0.4. Verify `import langfuse` succeeds and `import langsmith` fails (confirming clean removal).

---

## Group 1 — Tracing migration

Replace LangSmith auto-tracing with explicit Langfuse `CallbackHandler` injection.

1.1. Update `notebooks/4_research_supervisor.ipynb`:
- Remove `os.environ.setdefault("LANGSMITH_TRACING", "true")` and related LangSmith env setup.
- Add `CallbackHandler` initialization from `langfuse.callback`.
- Pass `callbacks=[handler]` in all `graph.invoke()` / `graph.ainvoke()` config.
- Replace LangSmith trace URL printing with Langfuse trace URL (via `handler.get_trace_url()`).
- Remove the "Recent traces helper" cell that queries LangSmith for trace URLs.
- Add `handler.flush()` after invocations.

1.2. Update `notebooks/5_full_agent.ipynb`:
- Same pattern as 1.1: remove `LANGSMITH_TRACING` env setup, add `CallbackHandler`, pass in config.
- Add `handler.flush()` after invocations.

1.3. Update `notebooks/1_scoping.ipynb` and `notebooks/2_research_agent.ipynb`:
- Check for any implicit LangSmith tracing env setup and remove it.
- Add `CallbackHandler` if tracing is desired in these notebooks (follow the same pattern).

---

## Group 2 — Evaluation infrastructure migration

Update shared eval helpers before migrating individual notebooks.

2.1. Update `notebooks/utils.py`:
- Rename `to_langsmith_result()` → `to_langfuse_score()`.
- Update the function signature and return type to produce a dict compatible with `langfuse.score()` parameters: `name`, `value`, `comment`, and metadata.
- Keep `JudgeResult`, `JudgeResultWithImprovement`, `normalize_score()`, `init_judge_model()` unchanged.
- Remove any LangSmith-specific docstring references.

2.2. Verify that `to_langfuse_score()` output dict has the shape:
```python
{
    "name": str,       # evaluator key (e.g., "research_depth_score")
    "value": float,    # normalized 0.0–1.0 score
    "comment": str,    # evidence + reasoning + confidence
    "metadata": dict,  # evaluator_info (type, strictness, raw_score, confidence, etc.)
}
```

---

## Group 3 — Notebook evaluation migration

Replace `langsmith.Client` evaluation patterns with Langfuse SDK in each notebook.

3.1. Update `notebooks/1_scoping.ipynb` eval section:
- Replace `from langsmith import Client` with `from langfuse import Langfuse`.
- Replace `langsmith_client = Client(...)` with `langfuse = Langfuse()`.
- Replace `langsmith_client.create_dataset()` / `create_examples()` with `langfuse.create_dataset()` / `dataset.create_item()`.
- Replace `langsmith_client.evaluate()` with Langfuse experiment loop: iterate dataset items, get handler, run target, score results.
- Update evaluator functions to use `to_langfuse_score()` instead of `to_langsmith_result()`.

3.2. Update `notebooks/2_research_agent.ipynb` eval section:
- Same pattern as 3.1.

3.3. Update `notebooks/4_research_supervisor.ipynb` eval section:
- Same pattern as 3.1, but use async-compatible patterns (`aevaluate()` → async Langfuse experiment loop).

3.4. Update `notebooks/5_full_agent.ipynb` eval section:
- Same pattern as 3.1, but use async-compatible patterns.
- This notebook has the most complex evaluation setup (4 evaluators for the E2E system).

3.5. Re-run all `%%writefile` cells in the affected notebooks to regenerate `src/` files.

3.6. Run `ruff check src/` and fix any new lint errors (fix in notebooks, not in `src/`).

---

## Group 4 — Documentation updates

4.1. Update `specs/tech-stack.md`:
- Change tracing row from `LangSmith (optional)` to `Langfuse (required)`.
- Update env var table: remove `LANGSMITH_*`, add `LANGFUSE_*`.
- Update evaluation candidates section to reference Langfuse.

4.2. Update `specs/roadmap.md`:
- Update Phase 6 description: replace "LangSmith pattern" references with Langfuse.
- Update "Done when" criteria.

4.3. Update `specs/2026-04-22-agent-validation/requirements.md`:
- Replace all LangSmith references with Langfuse equivalents.
- Update integration pattern descriptions.
- Update env var table.

4.4. Update `specs/2026-04-22-agent-validation/plan.md`:
- Replace all `langsmith_client.evaluate()` references with Langfuse experiment pattern.
- Replace `LangSmith` mentions with `Langfuse`.

4.5. Update `specs/2026-04-22-agent-validation/validation.md`:
- Replace "LangSmith experiment" references with "Langfuse experiment".
- Update acceptance criteria and "How to run validation" commands.

4.6. Update `README.md`:
- Replace LangSmith env var examples with Langfuse.
- Update "Optional: For evaluation and tracing" section.

4.7. Update `CLAUDE.md` and `.github/copilot-instructions.md`:
- Replace `LANGSMITH_API_KEY`, `LANGSMITH_TRACING` references with Langfuse equivalents.

4.8. Update `TODO.md`:
- Replace LangSmith references in agent validation and shared infrastructure sections.

---

## Group 5 — Final validation and merge readiness

5.1. Run a full text search for `langsmith` (case-insensitive) across the repository and confirm zero matches outside of `uv.lock` (which will be regenerated) and historical git commits.

5.2. Run `ruff check src/` and confirm no errors.

5.3. Verify tracing: run a notebook cell that invokes the graph and confirm traces appear in the self-hosted Langfuse instance.

5.4. Verify evaluation: run a notebook eval section and confirm:
- Dataset is created in Langfuse.
- Experiment run completes.
- Evaluator scores (both heuristic and LLM-judge) are recorded with correct metadata.

5.5. Commit on `development` branch, then open PR from `development` → `main`.
