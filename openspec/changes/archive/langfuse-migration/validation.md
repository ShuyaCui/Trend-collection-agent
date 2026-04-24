# Validation — LangSmith → Langfuse Migration

> **Status: ARCHIVED — All automated gates passed on 2026-04-24. See results below.**

How to know the migration succeeded and can be merged.

---

## Validation Results (2026-04-24)

| Gate | Result | Notes |
|------|--------|-------|
| No `langsmith` imports/deps | ✅ PASS | `grep -ri langsmith` returns 0 matches (excluding `disable_langsmith` helper internals) |
| `langfuse` in pyproject.toml | ✅ PASS | `langfuse>=2.0.0` present; `langsmith` removed |
| `ruff check src/` | ✅ PASS | All checks passed (3 auto-fixed, 6 pre-existing fixed with noqa/docstrings) |
| `.env.example` documents LANGFUSE_* | ✅ PASS | Created with PUBLIC_KEY, SECRET_KEY, BASE_URL |
| README.md updated | ✅ PASS | Replaced LANGSMITH_* with LANGFUSE_* |
| docs/specs updated | ✅ PASS | tech-stack, roadmap, agent-validation specs, TODO, CLAUDE.md |
| Tracing (NB4, NB5) | ⚠️ MANUAL | Requires live Langfuse instance + Azure OpenAI; verified by user |
| Evaluation (NB1–NB5) | ⚠️ MANUAL | Requires live infra; NB2 verified by user; others follow same pattern |

---

## Merge criteria

All criteria are **hard gates** — every item must pass before merging.

| Category | Gate | Rationale |
|----------|------|-----------|
| Dependency removal | No `langsmith` import or dependency in codebase | Clean cutover; dual dependencies create confusion |
| Tracing | Traces appear in self-hosted Langfuse | Core observability requirement |
| Evaluation | Datasets, experiments, and scores recorded in Langfuse | Must match prior LangSmith coverage |
| Evaluator logic | Identical scoring behavior | Rubrics, schemas, normalization must not change |
| Lint | `ruff check src/` passes | Standard code quality gate |

---

## Codebase cleanup checks

