## Context

当前 `extract_single_report()` 每份报告只做 2 次 LLM 调用（Pass 1：全文提取颜色/装饰物/质地；Pass 2：全文提取风格）。LLM 面对整篇长报告（~8k-15k 字）时，倾向于将多个趋势段落压缩为少数几条卡片，实际测量每维度平均仅提取 1 条，远低于报告包含的趋势数量（通常 5-15 个章节）。

本 design 采用「章节切分 → 分 chunk 提取 → 合并去重」的策略，使每个 LLM 调用仅需处理 1 个章节（~500-2000 字），从根本上解决粒度压缩问题。

## Goals / Non-Goals

**Goals:**
- 将一篇报告按 H2/H3 标题切分为若干 chunk
- 对每个 chunk 独立调用 Pass 1（颜色/装饰物/质地）
- 风格（Pass 2）保持全文提取，不按 chunk 拆分（风格跨越整篇报告）
- chunk 产出的元素合并后经现有 `_deduplicate_elements()` 去重
- `EXTRACTION_SCHEMA_VERSION` 升为 3，自动废弃 v2 缓存

**Non-Goals:**
- 修改 `MaterialElement` / `ReportExtraction` / `DimensionFile` schema
- 修改去重合并逻辑（`_deduplicate_elements()` 不变）
- 修改 Pass 2（风格提取）的 prompt 或逻辑
- 支持非 Markdown 格式报告的切分
- 并行化 chunk 的 LLM 调用（单线程顺序处理即可）

## Decisions

### D1：切分粒度选 H2/H3，最小 chunk 字数设门槛

**决策**：按 H2 和 H3 标题切分，每个 chunk 包含标题及其下所有正文（直到下一个同级或更高级标题）。若某 chunk 字数 < 200 字（如目录行、总览标题），跳过不提取。

**理由**：H2/H3 是趋势报告的典型趋势段落边界；太短的 chunk 一般是导言或过渡，没有实质趋势内容。

**备选**：仅按 H2 切分 → chunk 可能仍然很长（含多个 H3）；按句子切分 → 太细，上下文丢失。

### D2：切分失败时先尝试段落切分，再降级为全文提取

**决策**：若报告中找不到 H2/H3（或切分后 chunk 数 < 2），先尝试按空行段落切分；若段落切分后 chunk 数仍 < 2，才降级为全文一次调用。

**理由**：部分报告使用纯段落分隔而非标题结构，段落切分比直接全文降级能获得更多粒度，避免 LLM 压缩问题。

### D3：Pass 2（风格）按 H3 切分提取

**决策**：风格提取按 H3 标题切分（与 Pass 1 相同粒度），每个 H3 chunk 独立调用 `_STYLE_EXTRACTION_PROMPT` 一次；提取结果汇总后经 `_deduplicate_elements()` 合并。

**理由**：H3 粒度更细，可以捕捉到每个子章节的风格特征。虽然会引入更多重复条目，但可以通过后续去重处理解决。H2 粒度仍然可能过粗，导致 LLM 在长 chunk 中压缩多个风格为一个。

**备选**：H2 切分 → 可能仍有粒度压缩；全文一次提取 → 明显压缩严重。

### D4：chunk 结果在 `extract_single_report()` 内合并，不改变返回类型

**决策**：所有 chunk 的元素在 `extract_single_report()` 内累积为一个 `list[MaterialElement]`，返回类型 `ReportExtraction` 不变。

**理由**：保持对 `extract_all_reports()` 和 `build_dimension_files()` 的零改动。

### D5：schema_version 升为 3
**决策**：`EXTRACTION_SCHEMA_VERSION = 3`，`ReportExtraction.schema_version` 默认值保持 `1`（表示"旧缓存"）。

**理由**：v2 缓存是按全文 2-pass 提取的，元素数量仍然偏少，需要废弃重提取。

## Risks / Trade-offs

- **LLM 调用次数增加**：从 2 次/报告 → `N_chunks + 1` 次（N 通常 5-15）。每次提取耗时 ~3-5 秒，整体提取时间从 ~10 秒 → ~60-90 秒/报告。可接受，因为是离线批量任务。

- **chunk 跨标题的上下文断裂**：有些报告在正文中引用前面章节的品牌案例。chunk 切分可能使 LLM 丢失该上下文。**缓解**：在每个 chunk 前拼接该 chunk 的标题面包屑层级（H3B，即从报告根到当前 H3 的完整标题路径，如 `## 一、趋势总览 > ### 1. 低饱和香氛色`），替代原始"前300字"方案。面包屑体积小，精准传递结构位置，避免截断正文内容。
- **元素数量激增后去重负担**：预期每报告素材从 ~3 条 → ~20-50 条（含 chunk 内重复）。现有 `_deduplicate_elements()` 按 `(dimension, name)` 精确匹配合并，不做语义相似度合并。语义接近但名称不同的条目仍会各自保留。这是当前版本的已知限制。

## Migration Plan

1. 升级 `EXTRACTION_SCHEMA_VERSION = 3`
2. 实现 `_chunk_report()` 函数
3. 修改 `extract_single_report()` 的 Pass 1 循环
4. 运行 `--force` 全量重提取验证（或等 schema version 自动触发）
5. 检查每份报告素材数量是否符合预期（> 5 条/维度）

## Open Questions

- 是否需要对 chunk 结果在报告级别先做一次去重，再在 `build_dimension_files()` 做跨报告去重？（当前方案：不做报告级预去重，统一在 `build_dimension_files()` 处理）
- chunk 级别的 `_warn_duplicates()` 是否有意义？（暂时不加，跨 chunk 重复属于正常，交给后续去重处理）
