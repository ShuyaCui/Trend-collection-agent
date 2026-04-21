
"""Research Agent Implementation.

This module implements a research agent that can perform iterative web searches
and synthesis to answer complex research questions.
"""

import os

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    ToolMessage,
    filter_messages,
)
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from typing_extensions import Literal

from deep_research_from_scratch.Helper import GenAIToken
from deep_research_from_scratch.prompts import (
    compress_research_human_message,
    compress_research_system_prompt,
    research_agent_prompt,
)
from deep_research_from_scratch.state_research import (
    ResearcherOutputState,
    ResearcherState,
)
from deep_research_from_scratch.utils import get_today_str, tavily_search, think_tool

load_dotenv()

# ===== CONFIGURATION =====

# Model role defaults
_DEFAULT_RESEARCH_MODEL = "azure_openai:gpt-4.1"
_DEFAULT_SUMMARIZATION_MODEL = "azure_openai:gpt-4.1-mini"  # reserved; not yet used by an active node
_DEFAULT_COMPRESS_MODEL = "azure_openai:gpt-4.1"

# Tools are module-level (no model dependency)
tools = [tavily_search, think_tool]
tools_by_name = {tool.name: tool for tool in tools}


def _build_model(model_id: str, **kwargs):
    """Build an Azure OpenAI model instance from a model identifier string.

    Extracts the deployment name from the model identifier using the
    convention that model name equals deployment name (e.g.,
    "azure_openai:gpt-4.1" -> deployment "gpt-4.1").
    """
    deployment = model_id.split(":")[-1]
    return init_chat_model(
        model=model_id,
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


# ===== AGENT NODES =====

def llm_call(state: ResearcherState, config: RunnableConfig):
    """Analyze current state and decide on next actions.

    The model analyzes the current conversation state and decides whether to:
    1. Call search tools to gather more information
    2. Provide a final answer based on gathered information

    Model is controlled by config["configurable"]["research_model"]
    (default: "azure_openai:gpt-4.1").

    Returns updated state with the model's response.
    """
    configurable = config.get("configurable", {})
    model = _build_model(
        configurable.get("research_model", _DEFAULT_RESEARCH_MODEL),
        temperature=0.0,
    )
    model_with_tools = model.bind_tools(tools)

    return {
        "researcher_messages": [
            model_with_tools.invoke(
                [SystemMessage(content=research_agent_prompt)] + state["researcher_messages"]
            )
        ]
    }


def tool_node(state: ResearcherState):
    """Execute all tool calls from the previous LLM response.

    Executes all tool calls from the previous LLM responses.
    Returns updated state with tool execution results.
    """
    tool_calls = state["researcher_messages"][-1].tool_calls

    observations = []
    for tool_call in tool_calls:
        tool = tools_by_name[tool_call["name"]]
        observations.append(tool.invoke(tool_call["args"]))

    tool_outputs = [
        ToolMessage(
            content=observation,
            name=tool_call["name"],
            tool_call_id=tool_call["id"]
        ) for observation, tool_call in zip(observations, tool_calls)
    ]

    return {"researcher_messages": tool_outputs}


def compress_research(state: ResearcherState, config: RunnableConfig) -> dict:
    """Compress research findings into a concise summary.

    Takes all the research messages and tool outputs and creates
    a compressed summary suitable for the supervisor's decision-making.

    Model is controlled by config["configurable"]["compress_model"]
    (default: "azure_openai:gpt-4.1").
    """
    configurable = config.get("configurable", {})
    compress_model = _build_model(
        configurable.get("compress_model", _DEFAULT_COMPRESS_MODEL),
        temperature=0.0,
        max_tokens=16384,
    )

    system_message = compress_research_system_prompt.format(date=get_today_str())
    messages = (
        [SystemMessage(content=system_message)]
        + state.get("researcher_messages", [])
        + [HumanMessage(content=compress_research_human_message)]
    )
    response = compress_model.invoke(messages)

    raw_notes = [
        str(m.content) for m in filter_messages(
            state["researcher_messages"],
            include_types=["tool", "ai"]
        )
    ]

    return {
        "compressed_research": str(response.content),
        "raw_notes": ["\n".join(raw_notes)]
    }


# ===== ROUTING LOGIC =====

def should_continue(state: ResearcherState) -> Literal["tool_node", "compress_research"]:
    """Determine whether to continue research or provide final answer.

    Determines whether the agent should continue the research loop or provide
    a final answer based on whether the LLM made tool calls.

    Returns:
        "tool_node": Continue to tool execution
        "compress_research": Stop and compress research
    """
    messages = state["researcher_messages"]
    last_message = messages[-1]

    if last_message.tool_calls:
        return "tool_node"
    return "compress_research"


# ===== GRAPH CONSTRUCTION =====

agent_builder = StateGraph(ResearcherState, output_schema=ResearcherOutputState)

agent_builder.add_node("llm_call", llm_call)
agent_builder.add_node("tool_node", tool_node)
agent_builder.add_node("compress_research", compress_research)

agent_builder.add_edge(START, "llm_call")
agent_builder.add_conditional_edges(
    "llm_call",
    should_continue,
    {
        "tool_node": "tool_node",
        "compress_research": "compress_research",
    },
)
agent_builder.add_edge("tool_node", "llm_call")
agent_builder.add_edge("compress_research", END)

researcher_agent = agent_builder.compile()
