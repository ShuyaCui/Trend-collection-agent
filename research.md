# Deep Research From Scratch（当前项目）深度理解总结
## 1) 项目目标与功能逻辑（What it does）

这是一个用 **LangGraph** 从零搭建的「深度研究（Deep Research）」系统，整体遵循三阶段架构：

1. **Scope（澄清与定题）**  
   - 判断用户输入是否信息充分，不足则提出**单个高质量澄清问题**。  
   - 信息充分则把对话历史转成**可执行的 research brief（研究简报 / 研究问题）**，并传递给后续研究模块。  
   - 关键实现：[`deep_research_from_scratch.research_agent_scope.clarify_with_user`](src/deep_research_from_scratch/research_agent_scope.py)、[`deep_research_from_scratch.research_agent_scope.write_research_brief`](src/deep_research_from_scratch/research_agent_scope.py)  
   - 结构化输出 schema：[`deep_research_from_scratch.state_scope.ClarifyWithUser`](src/deep_research_from_scratch/state_scope.py)、[`deep_research_from_scratch.state_scope.ResearchQuestion`](src/deep_research_from_scratch/state_scope.py)

2. **Research（研究执行）**  
   研究有两条实现路径：
   - **Web 搜索型研究代理**：迭代调用搜索工具 + 反思工具，最终压缩整理研究发现。  
     - 关键实现：[`deep_research_from_scratch.research_agent`](src/deep_research_from_scratch/research_agent.py)  
     - 主要工具：[`deep_research_from_scratch.utils.tavily_search`](src/deep_research_from_scratch/utils.py)、[`deep_research_from_scratch.utils.think_tool`](src/deep_research_from_scratch/utils.py)
   - **MCP 本地文件型研究代理**：通过 **Model Context Protocol（MCP）filesystem server** 对本地资料库做“目录探查→搜索→阅读→反思→停止”。  
     - 关键实现：[`deep_research_from_scratch.research_agent_mcp`](src/deep_research_from_scratch/research_agent_mcp.py)  
     - 文件根目录由 [`deep_research_from_scratch.utils.get_current_dir`](src/deep_research_from_scratch/utils.py) 决定，并挂载到 `.../src/deep_research_from_scratch/files/`（示例文件见：[src/deep_research_from_scratch/files/coffee_shops_sf.md](src/deep_research_from_scratch/files/coffee_shops_sf.md)）

3. **Write（写作汇总）**  
   - 将研究 notes 聚合成最终报告（Markdown 结构化、带 Sources）。  
   - 关键实现：[`deep_research_from_scratch.research_agent_full.final_report_generation`](src/deep_research_from_scratch/research_agent_full.py)  
   - 使用提示词模板：[`deep_research_from_scratch.prompts.final_report_generation_prompt`](src/deep_research_from_scratch/prompts.py)

---

## 2) 代码结构（How it’s organized）

### 2.1 重要约束：Notebook 是“唯一真源”
- **只能修改** `notebooks/` 下的教程 Notebook（例如：[notebooks/1_scoping.ipynb](notebooks/1_scoping.ipynb)、[notebooks/2_research_agent.ipynb](notebooks/2_research_agent.ipynb) 等）。  
- `src/deep_research_from_scratch/` 是通过 Notebook 里的 `%%writefile` **自动生成的产物**，不应手改（否则会被覆盖）。  
- 该工作流在仓库指南中明确（见：[CLAUDE.md](CLAUDE.md)）。

