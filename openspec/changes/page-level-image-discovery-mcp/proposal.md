# Proposal: page-level-image-discovery-mcp

## Summary

Add page-level image discovery to the existing research pipeline so that images are not limited to Tavily's top-level `images` field. After Tavily identifies relevant source pages, the system should inspect those pages with MCP-backed page tools, extract image candidates and their surrounding context, download selected images into the report output directory, and make them available for Markdown embedding in the final report.

## Why

The current image-fetching flow is useful but shallow:

- Tavily can return image URLs, but those images are not reliably attributed to the source page that justified them.
- Many useful report images only exist in the page DOM and never appear in Tavily's `images` list.
- The writer often receives weak image context, which lowers the likelihood of correct image placement in the final Markdown report.

This change improves auditability and report quality by answering three practical questions:

- Where did the image come from?
- Which page justified including it?
- What nearby page context explains why it matters?

## What Changes

- Keep Tavily as the primary search and ranking layer for candidate pages.
- Add deterministic MCP-based page inspection after Tavily result selection.
- Use a browser or Playwright-style MCP server first to inspect rendered pages and extract:
  - `img` sources
  - `alt` text
  - `figure` / `figcaption` text
  - `og:image`
  - page title
- Fall back to fetch / HTTP / DOM parsing MCP tools when browser inspection fails or is unavailable.
- Normalize discovered image metadata into `ImageResult` records and populate `source_page`, `title`, and `description` with page-derived context.
- Preserve discovered images through research compression, supervisor aggregation, image download, and final report generation.
- Require automated coverage for the discovery and download chain.

## Non-Goals

- Replacing Tavily as the primary search backend.
- Building a separate MCP-only research agent for this feature.
- Adding image quality ranking, OCR, caption generation, or vision-model analysis.
- Adding a new external image search provider.
- Performing image editing, resizing, or thumbnail generation.
- Solving duplicate detection beyond normalized URL- and metadata-level handling in v1.

## Constraints

- Notebooks remain the source of truth; implementation must be made in notebook `%%writefile` cells, not directly in generated `src/` files.
- The feature must fit the existing LangGraph pipeline and preserve current text-only behavior.
- Browser-first MCP inspection must degrade safely to fetch / HTTP inspection without breaking research runs.
- Download failures must remain best-effort and must not block report generation.
- The output must still land in the existing `reports/<session_id>/images/` structure so current report portability expectations remain intact.

## Success Signals

- At least one end-to-end research query can discover images from source-page DOM content rather than relying only on Tavily `images` output.
- Downloaded images appear in the correct report image directory with metadata linked to the originating page.
- The final report can reference local image paths in Markdown for page-discovered images.
- Automated tests cover page discovery normalization, fallback behavior, and local download/report wiring.

## Facts and Assumptions

### Confirmed Facts

- The repository already has a Tavily-based image flow and `ImageResult` state threading.
- MCP support already exists in the codebase via `MultiServerMCPClient`.
- The roadmap's next image-related work is Phase 8 image fetching.

### Assumptions

- Suitable browser / Playwright and fetch / HTTP MCP servers will be available in the target runtime.
- Page-level extraction can be added as an internal enrichment step without changing the LLM-visible tool contract in v1.
- The existing `ImageResult` schema can be extended if page-derived metadata proves insufficient in its current form.
