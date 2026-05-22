
"""End-to-end deep research system combining scope, research, and report synthesis.

This module composes the scoping, multi-agent research, and report generation
components into a single LangGraph workflow. The pipeline:
1. Clarifies user intent and generates a research brief
2. Conducts parallel research on multiple sub-topics
3. Synthesizes findings into a comprehensive markdown report

This is the main entry point for the complete deep research system.
"""

import asyncio
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from deep_research_from_scratch.Helper import GenAIToken
from deep_research_from_scratch.multi_agent_supervisor import supervisor_agent
from deep_research_from_scratch.prompts import final_report_generation_prompt
from deep_research_from_scratch.research_agent_scope import scope_research
from deep_research_from_scratch.state_scope import AgentState
from deep_research_from_scratch.trend_dimensions import (
    format_dimensions_for_prompt,
    load_trend_dimensions,
)
from deep_research_from_scratch.utils import (
    download_images,
    get_today_str,
    normalize_model_id,
)

load_dotenv()


# ===== CONFIGURATION =====

_DEFAULT_WRITER_MODEL = "azure_openai:GPT-54-2026-03-05"


def _build_model(model_id: str, **kwargs):
    """Build an Azure OpenAI model instance from a model identifier string.

    Extracts the deployment name from the model identifier using the
    convention that model name equals deployment name (e.g.,
    "azure_openai:gpt-5.3" -> deployment "GPT-5.3").
    """
    normalized_model_id = normalize_model_id(model_id)
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


# ===== REPORT GENERATION =====

def _build_report_dimensions_section() -> str:
    """Build the expert dimensions section for the final report prompt.

    Returns a full XML section string when dimensions are available,
    or an empty string for graceful degradation (no empty XML block).
    """
    dims = format_dimensions_for_prompt(load_trend_dimensions())
    if not dims:
        return ""
    return (
        "<Expert Dimensions>\n"
        "Use these expert analytical dimensions where relevant to structure the final report, "
        "organize findings, and identify gaps or future opportunities:\n"
        f"{dims}\n"
        "Apply them selectively based on the research topic rather than forcing every dimension.\n"
        "</Expert Dimensions>\n"
    )


async def final_report_generation(
    state: AgentState,
    config: RunnableConfig,
):
    """Generate the final comprehensive report from research findings.

    Downloads collected images to local storage first, then synthesizes
    research notes into a well-structured markdown report with embedded
    image references.

    Model is controlled by config["configurable"]["writer_model"]
    (default: "azure_openai:GPT-54-2026-03-05").
    Backward compatibility: also accepts "final_report_model".

    Args:
        state: Output from supervisor phase containing notes, research brief,
            and accumulated images.
        config: LangGraph runtime config; supports configurable["writer_model"]
            (or legacy configurable["final_report_model"]) and
            configurable["thread_id"] for output directory naming.

    Returns:
        Dictionary containing the final markdown report and downloaded images.
    """
    configurable = config.get("configurable", {})
    writer_model = _build_model(
        configurable.get(
            "writer_model",
            configurable.get("final_report_model", _DEFAULT_WRITER_MODEL),
        ),
        temperature=0,
    )

    notes = state.get("notes", [])
    rq = state.get("research_brief")
    research_brief = rq.research_brief if hasattr(rq, "research_brief") else (rq or "")
    images = state.get("images", [])

    # Download images BEFORE report generation so local paths are available
    thread_id = configurable.get("thread_id", "") or str(uuid.uuid4())
    # Anchor to project root so the path is correct regardless of
    # the working directory (e.g. when running from notebooks/).
    _project_root = Path(__file__).resolve().parent.parent.parent
    output_dir = _project_root / "reports" / thread_id / "images"

    if images:
        downloaded_images = await asyncio.to_thread(download_images, images, output_dir)
    else:
        downloaded_images = []

    # Format image metadata for the report prompt
    if downloaded_images:
        lines = []
        for i, img in enumerate(downloaded_images, 1):
            # Use relative path so the report is portable regardless of where it is opened
            path = ("images/" + Path(img.local_path).name) if img.local_path else img.url
            line = f"[{i}] {img.title or img.url}"
            if img.description:
                line += f"\n    Description: {img.description}"
            if img.source_page:
                line += f"\n    Source: {img.source_page}"
            line += f"\n    Path: {path}"
            lines.append(line)
        images_text = "\n".join(lines)
    else:
        images_text = "No images were found during research."

    findings_text = "\n\n".join(notes) if isinstance(notes, list) else str(notes)

    system_prompt = final_report_generation_prompt.format(
        research_brief=research_brief,
        date=get_today_str(),
        findings=findings_text,
        images=images_text,
    )

    # Append expert dimensions as supplementary guidance in the user turn
    dims = _build_report_dimensions_section()
    user_content = "Generate the comprehensive research report now."
    if dims:
        user_content = f"{dims}\n\n{user_content}"

    result = await writer_model.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ])

    return {
        "final_report": result.content,
        "images": downloaded_images or images,
    }


# ===== GRAPH CONSTRUCTION =====

deep_researcher_builder = StateGraph(AgentState)

deep_researcher_builder.add_node("scope_research", scope_research)
deep_researcher_builder.add_node("supervisor_agent", supervisor_agent)
deep_researcher_builder.add_node("final_report_generation", final_report_generation)

deep_researcher_builder.add_edge(START, "scope_research")
deep_researcher_builder.add_edge("scope_research", "supervisor_agent")
deep_researcher_builder.add_edge("supervisor_agent", "final_report_generation")
deep_researcher_builder.add_edge("final_report_generation", END)

agent = deep_researcher_builder.compile()
