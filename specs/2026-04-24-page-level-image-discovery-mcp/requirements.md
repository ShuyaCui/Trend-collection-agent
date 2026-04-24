# Feature: Page-Level Image Discovery MCP

## Objective

Extend the existing image-fetching pipeline so that relevant images come from the actual source pages selected during research, not only from Tavily's top-level `images` field. The system should discover page images via MCP inspection, preserve page-aware metadata, download eligible images into the report image directory, and make those local files available for Markdown embedding in the final report.

## User / Problem Context

The current report pipeline can download images, but those images are only as good as Tavily's image output. That leaves three quality gaps:

- important images embedded in the source page DOM are missed entirely
- the pipeline often cannot say which page an image came from
- the report writer receives weak context and may skip or misuse otherwise relevant images

This feature improves research auditability and report usefulness by making page-level image discovery part of the main research path.

## Scope

### In Scope

- Keep Tavily as the primary search mechanism for candidate pages.
- Inspect high-value Tavily result pages with MCP tools.
- Use browser / Playwright-style MCP first and fall back to fetch / HTTP / DOM parsing MCP when needed.
- Extract page-derived image candidates from `img`, `alt`, `figcaption`, `og:image`, and page title data.
- Normalize those candidates into `ImageResult` records with `source_page`, `title`, and `description` populated from page context.
- Merge page-discovered images with Tavily-provided images before the existing download/report path.
- Download discovered images into the existing report image directory so the final Markdown report can reference local files.
- Add automated test coverage for discovery, fallback, and report/download wiring.

### Non-Goals

- Replacing Tavily as the search backend.
- Building a separate MCP-only research agent.
- Adding a new image search provider.
- Adding OCR, visual captioning, chart classification, or quality ranking.
- Editing, resizing, or transforming downloaded images.

## Constraints

- Notebook `%%writefile` cells remain the source of truth; generated `src/` files must not be edited directly.
- The feature must preserve current text-only behavior when MCP inspection yields no usable images.
- Browser MCP failure must not fail the research run; fallback and best-effort behavior are required.
- The local download location must remain compatible with the existing `reports/<session_id>/images/` convention.
- Automated tests should not require live MCP servers; mocked or fixture-driven tests are required.

## Key Decisions

| Decision                 | Choice                                                   | Rationale                                                           |
| ------------------------ | -------------------------------------------------------- | ------------------------------------------------------------------- |
| Search backbone          | Keep Tavily first                                        | Reuses existing relevance and source-selection behavior             |
| Page inspection strategy | Browser MCP first, fetch / HTTP fallback                 | Balances rendered-page fidelity with operational resilience         |
| Integration point        | Deterministic helper inside current search flow          | Avoids exposing a new LLM-facing tool and reduces agent regressions |
| Report path              | Reuse current local download and Markdown embedding path | Keeps offline portability and minimizes downstream changes          |
| Testing bar              | Require automated coverage                               | User requested merge criteria stronger than manual validation only  |

## Inputs / Outputs

### Inputs

- User research question
- Tavily search results and deduplicated candidate source pages
- MCP page inspection responses

### Outputs

- Enriched `images` state with page-aware `ImageResult` entries
- Downloaded local files under `reports/<session_id>/images/`
- `images_metadata.json` containing page-derived attribution metadata
- Final report Markdown that can embed local page-discovered images

## Open Questions / Assumptions

### Confirmed Facts

- MCP support already exists in the repository.
- The main production research path lives in notebooks 2, 4, and 5.
- The existing image pipeline already downloads images and feeds report generation.

### Assumptions

- Browser / Playwright and fetch / HTTP MCP servers will be available or configurable in the target environment.
- The current `ImageResult` shape is close enough to v1 needs, with optional extension only if implementation proves it necessary.
- Page inspection can stay deterministic and internal instead of becoming a model-planned tool action.

### Open Questions

1. Should v1 cap the number of images per page or per report?
2. Should page-title and discovery-method fields be added now or deferred?
3. Should report generation receive all discovered images or a bounded curated subset?
