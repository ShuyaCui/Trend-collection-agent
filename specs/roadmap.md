# Roadmap

Phases follow the 5-notebook progression. Each phase is independently shippable.  
Phases 6–7 address known gaps identified in the constitution.  
**Current focus: Phase 6 (Agent Validation) → Phase 8 (Image Fetching) → Phase 7 (Web UI).**

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

## 🔄 Phase 6 — Agent Validation (per-module)  ← current
**Status**: In progress  
**Approach**: Evaluation lives at the end of each module notebook (not a standalone phase). Every notebook follows the Langfuse pattern: dataset → evaluator(s) → `langfuse.run_experiment()`.

### Notebook 1 — Scoping (strengthen)
Existing evals: `evaluate_success_criteria`, `evaluate_no_assumptions`.
- [ ] Expand dataset to 5+ examples (ambiguous queries, multi-topic, no-clarification-needed)
- [ ] Add `evaluate_clarification_routing` — verify clarification vs. proceed decision
- [ ] Add `evaluate_brief_completeness` — all `ResearchQuestion` fields populated

### Notebook 2 — Research Agent (strengthen)
Existing eval: `evaluate_next_step`.
- [ ] Expand dataset to 5+ examples (multi-step, single-step, topic drift, empty results)
- [ ] Add `evaluate_research_depth` — LLM-as-judge for note quality
- [ ] Add `evaluate_citation_presence` — heuristic for source URLs in notes

### Notebook 4 — Supervisor (strengthen)
Existing eval: `evaluate_parallelism`.
- [ ] Expand dataset to 5+ examples (single-topic, 3+ subtopics, overlapping)
- [ ] Add `evaluate_topic_coverage` — LLM-as-judge for decomposition quality
- [ ] Add `evaluate_aggregation_quality` — merged notes coherent and non-redundant

### Notebook 5 — Full System (gap — add end-to-end eval)
No existing evals.
- [ ] Create `deep_research_e2e` Langfuse dataset (3–5 full queries)
- [ ] Add `evaluate_report_source_coverage` — LLM-as-judge for source diversity
- [ ] Add `evaluate_report_factual_consistency` — claims match cited sources
- [ ] Add `evaluate_report_completeness` — all aspects of question addressed
- [ ] Add `evaluate_report_structure` — heuristic for expected sections

### Shared
- [ ] Add eval prompt templates to `prompts.py` via `%%writefile`
- [ ] Document `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL` setup in `.env.example`

**Done when**: Every module notebook (1–5) has a working evaluation section; running all evals produces Langfuse experiment results that detect regressions when prompts or agent logic change.

---

## 📋 Phase 8 — Research Image Fetching  ← next
**Source**: `notebooks/2_research_agent.ipynb`, `notebooks/4_research_supervisor.ipynb`, `notebooks/5_full_agent.ipynb`  **Status**: Not started
**Spec**: `specs/2026-04-22-image-fetching/`

- [ ] Add `ImageResult` Pydantic schema and `images` field to all state objects
- [ ] Enable Tavily `include_images=True` and extract image metadata in `tavily_search` tool
- [ ] Add `download_images()` utility (best-effort download with timeout, SSL-aware)
- [ ] Update `tool_node` and `compress_research` to accumulate and preserve image references
- [ ] Update supervisor to aggregate images from parallel sub-agents
- [ ] Update prompts to instruct agents on image collection and relevance
- [ ] Update `final_report_generation` to embed images via Markdown syntax
- [ ] Write `images_metadata.json` alongside downloaded images in `reports/<session_id>/images/`

**Done when**: A research query produces a final report that includes relevant images downloaded to local disk, with Markdown image references in the report body. Text-only research still works without regression.

---

## 📋 Phase 7 — Web UI
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
