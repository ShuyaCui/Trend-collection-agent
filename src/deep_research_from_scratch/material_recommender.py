
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

import numpy as np
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import AzureOpenAIEmbeddings
from langgraph.graph import END, START, StateGraph

from deep_research_from_scratch.Helper import GenAIToken
from deep_research_from_scratch.prompts import recommender_system_prompt
from deep_research_from_scratch.state_recommender import (
    ElementRecommendation,
    ImageReference,
    RecommendationResult,
    RecommenderState,
)

load_dotenv()

_DEFAULT_RECOMMENDER_MODEL = "azure_openai:GPT-55-2026-04-24"
_MATERIAL_LIBRARY_DIR = Path(__file__).parent.parent.parent / "material_library"
_REPORTS_DIR = Path(__file__).parent.parent.parent / "reports"
_IMAGE_EMBEDDINGS_CACHE = _MATERIAL_LIBRARY_DIR / "image_embeddings.npz"
_TOP_K_IMAGES = 3


def _normalize_model_id(model_id: str) -> str:
    """Normalize Azure model identifiers to use the expected deployment casing."""
    provider, separator, deployment = model_id.partition(":")
    if not separator:
        return model_id
    return f"{provider}{separator}{deployment.upper()}"


def _build_model(model_id: str, **kwargs):
    """Build an Azure OpenAI model instance."""
    normalized_model_id = _normalize_model_id(model_id)
    deployment = normalized_model_id.split(":")[-1]
    return init_chat_model(
        model=normalized_model_id,
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        azure_deployment=deployment,
        azure_ad_token_provider=lambda: GenAIToken().token(),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        default_headers={
            "project-name": os.getenv("HEADERS_PROJECT_NAME"),
            "userid": os.getenv("HEADERS_USERID"),
        },
        **kwargs,
    )


def _build_embedding_model() -> AzureOpenAIEmbeddings:
    """Build an AzureOpenAIEmbeddings client using TEXT-EMBEDDING-3-SMALL."""
    return AzureOpenAIEmbeddings(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        deployment="TEXT-EMBEDDING-3-SMALL",
        api_version="2024-09-01-preview",
        azure_ad_token_provider=lambda: GenAIToken().token(),
        default_headers={
            "project-name": os.getenv("HEADERS_PROJECT_NAME"),
            "userid": os.getenv("HEADERS_USERID"),
        },
    )


def _load_all_image_metadata(reports_dir: Path | None = None) -> list[dict]:
    """Scan all report directories for images_metadata.json and aggregate records.

    Each returned record has 'local_path', 'description', and 'report_id' keys.
    """
    if reports_dir is None:
        reports_dir = _REPORTS_DIR
    records: list[dict] = []
    for meta_path in sorted(reports_dir.glob("*/images/images_metadata.json")):
        report_id = meta_path.parent.parent.name
        try:
            with open(meta_path, encoding="utf-8") as f:
                entries = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        for entry in entries:
            local_path = entry.get("local_path", "")
            description = entry.get("description", "")
            if local_path and description:
                records.append({
                    "local_path": local_path,
                    "description": description,
                    "report_id": report_id,
                })
    return records


def _is_cache_valid(records: list[dict], cache_path: Path) -> bool:
    """Return True if the embedding cache exists and is up-to-date."""
    if not cache_path.exists():
        return False
    cached = np.load(str(cache_path), allow_pickle=True)
    cached_metadata = json.loads(str(cached["metadata"]))
    if len(cached_metadata) != len(records):
        return False
    # Invalidate if any images_metadata.json was modified after the cache
    cache_mtime = cache_path.stat().st_mtime
    for meta_path in (_REPORTS_DIR).glob("*/images/images_metadata.json"):
        if meta_path.stat().st_mtime > cache_mtime:
            return False
    return True


def _build_image_index(
    reports_dir: Path | None = None,
    cache_path: Path | None = None,
) -> tuple[np.ndarray, list[dict]]:
    """Build or load the image embedding index.

    Returns (embeddings_matrix, metadata_list) where embeddings_matrix has
    shape (N, D) and metadata_list[i] corresponds to embeddings_matrix[i].
    """
    if cache_path is None:
        cache_path = _IMAGE_EMBEDDINGS_CACHE
    records = _load_all_image_metadata(reports_dir)
    if _is_cache_valid(records, cache_path):
        cached = np.load(str(cache_path), allow_pickle=True)
        embeddings = cached["embeddings"]
        metadata = json.loads(str(cached["metadata"]))
        return embeddings, metadata
    # Build fresh index
    emb_model = _build_embedding_model()
    descriptions = [r["description"] for r in records]
    vectors = np.array(emb_model.embed_documents(descriptions), dtype=float)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        str(cache_path),
        embeddings=vectors,
        metadata=json.dumps(records, ensure_ascii=False),
    )
    return vectors, records


def _build_element_query(element: ElementRecommendation, element_index: dict[str, dict]) -> str:
    """Construct a retrieval query string from an element's name and visual keywords."""
    raw = element_index.get(element.element_id, {})
    keywords: list[str] = raw.get("visual_keywords", [])
    name = element.element_name
    if keywords:
        return f"{name} {' '.join(keywords)}"
    return name


