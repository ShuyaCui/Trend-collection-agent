# Feature: Trend Analysis Dimension Skill

## Objective

Analyze the 12 curated historical trend reports in `history_trend_report/` to extract a structured set of **trend analysis dimensions** (e.g., consumer demographics, ingredient innovation, regional market, distribution channel). These dimensions are dynamically injected into the Scope and Supervisor prompts at runtime, guiding the LLM to decompose and investigate research questions along expert-derived angles — improving research richness and coverage without adding a new agent tool.

## User / Problem Context

The research agent currently relies exclusively on Tavily web search and decomposes research topics without any domain methodology guidance. The `history_trend_report/` directory contains 12 curated, authoritative trend reports (PDFs + PPTXs) covering beauty industry trends — sourced from NIQ, Spate, Trendalytics, and similar market research firms.

These documents are valuable not only for their content but for **how** they structure trend analysis: which dimensions they investigate, which angles they apply, and which lenses they use to decompose a broad topic. Expert trend analysts consistently consider dimensions such as consumer demographic segments, ingredient or technology innovation, regional market dynamics, price tier behavior, and channel shifts.

Without access to this methodological framework, the agent's research decomposition is ad-hoc and misses dimensions that domain experts treat as standard. The goal is to teach the agent **how experts think about trends**, not what the trends are.

## Scope

### In Scope

- **Dimension extraction pipeline**: Parse all 12 documents in `history_trend_report/` (PDF via `pdfplumber`, PPTX via `python-pptx`); run a two-phase LLM extraction to produce a unified dimension list; store as `trend_knowledge/dimensions.json`

  **Two-phase LLM extraction design:**
  - *Phase 1 — Per-document extraction (12 LLM calls)*: For each document, send the full extracted text to the LLM with a structured output prompt instructing it to identify the analytical dimensions that document uses (e.g., "what angles does this report use to study trends?"). Each call returns a `PerDocumentDimensions` Pydantic schema: `dimensions: list[Dimension(name, description, examples)]`.
  - *Phase 2 — Cross-document synthesis (1 LLM call)*: Collect all 12 per-document dimension lists and send to LLM in a single synthesis call, instructing it to consolidate, deduplicate, and merge synonymous entries into a unified list of 10–20 canonical dimensions. Returns a `UnifiedDimensionList` Pydantic schema.
  - Final output written to `trend_knowledge/dimensions.json`.

- **Notebook-based extraction**: The full extraction pipeline (text parsing + Phase 1 + Phase 2 + writing `dimensions.json`) runs as interactive cells in `notebooks/6_trend_skill.ipynb`. The notebook is both the tutorial and the runnable extraction tool — no separate standalone script.
- **`%%writefile` cells**: The same notebook generates `src/deep_research_from_scratch/trend_dimensions.py` (dimension loader utility used at agent runtime).
- **Dynamic dimension lookup**: At runtime, Scope and Supervisor nodes read `trend_knowledge/dimensions.json` and inject the dimension list into their prompts.
- **Scope node prompt enrichment**: When generating the `ResearchQuestion` brief, the scope prompt includes the dimension list so the brief explicitly names which dimensions the research should cover.
- **Supervisor node prompt enrichment**: `lead_researcher_prompt` includes the dimension list so the supervisor decomposes the research question along expert dimensions when issuing `ConductResearch` calls.
- **Dependencies**: Add `pdfplumber` and `python-pptx` to `pyproject.toml`.

### Non-Goals

- Extracting the **content/findings** of the trend reports (what the trends are) — only the analytical methodology (how they are studied)
- Adding a new tool to the researcher agent (no new tool exposed; integration is via prompt injection only)
- Standalone extraction script outside of the notebook (extraction runs in Notebook 6)
- Vector database or semantic embedding search
- Automatic re-indexing when new files are added (re-run notebook cells to regenerate)
- Supporting file types beyond PDF and PPTX
- Image extraction from PDFs or PPTXs
- Internet-connected trend search APIs
- Multilingual dimension lists in v1 (English only)

## Key Decisions

| Decision | Choice | Rationale |
|---|---|---|
| **What to extract** | Analytical dimensions (not content) | Goal is methodological framework, not content retrieval |
| **Dimension form** | Named dimensions with description + examples | Gives LLM enough context to apply each dimension meaningfully without overloading the prompt |
| **LLM extraction strategy** | Two-phase: per-document (12 calls) → synthesis (1 call) | Each document is fully analyzed before synthesis; deduplication is handled by a dedicated LLM call |
| **Extraction location** | Runs inside `notebooks/6_trend_skill.ipynb` | Follows notebook-first source-of-truth principle; no separate scripts directory needed |
| **Integration point** | Scope + Supervisor prompt injection (not a researcher tool) | Dimensions guide decomposition, not search execution |
| **Injection method** | Dynamic lookup from file at node call time | Allows dimension list to be updated without redeploying code |
| **Storage format** | Single `trend_knowledge/dimensions.json` | Simple, auditable, no infrastructure required |
| **New docs handling** | Manual: re-run Notebook 6 extraction cells | v1 simplicity; auto-detection deferred |
| **Primary domain** | Beauty / consumer goods | All 12 current files are beauty-industry focused |
| **Dimension count** | Target 10–20 dimensions | Comprehensive yet small enough to fit in prompt without overwhelming |

