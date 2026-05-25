# Spec: KG Co-occurrence

## ADDED Requirements

### Requirement: Query co-occurring materials for a specific material
The system SHALL provide `get_cooccurring_materials(driver, material_id, min_shared=2, limit=5)` that accepts a Neo4j driver and returns a ranked list of co-occurring materials from other dimensions. Each result SHALL include `material_name`, `material_id`, `dimension`, and `shared_count`.

#### Scenario: Specific material returns cross-dimension pairings
- **WHEN** querying co-occurrences for a specific color element
- **THEN** the system SHALL return textures and decorations that frequently appear in the same product images

#### Scenario: No meaningful co-occurrences
- **WHEN** no material shares at least `min_shared` images with the requested material
- **THEN** the system SHALL return an empty list

### Requirement: Query top co-occurrence pairs globally
The system SHALL provide `get_top_cooccurrence_pairs(driver, dimension_filter=None, min_shared=2, limit=20)` that accepts a Neo4j driver and returns globally ranked cross-dimension material pairs with shared image counts.

#### Scenario: Global pair analytics
- **WHEN** calling `get_top_cooccurrence_pairs`
- **THEN** the system SHALL return globally ranked cross-dimension pairs ordered by shared image count

### Requirement: Use Neo4j driver injection
Both `get_cooccurring_materials` and `get_top_cooccurrence_pairs` SHALL take a Neo4j driver parameter rather than relying on hidden global state.

#### Scenario: Caller provides driver
- **WHEN** either co-occurrence query function is invoked
- **THEN** the caller SHALL supply the Neo4j driver used to execute the Cypher query

### Requirement: Restrict results to cross-dimension relationships
Both co-occurrence query functions SHALL only return relationships where the paired materials belong to different dimensions (`m1.dimension_key != m2.dimension_key`).

#### Scenario: Same-dimension relationships excluded
- **WHEN** two materials share images but belong to the same dimension
- **THEN** those materials SHALL NOT appear in co-occurrence results

### Requirement: Sort by shared image count descending
Both co-occurrence query functions SHALL sort results by shared image count in descending order before applying the output limit.

#### Scenario: Highest-frequency pairs first
- **WHEN** multiple co-occurrence results are available
- **THEN** the results SHALL be ordered from highest `shared_count` to lowest `shared_count`

### Requirement: Typed co-occurrence annotation model
The system SHALL define a `CooccurringElement` Pydantic model with fields `material_id`, `material_name`, `dimension`, and `shared_image_count`.

#### Scenario: Structured co-occurrence data
- **WHEN** co-occurrence data is attached to recommendation output
- **THEN** each annotation item SHALL conform to the `CooccurringElement` schema
