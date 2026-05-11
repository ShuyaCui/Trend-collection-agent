# Tasks: page-level-image-discovery-mcp

## Group 1 — Schema Extension

- [x] Extend `ImageResult` in `state_research.py` (via Notebook 2 `%%writefile` cell) with 4 new optional fields: `discovery_method: str = "tavily"`, `page_title: str = ""`, `alt_text: str = ""`, `figcaption: str = ""`.
- [x] Verify all existing code that reads `ImageResult` (tool_node, compress_research, supervisor aggregation, download_images, report generation) still works with no changes — new fields have safe defaults.

## Group 2 — Page Fetch and Parse Helpers

- [x] Add cross-call URL skip set as `_inspected_page_urls: contextvars.ContextVar[set[str]]` in `utils.py` alongside `_last_search_images`; expose `reset_page_discovery_cache()` for test isolation.
- [x] Add `normalize_page_image(tag, base_url: str, page_title: str) -> ImageResult | None` in `utils.py`: resolve `src` via `urljoin`, filter `data:` URIs and SVG blobs, populate `title` (alt > tag title > page_title), `description` from nearest `<figcaption>`, `source_page`, `discovery_method="httpx"`, `alt_text`, `figcaption`, `page_title`.
- [x] Add `discover_page_images(url: str, session: httpx.Client) -> list[ImageResult]` in `utils.py`: GET with `verify=False, timeout=10, follow_redirects=True`; parse with `BeautifulSoup(html, "lxml")`; extract `img` tags + `og:image`; call `normalize_page_image` for each; cap at 10; return `[]` on any exception with a WARNING log.
- [x] Add `batch_discover_images(urls: list[str], max_concurrent: int = 3) -> list[ImageResult]` in `utils.py`: filter already-inspected URLs via skip set; run `discover_page_images` concurrently under `ThreadPoolExecutor`; update skip set after batch completes.

## Group 3 — Pipeline Integration

- [x] Add `merge_image_lists(tavily: list[ImageResult], page: list[ImageResult]) -> list[ImageResult]` in `utils.py`: URL dedup, backfill `source_page` and page-context fields on Tavily entries that match a page-discovered URL, preserve Tavily entry order, append new page entries after.
- [x] Update `tavily_search` tool in `utils.py` to call `batch_discover_images(result_urls)` and then `merge_image_lists(tavily_images, page_images)` before `_last_search_images.set(merged)`. Tool uses `ThreadPoolExecutor` (sync) rather than async since `@tool` is sync.

## Group 4 — Validation

- [x] Add unit tests for `normalize_page_image`: relative URL → absolute, `data:` URI filtered, `alt` over `title` over `page_title` priority, figcaption extracted from parent `<figure>`, returns `None` for SVG blob src.
- [x] Add unit tests for `merge_image_lists`: Tavily-only, page-only, overlap → dedup + `source_page` backfill, output order (Tavily first, then new page entries).
- [x] Add unit tests for `batch_discover_images` with mocked httpx responses: per-page cap of 10 enforced, semaphore limits ≤3 concurrent fetches, skip set prevents re-fetching already-seen URLs, returns `[]` cleanly on HTTP error.
- [x] Add integration smoke tests: verify `tavily_search` calls `batch_discover_images` with result URLs and passes page images through `merge_image_lists`. (28/28 tests pass.)
- [x] Run `ruff check src/ --fix` — all checks passed after fixing import ordering in notebook cells.

## Group 5 — Review

- [ ] Confirm `images_metadata.json` output from an end-to-end run includes `source_page` populated for page-discovered images (manual verification with one real research query).
- [ ] Review notebook/source-of-truth boundaries before merge: all changes in notebook `%%writefile` cells, none in `src/` directly.
- [ ] Open PR from `development` → `main` for human review.
