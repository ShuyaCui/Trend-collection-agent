# 🧱 Design trend intelligence agent

This repo builds a deep researcher based on "deep research from scratch" from LangChain — culminating in a domain-specific design-trend intelligence system powered by a multimodal knowledge graph.

![overview](https://github.com/user-attachments/assets/b71727bd-0094-40c4-af5e-87cdb02123b4)

## 🗺️ What We Build

| Phase | Notebooks | What you get |
|-------|-----------|--------------|
| **Core Research System** | 1 – 5 | Scoping → multi-agent research → final report |
| **Domain Intelligence** | 6 – 8 | Trend extraction → material recommender → multimodal KG |

## 🚀 Quickstart

### Prerequisites

- **Python 3.11+** (required for LangGraph compatibility)
  ```bash
  python3 --version
  ```

- **[uv](https://docs.astral.sh/uv/) package manager**
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
  ```

- **Node.js / npx** (required for MCP server in notebook 3)
  ```bash
  # macOS
  brew install node
  # Ubuntu/Debian
  curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash - && sudo apt-get install -y nodejs
  ```

- **Neo4j** (required for notebook 8 — multimodal knowledge graph)

### Installation

```bash
git clone https://github.com/ShuyaCui/Trend-collection-agent
cd Trend-collection-agent
uv sync
```

### Configuration

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

```env
# Azure OpenAI (required)
AZURE_OPENAI_ENDPOINT=https://<your-endpoint>/stg/v1
AZURE_OPENAI_DEPLOYMENT=<your-deployment-name>
AZURE_OPENAI_API_VERSION=2025-04-01-preview
AZURE_CLIENT_ID=<your-client-id>
AZURE_CLIENT_SECRET=<your-client-secret>
AZURE_TENANT_ID=<your-tenant-id>

# GenAI platform headers (required)
HEADERS_USERID=<your-email>
HEADERS_PROJECT_NAME=<your-project-name>

# Web search (required for notebooks 2–5)
TAVILY_API_KEY=<your-tavily-key>

# Multimodal VLM — Gemini via proxy (required for notebook 8)
NANO_BANANA_URL=<gemini-flash-image-endpoint>
NANO_BANANA_PRO_URL=<gemini-pro-image-endpoint>
NANO_BANANA_FLASH_URL=<gemini-flash-endpoint>

# Neo4j (required for notebook 8)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<your-neo4j-password>

# Observability — optional
LANGFUSE_PUBLIC_KEY=<>
LANGFUSE_SECRET_KEY=<>
LANGFUSE_BASE_URL=http://localhost:3000
```

### Running Notebooks

```bash
uv run jupyter notebook
# or activate the venv first
source .venv/bin/activate && jupyter notebook
```

### LangGraph Studio

LangGraph Studio lets you interactively run and inspect any agent graph registered in `langgraph.json` — including the **material recommender** (notebook 7) — without writing code.

#### Start the local dev server

Run from the **repo root** (not from inside `notebooks/`):

```bash
UV_LINK_MODE=copy uvx --refresh --from "langgraph-cli[inmem]" --with-editable . \
  --python 3.11 langgraph dev
```

The server starts at `http://127.0.0.1:2024`. You should see:

```
Ready!
- API: http://127.0.0.1:2024
- Docs: http://127.0.0.1:2024/docs
- LangGraph Studio: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
```

> **Note:** `UV_LINK_MODE=copy` is required on shared filesystems where hardlinking across mount points is not permitted.

#### Open the Studio UI

1. Sign in at [smith.langchain.com](https://smith.langchain.com) (free LangSmith account required).
2. Open: **https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024**
3. Select a graph from the dropdown — all entries in `langgraph.json` appear here.

#### Remote server setup

If `langgraph dev` runs on a **remote server** (e.g., via VS Code Remote SSH), the browser on your local machine cannot reach `127.0.0.1:2024` directly. You need port forwarding:

**Option A — VS Code PORTS panel (recommended):**
1. Open the **PORTS** tab in the VS Code bottom panel *(View → Terminal → Ports, or `Ctrl+Shift+P` → "Focus on Ports View")*.
2. Click **"Forward a Port"** → enter `2024` → press Enter.
3. VS Code tunnels the remote `127.0.0.1:2024` to your local `localhost:2024`.

**Option B — SSH command (on your local terminal):**
```bash
ssh -L 2024:127.0.0.1:2024 <user>@<remote-server-ip> -N
```

After forwarding, verify `http://localhost:2024` returns `{"ok":true}` in your local browser, then open Studio.

#### Troubleshooting: Studio UI shows empty / "Failed to fetch"

If the API works (`http://localhost:2024` returns `{"ok":true}`) but Studio shows nothing:

1. **Check `.env`** — `LANGSMITH_API_KEY` must be set (Studio needs it for auth). To keep data local, also set `LANGCHAIN_TRACING_V2=false`:
   ```env
   LANGSMITH_API_KEY=lsv2_pt_...
   LANGCHAIN_TRACING_V2=false  # Studio auth works, but no trace data is uploaded
   ```

2. **Chrome blocks private network requests** — navigate to `chrome://flags/#block-insecure-private-network-requests`, set to **Disabled**, and restart Chrome.

3. **Try both URL variants** — `localhost` vs `127.0.0.1`:
   ```
   https://smith.langchain.com/studio/?baseUrl=http://localhost:2024
   https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
   ```

4. **Check browser DevTools** (F12 → Network tab) for blocked/red requests to confirm the issue.

5. **LangGraph Desktop app** (macOS only, avoids all browser restrictions):
   ```bash
   brew install --cask langgraph-studio
   ```

#### Available graphs

| Graph name | Notebook | What it does |
|---|---|---|
| `scope_research` | 1 | Clarifies user intent; produces a research brief |
| `research_agent` | 2 | Iterative web research with Tavily |
| `research_agent_mcp` | 3 | Research agent using MCP tool servers |
| `research_agent_supervisor` | 4 | Supervisor coordinating parallel sub-agents |
| `research_agent_full` | 5 | End-to-end: scope → research → report |
| `material_recommender` | 7 | Recommends design elements (colors / textures / decorations) from the material library |

#### Trying the material recommender (notebook 7)

1. Select **`material_recommender`** in the graph dropdown.
2. Send a design concept query, for example:
   ```
   设计一款以酸奶为设计概念的沐浴露，推荐颜色/质地/装饰物各3个候选
   ```
3. The agent runs two nodes — `recommend` → `attach_images` — and returns:
   - **概念分析** — concept analysis
   - **候选颜色 / 质地 / 装饰物** — recommended elements with reasoning, source report traceability, and reference images
4. Follow up in the same thread for multi-turn refinement (e.g., ask for alternatives or a different style).

#### Optional: override the model

In the Studio config panel (⚙️), set:

```json
{ "recommender_model": "azure_openai:GPT-55-2026-04-24" }
```

## 🏗️ Architecture

The system follows a three-phase pipeline:

```
User Query
    │
    ▼
┌─────────┐     ┌──────────────────────────────┐     ┌───────────┐
│  Scope  │────▶│  Research (multi-agent)       │────▶│   Write   │
│ (NB 1)  │     │  Supervisor → Sub-agents (NB 4)│     │  (NB 5)  │
└─────────┘     └──────────────────────────────┘     └───────────┘
                         │
              ┌──────────┴──────────┐
              │  Trend Intelligence  │
              │  NB 6 → NB 7 → NB 8 │
              └─────────────────────┘
```

**Key design choices:**
- **Azure OpenAI** with Azure AD token auth (auto-refresh via `GenAIToken` in `Helper.py`)
- **LangGraph** `StateGraph` for all agent workflows; subgraphs compose cleanly across phases
- **Structured output** (`model.with_structured_output(PydanticSchema)`) at every decision point
- **Parallel execution** via `asyncio.gather()` in the supervisor for concurrent sub-agents
- **Notebooks as source of truth** — `%%writefile` cells generate `src/` automatically

## 📝 Repository Layout

```
trend_agent/
├── notebooks/                    # ✏️  Edit here — source of truth
│   ├── 1_scoping.ipynb
│   ├── 2_research_agent.ipynb
│   ├── 3_research_agent_mcp.ipynb
│   ├── 4_research_supervisor.ipynb
│   ├── 5_full_agent.ipynb
│   ├── 6_trend_skill.ipynb
│   ├── 7_material_recommender.ipynb
│   ├── 8_multimodal_kg.ipynb
│   └── utils.py
├── src/trend_agent/  # ⚙️  Auto-generated — do not edit
│   ├── research_agent_scope.py
│   ├── research_agent.py
│   ├── research_agent_mcp.py
│   ├── multi_agent_supervisor.py
│   ├── research_agent_full.py
│   ├── material_recommender.py
│   ├── kg_builder.py
│   ├── kg_retrieval.py
│   ├── trend_dimensions.py
│   ├── prompts.py
│   └── Helper.py
├── history_trend_report/         # Input: raw trend report files
├── trend_knowledge/              # Output: extracted trend dimensions JSON
├── material_library/             # Input: material assets & index
├── reports/                      # Output: generated research reports
├── langgraph.json                # LangGraph entry points
└── pyproject.toml
```

> **⚠️ Development rule:** Always edit notebooks, then run `%%writefile` cells to regenerate `src/`. Never edit `src/` files directly.

## 📚 Tutorial Notebooks

### Phase 1 — Core Research System

#### Notebook 1 · Scoping (`1_scoping.ipynb`)

Clarifies research intent and produces a structured brief before any web search begins.

- `ClarifyWithUser` structured output decides whether to ask a follow-up question or proceed
- `ResearchQuestion` captures the final brief (topic, sub-questions, date context)
- LangGraph `Command` for conditional routing between ask/proceed branches

**Generates:** `research_agent_scope.py` → LangGraph entry point `scope_research`

---

#### Notebook 2 · Research Agent (`2_research_agent.ipynb`)

ReAct-style agent that iterates through search → summarise → reason cycles.

- Tavily search with per-result summarisation to fit context budgets
- `think_tool` for explicit reasoning steps between searches
- Synchronous tool execution for predictable, debuggable behaviour

**Generates:** `research_agent.py` → LangGraph entry point `research_agent`

---

#### Notebook 3 · Research Agent with MCP (`3_research_agent_mcp.ipynb`)

Swaps custom tools for MCP servers, keeping the same agent loop.

- `MultiServerMCPClient` manages stdio/HTTP MCP transports
- Config-driven server setup — drop in any MCP-compatible tool
- Async tool execution required by the MCP protocol

**Generates:** `research_agent_mcp.py` → LangGraph entry point `research_agent_mcp`

---

#### Notebook 4 · Research Supervisor (`4_research_supervisor.ipynb`)

Coordinates multiple research agents in parallel for complex, multi-faceted queries.

- Supervisor LLM issues `ConductResearch` tool calls — one per sub-topic
- Sub-agents run concurrently with `asyncio.gather()`; each has an isolated context window
- `ResearchComplete` tool signals completion and collects compressed findings

**Generates:** `multi_agent_supervisor.py` → LangGraph entry point `research_agent_supervisor`

---

#### Notebook 5 · Full End-to-End System (`5_full_agent.ipynb`)

Wires Scope + Supervisor + Write into a single `StateGraph`.

- Subgraphs with typed output schemas keep state transitions clean
- `final_report_generation` node synthesises all compressed sub-agent findings
- Thread-based conversation management for multi-turn clarification

**Generates:** `research_agent_full.py` → LangGraph entry point `research_agent_full`

---

### Phase 2 — Domain Intelligence Layer

#### Notebook 6 · Trend Dimension Extraction (`6_trend_skill.ipynb`)

Extracts structured trend dimensions from raw historical trend reports.

- Two-phase LLM pipeline: extract raw signals → normalise into canonical dimensions
- Reads all files in `history_trend_report/`, writes `trend_knowledge/dimensions.json`
- Re-run whenever new trend reports are added

**Generates:** `trend_dimensions.py` (runtime loader used by Scope and Supervisor nodes)

---

#### Notebook 7 · Material Recommender (`7_material_recommender.ipynb`)

Recommends design materials (colors, textures, decorations) from the material library based on user design queries.

- Full material library injected into LLM context (no vector search needed at current scale)
- Structured Pydantic output with post-hoc source traceability (report ID + trend heading)
- Multi-turn conversation support; cross-category associations encouraged

**Generates:** `material_recommender.py` → LangGraph entry point `material_recommender`

---

#### Notebook 8 · Multimodal Knowledge Graph (`8_multimodal_kg.ipynb`)

Builds a Neo4j knowledge graph connecting 275 product images to 107 material trend elements via VLM classification.

- **Phase A:** Upsert Neo4j nodes (products, materials, trend elements)
- **Phase B:** VLM 3-vote closed-set classification links images to material attributes
- `kg_retrieval.py` provides a clean retrieval interface over the graph
- Validation suite confirms edge coverage and classification quality

**Generates:** `kg_builder.py`, `kg_retrieval.py`

---

## 🎯 Key Learning Outcomes

| Topic | Notebooks |
|-------|-----------|
| Structured output with Pydantic | 1, 4, 7 |
| ReAct agent loops | 2, 3 |
| MCP tool integration | 3 |
| Multi-agent supervisor pattern | 4, 5 |
| Async / parallel orchestration | 4, 5 |
| Subgraph composition in LangGraph | 5 |
| LLM-based information extraction | 6 |
| Knowledge graph construction | 8 |
| Multimodal VLM classification | 8 |

## 🛠️ Development

```bash
# Install with dev dependencies (includes ruff)
uv sync --extra dev

# Lint generated source files
ruff check src/

# Auto-fix
ruff check src/ --fix
```

Fix lint issues in the notebook `%%writefile` cells, not in `src/` directly, then rerun the cell to regenerate the file.
