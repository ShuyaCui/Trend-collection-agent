# Requirements — LangSmith → Langfuse Migration

> **Status: ARCHIVED — Implementation complete as of 2026-04-24.**

## Objective

Replace all LangSmith integration (runtime tracing and agent validation experiments) with Langfuse across the deep research pipeline. After this work, no LangSmith code, imports, or dependencies remain in the codebase.

## Problem context

The platform currently uses LangSmith for two purposes:

1. **Runtime tracing** — `LANGSMITH_TRACING`, `LANGSMITH_PROJECT`, `LANGSMITH_API_KEY` env vars enable LangGraph/LangChain trace capture. Notebooks 4 and 5 print LangSmith trace URLs for debugging.
2. **Agent validation** — `langsmith.Client` manages datasets, runs experiments via `evaluate()`/`aevaluate()`, and records evaluator scores. Notebooks 1, 2, 4, and 5 each have an evaluation section that follows this pattern.

The team is migrating to a **self-hosted Langfuse instance**. This requires replacing both the tracing integration and the evaluation framework while keeping existing evaluator logic (rubrics, `JudgeResult` schema, scoring) unchanged.

## Scope

### In scope

- Replace LangSmith tracing with Langfuse `CallbackHandler` in notebooks 1, 2, 4, 5.
- Replace LangSmith evaluation (datasets, `evaluate()`, experiment results) with Langfuse SDK (datasets, items, experiment runs, scores) in notebooks 1, 2, 4, 5.
- Update `notebooks/utils.py`: rename `to_langsmith_result` → Langfuse-compatible helper (e.g., `to_langfuse_score`); remove LangSmith-specific formatting.
- Replace `langsmith` dependency with `langfuse` in `pyproject.toml`; run `uv sync` to regenerate `uv.lock`.
- Replace env vars: `LANGSMITH_API_KEY`, `LANGSMITH_TRACING`, `LANGSMITH_PROJECT` → `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`.
- Update documentation:
  - `specs/tech-stack.md` — tracing row, env var table, evaluation candidates
  - `specs/roadmap.md` — Phase 6 description, "Done when" criteria
  - `specs/2026-04-22-agent-validation/*` — all three files (`requirements.md`, `plan.md`, `validation.md`)
  - `README.md` — env var examples
  - `CLAUDE.md` and `.github/copilot-instructions.md` — env var references
  - `TODO.md` — replace LangSmith references in agent validation and shared infrastructure sections

### Non-goals

- Adding new evaluators or changing evaluator logic (rubrics, scoring, bias mitigation).
- Changing agent behavior, prompts, or pipeline structure.
- Supporting dual-backend (LangSmith + Langfuse simultaneously).
- Migrating historical LangSmith data or experiments to Langfuse.
- Changes to `notebooks/3_research_agent_mcp.ipynb` (no LangSmith usage exists there).
- Deploying or configuring the Langfuse server itself (assumed already running).
- Making Langfuse optional — it is now required for tracing and evaluation.

## Key decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Tracing integration method | **CallbackHandler** (`langfuse.callback.CallbackHandler`) | LangChain-native, drop-in replacement. Pass as `callbacks=[handler]` to any `invoke()` / `ainvoke()` call. Minimal code changes. |
| Evaluation integration method | **Langfuse SDK** (`langfuse.Langfuse`) | Langfuse provides native dataset/experiment APIs: `create_dataset()`, `dataset.items`, `get_langchain_handler()`, `langfuse.score()`. Maps cleanly to the existing LangSmith pattern. |
| Hosting model | **Self-hosted** | Team requirement. `LANGFUSE_HOST` points to the internal Langfuse server. |
| Dependency management | **Remove `langsmith` entirely, add `langfuse`** | Clean cutover. No optional/dual dependency. |
| Backend requirement | **Required** | `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` must be set. No graceful no-op fallback. |
| Evaluator logic preservation | **Unchanged** | `JudgeResult`, `JudgeResultWithImprovement`, `normalize_score()`, `init_judge_model()` remain identical. Only the result-formatting helper and client calls change. |
| Experiment pattern | **Langfuse dataset items + `get_langchain_handler()`** | Each dataset item provides a callback handler scoped to an experiment run, enabling per-item tracing and scoring. Replaces `langsmith_client.evaluate()` loop. |

## Integration patterns

### Tracing (before → after)

**Before (LangSmith):**
```python
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_PROJECT"] = "deep_research_from_scratch"
# Traces are captured automatically by LangChain/LangGraph
result = graph.invoke(input, config={...})
```