## Architecture

```
history_trend_report/            ← input: 12 PDFs + PPTXs (curated beauty trend reports)
    ↓  [notebooks/6_trend_skill.ipynb — run extraction cells manually]

Phase 1 (12 LLM calls):
    per-document text → LLM → PerDocumentDimensions
    (repeated for each of the 12 files)

Phase 2 (1 LLM call):
    all 12 PerDocumentDimensions → LLM synthesis → UnifiedDimensionList
    ↓
trend_knowledge/
    dimensions.json              ← [{name, description, examples: [...]}]

    ↓  [%%writefile cells in same notebook]
src/deep_research_from_scratch/trend_dimensions.py   ← runtime loader utility

    ↓  [runtime: dynamic lookup in Scope and Supervisor nodes]

Scope node (research_agent_scope.py)
    loads dimensions.json via trend_dimensions.py
    injects dimension list into transform_messages_into_research_topic_prompt
    → ResearchQuestion brief explicitly names which dimensions to cover

Supervisor node (multi_agent_supervisor.py)
    loads dimensions.json via trend_dimensions.py
    injects dimension list into lead_researcher_prompt
    → ConductResearch calls structured by dimension
```

## Pydantic Schemas (Extraction)

```python
class Dimension(BaseModel):
    name: str                     # e.g., "Consumer Demographics"
    description: str              # 1-sentence description
    examples: list[str]           # 2–3 concrete examples

class PerDocumentDimensions(BaseModel):
    source_doc: str               # filename
    dimensions: list[Dimension]

class UnifiedDimensionList(BaseModel):
    dimensions: list[Dimension]   # 10–20 deduplicated, synthesized dimensions
```

## Dimension JSON Format

```json
{
  "extraction_date": "2026-04-23",
  "source_docs": ["NIQ_BlackBeautyConsumer_February2026.pdf", "..."],
  "dimensions": [
    {
      "name": "Consumer Demographics",
      "description": "Analyze trends by consumer age group, ethnicity, income level, or lifestyle segment.",
      "examples": ["Gen Z beauty preferences", "Black consumer beauty spend", "luxury vs. mass market adoption"]
    },
    {
      "name": "Ingredient & Technology Innovation",
      "description": "Track which new ingredients, formulations, or technologies are gaining traction.",
      "examples": ["active ingredient trends", "biofermentation", "AI-personalized skincare"]
    }
  ]
}
```

## Constraints

- **Notebook workflow**: All code — both the extraction pipeline and the runtime loader — goes through `%%writefile` cells in `notebooks/6_trend_skill.ipynb`
- **Graceful degradation**: If `trend_knowledge/dimensions.json` is not found at runtime, Scope and Supervisor nodes log a warning and proceed without dimension injection — preserving existing behavior
- **Prompt token budget**: Dimension list is injected as a compact bulleted list (name + 1-line description). Estimated addition: ~500–800 tokens per node call
- **`pdfplumber` + `python-pptx`**: Must be added to `pyproject.toml`; both are pure-Python
- **`dimensions.json` committed to git**: Pre-generated artifact committed so new clones work without re-running extraction
- **LLM calls during extraction**: Phase 1 is 12 LLM calls (one per document); Phase 2 is 1 call. Total: 13 calls. These run only during extraction (notebook), not at agent runtime.

## Inputs and Outputs

### Extraction (notebook) inputs
- All files in `history_trend_report/` (PDF + PPTX)

### Extraction (notebook) output
- `trend_knowledge/dimensions.json` — unified dimension list

### Runtime effect on Scope node
- **Input**: User research question (unchanged)
- **Output**: `ResearchQuestion` brief now explicitly enumerates which dimensions to cover, e.g.:
  > "Investigate 2026 haircare trends. Cover these analytical dimensions: consumer demographics, ingredient innovation, regional market dynamics, channel shifts, sustainability positioning."

### Runtime effect on Supervisor node
- **Input**: Research brief (enriched by Scope)
- **Output**: `ConductResearch` tool calls decomposed by dimension, e.g.:
  > `ConductResearch("2026 haircare trends: consumer demographics — Gen Z and millennial preferences")`
  > `ConductResearch("2026 haircare trends: ingredient innovation — key active ingredients")`

## Open Questions / Assumptions

1. **Dimension generalizability**: The 12 documents are all beauty-focused. Extracted dimensions may be beauty-specific. For non-beauty research questions, dimensions are framed as "expert analytical lenses to consider" (not mandatory), so the LLM can apply them selectively.
2. **Extraction quality**: `pdfplumber` may struggle with scanned or image-heavy PDFs. Assume all 12 files are text-based; log warnings for failed pages without crashing.
3. **Phase 1 context length**: Some PDFs may be very long. If a document exceeds the LLM's context window, sample the first N pages / slides as a representative excerpt for Phase 1.
4. **Prompt injection placement**: Exact placement within `transform_messages_into_research_topic_prompt` and `lead_researcher_prompt` determined during implementation. Dimensions are framed as "analytical lenses to consider," not a mandatory checklist.
5. **Dimension deduplication**: Handled by Phase 2 synthesis LLM call; the prompt explicitly instructs consolidation of synonymous dimensions.
