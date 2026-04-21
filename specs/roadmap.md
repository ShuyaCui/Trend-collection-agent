# Roadmap

Phases follow the 5-notebook progression. Each phase is independently shippable.  
Phases 6–7 address known gaps identified in the constitution.  
**Current focus: Phase 6 (Agent Validation) → Phase 7 (Web UI).**

---

## ✅ Phase 1 — Scoping Agent
**Source**: `notebooks/1_scoping.ipynb`  **Status**: Complete

- [x] Implement `ClarifyWithUser` structured output to detect when user intent is ambiguous
- [x] Implement `ResearchQuestion` Pydantic schema to represent a structured research brief
- [x] Build two-node LangGraph: clarification → brief generation
- [x] Add conditional routing via `Command` (ask user or proceed)
- [x] Date-aware prompts for context-sensitive queries

---

## ✅ Phase 2 — Research Agent (Custom Tools)
**Source**: `notebooks/2_research_agent.ipynb`  **Status**: Complete

- [x] Build LLM decision node + tool execution node (ReAct pattern)
- [x] Integrate Tavily search with response summarization
- [x] Implement iterative research loop with conditional exit
- [x] Add research prompt engineering (breadth, depth, citation style)

---

## ✅ Phase 3 — Research Agent (MCP)
**Source**: `notebooks/3_research_agent_mcp.ipynb`  **Status**: Complete

- [x] Set up `MultiServerMCPClient` for MCP server management
- [x] Replace Tavily tool with MCP-served filesystem/search tools
- [x] Validate async tool execution (MCP requires async)
- [x] Document how to add/swap MCP servers via config

---

## ✅ Phase 4 — Multi-Agent Supervisor
**Source**: `notebooks/4_research_supervisor.ipynb`  **Status**: Complete

- [x] Implement supervisor node that delegates subtopics via `ConductResearch` tool calls
- [x] Implement `ResearchComplete` tool to signal supervisor termination
- [x] Run worker research agents in parallel via `asyncio.gather()`
- [x] Aggregate compressed notes from all workers into supervisor state

---

## ✅ Phase 5 — Full End-to-End System
**Source**: `notebooks/5_full_agent.ipynb`  **Status**: Complete

- [x] Compose scoping subgraph → supervisor subgraph → write node into one `StateGraph`
- [x] Define output schemas for each subgraph to control state propagation
- [x] Implement `final_report_generation` node to synthesize compressed notes into a report
- [x] Thread-based conversation management for multi-turn clarification

---

## 🔄 Phase 6 — Agent Validation  ← current
**Source**: `notebooks/6_evaluation.ipynb`  **Status**: In progress  
**Addresses gap**: No automated quality measurement.

### Evaluation schema
- [ ] Define `EvaluationResult` Pydantic schema: `source_coverage`, `factual_consistency`, `answer_completeness`, `citation_quality` (0–10 float scores + rationale strings)
- [ ] Add rubric prompt template to `prompts.py` (LLM-as-judge, JSON output)

### LangSmith evaluator
- [ ] Create `notebooks/6_evaluation.ipynb`; expose code to `src/` via `%%writefile`
- [ ] Implement `run_evaluator(run_id, rubric)` calling LangSmith SDK
- [ ] Add `LANGSMITH_API_KEY` / `LANGSMITH_TRACING` to `.env.example`

### Benchmark dataset
- [ ] Create `evals/benchmark.json` — 10–20 gold-standard questions with expected source domains, key facts, minimum section coverage
- [ ] Write `evals/run_benchmark.py` to batch-invoke the full agent and emit `EvaluationResult` per question

### Regression guard
- [ ] Add `evals/` test path to `pyproject.toml`; mark slow tests with `@pytest.mark.slow`
- [ ] Make `uv run pytest evals/` runnable (skippable in CI without API keys via `SKIP_EVALS=1`)
- [ ] Document evaluation workflow in `specs/evaluation.md`

**Done when**: Any prompt or agent logic change can be scored against the benchmark set and regressions are detectable.

---

## 📋 Phase 7 — Web UI  ← next
**Addresses gap**: No browser interface for enterprise users.

### Tech stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI, uvicorn, `sse-starlette` (SSE streaming) |
| WebSocket | FastAPI WebSocket (bidirectional clarification dialog) |
| Frontend framework | Next.js 16, React 19, TypeScript |
| Styling | TailwindCSS, `tailwind-merge`, `clsx` |
| UI components | `lucide-react`, `framer-motion` |
| Markdown / code | `react-markdown`, `remark-gfm`, `rehype-raw`, `react-syntax-highlighter` |
| Charts / diagrams | `chart.js`, `react-chartjs-2`, `mermaid` |
| Export | `jspdf`, `html2canvas` |
| Containerization | Docker, `docker-compose.yml` |

### Backend API  (`web/backend/`)
- [ ] FastAPI app with CORS, uvicorn entry point (`run_server.py`)
- [ ] `POST /api/v1/research` — accept query, return `session_id`
- [ ] `GET  /api/v1/research/{session_id}/stream` — SSE stream of LangGraph node events
- [ ] `GET  /api/v1/research/{session_id}/report` — return final `ResearchReport` JSON
- [ ] `WS   /api/v1/ws/{session_id}` — bidirectional WebSocket for clarification dialog
- [ ] `GET  /api/v1/health` — system health check
- [ ] Add `fastapi`, `uvicorn[standard]`, `sse-starlette` to `pyproject.toml [server]` extras

### Frontend  (`web/frontend/`)
- [ ] Scaffold with `create-next-app` (Next.js 16, React 19, TypeScript, Tailwind)
- [ ] Pages: `/` (query input), `/research/[sessionId]` (live progress + clarification), `/research/[sessionId]/report` (final report viewer)
- [ ] Components: `QueryInput`, `ClarificationDialog`, `ProgressFeed`, `ReportViewer`, `ExportMenu`
- [ ] Hooks: `useResearchStream(sessionId)` (SSE), `useResearchWS(sessionId)` (WebSocket)
- [ ] `NEXT_PUBLIC_API_URL` env var pointing to FastAPI backend

### Integration & packaging
- [ ] `docker-compose.yml` — `backend` (FastAPI) + `frontend` (Next.js) services
- [ ] `Dockerfile.backend` and `Dockerfile.frontend`
- [ ] End-to-end smoke test: submit query via UI → streamed clarification → final report displayed
- [ ] Update `specs/tech-stack.md` with Web UI stack section

**Done when**: An enterprise user can submit a query, answer clarifying questions, and download a report entirely through a browser — no notebook or CLI required.

---

## Deferred / Out of Scope

- Vector database / RAG over internal documents
- Multi-tenancy and user authentication
- Self-hosted search backend
- Deployment infrastructure beyond Docker Compose (Helm, managed CI/CD)
