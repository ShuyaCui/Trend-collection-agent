
"""End-to-end deep research system combining scope, research, and report synthesis.

This module composes the scoping, multi-agent research, and report generation
components into a single LangGraph workflow. The pipeline:
1. Clarifies user intent and generates a research brief
2. Conducts parallel research on multiple sub-topics
3. Synthesizes findings into a comprehensive markdown report

This is the main entry point for the complete deep research system.
"""

import os

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from deep_research_from_scratch.Helper import GenAIToken
from deep_research_from_scratch.multi_agent_supervisor import supervisor_agent
from deep_research_from_scratch.prompts import final_report_generation_prompt
from deep_research_from_scratch.research_agent_scope import scope_research
from deep_research_from_scratch.state_multi_agent_supervisor import SupervisorState
from deep_research_from_scratch.state_scope import ResearchQuestion
from deep_research_from_scratch.trend_dimensions import (
    format_dimensions_for_prompt,
    load_trend_dimensions,
)
from deep_research_from_scratch.utils import get_today_str, normalize_model_id

load_dotenv()


# ===== CONFIGURATION =====

_DEFAULT_FINAL_REPORT_MODEL = "azure_openai:gpt-5.3"


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
    state: SupervisorState,
    config: RunnableConfig,
):
    """Generate the final comprehensive report from research findings.

    Takes the accumulated research notes from the supervisor phase and synthesizes
    them into a well-structured markdown report. The report includes analysis,
    findings, and actionable insights based on the research brief.

    Model is controlled by config["configurable"]["final_report_model"]
    (default: "azure_openai:gpt-5.3").

    Args:
        state: Output from supervisor phase containing notes and research brief
        config: LangGraph runtime config; supports configurable["final_report_model"]

    Returns:
        Dictionary containing the final markdown report and propagated images.
    """
    configurable = config.get("configurable", {})
    final_report_model = _build_model(
        configurable.get("final_report_model", _DEFAULT_FINAL_REPORT_MODEL),
        temperature=0,
    )

    notes = state.get("notes", [])
    research_brief = state.get("research_brief", ResearchQuestion()).research_brief

    system_prompt = final_report_generation_prompt.format(
        date=get_today_str(),
        trend_dimensions=_build_report_dimensions_section(),
    )
    user_prompt = (
        f"<research_brief>\n{research_brief}\n</research_brief>\n\n"
        f"<notes>\n{notes}\n</notes>"
    )

    result = await final_report_model.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ])

    return {
        "final_report": result.content,
        "images": state.get("images", []),
    }


# ===== GRAPH CONSTRUCTION =====

builder = StateGraph(SupervisorState)

builder.add_node("scope_research", scope_research)
builder.add_node("supervisor_agent", supervisor_agent)
builder.add_node("final_report_generation", final_report_generation)

builder.add_edge(START, "scope_research")
builder.add_edge("scope_research", "supervisor_agent")
builder.add_edge("supervisor_agent", "final_report_generation")
builder.add_edge("final_report_generation", END)

agent = builder.compile()
