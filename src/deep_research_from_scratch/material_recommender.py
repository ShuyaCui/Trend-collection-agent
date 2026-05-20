
"""Material Recommendation Agent.

This module implements a LangGraph-based recommendation agent that suggests
design elements (colors, textures, decorations) from the material library
based on user product design queries. It supports multi-turn conversations
and provides source traceability for all recommendations via post-hoc lookup.
"""

import json
import os
import urllib.parse  # noqa: F401 — pre-load before urllib3 can shadow it
from pathlib import Path

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from deep_research_from_scratch.Helper import GenAIToken
from deep_research_from_scratch.prompts import recommender_system_prompt
from deep_research_from_scratch.state_recommender import (
    ElementRecommendation,
    RecommendationResult,
    RecommenderState,
)

load_dotenv()

# ===== CONFIGURATION =====

_DEFAULT_RECOMMENDER_MODEL = "azure_openai:gpt-4.1"

# Path to material_library/ relative to this file:
# src/deep_research_from_scratch/material_recommender.py -> ../../.. -> project root
_MATERIAL_LIBRARY_DIR = Path(__file__).parent.parent.parent / "material_library"


# ===== UTILITY FUNCTIONS =====

def _normalize_model_id(model_id: str) -> str:
    """Normalize Azure model identifiers to use the expected deployment casing."""
    provider, separator, deployment = model_id.partition(":")
    if not separator:
        return model_id
    return f"{provider}{separator}{deployment.upper()}"


def _build_model(model_id: str, **kwargs):
    """Build an Azure OpenAI model instance from a model identifier string.

    Extracts the deployment name from the model identifier using the
    convention that model name equals deployment name.
    """
    normalized_model_id = _normalize_model_id(model_id)
    deployment = normalized_model_id.split(":")[-1]
    return init_chat_model(
        model=normalized_model_id,
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        azure_deployment=deployment,
        api_key=GenAIToken().token(),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        default_headers={
            "project-name": os.getenv("HEADERS_PROJECT_NAME"),
            "userid": os.getenv("HEADERS_USERID"),
        },
        **kwargs,
    )


def load_material_library(library_dir: Path | None = None) -> str:
    """Load and format all material library elements for LLM context injection.

    Loads color, texture, and decoration elements from the material library JSON
    files and formats them as compact single-line text entries. Source traceability
    fields (source_report, source_heading) are intentionally excluded from the
    prompt context — they are added via post-hoc lookup after recommendations are
    produced.

    Args:
        library_dir: Path to the material_library directory. Defaults to the
            standard location relative to the project root.

    Returns:
        A formatted string containing all material library elements ready for
        prompt injection.

    Raises:
        FileNotFoundError: If any of the required JSON files cannot be found.
        ValueError: If any JSON file is malformed.
    """
    if library_dir is None:
        library_dir = _MATERIAL_LIBRARY_DIR

    files = {
        "颜色": library_dir / "color.json",
        "透明度与质地": library_dir / "texture.json",
        "装饰物": library_dir / "decoration.json",
    }

    lines = []
    for dimension_label, filepath in files.items():
        if not filepath.exists():
            raise FileNotFoundError(
                f"Material library file not found: {filepath}. "
                f"Ensure the material_library/ directory is present at the project root."
            )
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Malformed JSON in {filepath}: {e}") from e

        elements = data.get("elements", [])
        lines.append(f"\n### {dimension_label} ({len(elements)} 个元素)\n")
        for elem in elements:
            keywords = ",".join(elem.get("visual_keywords", [])[:10])
            signals = ",".join(elem.get("signals", [])[:10])
            use = elem.get("typical_use", "")
            name = elem.get("name", "")
            name_en = elem.get("name_en", "")
            elem_id = elem.get("id", "")
            line = (
                f"[{dimension_label}] {name} / {name_en} (id:{elem_id})"
                f" | keywords: {keywords}"
                f" | signals: {signals}"
                f" | use: {use}"
            )
            lines.append(line)

    return "\n".join(lines)


def _build_element_index(library_dir: Path | None = None) -> dict[str, dict]:
    """Build an index of all material library elements keyed by element ID.

    Used for post-hoc traceability lookup after the LLM produces recommendations
    with element_id values.

    Args:
        library_dir: Path to the material_library directory.

    Returns:
        Dictionary mapping element_id -> element dict from the JSON files.
    """
    if library_dir is None:
        library_dir = _MATERIAL_LIBRARY_DIR

    index: dict[str, dict] = {}
    for filename in ["color.json", "texture.json", "decoration.json"]:
        filepath = library_dir / filename
        if not filepath.exists():
            continue
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        for elem in data.get("elements", []):
            elem_id = elem.get("id", "")
            if elem_id:
                index[elem_id] = elem
    return index


