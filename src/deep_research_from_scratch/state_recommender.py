
"""State Definitions and Pydantic Schemas for Material Recommendation.

This defines state objects and structured output schemas for the material
recommendation workflow, including the RecommenderState and Pydantic models
for structured recommendation output.
"""

from langgraph.graph import MessagesState
from pydantic import BaseModel, Field

# ===== STRUCTURED OUTPUT SCHEMAS =====

class ImageReference(BaseModel):
    """A reference image matched to a recommended element via embedding retrieval."""

    local_path: str = Field(description="Absolute local file path to the image.")
    description: str = Field(description="Chinese visual description of the image.")


class ElementRecommendation(BaseModel):
    """A single recommended material element from the library."""

    element_id: str = Field(
        description="The element's unique ID from the material library (must match exactly).",
    )
    element_name: str = Field(
        description="The element's Chinese name as it appears in the library.",
    )
    element_name_en: str = Field(
        description="The element's English name as it appears in the library.",
    )
    dimension: str = Field(
        description="The design dimension: 颜色 / 透明度与质地 / 装饰物.",
    )
    reasoning: str = Field(
        description="1-2 sentence explanation of the conceptual link to the user's query.",
    )
    source_reports: list[str] = Field(
        default_factory=list,
        description="Source report IDs — populated via post-hoc lookup, not by the LLM.",
    )
    source_heading: str = Field(
        default="",
        description="Source trend section heading — populated via post-hoc lookup, not by the LLM.",
    )
    reference_images: list[ImageReference] = Field(
        default_factory=list,
        description="Reference images matched via embedding retrieval — populated by attach_images node.",
    )


class RecommendationResult(BaseModel):
    """Structured result of a material recommendation query."""

    concept_analysis: str = Field(
        description=(
            "2-3 sentence analysis of the user's design concept and the key aesthetic "
            "associations driving the recommendations."
        ),
    )
    colors: list[ElementRecommendation] = Field(
        description="Recommended color elements (颜色 dimension).",
    )
    textures: list[ElementRecommendation] = Field(
        description="Recommended texture/transparency elements (透明度与质地 dimension).",
    )
    decorations: list[ElementRecommendation] = Field(
        description="Recommended decoration elements (装饰物 dimension).",
    )


# ===== STATE DEFINITIONS =====

class RecommenderState(MessagesState):
    """State for the material recommender agent.

    Extends MessagesState to support multi-turn conversations,
    storing the latest structured recommendation result for downstream
    consumption and post-hoc source traceability lookup.
    """

    recommendations: RecommendationResult | None = None
