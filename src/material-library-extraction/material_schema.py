"""Pydantic schemas for the Material Library extraction pipeline.

Defines the data models for element cards, dimension files,
persona catalog, and index metadata.
"""

from __future__ import annotations

import hashlib
import re
from typing import Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DIMENSIONS = ("颜色", "装饰物", "透明度与质地")
DIMENSION_EN = {"颜色": "color", "装饰物": "decoration", "透明度与质地": "texture"}

MATURITY_LEVELS = ("主流", "上升", "实验性")

AESTHETIC_PERSONAS = (
    "科技净澈",
    "天然奢养",
    "奢华克制",
    "感官甜品",
    "自然清体",
    "可视科技",
)

# Map Chinese dimension labels found in reports to canonical enum values.
DIMENSION_ALIASES: dict[str, str] = {
    "颜色": "颜色",
    "颜色趋势": "颜色",
    "装饰": "装饰物",
    "装饰物": "装饰物",
    "装饰趋势": "装饰物",
    "纹理": "透明度与质地",
    "纹理感": "透明度与质地",
    "纹理感趋势": "透明度与质地",
    "透明度": "透明度与质地",
    "透明度与质地": "透明度与质地",
    "质地": "透明度与质地",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def slugify(text: str) -> str:
    """Convert Chinese/English text to a URL-safe slug."""
    ascii_text = text.encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    if not slug:
        slug = hashlib.md5(text.encode()).hexdigest()[:8]  # noqa: S324
    return slug


def make_element_id(
    product_category: str,
    dimension: str,
    name: str,
    source_section: str,
) -> str:
    """Generate a deterministic element ID.

    Format: ``{category_slug}-{dim_en}-{name_slug}-{hash6}``
    """
    cat_slug = slugify(product_category)[:8]
    dim_en = DIMENSION_EN.get(dimension, slugify(dimension))
    name_slug = slugify(name)[:20]
    raw = f"{product_category}|{dimension}|{name}|{source_section}"
    short_hash = hashlib.sha256(raw.encode()).hexdigest()[:6]
    return f"{cat_slug}-{dim_en}-{name_slug}-{short_hash}"


# ---------------------------------------------------------------------------
# Core element model
# ---------------------------------------------------------------------------

class MaterialElement(BaseModel):
    """A single design element extracted from a trend report."""

    id: str = Field(default="", description="Deterministic ID; set after extraction")
    dimension: Literal["颜色", "装饰物", "透明度与质地"]
    name: str = Field(description="Element name in Chinese")
    name_en: str = Field(description="Element name in English")
    visual_keywords: list[str] = Field(
        description="Scannable visual descriptors (3-8 items)",
    )
    aesthetic_persona: Literal[
        "科技净澈", "天然奢养", "奢华克制", "感官甜品", "自然清体", "可视科技"
    ] = Field(description="Closest aesthetic persona from the predefined set")
    signals: list[str] = Field(
        description="What this element communicates to consumers (2-5 items)",
    )
    maturity: Literal["主流", "上升", "实验性"]
    year_range: str = Field(default="2025-2026")
    typical_use: str = Field(description="Typical product/usage context")
    source_section: str = Field(description="Report section heading reference")
    source_heading: str = Field(
        default="",
        description="Exact heading text from the report for traceability",
    )
    source_report: str = Field(
        default="",
        description="Source report filename",
    )
    product_category: str = Field(
        default="",
        description="Product category, e.g. 饮料, 洗发水, 面部精华",
    )


# ---------------------------------------------------------------------------
# LLM extraction output (per-chapter)
# ---------------------------------------------------------------------------

class ChapterExtraction(BaseModel):
    """LLM output for a single chapter (one dimension) of a report."""

    dimension: Literal["颜色", "装饰物", "透明度与质地"]
    elements: list[MaterialElement]


# ---------------------------------------------------------------------------
# Cached per-report extraction result
# ---------------------------------------------------------------------------

class ReportExtraction(BaseModel):
    """Full extraction result for one report, cached for incremental rebuilds."""

    source_report: str
    product_category: str
    extraction_date: str
    file_hash: str = Field(description="SHA-256 of source report content")
    elements: list[MaterialElement]


# ---------------------------------------------------------------------------
# Dimension file (color.json / decoration.json / texture.json)
# ---------------------------------------------------------------------------

class DimensionFile(BaseModel):
    """Output file for a single dimension, merging elements from all reports."""

    dimension: str
    dimension_en: str
    last_updated: str
    主流: list[MaterialElement] = Field(default_factory=list)
    上升: list[MaterialElement] = Field(default_factory=list)
    实验性: list[MaterialElement] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Persona catalog
# ---------------------------------------------------------------------------

class PersonaEntry(BaseModel):
    """One aesthetic persona with description and typical element combos."""

    name: str
    description: str
    typical_colors: list[str] = Field(default_factory=list)
    typical_decorations: list[str] = Field(default_factory=list)
    typical_textures: list[str] = Field(default_factory=list)


class PersonaCatalog(BaseModel):
    """Complete persona catalog written to personas.json."""

    last_updated: str
    personas: list[PersonaEntry]


# ---------------------------------------------------------------------------
# Index metadata
# ---------------------------------------------------------------------------

class ProcessedReport(BaseModel):
    """Metadata for a single processed report in index.json."""

    filename: str
    product_category: str
    extraction_date: str
    file_hash: str
    element_count: int
    cache_path: str


class IndexMetadata(BaseModel):
    """Top-level index.json structure."""

    last_updated: str
    total_elements: int = 0
    color_count: int = 0
    decoration_count: int = 0
    texture_count: int = 0
    processed_reports: list[ProcessedReport] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Predefined persona catalog
# ---------------------------------------------------------------------------

PERSONA_CATALOG: list[PersonaEntry] = [
    PersonaEntry(
        name="科技净澈",
        description="以无色透明、高折光、极简精密为核心的科技感审美。"
        "传达高纯度、实验室级精炼、配方自信。",
        typical_colors=["无色透明", "冷感透明", "极浅色"],
        typical_decorations=["微囊悬浮", "双相结构", "规则悬浮颗粒"],
        typical_textures=["高折光水感", "清透精华感", "液晶反光"],
    ),
    PersonaEntry(
        name="天然奢养",
        description="以琥珀金、蜂蜜色、温润油感为核心的天然滋养审美。"
        "传达珍稀植物、发酵活性、贵价天然原料。",
        typical_colors=["浅琥珀", "蜂蜜金", "浅茶金"],
        typical_decorations=["油珠悬浮", "植物碎片", "双相分层"],
        typical_textures=["丝缎油感", "蜜感浓润", "半透明柔光"],
    ),
    PersonaEntry(
        name="奢华克制",
        description="以香槟微金、细腻珠光、极致均匀为核心的低调奢华审美。"
        "传达精密工艺、稀缺成分、少即是贵。",
        typical_colors=["香槟金微光", "浅金色", "乳白半透明"],
        typical_decorations=["细微珠光", "微金感悬浮", "精致油珠"],
        typical_textures=["丝缎光泽", "高密度轻盈", "柔润内发光"],
    ),
    PersonaEntry(
        name="感官甜品",
        description="以奶白、焦糖、绵密厚乳为核心的甜品化审美。"
        "传达温暖、醇厚、甜蜜、可食用联想。",
        typical_colors=["奶白", "焦糖色", "米白", "可可棕"],
        typical_decorations=["奶盖", "拉花", "顶部碎料", "果肉可见"],
        typical_textures=["绵密厚乳", "顺滑奶感", "慕斯感"],
    ),
    PersonaEntry(
        name="自然清体",
        description="以植物绿、纤维感、天然浑浊为核心的健康自然审美。"
        "传达真实、低加工、膳食纤维、功能性。",
        typical_colors=["植物深绿", "灰绿", "黄绿", "番茄红"],
        typical_decorations=["纤维悬浮", "果肉颗粒", "浆感痕迹"],
        typical_textures=["浆感浑浊", "纤维感", "轻微颗粒"],
    ),
    PersonaEntry(
        name="可视科技",
        description="以透明基底中可见结构（微囊、颗粒、分相）为核心的2026前沿审美。"
        "传达功效可视化、靶向输送、科技门槛。",
        typical_colors=["冷感透明", "冰透感", "极浅色基底"],
        typical_decorations=["肉眼可见微囊", "悬浮珠粒", "凝胶中微滴"],
        typical_textures=["凝胶结构感", "冻感流体", "液晶精华感"],
    ),
]
