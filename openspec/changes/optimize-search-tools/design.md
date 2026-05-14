## Context

当前系统使用 Tavily 作为唯一 Web 搜索后端。搜索工具在 `utils.py` 中定义为 `tavily_search()` LangChain `@tool`，通过 `InjectedToolArg` 注入系统参数（`max_results`、`topic`）。研究代理在 `research_agent.py` 中硬编码 `tools = [tavily_search, think_tool]`，并通过 `model.bind_tools(tools)` 绑定到 LLM。

Tavily 的优势在于快速发现相关网页和提取摘要，但存在两个盲区：
1. **深度不够**：Tavily 返回摘要片段而非完整页面内容，对于长文章、技术文档、研究报告，关键信息可能被截断。
2. **语义精度不够**：Tavily 基于关键词匹配，对于概念性、语义性查询（如"美妆行业中反消费主义趋势的消费者心理驱动因素"），难以精准命中。

本设计引入 Exa 和 Firecrawl 形成三层搜索策略：
- **Tavily**（广度搜索）→ 发现相关网页、快速获取上下文摘要
- **Exa**（语义检索）→ 基于神经网络嵌入的语义相似度检索
- **Firecrawl**（深度抓取）→ 对关键 URL 进行完整抓取、HTML 清洗、Markdown 结构化

## Goals / Non-Goals

**Goals:**

- 在 `utils.py` 中新增 `exa_search` 和 `firecrawl_scrape` 两个 `@tool` 函数，遵循现有 `tavily_search` 的模式（`InjectedToolArg`、错误处理、格式化输出）
- 实现可配置的工具注册表，根据环境变量动态加载可用工具
- 更新 `prompts.py` 中的 research agent prompt，指导 LLM 正确选择工具
- 保持向后兼容：缺少 Exa/Firecrawl API key 时，系统自动退回 Tavily-only 模式

**Non-Goals:**

- 不修改 LangGraph StateGraph 结构（`llm_call → tool_node → compress_research` 循环不变）
- 不引入工具路由中间件或 Agent-of-Agents 架构
- 不实现 Firecrawl 的 crawl（多页爬取）或 map（站点地图发现）功能
- 不修改 supervisor、scoping、report generation 逻辑

## Decisions

### Decision 1: 工具定义模式 — 复用 `@tool` + `InjectedToolArg`

**选择**：新工具沿用 `tavily_search` 相同的 `@tool(parse_docstring=True)` + `InjectedToolArg` 模式。

**理由**：
- 与现有代码一致，降低理解成本
- `InjectedToolArg` 允许系统控制参数（如 `max_results`）而不暴露给 LLM
- LangChain 原生支持，无需自定义基础设施

**替代方案**：
- Pydantic `BaseModel` + `@tool` 装饰器：更结构化但当前工具较简单，不需要
- MCP server 封装：增加进程间通信开销，不适合 API 调用类工具

### Decision 2: 工具注册表 — 环境变量驱动的函数式注册

**选择**：在 `utils.py` 中新增 `get_available_search_tools() -> list[BaseTool]` 函数，根据环境变量检测可用 API key，返回对应工具列表。

```python
def get_available_search_tools() -> list[BaseTool]:
    tools = [tavily_search]  # Tavily 始终可用（假设 TAVILY_API_KEY 已设置）
    if os.environ.get("EXA_API_KEY"):
        tools.append(exa_search)
    if os.environ.get("FIRECRAWL_API_KEY"):
        tools.append(firecrawl_scrape)
    return tools
```

**理由**：
- 最小改动：`research_agent.py` 只需将 `tools = [tavily_search, think_tool]` 改为 `tools = get_available_search_tools() + [think_tool]`
- 运行时自适应：不同部署环境可启用不同工具集
- 无需配置文件解析

**替代方案**：
- 配置文件（YAML/JSON）：更灵活但引入额外解析逻辑，当前仅 3 个工具不需要
- 插件系统（entry_points）：过度工程化

### Decision 3: Exa 集成 — `exa_search` 工具设计

**选择**：暴露 `query`（必需）给 LLM，其余参数（`num_results`、`type`、`use_autoprompt`、`text_contents_options`）通过 `InjectedToolArg` 由系统控制。

```python
@tool(parse_docstring=True)
def exa_search(
    query: str,
    num_results: Annotated[int, InjectedToolArg] = 5,
    search_type: Annotated[Literal["neural", "keyword", "auto"], InjectedToolArg] = "auto",
) -> str:
```

