## Context

素材库目前包含 54 个设计元素（颜色/装饰物/质地/风格），分布在 4 个维度 JSON 文件中，关联 6 种审美风格、103 个消费者信号、182 个视觉关键词。数据来源于 3 份行业趋势报告，后续会持续增长。

Design Agent（`design-agent` change）需要图结构来支持多策略创意检索（直觉匹配、角色类比、跨品类迁移、趋势前沿）。本 POC 验证 Semantica 框架能否胜任。

## Goals / Non-Goals

**Goals:**
- 验证 Semantica `GraphStore` API 能否从素材库 JSON 构建完整知识图谱
- 验证三种检索模式（Cypher 图遍历、embedding 语义搜索、hybrid）的可行性和 API 体验
- 评估 Semantica 的 embedding 集成（FastEmbed/sentence-transformers）对中文美妆领域的效果
- 输出 Go/No-Go 结论 + 具体问题清单

**Non-Goals:**
- 不做 Semantica vs raw Neo4j 的性能对比
- 不集成到 Design Agent 主流程（POC 是独立脚本）
- 不使用 Semantica 的 NER/RE 管线
- 不构建 OWL 本体

## Decisions

### Decision 1: Graph 后端选择——先用 NetworkX，再测 Neo4j

**选择**: 先用 Semantica 默认的 NetworkX（内存图），验证 API 可用性；如果 API OK 再切换到 Neo4j 后端验证持久化。

**理由**: NetworkX 零依赖、无需启动服务，适合快速验证 API 模式。54 节点完全在内存图的合理范围内。

**备选**: 直接用 Neo4j → 增加启动成本（Docker），POC 阶段不必要。

### Decision 2: 节点与边 Schema

**节点类型 (Labels)**:

| Label | 属性 | 来源 |
|-------|------|------|
| `Element` | id, name, name_en, maturity, year_range, typical_use, product_category | 素材库 JSON 直接映射 |
| `Style` | name | 从 `aesthetic_style` 字段去重提取 |
| `Signal` | name | 从 `signals` 数组去重提取 |
| `Dimension` | name, name_en | 4 个固定维度 |
| `Keyword` | text | 从 `visual_keywords` 数组去重提取 |

**边类型 (Relationships)**:

| 关系 | 方向 | 来源 | 作用 |
|------|------|------|------|
| `BELONGS_TO_STYLE` | Element → Style | `aesthetic_style` 字段 | 风格归属 |
| `IN_DIMENSION` | Element → Dimension | `dimension` 字段 | 维度分类 |
| `HAS_SIGNAL` | Element → Signal | `signals` 数组 | 消费者信号 |
| `HAS_KEYWORD` | Element → Keyword | `visual_keywords` 数组 | 视觉关键词 |
| `SIGNAL_BRIDGE` | Style ↔ Style | 推导：共享 Signal 数 ≥ 1 | 风格间信号桥接，weight=共享数 |
| `KEYWORD_BRIDGE` | Style ↔ Style | 推导：共享 Keyword 数 ≥ 1 | 风格间关键词桥接，weight=共享数 |

**选择理由**: 第一类边（结构边）从 JSON 字段直接映射，确定性高。第二类边（推导边）从数据计算，支持图遍历式的风格关联发现。

### Decision 3: Embedding 策略

**选择**: 使用 Semantica 内置 `EmbeddingGenerator`，默认 `BAAI/bge-small-en-v1.5`（FastEmbed）。

**嵌入内容**: 每个 Element 节点拼接 profile text：
```
"{name} | 风格:{aesthetic_style} | 关键词:{','.join(visual_keywords)} | 信号:{','.join(signals)}"
```

**验证点**:
1. 中文文本的 embedding 质量（bge-small-en 主要是英文模型，可能需要切换到 `BAAI/bge-small-zh-v1.5`）
2. 语义搜索是否能捕获 "蜂蜜色" → "琥珀色/金黄/发酵" 这类联想
3. 与图遍历结果的互补性

**备选**: Azure OpenAI embedding → 需要网络调用，POC 阶段优先本地模型。

### Decision 4: POC 脚本结构

```
notebooks/kg_poc.py
├── Part 1: Data Loading（从素材库 JSON 加载）
├── Part 2: Graph Construction（创建节点 + 边）
├── Part 3: Derived Edges（计算推导边）
├── Part 4: Graph Queries（Cypher / traversal 测试）
├── Part 5: Embedding Search（语义搜索测试）
├── Part 6: Hybrid Search（图 + 向量混合）
└── Part 7: Evaluation（输出结论）
```

**选择**: 单脚本而非 notebook，方便命令行运行和 CI。

## Risks / Trade-offs

| 风险 | 影响 | 缓解 |
|------|------|------|
| Semantica 核心依赖过重（torch, spacy 等） | 安装时间长、venv 膨胀 | 先检查是否可以只安装 `semantica[core]` 子集；如果不行，评估是否值得 |
| bge-small-en 对中文美妆术语效果差 | 语义搜索不准 | POC 中明确测试，准备 fallback 到 bge-zh 或 Azure OpenAI embedding |
| Semantica API 不稳定（v0.5.0，11个月） | import 报错、API 变更 | POC 就是为了发现这些问题；记录所有踩坑点 |
| NetworkX 后端不支持某些高级查询 | 部分 Cypher 功能不可用 | 记录限制，后续评估是否需要 Neo4j |

## Open Questions

1. Semantica 的 `GraphStore` NetworkX 后端是否支持 `get_neighbors()` 多跳遍历？还是仅限 1-hop？
2. `EmbeddingGenerator` 是否支持自定义模型路径（用 bge-zh 替换 bge-en）？
3. `hybrid_search` 模块是否支持自定义权重（图分数 vs 向量分数的 α 参数）？
4. Semantica 安装后的实际 venv 大小增量是多少？
