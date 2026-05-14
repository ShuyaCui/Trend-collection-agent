## Why

当前 `_deduplicate_elements` 仅按 `(dimension, name)` 完全匹配进行合并。实际提取结果中，语义相同的条目常以不同表述出现（如"珠光"与"珍珠光泽"、"透明感"与"透明质地"），导致材料库存在大量语义重复条目，影响下游报告质量和用量分析准确性。

## What Changes

- 在现有精确名称匹配去重之后，增加一轮基于 embedding 的语义去重步骤。
- 使用 `AzureOpenAIEmbeddings`（deployment: `TEXT-EMBEDDING-3-SMALL`）对同一维度内所有剩余条目的 `name` 字段进行批量向量化。
- 对同一维度内，所有条目对计算余弦相似度；similarity score > 0.7 的两个条目按现有合并规则合并（取 maturity 更高者为 primary，union list 字段，合并 source_report）。
- 合并采用贪心聚类（Union-Find 或单遍扫描）：将相似度超阈值的条目分入同一组，每组只保留一个代表条目。
- 新增环境变量 / 配置：无（复用现有 `AZURE_OPENAI_ENDPOINT` 和 `AZURE_OPENAI_API_VERSION` 等）。
- 新增可选 CLI 参数 `--no-semantic-dedup` 以便跳过此步骤（适合调试或离线场景）。

## Capabilities

### New Capabilities

- `semantic-dedup`: 在 `_deduplicate_elements` 后追加一个 `_semantic_deduplicate_elements` 函数，使用 text-embedding-3-small 做 embedding，并执行余弦相似度聚类合并。

### Modified Capabilities

- （无 spec 级行为变更，仅在现有去重管线后追加新阶段）

## Impact

- **文件**: `src/material-library-extraction/extract_material_library.py`（主逻辑）；对应 notebook（若存在 `%%writefile` 单元）。
- **新依赖**: `langchain-openai`（已在项目中使用，`AzureOpenAIEmbeddings` 来自此包）；`numpy`（余弦相似度计算，假设已安装，[假设]）。
- **API 调用**: 每次运行会批量调用 Azure OpenAI Embeddings API；条目数较多时会有额外延迟和 token 消耗。
- **不影响**: 现有精确名称去重逻辑、schema 定义、JSON 输出格式、其他脚本。

### Non-goals

- 不修改 LLM 提取阶段的 prompt 或 schema。
- 不对 `visual_keywords` / `signals` 字段做 embedding 去重（仅对 `name` 做）。
- 不引入持久化 embedding 缓存（超出当前范围）。
- 不更改阈值自动调优逻辑（阈值固定为 0.7）。
