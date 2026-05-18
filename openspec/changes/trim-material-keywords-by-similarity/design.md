## Context

`_merge_group()` in `extract_material_library.py` performs union-deduplication of `visual_keywords` and `signals` across all source elements in a merge group. Because the same element may appear in many reports, these lists balloon to 1000+ items after merging. The existing embedding infrastructure (`text-embedding-3-small` via `_build_embedding_model()`) is already present in the script for semantic element deduplication.

The trimming must happen inside `_merge_group()` — this is the single place where both exact-name and semantic duplicate merges converge, so a post-merge trim here covers all paths.

## Goals / Non-Goals

**Goals:**
- Bound `visual_keywords` and `signals` to ≤ 20 items per element after any merge.
- Select retained items by embedding cosine similarity to the element's topic string (`name + name_en + typical_use`), keeping the most relevant.
- Reuse the existing `_build_embedding_model()` helper; no new dependencies.
- Keep the trim lazy: only invoke embeddings when a list actually exceeds the limit.

**Non-Goals:**
- Does not change the merge logic for any other field.
- Does not enforce a hard cap on the schema (`list[str]` stays unconstrained); this is a runtime policy applied during extraction only.
- Does not retroactively trim existing `material_library/*.json` files without re-running the extraction pipeline.
- Does not apply trimming during the `_semantic_deduplicate_elements` pass (it already calls `_merge_group()`, which will trim internally).

## Decisions

### D1: Trim inside `_merge_group()`, not as a separate post-processing step

**Decision**: add trimming at the end of `_merge_group()` before returning the merged element.

**Rationale**: `_merge_group()` is the single convergence point for all merges (exact-name via `_deduplicate_elements` and semantic via `_semantic_deduplicate_elements`). A post-merge step would require threading results through both callers. Putting it here keeps the change isolated and guarantees every merge path is covered.

**Alternative considered**: a separate `_trim_all_elements()` pass after all deduplication — rejected because it duplicates embedding calls and couples the function signature to the trimming policy.

### D2: Topic string = `name + " " + name_en + " " + typical_use`

**Decision**: embed the concatenation of `name`, `name_en`, and `typical_use` as the reference vector for the topic.

**Rationale**: `name` alone is too short for a stable embedding; `typical_use` adds product context. `aesthetic_style` is excluded because it is a category label (one of 6 fixed values) and would bias toward style-level semantics rather than element-specific relevance.

**Alternative**: embed only `name` — rejected because 1-3 character Chinese names embed poorly in isolation.

### D3: Similarity metric = cosine similarity against a single topic vector

**Decision**: embed each keyword/signal string, compute cosine similarity to the topic vector, sort descending, keep top 20.

**Rationale**: Cosine similarity is already used in the semantic deduplication pass and requires only a batch embed call, no additional libraries.

**Alternative**: BM25 or TF-IDF substring overlap — rejected because the keyword items are short phrases in Chinese where token frequency is not meaningful.

### D4: Limit = 20, threshold = unconditional (no similarity floor)

**Decision**: always keep the top 20 by score; no minimum similarity threshold to pass.

**Rationale**: the goal is to bound list size while preserving the best items. Applying a minimum floor risks trimming below 20 even when good candidates exist. The 20-item cap matches the original schema annotation ("3-8 items" per single extraction; ~20 is generous for a merged entry spanning multiple reports).

## Risks / Trade-offs

- **[Risk] Embedding API latency**: each `_merge_group()` call with >20 items now makes 1+N embed requests (topic + keywords/signals batch). For large merges this adds seconds per element.  
  → **Mitigation**: batch `visual_keywords` and `signals` in a single `embed_documents` call; share the topic vector across both lists; add an INFO log when trimming is invoked.

- **[Risk] Embedding model unavailable at merge time**: `_build_embedding_model()` uses Azure OpenAI — if credentials are missing, `_merge_group()` will raise.  
  → **Mitigation**: guard with a try/except; fall back to keeping the first 20 items (insertion order) and log a WARNING.

- **[Risk] Short lists never trimmed**: if a merge produces ≤20 items, no embed call is made — zero overhead for the common case.

## Migration Plan

1. Update `_merge_group()` in `extract_material_library.py` with a new `_trim_by_similarity()` helper.
2. Re-run the extraction pipeline (`uv run python src/material-library-extraction/extract_material_library.py --force`) to regenerate all `material_library/*.json` files.
3. Verify that no entry has `visual_keywords` or `signals` exceeding 20 items.

**Rollback**: revert the `_merge_group()` change and re-run extraction with `--force`.

## Open Questions

- Should the limit (20) be configurable via a CLI flag or env var? **Assumption**: hardcoded for now; can be promoted to a parameter if needed.
- Should trimming also apply during the style dimension (风格) extraction, which uses a separate `_STYLE_EXTRACTION_PROMPT`? **Assumption**: yes — `_merge_group()` is shared, so style elements are covered automatically.
