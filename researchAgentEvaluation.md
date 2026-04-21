# Research Agent Evaluation 优化方案

## 一、实现思路

- **目标**：将单一“是否继续/停止”评估，升级为覆盖过程质量与产物质量的多维度体系，兼顾结果导向、非确定性鲁棒、可持续追踪。
- **评估对象**：
  - Node-level（决策层）：保留/扩展对 `llm_call` 节点的评估，快速回归。
  - End-to-end（产物层）：完整运行 research agent，评估 `compressed_research`、`raw_notes`、`researcher_messages` 等产物质量。
- **数据集设计**：
  - Synthetic（可控）：toy message histories，制造边界条件。
  - Real briefs（真实）：5–10 条实际 research brief，覆盖 simple/medium/complex/very_complex。
- **多维度指标**：
  1.  Tool efficiency（工具调用次数、冗余度、预算遵守）
  2.  Process quality（每次搜索后是否有 think_tool 反思）
  3.  Source quality（来源数量、域名多样性、可信度）
  4.  Citation correctness（引用格式、编号连续、Sources 列表）
  5.  Faithfulness/completeness（压缩内容对工具输出的忠实度）
- **评估方法**：Hybrid（启发式门禁 + LLM-as-judge）
  - 启发式门禁：硬性要求（预算、格式、泄漏、反思污染）
  - LLM-as-judge：主观/语义类质量（query 质量、压缩忠实度）
- **持续评估/回归**：每次改 prompt/工具/路由都跑同一套 eval，记录各维度得分、token/tool calls。

### 1.1 评估总体结构（Outcome-first + Multi-dimensional）

- **原则**：不评估“走了哪条路径”，评估“是否产出可用的研究产物 + 过程是否合理”。
- **两类评估并行**：
  - **质量门禁（Gates）**：确定性、低成本、用于阻止明显回归（格式/泄漏/预算/反思污染）。
  - **质量评分（Rubric）**：多维度、可趋势追踪，用于衡量改动是否“更好”。

### 1.2 Rubric（维度、权重、通过阈值）

参照 evaluation skill 的默认 rubric（见 metrics reference），并结合本项目“research agent”特点（依赖外部来源、强引用要求）做轻量调整：

- **factual_accuracy / supportedness（0.30）**：关键断言是否被来源支持（不要求“全量 ground truth”，改用“可被引用支持/可追溯”）。
- **completeness（0.25）**：是否覆盖 research brief 的关键问题与约束，是否回答到“用户真正关心的维度”。
- **citation_accuracy（0.15）**：引用格式正确、可追溯，引用与 sources 列表一致。
- **source_quality（0.10）**：来源可信度与多样性（优先权威/一手/高质量聚合）。
- **tool_efficiency（0.20）**：工具使用是否合理（次数、冗余、是否因错误搜索策略导致浪费）。

**总体得分**：$overall = \sum_i weight_i \cdot score_i$；建议默认 **pass threshold = 0.70**（可按业务风险调整）。

> 说明：research agent 很难获得严格的“ground truth”；因此 factual_accuracy 的实现更贴近“supportedness”（抽样核对关键主张是否有对应来源支持）。

## 二、需要修改的文件路径

- 方案文档（本文件）
  - [deep_research_from_scratch/researchAgentEvaluation.md](deep_research_from_scratch/researchAgentEvaluation.md)
- 研究 agent 的 eval 实现与实验入口
  - [deep_research_from_scratch/notebooks/2_research_agent.ipynb](deep_research_from_scratch/notebooks/2_research_agent.ipynb)
- 可选：end-to-end 产物评估
  - [deep_research_from_scratch/notebooks/5_full_agent.ipynb](deep_research_from_scratch/notebooks/5_full_agent.ipynb)
- 可选：抽取/解析复用逻辑
  - [deep_research_from_scratch/notebooks/utils.py](deep_research_from_scratch/notebooks/utils.py)

> 注：源码生成仍由 notebook `%%writefile`，不直接改 src/ 目录。

## 三、数据集与标注规范（Test Set Design）

### 3.1 用例分层（Complexity Stratification）

建议将测试集按复杂度分层，并在每条 case 打标签（tags），便于趋势分析和定位回归：

