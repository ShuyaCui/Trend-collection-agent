## Why

当前系统仅依赖 Tavily 作为唯一的 Web 搜索后端，搜索能力单一：Tavily 擅长快速发现相关网页并提取上下文摘要，但对于需要**深度抓取完整页面内容**或**语义级别的精准检索**的场景力不从心。企业级研究任务往往需要多层次的信息获取策略——先广泛发现、再深入抓取、再语义精筛——单一工具无法覆盖全部需求。

通过引入 Exa（语义检索）和 Firecrawl（深度抓取与结构化），形成三工具互补的搜索组合，显著提升研究深度和信息质量。

## What Changes

- **新增 Exa 搜索工具**：基于 Exa API 实现语义检索工具（`exa_search`），支持 neural / keyword / auto 搜索模式，返回语义最相关的结果。
- **新增 Firecrawl 抓取工具**：基于 Firecrawl API 实现深度抓取工具（`firecrawl_scrape`），对指定 URL 进行完整页面抓取、HTML 清洗、Markdown 结构化输出。
- **重构搜索工具注册机制**：将工具列表从硬编码改为可配置的工具注册表，research agent 根据配置加载可用工具组合。
- **更新 research agent prompt**：在提示词中说明三个工具的定位和使用策略，引导 LLM 在不同场景选择合适工具。
- **新增环境变量**：`EXA_API_KEY`、`FIRECRAWL_API_KEY`。
- **更新依赖**：在 `pyproject.toml` 中添加 `exa-py` 和 `firecrawl-py` 依赖。

## Non-Goals

- 不替换 Tavily：Tavily 仍是主要的广度搜索工具，Exa 和 Firecrawl 是补充而非替代。
- 不修改 supervisor / scoping / report 阶段逻辑：变更仅限于搜索工具层和 research agent 工具绑定。
- 不引入工具自动选择 / 路由框架：由 LLM 根据 prompt 自行判断使用哪个工具，不新增编程式路由。
- 不实现 Firecrawl 的批量爬取（crawl）或站点地图功能：仅实现单页抓取（scrape）。

## Capabilities

### New Capabilities

- `exa-search`: Exa 语义搜索工具集成——实现 `exa_search` tool，支持 neural/keyword/auto 模式、内容摘要提取、日期过滤等。
- `firecrawl-scrape`: Firecrawl 深度抓取工具集成——实现 `firecrawl_scrape` tool，支持 URL 页面抓取、HTML→Markdown 清洗、结构化内容提取。
- `search-tool-registry`: 搜索工具注册与配置机制——将工具组合从硬编码改为可配置，支持按环境变量或配置启用/禁用各搜索工具。

### Modified Capabilities

_无现有 spec 级别的需求变更。工具扩展属于新增能力，不改变已有 capability 的对外行为。_

## Impact

- **代码影响**：
  - `notebooks/2_research_agent.ipynb`：新增 Exa 和 Firecrawl 工具定义单元，修改工具注册逻辑
  - `src/deep_research_from_scratch/utils.py`（由 notebook 生成）：新增 `exa_search()` 和 `firecrawl_scrape()` 函数
  - `src/deep_research_from_scratch/research_agent.py`（由 notebook 生成）：工具列表从硬编码改为注册表加载
  - `src/deep_research_from_scratch/prompts.py`（由 notebook 生成）：更新 research agent prompt
- **依赖影响**：`pyproject.toml` 新增 `exa-py`、`firecrawl-py`
- **环境变量影响**：新增 `EXA_API_KEY`（必需）、`FIRECRAWL_API_KEY`（必需）
- **API 影响**：无对外 API 变更
- **向后兼容**：若 Exa / Firecrawl API key 未设置，对应工具不注册，系统退回仅 Tavily 模式（**假设：需验证此降级策略是否可接受**）
