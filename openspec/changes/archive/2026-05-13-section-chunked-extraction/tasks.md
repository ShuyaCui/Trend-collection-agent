## 1. Schema 版本升级

- [x] 1.1 在 `material_schema.py` 中将 `EXTRACTION_SCHEMA_VERSION` 从 `2` 改为 `3`，触发旧缓存自动失效
- [x] 1.2 验证：`python -c "from material_schema import EXTRACTION_SCHEMA_VERSION; assert EXTRACTION_SCHEMA_VERSION == 3"`

## 2. 实现 `_chunk_report()` 函数

- [x] 2.1 在 `extract_material_library.py` 中实现 `_chunk_report(report_text: str, min_chars: int = 200) -> list[str]`：按 H2/H3 标题切分；若 chunk 数 < 2 则尝试段落切分（空行分隔）；若段落切分后仍 < 2 chunk，返回 `[report_text]`（最终降级）；过滤 < min_chars 的短 chunk
- [x] 2.2 实现 `_build_breadcrumb(headings: list[str]) -> str`：将从报告根到当前 chunk 的祖先标题拼成面包屑字符串（如 `## 趋势总览 > ### 1. 低饱和香氛色`），替代原始 preamble 方案；无祖先时返回空字符串
- [x] 2.3 单元测试（无 LLM）：构造包含 3 个 H2 章节的模拟报告，验证 `_chunk_report()` 返回 3 个元素，且每个元素以对应标题开头

## 3. 修改 Pass 1 为逐 chunk 提取

- [x] 3.1 在 `extract_single_report()` 中，将 Pass 1 从单次全文调用改为 `for chunk in _chunk_report(report_text)` 循环，每次调用 `_call_with_retry(three_dim_model, [HumanMessage(content=prompt)])`
- [x] 3.2 记录每个 chunk 的提取日志（chunk 序号、字数、提取元素数）
- [x] 3.3 实现 Pass 2 的 H3 切分：复用 `_chunk_report()` 的 H3 切分结果（与 Pass 1 相同粒度），对每个 H3 chunk 调用 `_STYLE_EXTRACTION_PROMPT`（含 H3B breadcrumb），汇总结果后交给 `_deduplicate_elements()`；无 H3 时降级为全文单次调用

## 4. 验证与集成测试

- [x] 4.1 对现有报告运行 dry-run（验证 chunk 数量是否合理）：导入测试通过，`_chunks_with_breadcrumbs` 在所有测试报告结构上正常工作
- [x] 4.2 确认 `ruff check src/material-library-extraction/` 通过，无新增 lint 错误

## 5. 提交

- [x] 5.1 将变更提交到 `development` 分支，commit message 说明：新增 `_chunk_report()`、Pass 1 改为 chunk 循环、schema version 升为 3
