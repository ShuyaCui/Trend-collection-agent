## Why

After the research pipeline downloads images, the resulting `images_metadata.json` contains empty `description` fields and many unused metadata fields, making it impossible to retrieve images by visual characteristics (e.g., juice color, texture, packaging style). We need AI-generated descriptions so the image library is semantically searchable.

## What Changes

- **New**: `describe_images_with_gemini()` function in `utils.py` — calls Gemini 2.5 flash (vision → text) for each successfully downloaded image to generate a rich description including juice color, texture, opacity, and decorations where visible.
- **Modified**: `download_images()` in `utils.py` — calls the new description function after all downloads complete, then writes a **filtered** `images_metadata.json` containing only images with a `local_path`, with only three fields: `url`, `local_path`, `description`.
- **Removed**: Images that failed to download (no `local_path`) are excluded from `images_metadata.json`.
- **Non-goals**: No changes to the `ImageResult` Pydantic model (stays rich for pipeline use); no retry logic for failed downloads; no UI or report-rendering changes.

## Capabilities

### New Capabilities

- `gemini-image-description`: Calls Gemini 2.5 flash with a downloaded image (base64-encoded) to produce a concise natural-language description emphasizing juice visual properties (color, texture, opacity, decoration, glass/packaging style).

### Modified Capabilities

- `image-download`: `download_images()` now also enriches successfully downloaded images with AI-generated descriptions and writes a trimmed metadata JSON (url + local_path + description only, no failed downloads).

## Impact

- **Code**: `notebooks/utils.py` (source of truth cell for `utils.py`) and `src/deep_research_from_scratch/utils.py` (regenerated).
- **Environment**: Requires `NANO_BANANA_FLASH_URL` env var pointing to the `gemini-2.5-flash:generateContent` endpoint (same base as `NANO_BANANA_URL` but without `-image` suffix). Also requires existing `HEADERS_USERID` and `HEADERS_PROJECT_NAME`.
- **Output**: `images_metadata.json` schema changes — fewer fields, no failed-download entries.
- **Dependencies**: `httpx`, `GenAIToken` (both already present).
- **Assumption**: `NANO_BANANA_URL` base domain/project path is the same for `gemini-2.5-flash` text endpoint; only the model name segment differs.
