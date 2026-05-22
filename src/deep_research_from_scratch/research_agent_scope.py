
"""User Clarification and Research Brief Generation.

This module implements the scoping phase of the research workflow, where we:
1. Assess if the user's request needs clarification
2. Generate a detailed research brief from the conversation

The workflow uses structured output to make deterministic decisions about
whether sufficient context exists to proceed with research.
"""

import os
import urllib.parse  # noqa: F401 — ensure stdlib urllib.parse is cached before urllib3
from datetime import datetime

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, get_buffer_string
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command
from typing_extensions import Literal

from deep_research_from_scratch.Helper import GenAIToken
from deep_research_from_scratch.prompts import (
    clarify_with_user_instructions,
    transform_messages_into_research_topic_prompt,
)
from deep_research_from_scratch.state_scope import (
    AgentInputState,
    AgentState,
    ClarifyWithUser,
    ResearchQuestion,
)
from deep_research_from_scratch.trend_dimensions import (
    format_dimensions_for_prompt,
    load_trend_dimensions,
)

load_dotenv()

# ===== UTILITY FUNCTIONS =====

def get_today_str() -> str:
    """Get current date in a human-readable format."""
    return datetime.now().strftime("%a %b %-d, %Y")


def _build_scope_dimensions_section() -> str:
    """Build the analytical dimensions list for trend decomposition in the scope prompt.

    Returns a formatted dimension list when dimensions are available,
    or an empty string for graceful degradation.
    """
    dims = format_dimensions_for_prompt(load_trend_dimensions())
    if not dims:
        return ""
    return f"Available analytical dimensions for trend decomposition:\n{dims}"


# ===== CONFIGURATION =====

_DEFAULT_SCOPE_MODEL = "azure_openai:gpt-4.1"


def _normalize_model_id(model_id: str) -> str:
    """Normalize Azure model identifiers to use the expected deployment casing."""
    provider, separator, deployment = model_id.partition(":")
    if not separator:
        return model_id
    return f"{provider}{separator}{deployment.upper()}"


def _build_model(model_id: str, **kwargs):
    """Build an Azure OpenAI model instance from a model identifier string.

    Extracts the deployment name from the model identifier using the
    convention that model name equals deployment name (e.g.,
    "azure_openai:gpt-54-2026-03-05" -> deployment "GPT-54-2026-03-05").
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


# ===== WORKFLOW NODES =====

def clarify_with_user(state: AgentState, config: RunnableConfig) -> Command[Literal["write_research_brief", "__end__"]]:
    """Determine if the user's request contains sufficient information to proceed with research.

    Uses structured output to make deterministic decisions and avoid hallucination.
    Routes to either research brief generation or ends with a clarification question.

    Model is controlled by config["configurable"]["scope_model"]
    (default: "azure_openai:GPT-4.1").
    """
    configurable = config.get("configurable", {})
    model = _build_model(configurable.get("scope_model", _DEFAULT_SCOPE_MODEL), temperature=0.0)
    structured_output_model = model.with_structured_output(ClarifyWithUser)

    response = structured_output_model.invoke([
        HumanMessage(content=clarify_with_user_instructions.format(
            messages=get_buffer_string(messages=state["messages"]),
            date=get_today_str()
        ))
    ])

    if response.need_clarification:
        return Command(
            goto=END,
            update={"messages": [AIMessage(content=response.question)]}
        )
    else:
        return Command(
            goto="write_research_brief",
            update={"messages": [AIMessage(content=response.verification)]}
        )


def write_research_brief(state: AgentState, config: RunnableConfig):
    """Transform the conversation history into a comprehensive research brief.

    Uses structured output to ensure the brief follows the required format
    and contains all necessary details for effective research.

    Model is controlled by config["configurable"]["scope_model"]
    (default: "azure_openai:gpt-4.1").
    """
    configurable = config.get("configurable", {})
    model = _build_model(configurable.get("scope_model", _DEFAULT_SCOPE_MODEL), temperature=0.0)
    structured_output_model = model.with_structured_output(ResearchQuestion)

    response = structured_output_model.invoke([
        HumanMessage(content=transform_messages_into_research_topic_prompt.format(
            messages=get_buffer_string(state.get("messages", [])),
            date=get_today_str(),
            trend_dimensions=_build_scope_dimensions_section()
        ))
    ])

    return {
        "research_brief": response.research_brief,
        "supervisor_messages": [HumanMessage(content=f"{response.research_brief}.")]
    }


# ===== GRAPH CONSTRUCTION =====

deep_researcher_builder = StateGraph(AgentState, input_schema=AgentInputState)

deep_researcher_builder.add_node("clarify_with_user", clarify_with_user)
deep_researcher_builder.add_node("write_research_brief", write_research_brief)

deep_researcher_builder.add_edge(START, "clarify_with_user")
deep_researcher_builder.add_edge("write_research_brief", END)

scope_research = deep_researcher_builder.compile()
