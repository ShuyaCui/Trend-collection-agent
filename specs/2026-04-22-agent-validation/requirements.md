# Requirements — Agent Validation (selected notebooks)

## Objective

Add or strengthen Langfuse-based evaluations at the end of the selected module notebooks so that changes to prompts, agent logic, or tool configuration produce measurable, comparable experiment results.

The current rollout covers:

- `notebooks/1_scoping.ipynb`
- `notebooks/2_research_agent.ipynb`
- `notebooks/4_research_supervisor.ipynb`
- `notebooks/5_full_agent.ipynb`

`notebooks/3_research_agent_mcp.ipynb` is explicitly skipped in this phase.

## Problem context

The deep research pipeline has five independently shippable modules, but the current validation effort is focused on four notebooks where either evaluation coverage is minimal or missing. Existing evals in notebooks 1, 2, and 4 use very small datasets and do not encode robust rubric-driven LLM-as-judge behavior. Notebook 5 has no end-to-end evaluation section yet. Without stronger per-module evals, prompt and agent changes can regress output quality without a measurable signal.

## Scope

### In scope

- Expand existing eval datasets for notebooks 1, 2, and 4 from 2 examples to 5 or more examples.
- Add new heuristic evaluators for structural invariants and routing behavior.
- Add new LLM-as-judge evaluators for notebooks 2, 4, and 5.
- Create an evaluation section from scratch for notebook 5.
- Add shared eval prompt templates to `prompts.py` via `%%writefile`.
- Document minimum Langfuse and model configuration in `.env.example`.
- Standardize evaluator metadata, structured outputs, and score normalization across all selected notebooks.

### Out of scope

- Validation for `notebooks/3_research_agent_mcp.ipynb`.
- MCP parity or live MCP-server validation in this phase.
- Standalone `evals/` directory or CI regression guard.
- Separate `notebooks/6_evaluation.ipynb`.
- Frontend or Web UI work.

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Current notebook coverage | **1, 2, 4, and 5 only** | Reduces scope to the notebooks currently prioritized in the plan and roadmap |
| Evaluation taxonomy | **Direct scoring for rubric-based single-output checks; pairwise reserved for future head-to-head use** | Direct scoring fits the selected evaluators, while pairwise comparison is only needed when comparing two responses directly |
| LLM-as-judge rubric | **Balanced 1–5 internal scale normalized to 0.0–1.0** | Gives enough granularity for analysis without overloading the judge |
| LLM-as-judge output contract | **Structured JSON with `score`, `reasoning`, `evidence`, and `confidence`** | Makes evaluator behavior inspectable and easier to debug |
| Judgment order | **Evidence before score** | Improves scoring reliability and reduces opaque judgments |
| Merge criteria | **Mixed gate: heuristic evaluators must pass; LLM-judge evaluators are advisory** | Heuristics are deterministic, while judge scores are more useful for trend tracking than hard gating |
| Task ordering | **Notebook 5 first, then 1, 2, and 4** | Matches the current plan ordering after Notebook 3 was removed |
| LLM-as-judge model | `azure_openai:GPT-54-2026-03-05` | User-specified judge model for new evaluator work |
| Rubric strictness | **Balanced** | Appropriate default for production-facing evaluation without making every borderline case fail |

## Advanced evaluation requirements

### Shared judge contract

Every LLM-as-judge evaluator in scope must:

- use a clear criterion definition with one measurable aspect per criterion
- require evidence before score
- include edge-case guidance for partial answers, sparse citations, and overlapping coverage
- return structured JSON that can be converted into the existing Langfuse Evaluation result shape
- expose confidence so low-confidence judgments can be spot-checked by humans

### Bias mitigation

The evaluation design must account for common judge biases:

- **Length bias**: judges must be instructed not to reward longer responses merely for being longer
- **Verbosity bias**: rubrics should reward useful detail, not generic explanation
- **Authority bias**: factual-consistency evaluation must prefer cited support over confident tone
- **Self-enhancement bias**: results are advisory because the judge may be from the same model family as the generating model

### Pairwise comparison

Pairwise comparison is not part of the selected notebook rollout. If future work adds head-to-head evaluators, the implementation must use swapped-order comparison and position-consistency checks.

## Constraints

- **Notebooks are source of truth.** All evaluation code lives in notebook cells. Any `%%writefile` cells regenerate files in `src/`. Never edit `src/` directly.
- **Langfuse dependency.** All evals require `LANGFUSE_PUBLIC_KEY`. No offline fallback is required.
- **Azure OpenAI auth.** Evaluator LLM calls use `GenAIToken`, consistent with the rest of the codebase.
- **Existing eval pattern.** Evaluators must follow the established Langfuse callback shape and integrate into `langfuse.run_experiment()`.
- **Normalized reporting.** LLM-judge evaluators must expose normalized `0.0–1.0` scores even if the underlying rubric uses `1–5`.

## Inputs and outputs

### Inputs per notebook

| Notebook | Langfuse dataset | Example format |
|---|---|---|
| 1 — Scoping | `deep_research_scoping` (expand) | `inputs: {messages}`, `outputs: {criteria}` |
| 2 — Research | `deep_research_agent_termination` (expand) | `inputs: {researcher_messages}`, `outputs: {next_step}` |
| 4 — Supervisor | `deep_research_supervisor_parallelism` (expand) | `inputs: {supervisor_messages}`, `outputs: {num_expected_threads}` |
| 5 — Full System | `deep_research_e2e` (new) | `inputs: {messages}`, `outputs: {expected_sources, expected_facts, expected_sections}` |

### Outputs

- Langfuse experiment results per selected notebook.
- Heuristic evaluators return `score: bool`.
- LLM-as-judge evaluators return normalized `score: float (0.0–1.0)` and include `reasoning`, `evidence`, and `confidence`.

## Required evaluators

### Notebook 1 — Scoping

- existing: `evaluate_success_criteria`
- existing: `evaluate_no_assumptions`
- new: `evaluate_clarification_routing`
- new: `evaluate_brief_completeness`

### Notebook 2 — Research Agent

- existing: `evaluate_next_step`
- new: `evaluate_research_depth`
- new: `evaluate_citation_presence`

### Notebook 4 — Supervisor

- existing: `evaluate_parallelism`
- new: `evaluate_topic_coverage`
- new: `evaluate_aggregation_quality`

### Notebook 5 — Full System

- new: `evaluate_report_source_coverage`
- new: `evaluate_report_factual_consistency`
- new: `evaluate_report_completeness`
- new: `evaluate_report_structure`

## Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `LANGFUSE_PUBLIC_KEY` | Yes | Langfuse auth (public key) |
| `LANGFUSE_BASE_URL` | No | Langfuse host URL |
| `AZURE_OPENAI_ENDPOINT` | Yes | Judge model endpoint |
| `AZURE_OPENAI_DEPLOYMENT` | Yes | Judge model deployment |
| `AZURE_OPENAI_API_VERSION` | Yes | API version |
| `TAVILY_API_KEY` | Yes (Notebook 5) | End-to-end evals invoke real search |

## Success criteria

- Each selected notebook ends with a runnable evaluation section.
- Heuristic evaluators detect structural regressions deterministically.
- LLM-judge evaluators produce inspectable advisory signals with evidence and confidence.
- Langfuse experiments support trend analysis across prompt and agent changes.