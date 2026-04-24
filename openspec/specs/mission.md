# Mission

## Purpose

Deep Research From Scratch is an **end-user research platform** — a production-grade AI system that enterprise teams use to conduct thorough, multi-source research on demand. Users submit a research question; the platform clarifies scope, autonomously searches the web, coordinates multiple AI agents in parallel, and delivers a structured final report.

## Problem

Enterprise knowledge workers spend substantial time on literature reviews, competitive intelligence, regulatory monitoring, and technical due diligence. Manual research is slow, inconsistent, and difficult to scale. Existing commercial deep research products (OpenAI, Perplexity, Google Gemini) are black boxes — teams cannot control the models, tools, data sources, or output format.

## Mission Statement

Provide enterprise teams with a transparent, configurable deep research platform they can own, operate, and extend — covering the full journey from intent clarification to structured report delivery.

## Target Audience

**Primary**: Enterprise teams performing recurring research tasks — analysts, engineers, strategists, compliance teams.

**Profile**:
- Work inside organizations with data governance requirements
- Need auditability: what sources were used, what reasoning was applied
- Want to customize LLMs, search providers, and report formats
- May require on-premises or private cloud deployment

## Scope

- AI-driven research pipeline: scope → research → write
- Multimodal research output: text findings and relevant images
- Multi-agent coordination for parallel topic coverage
- Configurable LLMs, search tools, and MCP servers
- Structured output (research briefs, final reports)
- LangGraph-based workflow that teams can fork and deploy

## Non-Goals

- Consumer-facing SaaS product (this is a platform, not a product UI)
- Real-time streaming chat (reports are batch-oriented)
- General-purpose chat assistant outside of research workflows

## Success Criteria

- A research question submitted by an enterprise user produces a sourced, structured report without manual intervention
- Platform components (scoping, research, writing) are independently testable and replaceable
- Teams can substitute their own LLM provider, search backend, or MCP server without core changes
