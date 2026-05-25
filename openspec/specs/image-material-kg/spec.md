## ADDED Requirements

### Requirement: Neo4j Image 节点
系统 SHALL 在 Neo4j 中为 `reports/*/images/` 下的每张图片创建一个 `(:Image)` 节点，包含完整元数据。

#### Scenario: Image 节点创建
- **WHEN** KG builder 初始化时
- **THEN** 系统 SHALL 为 275 张图片各创建一个 `(:Image)` 节点，包含属性：`path`（绝对路径）、`description`（中文描述）、`report_id`（所属报告 UUID）、`filename`（文件名）

#### Scenario: 重复运行幂等性
- **WHEN** KG builder 对已存在的图片再次运行
- **THEN** 系统 SHALL 使用 `MERGE` 而非 `CREATE`，不产生重复节点（以 `path` 作为唯一键）

### Requirement: Neo4j Material 节点
系统 SHALL 为 `material_library/color.json`、`texture.json`、`decoration.json` 中的每个素材元素创建一个 `(:Material)` 节点。

#### Scenario: Material 节点创建
- **WHEN** KG builder 初始化时
- **THEN** 系统 SHALL 为 107 个素材各创建一个 `(:Material)` 节点，包含属性：`id`、`name`、`name_en`、`dimension`（"颜色"/"透明度与质地"/"装饰物"）、`visual_keywords`（列表）、`signals`（列表）、`typical_use`、`product_category`

#### Scenario: 重复运行幂等性
- **WHEN** KG builder 对已存在的素材再次运行
- **THEN** 系统 SHALL 使用 `MERGE`，以 `id` 作为唯一键，不产生重复节点

### Requirement: 图片↔素材关系边
系统 SHALL 基于 VLM 三投票结果在图片节点与素材节点之间建立有向关系边。

#### Scenario: 颜色维度边创建
- **WHEN** VLM 对某张图片在颜色维度连续三次均返回同一素材 id
- **THEN** 系统 SHALL 建立 `(:Image)-[:HAS_COLOR]->(:Material)` 关系

#### Scenario: 质地维度边创建
- **WHEN** VLM 对某张图片在质地维度连续三次均返回同一素材 id
- **THEN** 系统 SHALL 建立 `(:Image)-[:HAS_TEXTURE]->(:Material)` 关系

#### Scenario: 装饰物维度边创建
- **WHEN** VLM 对某张图片在装饰物维度连续三次均返回同一素材 id
- **THEN** 系统 SHALL 建立 `(:Image)-[:HAS_DECORATION]->(:Material)` 关系

#### Scenario: 不一致匹配不建边
- **WHEN** VLM 对某张图片在某维度的三次调用结果不完全一致（即某素材未在三次中均出现）
- **THEN** 系统 SHALL NOT 为该图片-素材对建立任何关系边

#### Scenario: 无匹配时不建边
- **WHEN** VLM 判断某张图片与某维度所有素材均不匹配，或三次投票无一致结果
- **THEN** 该图片在该维度无出边，系统 SHALL NOT 强制建立关系

### Requirement: Neo4j 唯一约束索引
系统 SHALL 在 Neo4j 中创建唯一约束以保证数据完整性。

#### Scenario: 约束初始化
- **WHEN** KG builder 首次连接 Neo4j 时
- **THEN** 系统 SHALL 执行：`CREATE CONSTRAINT IF NOT EXISTS FOR (i:Image) REQUIRE i.path IS UNIQUE` 和 `CREATE CONSTRAINT IF NOT EXISTS FOR (m:Material) REQUIRE m.id IS UNIQUE`