**理由**：
- LLM 只需关注"搜什么"，不需要理解搜索模式差异
- `auto` 模式让 Exa 自行决定最佳检索策略
- `text.include_text = True` + `highlights` 确保返回摘要内容，减少后续抓取需求

### Decision 4: Firecrawl 集成 — `firecrawl_scrape` 工具设计

**选择**：暴露 `url`（必需）给 LLM，系统控制输出格式和清洗选项。

```python
@tool(parse_docstring=True)
def firecrawl_scrape(
    url: str,
    output_format: Annotated[Literal["markdown", "html"], InjectedToolArg] = "markdown",
) -> str:
```

**理由**：
- Firecrawl 的核心价值是将复杂网页转为干净 Markdown，与 LLM 处理能力完美匹配
- LLM 只需提供 URL（通常来自 Tavily 或 Exa 的搜索结果），不需要控制抓取参数
- 输出截断到合理长度（~10000 字符），防止超长页面消耗过多 token

### Decision 5: Prompt 策略 — 三工具使用指南

**选择**：在 `research_agent_prompt` 中增加工具选择指南章节：

```
## Available Search Tools

1. **tavily_search** — 广度搜索：发现相关网页、快速获取上下文摘要。适用于探索性查询、新闻搜索。
2. **exa_search** — 语义检索：基于语义相似度的精准搜索。适用于概念性查询、寻找特定观点或论述。
3. **firecrawl_scrape** — 深度抓取：对已知 URL 进行完整页面抓取。适用于从搜索结果中挑选关键页面深入阅读。

## 推荐工作流
1. 先用 tavily_search 广泛搜索，发现相关资源
2. 对搜索结果中特别重要的页面，用 firecrawl_scrape 获取完整内容
3. 用 exa_search 做语义补充，查找 tavily 可能遗漏的相关内容
```

**理由**：
- LLM 擅长根据明确指导选择工具，无需程序化路由
- 推荐工作流提供了清晰的使用范式，但不强制顺序

### Decision 6: 图片收集 — Exa 和 Firecrawl 的图片处理

**选择**：初期不从 Exa/Firecrawl 提取图片，图片收集仍由 Tavily 负责。

**理由**：
- Tavily 已有成熟的 `include_images` + `ImageResult` 流程
- Exa 返回的图片元数据较少，Firecrawl 返回的是 Markdown 内嵌图片（需解析）
- 图片提取可作为后续增强，不阻塞 MVP

## Risks / Trade-offs

| Risk | Impact | Mitigation |
|------|--------|------------|
| Exa/Firecrawl API 延迟增加总研究时间 | 中 | 工具调用是串行的（LLM 决策循环），但每次调用独立；可通过 prompt 限制总搜索次数控制 |
| LLM 不擅长选择正确工具 | 中 | 通过 prompt 明确工具定位和使用场景；`think_tool` 鼓励工具选择前的推理 |
| Firecrawl 返回内容过长导致 token 超限 | 高 | 截断输出到 ~10000 字符；后续可引入摘要压缩 |
| API key 管理复杂度增加 | 低 | 环境变量驱动的优雅降级——缺 key 则不加载对应工具 |
| Exa 免费额度有限 | 低 | `num_results` 默认 5，搜索次数受 prompt 控制（总搜索上限 5-6 次） |

## Integration Points

- **`utils.py`**：新增 `exa_search()`、`firecrawl_scrape()`、`get_available_search_tools()`
- **`research_agent.py`**：`tools = get_available_search_tools() + [think_tool]` 替换硬编码
- **`prompts.py`**：`research_agent_prompt` 增加三工具使用指南
- **`pyproject.toml`**：新增 `exa-py`、`firecrawl-py` 依赖
- **`tech-stack.md`**：更新搜索层技术栈说明

## Open Questions

1. **搜索次数上限**：当前 prompt 限制 2-5 次搜索。三工具后是否需要调高上限（如 6-8 次）？需要通过实际测试确定。
2. **Firecrawl 内容截断策略**：固定字符截断 vs. 按段落截断 vs. LLM 摘要——MVP 先用固定截断，后续可优化。
3. **Exa `search_type` 默认值**：`auto` vs. `neural` —— 目前选择 `auto` 让 Exa 自行决策，但如果发现 `neural` 在研究场景下效果更好，可调整。
