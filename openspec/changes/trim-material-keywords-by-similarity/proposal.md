## Why

After merging duplicate elements across reports, `visual_keywords` and `signals` lists in the Material Library grow through union-accumulation and can reach 1000+ items per entry (e.g., 淡粉色 has 1214 visual_keywords, 1074 signals). These bloated lists degrade prompt quality, increase token cost, and dilute the relevance signal when the library is injected into LLM prompts.

## What Changes

- **New trimming step** added to `_merge_group()` in `extract_material_library.py`: after merging, if `visual_keywords` or `signals` exceeds 20 items, rank all candidates by cosine similarity to the element's topic embedding (`name + name_en + typical_use`), and keep only the top 20.
- The same Azure OpenAI text-embedding model already used for semantic deduplication (`text-embedding-3-small`) will be reused for the trimming similarity computation.
- The trimming runs **in-process** inside `_merge_group()`, so it applies to both exact-name and semantic deduplication merges.
- No changes to the JSON schema; field counts are simply bounded post-merge.

**Assumed fact**: the embedding model used in `_semantic_deduplicate_elements` is accessible at trimming time (both run inside the same process).

## Capabilities

### New Capabilities

- `keyword-trim-by-similarity`: After merging, automatically trim `visual_keywords` and `signals` to at most 20 items each by embedding-similarity ranking against the element topic.

### Modified Capabilities

*(None — no existing spec-level requirement is changing.)*

## Impact

- **`src/material-library-extraction/extract_material_library.py`**: `_merge_group()` gains an optional embedding-based trimming call; a new helper `_trim_by_similarity()` is introduced.
- **`src/material-library-extraction/material_schema.py`**: No schema changes; field constraints remain `list[str]` without a max-length enforcement (trimming is a runtime policy).
- **`material_library/*.json`**: Regenerated files will have ≤20 items in `visual_keywords` and `signals` per entry.
- **Dependencies**: No new packages; reuses `langchain` + Azure OpenAI embeddings already present.
- **Non-goals**: Does not change the deduplication threshold, the merge strategy for other fields, or add any UI/API exposure. Does not enforce trimming for entries created before re-running the extraction pipeline.
