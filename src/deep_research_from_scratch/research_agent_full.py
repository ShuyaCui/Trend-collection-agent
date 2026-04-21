
"""Full Multi-Agent Research System.

This module integrates all components of the research system:
- User clarification and scoping
- Research brief generation
- Multi-agent research coordination
- Final report generation

The system orchestrates the complete research workflow from initial user
input through final report delivery.
"""

import os

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from deep_research_from_scratch.Helper import GenAIToken
from deep_research_from_scratch.multi_agent_supervisor import supervisor_agent
from deep_research_from_scratch.prompts import final_report_generation_prompt
from deep_research_from_scratch.research_agent_scope import (
    clarify_with_user,
    write_research_brief,
)
from deep_research_from_scratch.state_scope import AgentInputState, AgentState
from deep_research_from_scratch.utils import get_today_str

load_dotenv()

# ===== CONFIGURATION =====

_DEFAULT_WRITER_MODEL = "azure_openai:gpt-5.3"


def _build_model(model_id: str, **kwargs):
    """Build an Azure OpenAI model instance from a model identifier string.

    Extracts the deployment name from the model identifier using the
    convention that model name equals deployment name (e.g.,
    "azure_openai:gpt-5.3" -> deployment "gpt-5.3").
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


# ===== FINAL REPORT GENERATION =====

async def final_report_generation(state: AgentState, config: RunnableConfig):
    """Generate the final research report.

    Synthesizes all research findings into a comprehensive final report.

    Model is controlled by config["configurable"]["writer_model"]
    (default: "azure_openai:gpt-5.3").
    """
    configurable = config.get("configurable", {})
    writer_model = _build_model(
        configurable.get("writer_model", _DEFAULT_WRITER_MODEL),
        temperature=1.0,
    )

    notes = state.get("notes", [])
    findings = "\n".join(notes)

    final_report_prompt = final_report_generation_prompt.format(
        research_brief=state.get("research_brief", ""),
        findings=findings,
        date=get_today_str()
    )

    final_report = await writer_model.ainvoke([HumanMessage(content=final_report_prompt)])

    return {
        "final_report": final_report.content,
        "messages": ["Here is the final report: " + final_report.content],
    }


# ===== GRAPH CONSTRUCTION =====

deep_researcher_builder = StateGraph(AgentState, input_schema=AgentInputState)

deep_researcher_builder.add_node("clarify_with_user", clarify_with_user)
deep_researcher_builder.add_node("write_research_brief", write_research_brief)
deep_researcher_builder.add_node("supervisor_subgraph", supervisor_agent)
deep_researcher_builder.add_node("final_report_generation", final_report_generation)

deep_researcher_builder.add_edge(START, "clarify_with_user")
deep_researcher_builder.add_edge("write_research_brief", "supervisor_subgraph")
deep_researcher_builder.add_edge("supervisor_subgraph", "final_report_generation")
deep_researcher_builder.add_edge("final_report_generation", END)

agent = deep_researcher_builder.compile()
