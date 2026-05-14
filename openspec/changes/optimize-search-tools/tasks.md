## 1. 依赖与环境配置

- [ ] 1.1 在 `pyproject.toml` 中添加 `exa-py` 和 `firecrawl-py` 依赖，运行 `uv sync` 安装
- [ ] 1.2 在 `openspec/specs/tech-stack.md` 的 Search 行更新为多工具组合说明，新增 `EXA_API_KEY` 和 `FIRECRAWL_API_KEY` 环境变量文档

## 2. Exa 搜索工具实现

- [ ] 2.1 在 `notebooks/2_research_agent.ipynb` 的 `%%writefile utils.py` 单元中新增 `exa_search()` 函数：使用 `@tool(parse_docstring=True)` 装饰器，`query` 为 LLM 可见参数，`num_results` 和 `search_type` 使用 `InjectedToolArg`，返回格式化搜索结果字符串
- [ ] 2.2 实现 `exa_search` 的错误处理：捕获 API 异常（网络错误、速率限制、无效 key），返回错误描述字符串而非抛出异常；空结果时返回"未找到相关结果"
- [ ] 2.3 运行 notebook 单元生成 `src/deep_research_from_scratch/utils.py`，用 `ruff check` 验证无 lint 错误

## 3. Firecrawl 抓取工具实现

- [ ] 3.1 在 `notebooks/2_research_agent.ipynb` 的 `%%writefile utils.py` 单元中新增 `firecrawl_scrape()` 函数：使用 `@tool(parse_docstring=True)` 装饰器，`url` 为 LLM 可见参数，`output_format` 使用 `InjectedToolArg`，返回清洗后的 Markdown 内容
- [ ] 3.2 实现内容截断逻辑：超过 10000 字符时截断并附加 `[内容已截断]` 标记
- [ ] 3.3 实现 `firecrawl_scrape` 的错误处理：捕获 API 异常和 URL 不可达情况，返回错误描述字符串
- [ ] 3.4 运行 notebook 单元生成源码，用 `ruff check` 验证

## 4. 工具注册表实现

- [ ] 4.1 在 `notebooks/2_research_agent.ipynb` 的 `%%writefile utils.py` 单元中新增 `get_available_search_tools()` 函数：始终包含 `tavily_search`，根据 `EXA_API_KEY` 和 `FIRECRAWL_API_KEY` 环境变量有条件地添加 `exa_search` 和 `firecrawl_scrape`
- [ ] 4.2 在 `notebooks/2_research_agent.ipynb` 的 `%%writefile research_agent.py` 单元中将 `tools = [tavily_search, think_tool]` 替换为 `tools = get_available_search_tools() + [think_tool]`，更新相应 import

## 5. Prompt 更新

- [ ] 5.1 在 `notebooks/2_research_agent.ipynb`（或包含 prompts 的 notebook）的 `%%writefile prompts.py` 单元中更新 `research_agent_prompt`：新增"Available Search Tools"章节，说明 `tavily_search`、`exa_search`、`firecrawl_scrape` 的定位和使用场景
- [ ] 5.2 在 prompt 中添加推荐工作流描述：先 tavily 广搜 → firecrawl 深抓关键页面 → exa 语义补充
- [ ] 5.3 调整搜索次数上限建议（从 2-5 次调整为 3-7 次以适应三工具组合）
- [ ] 5.4 运行 notebook 单元生成源码，用 `ruff check` 验证

## 6. 集成验证

- [ ] 6.1 确保所有 notebook 单元可正常运行，生成的 `src/` 文件无 lint 错误
- [ ] 6.2 验证仅 Tavily key 存在时系统退回单工具模式（向后兼容）
- [ ] 6.3 提交变更到 development 分支，包含所有修改的 notebook 和生成的 src 文件
