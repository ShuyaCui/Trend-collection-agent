# TODO

Current sprint items for **Agent Validation** (per-module) and **Web UI**.
Phases 1–5 (scoping, research, MCP, supervisor, full system) are implemented.
Evaluation is performed **at the end of each module notebook**, not as a standalone phase.

---

## Agent Validation  ← current focus

Evaluation lives at the bottom of each module notebook. Every notebook follows the same pattern: create a Langfuse dataset → define evaluator(s) → run `langfuse.run_experiment()`.

### Notebook 1 — Scoping (`1_scoping.ipynb`) — strengthen existing evals
**Existing evaluators**: `evaluate_success_criteria` (LLM-as-judge), `evaluate_no_assumptions` (LLM-as-judge).
- [ ] Expand dataset from 2 → 5+ examples (add edge cases: ambiguous queries, multi-topic queries, queries that need no clarification)
- [ ] Add evaluator: `evaluate_clarification_routing` — verify the agent correctly decides to ask clarification vs. proceed (test `ClarifyWithUser.need_clarification` routing)
- [ ] Add evaluator: `evaluate_brief_completeness` — check that all fields of `ResearchQuestion` are populated (non-empty title, background, key_questions, etc.)

### Notebook 2 — Research Agent (`2_research_agent.ipynb`) — strengthen existing evals
**Existing evaluator**: `evaluate_next_step` (heuristic — continue vs. stop).
- [ ] Expand dataset from 2 → 5+ examples (add: multi-step search needed, single search sufficient, topic drift scenario, empty search results)
- [ ] Add evaluator: `evaluate_research_depth` — LLM-as-judge that scores whether the agent's final compressed notes have sufficient depth / breadth for the given question
- [ ] Add evaluator: `evaluate_citation_presence` — heuristic check that URLs/sources appear in compressed research notes

### Notebook 3 — MCP Agent (`3_research_agent_mcp.ipynb`) — add evals (gap)
**Existing evaluators**: None.
- [ ] Create Langfuse dataset `deep_research_mcp_tools` with 3+ examples testing MCP tool selection and results
- [ ] Add evaluator: `evaluate_tool_selection` — verify the agent selects the correct MCP tool for a given query type (filesystem vs. search)
- [ ] Add evaluator: `evaluate_mcp_parity` — compare MCP agent output quality against custom-tool agent output on same input (functional parity check)

### Notebook 4 — Supervisor (`4_research_supervisor.ipynb`) — strengthen existing evals
**Existing evaluator**: `evaluate_parallelism` (heuristic — correct number of threads).
- [ ] Expand dataset from 2 → 5+ examples (add: single-topic, 3+ subtopics, partially overlapping topics, negation "don't compare")
- [ ] Add evaluator: `evaluate_topic_coverage` — LLM-as-judge that checks whether the decomposed subtopics cover the original question without gaps
- [ ] Add evaluator: `evaluate_aggregation_quality` — verify merged notes from all workers are coherent and non-redundant

### Notebook 5 — Full System (`5_full_agent.ipynb`) — add end-to-end eval (gap)
**Existing evaluators**: None.
- [ ] Create Langfuse dataset `deep_research_e2e` with 3–5 full research queries + expected report characteristics (source domains, key facts, required sections)
- [ ] Add evaluator: `evaluate_report_source_coverage` — LLM-as-judge scoring how well the report cites diverse, relevant sources
- [ ] Add evaluator: `evaluate_report_factual_consistency` — LLM-as-judge checking claims against cited sources
- [ ] Add evaluator: `evaluate_report_completeness` — LLM-as-judge verifying all aspects of the research question are addressed in the report
- [ ] Add evaluator: `evaluate_report_structure` — heuristic check for expected sections (introduction, findings, conclusion, references)

### Shared infrastructure
- [ ] Add eval prompt templates to `prompts.py` via `%%writefile` (criteria judge, depth judge, report quality judge)
- [ ] Ensure `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL` are in `.env.example` with instructions

---

## Web UI  ← next focus

### 7.1  Backend API  (FastAPI + LangGraph streaming)
- [ ] Create `web/backend/` package with FastAPI app
- [ ] `POST /api/v1/research` — accept query, return `session_id`
- [ ] `GET  /api/v1/research/{session_id}/stream` — SSE stream of LangGraph node events
- [ ] `GET  /api/v1/research/{session_id}/report` — return final `ResearchReport` JSON
- [ ] WebSocket endpoint `/api/v1/ws/{session_id}` for bidirectional clarification dialog (mirrors DeepTutor `unified_ws` pattern)
- [ ] `GET  /api/v1/health` system health check
- [ ] CORS config, uvicorn entry point (`web/backend/run_server.py`)
- [ ] Add `fastapi`, `uvicorn[standard]`, `sse-starlette` to `pyproject.toml [server]` extras

### 7.2  Frontend  (Next.js 16 · React 19 · TypeScript · TailwindCSS)
- [ ] Scaffold `web/frontend/` with `create-next-app` (Next.js 16, React 19, TypeScript, Tailwind)
- [ ] Install shared UI libraries: `lucide-react`, `framer-motion`, `react-markdown`, `remark-gfm`, `rehype-raw`, `react-syntax-highlighter`, `chart.js`, `react-chartjs-2`, `mermaid`, `clsx`, `tailwind-merge`
- [ ] Pages:
  - [ ] `/` — query input with submit; minimal landing
  - [ ] `/research/[sessionId]` — live progress panel + clarification dialog
  - [ ] `/research/[sessionId]/report` — final report viewer with export buttons
- [ ] Components:
  - [ ] `QueryInput` — textarea + submit, loading state
  - [ ] `ClarificationDialog` — renders agent question, captures answer, sends over WS
  - [ ] `ProgressFeed` — streams and renders LangGraph node events (scoping → research → writing)
  - [ ] `ReportViewer` — renders Markdown report; supports Mermaid diagrams and syntax highlighting
  - [ ] `ExportMenu` — download as Markdown or PDF (`jspdf` + `html2canvas`)
- [ ] Implement streaming hook `useResearchStream(sessionId)` over SSE
- [ ] Implement WebSocket hook `useResearchWS(sessionId)` for clarification
- [ ] Environment variable: `NEXT_PUBLIC_API_URL` pointing to FastAPI backend

### 7.3  Integration & packaging
- [ ] `docker-compose.yml` — services: `backend` (FastAPI), `frontend` (Next.js), optional `langgraph-api`
- [ ] `Dockerfile.backend` and `Dockerfile.frontend`
- [ ] End-to-end smoke test: submit query via UI → receive streamed report

### 7.4  Tech stack documentation
- [ ] Update `specs/tech-stack.md` with Web UI stack section
- [ ] Add architecture diagram (Mermaid) to `README.md`

---

## Housekeeping
- [ ] Update `specs/roadmap.md` status as phases complete
- [ ] Regenerate `src/` files from notebooks before each commit (`%%writefile` cells)
- [ ] Keep `ruff check src/ --fix` clean before pushing
