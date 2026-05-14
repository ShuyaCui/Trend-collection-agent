## ADDED Requirements

### Requirement: Dynamic search tool registration

系统 SHALL 提供 `get_available_search_tools()` 函数，根据环境变量中可用的 API key 动态返回搜索工具列表。

`tavily_search` SHALL 始终包含在返回列表中（假设 `TAVILY_API_KEY` 已设置）。

当 `EXA_API_KEY` 环境变量已设置时，返回列表 SHALL 包含 `exa_search`。

当 `FIRECRAWL_API_KEY` 环境变量已设置时，返回列表 SHALL 包含 `firecrawl_scrape`。

#### Scenario: All API keys available

- **WHEN** `TAVILY_API_KEY`、`EXA_API_KEY`、`FIRECRAWL_API_KEY` 均已设置
- **THEN** `get_available_search_tools()` 返回 `[tavily_search, exa_search, firecrawl_scrape]`

#### Scenario: Only Tavily available

- **WHEN** 仅 `TAVILY_API_KEY` 已设置，`EXA_API_KEY` 和 `FIRECRAWL_API_KEY` 未设置
- **THEN** `get_available_search_tools()` 返回 `[tavily_search]`，系统行为与当前完全一致

#### Scenario: Partial availability

- **WHEN** `TAVILY_API_KEY` 和 `EXA_API_KEY` 已设置，`FIRECRAWL_API_KEY` 未设置
- **THEN** `get_available_search_tools()` 返回 `[tavily_search, exa_search]`

### Requirement: Research agent tool binding uses registry

`research_agent.py` 中的工具列表 SHALL 通过 `get_available_search_tools()` 动态获取，而非硬编码。

工具绑定代码 SHALL 为 `tools = get_available_search_tools() + [think_tool]`。

#### Scenario: Agent uses registered tools

- **WHEN** research agent 初始化时
- **THEN** 通过 `get_available_search_tools()` 获取搜索工具列表，并与 `think_tool` 合并后绑定到 LLM

### Requirement: Research agent prompt reflects available tools

`prompts.py` 中的 `research_agent_prompt` SHALL 包含三工具使用指南，说明每个工具的定位和推荐使用场景。

prompt SHALL 包含推荐工作流：先用 `tavily_search` 广度搜索 → 对关键页面用 `firecrawl_scrape` 深度抓取 → 用 `exa_search` 语义补充。

#### Scenario: Prompt includes tool guide

- **WHEN** research agent 使用更新后的 prompt
- **THEN** prompt 中包含每个搜索工具的名称、用途说明和推荐工作流描述
