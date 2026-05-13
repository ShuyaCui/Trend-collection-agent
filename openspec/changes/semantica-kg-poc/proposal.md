## Why

Design Agent 需要一个知识图谱来存储素材库中的设计元素（颜色、装饰物、质地、风格）及其语义关系（共享信号、风格邻接、跨品类关联），以支持多策略创意检索。当前素材库是扁平 JSON 文件，无法表达元素间的关联关系，也无法做图遍历式的类比发现和跨品类迁移。

本 POC 验证 [Semantica](https://github.com/Hawksight-AI/semantica) 框架是否适合构建和查询这个知识图谱——评估其 GraphStore API、embedding 集成、hybrid search 能力，以及与现有素材库数据的对接可行性。

## What Changes

- 新增 `notebooks/kg_poc.py`：POC 脚本，使用 Semantica 从素材库 JSON 构建知识图谱
- 新增依赖 `semantica` 到 `pyproject.toml`（含 `graph-neo4j` extra）
- 构建图结构：Element / Style / Signal / Dimension / Keyword 节点 + 结构边 + 推导边
- 验证三种检索模式：Cypher 图遍历、embedding 语义搜索、hybrid graph+vector 检索
- 输出 POC 评估结论，决定是否在 Design Agent 正式采用 Semantica

## Non-goals

- 不实现完整的 Design Agent CLI（已在 `design-agent` change 中规划）
- 不使用 Semantica 的 NER/RE 抽取管线（素材库已是结构化数据）
- 不做性能基准测试（60 节点规模下性能不是问题）
- 不构建 OWL 本体（schema-optional 即可）

## Capabilities

### New Capabilities

- `kg-graph-construction`: 从素材库 JSON 构建知识图谱——节点创建、边类型定义、推导边计算
- `kg-retrieval-modes`: 三种检索模式的 POC 验证——图遍历、语义搜索、混合检索

### Modified Capabilities

（无）

## Impact

- **依赖**: 新增 `semantica[graph-neo4j]`，引入 torch/spacy/sentence-transformers 等重依赖
- **基础设施**: 需要运行 Neo4j 实例（可用 Docker `neo4j:5` 或 Semantica 内置 NetworkX 后端做初步验证）
- **后续影响**: POC 结论将直接影响 `design-agent` change 的技术选型——如果 Semantica 不适合，回退到 raw neo4j driver + 独立 embedding 方案
