## ADDED Requirements

### Requirement: Load material library into graph nodes

系统 SHALL 从 `material_library/` 下的 4 个维度 JSON 文件（color.json, decoration.json, texture.json, style.json）读取所有元素，为每个元素创建 `Element` 节点，属性包含 id, name, name_en, maturity, year_range, typical_use, product_category。

#### Scenario: All elements loaded

- **WHEN** 素材库包含 54 个元素（14 颜色 + 17 装饰物 + 16 质地 + 7 风格）
- **THEN** 图中创建 54 个 `Element` 节点，每个节点包含完整属性

#### Scenario: Missing dimension file

- **WHEN** `material_library/texture.json` 不存在
- **THEN** 系统跳过该文件并 log 警告，其他维度正常加载

### Requirement: Create auxiliary nodes from element fields

系统 SHALL 从所有元素中提取去重的 Style、Signal、Dimension、Keyword 值，分别创建对应类型的节点。

#### Scenario: Style nodes created

- **WHEN** 素材库中元素的 `aesthetic_style` 包含 6 个不同值
- **THEN** 图中创建 6 个 `Style` 节点

#### Scenario: Signal nodes deduplicated

- **WHEN** 多个元素共享同一个 signal（如 "高端感" 出现在 7 个元素中）
- **THEN** 图中只创建 1 个 `Signal(name="高端感")` 节点

### Requirement: Create structural edges from element fields

系统 SHALL 为每个元素创建 4 种结构边：`BELONGS_TO_STYLE`（→ Style）、`IN_DIMENSION`（→ Dimension）、`HAS_SIGNAL`（→ Signal，每个信号一条边）、`HAS_KEYWORD`（→ Keyword，每个关键词一条边）。

#### Scenario: Element with 5 signals creates 5 edges

- **WHEN** 元素 "透明/半透明" 有 signals=["洁净科技","低负担","好吸收","清爽","控油修护"]
- **THEN** 创建 5 条 `HAS_SIGNAL` 边，从该 Element 分别指向 5 个 Signal 节点

#### Scenario: Edge count matches data

- **WHEN** 全部 54 个元素加载完成
- **THEN** `BELONGS_TO_STYLE` 边数 = 54，`IN_DIMENSION` 边数 = 54

### Requirement: Compute derived style bridge edges

系统 SHALL 计算 Style 节点间的推导边：当两个 Style 的下属元素共享至少 1 个 Signal 时，创建 `SIGNAL_BRIDGE` 边（weight=共享信号数）；共享至少 1 个 Keyword 时，创建 `KEYWORD_BRIDGE` 边（weight=共享关键词数）。

#### Scenario: Signal bridge with weight

- **WHEN** "科技净澈" 和 "自然清体" 的元素共享信号 ["清爽","补水"]
- **THEN** 创建 `SIGNAL_BRIDGE(weight=2, signals=["清爽","补水"])` 边连接两个 Style 节点

#### Scenario: No bridge for disjoint styles

- **WHEN** 两个 Style 的元素没有任何共享信号或关键词
- **THEN** 不创建它们之间的 bridge 边

### Requirement: Graph statistics output

系统 SHALL 在图构建完成后输出统计信息：各类型节点数量、各类型边数量、总节点数、总边数。

#### Scenario: Statistics printed after construction

- **WHEN** 图构建完成
- **THEN** 输出包含 "Element: 54, Style: 6, Signal: N, Dimension: 4, Keyword: M" 的统计
