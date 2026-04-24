# Plan — Agent Validation (per-module)

Task groups are ordered gaps-first, then strengthening existing evals. This revision applies the advanced-evaluation guidance so the plan distinguishes direct scoring from pairwise comparison, defines bias controls up front, and keeps heuristic gates separate from advisory LLM-judge signals.

---

## Group 0 — Shared evaluation design and infrastructure

0.1. Create `.env.example` at the repo root and document the minimum eval setup:

- `LANGFUSE_PUBLIC_KEY`
- `LANGFUSE_BASE_URL`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_DEPLOYMENT`
- `AZURE_OPENAI_API_VERSION`
- `TAVILY_API_KEY`
- Note that NB3 requires a live MCP server before evaluation.

0.2. Add new eval prompt templates to `prompts.py` via `%%writefile` in the relevant notebooks:

- `RESEARCH_DEPTH_JUDGE_PROMPT`
- `TOPIC_COVERAGE_JUDGE_PROMPT`
- `REPORT_SOURCE_COVERAGE_PROMPT`
- `REPORT_FACTUAL_CONSISTENCY_PROMPT`
- `REPORT_COMPLETENESS_PROMPT`

0.3. Make every LLM-judge prompt follow the same rubric contract:

- Use direct scoring for single-response objective or rubric-driven checks.
- Use pairwise comparison only where two outputs are being compared directly.
- Require evidence before score.
- Return structured JSON with `score`, `reasoning`, `evidence`, and `confidence`.
- Use a balanced 1–5 rubric internally, then normalize to `0.0–1.0` for Langfuse.
- Include edge-case guidance so judges handle partial answers, sparse citations, and overlapping topics consistently.

0.4. Add small shared judge helpers in notebook eval cells:

- score normalization helper (`1–5` → `0.0–1.0`)
- structured output parser / schema
- confidence extraction
- optional pairwise position-swap reconciliation helper for future head-to-head evals

0.5. Ensure `azure_openai:GPT-54-2026-03-05` is available as the judge model and document one known limitation in notebook markdown:

- some evals may judge outputs produced by the same model family, so results are advisory and should be spot-checked when scores shift materially.

0.6. Record evaluator metadata consistently in each notebook eval section:

- judge model
- prompt name
- rubric strictness (`balanced`)
- whether evaluator is `heuristic`, `direct_scoring`, or `pairwise`

---

## Group 1 — Notebook 5: Full System E2E (fill gap)

1.1. Design 3–5 eval examples for `deep_research_e2e` Langfuse dataset:

- Each example includes a full research query plus expected report characteristics.
- Reference outputs should capture `expected_sources`, `expected_facts`, and `expected_sections`.
- Cover diverse topics: commercial trend, niche technical, and at least one query with multiple sub-questions.

1.2. Implement `evaluate_report_source_coverage(outputs, reference_outputs)`:

- Direct-scoring LLM judge.
- Rubric checks source relevance, source diversity, and whether claims are grounded in cited material.
- Require explicit evidence extracted from the report before the score.

1.3. Implement `evaluate_report_factual_consistency(outputs, reference_outputs)`:

- Direct-scoring LLM judge.
- Rubric checks whether key claims are supported by cited sources and flags unsupported assertions.
- Include an edge case for partial citation support rather than treating all mixed-quality reports as full failures.

1.4. Implement `evaluate_report_completeness(outputs, reference_outputs)`:

- Direct-scoring LLM judge.
- Rubric checks whether every material aspect of the original research question is addressed.
- Penalize omission more than brevity.

1.5. Implement `evaluate_report_structure(outputs, reference_outputs)`:

- Heuristic gate.
- Check for expected sections such as introduction, findings, conclusion, and references.

1.6. Write the evaluation section at the end of `notebooks/5_full_agent.ipynb`:

- dataset creation
- judge rubric definitions
- evaluator functions
- `langfuse.run_experiment()` call
- explicit note that E2E evals always run and are not marked slow

1.7. Run the E2E evals and verify results appear in Langfuse with normalized scores, evidence, and confidence for every LLM-judge output.

---

## Group 2 — Notebook 1: Scoping (strengthen)

2.1. Expand `deep_research_scoping` dataset from 2 → 5+ examples:

- ambiguous query
- multi-topic query
- query needing no clarification
- very short query
- query with conflicting requirements

2.2. Implement `evaluate_clarification_routing(outputs, reference_outputs)`:

- Heuristic gate.
- Verify `ClarifyWithUser.need_clarification` matches the expected routing decision.

2.3. Implement `evaluate_brief_completeness(outputs, reference_outputs)`:

- Heuristic gate.
- Check all required `ResearchQuestion` fields are populated and non-empty.

2.4. Add the new evaluators to the existing `langfuse.run_experiment()` call in `notebooks/1_scoping.ipynb`.

2.5. Run and verify in Langfuse, with special attention to systematic disagreements on the ambiguous-query cases.

---

## Group 3 — Notebook 2: Research Agent (strengthen)

3.1. Expand `deep_research_agent_termination` dataset from 2 → 5+ examples:

- multi-step search needed
- topic drift scenario
- empty search results
- sufficient after one search
- conflicting sources

3.2. Implement `evaluate_research_depth(outputs, reference_outputs)`:

- Direct-scoring LLM judge using `RESEARCH_DEPTH_JUDGE_PROMPT`.
- Rubric checks depth, breadth, and usefulness of compressed notes.
- Require evidence before score and return one concrete improvement note for debugging weak runs.

3.3. Implement `evaluate_citation_presence(outputs, reference_outputs)`:

- Heuristic gate.
- Check that URLs or source references appear in compressed research notes.

3.4. Add the new evaluators to `notebooks/2_research_agent.ipynb` and keep the existing termination heuristic as a separate deterministic signal.

3.5. Run and verify in Langfuse, watching for length bias by comparing short but high-quality notes against longer but repetitive notes.

---

## Group 4 — Notebook 4: Supervisor (strengthen)

4.1. Expand `deep_research_supervisor_parallelism` dataset from 2 → 5+ examples:

- single-topic (1 thread)
- 3+ subtopics
- partially overlapping topics
- negation (`don't compare`)
- broad survey question

