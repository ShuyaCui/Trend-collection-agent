# Implementation Plan: Page-Level Image Discovery MCP

## Overview

Add a page-level image discovery enrichment stage to the existing Tavily-based image pipeline. The implementation should remain notebook-first, keep Tavily as the primary search step, and insert deterministic MCP page inspection before local download and report generation.

---

## Phase A — Skeleton

### Group 1 — MCP Inspection Foundation

Goal: establish the production-path MCP configuration and helper boundaries without changing the user-facing research loop.

#### 1.1 Define page inspection MCP configuration

- **Files**: `notebooks/2_research_agent.ipynb` → generated `utils.py`
- Add lazy MCP client setup for page inspection.
- Configure browser / Playwright MCP as the preferred path.
- Configure fetch / HTTP MCP as the fallback path.

#### 1.2 Define normalization boundaries

- **Files**: `notebooks/2_research_agent.ipynb` → generated `utils.py`, optionally `state_research.py`
- Decide whether the existing `ImageResult` schema is sufficient.
- Add helper interfaces for converting page-inspection outputs into `ImageResult`.

---

## Phase B — Main Logic

### Group 2 — Page Discovery and Metadata Extraction

Goal: inspect Tavily-selected pages and extract usable page-derived image metadata.

#### 2.1 Add browser-first extraction helper

- **Files**: `notebooks/2_research_agent.ipynb` → generated `utils.py`
- Extract page title, rendered images, `alt` text, `figcaption`, and `og:image`.
- Resolve relative URLs against the source page URL.

#### 2.2 Add fetch / HTTP fallback helper

- **Files**: `notebooks/2_research_agent.ipynb` → generated `utils.py`
- Parse raw HTML when browser inspection fails.
- Return the same normalized intermediate structure as the browser path.

#### 2.3 Merge Tavily and page-derived images

- **Files**: `notebooks/2_research_agent.ipynb` → generated `utils.py`
- Merge page-derived images with Tavily-provided images.
- Deduplicate without regressing current Tavily behavior.
- Populate `source_page`, `title`, and `description` from page context.

### Group 3 — Pipeline Wiring

Goal: ensure discovered page images survive the full research flow.

#### 3.1 Preserve page-derived images in the researcher path

- **Files**: `notebooks/2_research_agent.ipynb` → generated `research_agent.py`, `prompts.py`
- Keep discovered images available to `tool_node` and compression.
- Strengthen formatted output or prompts only as needed to preserve image relevance.

#### 3.2 Verify supervisor aggregation compatibility

- **Files**: `notebooks/4_research_supervisor.ipynb` → generated `multi_agent_supervisor.py`
- Confirm richer image metadata merges cleanly across sub-agents.

#### 3.3 Keep report generation and local download aligned

- **Files**: `notebooks/5_full_agent.ipynb` → generated `research_agent_full.py`, `prompts.py`
- Ensure page-discovered images are downloaded to `reports/<session_id>/images/`.
- Ensure report generation can embed local paths for those images.

---

## Phase C — Edge Cases, Tests, Docs

### Group 4 — Automated Validation

Goal: add the automated coverage required by the merge criteria.

#### 4.1 Add unit tests for normalization and fallback

- **Files**: `tests/`
- Cover relative URL resolution.
- Cover metadata precedence (`alt`, `figcaption`, page title).
- Cover browser-failure fallback to fetch / HTTP.

#### 4.2 Add pipeline tests for image preservation

- **Files**: `tests/`
- Cover merged image propagation into report/download inputs.
- Cover no-regression behavior when page discovery returns nothing.

### Group 5 — Cleanup and Documentation

Goal: validate notebook-driven generation and document any scope deltas.

#### 5.1 Run targeted quality checks

- Run `ruff check src/` after regenerating source files.
- Run targeted tests covering the modified path.

#### 5.2 Sync spec context if implementation diverges

- **Files**: current feature spec artifacts, plus roadmap/tech-stack only if the implementation changes long-term project assumptions.
- Record any schema or MCP-environment assumptions discovered during implementation.
