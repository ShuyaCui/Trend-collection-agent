## Context

`tavily_search` currently runs two image-discovery paths in sequence:

1. **Tavily-native** (`extract_images_from_search_results`): extracts `images[]` returned directly by Tavily API — always populated, reliable.
2. **httpx page discovery** (`batch_discover_images`): fetches each Tavily result URL with httpx, parses static HTML with BeautifulSoup, extracts `<img src>` / `og:image`. Added by `page-level-image-discovery-mcp`.

End-to-end testing showed path (2) almost never produces useful results in the target domain (Chinese beauty/consumer content sites) because those pages use JavaScript lazy-loading — `<img src>` in static HTML is empty or a 1px placeholder. The complexity added (ThreadPoolExecutor, threading.local skip set, side-channel `last_search_images`, BS4 parsing, CDN Referer workarounds, trust_env=False, Instagram skip patterns) yields negligible image yield and is the source of most download error noise.

## Goals / Non-Goals

**Goals:**
- Remove `batch_discover_images`, `discover_page_images`, `normalize_page_image`, `merge_image_lists`, `reset_page_discovery_cache`, `_get_inspected_urls` from `utils.py`
- Remove `_thread_local` machinery (threading.local, skip set, last_search_images side-channel)
- Simplify `tavily_search`: keep Tavily-native images only; remove the page-fetch block
- Clean up unused imports (`bs4.BeautifulSoup`, `ThreadPoolExecutor`, `as_completed`, `threading`)
- Keep `get_last_search_images()` but reimplement without threading.local if still needed, or remove entirely if the supervisor reads images from state directly
- Remove `tests/test_page_image_discovery.py` (tests for removed code)
- Archive `page-level-image-discovery-mcp` change

**Non-Goals:**
- No changes to `download_images()` — it is still needed
- No changes to `ImageResult` schema fields (extra fields are zero-cost optional)
- No changes to LangGraph graph structure
- No changes to `research_agent_full.py` or supervisor
- No introducing a replacement image-discovery mechanism

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Image source after change | Tavily-native only (`include_images=True`) | Reliable; no network overhead beyond the existing search call |
| `ImageResult` extra fields | Keep (`discovery_method`, `source_page`, `alt_text`, etc.) | Zero cost; may be backfilled by Tavily metadata in future |
| `get_last_search_images()` | Keep as thin wrapper reading from a simple module-level list, or remove if tool_node reads from state directly | Avoids ripping out more code than necessary |
| `threading.local` | Remove entirely | Only needed for the side-channel; no other use |
| `BeautifulSoup` import | Remove | No remaining usage |
| `ThreadPoolExecutor` / `as_completed` | Remove | No remaining usage |
| `test_page_image_discovery.py` | Delete | Tests cover only removed code |

## Risks / Trade-offs

- **Image yield reduction**: Tavily-native images are limited to what Tavily exposes (typically 1–5 per query). This is the pre-`page-level-image-discovery-mcp` baseline — no regression beyond that change.
- **`get_last_search_images` interface**: If tool_node code elsewhere calls this function, it must remain (with simplified internals). Check all callers before removing.
- **Future re-introduction**: If a JS-capable rendering path becomes available (e.g., Playwright without corporate proxy), page discovery can be re-added. The `ImageResult` schema already supports it.