- **simple**：1 次搜索即可回答（例如“列出 X 的前 3 个候选 + 引用”）。
- **medium**：2–3 次搜索 + 需要对比/归纳。
- **complex**：多约束、多来源冲突、需要明确方法论（例如“按某指标排名并解释依据”）。
- **very_complex**：存在歧义/需要澄清假设/跨领域综合（可用于压力测试）。

### 3.2 Case 结构（LangSmith Dataset Schema 建议）

为兼容 node-level 与 end-to-end 两类 target_func，建议准备两种输入形态（或在一个 case 中同时包含）：

- **Node-level cases**：
  - inputs：`{ researcher_messages: [...] }`（人工构造的 message history）
  - expected：`{ next_step: "continue" | "stop" }`
- **End-to-end cases**：
  - inputs：`{ research_topic / research_brief / researcher_messages(单条Human) }`
  - expected（轻量标注即可，不追求完美 ground truth）：
    - `min_sources`（例如 >=3）
    - `must_include`（2–6 条关键点/约束）
    - `must_not_include`（禁止假设/禁止反思污染/禁止占位符泄漏）

### 3.3 标注策略（Low-effort, High-signal）

- **先小后大**：先用 5–10 条 small set 快速迭代，稳定后再扩充。
- **标注粒度**：
  - 对“完整性”只标注关键点（must_include），避免标注成本过高。
  - 对“事实准确性”优先做“可追溯性/被引用支持”的抽样核对。

## 四、评估器设计（Evaluators）

本节将评估器分为：**硬门禁（Gates）** 与 **Rubric 评分（Scores）**。

### 4.1 硬门禁（建议默认必须通过）

- **G1：模板占位符泄漏**：`compressed_research` / 末尾产物中不得出现 `{date}`、`{research_topic}` 等 `\{[a-zA-Z_]+\}`。
- **G2：反思污染**：压缩产物不得包含 think_tool 输出（例如 `Reflection recorded:`）。
- **G3：引用格式合规**：必须包含 inline 引用与 `### Sources` 列表，sources 编号必须连续无缺口。
- **G4：最小来源数**：unique URL 数量达到阈值（例如 >=3）。
- **G5：工具预算**：`tavily_search` 次数 <= 设定上限（与 prompt 一致）。

> 门禁失败应直接标记 run 为 fail（无论 rubric 得分如何），因为这类问题通常会破坏下游 writer 或导致不可用输出。

### 4.2 Rubric 评分（多维度可趋势追踪）

- **tool_efficiency**：结合搜索次数、冗余度、是否出现“重复 query / 重复 URL”衡量。
- **citation_accuracy**：除了格式，还应检查“引用编号在正文出现”与“Sources 列表存在对应条目”。
- **source_quality**：以启发式为主（域名多样性/权威域名白名单/明显低质域名黑名单），必要时用 LLM judge。
- **completeness**：用 must_include 的覆盖率 + LLM judge 双保险。
- **supportedness（替代 factual_accuracy）**：从产物抽样 5–10 个关键主张，让 judge 判断“是否有对应来源支持/是否过度推断”。

## 五、关键代码片段（伪代码/结构化描述）

**A. 工具预算与循环检测**

```
count_search_calls(researcher_messages) -> n
pass if n <= MAX_SEARCHES else fail
redundancy_score = 1 - similarity(q_i, q_{i-1})  # 或 URL overlap
```

**A2. 总体得分汇总（Rubric 计算）**

```
overall = sum(weight[d] * score[d] for d in dimensions)
passed = (overall >= 0.70) and all(gates_passed)
```

**B. think-after-search 合规率**

```
for each tavily_search call:
   check next tool call before next search/stop includes think_tool
score = compliant / total_searches
```

**C. 引用格式与 Sources 列表校验**

```
has_sources_section = "### Sources" in compressed_research
has_inline_citations = match r"\[\d+\]" in body
sources_numbered_sequentially = check [1],[2],... 无缺口
score = weighted_rules_passed
```

**C2. 引用一致性（正文引用 ↔ Sources 列表）**

```
body_citations = extract_numbers_in_brackets(body)
sources_numbers = extract_numbers_in_sources_list(sources_section)
pass if body_citations subset_of sources_numbers
```

**D. 禁止泄漏（反思污染/模板占位符）**

