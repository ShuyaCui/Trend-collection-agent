"""Extract structured material library from trend reports.

Reads Markdown trend reports from ``reports/``, extracts design elements
(颜色, 装饰物, 透明度与质地, 风格) via LLM structured output, and writes
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
# File lives at src/material-library-extraction/, so go up 3 levels.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from langchain.chat_models import init_chat_model  # noqa: E402
from langchain_core.messages import HumanMessage  # noqa: E402
from material_schema import (  # noqa: E402
    DIMENSION_EN,
    DIMENSIONS,
    EXTRACTION_SCHEMA_VERSION,
    MATURITY_LEVELS,
    STYLE_CATALOG,
    ChapterExtraction,
    DimensionFile,
    IndexMetadata,
    MaterialElement,
    ProcessedReport,
    ReportExtraction,
    ThreeDimExtraction,
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


def _infer_category(report_path: Path) -> str:
    """Infer product category from report path or content."""
    for keyword, category in _CATEGORY_MAP.items():
        if keyword in report_path.name:
            return category
    # Filename is generic (e.g. report.md) — scan the first 500 chars of content
    try:
        content = report_path.read_text(encoding="utf-8")[:500]
        for keyword, category in _CATEGORY_MAP.items():
            if keyword in content:
                return category
    except OSError:
        pass
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

# ---------------------------------------------------------------------------
# Extraction prompts
# ---------------------------------------------------------------------------

_THREE_DIM_EXTRACTION_PROMPT = """你是一个设计元素提取专家。你的任务是从以下趋势报告中一次性提取所有属于「颜色」「装饰物」「透明度与质地」三个维度的设计元素卡片。

## 三个维度的定义（互斥）

- **颜色**：色相、色调、色彩语言（如"琥珀金""植物绿""低饱和香氛色"）。主要信号是颜色本身，即使该颜色的产品恰好是透明的。
- **装饰物**：液体中或表面的可见附加元素（如"微囊""奶盖""珠光颗粒""油珠悬浮""盐晶""花瓣"）。
- **透明度与质地**：通透性 + 黏度 + 流动性 + 光泽 + 表面状态（如"高折光水感""凝胶感""丝缎流动""奶霜质地"）。主要信号是物质的物理形态，而非颜色。

### 维度分配规则（遇到重叠时必须遵守）

1. 一个设计元素只能归属于**唯一一个维度**，禁止将同一概念分配到多个维度。
2. 判断主要信号：
   - 如果主要在描述"是什么颜色" → 归「颜色」
   - 如果主要在描述"有什么可见漂浮/颗粒/层次元素" → 归「装饰物」
   - 如果主要在描述"质感如何、透不透、稠不稠、流不流动" → 归「透明度与质地」
3. 颜色词（如"透明金色""乳白"）中，若重点是颜色 → 归「颜色」；若重点是透明度状态 → 归「透明度与质地」。

## 通用提取规则

- **粒度**: 每个独立的设计概念成为一张卡片。一个趋势段落可能包含1-3个独立元素。
- **成熟度判定**:
   - "已广泛出现""主流""当前最核心" → 主流
   - "正在上升""新兴" → 上升
   - "实验性""概念化""尚有限制" → 实验性
- **aesthetic_style** 必须从以下预定义列表中选择最接近的一个:
{styles}
- **source_heading**: 必须填写该元素对应的报告中的原始章节标题文本。
- **source_section**: 填写章节编号（如 "§4.1", "趋势3", "3.2"）。
- **signals**: 该元素向消费者传达的信息，2-5项。
- **visual_keywords**: 可扫描的视觉描述词，3-8项。
- **name_en**: 提供准确的英文翻译。
- **typical_use**: 典型的产品/使用场景。

## 报告内容

{content}

## 输出要求

提取报告中所有独立的设计元素，不要遗漏任何趋势项。
每张卡片的 dimension 字段必须精确填写「颜色」「装饰物」或「透明度与质地」之一。
严禁将同一概念重复出现在不同维度中。
"""

_STYLE_EXTRACTION_PROMPT = """你是一个审美风格分析专家。你的任务是从以下趋势报告中识别并提取「风格」维度的元素卡片。

## 风格维度说明

风格元素代表报告中出现的整体审美主题（aesthetic style）。每个风格元素综合描述一种跨越颜色、装饰物、质地的整体审美方向。

## 预定义风格列表（必须从中选择）

{styles}

