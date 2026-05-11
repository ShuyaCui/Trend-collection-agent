## Context

The deep research pipeline downloads images found during web research into a local `reports/<id>/images/` folder. After download, it writes `images_metadata.json` — but all `description`, `title`, `alt_text`, and `figcaption` fields are empty (sources like Tavily don't provide these). The only populated field per image is `url` and, on success, `local_path`.

Currently the metadata JSON includes 8 fields per image and retains failed-download entries, making it noisy and semantically useless for retrieval.

The change adds a Gemini 2.5 flash vision call immediately after download to generate descriptions, and trims the metadata output to three fields.

**Integration point**: `download_images()` in `utils.py` (source in `notebooks/utils.py` via `%%writefile`).

## Goals / Non-Goals

**Goals:**
- Generate AI descriptions for all successfully downloaded images using Gemini 2.5 flash
- Descriptions emphasise juice visual properties (color, texture, opacity, decorations) to enable property-based retrieval
- `images_metadata.json` contains only images with `local_path`, with fields `url`, `local_path`, `description`
- Reuse `GenAIToken` auth and `httpx` patterns already in the codebase

**Non-Goals:**
- Retrying or re-downloading failed images
- Changing the `ImageResult` Pydantic model (stays rich for in-pipeline use)
- Modifying any report rendering or LangGraph state logic
- Structured/JSON output from Gemini — plain text description is sufficient

## Decisions

### D1: Call Gemini inside `download_images()`, after the download loop

**Decision**: Add description enrichment as a final step in `download_images()`, before writing the metadata JSON.

**Why**: Keeps the whole download+describe flow in one function call. The caller (`research_agent_full.py`) doesn't need to know about the description step, and `images_metadata.json` is always written once with complete data.

**Alternative considered**: Separate `enrich_image_descriptions()` called from `research_agent_full.py`. Rejected — adds complexity at the call site and risks the metadata being written before enrichment.

---

### D2: Derive `gemini-2.5-flash` text endpoint from `NANO_BANANA_FLASH_URL` env var

**Decision**: Introduce a new env var `NANO_BANANA_FLASH_URL` for the `gemini-2.5-flash:generateContent` text endpoint. This is the same infrastructure base as `NANO_BANANA_URL` but pointing to the text model.

**Why**: The image-gen model (`gemini-2.5-flash-image`) and text model (`gemini-2.5-flash`) are different endpoints. A dedicated env var is explicit and consistent with the existing `NANO_BANANA_URL` / `NANO_BANANA_PRO_URL` pattern.

**Alternative considered**: Derive URL programmatically by string-replacing `-image` in `NANO_BANANA_URL`. Rejected — brittle if URL structure changes.

---

### D3: Sequential description calls (no concurrency)

**Decision**: Call Gemini for each image one at a time.

**Why**: Simpler code, avoids rate-limit complexity. Typical report has ~100 images; at ~2s/call this is ~3 minutes, acceptable for an async background task.

**Alternative considered**: `asyncio.gather` / `ThreadPoolExecutor`. Left as a future optimisation.

---

### D4: Graceful degradation — description failure leaves field empty

**Decision**: If the Gemini call fails for an image (network error, rate limit), log a warning and leave `description` as `""`. The image is still included in metadata.

**Why**: Description enrichment must not block the report pipeline.

---

### D5: Filter metadata on write — only `url`, `local_path`, `description`

**Decision**: When serialising to `images_metadata.json`, only emit `url`, `local_path`, `description` for images where `local_path` is not null.

**Why**: Keeps the output lean and focused. The rich `ImageResult` is still used in-memory throughout the pipeline.

## Risks / Trade-offs

- **Latency**: ~100 sequential Gemini calls add ~3–5 min to pipeline. → Acceptable for now; concurrency can be added later.
- **Cost/quota**: Each call consumes Gemini quota. → No mitigation needed at current scale.
- **`NANO_BANANA_FLASH_URL` not set**: Function logs a warning and skips description enrichment entirely, writing metadata with empty descriptions. → Documented in `.env.example`.
- **Prompt hallucination**: Gemini may describe non-juice images as if they contain juice. → The prompt asks Gemini to describe juice properties *if visible*, reducing false positives.

## Open Questions

- None — requirements confirmed by user in explore session.
