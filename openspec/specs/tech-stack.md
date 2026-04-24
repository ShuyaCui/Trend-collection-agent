# Tech Stack

## Current Stack

| Layer | Technology | Role |
|---|---|---|
| Orchestration | [LangGraph](https://langchain-ai.github.io/langgraph/) | Stateful agent graph execution |
| LLM abstraction | [LangChain](https://python.langchain.com/) | Model-agnostic LLM calls, tool binding |
| LLM providers | OpenAI, Anthropic, Azure OpenAI | Reasoning, structured output |
| Search | [Tavily](https://tavily.com/) | Web search with content extraction and image collection |
| Tool protocol | [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) | Standardized AI tool access |
| Language | Python 3.11+ | Runtime |
| Package management | [uv](https://docs.astral.sh/uv/) | Fast, reproducible Python environments |
| Notebooks | Jupyter | Executable tutorials; source of truth for `src/` |
| Auth (Azure) | GenAIToken (Azure AD) | Token-based LLM auth with auto-refresh |
| Tracing | [Langfuse](https://langfuse.com/) (self-hosted or cloud) | Observability and run tracing |

## Architecture Constraints

- **Notebooks are source of truth.** Files under `src/deep_research_from_scratch/` are generated via `%%writefile` cells in notebooks. Never edit `src/` directly.
- **Async where it matters.** Parallel sub-agent execution uses `asyncio.gather()`. Sequential tool loops remain synchronous for simplicity.
- **Structured output enforced at decision points.** Pydantic schemas prevent hallucinated routing (e.g., `ClarifyWithUser`, `ResearchQuestion`, `ConductResearch`, `ImageResult`).
- **Image collection.** Tavily's `include_images` parameter captures image URLs alongside text results. Images are downloaded best-effort to `reports/<session_id>/images/` with metadata stored in `images_metadata.json`.

## Known Gaps (Roadmap Items)

### 1. Frontend UI
**Status**: Not implemented — interaction today is via notebooks and LangGraph Studio.  
**Need**: Enterprise teams require a browser interface for submitting queries, reviewing reports, and re-running research.  
**Candidates**: React/Next.js frontend, LangGraph streaming API, report export (PDF/Markdown).

### 2. Evaluation Framework
**Status**: Not implemented — no automated quality measurement of research outputs.  
**Need**: Teams must be able to assess report quality, source coverage, and factual accuracy over time.  
**Candidates**: Langfuse experiments with custom rubric-based LLM-as-judge, ragas, or ARES.

## Deliberately Out of Scope

- Vector database / RAG over internal documents (search is web-only today)
- Authentication and multi-tenancy (single-user deployment assumed)
- Self-hosted search backend (Tavily is the only supported provider today)
- Deployment infrastructure (no Dockerfile, Helm chart, or CI/CD pipeline yet)

## Environment Variables

| Variable | Required | Purpose |
|---|---|---|
| `TAVILY_API_KEY` | Yes | Web search |
| `OPENAI_API_KEY` | Yes (or Anthropic) | LLM calls |
| `ANTHROPIC_API_KEY` | Yes (or OpenAI) | LLM calls |
| `AZURE_OPENAI_ENDPOINT` | Azure only | Azure OpenAI endpoint |
| `AZURE_OPENAI_DEPLOYMENT` | Azure only | Model deployment name |
| `AZURE_OPENAI_API_VERSION` | Azure only | API version |
| `LANGFUSE_PUBLIC_KEY` | No | Langfuse tracing auth |
| `LANGFUSE_SECRET_KEY` | No | Langfuse tracing auth |
| `LANGFUSE_BASE_URL` | No | Langfuse host (default: cloud) |
