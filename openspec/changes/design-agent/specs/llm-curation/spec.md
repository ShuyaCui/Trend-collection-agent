## ADDED Requirements

### Requirement: Query parsing with structured output

系统 SHALL 使用 LLM + Pydantic structured output 将用户自然语言输入解析为 `ParsedQuery` 对象，包含 `target_style`、`color_keywords`、`decoration_keywords`、`texture_keywords`、`product_context` 字段。

#### Scenario: Full natural language input

- **WHEN** 用户输入 "天然奢养风格的沐浴露"
- **THEN** 解析结果为 `target_style="天然奢养"`, `product_context="沐浴露"`，并从风格定义中填充对应维度的关键词

#### Scenario: Keywords only without explicit style

- **WHEN** 用户输入 "蜂蜜色半透明有油珠的液体"
- **THEN** `target_style` 为 None 或 LLM 推断最接近的风格，`color_keywords=["蜂蜜色", "半透明"]`，`decoration_keywords=["油珠"]`

### Requirement: LLM curation from candidate pool

系统 SHALL 将多策略产生的候选池和用户查询一起提交给 LLM，由 LLM 为每个维度（颜色/装饰/质地）选出 N 个最有价值的推荐元素（默认 N=3），输出为 `CurationResult` structured output。

#### Scenario: Sufficient candidates

- **WHEN** 候选池中颜色维度有 12 个候选
- **THEN** LLM 从中选出 3 个颜色推荐，每个包含 `element_id`、`element_name`、`strategy`（来源策略名称）

#### Scenario: Insufficient candidates

- **WHEN** 某维度候选总数少于 N
- **THEN** LLM 返回该维度所有候选作为推荐，不补充虚构元素

### Requirement: Reference image matching

系统 SHALL 为每个推荐元素匹配 M 张参考图（默认 M=3）。匹配方式为：用元素的 `visual_keywords` 在所有 `images_metadata.json` 的 `description` 字段中做子串匹配，按匹配关键词数量排序取 top-M。

#### Scenario: Images found for element

- **WHEN** 元素 visual_keywords=["蜂蜜色", "金色", "温润油感"]，图片描述中包含 "金色" 子串的图片有 5 张
- **THEN** 返回匹配度最高的 3 张图片，每张包含 `local_path` 和 `description`

#### Scenario: No images match

- **WHEN** 元素的 visual_keywords 在所有图片描述中无子串匹配
- **THEN** 该元素的参考图列表为空

#### Scenario: Images with empty description

- **WHEN** 某张图片的 description 为空字符串
- **THEN** 该图片不参与关键词匹配（不会被任何元素匹配到）

### Requirement: Curation prompt includes strategy provenance

策展 prompt SHALL 向 LLM 标注每个候选元素来自哪个策略（直觉匹配/角色类比/跨品类迁移/趋势前沿），使 LLM 在选择时能考虑策略多样性。

#### Scenario: LLM sees strategy labels

- **WHEN** 候选池提交给 LLM
- **THEN** 每个候选标注其来源策略名称，LLM 的推荐结果中 `strategy` 字段反映实际来源
