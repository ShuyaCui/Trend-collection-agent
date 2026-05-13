## Why

设计师需要从现有素材库（material library）中检索跨品类设计元素，组合成新产品（如沐浴露）的设计方案。当前素材库有 ~150 个结构化元素（颜色/装饰/质地/风格）和 ~100 张带描述的参考图，但没有检索和组合工具。设计师只能手动翻阅 JSON 文件，无法高效地进行创意探索。

## What Changes

- **新增 Design Agent CLI 工具**：自然语言输入 → 多策略并行检索 → LLM 策展 → 按维度输出推荐元素 + 参考图
- **新增多策略检索引擎**：实现 4 种独立检索策略（直觉匹配、角色类比、跨品类迁移、趋势前沿），每种策略用不同的创意逻辑产生候选
- **新增 LLM 策展层**：从多策略候选池中，为每个维度（颜色/装饰/质地）选出最有价值的推荐
- **新增参考图匹配**：基于 `images_metadata.json` 的 description 字段，为每个推荐元素匹配 N 张参考图（默认 3 张）

## Non-goals

- 不构建 Web UI（当前仅 CLI，UI 是后续独立工作）
- 不生成设计渲染图或 moodboard 拼图
- 不新增趋势研究报告（仅使用现有素材库和图片）
- 不修改现有素材库 schema 或提取流程
- 不做 embedding / 向量数据库（Phase 1 用关键词 + LLM）

## Capabilities

### New Capabilities

- `multi-strategy-retrieval`: 多策略并行检索引擎，包含直觉匹配、角色类比、跨品类迁移、趋势前沿四种策略，每种策略独立产生候选元素
- `llm-curation`: LLM 策展层，从多策略候选池中为每个维度选出推荐，并匹配参考图
- `design-agent-cli`: CLI 入口，接受自然语言输入，调用检索和策展，格式化输出推荐结果

### Modified Capabilities

（无现有 capability 的 requirement 变更）

## Impact

- **新增文件**: `notebooks/design_agent.py`（主入口）, `src/deep_research_from_scratch/design_agent/` 下的模块文件
- **依赖**: 需要读取 `material_library/*.json` 和 `reports/*/images/images_metadata.json`
- **LLM 调用**: 查询解析 1 次 + 策展 1 次，每次查询约 2 次 LLM 调用
- **现有代码**: 不修改现有模块；复用 `Helper.py` 的 `GenAIToken` 做 Azure OpenAI 认证
