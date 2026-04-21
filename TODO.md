# TODO

Current sprint items for **Phase 6 — Agent Validation** and **Phase 7 — Web UI**.
Phases 1–5 (scoping, research, MCP, supervisor, full system) are complete.

---

## Phase 6 — Agent Validation  ← current focus

### 6.1  Evaluation rubric & schema
- [ ] Define `EvaluationResult` Pydantic schema: scores for source coverage, factual consistency, answer completeness, citation quality
- [ ] Write rubric prompt in `prompts.py` (LLM-as-judge template, JSON output)

### 6.2  LangSmith evaluator
- [ ] Create `notebooks/6_evaluation.ipynb`; expose generated code to `src/` via `%%writefile`
- [ ] Implement `run_evaluator(run_id, rubric)` using LangSmith SDK
- [ ] Add `LANGSMITH_API_KEY` / `LANGSMITH_TRACING` to `.env.example`

### 6.3  Benchmark dataset
- [ ] Create `evals/benchmark.json` — 10–20 gold-standard research questions with expected source domains, key facts, and minimum section coverage
- [ ] Write `evals/run_benchmark.py` to batch-invoke the full agent and collect `EvaluationResult` per question

### 6.4  Regression guard
- [ ] Add `evals/` to `pyproject.toml` test paths
- [ ] Make `uv run pytest evals/` runnable in CI (mark slow tests `@pytest.mark.slow`)
- [ ] Document evaluation workflow in `specs/evaluation.md`

---

## Phase 7 — Web UI  ← next focus

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
