## Why

The `page-level-image-discovery-mcp` change added an httpx + BeautifulSoup stage inside `tavily_search` to extract images from source pages. In practice, the vast majority of Chinese content sites use JavaScript lazy-loading (`data-src` populated only after JS execution), so static HTML parsing returns 0 images for most pages. Nearly all images in the pipeline still come from Tavily directly. The added complexity (ThreadPoolExecutor, skip-set management, threading.local, per-page fetches, BS4 parsing) produces negligible benefit and introduces noise (420/403 CDN errors, corporate proxy timeouts, Instagram HTML responses). Removing it simplifies the pipeline and makes the codebase easier to maintain.

## What Changes

- **Remove** `discover_page_images()` helper from `utils.py`
- **Remove** `batch_discover_images()` helper from `utils.py`
- **Remove** `normalize_page_image()` helper from `utils.py`
- **Remove** `merge_image_lists()` helper from `utils.py`
- **Remove** `reset_page_discovery_cache()` and `_get_inspected_urls()` helpers from `utils.py`
- **Remove** `_thread_local` / `threading.local` machinery (skip set, last_search_images side-channel)
- **Simplify** `tavily_search` tool: drop the page-discovery block; keep `extract_images_from_search_results()` for Tavily-native images; store results via a simpler mechanism
- **Remove** unused imports: `BeautifulSoup`, `ThreadPoolExecutor`, `as_completed`, `threading`
- **Retain** `download_images()`, `ImageResult`, `get_last_search_images()`, and the `images_metadata.json` pipeline — these remain needed downstream
- **Archive** `page-level-image-discovery-mcp` change via `openspec archive`

Non-goal fields added to `ImageResult` (`discovery_method`, `page_title`, `alt_text`, `figcaption`, `source_page`) can be kept as optional with defaults — they add no overhead and may be useful for Tavily-provided metadata in future.

## Capabilities

### New Capabilities

*(none — this is a simplification)*

### Modified Capabilities

- `image-pipeline`: Tavily-only image discovery; httpx page-fetch stage removed.

## Impact

- `src/deep_research_from_scratch/utils.py` (generated from `notebooks/2_research_agent.ipynb` cell 7): significant reduction — ~160 lines of helpers removed
- `tests/test_page_image_discovery.py`: most tests become irrelevant and should be removed or replaced with a smoke test of `tavily_search` image extraction
- No graph-level changes to `research_agent_full.py`, `multi_agent_supervisor.py`, or state files
- `BeautifulSoup4` / `lxml` remain installed (transitive deps); no pyproject.toml changes needed
- `threading` import can be removed if no longer used elsewhere