def _search_images(
    query: str,
    embeddings: np.ndarray,
    metadata: list[dict],
    emb_model: AzureOpenAIEmbeddings,
    top_k: int = _TOP_K_IMAGES,
) -> list[ImageReference]:
    """Retrieve top-k most similar images to a query via cosine similarity."""
    q_vec = np.array(emb_model.embed_query(query), dtype=float)
    # Cosine similarity: dot product of unit vectors
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    normed = embeddings / norms
    q_norm = q_vec / (np.linalg.norm(q_vec) or 1.0)
    scores = normed @ q_norm
    top_indices = np.argsort(scores)[::-1][:top_k]
    results = []
    for idx in top_indices:
        m = metadata[idx]
        results.append(ImageReference(local_path=m["local_path"], description=m["description"]))
    return results


def load_material_library(library_dir: Path | None = None) -> str:
    """Load and format all material library elements for LLM context injection.

    Source traceability fields are excluded from prompt context and added
    via post-hoc lookup after recommendations are produced.
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
            raise FileNotFoundError(f"Material library file not found: {filepath}")
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
    """Build an index of all material library elements keyed by element ID."""
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
    """Populate source traceability fields via post-hoc element lookup."""

    def enrich_list(recs: list[ElementRecommendation]) -> list[ElementRecommendation]:
        enriched = []
        for rec in recs:
            elem = element_index.get(rec.element_id, {})
            raw_source = elem.get("source_report", "")
            source_reports = list(
                dict.fromkeys(s.strip() for s in raw_source.split(" + ") if s.strip())
            )
            source_heading = elem.get("source_heading", "")
            enriched.append(
                rec.model_copy(update={"source_reports": source_reports, "source_heading": source_heading})
            )
        return enriched

    return RecommendationResult(
        concept_analysis=result.concept_analysis,
        colors=enrich_list(result.colors),
        textures=enrich_list(result.textures),
        decorations=enrich_list(result.decorations),
    )


def _format_recommendations_as_text(result: RecommendationResult) -> str:
    """Format a RecommendationResult as readable markdown for conversation history."""
    lines = [f"**概念分析**: {result.concept_analysis}\n"]
    for dimension_label, recs in [
        ("候选颜色", result.colors),
        ("候选质地", result.textures),
        ("候选装饰物", result.decorations),
    ]:
        lines.append(f"### {dimension_label}")
        for i, rec in enumerate(recs, 1):
            source_info = ""
            if rec.source_heading:
                report_ids = [r.split("/")[0][:8] for r in rec.source_reports]
                source_info = f" *(来源: {rec.source_heading}，报告: {', '.join(report_ids)})*"
            lines.append(
                f"{i}. **{rec.element_name}** ({rec.element_name_en})\n"
                f"   {rec.reasoning}{source_info}"
            )
            for img in rec.reference_images:
                lines.append(f"   📷 {img.description} ({img.local_path})")
        lines.append("")
    return "\n".join(lines)


def recommend(state: RecommenderState, config: RunnableConfig) -> dict:
    """Generate material recommendations based on conversation state.

    Loads the full material library, builds the system prompt, calls LLM with
    structured output, then enriches results with source traceability via post-hoc
    lookup. Multi-turn conversations are supported through full message history.

    Model is controlled by config["configurable"]["recommender_model"]
    (default: "azure_openai:gpt-4.1").
    """
    configurable = config.get("configurable", {})
    model = _build_model(
        configurable.get("recommender_model", _DEFAULT_RECOMMENDER_MODEL),
        temperature=0.7,
    )
    structured_model = model.with_structured_output(RecommendationResult)

    material_library_text = load_material_library()
    system_content = recommender_system_prompt.format(material_library=material_library_text)

    messages = [SystemMessage(content=system_content)] + list(state["messages"])
    result: RecommendationResult = structured_model.invoke(messages)

    element_index = _build_element_index()
    result = _enrich_with_sources(result, element_index)

    return {
        "messages": [],
        "recommendations": result,
    }


def attach_images(state: RecommenderState) -> dict:
    """Attach reference images to each recommended element via embedding retrieval.

    Loads (or builds) the image embedding index, then for each ElementRecommendation
    in the current recommendations, computes a query from the element's name and
    visual keywords and retrieves the top-k most similar images.
    """
    result: RecommendationResult | None = state.get("recommendations")
    if result is None:
        return {}

    element_index = _build_element_index()
    embeddings, metadata = _build_image_index()
    emb_model = _build_embedding_model()

    def attach_to_list(recs: list[ElementRecommendation]) -> list[ElementRecommendation]:
        updated = []
        for rec in recs:
            query = _build_element_query(rec, element_index)
            images = _search_images(query, embeddings, metadata, emb_model)
            updated.append(rec.model_copy(update={"reference_images": images}))
        return updated

    enriched_result = RecommendationResult(
        concept_analysis=result.concept_analysis,
        colors=attach_to_list(result.colors),
        textures=attach_to_list(result.textures),
        decorations=attach_to_list(result.decorations),
    )

    recommendations_text = _format_recommendations_as_text(enriched_result)
    return {
        "messages": [AIMessage(content=recommendations_text)],
        "recommendations": enriched_result,
    }


def _build_graph() -> StateGraph:
    """Construct the material recommender StateGraph."""
    graph = StateGraph(RecommenderState)
    graph.add_node("recommend", recommend)
    graph.add_node("attach_images", attach_images)
    graph.add_edge(START, "recommend")
    graph.add_edge("recommend", "attach_images")
    graph.add_edge("attach_images", END)
    return graph


recommender_agent = _build_graph().compile()
