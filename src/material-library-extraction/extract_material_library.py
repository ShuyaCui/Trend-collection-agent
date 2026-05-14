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
import re
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
    "azure_openai:GPT-54-2026-03-05",
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
# Report chunking helpers
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^(#{2,3})\s+(.+)", re.MULTILINE)


def _chunk_report(report_text: str, min_chars: int = 200) -> list[str]:
    """Split a Markdown report into section chunks for focused LLM extraction.

    Strategy (in order):
    1. Split on H2/H3 headings — each chunk = heading + body until next heading.
    2. If fewer than 2 heading-chunks result, fall back to paragraph splitting
       (blank-line separated blocks).
    3. If paragraph splitting also yields fewer than 2 chunks, return the full
       report as a single-element list.

    Chunks shorter than *min_chars* (after stripping) are discarded.
    """
    lines = report_text.splitlines(keepends=True)

    # --- Step 1: heading-based split ---
    heading_positions: list[int] = []
    for i, line in enumerate(lines):
        if _HEADING_RE.match(line):
            heading_positions.append(i)

    if len(heading_positions) >= 2:
        chunks: list[str] = []
        for idx, start in enumerate(heading_positions):
            end = heading_positions[idx + 1] if idx + 1 < len(heading_positions) else len(lines)
            chunk = "".join(lines[start:end]).strip()
            if len(chunk) >= min_chars:
                chunks.append(chunk)
        if len(chunks) >= 2:
            return chunks

    # --- Step 2: paragraph-based fallback ---
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", report_text) if p.strip()]
    para_chunks = [p for p in paragraphs if len(p) >= min_chars]
    if len(para_chunks) >= 2:
        return para_chunks

    # --- Step 3: full-report degradation ---
    return [report_text]


def _build_breadcrumb(ancestor_headings: list[str]) -> str:
    """Build a heading breadcrumb string from ancestor heading lines.

    Example: ["## 一、趋势总览", "### 1. 低饱和香氛色"]
             → "## 一、趋势总览 > ### 1. 低饱和香氛色"

    Returns empty string when no ancestors are provided.
    """
    cleaned = [h.strip() for h in ancestor_headings if h.strip()]
    return " > ".join(cleaned)


def _chunks_with_breadcrumbs(report_text: str, min_chars: int = 200) -> list[tuple[str, str]]:
    """Return list of (breadcrumb, chunk_text) pairs for all chunks in a report.

    The breadcrumb for each chunk is the ordered path of ancestor H2/H3 headings
    leading to its own heading. The chunk body does NOT include the leading heading
    line (that is captured in the breadcrumb instead).
    """
    lines = report_text.splitlines(keepends=True)
    heading_positions: list[tuple[int, str, int]] = []  # (line_idx, heading_text, level)
    for i, line in enumerate(lines):
        m = _HEADING_RE.match(line)
        if m:
            level = len(m.group(1))  # 2 for ##, 3 for ###
            heading_positions.append((i, line.rstrip(), level))

    if len(heading_positions) < 2:
        # Degenerate case: no meaningful structure, return full text with no breadcrumb
        return [("", report_text)]

    results: list[tuple[str, str]] = []
    for idx, (start, heading_text, level) in enumerate(heading_positions):
        end_line = heading_positions[idx + 1][0] if idx + 1 < len(heading_positions) else len(lines)
        body = "".join(lines[start + 1 : end_line]).strip()
        if len(body) < min_chars:
            continue
        # Build breadcrumb: all ancestor headings whose level < current level,
        # keeping only the closest ancestor per level.
        ancestors: list[str] = []
        seen_levels: set[int] = set()
        for prev_line_idx, prev_heading, prev_level in reversed(heading_positions[:idx]):
            if prev_level < level and prev_level not in seen_levels:
                ancestors.insert(0, prev_heading)
                seen_levels.add(prev_level)
        breadcrumb = _build_breadcrumb(ancestors + [heading_text])
        results.append((breadcrumb, body))

    if not results:
        return [("", report_text)]
    return results


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
    """Extract all design elements from one report via section-chunked two-pass LLM extraction.

    Pass 1: Iterate over H2/H3 sections. Each section is sent individually to the
    LLM with a breadcrumb context prefix. Extracts 颜色, 装饰物, and 透明度与质地;
    each element self-declares its primary dimension to avoid cross-dimension duplication.

    Pass 2: Same per-section loop for 风格, preserving its aesthetic_style=name invariant.

    Fallback: if the report has no heading structure, falls back to paragraph splitting;
    if still fewer than 2 chunks, falls back to full-report extraction.
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
    chunks = _chunks_with_breadcrumbs(report_text)
    logger.info(
        "  Report %s: %d chars → %d section chunk(s)",
        source_label,
        len(report_text),
        len(chunks),
    )

    # --- Pass 1: 颜色 + 装饰物 + 透明度与质地 (per chunk) ---
    three_dim_model = model.with_structured_output(ThreeDimExtraction)
    non_style_dims = {"颜色", "装饰物", "透明度与质地"}
    pass1_total = 0

    for chunk_idx, (breadcrumb, chunk_body) in enumerate(chunks):
        context = f"[章节位置: {breadcrumb}]\n\n{chunk_body}" if breadcrumb else chunk_body
        prompt1 = _THREE_DIM_EXTRACTION_PROMPT.format(
            styles=style_list, content=context
        )
        logger.info(
            "  Pass 1 chunk %d/%d (%d chars, bc=%r)...",
            chunk_idx + 1,
            len(chunks),
            len(context),
            breadcrumb[:60] if breadcrumb else "",
        )
        result1: ThreeDimExtraction = _call_with_retry(
            three_dim_model, [HumanMessage(content=prompt1)]
        )
        chunk_count = 0
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
            chunk_count += 1
        logger.info("    → %d elements from chunk %d", chunk_count, chunk_idx + 1)
        pass1_total += chunk_count

    logger.info("  Pass 1 total: %d elements across %d chunks", pass1_total, len(chunks))
    if pass1_total < 3 and len(report_text) > 1000:
        logger.warning(
            "Only %d elements in pass 1 from a %d-char report — possible LLM output issue",
            pass1_total,
            len(report_text),
        )

    # --- Pass 2: 风格 (per chunk) ---
    style_model = model.with_structured_output(ChapterExtraction)
    pass2_total = 0

    for chunk_idx, (breadcrumb, chunk_body) in enumerate(chunks):
        context = f"[章节位置: {breadcrumb}]\n\n{chunk_body}" if breadcrumb else chunk_body
        prompt2 = _STYLE_EXTRACTION_PROMPT.format(
            styles=style_list, content=context
        )
        logger.info(
            "  Pass 2 chunk %d/%d (%d chars)...",
            chunk_idx + 1,
            len(chunks),
            len(context),
        )
        result2: ChapterExtraction = _call_with_retry(
            style_model, [HumanMessage(content=prompt2)]
        )
        chunk_count = 0
        for elem in result2.elements:
            elem.dimension = "风格"
            elem.source_report = source_label
            elem.product_category = category
            elem.id = make_element_id(category, "风格", elem.name, elem.source_section)
            all_elements.append(elem)
            chunk_count += 1
        logger.info("    → %d style elements from chunk %d", chunk_count, chunk_idx + 1)
        pass2_total += chunk_count

    logger.info("  Pass 2 total: %d style elements", pass2_total)

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

_MATURITY_RANK: dict[str, int] = {"主流": 0, "上升": 1, "实验性": 2}


def _merge_group(group: list[MaterialElement]) -> MaterialElement:
    """Merge a group of MaterialElements into one canonical entry.

    Rules:
    - maturity: keep the highest (主流 > 上升 > 实验性)
    - visual_keywords / signals: union, deduped, order-preserving
    - source_report: join distinct sources with " + "
    - all other fields: taken from the highest-maturity entry
    """
    if len(group) == 1:
        return group[0]

    group = sorted(group, key=lambda e: _MATURITY_RANK.get(e.maturity, 99))
    primary = group[0]

    seen_kw: set[str] = set()
    merged_kw: list[str] = []
    for e in group:
        for kw in e.visual_keywords:
            if kw not in seen_kw:
                seen_kw.add(kw)
                merged_kw.append(kw)

    seen_sig: set[str] = set()
    merged_sig: list[str] = []
    for e in group:
        for sig in e.signals:
            if sig not in seen_sig:
                seen_sig.add(sig)
                merged_sig.append(sig)

    sources = list(dict.fromkeys(e.source_report for e in group if e.source_report))
    merged_source = " + ".join(sources)

    return primary.model_copy(
        update={
            "visual_keywords": merged_kw,
            "signals": merged_sig,
            "source_report": merged_source,
        }
    )


def _deduplicate_elements(elements: list[MaterialElement]) -> list[MaterialElement]:
    """Merge elements with the same (dimension, name) across multiple reports."""
    from collections import defaultdict

    groups: dict[tuple[str, str], list[MaterialElement]] = defaultdict(list)
    for elem in elements:
        groups[(elem.dimension, elem.name)].append(elem)

    merged: list[MaterialElement] = []
    for (dim, name), group in groups.items():
        result = _merge_group(group)
        if len(group) > 1:
            logger.info(
                "Merged %d '%s' (%s) entries → maturity=%s, sources=[%s]",
                len(group),
                name,
                dim,
                result.maturity,
                result.source_report,
            )
        merged.append(result)

    return merged


def _union_find_clusters(n: int, pairs: list[tuple[int, int]]) -> list[list[int]]:
    """Group indices into clusters using Union-Find.

    Args:
        n: Total number of elements.
        pairs: Index pairs (i, j) that should be in the same cluster.

    Returns:
        List of clusters, each cluster is a sorted list of indices.
        Singletons are included as single-element lists.
    """
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        parent[find(x)] = find(y)

    for i, j in pairs:
        union(i, j)

    from collections import defaultdict

    clusters: dict[int, list[int]] = defaultdict(list)
    for idx in range(n):
        clusters[find(idx)].append(idx)
    return list(clusters.values())


def _build_embedding_model():
    """Build an AzureOpenAIEmbeddings client for TEXT-EMBEDDING-3-SMALL."""
    from langchain_openai import AzureOpenAIEmbeddings

    return AzureOpenAIEmbeddings(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        deployment="TEXT-EMBEDDING-3-SMALL",
        api_version="2024-09-01-preview",
        api_key=GenAIToken().token(),
        default_headers={
            "project-name": os.getenv("HEADERS_PROJECT_NAME"),
            "userid": os.getenv("HEADERS_USERID"),
        },
    )


def _semantic_deduplicate_elements(
    elements: list[MaterialElement],
    threshold: float = 0.7,
) -> list[MaterialElement]:
    """Merge semantically similar elements within each dimension using embeddings.

    For each dimension, batch-embeds all element ``name`` fields via
    text-embedding-3-small, computes pairwise cosine similarity, and merges
    any pair whose similarity exceeds ``threshold`` using the same rules as
    :func:`_merge_group`.  Union-Find ensures transitive groups are handled
    correctly and the result is order-independent.

    Args:
        elements: Elements after exact-name deduplication.
        threshold: Cosine similarity threshold above which two elements are merged.

    Returns:
        Elements with semantic duplicates merged.
    """
    from collections import defaultdict

    import numpy as np

    embedding_model = _build_embedding_model()

    by_dim: dict[str, list[MaterialElement]] = defaultdict(list)
    for elem in elements:
        by_dim[elem.dimension].append(elem)

    result: list[MaterialElement] = []

    for dim, dim_elems in by_dim.items():
        if len(dim_elems) <= 1:
            result.extend(dim_elems)
            continue

        names = [e.name for e in dim_elems]
        vectors = np.array(embedding_model.embed_documents(names), dtype=float)

        # Normalise rows for fast cosine similarity via dot product
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        unit_vecs = vectors / norms

        # Collect pairs above threshold (upper triangle only)
        n = len(dim_elems)
        above_threshold: list[tuple[int, int]] = []
        sim_matrix = unit_vecs @ unit_vecs.T
        for i in range(n):
            for j in range(i + 1, n):
                if sim_matrix[i, j] > threshold:
                    above_threshold.append((i, j))

        clusters = _union_find_clusters(n, above_threshold)

        for cluster in clusters:
            group = [dim_elems[idx] for idx in cluster]
            merged = _merge_group(group)
            if len(group) > 1:
                merged_names = [e.name for e in group]
                logger.info(
                    "Semantic-merged %d (%s) entries %s → '%s' maturity=%s",
                    len(group),
                    dim,
                    merged_names,
                    merged.name,
                    merged.maturity,
                )
            result.append(merged)

    return result


def build_dimension_files(
    extractions: list[ReportExtraction],
    output_dir: Path,
    semantic_dedup: bool = True,
) -> dict[str, int]:
    """Split all elements by dimension, deduplicate, group by maturity, write JSON files.

    Performs two deduplication passes:
    1. Exact-name deduplication (always).
    2. Semantic deduplication via text-embedding-3-small (when ``semantic_dedup=True``).

    Returns a dict of dimension -> element count (post-deduplication).
    """
    # Collect all elements
    all_elements: list[MaterialElement] = []
    for ext in extractions:
        all_elements.extend(ext.elements)

    # Pass 1: deduplicate exact-name matches within each dimension
    all_elements = _deduplicate_elements(all_elements)

    # Pass 2: semantic deduplication via embeddings
    if semantic_dedup:
        logger.info("Running semantic deduplication (threshold=0.7)…")
        all_elements = _semantic_deduplicate_elements(all_elements)
        logger.info("After semantic dedup: %d elements total", len(all_elements))

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
    parser.add_argument(
        "--no-semantic-dedup",
        action="store_true",
        help="Skip embedding-based semantic deduplication (exact-name dedup still runs)",
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
    logger.info("Semantic dedup: %s", not args.no_semantic_dedup)

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
    dim_counts = build_dimension_files(
        extractions,
        args.output_dir,
        semantic_dedup=not args.no_semantic_dedup,
    )

    # 3. Update index
    update_index(extractions, args.output_dir, dim_counts)

    logger.info("=== Done ===")
    total = sum(dim_counts.values())
    logger.info("Total elements: %d", total)
    for dim, count in dim_counts.items():
        logger.info("  %s: %d", dim, count)


if __name__ == "__main__":
    main()