5.2. Implement `evaluate_topic_coverage(outputs, reference_outputs)`:

- Direct-scoring LLM judge using `TOPIC_COVERAGE_JUDGE_PROMPT`.
- Rubric checks whether decomposed subtopics cover the original question without obvious blind spots.

5.3. Implement `evaluate_aggregation_quality(outputs, reference_outputs)`:

- Direct-scoring LLM judge.
- Rubric checks coherence, non-redundancy, and whether merged notes synthesize rather than merely concatenate worker outputs.
- Include an edge case for intentional overlap so necessary repetition is not over-penalized.

5.4. Add the new evaluators to `notebooks/4_research_supervisor.ipynb` alongside the existing `evaluate_parallelism` heuristic.

5.5. Run and verify in Langfuse, especially on broad-survey examples where topic omission is more likely than outright failure.

---

## Group 6 — Final validation and merge readiness

6.1. Run all notebook eval sections sequentially (NB1 → NB2 → NB3 → NB4 → NB5) and confirm all Langfuse experiments complete.

6.2. Verify merge criteria:

- all heuristic evaluators pass on every example
- all LLM-as-judge evaluators return normalized scores, evidence, and confidence

6.3. Review score distributions, not just means:

- inspect outliers
- inspect low-confidence judgments
- inspect any systematic disagreement concentrated in a single criterion or query type

6.4. Perform a lightweight human spot-check on a small sample from each notebook eval set when judge scores look surprising, so the team can distinguish true regressions from judge drift.

6.5. Re-run all notebook `%%writefile` cells touched by the work and run `ruff check src/` to ensure generated files stay lint-clean.

6.6. Commit the implementation on `development`, then open a PR from `development` → `main` per repo policy.