## 提取规则

1. **识别报告中实际出现的风格**: 从预定义列表中找出在报告内容中有具体体现的风格（有品牌案例或产品支撑的才算）。

2. **粒度**: 每个有充分证据支撑的风格成为一张卡片。不要生造无证据的风格。

3. **成熟度判定**:
   - 多个品牌已广泛采用 → 主流
   - 少数品牌开始采用，趋势上升 → 上升
   - 仅有概念验证或极少数案例 → 实验性

4. **aesthetic_style**: 风格元素的 aesthetic_style 字段填写该元素自身的名称（如元素名为"科技净澈"则 aesthetic_style 也填"科技净澈"）。

5. **visual_keywords**: 描述该风格的跨维度视觉词（颜色+装饰+质地），3-8项。

6. **signals**: 该风格向消费者传达的品牌/产品信号，2-5项。

7. **source_section** / **source_heading**: 填写报告中最能代表该风格的章节编号和标题。

8. **name_en**: 提供准确的英文翻译。

9. **typical_use**: 典型的产品品类或使用场景。

## 报告内容

{content}

## 输出要求

仅提取报告中有实质性内容支撑的风格，不要强行填满全部6个。
每个风格卡片的 dimension 字段必须填写「风格」。
"""


# ---------------------------------------------------------------------------
# Core extraction
# ---------------------------------------------------------------------------


def _file_hash(path: Path) -> str:
    """Return SHA-256 hex digest of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _call_with_retry(structured_model, messages, max_attempts: int = 2):
    """Invoke a structured model with simple retry on failure."""
    last_exc = None
    for attempt in range(1, max_attempts + 1):
        try:
            return structured_model.invoke(messages)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning("LLM call failed (attempt %d/%d): %s", attempt, max_attempts, exc)
    raise RuntimeError(f"LLM call failed after {max_attempts} attempts") from last_exc


def _warn_duplicates(elements: list[MaterialElement], source_label: str) -> None:
    """Log a warning for any element names that appear in more than one dimension."""
    from collections import defaultdict

    dim_by_name: dict[str, list[str]] = defaultdict(list)
    for elem in elements:
        dim_by_name[elem.name].append(elem.dimension)

    for name, dims in dim_by_name.items():
        if len(dims) > 1:
            logger.warning(
                "Duplicate element '%s' in %s across dimensions: %s",
                name,
                source_label,
                ", ".join(dims),
            )


