## ADDED Requirements

### Requirement: Semantic deduplication after exact-name deduplication
The system SHALL perform a second deduplication pass using text embeddings after the exact-name deduplication step. Within each dimension, any two elements whose `name` fields have a cosine similarity score greater than 0.7 SHALL be merged into a single element.

#### Scenario: Two elements with semantically equivalent names are merged
- **WHEN** two `MaterialElement` objects share the same `dimension` and their `name` fields yield a cosine similarity > 0.7 via text-embedding-3-small
- **THEN** the two elements SHALL be merged into one using the same merge rules as exact-name deduplication (highest maturity wins, list fields unioned, source_report concatenated)

#### Scenario: Two elements with dissimilar names are not merged
- **WHEN** two `MaterialElement` objects share the same `dimension` but their `name` cosine similarity ≤ 0.7
- **THEN** both elements SHALL remain as separate entries in the output

#### Scenario: Elements in different dimensions are never merged by semantic dedup
- **WHEN** two `MaterialElement` objects have different `dimension` values, regardless of name similarity
- **THEN** the system SHALL NOT merge them during the semantic deduplication step

### Requirement: Union-Find clustering for semantic groups
The system SHALL use Union-Find (disjoint-set) clustering to determine merge groups, so that all elements mutually above the similarity threshold are grouped together regardless of comparison order.

#### Scenario: Transitive similarity group is merged as one
- **WHEN** element A and B have similarity > 0.7, and B and C have similarity > 0.7
- **THEN** A, B, and C SHALL all be merged into a single element

### Requirement: Embedding model configuration
The system SHALL use `AzureOpenAIEmbeddings` with deployment `TEXT-EMBEDDING-3-SMALL`, `api_version="2024-09-01-preview"`, authenticated via `GenAIToken().token()` and the standard Azure headers (`project-name`, `userid`).

#### Scenario: Embedding client uses correct deployment and auth
- **WHEN** semantic deduplication is invoked
- **THEN** the embedding client SHALL call Azure OpenAI with deployment `TEXT-EMBEDDING-3-SMALL` and a valid bearer token from `GenAIToken`

### Requirement: Opt-out via CLI flag
The system SHALL accept a `--no-semantic-dedup` CLI argument. When supplied, the semantic deduplication step SHALL be skipped entirely and the output SHALL be identical to the current (exact-name-only) behavior.

#### Scenario: Running with --no-semantic-dedup skips embedding calls
- **WHEN** the script is invoked with `--no-semantic-dedup`
- **THEN** no calls to the Azure OpenAI Embeddings API SHALL be made, and the output SHALL match the exact-name-dedup-only result

### Requirement: Merge logging for semantic duplicates
The system SHALL emit an `INFO`-level log message for each semantic merge, consistent in format with existing exact-name merge logs, identifying the merged names, dimension, and chosen maturity.

#### Scenario: Semantic merge is logged
- **WHEN** two or more elements are merged by semantic deduplication
- **THEN** a log line SHALL be emitted stating how many elements were merged, their names, the dimension, and the resulting maturity
