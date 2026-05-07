# Design: page-level-image-discovery-mcp

## Overview

This feature adds a deterministic page-inspection stage inside the existing `tavily_search` helper. After Tavily returns its result URLs, the helper fetches each source page with `httpx`, parses the rendered HTML with BeautifulSoup, and extracts image candidates not visible in Tavily's own `images` field. Discovered images are merged with Tavily-provided images and stored via the existing `_last_search_images` context var, so the downstream pipeline (tool_node → state → compress → supervisor → download → `images_metadata.json`) requires no structural changes.

v1 scope is intentionally narrow: **page discovery and metadata storage only**. Material enrichment and final report presentation are deferred to subsequent changes.

### Confirmed Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Trigger point | Inside `tavily_search` helper | Agent-transparent; no graph changes needed |
| Pages to inspect | All Tavily result URLs | Maximum coverage |
| Images per page cap | 10 | Prevents combinatorial explosion |
| Concurrency | `asyncio.Semaphore(3)` | Prevents rate-limit floods |
| URL dedup across calls | ✅ Cross-call skip set via context var | Revisiting pages is free |
| Browser (Playwright) | ❌ Not used | Corporate proxy intercepts Chromium HTTPS; httpx bypasses via `verify=False` |
| Primary fetch | `httpx.AsyncClient` | Only reliable HTTP path in current network environment |
| MCP fetch server | ❌ Not used in v1 | Same proxy interception risk as Playwright; simpler to use httpx directly |
| HTML parser | `BeautifulSoup4` + `lxml` | Tolerant, fast; both already in venv via transitive deps |
| Material enrichment | ❌ Deferred to v2 | Out of v1 scope |
| Report presentation | ❌ Deferred | Out of v1 scope |
| `extract_images_from_search_results()` | Unchanged | Existing Tavily image extraction stays as-is |
| `download_images()` | Unchanged | Existing download + `images_metadata.json` persistence stays as-is |
| New dependencies | None | `httpx`, `beautifulsoup4`, `lxml` already present in venv |

## Goals

- Discover images from Tavily-hit pages even when Tavily does not expose them in its `images` field.
- Populate page-aware metadata (`source_page`, `alt_text`, `figcaption`, `page_title`, `discovery_method`) so each image can be traced back to its originating page.
- Preserve full compatibility with the existing `ImageResult` state flow, supervisor aggregation, `download_images()`, and `images_metadata.json` persistence — none of those are modified.
- Degrade gracefully: if httpx fetch fails for a page, skip it and keep Tavily-only images.

## Non-Goals (v1)

- No material enrichment (`MaterialLink`, keyword matching, material library linking) — deferred to v2.
- No changes to `extract_images_from_search_results()` — Tavily image extraction stays as-is.
- No changes to `download_images()` or `images_metadata.json` schema — existing download machinery is sufficient.
- No changes to final report generation or prompt templates.
- No MCP fetch server — `httpx` is the only fetch backend.
- No Playwright or browser-based rendering.
- No LangGraph graph structure changes.

## Architecture

```text
tavily_search() helper — extended internal flow
  ├── tavily_search_multiple(include_images=True)   [existing, unchanged]
  │     └── extract_images_from_search_results()   [existing, unchanged]
  │           → tavily_images: ImageResult[] with source_page=""
  │
  ├── deduplicated result URLs (all)
  │     └── filter already-inspected URLs via cross-call skip set (context var)
  │
  ├── batch_discover_images(urls, semaphore=3)      [NEW]
  │     └── for each URL (≤3 concurrent via asyncio.Semaphore):
  │           httpx.AsyncClient.get(url, timeout=10, verify=False, follow_redirects=True)
  │           └── BeautifulSoup(html, "lxml"):
  │                 img[src] → urljoin(base_url, src)  filter data: / svg blobs
  │                 img[alt], figure>figcaption
  │                 meta[og:image], <title>
  │                 → normalize_page_image() → ImageResult[] (≤10/page)
  │                       discovery_method="httpx"
  │                       source_page=<result URL>  ← always populated
  │
  └── merge_image_lists(tavily_images, page_images) [NEW]
        ├── URL dedup (normalized)
        ├── backfill source_page on Tavily entries that match a page-discovered URL
        └── Tavily entries first; new page entries appended

_last_search_images.set(merged)
  → tool_node → state.images → compress_research → supervisor aggregation
  → download_images() [existing, unchanged]
  → images_metadata.json [existing schema, unchanged]
```

