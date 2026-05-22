
"""State Definitions and Pydantic Schemas for Research Agent.

This module defines the state objects and structured schemas used for
the research agent workflow, including researcher state management and output schemas.
"""

import operator

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from typing_extensions import Annotated, List, Sequence, TypedDict

# ===== IMAGE METADATA SCHEMA =====

class ImageResult(BaseModel):
    """Schema for image metadata collected during research."""

    url: str = Field(description="URL of the image")
    title: str = Field(
        description="Title or alt text of the image", default=""
    )
    source_page: str = Field(
        description="URL of the page where the image was found", default=""
    )
    description: str = Field(
        description="Brief description of the image content", default=""
    )
    local_path: str | None = Field(
        description="Local file path after download", default=None
    )
    # Page-discovery context (populated by batch_discover_images)
    discovery_method: str = Field(
        description="How the image was found: 'tavily' or 'httpx'", default="tavily"
    )
    page_title: str = Field(
        description="<title> of the page where the image was found", default=""
    )
    alt_text: str = Field(
        description="alt attribute of the <img> element", default=""
    )
    figcaption: str = Field(
        description="Caption from a parent <figure> element", default=""
    )

# ===== STATE DEFINITIONS =====

class ResearcherState(TypedDict):
    """State for the research agent containing message history and research metadata.

    This state tracks the researcher's conversation, iteration count for limiting
    tool calls, the research topic being investigated, compressed findings,
    and raw research notes for detailed analysis.
    """
    researcher_messages: Annotated[Sequence[BaseMessage], add_messages]
    tool_call_iterations: int
    research_topic: str
    compressed_research: str
    raw_notes: Annotated[List[str], operator.add]
    images: Annotated[List[ImageResult], operator.add]

class ResearcherOutputState(TypedDict):
    """Output state for the research agent containing final research results.

    This represents the final output of the research process with compressed
    research findings and all raw notes from the research process.
    """
    compressed_research: str
    raw_notes: Annotated[List[str], operator.add]
    researcher_messages: Annotated[Sequence[BaseMessage], add_messages]
    images: Annotated[List[ImageResult], operator.add]

# ===== STRUCTURED OUTPUT SCHEMAS =====

class ClarifyWithUser(BaseModel):
    """Schema for user clarification decisions during scoping phase."""
    need_clarification: bool = Field(
        description="Whether the user needs to be asked a clarifying question.",
    )
    question: str = Field(
        description="A question to ask the user to clarify the report scope",
    )
    verification: str = Field(
        description="Verify message that we will start research after the user has provided the necessary information.",
    )

class ResearchQuestion(BaseModel):
    """Schema for research brief generation."""
    research_brief: str = Field(
        description="A research question that will be used to guide the research.",
    )

class Summary(BaseModel):
    """Schema for webpage content summarization."""
    summary: str = Field(description="Concise summary of the webpage content")
    key_excerpts: str = Field(description="Important quotes and excerpts from the content")
