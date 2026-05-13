## ADDED Requirements

### Requirement: Graph traversal queries via Python API

系统 SHALL 支持通过 Semantica GraphStore Python API 执行图遍历查询：给定一个 Style 名称，返回该风格下的所有 Element 节点；给定一个 Element，返回其所有 Signal 邻居。

#### Scenario: Find elements by style

- **WHEN** 查询 Style="天然奢养" 的所有 Element
- **THEN** 返回 aesthetic_style 为 "天然奢养" 的所有 Element 节点（≥3 个）

#### Scenario: Find signals of an element

- **WHEN** 查询 Element "金箔" 的 HAS_SIGNAL 邻居
- **THEN** 返回 Signal 节点列表，包含 "贵妇护理"、"焕亮"、"抗老"

#### Scenario: Multi-hop traversal via bridge edges

- **WHEN** 从 Style "天然奢养" 出发，经过 SIGNAL_BRIDGE 到达邻接 Style，再到达其下属 Element
- **THEN** 返回邻接风格的元素列表（如 "奢华克制" 下的元素）

### Requirement: Embedding-based semantic search

系统 SHALL 为每个 Element 节点生成 embedding（拼接 name + aesthetic_style + visual_keywords + signals），支持给定自然语言查询文本，返回 embedding 余弦相似度 top-K 的 Element。

#### Scenario: Semantic similarity finds related elements

- **WHEN** 查询文本为 "蜂蜜色滋养精华"
- **THEN** 返回的 top-5 中包含 "琥珀滋养精华" 或 "黄色/橙色/琥珀色"

#### Scenario: Cross-dimension semantic match

- **WHEN** 查询文本为 "奢华金色抗老"
- **THEN** 返回的 top-5 中包含来自不同维度的元素（如颜色 "金色" + 装饰物 "金箔" + 质地 "金色奢华凝露"）

### Requirement: Hybrid graph + vector retrieval

系统 SHALL 支持混合检索模式：先通过图遍历获取候选集（如某风格下的元素），再用 embedding 相似度在候选集内排序。

#### Scenario: Style-scoped semantic search

- **WHEN** 限定 Style="科技净澈"，查询文本为 "冷感舒缓"
- **THEN** 返回 "科技净澈" 风格下按语义相似度排序的 Element，"淡蓝冷感凝露" 或 "淡蓝" 排名靠前

#### Scenario: Bridge-expanded semantic search

- **WHEN** 从 Style="天然奢养" 出发，经 SIGNAL_BRIDGE 扩展到邻接风格的元素候选集，再用查询文本 "发酵滋养" 排序
- **THEN** 结果包含天然奢养本风格元素和邻接风格中与 "发酵滋养" 语义相关的元素

### Requirement: POC evaluation output

系统 SHALL 在所有检索测试完成后输出评估报告，包含：每种检索模式的测试结果、发现的 API 问题/限制、Go/No-Go 建议。

#### Scenario: Evaluation report generated

- **WHEN** 所有检索模式测试完成
- **THEN** 输出结构化评估，每个测试用例标注 ✅ PASS 或 ❌ FAIL + 原因
