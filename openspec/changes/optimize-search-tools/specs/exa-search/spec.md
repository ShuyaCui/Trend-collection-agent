## ADDED Requirements

### Requirement: Exa semantic search tool

系统 SHALL 提供 `exa_search` 工具，允许 LLM 通过 Exa API 执行语义检索。该工具接受 `query`（字符串）作为 LLM 可见参数，返回格式化的搜索结果字符串。

系统 SHALL 使用 `InjectedToolArg` 控制 `num_results`（默认 5）和 `search_type`（默认 `"auto"`，可选 `"neural"`、`"keyword"`）参数，这些参数不暴露给 LLM。

系统 SHALL 对每条结果返回标题、URL、发布日期（如有）和内容摘要/高亮片段。

#### Scenario: Basic semantic search

- **WHEN** LLM 调用 `exa_search(query="美妆行业中反消费主义趋势")`
- **THEN** 系统通过 Exa API 执行语义检索，返回最多 `num_results` 条结果，每条包含标题、URL 和内容摘要

#### Scenario: Exa API key not set

- **WHEN** 环境变量 `EXA_API_KEY` 未设置
- **THEN** `exa_search` 工具不出现在可用工具列表中，系统正常运行不报错

#### Scenario: Exa API error handling

- **WHEN** Exa API 调用失败（网络错误、速率限制、无效 key）
- **THEN** 工具返回包含错误描述的字符串（不抛出异常），LLM 可据此决定使用其他工具重试

#### Scenario: Empty results

- **WHEN** Exa 搜索返回 0 条结果
- **THEN** 工具返回明确说明"未找到相关结果"的字符串
