## ADDED Requirements

### Requirement: Intuition matching strategy

系统 SHALL 实现直觉匹配策略：过滤 `aesthetic_style` 与目标风格一致的元素，按 `visual_keywords` 与用户关键词的子串重叠度排序，每维度返回 top-5 候选。

#### Scenario: Exact style match with keyword overlap

- **WHEN** 用户查询解析结果为 `target_style="天然奢养"`, `color_keywords=["蜂蜜", "金色"]`
- **THEN** 系统返回 `aesthetic_style == "天然奢养"` 的颜色元素，按 visual_keywords 中包含 "蜂蜜" 或 "金色" 子串的数量降序排列，最多 5 个

#### Scenario: No keywords provided

- **WHEN** 用户查询解析结果只有 `target_style` 而无维度关键词
- **THEN** 系统返回该风格下所有元素，按 maturity 排序（主流优先），每维度最多 5 个

### Requirement: Role analogy strategy

系统 SHALL 实现角色类比策略：根据风格邻接图，找到相邻风格中扮演"核心元素"角色的元素。核心元素定义为 `style.json` 中该风格的 `typical_colors` / `typical_decorations` / `typical_textures` 所匹配的元素。

#### Scenario: Cross-style core element discovery

- **WHEN** 目标风格为 "天然奢养"，邻接风格包括 "奢华克制"
- **THEN** 系统返回 "奢华克制" 的核心元素（如匹配 `typical_colors=["香槟金微光", "浅金色"]` 的颜色元素），每维度最多 5 个

#### Scenario: No adjacent styles defined

- **WHEN** 目标风格不在风格邻接图中
- **THEN** 该策略返回空列表，不报错

### Requirement: Cross-category transfer strategy

系统 SHALL 实现跨品类迁移策略：找到与目标元素 `signals` 有交集但 `product_category` 不同的元素。

#### Scenario: Signal overlap across categories

- **WHEN** 目标风格 signals 包含 "滋润" 且素材库中饮品品类元素的 signals 也包含 "滋润"
- **THEN** 系统返回该饮品元素作为跨品类候选

#### Scenario: All elements same category

- **WHEN** 素材库中所有元素属于同一 `product_category`
- **THEN** 该策略返回空列表

### Requirement: Trend frontier strategy

系统 SHALL 实现趋势前沿策略：返回 `maturity` 为 "上升" 或 "实验性" 的元素，不限风格，按 maturity 优先级排序（实验性 > 上升）。

#### Scenario: Experimental elements prioritized

- **WHEN** 素材库中存在 maturity="实验性" 和 maturity="上升" 的元素
- **THEN** 实验性元素排在上升元素之前

#### Scenario: No non-mainstream elements

- **WHEN** 素材库中所有元素 maturity="主流"
- **THEN** 该策略返回空列表

### Requirement: Strategies return deduplicated candidates

每个策略返回的候选元素列表 SHALL 不包含重复 element ID。跨策略的候选可以重复（同一个元素可能被多个策略选中）。

#### Scenario: Same element matched by multiple keywords

- **WHEN** 一个元素的 visual_keywords 同时包含用户的多个关键词
- **THEN** 该元素在直觉匹配策略结果中只出现一次，重叠度计为匹配的关键词数量

### Requirement: All strategies handle empty material library gracefully

当素材库某个维度的 JSON 文件为空或不存在时，所有策略 SHALL 返回空列表而不抛出异常。

#### Scenario: Missing dimension file

- **WHEN** `material_library/decoration.json` 不存在
- **THEN** 所有策略对装饰维度返回空列表，其他维度正常运行