**After (Langfuse):**
```python
from langfuse.callback import CallbackHandler
handler = CallbackHandler()
result = graph.invoke(input, config={"callbacks": [handler]})
handler.flush()
```

### Evaluation (before → after)

**Before (LangSmith):**
```python
from langsmith import Client
client = Client(api_key=os.getenv("LANGSMITH_API_KEY"))
dataset = client.create_dataset("my_dataset")
client.create_examples(inputs=[...], outputs=[...], dataset_id=dataset.id)
client.evaluate(target_fn, data="my_dataset", evaluators=[eval_fn])
```

**After (Langfuse):**
```python
from langfuse import Langfuse
langfuse = Langfuse()
dataset = langfuse.create_dataset("my_dataset")
for inp, exp in zip(inputs, expected):
    dataset.create_item(input=inp, expected_output=exp)

# Experiment run
dataset = langfuse.get_dataset("my_dataset")
for item in dataset.items:
    handler = item.get_langchain_handler(run_name="experiment-1")
    result = target_fn(item.input, config={"callbacks": [handler]})
    # Score with evaluators
    for eval_fn in evaluators:
        score = eval_fn(result, item.expected_output)
        item.link(handler, run_name="experiment-1", run_metadata={...})
        langfuse.score(trace_id=handler.get_trace_id(), name=score["key"], value=score["score"], comment=score.get("comment"))
langfuse.flush()
```

## Environment variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `LANGFUSE_HOST` | Yes | Self-hosted Langfuse server URL |
| `LANGFUSE_PUBLIC_KEY` | Yes | Langfuse project public key |
| `LANGFUSE_SECRET_KEY` | Yes | Langfuse project secret key |
| `AZURE_OPENAI_ENDPOINT` | Yes | Judge model endpoint (unchanged) |
| `AZURE_OPENAI_DEPLOYMENT` | Yes | Judge model deployment (unchanged) |
| `AZURE_OPENAI_API_VERSION` | Yes | API version (unchanged) |
| `TAVILY_API_KEY` | Yes (NB5) | End-to-end evals invoke real search (unchanged) |

Variables removed: `LANGSMITH_API_KEY`, `LANGSMITH_TRACING`, `LANGSMITH_PROJECT`.

## Constraints

- **Notebooks are source of truth.** All changes must be in notebook cells (including `%%writefile` cells). Never edit `src/` directly.
- **Evaluator logic is unchanged.** Rubrics, `JudgeResult` schema, `normalize_score()`, `init_judge_model()` — all stay the same.
- **Langfuse is required.** No fallback mode. Missing env vars should produce a clear error.
- **Self-hosted only.** No Langfuse Cloud support needed at this time.
- **Existing eval pattern preserved.** The notebook eval sections still follow: create dataset → define evaluators → run experiment → record scores. Only the client/SDK calls change.

## Affected files

| File | Change type |
|------|-------------|
| `notebooks/1_scoping.ipynb` | Replace LangSmith client with Langfuse SDK in eval section |
| `notebooks/2_research_agent.ipynb` | Replace LangSmith client with Langfuse SDK in eval section |
| `notebooks/4_research_supervisor.ipynb` | Replace LangSmith tracing + eval with Langfuse |
| `notebooks/5_full_agent.ipynb` | Replace LangSmith tracing + eval with Langfuse |
| `notebooks/utils.py` | Rename `to_langsmith_result` → `to_langfuse_score`; update helper |
| `pyproject.toml` | Remove `langsmith`, add `langfuse` |
| `README.md` | Update env var examples |
| `CLAUDE.md` | Update env var references |
| `.github/copilot-instructions.md` | Update env var references |
| `TODO.md` | Replace LangSmith references |
| `specs/tech-stack.md` | Update tracing row and env var table |
| `specs/roadmap.md` | Update Phase 6 description |
| `specs/2026-04-22-agent-validation/requirements.md` | Replace LangSmith references with Langfuse |
| `specs/2026-04-22-agent-validation/plan.md` | Replace LangSmith references with Langfuse |
| `specs/2026-04-22-agent-validation/validation.md` | Replace LangSmith references with Langfuse |

## Success criteria

- No `langsmith` import, env var reference, or dependency remains in the codebase.
- Traces for all notebook runs appear in self-hosted Langfuse with correct project/session grouping.
- Datasets, experiment runs, and evaluator scores are recorded in Langfuse with the same coverage as the prior LangSmith setup.
- All existing evaluator logic produces identical scoring behavior (same rubrics, same `JudgeResult` schema, same normalization).
- `ruff check src/` passes with no new errors after notebook `%%writefile` cells are re-run.
