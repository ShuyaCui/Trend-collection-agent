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
    trend_time: str = Field(
        default="",
        description="Trend time range extracted from report title, e.g. '2025年11月—2026年5月'",
    )
    visual_keywords: list[str] = Field(
        description="Scannable visual descriptors (3-8 items)",
    )
    signals: list[str] = Field(
        description="What this element communicates to consumers (2-5 items)",
    )
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


class ThreeDimExtraction(BaseModel):
    """LLM output for a single-pass extraction of 颜色, 装饰物, and 透明度与质地.

    Each element self-declares its primary dimension, ensuring every concept is
    assigned to exactly one of the three non-style dimensions and cannot be
    duplicated across them.
    """

    elements: list[MaterialElement]


# ---------------------------------------------------------------------------
# Schema version — bump when ReportExtraction layout changes incompatibly so
# stale cache entries are automatically invalidated on next run.
# ---------------------------------------------------------------------------

EXTRACTION_SCHEMA_VERSION = 4


# ---------------------------------------------------------------------------
# Cached per-report extraction result
# ---------------------------------------------------------------------------

class ReportExtraction(BaseModel):
    """Full extraction result for one report, cached for incremental rebuilds."""

    schema_version: int = Field(
        default=1,
        description="Schema version; cache entries with a different version are discarded.",
    )
    source_report: str
    product_category: str
    trend_time: str = Field(default="", description="Trend time range from report title")
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
    elements: list[MaterialElement] = Field(default_factory=list)


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