### 2.2 `src/deep_research_from_scratch/` 模块职责划分（核心）
- **Prompt 模板集中管理**：  
  - [src/deep_research_from_scratch/prompts.py](src/deep_research_from_scratch/prompts.py)  
  - 包含 scoping、research、compression、final report、citation rules、hard limits 等关键提示词。  
  - 代表性模板：  
    - [`deep_research_from_scratch.prompts.clarify_with_user_instructions`](src/deep_research_from_scratch/prompts.py)（要求输出固定 JSON key）  
    - [`deep_research_from_scratch.prompts.transform_messages_into_research_topic_prompt`](src/deep_research_from_scratch/prompts.py)（把对话变成研究问题，强调“未指明维度谨慎处理”）  
    - [`deep_research_from_scratch.prompts.research_agent_prompt_with_mcp`](src/deep_research_from_scratch/prompts.py)（MCP 文件研究策略与 file operation budgets）  
    - [`deep_research_from_scratch.prompts.compress_research_system_prompt`](src/deep_research_from_scratch/prompts.py)（压缩研究：保留信息与 sources，过滤 think_tool）  
    - [`deep_research_from_scratch.prompts.final_report_generation_prompt`](src/deep_research_from_scratch/prompts.py)（最终报告、语言一致性、Sources）

- **State 与结构化 Schema（Pydantic / TypedDict）**：
  - Scoping 状态与 schema：[src/deep_research_from_scratch/state_scope.py](src/deep_research_from_scratch/state_scope.py)  
    - 代表性 schema：[`deep_research_from_scratch.state_scope.ClarifyWithUser`](src/deep_research_from_scratch/state_scope.py)、[`deep_research_from_scratch.state_scope.ResearchQuestion`](src/deep_research_from_scratch/state_scope.py)
  - Research 状态与 schema：[src/deep_research_from_scratch/state_research.py](src/deep_research_from_scratch/state_research.py)  
    - 研究状态字段清晰：[`deep_research_from_scratch.state_research.ResearcherState`](src/deep_research_from_scratch/state_research.py)（`researcher_messages / tool_call_iterations / research_topic / compressed_research / raw_notes`）
    - 网页摘要 schema：[`deep_research_from_scratch.state_research.Summary`](src/deep_research_from_scratch/state_research.py)
  - Supervisor 状态与工具 schema：[src/deep_research_from_scratch/state_multi_agent_supervisor.py](src/deep_research_from_scratch/state_multi_agent_supervisor.py)  
    - 代表性工具：[`deep_research_from_scratch.state_multi_agent_supervisor.ConductResearch`](src/deep_research_from_scratch/state_multi_agent_supervisor.py)、[`deep_research_from_scratch.state_multi_agent_supervisor.ResearchComplete`](src/deep_research_from_scratch/state_multi_agent_supervisor.py)

- **Agent/Graph 实现（LangGraph）**：
  - Scoping 子图：[`deep_research_from_scratch.research_agent_scope`](src/deep_research_from_scratch/research_agent_scope.py)
  - 单研究员（web）：[`deep_research_from_scratch.research_agent`](src/deep_research_from_scratch/research_agent.py)
  - 单研究员（MCP/files）：[`deep_research_from_scratch.research_agent_mcp`](src/deep_research_from_scratch/research_agent_mcp.py)
  - 多智能体 Supervisor：[`deep_research_from_scratch.multi_agent_supervisor`](src/deep_research_from_scratch/multi_agent_supervisor.py)
  - 端到端整合：[`deep_research_from_scratch.research_agent_full`](src/deep_research_from_scratch/research_agent_full.py)

- **工具与通用能力（utils）**：  
  - [src/deep_research_from_scratch/utils.py](src/deep_research_from_scratch/utils.py)  
  - 关键能力：
    - 日期：[`deep_research_from_scratch.utils.get_today_str`](src/deep_research_from_scratch/utils.py)
    - 反思停顿工具：[`deep_research_from_scratch.utils.think_tool`](src/deep_research_from_scratch/utils.py)（强制研究节奏：每次信息获取后反思是否足够）
    - 网页内容压缩总结：[`deep_research_from_scratch.utils.summarize_webpage_content`](src/deep_research_from_scratch/utils.py)（结构化输出 Summary，并格式化为 `<summary>...</summary><key_excerpts>...</key_excerpts>`）

---

## 3) 技术栈（Tech stack）

