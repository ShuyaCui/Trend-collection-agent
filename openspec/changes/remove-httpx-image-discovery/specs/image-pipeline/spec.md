## REMOVED Requirements

### Requirement: httpx-page-discovery
After each `tavily_search` call, the helper SHALL no longer fetch Tavily result pages with httpx + BeautifulSoup to discover additional images.

**Reason**: JS lazy-loading on target sites means static HTML parse yields near-zero images. The added complexity (ThreadPoolExecutor, threading.local, CDN workarounds) is not justified.

**Migration**: No migration needed. Downstream code that reads `discovery_method` on `ImageResult` objects will now only see `"tavily"` values. No behavioural change to `download_images` or `images_metadata.json`.

#### Scenario: page-discovery-removed
- **WHEN** `tavily_search` is called with any query
- **THEN** the tool SHALL NOT make any additional HTTP requests to Tavily result URLs beyond the Tavily API call itself

#### Scenario: images-still-populated
- **WHEN** `tavily_search` returns results that include Tavily-native images
- **THEN** `get_last_search_images()` SHALL return those images with `discovery_method = "tavily"`

## MODIFIED Requirements

### Requirement: image-side-channel
`get_last_search_images()` SHALL remain callable and return the list of `ImageResult` objects from the most recent `tavily_search` call.

#### Scenario: side-channel-readable
- **WHEN** `tavily_search` completes successfully
- **THEN** `get_last_search_images()` SHALL return the Tavily-native images extracted during that call

#### Scenario: side-channel-empty-on-no-results
- **WHEN** `tavily_search` returns results with no images
- **THEN** `get_last_search_images()` SHALL return an empty list
