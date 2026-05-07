"""Extract structured material library from trend reports.

Reads Markdown trend reports from ``reports/``, extracts design elements
(颜色, 装饰物, 透明度与质地) via LLM structured output, and writes
per-dimension JSON files to ``material_library/``.

Usage::

    uv run python scripts/extract_material_library.py
    uv run python scripts/extract_material_library.py --force
    uv run python scripts/extract_material_library.py --reports-dir reports/ --output-dir material_library/
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv

# Ensure project root is on sys.path so we can import helpers.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from langchain.chat_models import init_chat_model  # noqa: E402
from langchain_core.messages import HumanMessage  # noqa: E402
from material_schema import (  # noqa: E402
    DIMENSION_EN,
    DIMENSIONS,
    MATURITY_LEVELS,
    PERSONA_CATALOG,
    ChapterExtraction,
    DimensionFile,
    IndexMetadata,
    MaterialElement,
    PersonaCatalog,
    ProcessedReport,
    ReportExtraction,
    make_element_id,
)

from deep_research_from_scratch.Helper import GenAIToken  # noqa: E402

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Report → category mapping
# ---------------------------------------------------------------------------

_CATEGORY_MAP: dict[str, str] = {
    "饮料": "饮料",
    "洗发水": "洗发水",
    "精华": "面部精华",
}


def _infer_category(filename: str) -> str:
    """Infer product category from report filename."""
    for keyword, category in _CATEGORY_MAP.items():
        if keyword in filename:
            return category
    return "未知品类"


# ---------------------------------------------------------------------------
# LLM helpers
# ---------------------------------------------------------------------------

_DEFAULT_MODEL = os.getenv(
    "MATERIAL_EXTRACTION_MODEL",
    "azure_openai:GPT-4O-2024-11-20",
)


def _build_model(model_id: str | None = None, **kwargs):
    """Build an Azure OpenAI model instance."""
    model_id = model_id or _DEFAULT_MODEL
    # Normalize: uppercase the deployment portion after the provider prefix
    provider, sep, deployment = model_id.partition(":")
    if sep:
        deployment = deployment.upper()
        model_id = f"{provider}{sep}{deployment}"
    else:
        deployment = model_id.upper()
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


# ---------------------------------------------------------------------------
# Extraction prompt
# ---------------------------------------------------------------------------

_EXTRACTION_PROMPT = """你是一个设计元素提取专家。你的任务是从以下趋势报告章节中提取结构化的设计元素卡片。

## 提取规则

1. **维度**: 你正在提取「{dimension}」维度的元素。
   - 颜色：色相、色调、色彩语言（如"琥珀金""植物绿""无色透明"）
   - 装饰物：液体中/表面的可见元素（如"微囊""奶盖""珠光""油珠悬浮"）
   - 透明度与质地：通透性 + 黏度 + 流动性 + 光泽 + 表面状态（如"高折光水感""凝胶感""丝缎流动"）

2. **粒度**: 每个独立的设计元素应该成为一张卡片。一个趋势段落可能包含1-3个独立元素。
   - 例如"原料本色与低人工感色彩"包含多个具体颜色：茶棕、奶白、果橙、莓红等，每个都是独立元素。
   - 但如果多个颜色构成一个整体概念（如"奶白—米白—焦糖—茶褐的柔和暖色系"），则作为一个元素。

3. **成熟度判定**:
   - "已经广泛出现""主流""当前最核心" → 主流
   - "正在上升""上升""新兴" → 上升
   - "实验性""概念化""尚有限制" → 实验性

4. **aesthetic_persona** 必须从以下预定义列表中选择最接近的一个:
   {personas}

5. **source_heading**: 必须填写该元素对应的报告中的原始章节标题文本。

6. **source_section**: 填写章节编号（如 "§4.1", "趋势3", "3.2"）。

7. **signals**: 该元素向消费者传达的信息，2-5项。

8. **visual_keywords**: 可扫描的视觉描述词，3-8项。

9. **name_en**: 提供准确的英文翻译。

10. **typical_use**: 典型的产品/使用场景。

## 报告内容（{dimension}部分）

{content}

## 输出要求

