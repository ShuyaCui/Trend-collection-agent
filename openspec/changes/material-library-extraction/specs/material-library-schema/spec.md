## ADDED Requirements

### Requirement: MaterialElement JSON schema definition
The system SHALL define a canonical JSON schema for individual design elements with the following required fields: id (string), dimension (enum), name (string), name_en (string), visual_keywords (array of strings), aesthetic_persona (string), signals (array of strings), maturity (enum), year_range (string), typical_use (string), source_section (string).

#### Scenario: Valid element passes schema validation
- **WHEN** a JSON object contains all required fields with correct types
- **THEN** it is accepted as a valid MaterialElement

#### Scenario: Missing required field rejected
- **WHEN** a JSON object is missing the `aesthetic_persona` field
- **THEN** the system raises a validation error

### Requirement: Three-dimension classification
Every element MUST be classified into exactly one of three dimensions: "颜色", "装饰物", "透明度与质地".

#### Scenario: Dimension values are constrained
- **WHEN** an element is created with `dimension: "纹理"`
- **THEN** validation fails because "纹理" is not in the allowed enum

#### Scenario: Texture elements use combined dimension
- **WHEN** extracting an element about "凝胶感/啫喱感" or "高折光通透"
- **THEN** it is classified under "透明度与质地" (not a separate "质地" dimension)

### Requirement: Maturity level enum
Maturity MUST be one of: "主流", "上升", "实验性".

#### Scenario: Maturity values are constrained
- **WHEN** an element is created with `maturity: "emerging"`
- **THEN** validation fails because only Chinese enum values are accepted

### Requirement: Per-report output format (ReportExtraction)
Each per-report JSON file SHALL contain: source_report (string), product_category (string), extraction_date (ISO date string), and elements (array of MaterialElement).

#### Scenario: Per-report file structure
- **WHEN** `material_library/beverage.json` is generated
- **THEN** it contains `source_report` matching the input filename, `product_category: "饮料"`, `extraction_date` as today's date, and an `elements` array

### Requirement: Index metadata format
`index.json` SHALL track: list of processed reports (filename, extraction_date, element_count, output_file), total element count, and last_updated timestamp.

#### Scenario: Index tracks all processed reports
- **WHEN** 3 reports are processed
- **THEN** `index.json` contains 3 entries in `processed_reports` with correct filenames and element counts

#### Scenario: Index is updated incrementally
- **WHEN** a 4th report is processed
- **THEN** `index.json` adds a 4th entry without modifying the existing 3

### Requirement: Cross-reference format with combinability
`cross_reference.json` SHALL organize elements by dimension, then by maturity level, with each element including: name, appears_in (list of categories), persona, and combinable_with (suggested compatible elements from other dimensions).

#### Scenario: Cross-reference groups by dimension
- **WHEN** `cross_reference.json` is read
- **THEN** it has top-level keys "颜色", "装饰物", "透明度与质地", each containing "主流", "上升", "实验性" sub-groups

#### Scenario: Combinability references are valid
- **WHEN** a color element lists `combinable_with.装饰物: ["微囊悬浮"]`
- **THEN** "微囊悬浮" exists as an actual element in the "装饰物" dimension

### Requirement: Aesthetic persona catalog
The system SHALL maintain a predefined persona catalog with at least 6 personas: 科技净澈, 天然奢养, 奢华克制, 感官甜品, 自然清体, 可视科技. Each persona SHALL have a description and typical element combinations.

#### Scenario: Persona catalog is included in output
- **WHEN** `cross_reference.json` is generated
- **THEN** it includes a `personas` section listing all personas with descriptions and example element combinations

#### Scenario: All elements reference valid personas
- **WHEN** any element's `aesthetic_persona` is checked
- **THEN** it matches one of the personas in the catalog (predefined or dynamically added)
