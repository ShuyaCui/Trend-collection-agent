# Roadmap

Phases follow the 5-notebook progression. Each phase is independently shippable. Phases 6+ address known gaps identified in the constitution.

---

## Phase 1 — Scoping Agent
**Source**: `notebooks/1_scoping.ipynb`

- [ ] Implement `ClarifyWithUser` structured output to detect when user intent is ambiguous
- [ ] Implement `ResearchQuestion` Pydantic schema to represent a structured research brief
- [ ] Build two-node LangGraph: clarification → brief generation
- [ ] Add conditional routing via `Command` (ask user or proceed)
- [ ] Date-aware prompts for context-sensitive queries

**Done when**: A user message produces either a clarifying question or a structured `ResearchQuestion` brief.

---

## Phase 2 — Research Agent (Custom Tools)
**Source**: `notebooks/2_research_agent.ipynb`

- [ ] Build LLM decision node + tool execution node (ReAct pattern)
- [ ] Integrate Tavily search with response summarization
- [ ] Implement iterative research loop with conditional exit
- [ ] Add research prompt engineering (breadth, depth, citation style)

**Done when**: Agent accepts a `ResearchQuestion` brief and returns compressed research notes with citations.

---

## Phase 3 — Research Agent (MCP)
**Source**: `notebooks/3_research_agent_mcp.ipynb`

- [ ] Set up `MultiServerMCPClient` for MCP server management
- [ ] Replace Tavily tool with MCP-served filesystem/search tools
- [ ] Validate async tool execution (MCP requires async)
- [ ] Document how to add/swap MCP servers via config

**Done when**: Research agent works identically with MCP-backed tools instead of direct Tavily calls.

---

## Phase 4 — Multi-Agent Supervisor
**Source**: `notebooks/4_research_supervisor.ipynb`

- [ ] Implement supervisor node that delegates subtopics via `ConductResearch` tool calls
- [ ] Implement `ResearchComplete` tool to signal supervisor termination
- [ ] Run worker research agents in parallel via `asyncio.gather()`
- [ ] Aggregate compressed notes from all workers into supervisor state

**Done when**: Supervisor decomposes a research brief into subtopics, delegates them in parallel, and merges results.

---

## Phase 5 — Full End-to-End System
**Source**: `notebooks/5_full_agent.ipynb`

- [ ] Compose scoping subgraph → supervisor subgraph → write node into one `StateGraph`
- [ ] Define output schemas for each subgraph to control state propagation
- [ ] Implement `final_report_generation` node to synthesize compressed notes into a report
- [ ] Thread-based conversation management for multi-turn clarification

**Done when**: A raw user query produces a complete, sourced research report end-to-end with no manual intervention.

---

## Phase 6 — Evaluation Framework
**Addresses gap**: No automated quality measurement.

- [ ] Define evaluation rubric: source coverage, factual consistency, answer completeness
- [ ] Implement LLM-as-judge evaluator (LangSmith or custom)
- [ ] Build a regression test set of benchmark research questions with expected outputs
- [ ] Add evaluation step to CI or notebook run

**Done when**: Any change to prompts or agent logic can be quantitatively assessed against the benchmark set.

---

## Phase 7 — Frontend UI
**Addresses gap**: No browser interface.

- [ ] Define API contract between LangGraph backend and frontend (streaming events, report schema)
- [ ] Scaffold minimal web UI: query input, clarification dialog, report display
- [ ] Integrate LangGraph streaming endpoint for real-time progress updates
- [ ] Add report export (Markdown, PDF)

**Done when**: An enterprise user can submit a query, answer clarifying questions, and download a report entirely through a browser — no notebook or CLI required.

---

## Deferred / Out of Scope

- Vector database / RAG over internal documents
- Multi-tenancy and user authentication
- Self-hosted search backend
- Deployment infrastructure (Docker, Helm, CI/CD)
