# Validation — Agent Validation (selected notebooks)

How to know the implementation succeeded and can be merged.

---

## Merge criteria

**Mixed gate**: heuristic evaluators must pass; LLM-as-judge evaluators are advisory.

| Evaluator type | Gate | Rationale |
|---|---|---|
| Heuristic (deterministic) | **Must pass** on every dataset example | These check structural invariants, routing, and section presence. Failures indicate concrete bugs or broken assumptions |
| LLM-as-judge (non-deterministic) | **Advisory** | Judge scores are useful for trend tracking and regression triage, but should not hard-block merges on their own |

---

## Shared evaluator expectations

Every LLM-as-judge result in scope must include:

- a normalized `score` in the `0.0–1.0` range
- `reasoning`
- explicit `evidence`
- `confidence`

Every selected notebook eval run should also preserve enough metadata to identify:

- judge model
- prompt or rubric name
- evaluator type (`heuristic` or `direct_scoring`)
- rubric strictness (`balanced`)

---

## Per-notebook acceptance criteria

### Notebook 1 — Scoping

- [ ] `deep_research_scoping` dataset has at least 5 examples in Langfuse
- [ ] `evaluate_success_criteria` runs without error on all examples
- [ ] `evaluate_no_assumptions` runs without error on all examples
- [ ] `evaluate_clarification_routing` passes on all examples
- [ ] `evaluate_brief_completeness` passes on all examples
- [ ] Langfuse experiment completes with all evaluators attached

### Notebook 2 — Research Agent

- [ ] `deep_research_agent_termination` dataset has at least 5 examples in Langfuse
- [ ] `evaluate_next_step` passes on all examples
- [ ] `evaluate_research_depth` runs without error and records score, evidence, and confidence
- [ ] `evaluate_citation_presence` passes on all examples
- [ ] Langfuse experiment completes with all evaluators attached

### Notebook 4 — Supervisor

- [ ] `deep_research_supervisor_parallelism` dataset has at least 5 examples in Langfuse
- [ ] `evaluate_parallelism` passes on all examples
- [ ] `evaluate_topic_coverage` runs without error and records score, evidence, and confidence
- [ ] `evaluate_aggregation_quality` runs without error and records score, evidence, and confidence
- [ ] Langfuse experiment completes with all evaluators attached

### Notebook 5 — Full System

- [ ] `deep_research_e2e` dataset is created with 3 to 5 examples in Langfuse
- [ ] E2E evals always run and are not hidden behind a slow marker or skip flag
- [ ] `evaluate_report_structure` passes on all examples
- [ ] `evaluate_report_source_coverage` runs without error and records score, evidence, and confidence
- [ ] `evaluate_report_factual_consistency` runs without error and records score, evidence, and confidence
- [ ] `evaluate_report_completeness` runs without error and records score, evidence, and confidence
- [ ] Langfuse experiment completes with all evaluators attached

### Notebook 3 — MCP Agent

- [ ] Not part of this validation phase
- [ ] No acceptance criteria required for `notebooks/3_research_agent_mcp.ipynb`

---

## Shared infrastructure checks

- [ ] New eval prompt templates are present in generated `prompts.py` output via notebook `%%writefile`
- [ ] `.env.example` documents Langfuse and Azure OpenAI eval setup
- [ ] All touched notebook `%%writefile` cells have been re-run so `src/` stays up to date
- [ ] `ruff check src/` passes with no errors

---

## Quality review checks

- [ ] Review score distributions, not only average scores
- [ ] Inspect low-confidence judge outputs
- [ ] Inspect systematic disagreement clustered around a single criterion or query type
- [ ] Perform a lightweight human spot-check when judge outputs look surprising or inconsistent with the artifacts

These checks are required because a judge that is consistently wrong in one class of examples is more dangerous than one with random noise.

---

## How to run validation

```bash
# 1. Ensure environment variables are set
cp .env.example .env
# Fill in LANGFUSE_PUBLIC_KEY, AZURE_OPENAI_*, and TAVILY_API_KEY

# 2. Run each selected notebook's eval section
uv run jupyter nbconvert --to notebook --execute notebooks/1_scoping.ipynb
uv run jupyter nbconvert --to notebook --execute notebooks/2_research_agent.ipynb
uv run jupyter nbconvert --to notebook --execute notebooks/4_research_supervisor.ipynb
uv run jupyter nbconvert --to notebook --execute notebooks/5_full_agent.ipynb

# 3. Verify experiments in Langfuse UI
# Check that all experiments completed and heuristic evals pass

# 4. Lint generated source
uv run ruff check src/
```

Notebook 3 is intentionally excluded from the command sequence above.

---

## Definition of done

The work can be considered complete when:

1. All selected notebooks have working evaluation sections at the end.
2. All heuristic evaluators pass on every dataset example.
3. All LLM-as-judge evaluators run without error and produce normalized scores with evidence and confidence.
4. Langfuse shows completed experiments for notebooks 1, 2, 4, and 5.
5. `ruff check src/` passes.
6. No existing non-eval notebook functionality is broken.
7. Notebook 3 remains out of scope for this validation phase.