### 3.1 Python & 依赖生态
- **Python 3.11+**（README 说明）：[README.md](README.md)
- **LangGraph**（状态图编排、子图、Command 路由）：  
  - 典型用法：`StateGraph`, `START`, `END`, `Command`（见 [`deep_research_from_scratch.research_agent_scope`](src/deep_research_from_scratch/research_agent_scope.py)）
- **LangChain**（模型初始化、messages、tools、结构化输出）：  
  - `init_chat_model`、`with_structured_output`、`HumanMessage/AIMessage/ToolMessage`
- **Pydantic**（结构化输出 schema，确保确定性与低幻觉）
- **Tavily**（外部搜索）：[`deep_research_from_scratch.utils.tavily_search`](src/deep_research_from_scratch/utils.py)
- **MCP（Model Context Protocol）**：filesystem server 通过 `npx @modelcontextprotocol/server-filesystem`（见 [`deep_research_from_scratch.research_agent_mcp.mcp_config`](src/deep_research_from_scratch/research_agent_mcp.py)）
- **dotenv**（加载 `.env`）：见 [src/deep_research_from_scratch/utils.py](src/deep_research_from_scratch/utils.py)、[src/deep_research_from_scratch/research_agent.py](src/deep_research_from_scratch/research_agent.py) 等
- **Node.js / npx**（MCP server 运行依赖）：[README.md](README.md)

### 3.2 模型使用策略（Models）
从现有代码片段可见多模型分工（按任务分层）：
- 摘要/写作倾向使用较大上下文（例如 gpt-4.1）：[`deep_research_from_scratch.utils.summarization_model`](src/deep_research_from_scratch/utils.py)、[`deep_research_from_scratch.research_agent_full.writer_model`](src/deep_research_from_scratch/research_agent_full.py)
- 研究代理可能使用不同供应商模型（示例见 [`deep_research_from_scratch.research_agent_mcp`](src/deep_research_from_scratch/research_agent_mcp.py) 初始化）

---

## 4) 关键规范与“内置护栏”（Standards & guardrails）

### 4.1 结构化输出优先（减少幻觉）
- Scoping 阶段的“是否需要澄清”与“研究问题生成”都走 Pydantic schema：  
  - [`deep_research_from_scratch.state_scope.ClarifyWithUser`](src/deep_research_from_scratch/state_scope.py) / [`deep_research_from_scratch.state_scope.ResearchQuestion`](src/deep_research_from_scratch/state_scope.py)  
  - 代码路由示例：[`deep_research_from_scratch.research_agent_scope.clarify_with_user`](src/deep_research_from_scratch/research_agent_scope.py)

### 4.2 研究节奏：工具调用后强制反思（think_tool）
- 反思工具定义：[`deep_research_from_scratch.utils.think_tool`](src/deep_research_from_scratch/utils.py)  
- Prompt 中明确：研究 supervisor / MCP 文件研究都要求在关键节点调用 `think_tool`（见 [`deep_research_from_scratch.prompts.lead_researcher_prompt`](src/deep_research_from_scratch/prompts.py) 与 [`deep_research_from_scratch.prompts.research_agent_prompt_with_mcp`](src/deep_research_from_scratch/prompts.py)）

### 4.3 硬限制（Hard limits / budgets）
- Supervisor 有 max iterations（提示词内硬限制）：[`deep_research_from_scratch.prompts.lead_researcher_prompt`](src/deep_research_from_scratch/prompts.py)
- MCP 文件研究有 file operation budgets（3-4/6 次上限）：[`deep_research_from_scratch.prompts.research_agent_prompt_with_mcp`](src/deep_research_from_scratch/prompts.py)

### 4.4 压缩研究结果的“信息保真”原则
- 压缩提示词强调：
  - **保留所有相关信息与 sources**
  - **过滤 think_tool**（反思不属于事实发现）  
  见：[`deep_research_from_scratch.prompts.compress_research_system_prompt`](src/deep_research_from_scratch/prompts.py)