请提取该章节中所有独立的设计元素。不要遗漏任何趋势项。
每个趋势标题下至少应提取1个元素，复杂趋势可拆分为多个元素。
"""


# ---------------------------------------------------------------------------
# Chapter splitting
# ---------------------------------------------------------------------------

_CHAPTER_KEYWORDS: dict[str, list[str]] = {
    "颜色": ["颜色趋势", "颜色方向", "颜色", "底色", "色彩"],
    "装饰物": ["装饰趋势", "装饰", "可见元素", "可视化元素", "珠光", "微囊"],
    "透明度与质地": [
        "纹理感趋势",
        "纹理",
        "质地",
        "透明度",
        "黏度",
        "流动",
        "光泽",
    ],
}


def _split_report_into_chapters(
    report_text: str,
) -> dict[str, str]:
    """Split a report into dimension chapters using heading detection.

    Returns a dict mapping canonical dimension names to chapter text.
    Falls back to sending the entire report for each dimension if
    chapter boundaries can't be detected.
    """
    lines = report_text.split("\n")
    h2_indices: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        if line.startswith("## ") or line.startswith("# "):
            h2_indices.append((i, line))

    if not h2_indices:
        return {dim: report_text for dim in DIMENSIONS}

    chapters: dict[str, str] = {}

    for dim, keywords in _CHAPTER_KEYWORDS.items():
        canonical = dim if dim in DIMENSIONS else "透明度与质地"
        start_idx = None
        end_idx = None

        for pos, (line_num, heading) in enumerate(h2_indices):
            if any(kw in heading for kw in keywords):
                start_idx = line_num
                # Find next major heading at same or higher level
                for next_pos in range(pos + 1, len(h2_indices)):
                    next_line_num, next_heading = h2_indices[next_pos]
                    # Check if this is a new major section (not a subsection)
                    if not any(
                        kw in next_heading
                        for kw in keywords
                    ):
                        # Verify it's a different dimension's heading
                        is_other_dim = False
                        for other_dim, other_kws in _CHAPTER_KEYWORDS.items():
                            if other_dim != dim and any(
                                kw in next_heading for kw in other_kws
                            ):
                                is_other_dim = True
                                break
                        if is_other_dim:
                            end_idx = next_line_num
                            break
                break

        if start_idx is not None:
            chunk = lines[start_idx : end_idx] if end_idx else lines[start_idx:]
            chapters[canonical] = "\n".join(chunk)

    # Fallback: if a dimension wasn't found, use full report
    for dim in DIMENSIONS:
        if dim not in chapters:
            logger.warning("Could not find chapter for %s, using full report", dim)
            chapters[dim] = report_text

    return chapters


# ---------------------------------------------------------------------------
# Core extraction
# ---------------------------------------------------------------------------


def _file_hash(path: Path) -> str:
    """Return SHA-256 hex digest of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract_single_report(
    report_path: Path,
    model_id: str | None = None,
) -> ReportExtraction:
    """Extract all design elements from one report via chapter-level LLM calls."""
    report_text = report_path.read_text(encoding="utf-8")
    category = _infer_category(report_path.name)
    chapters = _split_report_into_chapters(report_text)

    model = _build_model(model_id, temperature=0.0)

    persona_list = "\n".join(
        f"   - {p.name}: {p.description}" for p in PERSONA_CATALOG
    )

    all_elements: list[MaterialElement] = []

    for dim, content in chapters.items():
        logger.info(
            "  Extracting %s from %s (%d chars)...",
            dim,
            report_path.name,
            len(content),
        )

        structured_model = model.with_structured_output(ChapterExtraction)

        prompt = _EXTRACTION_PROMPT.format(
            dimension=dim,
            personas=persona_list,
            content=content,
        )

        result: ChapterExtraction = structured_model.invoke(
            [HumanMessage(content=prompt)]
        )

        # Post-process: set report-level fields and generate IDs
        for elem in result.elements:
            elem.dimension = dim  # Normalize
            elem.source_report = report_path.name
            elem.product_category = category
            elem.id = make_element_id(
                category, dim, elem.name, elem.source_section
            )

        logger.info("    → %d elements extracted", len(result.elements))
        all_elements.extend(result.elements)

    return ReportExtraction(
        source_report=report_path.name,
        product_category=category,
        extraction_date=date.today().isoformat(),
        file_hash=_file_hash(report_path),
        elements=all_elements,
    )


# ---------------------------------------------------------------------------
# Batch extraction with incremental logic
# ---------------------------------------------------------------------------


