## 1. Implement Trimming Helper

- [x] 1.1 Add `_trim_by_similarity(items, topic, model, limit=20)` helper function in `extract_material_library.py` that: embeds `topic` and all `items` in a single batch call, computes cosine similarity of each item to the topic, returns the top-`limit` items sorted by similarity descending
- [x] 1.2 Add fallback logic in `_trim_by_similarity`: if the embedding call raises any exception, log a WARNING and return `items[:limit]` (first N by insertion order)

## 2. Integrate Trimming into `_merge_group()`

- [x] 2.1 At the end of `_merge_group()` (after building `merged_kw` and `merged_sig`), call `_trim_by_similarity` on `merged_kw` if `len(merged_kw) > 20`, using the topic string `f"{primary.name} {primary.name_en} {primary.typical_use}"`
- [x] 2.2 Apply the same trim call to `merged_sig` if `len(merged_sig) > 20`, reusing the same topic string and the same embedding model instance (pass model as a parameter or build once)
- [x] 2.3 Add an INFO log line whenever trimming is invoked, reporting the field name, original count, and retained count

## 3. Validation

- [x] 3.1 Re-run the extraction pipeline with `--force` flag: `uv run python src/material-library-extraction/extract_material_library.py --force`
- [x] 3.2 Verify no entry in any `material_library/*.json` file has `visual_keywords` or `signals` exceeding 20 items (run a quick Python assertion script)
- [x] 3.3 Spot-check a previously bloated entry (e.g., `淡粉色` in `color.json`) to confirm the retained keywords are semantically relevant to the element name

## 4. Commit

- [ ] 4.1 Commit changes to the `development` branch with message: `Trim visual_keywords and signals to top-20 by embedding similarity after merge`
