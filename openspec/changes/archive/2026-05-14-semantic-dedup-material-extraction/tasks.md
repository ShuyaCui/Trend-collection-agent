## 1. Refactor shared merge helper

- [x] 1.1 Extract `_merge_group(group: list[MaterialElement]) -> MaterialElement` from `_deduplicate_elements` — encapsulates maturity ranking, list-field union, and source_report joining logic
- [x] 1.2 Update `_deduplicate_elements` to call `_merge_group` instead of inline merge logic; verify exact-name dedup behavior is unchanged

## 2. Implement embedding client

- [x] 2.1 Add `_build_embedding_model()` function that initializes `AzureOpenAIEmbeddings` with `deployment="TEXT-EMBEDDING-3-SMALL"`, `api_version="2024-09-01-preview"`, `api_key=GenAIToken().token()`, and standard Azure headers
- [x] 2.2 Guard instantiation so the embedding model is only created when semantic dedup is enabled (lazy init or pass-through flag)

## 3. Implement Union-Find clustering

- [x] 3.1 Implement `_union_find_clusters(n: int, pairs: list[tuple[int, int]]) -> list[list[int]]` — takes element count and list of (i, j) index pairs that exceed threshold; returns grouped index lists
- [x] 3.2 Write a quick unit test (or inline assertion) to verify transitivity: A-B + B-C above threshold → one group of three

## 4. Implement `_semantic_deduplicate_elements`

- [x] 4.1 Implement `_semantic_deduplicate_elements(elements: list[MaterialElement], threshold: float = 0.7) -> list[MaterialElement]`:
  - Group elements by `dimension`
  - For each dimension: batch-embed all `name` fields, compute pairwise cosine similarity, collect pairs above `threshold`, run Union-Find, merge each cluster with `_merge_group`
  - Log merged clusters at INFO level (names, dimension, resulting maturity)
- [x] 4.2 Compute cosine similarity using `numpy` (`np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))`) on the returned embedding vectors

## 5. Wire into `build_dimension_files`

- [x] 5.1 Add `--no-semantic-dedup` argument to the `argparse` parser in `main()`
- [x] 5.2 Pass `semantic_dedup: bool` flag through to `build_dimension_files`; call `_semantic_deduplicate_elements` after `_deduplicate_elements` when flag is `True`

## 6. Validation

- [x] 6.1 Run the script on existing reports (`uv run python src/material-library-extraction/extract_material_library.py`) and confirm it completes without errors
- [x] 6.2 Confirm `--no-semantic-dedup` produces the same output as the current (pre-change) behavior
- [x] 6.3 Manually inspect the INFO logs to verify at least one semantic merge is reported (or confirm zero merges if all names are already distinct)
- [x] 6.4 Run `ruff check src/material-library-extraction/` and fix any lint issues
