## Tasks

### 1. Add co-occurrence query functions to kg_retrieval.py
- [ ] 1.1 Add `get_cooccurring_materials(driver, material_id, min_shared=2, limit=5)` function with Cypher query
- [ ] 1.2 Add `get_top_cooccurrence_pairs(driver, min_shared=2, limit=20)` function
- [ ] 1.3 Update %%writefile cell in notebooks/8_multimodal_kg.ipynb for kg_retrieval.py
- [ ] 1.4 Run ruff check

### 2. Add Pydantic model for co-occurrence
- [ ] 2.1 Add CooccurringElement model to state_recommender.py (material_id, material_name, dimension, shared_image_count)
- [ ] 2.2 Add optional `frequently_paired_with: list[CooccurringElement] = []` field to ElementRecommendation
- [ ] 2.3 Update %%writefile cell in notebooks/7_material_recommender.ipynb for state_recommender.py

### 3. Add enrich_cooccurrence node to recommender graph
- [ ] 3.1 Implement `enrich_cooccurrence(state)` node: iterate recommendations, query KG, annotate
- [ ] 3.2 Update StateGraph edges: recommend → enrich_cooccurrence → attach_images → END
- [ ] 3.3 Update %%writefile cell in notebooks/7_material_recommender.ipynb

### 4. Add analytics demo cells
- [ ] 4.1 Add demo cells to notebooks/8_multimodal_kg.ipynb showing top co-occurrence pairs
- [ ] 4.2 Add demo cell showing co-occurrences for a specific material

### 5. Validate
- [ ] 5.1 Run ruff check on all modified source files
- [ ] 5.2 Test recommender with sample query: verify frequently_paired_with annotations appear
- [ ] 5.3 Commit to development branch
