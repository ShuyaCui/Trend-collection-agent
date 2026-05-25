# Spec: Material Recommendation

## MODIFIED Requirements

### Requirement: Structured recommendation output
`ElementRecommendation` output SHALL gain an optional `frequently_paired_with: list[CooccurringElement]` field for KG-based co-occurrence annotations.

#### Scenario: Recommendation includes co-occurrence annotations
- **WHEN** an element has cross-dimension co-occurrences above the configured threshold
- **THEN** its `ElementRecommendation` output SHALL include `frequently_paired_with` entries describing the paired materials

#### Scenario: Recommendation without meaningful co-occurrences
- **WHEN** no paired materials meet the configured threshold
- **THEN** the recommendation MAY omit `frequently_paired_with` or provide it as an empty list

### Requirement: Recommender graph topology
The recommendation graph topology SHALL change from `recommend -> attach_images -> END` to `recommend -> enrich_cooccurrence -> attach_images -> END`.

#### Scenario: Co-occurrence enrichment runs before image attachment
- **WHEN** the recommender graph executes for a user query
- **THEN** it SHALL run `recommend`, then `enrich_cooccurrence`, then `attach_images`, and finally return the enriched recommendation result

### Requirement: Co-occurrence enrichment node behavior
The `enrich_cooccurrence` node SHALL iterate over each recommended element, query the KG for top co-occurring materials from other dimensions, and annotate the existing recommendation in place.

#### Scenario: Annotation-only enrichment
- **WHEN** `enrich_cooccurrence` processes a recommendation result
- **THEN** it SHALL annotate each existing recommendation with co-occurrence data and SHALL NOT add new recommended elements to any dimension list