## Components

### 1. Candidate Page Selection

All Tavily result URLs become inputs to page-level discovery. A cross-call skip set stored in a `contextvars.ContextVar[set[str]]` prevents re-fetching pages already inspected during the same research session — critical because `tavily_search` is called multiple times per agent loop.

**Per-call flow:**
1. Collect all result URLs from `tavily_search_multiple` response.
2. Filter out URLs already in the skip set.
3. Pass remaining URLs to `batch_discover_images()`.
4. Add all processed URLs to the skip set.

### 2. Page Fetch Layer

All page inspection uses `httpx.AsyncClient` directly — no MCP fetch server, no Playwright.

**Why httpx only:** Testing confirmed that `httpx` with `verify=False` reaches external pages correctly in the current network environment, while Playwright and MCP-based fetch are intercepted by the corporate proxy and redirected to SSO.

```python
async with httpx.AsyncClient(
    verify=False,
    timeout=10,
    follow_redirects=True,
    headers={"User-Agent": "Mozilla/5.0 (compatible; research-agent/1.0)"},
) as session:
    resp = await session.get(url)
    html = resp.text  # passed to BeautifulSoup
```

Concurrency is controlled by `asyncio.Semaphore(3)` shared across all in-flight page requests within a single `tavily_search` call.

**HTML parsing:**
- `BeautifulSoup(html, "lxml")` — lxml for speed and malformed-HTML tolerance.
- Extract: `img[src]`, `img[alt]`, `figure > figcaption`, `meta[property="og:image"]`, `<title>`.
- Resolve relative URLs via `urllib.parse.urljoin(base_url, src)`.
- Cap at 10 images per page after dedup; filter `data:` URIs and inline SVG blobs.

### 3. Schema Extensions

Only page-context fields are added in v1. No material library types.

```python
class ImageResult(BaseModel):
    # --- existing fields (unchanged) ---
    url: str
    title: str = ""
    source_page: str = ""
    description: str = ""
    local_path: str | None = None

    # --- NEW: page discovery context ---
    discovery_method: str = "tavily"  # "tavily" | "httpx"
    page_title: str = ""
    alt_text: str = ""
    figcaption: str = ""
```

All new fields are optional with safe defaults. All existing code reading only the original five fields continues to work without modification.

### 4. Normalization

`normalize_page_image(tag, base_url, page_title)` maps a BS4 `<img>` tag to `ImageResult`:

- `url`: `urljoin(base_url, tag["src"])` — absolute URL always
- `title`: `tag.get("alt") or tag.get("title") or page_title`
- `description`: nearest `<figcaption>` text if tag is inside `<figure>`, else `""`
- `source_page`: the Tavily result URL being inspected
- `discovery_method`: `"httpx"`
- `alt_text`, `figcaption`, `page_title`: preserved as separate fields for future enrichment

`og:image` is emitted as a standalone `ImageResult` with `title` from `<title>` and `discovery_method="httpx"`.

### 5. Merge and Deduplication

`merge_image_lists(tavily_images, page_images) -> list[ImageResult]`:
- Primary dedup key: normalized URL.
- If a Tavily image URL also appears in page_images, backfill `source_page` (and page-context fields) on the Tavily entry — Tavily does not populate `source_page`.
- Page-discovered images not already in tavily_images are appended after (Tavily order preserved).

### 6. New Helper Functions (all in `utils.py` via Notebook 2)

| Function | Signature | Responsibility |
|----------|-----------|----------------|
| `discover_page_images` | `(url: str, session: httpx.AsyncClient) -> list[ImageResult]` | Fetch one page + parse + normalize |
| `batch_discover_images` | `(urls: list[str], max_concurrent: int = 3) -> list[ImageResult]` | Concurrent batch, skip-set aware |
| `normalize_page_image` | `(tag, base_url: str, page_title: str) -> ImageResult \| None` | BS4 tag → ImageResult |
| `merge_image_lists` | `(tavily: list[ImageResult], page: list[ImageResult]) -> list[ImageResult]` | Dedup + source_page backfill |

