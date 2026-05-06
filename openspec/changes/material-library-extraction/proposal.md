## Why

现有 `reports/` 目录包含 3 份完整的趋势报告（饮料、洗发水、面部精华），每份约 800-900 行叙事文本。这些报告蕴含丰富的设计元素（颜色、装饰物、透明度+质地），但以散文形式呈现，无法被下游 AI 直接消费来生成产品设计方案。产品经理需要一个结构化的「素材库」，将散文拆解为可挑选、可组合的元素卡片，供另一个 AI 系统读取并生成设计提案。

## What Changes

- **新增 LLM 提取脚本**：读取 `reports/*.md`，通过 LLM 将叙事文本拆解为结构化 JSON 元素卡片
- **新增 `material_library/` 目录结构**：存放每份报告的提取结果（per-report JSON）和跨品类汇总索引（cross-reference JSON）
- **定义标准化元素卡片 Schema**：覆盖颜色、装饰物、透明度+质地三个维度，包含 aesthetic persona 标签支持组合推理
- **增量更新机制**：新报告加入 `reports/` 后，只提取新文件并重建跨品类索引（幂等）

## Non-goals

- 不修改现有 deep research agent 的 Scope/Research/Write pipeline
- 不修改现有 `trend_knowledge/dimensions.json` 或 trend skill 功能
- 不构建前端可视化界面
- 不在本阶段实现下游 AI 的「设计方案生成」功能（只提供素材库供其消费）
- 不处理非 Markdown 格式的报告

## Capabilities

### New Capabilities
- `material-extraction`: 从趋势报告中提取结构化设计元素卡片的 LLM pipeline，包含提取 prompt、JSON schema 定义、增量处理逻辑
- `material-library-schema`: 素材库的数据模型定义（元素卡片 schema、aesthetic persona 体系、cross-reference 索引结构）

### Modified Capabilities
<!-- 无现有 spec 需要修改 -->

## Impact

- **新文件**：`material_library/` 目录（index.json, per-report JSONs, cross_reference.json）、提取脚本
- **依赖**：复用现有 Azure OpenAI LLM 调用模式（`init_chat_model` + `GenAIToken`）
- **不影响**：现有 notebooks、src/ 源文件、agent pipeline、trend_knowledge/
