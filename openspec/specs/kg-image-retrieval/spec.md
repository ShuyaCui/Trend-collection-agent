## ADDED Requirements

### Requirement: 按素材检索代表图片
系统 SHALL 提供 Python 函数，给定素材 id 或素材名称，返回所有与该素材相连的图片列表。

#### Scenario: 按 material_id 检索
- **WHEN** 调用 `get_images_for_material(material_id="25fccecd-color-90b96051-26da05")`
- **THEN** 系统 SHALL 执行 Cypher `MATCH (i:Image)-[]->(m:Material {id: $id}) RETURN i` 并返回图片节点属性列表（含 `path`、`description`、`report_id`、`filename`）

#### Scenario: 按 material_name 检索
- **WHEN** 调用 `get_images_for_material(material_name="低饱和香氛色")`
- **THEN** 系统 SHALL 执行按 `name` 属性的匹配查询，返回相同格式的图片列表

#### Scenario: 无匹配时返回空列表
- **WHEN** 给定素材无任何图片与之相连
- **THEN** 函数 SHALL 返回空列表 `[]`，不抛出异常

### Requirement: 按维度过滤检索
系统 SHALL 支持仅通过特定关系类型（颜色/质地/装饰）检索图片。

#### Scenario: 仅查颜色关系
- **WHEN** 调用 `get_images_for_material(material_id="...", relation="HAS_COLOR")`
- **THEN** 系统 SHALL 仅返回通过 `[:HAS_COLOR]` 关系连接的图片

#### Scenario: 查全部关系（默认）
- **WHEN** 调用 `get_images_for_material(material_id="...")` 不指定 relation
- **THEN** 系统 SHALL 返回通过任意关系（HAS_COLOR、HAS_TEXTURE、HAS_DECORATION）连接的图片

### Requirement: 按报告过滤
系统 SHALL 支持按 report_id 过滤检索结果。

#### Scenario: 按 report 过滤
- **WHEN** 调用 `get_images_for_material(material_id="...", report_id="e602b08d-...")`
- **THEN** 系统 SHALL 仅返回属于该报告的图片

### Requirement: 素材统计查询
系统 SHALL 提供统计接口，支持查询各素材的代表图片数量。

#### Scenario: 素材图片计数
- **WHEN** 调用 `get_material_image_counts(dimension="颜色")`
- **THEN** 系统 SHALL 返回该维度所有素材的 `{material_name: image_count}` 字典，按 count 降序排列

#### Scenario: 全维度统计
- **WHEN** 调用 `get_material_image_counts()` 不指定维度
- **THEN** 系统 SHALL 返回全部 107 个素材的图片计数