### 4.5 引用与 Sources 规范（对最终报告非常关键）
- 最终写作提示词包含 citation rules（顺序编号、不跳号、Sources 列表）：  
  - 见 [`deep_research_from_scratch.prompts.final_report_generation_prompt`](src/deep_research_from_scratch/prompts.py) 与相关 citation 规则段落（同文件）

### 4.6 开发与格式化规范
- Ruff 检查（且强调：**格式问题要在 notebooks 的 writefile cell 修**）：[CLAUDE.md](CLAUDE.md)

---

## 5) 端到端数据流（State flow / control flow）

### 5.1 Scope 子图（澄清→brief）
- 输入：对话消息（messages）
- 输出：`research_brief`（字符串），并生成给 supervisor 的消息（如 `supervisor_messages`）
- 关键节点：  
  - [`deep_research_from_scratch.research_agent_scope.clarify_with_user`](src/deep_research_from_scratch/research_agent_scope.py)（`need_clarification` → END；否则 goto `write_research_brief`）  
  - [`deep_research_from_scratch.research_agent_scope.write_research_brief`](src/deep_research_from_scratch/research_agent_scope.py)

### 5.2 Research（单代理 or Supervisor 多代理）
- 单代理研究状态：[`deep_research_from_scratch.state_research.ResearcherState`](src/deep_research_from_scratch/state_research.py)
- Supervisor 的“委派工具”schema：[`deep_research_from_scratch.state_multi_agent_supervisor.ConductResearch`](src/deep_research_from_scratch/state_multi_agent_supervisor.py) + 完成信号 [`deep_research_from_scratch.state_multi_agent_supervisor.ResearchComplete`](src/deep_research_from_scratch/state_multi_agent_supervisor.py)

### 5.3 Write（最终报告）
- 端到端整合图：[`deep_research_from_scratch.research_agent_full`](src/deep_research_from_scratch/research_agent_full.py)  
- 最终写作节点：[`deep_research_from_scratch.research_agent_full.final_report_generation`](src/deep_research_from_scratch/research_agent_full.py)（把 `notes` 合并为 findings，套 prompt 生成 final_report）

---

## 6) 你当前 `src/` 附带的本地资料库（MCP/files）
- 目录：[src/deep_research_from_scratch/files/](src/deep_research_from_scratch/files/)  
- 示例文件：[src/deep_research_from_scratch/files/coffee_shops_sf.md](src/deep_research_from_scratch/files/coffee_shops_sf.md)  
- MCP research agent 的 filesystem server 配置在：[`deep_research_from_scratch.research_agent_mcp.mcp_config`](src/deep_research_from_scratch/research_agent_mcp.py)

---

## 7) 实用结论（给后续开发/改造用的要点）
1. **想改行为 = 改 notebook**：任何 prompt、graph、state 的调整都应该在 [notebooks/](notebooks/) 中改，并运行对应 `%%writefile` cell 生成到 [src/](src/)（见 [CLAUDE.md](CLAUDE.md)）。
2. **“可靠”来自结构化输出**：scoping 与 summarization 都用 schema（见 [`deep_research_from_scratch.state_scope`](src/deep_research_from_scratch/state_scope.py)、[`deep_research_from_scratch.state_research.Summary`](src/deep_research_from_scratch/state_research.py)）。
3. **研究质量控制靠 think_tool + budgets + citations**：  
   - 反思工具：[`deep_research_from_scratch.utils.think_tool`](src/deep_research_from_scratch/utils.py)  
   - 硬限制写在 prompts：[`deep_research_from_scratch.prompts`](src/deep_research_from_scratch/prompts.py)
4. **压缩阶段不要把“思考”当“事实”**：压缩提示词明确过滤 think_tool（见 [`deep_research_from_scratch.prompts.compress_research_system_prompt`](src/deep_research_from_scratch/prompts.py)）。

---