# Design: page-level-image-discovery-mcp

## Overview

This feature extends the current image-fetching architecture with a deterministic MCP enrichment stage that runs after Tavily identifies relevant source pages and before final image download. The design keeps Tavily as the search and result-ranking mechanism, while using MCP page tooling to extract image candidates directly from the source pages that support the research findings.

The key design decision is to treat page-level image discovery as an internal enrichment pipeline, not as a new LLM-facing research tool. This keeps the existing research-agent control loop stable while improving image coverage and attribution.

## Goals

- Discover images from Tavily-hit pages even when Tavily does not expose them in its `images` field.
- Populate page-aware metadata so each image can be traced back to a source page and nearby context.
- Preserve compatibility with the existing `ImageResult` state flow, supervisor aggregation, image download, and report embedding.
- Degrade gracefully when browser MCP tooling is unavailable by falling back to fetch / HTTP / DOM parsing.

## Non-Goals

- No independent image search workflow.
- No LLM-driven image selection or visual understanding in v1.
- No new user-facing prompt or agent-mode dedicated to MCP image search.
- No rewrite of the existing MCP notebook into the main research path.

## Architecture

```text
Tavily search
  -> deduplicated source pages
  -> page image discovery enrichment
       -> browser / Playwright MCP (preferred)
       -> fetch / HTTP / DOM MCP (fallback)
  -> normalized image candidates
  -> research state / supervisor state
  -> local image download
  -> final report Markdown embedding
```

## Components

### 1. Candidate Page Selection

The existing Tavily search flow already deduplicates source pages. That set of unique result URLs becomes the input to page-level discovery. v1 should inspect only the high-value pages already selected by the Tavily search helper rather than broadening the retrieval surface.

**Why:** this preserves current search cost and quality behavior and avoids turning page discovery into a crawl.

### 2. MCP Discovery Layer

Introduce a lazy-initialized MCP client for deterministic internal helpers, separate from the notebook 3 filesystem demo flow.

Recommended server order:

1. Browser / Playwright-style MCP server
2. Fetch / HTTP MCP server
3. DOM parsing helper built around returned HTML if the fetch server only returns raw markup

The browser path should extract:

- rendered page title
- all significant `img[src]` values
- `alt` text
- `figure > figcaption`
- `meta[property="og:image"]`
- optional surrounding DOM text for attribution

The fallback path should extract the same data from raw HTML when possible.

### 3. Normalization

Add a normalization helper that converts MCP outputs into `ImageResult` entries.

Normalization responsibilities:

- resolve relative image URLs against `source_page`
- strip obvious tracking fragments when safe
- deduplicate by normalized URL per source page
- map extracted fields into stable report-friendly metadata

Recommended v1 mapping:

- `url`: normalized absolute image URL
- `source_page`: Tavily result URL being inspected
- `title`: best available image label in order of preference: `alt` -> explicit image title -> page title
- `description`: best available contextual text in order of preference: `figcaption` -> nearby DOM text -> `og:image` context marker

If needed during implementation, `ImageResult` may be extended with optional fields such as `page_title` or `discovery_method`, but the core report path should continue to work with the existing fields.

### 4. Research-Agent Integration

The current `tavily_search` helper already extracts Tavily images and stores them for `tool_node` consumption. The new design adds page-level enrichment inside the same search helper layer so that the agent still observes one coherent search result.

Recommended flow inside the helper:

1. Run Tavily search.
2. Deduplicate result pages.
3. Extract Tavily-provided images.
4. Enrich with MCP-discovered page images.
5. Merge, deduplicate, and store the final image list.
6. Format the tool output so relevant image references remain visible to the agent.

This avoids adding a separate LLM tool call and keeps the agent policy unchanged.

### 5. Download and Report Integration

The existing local download path remains the final source of truth for report embedding. The only required changes are:

- ensure page-discovered images enter the same `images` state path
- preserve page-derived metadata in `images_metadata.json`
- continue using local relative paths during report generation when downloads succeed

## File and Notebook Impact

### Notebook 2

Primary implementation surface.

- Extend generated `utils.py` helpers for MCP discovery, normalization, and merge logic.
- Update generated `research_agent.py` only if state handling or formatted output needs adjustment.
- Update generated `prompts.py` only if the compression or writer context needs stronger instructions for page-derived images.

### Notebook 4

No structural redesign expected. Confirm supervisor aggregation remains correct for the richer image metadata.

### Notebook 5

Likely minimal updates. Ensure final report generation and download metadata use page-derived `source_page`, `title`, and `description` cleanly.

### Notebook 3

Do not turn notebook 3 into the implementation home for this feature. It remains an MCP tutorial/demo notebook. Reuse MCP patterns from it, but keep the production-path feature in notebooks 2, 4, and 5 where the main research pipeline lives.

## Error Handling

- If browser MCP inspection fails for a page, log and fall back to fetch / HTTP inspection.
- If all MCP inspection fails, retain Tavily-only images so the feature degrades to current behavior.
- If a page yields malformed image URLs, drop only those candidates, not the whole page result.
- If image downloads fail, preserve metadata and allow report generation to continue.

## Testing Strategy

Automated coverage is required for:

- normalization of relative and absolute page image URLs
- metadata extraction precedence (`alt`, `figcaption`, page title)
- fallback from browser MCP to fetch / HTTP MCP
- merging Tavily and page-discovered images without duplicate regressions
- end-to-end preservation of page-derived metadata into download and report generation inputs

Use mocks or fixtures for MCP responses so tests do not depend on live MCP servers.

## Trade-Offs

### Chosen Approach

Deterministic internal enrichment after Tavily.

**Pros**

- Minimal change to agent behavior
- Easy to fall back to current Tavily-only behavior
- Better attribution and metadata quality
- Compatible with existing report pipeline

**Cons**

- More helper complexity in notebook 2
- Requires mocked MCP interfaces for reliable tests
- Browser MCP availability may vary across environments

### Rejected Alternative

Make page discovery a separate LLM-visible MCP tool.

**Why rejected for v1**

- Increases agent planning complexity
- Makes image discovery dependent on model behavior rather than deterministic pipeline logic
- Raises regression risk in the core research loop

## Open Questions

1. Should v1 cap the number of page images per source page, or defer that until ranking exists?
2. Should `ImageResult` be extended now for `page_title` and `discovery_method`, or only if implementation pressure proves it necessary?
3. Should the formatted tool output expose all discovered images, or only a bounded subset plus metadata persistence behind the scenes?
