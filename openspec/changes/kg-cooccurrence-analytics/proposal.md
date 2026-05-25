## Why

The multimodal KG contains rich cross-dimensional relationships: each product image is connected to color, texture, and decoration materials. This encodes which elements actually appear together in real products — a signal that the current LLM-only recommender cannot leverage.

**Opportunity 1 (Analytics)**: Expose co-occurrence patterns as a standalone query — e.g., "what textures most frequently appear with 淡粉色?" — for trend exploration and report insights.

**Opportunity 2 (Recommendation enrichment)**: After the LLM recommends elements, annotate each recommendation with "frequently paired with Y, Z" based on KG co-occurrence data. This grounds the LLM's creative suggestions in observed product data.

## What Changes

- Add a standalone co-occurrence query function to `kg_retrieval.py`:
  - Input: optional `material_id` or `dimension` filter
  - Output: ranked list of cross-dimension material pairs with shared image count
  - Implemented as a Cypher query: `MATCH (m1)<--(i)-->(m2) WHERE m1.dimension_key <> m2.dimension_key`
- Add a `enrich_cooccurrence` node (or post-processing step) in the material recommender LangGraph:
  - For each recommended element, query the KG for its top co-occurring elements from other dimensions
  - Annotate the `ElementRecommendation` with a `frequently_paired_with` field
  - No new elements are added to the recommendation list — annotation only
- Add demo cells to Notebook 8 (KG notebook) for standalone analytics
- Update Notebook 7 `%%writefile` cell for the enrichment integration

## Non-goals

- Not adding new elements to recommendations based on co-occurrence (annotation only)
- Not implementing community detection or clustering algorithms
- Not changing the KG schema or edge creation logic
- Not building a UI or visualization layer (analytics is query-level)

## Assumptions

- *(Assumption)* The current KG density (~4.8 edges per image, 205 images) provides enough signal for meaningful co-occurrence patterns. Will validate during implementation by checking minimum shared image thresholds.
- *(Assumption)* Cross-dimension co-occurrence is more useful than within-dimension (confirmed by user).

## Capabilities

### New Capabilities

- `kg-cooccurrence`: Cross-dimension co-occurrence analytics. Covers the Cypher query logic, the standalone query function, and the enrichment integration into the recommender graph.

### Modified Capabilities

- `material-recommendation`: The recommendation output gains a `frequently_paired_with` annotation field on each `ElementRecommendation`. The recommendation logic itself is unchanged — this is post-processing enrichment only.

## Impact

- `src/deep_research_from_scratch/kg_retrieval.py`: New query function(s) for co-occurrence
- `src/deep_research_from_scratch/material_recommender.py`: New `enrich_cooccurrence` node or integration into existing flow
- `src/deep_research_from_scratch/state_recommender.py`: `ElementRecommendation` Pydantic model gains `frequently_paired_with` field
- `notebooks/7_material_recommender.ipynb`: Source of truth for recommender changes
- `notebooks/8_multimodal_kg.ipynb`: Demo cells for standalone analytics
- No new dependencies required
