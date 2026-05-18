## ADDED Requirements

### Requirement: Trim visual_keywords and signals after merge
After any merge of MaterialElement groups, if the resulting `visual_keywords` list exceeds 20 items, the system SHALL trim it to exactly 20 items by retaining only those with the highest cosine similarity to the element's topic embedding. The same rule applies independently to the `signals` list.

#### Scenario: visual_keywords exceeds limit after merge
- **WHEN** `_merge_group()` produces a merged element whose `visual_keywords` list contains more than 20 items
- **THEN** the returned element's `visual_keywords` SHALL contain exactly 20 items, selected as the top-20 by cosine similarity to the topic vector derived from `name + name_en + typical_use`

#### Scenario: signals exceeds limit after merge
- **WHEN** `_merge_group()` produces a merged element whose `signals` list contains more than 20 items
- **THEN** the returned element's `signals` SHALL contain exactly 20 items, selected as the top-20 by cosine similarity to the same topic vector

#### Scenario: lists within limit — no trimming
- **WHEN** both `visual_keywords` and `signals` have 20 or fewer items after merge
- **THEN** no embedding call SHALL be made and both lists SHALL be returned unchanged

#### Scenario: embedding model unavailable
- **WHEN** the Azure OpenAI embedding model cannot be reached during trimming
- **THEN** the system SHALL log a WARNING, retain the first 20 items by insertion order, and continue without raising an exception

#### Scenario: single-element group — no trimming
- **WHEN** `_merge_group()` receives a group of exactly one element
- **THEN** no trimming SHALL be applied regardless of list length (single-source elements are not expected to be oversized; trimming is a merge concern)
