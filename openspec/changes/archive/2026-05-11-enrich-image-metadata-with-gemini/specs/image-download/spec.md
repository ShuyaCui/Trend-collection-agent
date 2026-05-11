## MODIFIED Requirements

### Requirement: Write filtered images_metadata.json after download
After all download attempts complete, `download_images()` SHALL write `images_metadata.json` containing ONLY images that were successfully downloaded (i.e., `local_path` is not null), and ONLY the fields `url`, `local_path`, and `description` per entry.

#### Scenario: Mix of successful and failed downloads
- **WHEN** `download_images()` is called with a list that includes both successful and failed downloads
- **THEN** `images_metadata.json` contains only entries for successfully downloaded images, each with exactly three fields: `url`, `local_path`, `description`

#### Scenario: All downloads fail
- **WHEN** every image in the input list fails to download
- **THEN** `images_metadata.json` is written as an empty JSON array `[]`

#### Scenario: Description enrichment completes before metadata write
- **WHEN** `download_images()` completes the download loop
- **THEN** `describe_images_with_gemini()` is called before `images_metadata.json` is written, so descriptions are present in the file

## ADDED Requirements

### Requirement: Call description enrichment as final step in download_images
`download_images()` SHALL call `describe_images_with_gemini()` on the list of successfully downloaded images immediately after the download loop, before writing `images_metadata.json`.

#### Scenario: Enrichment integrates into download pipeline
- **WHEN** `download_images()` is called
- **THEN** the `images_metadata.json` output contains AI-generated descriptions for images where `NANO_BANANA_FLASH_URL` is configured and calls succeed
