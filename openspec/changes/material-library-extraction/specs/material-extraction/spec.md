## ADDED Requirements

### Requirement: Extract elements from single report
The system SHALL accept a single Markdown trend report file and extract all design elements into structured JSON, covering three dimensions: 颜色, 装饰物, 透明度与质地.

#### Scenario: Extract from beverage report
- **WHEN** the extraction script is run with `reports/FY2526中国饮料内容物设计趋势报告.md` as input
- **THEN** the system produces a JSON file containing all color elements (趋势1-6), decoration elements (趋势7-12), and texture/transparency elements (趋势13-18) from the report

#### Scenario: Extract from report with different structure
- **WHEN** the extraction script is run with a report that uses numbered subsections (§3.1, §4.1) instead of numbered trends (趋势1, 趋势2)
- **THEN** the system still extracts all elements correctly, adapting to the content structure

### Requirement: Each extracted element SHALL conform to MaterialElement schema
Every extracted element MUST include: id, dimension, name, name_en, visual_keywords, aesthetic_persona, signals, maturity, year_range, typical_use, and source_section.

#### Scenario: Element has all required fields
- **WHEN** an element is extracted from a report section describing "浅琥珀/蜂蜜色"
- **THEN** the element JSON includes all schema fields with non-empty values, and `dimension` is one of ["颜色", "装饰物", "透明度与质地"]

#### Scenario: Maturity classification is accurate
- **WHEN** a report section is labeled "已经广泛出现" or "主流"
- **THEN** the extracted element has `maturity: "主流"`
- **WHEN** a report section is labeled "正在上升" or "上升"
- **THEN** the extracted element has `maturity: "上升"`
- **WHEN** a report section is labeled "实验性" or "概念化"
- **THEN** the extracted element has `maturity: "实验性"`

### Requirement: Aesthetic persona assignment from predefined set
The system SHALL assign each element an `aesthetic_persona` from a predefined set: 科技净澈, 天然奢养, 奢华克制, 感官甜品, 自然清体, 可视科技. Custom personas MAY be added if no predefined one fits.

#### Scenario: Persona matches element characteristics
- **WHEN** an element describes "无色透明、高折光、微囊悬浮"
- **THEN** the assigned persona is "科技净澈" or "可视科技"

#### Scenario: Element does not fit predefined personas
- **WHEN** an element has characteristics that don't map to any predefined persona
- **THEN** the system assigns a new descriptive persona and includes it in the output

### Requirement: Batch processing of all reports
The system SHALL process all `.md` files in the `reports/` directory in a single invocation.

#### Scenario: Process three reports at once
- **WHEN** the script is run without arguments (or with `--all` flag)
- **THEN** all 3 reports in `reports/` are processed and individual JSON files are generated for each

### Requirement: Incremental update support
The system SHALL skip reports that have already been processed (based on filename match in index.json) unless `--force` flag is provided.

#### Scenario: New report added
- **WHEN** a 4th report is added to `reports/` and the script is run
- **THEN** only the new report is processed; existing 3 JSON outputs are unchanged

#### Scenario: Force re-extraction
- **WHEN** the script is run with `--force` flag
- **THEN** all reports are re-processed regardless of previous extraction state

### Requirement: Cross-reference index generation
After extracting all reports, the system SHALL generate a `cross_reference.json` that groups elements by dimension and maturity across all categories.

#### Scenario: Cross-category color comparison
- **WHEN** cross_reference.json is generated from 3 reports
- **THEN** the "颜色" section lists elements from all categories with `appears_in` arrays showing which reports contain each element

#### Scenario: Combinability hints in cross-reference
- **WHEN** cross_reference.json is generated
- **THEN** each element in the cross-reference includes a `combinable_with` field listing compatible elements from other dimensions, grouped by persona
