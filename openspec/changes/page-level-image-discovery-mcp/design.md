# Design: page-level-image-discovery-mcp

## Objective

Extend the existing Tavily-based image workflow so that images are:

1. discovered from source-page DOM content,
2. fetched and persisted locally for report portability,
3. enriched with structured metadata,
4. linked to material library dimensions (color, texture, decoration, style),
5. preserved through the full LangGraph pipeline without changing the current LLM-facing tool contract.

## Problem Context

The current pipeline captures top-level Tavily image URLs and persists them, but it lacks:

- reliable source-page attribution,
- deterministic extraction of page-only images,
- reusable metadata fields for downstream trend analysis,
- explicit linking between discovered images and material library elements.

As a result, image usage in reports is weakly grounded and hard to reuse in material-library-driven workflows.

## Scope

### In Scope

- Browser-first MCP page inspection for Tavily-selected source pages.
- Fallback HTML-based extraction when browser inspection fails.
- URL normalization and image candidate deduplication.
- Structured metadata enrichment using page context and image asset facts.
- Catalog-constrained linking to material library entries.
- Preservation of enriched metadata in `images_metadata.json`.
- Bounded image ranking/selection for report embedding.
- Test coverage for extraction, fallback, linkage, persistence, and no-match behavior.

### Out of Scope

- Replacing Tavily as the search backend.
- Introducing a separate user-visible image search tool.
- Unconstrained vision classification that invents new taxonomy labels.
- OCR-heavy pipelines or generalized CV model integration in v1.
- Image editing, resizing, and thumbnail generation.

## Constraints

- Notebooks are source of truth. Implementation must happen in `notebooks/*.ipynb` `%%writefile` cells.
- Generated `src/deep_research_from_scratch/*.py` files are outputs, not edit targets.
- Existing state threading and report generation behavior must remain backward compatible.
- Failures in enrichment/linking must be best-effort and non-blocking.
- Output paths must remain under `reports/<session_id>/images/`.

## High-Level Architecture

```text
Tavily search (existing)
  -> dedupe result pages
  -> page discovery (new)
       -> browser MCP extractor (preferred)
       -> fetch/http/html extractor (fallback)
  -> candidate normalization (new)
  -> image fetch + asset metadata (new)
  -> material enrichment + catalog linking (new)
  -> merge with Tavily images (updated)
  -> state propagation (existing flow, richer payload)
  -> download + images_metadata.json (updated)
  -> report writer image selection (updated)
```

## Data Model Design

### Existing Base Model

`ImageResult` already carries:

- `url`
- `title`
- `source_page`
- `description`
- `local_path`

### Optional Extensions (v1)

Add optional fields so current consumers remain compatible.

#### Discovery Context

- `discovery_method`: `tavily|mcp_browser|mcp_fetch|mcp_og`
- `page_title`
- `alt_text`
- `figcaption`
- `nearby_text`
- `source_query`

#### Asset Facts

- `content_type`
- `width`
- `height`
- `file_size_bytes`
- `dominant_colors` (optional, bounded list)

#### Material Metadata

- `material_metadata.color_tags[]`
- `material_metadata.texture_tags[]`
- `material_metadata.decoration_tags[]`
- `material_metadata.style_tags[]`

#### Material Library Links

- `material_library_links[]`, each with:
  - `dimension`: `color|texture|decoration|style`
  - `target_id` (element id for dimension entries) or `target_name` (style name)
  - `matched_name`
  - `confidence`: `high|medium|low`
  - `evidence_source`: `alt_text|figcaption|nearby_text|page_title|dominant_color|combined`
  - `evidence_text`

## Pipeline Components

### 1. Candidate Page Selection

Input: deduplicated Tavily result URLs.

Rules:

- only inspect URLs already selected by Tavily,
- optionally cap page count per query for deterministic runtime,
- skip non-http(s) URLs.

Output: ordered list of candidate source pages.

### 2. Page Discovery Extractors

#### Browser Extractor (Primary)

Extract:

- page title,
- `img[src]`,
- `img[alt]`,
- figure/caption text,
- `meta[property='og:image']`,
- bounded nearby text snippet.

