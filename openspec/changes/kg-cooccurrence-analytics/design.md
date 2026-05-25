## Context

The proposal adds cross-dimension co-occurrence analytics on top of the multimodal KG and uses the same signal to enrich material recommendations. The KG already links `Image` nodes to `Material` nodes across color, texture, and decoration dimensions, so image-level co-occurrence can be queried without changing the schema.

The implementation must fit the existing notebook-first workflow: `%%writefile` cells in `notebooks/8_multimodal_kg.ipynb` generate `kg_retrieval.py`, and `%%writefile` cells in `notebooks/7_material_recommender.ipynb` generate recommender code and state models. The recommender already follows LangGraph `StateGraph` patterns with typed state and post-processing nodes.

## Goals / Non-Goals

**Goals**
- Add a standalone analytics query surface in `kg_retrieval.py` for cross-dimension material co-occurrence.
- Add recommender enrichment that annotates each recommended element with frequent cross-dimension pairings from the KG.
- Keep the change aligned with existing `StateGraph`, `TypedDict`, and notebook `%%writefile` architecture.
- Return ranked, thresholded co-occurrence results that are meaningful for trend analysis and recommendation context.

**Non-Goals**
- Do not change the KG schema, ingestion flow, or edge creation logic.
- Do not add new elements to the recommendation output based on co-occurrence; enrichment is annotation-only.
- Do not introduce clustering, community detection, or visualization features.
- Do not move source-of-truth logic out of the notebooks.

## Decisions

### 1. Two-component implementation
The change is split into two components:
- **A. Standalone analytics query function in `kg_retrieval.py`** for reusable KG analysis.
- **B. Enrichment integration into the recommender** so existing recommendations gain co-occurrence context.

This separation keeps analytics reusable outside the recommender while avoiding tight coupling between ad hoc KG exploration and the recommendation graph.

### 2. Cypher query shape
Global pair analytics use this query pattern:

```cypher
MATCH (m1:Material)<--(i:Image)-->(m2:Material)
WHERE m1.dimension_key <> m2.dimension_key AND id(m1) < id(m2)
RETURN m1.name, m2.name, count(i)
ORDER BY count(i) DESC
```

The `m1.dimension_key <> m2.dimension_key` predicate enforces cross-dimension only results, and `id(m1) < id(m2)` removes mirrored duplicates from pair rankings.

Single-material enrichment uses this query pattern:

```cypher
MATCH (m:Material {id: $id})<--(i)-->(m2:Material)
WHERE m.dimension_key <> m2.dimension_key
RETURN m2.name, count(i)
ORDER BY count(i) DESC
```

This keeps the recommender lookup focused on one recommended material and returns only materials from other dimensions.

### 3. Thresholded co-occurrence semantics
A co-occurrence is considered meaningful only when two materials share at least **2** images. This is an implementation assumption chosen to suppress one-off pairings in a small graph. The threshold should be exposed as a configurable parameter (`min_shared`) in query functions instead of hardcoding behavior in call sites.

### 4. Annotation-only enrichment
`enrich_cooccurrence` only adds a `frequently_paired_with` annotation to each existing `ElementRecommendation`. It must not inject new recommendations, reorder the recommendation lists, or override the LLM's selected elements. This preserves the current recommendation contract while grounding the output in observed KG patterns.

### 5. Pydantic and state model extension
`state_recommender.py` will define a `CooccurringElement` Pydantic model and extend `ElementRecommendation` with an optional `frequently_paired_with: list[CooccurringElement]` field. This keeps co-occurrence data typed, serializable, and compatible with existing structured LangGraph outputs.

### 6. LangGraph integration point
The recommender graph topology changes from `recommend -> attach_images -> END` to `recommend -> enrich_cooccurrence -> attach_images -> END`. Placing enrichment after `recommend` ensures it annotates concrete recommendation IDs, while keeping `attach_images` unchanged as the final post-processing step.

### 7. Notebook-first implementation
All source changes must be made in notebooks, not generated `src/` files:
- Recommender changes belong in `notebooks/7_material_recommender.ipynb`.
- Analytics query functions and demo cells belong in `notebooks/8_multimodal_kg.ipynb`.

This follows the repository's `%%writefile` generation pattern and avoids drift between notebooks and generated Python modules.

## Risks / Trade-offs

- **Sparse signal risk**: With a modest number of images, some materials may have no pairings above the threshold, producing empty annotations. This is acceptable and preferable to surfacing weak one-off connections.
- **Extra KG queries in recommender**: Enrichment adds one KG lookup per recommended element, increasing latency. The trade-off is acceptable because the node is post-processing and bounded by small recommendation lists.
- **Threshold sensitivity**: A default of 2 reduces noise, but it may hide emerging low-frequency pairs. Making `min_shared` configurable limits this risk.
- **Schema coupling to current labels/properties**: The design depends on `Material`, `Image`, `id`, `name`, and `dimension_key` remaining stable in Neo4j. This is acceptable because the change intentionally aligns with the existing KG architecture.
- **Output growth**: Adding `frequently_paired_with` increases recommendation payload size. Keeping the field optional and bounded by a result limit contains that cost.