def _enrich_with_sources(
    result: RecommendationResult,
    element_index: dict[str, dict],
) -> RecommendationResult:
    """Populate source traceability fields via post-hoc element lookup.

    The LLM produces recommendations with element_id values but leaves
    source_reports and source_heading empty. This function looks up each element
    in the material library index and copies the traceability fields.

    Args:
        result: The LLM-produced RecommendationResult with element_ids.
        element_index: Dict mapping element_id -> element data from JSON files.

    Returns:
        A new RecommendationResult with source_reports and source_heading
        populated for each ElementRecommendation.
    """

    def enrich_list(
        recs: list[ElementRecommendation],
    ) -> list[ElementRecommendation]:
        enriched = []
        for rec in recs:
            elem = element_index.get(rec.element_id, {})
            raw_source = elem.get("source_report", "")
            # Split multiple sources separated by " + " and deduplicate
            source_reports = list(
                dict.fromkeys(
                    s.strip() for s in raw_source.split(" + ") if s.strip()
                )
            )
            source_heading = elem.get("source_heading", "")
            enriched.append(
                rec.model_copy(
                    update={
                        "source_reports": source_reports,
                        "source_heading": source_heading,
                    }
                )
            )
        return enriched

    return RecommendationResult(
        concept_analysis=result.concept_analysis,
        colors=enrich_list(result.colors),
        textures=enrich_list(result.textures),
        decorations=enrich_list(result.decorations),
    )


def _format_recommendations_as_text(result: RecommendationResult) -> str:
    """Format a RecommendationResult as a readable markdown message for conversation history.

    Args:
        result: The recommendation result to format.

    Returns:
        A markdown-formatted string suitable for display.
    """
    lines = [f"**概念分析**: {result.concept_analysis}\n"]

    dimension_groups = [
        ("候选颜色", result.colors),
        ("候选质地", result.textures),
        ("候选装饰物", result.decorations),
    ]
    for dimension_label, recs in dimension_groups:
        lines.append(f"### {dimension_label}")
        for i, rec in enumerate(recs, 1):
            source_info = ""
            if rec.source_heading:
                report_ids = [r.split("/")[0][:8] for r in rec.source_reports]
                source_info = (
                    f" *(来源: {rec.source_heading}，报告: {', '.join(report_ids)})*"
                )
            lines.append(
                f"{i}. **{rec.element_name}** ({rec.element_name_en})"
                f" — 相关性: {rec.relevance_score:.2f}\n"
                f"   {rec.reasoning}{source_info}"
            )
        lines.append("")

    return "\n".join(lines)


# ===== GRAPH NODES =====

def recommend(state: RecommenderState, config: RunnableConfig) -> dict:
    """Generate material recommendations based on conversation state.

    Loads the full material library, injects it into the system prompt, and
    calls the LLM with structured output to produce recommendations. After
    the LLM responds, source traceability fields are enriched via post-hoc
    element lookup.

    Multi-turn conversations are naturally supported: the full message history
    in state["messages"] is passed to the LLM, allowing it to see previous
    recommendations and user refinement requests.

    Model is controlled by config["configurable"]["recommender_model"]
    (default: "azure_openai:gpt-4.1").

    Args:
        state: Current RecommenderState including full message history.
        config: LangGraph runnable config.

    Returns:
        State update dict with new messages and structured recommendations.
    """
    configurable = config.get("configurable", {})
    model = _build_model(
        configurable.get("recommender_model", _DEFAULT_RECOMMENDER_MODEL),
        temperature=0.7,
    )
    structured_model = model.with_structured_output(RecommendationResult)

    # Build system prompt with full material library (no source fields)
    material_library_text = load_material_library()
    system_content = recommender_system_prompt.format(
        material_library=material_library_text,
    )

    messages = [SystemMessage(content=system_content)] + list(state["messages"])
    result: RecommendationResult = structured_model.invoke(messages)

    # Post-hoc source enrichment (never generated by the LLM)
    element_index = _build_element_index()
    result = _enrich_with_sources(result, element_index)

    # Serialize result to a human-readable AI message for multi-turn conversation history
    recommendations_text = _format_recommendations_as_text(result)

    return {
        "messages": [AIMessage(content=recommendations_text)],
        "recommendations": result,
    }


# ===== GRAPH DEFINITION =====

def _build_graph() -> StateGraph:
    """Construct the material recommender StateGraph."""
    graph = StateGraph(RecommenderState)
    graph.add_node("recommend", recommend)
    graph.add_edge(START, "recommend")
    graph.add_edge("recommend", END)
    return graph


recommender_agent = _build_graph().compile()
