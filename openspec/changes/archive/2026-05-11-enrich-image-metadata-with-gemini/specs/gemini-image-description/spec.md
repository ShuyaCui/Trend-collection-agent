## ADDED Requirements

### Requirement: Generate AI description for a downloaded image
The system SHALL call Gemini 2.5 flash (vision → text) for each image that has a `local_path`, reading the image file and producing a concise English description. The description SHALL mention juice color, texture, opacity, and decorations (e.g., fruit garnish, ice, glass style, packaging) when these are visible in the image.

#### Scenario: Image shows juice product
- **WHEN** `describe_images_with_gemini()` is called with an image whose `local_path` points to a file showing a juice product
- **THEN** the returned description includes at least one visually distinctive property (color, texture, opacity, or decoration) of the juice

#### Scenario: Image does not show juice
- **WHEN** `describe_images_with_gemini()` is called with an image that does not contain juice
- **THEN** the returned description describes what is visible without fabricating juice properties

#### Scenario: Gemini call fails (network or API error)
- **WHEN** the Gemini API call raises an exception or returns a non-2xx status
- **THEN** the system logs a warning and returns an empty string for `description`; it SHALL NOT raise an exception

#### Scenario: `NANO_BANANA_FLASH_URL` is not configured
- **WHEN** `describe_images_with_gemini()` is called and `NANO_BANANA_FLASH_URL` env var is unset or empty
- **THEN** the system logs a warning, skips all Gemini calls, and returns the input list unchanged (all descriptions remain `""`)