#### Fetch/HTML Extractor (Fallback)

Extract same fields from raw HTML when rendering is unavailable.

Failure strategy:

- page-level fallback from browser to fetch,
- if both fail, keep Tavily-only image set.

### 3. Candidate Normalization

Normalization rules:

- resolve relative image URLs against source page,
- strip known tracking parameters (bounded allowlist/denylist),
- reject malformed URLs,
- dedupe key: normalized URL + source page,
- preserve origin fields for traceability.

### 4. Asset Enrichment

On successful fetch/download:

- detect content type,
- collect dimensions and file size when available,
- optionally compute dominant colors if runtime budget allows.

If fetch fails:

- keep candidate metadata,
- leave `local_path` empty,
- continue pipeline.

### 5. Material Linking

Load catalogs:

- `material_library/color.json`
- `material_library/texture.json`
- `material_library/decoration.json`
- `material_library/style.json`

Linking strategy (deterministic first):

1. Build per-dimension candidate lexicons from catalog names + known keywords.
2. Score matches from page evidence fields (`alt_text`, `figcaption`, `nearby_text`, `page_title`).
3. Optionally boost color candidates from dominant color hints.
4. Emit bounded links per dimension with confidence + evidence.
5. If no confident match exists, emit empty links and continue.

Guardrail:

- only link to existing catalog entries,
- do not generate new taxonomy labels in v1.

### 6. Merge and State Propagation

Merge sources:

- Tavily image list,
- MCP discovered and enriched list.

Merge rules:

- prefer richer metadata when URLs collide,
- retain both if same URL has distinct source pages,
- keep stable ordering for reproducible report outputs.

State propagation:

- maintain compatibility with `ResearcherState`, supervisor aggregation, and full agent output.

### 7. Report Image Selection

When image count must be bounded, rank by:

1. material-link confidence,
2. number of dimensions linked,
3. source relevance (query/page proximity),
4. asset quality signals (format, dimensions).

Persist both:

- selected images used by report writer,
- full enriched metadata in `images_metadata.json`.

## Error Handling Matrix

- Browser MCP unavailable: use fetch/html fallback.
- Page parsing failure: skip page, continue other pages.
- Bad image URL: drop candidate only.
- Download failure: keep metadata, no local path.
- Catalog load failure: disable linking, preserve base image flow.
- Low-confidence links: persist with low confidence instead of hard-fail.

## Performance and Safety

- Bound pages per query and images per page.
- Bound nearby text extraction length.
- Use deterministic dedupe to avoid state blow-up.
- Timebox MCP page inspection and per-image fetch.
- Redact/ignore unsupported URL schemes.

## Notebook and File Impact

- Notebook 2 (`2_research_agent.ipynb`): primary implementation for extraction, normalization, enrichment, merge.
- Notebook 4 (`4_research_supervisor.ipynb`): confirm aggregated image payload remains intact.
- Notebook 5 (`5_full_agent.ipynb`): update final image ranking/selection and report metadata consumption.
- Material catalogs (read-only inputs): `material_library/*.json`.

## Acceptance Criteria

- A1: Page-level discovery finds images absent from Tavily top-level `images`.
- A2: Every retained image contains traceable source-page attribution.
- A3: Enriched metadata persists to `images_metadata.json` with backward-compatible base fields.
- A4: Material linking is catalog-constrained and includes confidence + evidence.
- A5: No-match and partial-failure cases do not block report generation.
- A6: Report writer can prioritize images with stronger material linkage when capped.

## Validation Plan

- Unit tests for URL normalization, dedupe, and field precedence.
- Unit tests for extractor fallback behavior.
- Unit tests for link scoring and confidence assignment.
- Unit tests for catalog-constrained linking and no-match handling.
- Integration tests for end-to-end metadata persistence.
- Regression tests for existing Tavily-only image flow.

## Open Questions

1. Should dominant color extraction be enabled by default or gated by config?
2. Should per-dimension link count be capped to top-1 or top-k in v1?
3. Should report image ranking be deterministic-only in v1 or allow optional LLM reranking later?