def extract_single_report(
    report_path: Path,
    model_id: str | None = None,
    report_id: str | None = None,
) -> ReportExtraction:
    """Extract all design elements from one report via two LLM passes.

    Pass 1: Single call for 颜色, 装饰物, and 透明度与质地 — each element
    self-declares its primary dimension, eliminating cross-dimension duplication.
    Pass 2: Separate call for 风格, preserving its aesthetic_style=name invariant.
    """
    report_text = report_path.read_text(encoding="utf-8")
    category = _infer_category(report_path)
    if report_id:
        source_label = report_id
    else:
        parent = report_path.parent
        source_label = (
            f"{parent.name}/{report_path.name}"
            if len(parent.name) == 36 and parent.name.count("-") == 4
            else report_path.name
        )

    model = _build_model(model_id, temperature=0.0)
    style_list = "\n".join(
        f"   - {name}: {desc}" for name, desc in STYLE_CATALOG.items()
    )

    all_elements: list[MaterialElement] = []

    # --- Pass 1: 颜色 + 装饰物 + 透明度与质地 ---
    logger.info(
        "  Pass 1 (颜色/装饰物/质地) from %s (%d chars)...",
        source_label,
        len(report_text),
    )
    three_dim_model = model.with_structured_output(ThreeDimExtraction)
    prompt1 = _THREE_DIM_EXTRACTION_PROMPT.format(
        styles=style_list, content=report_text
    )
    result1: ThreeDimExtraction = _call_with_retry(
        three_dim_model, [HumanMessage(content=prompt1)]
    )
    # Validate: elements should only use the three non-style dimensions
    non_style_dims = {"颜色", "装饰物", "透明度与质地"}
    for elem in result1.elements:
        if elem.dimension not in non_style_dims:
            logger.warning(
                "Element '%s' has unexpected dimension '%s' in pass 1; skipping",
                elem.name,
                elem.dimension,
            )
            continue
        elem.source_report = source_label
        elem.product_category = category
        elem.id = make_element_id(category, elem.dimension, elem.name, elem.source_section)
        all_elements.append(elem)
    logger.info("    → %d elements (pass 1)", len(result1.elements))

    # Sanity check: warn if suspiciously few elements for a non-trivial report
    min_expected = 3
    if len(result1.elements) < min_expected and len(report_text) > 1000:
        logger.warning(
            "Only %d elements extracted from a %d-char report — possible LLM output issue",
            len(result1.elements),
            len(report_text),
        )

    # --- Pass 2: 风格 ---
    logger.info("  Pass 2 (风格) from %s ...", source_label)
    style_model = model.with_structured_output(ChapterExtraction)
    prompt2 = _STYLE_EXTRACTION_PROMPT.format(styles=style_list, content=report_text)
    result2: ChapterExtraction = _call_with_retry(
        style_model, [HumanMessage(content=prompt2)]
    )
    for elem in result2.elements:
        elem.dimension = "风格"
        elem.source_report = source_label
        elem.product_category = category
        elem.id = make_element_id(category, "风格", elem.name, elem.source_section)
        all_elements.append(elem)
    logger.info("    → %d elements (pass 2)", len(result2.elements))

    _warn_duplicates(all_elements, source_label)

    return ReportExtraction(
        source_report=source_label,
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

    # Support both flat layout (*.md directly in dir) and nested layout
    # ({uuid}/report.md).  Nested takes precedence when present.
    report_files = sorted(reports_dir.glob("*/report.md"))
    if not report_files:
        report_files = sorted(reports_dir.glob("*.md"))
    if not report_files:
        logger.warning("No .md files found in %s", reports_dir)
        return []

    all_extractions: list[ReportExtraction] = []

    for report_path in report_files:
        # Use a unique identifier that survives the UUID directory layout.
        # For nested layout: "<uuid>/report.md"; for flat: "report_name.md".
        report_id = (
            f"{report_path.parent.name}/{report_path.name}"
            if report_path.parent != reports_dir
            else report_path.name
        )
        current_hash = _file_hash(report_path)
        cached = processed.get(report_id)
        # Cache filename: use UUID (parent dir name) to avoid collisions when
        # every file is named report.md.
        cache_key = (
            report_path.parent.name
            if report_path.parent != reports_dir
            else report_path.stem
        )
        cache_path = cache_dir / f"{cache_key}.json"

        # Skip if cached, hash matches, AND schema version is current
        if (
            not force
            and cached
            and cached.file_hash == current_hash
            and cache_path.exists()
        ):
            extraction = ReportExtraction.model_validate_json(
                cache_path.read_text()
            )
            if extraction.schema_version != EXTRACTION_SCHEMA_VERSION:
                logger.info(
                    "Cache schema version mismatch for %s (cache=%d, current=%d) — re-extracting",
                    report_id,
                    extraction.schema_version,
                    EXTRACTION_SCHEMA_VERSION,
                )
            else:
                logger.info("Skipping %s (unchanged, schema v%d)", report_id, EXTRACTION_SCHEMA_VERSION)
                all_extractions.append(extraction)
                continue

        logger.info("Extracting %s ...", report_id)
        extraction = extract_single_report(report_path, model_id, report_id=report_id)

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
        # source_report may be "uuid/report.md" (nested) or "name.md" (flat).
        # Derive the cache filename the same way extract_all_reports does.
        src = Path(ext.source_report)
        cache_key = src.parent.name if src.parent != Path(".") else src.stem
        reports.append(
            ProcessedReport(
                filename=ext.source_report,
                product_category=ext.product_category,
                extraction_date=ext.extraction_date,
                file_hash=ext.file_hash,
                element_count=count,
                cache_path=f".cache/{cache_key}.json",
            )
        )

    index = IndexMetadata(
        last_updated=datetime.now().isoformat(timespec="seconds"),
        total_elements=total,
        color_count=dim_counts.get("颜色", 0),
        decoration_count=dim_counts.get("装饰物", 0),
        texture_count=dim_counts.get("透明度与质地", 0),
        style_count=dim_counts.get("风格", 0),
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

    # 3. Update index
    update_index(extractions, args.output_dir, dim_counts)

    logger.info("=== Done ===")
    total = sum(dim_counts.values())
    logger.info("Total elements: %d", total)
    for dim, count in dim_counts.items():
        logger.info("  %s: %d", dim, count)


if __name__ == "__main__":
    main()
