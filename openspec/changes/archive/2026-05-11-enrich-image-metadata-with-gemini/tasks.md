## 1. Environment & Configuration

- [x] 1.1 Add `NANO_BANANA_FLASH_URL` to `.env` pointing to `gemini-2.5-flash:generateContent` endpoint (same base URL as `NANO_BANANA_URL`, replace `gemini-2.5-flash-image` with `gemini-2.5-flash`)

## 2. Implement `describe_images_with_gemini()`

- [x] 2.1 In `notebooks/utils.py` (the `%%writefile` cell for `utils.py`), add helper `_image_to_inline_part(path)` that base64-encodes a local image file and returns a Gemini `inlineData` part dict (mirror of `file_to_inline_part` in ICIE_SOE)
- [x] 2.2 Add `describe_images_with_gemini(images: list[ImageResult]) -> list[ImageResult]` function that: reads `NANO_BANANA_FLASH_URL`, `HEADERS_USERID`, `HEADERS_PROJECT_NAME`; logs a warning and returns input unchanged if URL is unset; for each image with `local_path`, calls Gemini with the image + description prompt; updates `img.description`; catches all exceptions per image and logs warning on failure
- [x] 2.3 Write the Gemini prompt: "Describe this image concisely in 1-3 sentences. If the image shows a juice product, include its color, texture, opacity, and any decorations such as fruit garnish, ice, glass style, or packaging. Focus on visually distinctive properties."

## 3. Integrate into `download_images()`

- [x] 3.1 In the same `%%writefile` cell, after the download loop, call `describe_images_with_gemini(updated)` and reassign the result to `updated`
- [x] 3.2 Change the metadata write to filter: only include images where `local_path` is not null, and only serialize `url`, `local_path`, `description` fields

## 4. Regenerate Source & Lint

- [x] 4.1 Run the modified `%%writefile` notebook cell to regenerate `src/deep_research_from_scratch/utils.py`
- [x] 4.2 Run `ruff check src/deep_research_from_scratch/utils.py --fix` and fix any remaining lint issues in the notebook cell

## 5. Backfill Existing Report

- [x] 5.1 Run `describe_images_with_gemini()` against the existing report `reports/af70fd80-6c12-497c-af87-c9fee8d1305c/images/` to generate descriptions for the 99 already-downloaded images and rewrite `images_metadata.json` with the filtered 3-field format

## 6. Commit

- [x] 6.1 Commit spec artifacts (`openspec/changes/enrich-image-metadata-with-gemini/`) to `development` branch
- [x] 6.2 Commit implementation changes (`notebooks/utils.py`, regenerated `src/deep_research_from_scratch/utils.py`, `.env` update) to `development` branch