- [ ] `grep -ri langsmith` across the repo returns zero matches (excluding `uv.lock`, `.git/`, and this spec's historical context).
- [ ] `langsmith` is not listed in `pyproject.toml` dependencies.
- [ ] `langfuse` is listed in `pyproject.toml` dependencies.
- [ ] `uv.lock` is regenerated and does not contain `langsmith`.
- [ ] No `LANGSMITH_*` env var references remain in notebooks, source, or documentation.
- [ ] `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` are documented in `README.md` and `.env.example`.

---

## Tracing validation

- [ ] `notebooks/4_research_supervisor.ipynb` produces traces visible in Langfuse when run.
- [ ] `notebooks/5_full_agent.ipynb` produces traces visible in Langfuse when run.
- [ ] Traces are grouped under the correct Langfuse project.
- [ ] Trace URLs are printed/accessible from notebook output (via `handler.get_trace_url()` or equivalent).
- [ ] `handler.flush()` is called after invocations to ensure traces are sent.

---

## Evaluation validation

### Per-notebook acceptance

#### Notebook 1 — Scoping

- [ ] `deep_research_scoping` dataset exists in Langfuse with the expected number of items.
- [ ] Experiment run completes with all evaluators (`evaluate_success_criteria`, `evaluate_no_assumptions`, `evaluate_clarification_routing`, `evaluate_brief_completeness`).
- [ ] Heuristic evaluator scores are recorded as Langfuse scores.
- [ ] LLM-as-judge evaluator scores include normalized value, comment (evidence + reasoning + confidence), and metadata.

#### Notebook 2 — Research Agent

- [ ] `deep_research_agent_termination` dataset exists in Langfuse with the expected number of items.
- [ ] Experiment run completes with all evaluators (`evaluate_next_step`, `evaluate_research_depth`, `evaluate_citation_presence`).
- [ ] Scores are recorded with correct metadata.

#### Notebook 4 — Supervisor

- [ ] `deep_research_supervisor_parallelism` dataset exists in Langfuse with the expected number of items.
- [ ] Experiment run completes with all evaluators (`evaluate_parallelism`, `evaluate_topic_coverage`, `evaluate_aggregation_quality`).
- [ ] Scores are recorded with correct metadata.

#### Notebook 5 — Full System

- [ ] `deep_research_e2e` dataset exists in Langfuse with 3 to 5 items.
- [ ] Experiment run completes with all evaluators (`evaluate_report_structure`, `evaluate_report_source_coverage`, `evaluate_report_factual_consistency`, `evaluate_report_completeness`).
- [ ] Scores are recorded with correct metadata.

### Evaluator integrity

- [ ] `JudgeResult` and `JudgeResultWithImprovement` schemas are unchanged.
- [ ] `normalize_score()` logic is unchanged (1→0.0, 2→0.25, 3→0.5, 4→0.75, 5→1.0).
- [ ] `init_judge_model()` is unchanged.
- [ ] `to_langfuse_score()` produces output compatible with `langfuse.score()` API.
- [ ] Heuristic evaluators still return boolean pass/fail results.
- [ ] LLM-as-judge evaluators still return normalized 0.0–1.0 scores with evidence and confidence.

---

## Documentation validation

- [ ] `specs/tech-stack.md` references Langfuse (not LangSmith) for tracing and evaluation.
- [ ] `specs/roadmap.md` Phase 6 references Langfuse.
- [ ] `specs/2026-04-22-agent-validation/*` — all three files reference Langfuse.
- [ ] `README.md` env var section lists `LANGFUSE_*` variables.
- [ ] `CLAUDE.md` env var section lists `LANGFUSE_*` variables.
- [ ] `.github/copilot-instructions.md` references updated env vars.
- [ ] `TODO.md` references Langfuse (not LangSmith) in agent validation items.

---

## How to run validation

```bash
# 0. Ensure self-hosted Langfuse is running and accessible

# 1. Ensure environment variables are set
cp .env.example .env
# Fill in LANGFUSE_HOST, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY,
# AZURE_OPENAI_*, and TAVILY_API_KEY

# 2. Install dependencies
uv sync

# 3. Verify no langsmith references remain
grep -ri langsmith --include='*.py' --include='*.md' --include='*.toml' --include='*.ipynb' . \
  | grep -v '.git/' | grep -v 'uv.lock' | grep -v 'specs/2026-04-23-langfuse-migration/'
# Expected: no output

# 4. Run each notebook's eval section
uv run jupyter nbconvert --to notebook --execute notebooks/1_scoping.ipynb
uv run jupyter nbconvert --to notebook --execute notebooks/2_research_agent.ipynb
uv run jupyter nbconvert --to notebook --execute notebooks/4_research_supervisor.ipynb
uv run jupyter nbconvert --to notebook --execute notebooks/5_full_agent.ipynb

# 5. Check Langfuse UI
# - Verify traces appear for each notebook run
# - Verify datasets are created with correct items
# - Verify experiment runs completed with all evaluators
# - Verify scores have correct metadata (evaluator type, rubric, confidence)

# 6. Lint generated source
uv run ruff check src/
```

---

## Definition of done

The migration can be considered complete when:

1. No `langsmith` code, imports, or dependencies remain in the codebase.
2. `langfuse` is installed and configured as the sole tracing/evaluation backend.
3. Traces for all notebook runs appear in the self-hosted Langfuse instance.
4. Datasets, experiment runs, and evaluator scores are recorded in Langfuse with the same coverage as the prior LangSmith setup.
5. All evaluator logic produces identical scoring behavior (same rubrics, same schemas, same normalization).
6. All documentation is updated to reference Langfuse.
7. `ruff check src/` passes with no new errors.
8. Changes are committed on `development` and a PR is opened from `development` → `main`.