```
fail if "Reflection recorded:" in compressed_research
fail if match r"\{[a-zA-Z_]+\}" in compressed_research
```

**E. LLM-as-judge：query 质量**

```
Input: research_brief + each tavily_search query
Output schema:
   relevance (1-5)
   specificity (1-5)
   constraint_coverage (1-5)
   reasoning (string)
Aggregate: mean score, plus “must-fix” reasons
```

**E2. LLM-as-judge Prompt 设计要点（减少偏差/提高一致性）**

```
- 角色：严格但公平的 research evaluation auditor
- 输出：强制结构化（JSON/Pydantic schema），避免自由散文
- 标准：给出 1-2 个 PASS/FAIL 例子，明确边界
- 指令：当信息不足时倾向 FAIL，并写出可操作的改进建议
```

**F. LLM-as-judge：压缩忠实度/信息保留**

```
Input: tool outputs (raw_notes filtered) + compressed_research
Output schema:
   faithfulness (0-1)
   key_facts_missing (list)
   hallucinations_detected (list)
   reasoning
Gate: fail if hallucinations_detected 非空
```

**F2. Supportedness（主张可追溯性抽样）**

```
claims = sample_key_claims(compressed_research, k=5..10)
for claim in claims:
  judge: supported_by_any_source? (yes/no) + which source id
score = supported_claims / total_claims
```

**G. 实验组织（LangSmith）**

```
Dataset:
   inputs: {research_brief | researcher_messages}
   reference_outputs: {expected_next_step | expected_min_sources | ...}
Evaluators: [heuristic_gates..., llm_judges...]
Run: node-level target_func + end-to-end target_func
Track: scores + tool_calls + token usage
```

## 六、执行与报告（Continuous Evaluation）

### 6.1 运行策略

- **开发期**：只跑 small set（例如 10–20 条），每次改 prompt 都跑。
- **合入/发布前**：跑 full set（含 real briefs），并输出趋势对比（与上一次 baseline 对比）。
- **非确定性处理**：对关键 case 重复运行 2–3 次，记录均值与最差值（避免“侥幸通过”）。

### 6.2 关键监控指标（建议写入实验摘要）

- pass rate（门禁通过率、总体通过率）
- overall rubric score（均值/分位数）
- per-dimension scores（定位回归）
- avg tool calls / avg token usage（成本与性能的主要驱动项）
- unique sources / unique domains（研究覆盖度）

### 6.3 失败用例归因模板（方便修复）

- **Failure type**：格式/引用/预算/反思污染/不完整/不支持
- **Likely root cause**：prompt 变化 / 工具输出变化 / 解析失败 / 路由错误
- **Fix suggestion**：针对性改 prompt、加 stop condition、改压缩过滤规则等

## 七、注意事项与风险

- **非确定性与评估噪声**：LLM judge 有波动，建议结构化输出+多次运行取均值/最差值。
- **评估成本**：LLM judge 成本高，建议启发式门禁优先，LLM judge 聚焦关键维度。
- **过拟合路径 vs 结果导向**：避免写死“必须用某搜索词/站点”，更应评估产物可用性与支撑。
- **输入输出可解析性**：tool call/URL 抽取依赖格式稳定，建议集中解析逻辑并显式报错。
- **反思污染**：think_tool 内容进入压缩结果为硬门禁。
- **模板占位符泄漏**：如 `{date}`、`{research_topic}`，建议硬门禁并 trace 源头。
- **数据集代表性**：synthetic+real 结合，开发期小样本+复杂度分层，后续扩充真实样本。

### 7.1 评估偏差与防护

- **位置/长度偏差**：judge 容易偏好更长输出；需要在 rubric 中明确“冗余扣分”与“引用/支持优先”。
- **模型漂移**：judge 模型升级可能改变评分；建议固定 judge 模型版本或定期重建 baseline。
- **过严门禁导致假阴性**：门禁应只覆盖“明确违反规范”的问题（占位符/反思污染/引用缺失）。

### 7.2 成本控制（与 evaluation skill 的 95% finding 对齐）

- 明确每次 eval 的 token/tool 预算；把“tool calls 数/重复搜索”纳入 tool_efficiency。
- 优先用启发式做大规模筛查，把 LLM judge 用在：query 质量、supportedness 抽样、faithfulness。
