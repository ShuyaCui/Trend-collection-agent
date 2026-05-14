## ADDED Requirements

### Requirement: Firecrawl page scrape tool

系统 SHALL 提供 `firecrawl_scrape` 工具，允许 LLM 通过 Firecrawl API 对指定 URL 进行完整页面抓取并返回清洗后的 Markdown 内容。该工具接受 `url`（字符串）作为 LLM 可见参数。

系统 SHALL 使用 `InjectedToolArg` 控制 `output_format`（默认 `"markdown"`）参数。

系统 SHALL 将返回内容截断到合理长度（默认 10000 字符），防止超长页面消耗过多 LLM token。截断时 SHALL 在末尾附加 `[内容已截断]` 标记。

#### Scenario: Scrape a web page

- **WHEN** LLM 调用 `firecrawl_scrape(url="https://example.com/article")`
- **THEN** 系统通过 Firecrawl API 抓取该 URL，返回清洗后的 Markdown 格式内容，包含页面标题和正文

#### Scenario: Firecrawl API key not set

- **WHEN** 环境变量 `FIRECRAWL_API_KEY` 未设置
- **THEN** `firecrawl_scrape` 工具不出现在可用工具列表中，系统正常运行不报错

#### Scenario: Invalid or unreachable URL

- **WHEN** LLM 提供的 URL 无法访问（404、超时、域名不存在）
- **THEN** 工具返回包含错误描述的字符串（不抛出异常）

#### Scenario: Content truncation

- **WHEN** 抓取的页面 Markdown 内容超过 10000 字符
- **THEN** 内容被截断到 10000 字符，并在末尾附加 `[内容已截断]` 标记

#### Scenario: Firecrawl API error handling

- **WHEN** Firecrawl API 调用失败（网络错误、速率限制、无效 key）
- **THEN** 工具返回包含错误描述的字符串（不抛出异常），LLM 可据此决定跳过该页面