## File and Notebook Impact

### Notebook 2 (primary and only implementation surface)

- **`utils.py`**: Add `batch_discover_images`, `discover_page_images`, `normalize_page_image`, `merge_image_lists`. Add cross-call skip set context var. Update `tavily_search` tool to call batch discovery and merge before `_last_search_images.set(...)`.
- **`state_research.py`**: Extend `ImageResult` with 4 new optional fields (`discovery_method`, `page_title`, `alt_text`, `figcaption`). No new model types.
- **`research_agent.py`**: No changes — `tool_node` already reads from `get_last_search_images()`.

### Notebooks 4, 5

No changes. Supervisor aggregation and download pipeline are compatible with the richer `ImageResult` schema via `operator.add` and existing JSON serialization.

### Notebook 3

No changes — remains an MCP demo.

### Dependencies

No new packages needed. `httpx` (0.28.1), `beautifulsoup4` (4.12.3), and `lxml` (5.3.0) are already present in the venv via transitive dependencies. Optionally add them as explicit entries in `pyproject.toml` for stability.

## Error Handling

```
httpx fetch raises (timeout, connection error, non-200)?
  └──▶ log WARNING; skip page; return [] for that URL

BeautifulSoup parsing error?
  └──▶ BS4 + lxml is tolerant; malformed HTML parsed best-effort
          └──▶ no img tags found → return [] for that page; no error raised

urljoin fails or produces non-http URL?
  └──▶ drop that single img candidate; log DEBUG; continue to next tag

Data URI or inline SVG blob?
  └──▶ filter at normalization: skip if src.startswith("data:") or src.startswith("<svg")

Per-page image cap exceeded (>10)?
  └──▶ take first 10 after normalization; remainder silently dropped

All pages fail?
  └──▶ merge returns tavily_images unchanged; behavior identical to current
```

## Testing Strategy

All new helpers tested with mocked httpx responses and BS4 HTML fixtures — no live network calls.

- `normalize_page_image`: relative URL → absolute, `data:` URI filtered, `alt` priority over `title` over `page_title`, figcaption extracted from `<figure>`.
- `merge_image_lists`: Tavily-only, page-only, overlap → dedup + `source_page` backfill, output order preserved.
- `batch_discover_images`: per-page cap of 10 enforced, semaphore limits ≤3 concurrent calls, cross-call skip set prevents re-fetching already-seen URLs, `[]` returned on httpx error.
- Integration smoke test: mocked `tavily_search` output → `state.images` contains page-discovered entries with non-empty `source_page` and `discovery_method="httpx"`.

## Trade-Offs

### Chosen: httpx-only, page discovery as internal enrichment

**Pros**
- No new dependencies — all libs already in venv.
- Deterministic: same page → same images; easy to test and reproduce.
- Agent loop and graph structure unchanged; minimal regression risk.
- Degrade path is the current behavior (Tavily-only images) — zero downside on failure.

**Cons**
- SPA / JS-rendered pages: only images in static HTML are captured; dynamically injected images are missed.
- `og:image` may be the only findable image on heavily JS-driven pages.

### Rejected: MCP fetch server

Tested in current environment — same corporate proxy interception as Playwright; redirected to SSO. Adds complexity with no benefit over direct httpx.

### Rejected: Playwright

Chromium HTTPS traffic intercepted by corporate proxy; `page.content()` returns SSO login page for all external URLs. Technically installable but functionally broken in this network environment.

### Deferred to v2

- Material enrichment (`MaterialLink`, keyword matching, material library linking).
- Final report presentation changes (image ranking by material score).
- Pixel-based image feature extraction.

## Open Questions

1. Should the formatted tool output (returned by `tavily_search` to the LLM) expose all discovered images, or only a bounded subset? Default: expose all via `_last_search_images`; let existing compression handle pruning.
2. Should `httpx` SSL verification be configurable per-environment rather than always `verify=False`? Recommend making it an env-var toggle.
