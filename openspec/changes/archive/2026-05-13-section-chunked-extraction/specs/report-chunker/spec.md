## ADDED Requirements

### Requirement: Report is split into section chunks by heading

The system SHALL split a Markdown trend report into a list of section chunks by detecting H2 (`##`) and H3 (`###`) headings. Each chunk SHALL contain the heading line plus all text until the next heading of equal or higher level. If fewer than 2 heading-based chunks result, the system SHALL fall back to paragraph-based splitting (splitting on blank lines). If paragraph-based splitting also produces fewer than 2 chunks, the system SHALL return the full report as a single chunk (final degradation).

#### Scenario: Normal report with multiple H2/H3 headings

- **WHEN** a report contains 5 or more H2/H3 headings
- **THEN** `_chunk_report()` returns a list of strings, one per detected section, each starting with its heading line

#### Scenario: No headings found — paragraph-based fallback

- **WHEN** a report contains 0 or 1 H2/H3 headings
- **THEN** `_chunk_report()` splits by blank lines into paragraphs, returning each paragraph as a chunk (if paragraph count ≥ 2)

#### Scenario: Both heading and paragraph splitting fail — full report degradation

- **WHEN** a report contains 0 or 1 headings AND fewer than 2 non-empty paragraphs
- **THEN** `_chunk_report()` returns a list containing the full report text as a single element

#### Scenario: Short chunks are skipped

- **WHEN** a section chunk contains fewer than 200 characters (after stripping whitespace)
- **THEN** that chunk is excluded from the returned list

### Requirement: Each chunk includes its heading breadcrumb (H3B) for context

The system SHALL prepend the heading breadcrumb of each chunk — the ordered path of ancestor H2/H3 titles leading to the current section (e.g., `## 一、趋势总览 > ### 1. 低饱和香氛色`) — before the chunk body when sending to the LLM. This replaces prepending the first 300 characters of the full report.

#### Scenario: Chunk sent to LLM includes H3B breadcrumb

- **WHEN** a chunk is prepared for a Pass 1 or Pass 2 LLM call
- **THEN** the content passed to the prompt is `breadcrumb + "\n\n---\n\n" + chunk_text`, where `breadcrumb` is the `>` -joined ancestor heading path

#### Scenario: Top-level chunk has no ancestor headings

- **WHEN** a chunk is the first section with no parent headings
- **THEN** the chunk is sent without a breadcrumb prefix (no empty prefix prepended)

### Requirement: Pass 1 extraction iterates over chunks

The system SHALL call the `_THREE_DIM_EXTRACTION_PROMPT` LLM once per chunk (not once per full report). All elements from all chunk calls SHALL be accumulated into a single list before deduplication.

#### Scenario: Multiple chunks produce independent element lists

- **WHEN** a report is split into N chunks
- **THEN** Pass 1 makes exactly N LLM calls, and all returned elements are merged into one list

#### Scenario: Pass 1 skips elements with unexpected dimension

- **WHEN** a chunk extraction returns an element whose `dimension` is not in `{颜色, 装饰物, 透明度与质地}`
- **THEN** that element is discarded with a warning log

### Requirement: Pass 2 (style) is split by H3 headings and extracted per H3 chunk

The system SHALL split the report by H3 (`###`) headings to produce style chunks — the same granularity as Pass 1. Each H3 chunk SHALL be sent to `_STYLE_EXTRACTION_PROMPT` independently with its H3B breadcrumb prepended. All style elements from all H3 chunks SHALL be accumulated and passed through `_deduplicate_elements()` before final output.

#### Scenario: Style extraction uses H3 chunks

- **WHEN** `extract_single_report()` is called for a report with N H3 sections
- **THEN** exactly N Pass 2 LLM calls are made, one per H3 chunk

#### Scenario: Style H3 chunks include H3B breadcrumb for context

- **WHEN** a style H3 chunk is prepared for a Pass 2 LLM call
- **THEN** the content passed to the prompt is `breadcrumb + "\n\n---\n\n" + h3_chunk_text`

#### Scenario: Style extraction falls back to full report when no H3 found

- **WHEN** the report contains 0 H3 headings
- **THEN** a single Pass 2 LLM call is made with the full report text

#### Scenario: Duplicate style elements across H3 chunks are merged

- **WHEN** the same style name (e.g. "科技净澈") appears in multiple H3 chunks
- **THEN** `_deduplicate_elements()` merges them into one entry with the highest maturity and union of signals/keywords

### Requirement: Schema version is bumped to invalidate v2 caches

`EXTRACTION_SCHEMA_VERSION` SHALL be set to `3`. Any cached `ReportExtraction` with `schema_version != 3` SHALL be re-extracted on the next run.

#### Scenario: Stale v2 cache triggers re-extraction

- **WHEN** a `.cache/*.json` file has `schema_version` of 1 or 2 (or missing)
- **THEN** the pipeline skips the cache and runs fresh extraction for that report
