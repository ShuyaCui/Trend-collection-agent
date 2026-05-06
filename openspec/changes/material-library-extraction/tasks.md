## 1. Phase A — Schema & Skeleton

- [ ] 1.1 Define Pydantic models (`MaterialElement`, `ReportExtraction`, `CrossReference`, `PersonaCatalog`) in `scripts/material_schema.py`
- [ ] 1.2 Create `material_library/` directory and empty `index.json` with initial structure
- [ ] 1.3 Define the 6 predefined aesthetic personas with descriptions and example combinations in a `PERSONA_CATALOG` constant

## 2. Phase B — Extraction Core

- [ ] 2.1 Write the LLM extraction prompt that instructs the model to parse a Markdown report and output `ReportExtraction` JSON (covering 颜色, 装饰物, 透明度与质地)
- [ ] 2.2 Implement `extract_single_report(report_path) -> ReportExtraction` function using `init_chat_model` + `with_structured_output(ReportExtraction)`
- [ ] 2.3 Implement `extract_all_reports(reports_dir, force=False)` with incremental logic: skip already-processed reports (check `index.json`), process new ones, save per-report JSON to `material_library/`
- [ ] 2.4 Implement `build_cross_reference(material_library_dir) -> CrossReference` that reads all per-report JSONs, groups elements by dimension + maturity, deduplicates cross-category elements, and generates combinability hints based on persona matching
- [ ] 2.5 Implement `update_index(material_library_dir)` to write/update `index.json` with processing metadata

## 3. Phase B — CLI Entry Point

- [ ] 3.1 Create `scripts/extract_material_library.py` with `argparse` CLI: `--reports-dir`, `--output-dir`, `--force` flags
- [ ] 3.2 Wire CLI to call `extract_all_reports()` then `build_cross_reference()` then `update_index()`
- [ ] 3.3 Run extraction on all 3 existing reports; verify output structure and element completeness

## 4. Phase C — Validation & Quality

- [ ] 4.1 Spot-check: compare extracted element count per dimension against report chapter count (颜色趋势 1-6, 装饰趋势 7-12, etc.) to ensure no elements were missed
- [ ] 4.2 Validate all elements pass Pydantic schema validation (no missing fields, correct enum values)
- [ ] 4.3 Validate cross_reference.json: all `combinable_with` references point to real elements; all personas are present
- [ ] 4.4 Ruff lint check on `scripts/material_schema.py` and `scripts/extract_material_library.py`

## 5. Phase C — Documentation & Commit

- [ ] 5.1 Add a README section in `material_library/README.md` explaining the schema, directory structure, and how to run the extraction
- [ ] 5.2 Commit all changes to `development` branch with summary of files changed