def extract_all_reports(
    reports_dir: Path,
    output_dir: Path,
    force: bool = False,
    model_id: str | None = None,
) -> list[ReportExtraction]:
    """Extract all reports, skipping already-processed ones unless forced.

    Returns list of all ReportExtraction objects (from cache or fresh).
    """
    cache_dir = output_dir / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Load existing index
    index_path = output_dir / "index.json"
    index = IndexMetadata.model_validate_json(index_path.read_text())

    # Build hash map from existing processed reports
    processed: dict[str, ProcessedReport] = {
        pr.filename: pr for pr in index.processed_reports
    }

    report_files = sorted(reports_dir.glob("*.md"))
    if not report_files:
        logger.warning("No .md files found in %s", reports_dir)
        return []

    all_extractions: list[ReportExtraction] = []

    for report_path in report_files:
        current_hash = _file_hash(report_path)
        cached = processed.get(report_path.name)
        cache_path = cache_dir / f"{report_path.stem}.json"

        # Skip if cached and hash matches
        if (
            not force
            and cached
            and cached.file_hash == current_hash
            and cache_path.exists()
        ):
            logger.info("Skipping %s (unchanged)", report_path.name)
            extraction = ReportExtraction.model_validate_json(
                cache_path.read_text()
            )
            all_extractions.append(extraction)
            continue

        logger.info("Extracting %s ...", report_path.name)
        extraction = extract_single_report(report_path, model_id)

        # Cache the extraction
        cache_path.write_text(
            json.dumps(extraction.model_dump(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        all_extractions.append(extraction)

    return all_extractions


# ---------------------------------------------------------------------------
# Build dimension files
# ---------------------------------------------------------------------------


def build_dimension_files(
    extractions: list[ReportExtraction],
    output_dir: Path,
) -> dict[str, int]:
    """Split all elements by dimension, group by maturity, write JSON files.

    Returns a dict of dimension -> element count.
    """
    # Collect all elements
    all_elements: list[MaterialElement] = []
    for ext in extractions:
        all_elements.extend(ext.elements)

    counts: dict[str, int] = {}

    for dim in DIMENSIONS:
        dim_elements = [e for e in all_elements if e.dimension == dim]
        counts[dim] = len(dim_elements)

        dim_file = DimensionFile(
            dimension=dim,
            dimension_en=DIMENSION_EN[dim],
            last_updated=datetime.now().isoformat(timespec="seconds"),
        )

        for mat in MATURITY_LEVELS:
            group = [e for e in dim_elements if e.maturity == mat]
            setattr(dim_file, mat, group)

        out_path = output_dir / f"{DIMENSION_EN[dim]}.json"
        out_path.write_text(
            json.dumps(dim_file.model_dump(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("Wrote %s: %d elements", out_path.name, len(dim_elements))

    return counts


# ---------------------------------------------------------------------------
# Build personas file
# ---------------------------------------------------------------------------


def build_personas_file(
    extractions: list[ReportExtraction],
    output_dir: Path,
) -> None:
    """Generate personas.json with the persona catalog."""
    catalog = PersonaCatalog(
        last_updated=datetime.now().isoformat(timespec="seconds"),
        personas=list(PERSONA_CATALOG),
    )

    out_path = output_dir / "personas.json"
    out_path.write_text(
        json.dumps(catalog.model_dump(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("Wrote %s: %d personas", out_path.name, len(catalog.personas))


# ---------------------------------------------------------------------------
# Update index
# ---------------------------------------------------------------------------


def update_index(
    extractions: list[ReportExtraction],
    output_dir: Path,
    dim_counts: dict[str, int],
) -> None:
    """Write/update index.json with processing metadata."""
    reports = []
    total = 0
    for ext in extractions:
        count = len(ext.elements)
        total += count
        reports.append(
            ProcessedReport(
                filename=ext.source_report,
                product_category=ext.product_category,
                extraction_date=ext.extraction_date,
                file_hash=ext.file_hash,
                element_count=count,
                cache_path=f".cache/{Path(ext.source_report).stem}.json",
            )
        )

    index = IndexMetadata(
        last_updated=datetime.now().isoformat(timespec="seconds"),
        total_elements=total,
        color_count=dim_counts.get("颜色", 0),
        decoration_count=dim_counts.get("装饰物", 0),
        texture_count=dim_counts.get("透明度与质地", 0),
        processed_reports=reports,
    )

    out_path = output_dir / "index.json"
    out_path.write_text(
        json.dumps(index.model_dump(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info(
        "Updated index.json: %d total elements from %d reports",
        total,
        len(reports),
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Extract structured material library from trend reports.",
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=_PROJECT_ROOT / "reports",
        help="Directory containing Markdown trend reports",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_PROJECT_ROOT / "material_library",
        help="Output directory for material library JSON files",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-extraction of all reports",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Override LLM model ID (e.g. azure_openai:gpt-4o-2024-11-20)",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Ensure index.json exists
    index_path = args.output_dir / "index.json"
    if not index_path.exists():
        index_path.write_text(
            json.dumps(IndexMetadata(last_updated="").model_dump(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    logger.info("=== Material Library Extraction ===")
    logger.info("Reports: %s", args.reports_dir)
    logger.info("Output:  %s", args.output_dir)
    logger.info("Force:   %s", args.force)

    # 1. Extract
    extractions = extract_all_reports(
        args.reports_dir,
        args.output_dir,
        force=args.force,
        model_id=args.model,
    )

    if not extractions:
        logger.warning("No reports to process.")
        return

    # 2. Build dimension files
    dim_counts = build_dimension_files(extractions, args.output_dir)

    # 3. Build personas file
    build_personas_file(extractions, args.output_dir)

    # 4. Update index
    update_index(extractions, args.output_dir, dim_counts)

    logger.info("=== Done ===")
    total = sum(dim_counts.values())
    logger.info("Total elements: %d", total)
    for dim, count in dim_counts.items():
        logger.info("  %s: %d", dim, count)


if __name__ == "__main__":
    main()
