## Why

当前 material 提取对每份报告整体发送全文给 LLM，导致 LLM 粒度压缩严重（每维度只提取 1 条素材，远低于报告实际趋势数量）。按章节截断后分别提取，能让 LLM 聚焦每个趋势段落，显著提升召回完整度。

## What Changes

- **新增** 报告章节切分器：将一篇 Markdown 报告按 H2/H3 标题切成多个 chunk，每个 chunk 对应报告中一个趋势段落
- **修改** Pass 1 提取逻辑：对每个 chunk 独立调用 `_THREE_DIM_EXTRACTION_PROMPT`，而非对全文调用一次
- **修改** Pass 2（风格）提取逻辑：风格跨越整篇报告，保持全文一次提取
- **新增** chunk 级别的去重合并：多个 chunk 产出的元素在合并到 dimension file 之前，先执行现有的 `_deduplicate_elements()`（已按 name 合并）

> 假设：报告结构以 H2/H3 标题划分趋势，章节数通常为 5-20 个。若章节数少于 2，降级为现有全文提取。

## Capabilities

### New Capabilities

- `report-chunker`: 将 Markdown 趋势报告按 H2/H3 heading 切分为若干趋势 chunk，每个 chunk 保留完整的上下文（标题 + 正文）

### Modified Capabilities

- （无 spec 级别行为变更；`_deduplicate_elements()` 逻辑不变，只是调用时机提前到 chunk 合并阶段）

## Impact

- 受影响文件：`src/material-library-extraction/extract_material_library.py`
- LLM 调用次数：从每报告 2 次 → 每报告 `(N_chunks + 1)` 次（N_chunks 为章节数，风格保持 1 次）
- 提取质量：预期每份报告素材数量从 ~3 条 → ~10-30 条（与报告章节数对齐）
- 缓存兼容性：需将 `EXTRACTION_SCHEMA_VERSION` 升级到 3，自动废弃旧 v2 缓存
- 无 breaking API 变更；`ReportExtraction`、`MaterialElement` schema 不变
