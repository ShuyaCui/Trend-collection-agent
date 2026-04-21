# Copilot Repository Instructions

This repository follows spec-driven development.

## Working model
For any non-trivial feature, workflow change, or architecture change:
1. Review the existing project constitution before proposing implementation.
2. If the constitution is missing or outdated, draft or update it first.
3. Draft a feature spec before implementation.
4. Do not jump straight to code unless the task is clearly trivial.
5. After implementation, validate the result against the feature spec.

## What every feature spec should include
A feature spec should clearly define:
- objective
- user/problem context
- scope
- non-goals
- constraints
- inputs and outputs
- acceptance criteria
- validation steps
- open questions or assumptions

## Default behavior
When asked to build something substantial:
- first look for existing constitution/spec files
- reuse existing architecture and patterns where possible
- avoid broad refactors unless explicitly requested by the spec
- separate observed facts from assumptions
- surface uncertainty instead of inventing missing requirements

## Engineering preferences
- Prefer modifying existing code over rewriting from scratch.
- Prefer small, auditable changes over large speculative rewrites.
- Keep implementation aligned with current project structure and stack.
- When requirements are ambiguous, draft the spec first and make assumptions explicit.
- When validation is missing, propose concrete validation steps.

## Output preference
When drafting constitution or specs:
- write in concise markdown
- use explicit headings
- keep language concrete and actionable
- avoid vague statements like "high quality" or "good UX" without measurable meaning

# Git commit policy

After completing a set of code changes, create a git commit with:

0. For every user task where you modify repository files, create a git commit before considering the task complete. Treat the commit as part of task completion even if the user only asked for the code change and did not separately ask for a commit.

1. A concise subject line (≤72 chars) in imperative mood describing _what_ changed, e.g. `Fix _get_reflection_prompt missing def line`.
2. A body (separated by a blank line) listing:
   - Files changed and the nature of the change (added / fixed / refactored / removed).
   - Why the change was made (bug root cause, user request, or improvement rationale).
3. Always append the Co-authored-by trailer:
   ```
   Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
   ```

Commit message template:

```
<imperative summary of change>

Files changed:
- src/foo.py: <what and why>
- src/bar.py: <what and why>


---
```

## Critical Workflow Rule

**Notebooks are the source of truth.** Files in `src/deep_research_from_scratch/` are auto-generated from notebooks via Jupyter `%%writefile` magic commands. Never edit `src/` files directly — all changes must go in the corresponding notebook cell in `notebooks/`. Run the notebook cell to regenerate the source file after editing.

## Build & Lint

```bash
# Install dependencies
uv sync

# Install dev dependencies (includes ruff)
uv sync --extra dev

# Lint generated source files
ruff check src/

# Lint with auto-fix
ruff check src/ --fix

# Lint a single file
ruff check src/deep_research_from_scratch/research_agent.py
```

Ruff is configured in `pyproject.toml` with Google-style docstrings (`D` rules), isort (`I`), pyflakes (`F`), and pycodestyle (`E`). Fix lint issues in the notebook `%%writefile` cells, not in `src/` directly.

## Architecture

The system implements a three-phase deep research pipeline using LangGraph:

1. **Scope** (`research_agent_scope.py` ← notebook 1): Clarifies user intent via structured output (`ClarifyWithUser`), then generates a `ResearchQuestion` brief. Uses `Command` for conditional routing (ask clarification or proceed).

2. **Research** (`research_agent.py` ← notebook 2, `multi_agent_supervisor.py` ← notebook 4): A supervisor agent delegates topics to parallel research sub-agents via `ConductResearch` tool calls. Each sub-agent runs an LLM→tool loop (Tavily search + think_tool), then compresses findings. Sub-agents execute concurrently with `asyncio.gather()`.

3. **Write** (`research_agent_full.py` ← notebook 5): Integrates all phases into one `StateGraph`. The `final_report_generation` node synthesizes compressed research notes into a report.

### Key entry points (defined in `langgraph.json`):
- `research_agent_full.py:agent` — full end-to-end system
- `research_agent.py:researcher_agent` — standalone research agent
- `multi_agent_supervisor.py:supervisor_agent` — supervisor with sub-agents
- `research_agent_scope.py:scope_research` — scoping-only workflow

## Conventions

- **State management**: Each graph phase uses separate `TypedDict` states (`AgentState`, `ResearcherState`, `SupervisorState`) with `Annotated` fields for reducer functions (e.g., `add_messages`, `operator.add`). Output states filter what flows between subgraphs.

- **Azure OpenAI authentication**: All LLM calls use `GenAIToken` (in `Helper.py`) for Azure AD token-based auth with auto-refresh. Models are initialized via `init_chat_model("azure_openai:...")` with env vars for endpoint, deployment, and API version.

- **Structured output**: Decision points use `model.with_structured_output(PydanticSchema)` to enforce deterministic routing (e.g., `ClarifyWithUser.need_clarification` decides whether to ask the user or proceed).

- **Tools as Pydantic models**: The supervisor uses `@tool`-decorated Pydantic `BaseModel` classes (`ConductResearch`, `ResearchComplete`) as structured tool definitions rather than function-based tools.

- **Prompts**: All prompt templates live in `src/deep_research_from_scratch/prompts.py` (generated from notebooks). They use `.format()` string interpolation with variables like `{date}`, `{messages}`, `{research_brief}`.

- **Environment variables**: Required: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION`, `HEADERS_PROJECT_NAME`, `HEADERS_USERID`, `TAVILY_API_KEY`. Optional: `LANGSMITH_API_KEY`, `LANGSMITH_TRACING`.
