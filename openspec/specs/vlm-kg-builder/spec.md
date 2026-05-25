## ADDED Requirements

### Requirement: VLM 闭集分类 Prompt
系统 SHALL 构造闭集分类 prompt，将素材列表以结构化格式传入 VLM，要求 VLM 从中选出与图片视觉特征匹配的素材 id。

#### Scenario: Prompt 包含完整维度素材列表
- **WHEN** 对某张图片执行颜色维度匹配
- **THEN** prompt 中 SHALL 包含该维度全部素材的 `id`、`name`、`visual_keywords`（前10个），以及明确指令"仅分析图片中产品内容物（液体/膏体/颗粒等）的视觉特征，忽略包装外观"

#### Scenario: 结构化输出约束
- **WHEN** VLM 返回匹配结果
- **THEN** 系统 SHALL 通过 `model.with_structured_output(DimensionMatches)` 强制返回 `{"matched_material_ids": ["id1", "id2", ...]}` 格式，只含有效的素材 id

#### Scenario: VLM 返回空匹配
- **WHEN** VLM 判断图片中没有与该维度任何素材匹配的视觉特征
- **THEN** `matched_material_ids` SHALL 为空列表 `[]`，系统正常处理（不视为错误）

### Requirement: 三次投票取交集
系统 SHALL 对每张图片的每个维度以 temperature=0.7 运行 VLM 三次，取三次结果的交集作为最终匹配集。

#### Scenario: 三次完全一致
- **WHEN** 某素材 id 在三次 VLM 调用结果中均出现
- **THEN** 该素材 id SHALL 进入最终匹配集，触发边创建

#### Scenario: 三次不完全一致
- **WHEN** 某素材 id 仅在一次或两次调用结果中出现
- **THEN** 该素材 id SHALL NOT 进入最终匹配集

#### Scenario: Temperature 设置
- **WHEN** 执行任意一次 VLM 调用
- **THEN** 系统 SHALL 使用 temperature=0.7，保证三次调用间存在采样差异

### Requirement: 断点续传
系统 SHALL 支持中断后从断点恢复，避免重复处理已完成的图片。

#### Scenario: 已处理图片跳过
- **WHEN** KG builder 运行时某张图片已在 Neo4j 中存在，且其所有待处理维度均已完成投票（即该图片与当前批次全部素材的匹配关系均已写入）
- **THEN** 系统 SHALL 跳过该图片，不再调用 VLM

#### Scenario: 部分完成图片继续处理
- **WHEN** 某张图片已完成颜色维度但质地/装饰尚未处理
- **THEN** 系统 SHALL 仅对未完成的维度继续运行 VLM

### Requirement: 增量更新（新图片 × 新素材）
当 reports 和 material_library 同步更新时，系统 SHALL 仅对新图片与所有素材（含新旧）建立匹配，无需重新处理已有图片与已有素材之间的关系。

#### Scenario: 检测新图片
- **WHEN** KG builder 运行时
- **THEN** 系统 SHALL 查询 Neo4j 中已存在的 Image 节点 path 列表，仅对 `reports/*/images/` 中尚未入图的图片执行 VLM 匹配

#### Scenario: 新图片对全量素材匹配
- **WHEN** 检测到新图片（未在 Neo4j 中）
- **THEN** 系统 SHALL 对该图片与当前 material_library 中**全部**素材（含本批新增素材）执行三投票匹配，确保新图片能连接到新旧素材

#### Scenario: 旧图片不重新处理
- **WHEN** 某图片 path 已存在于 Neo4j 中
- **THEN** 系统 SHALL 跳过该图片，不重新运行 VLM（即使 material_library 新增了素材）

### Requirement: Nano Banana VLM 认证
系统 SHALL 通过 `NANO_BANANA_URL` 环境变量调用 nano banana VLM，使用 OpenAI 兼容接口。

#### Scenario: 使用 NANO_BANANA_URL 调用 VLM
- **WHEN** VLM 客户端初始化时
- **THEN** 系统 SHALL 读取 `NANO_BANANA_URL` 环境变量作为 base_url，使用 OpenAI 兼容客户端（`openai.AsyncOpenAI(base_url=NANO_BANANA_URL)`）发起调用

#### Scenario: NANO_BANANA_URL 未配置时报错
- **WHEN** `NANO_BANANA_URL` 环境变量未设置或为空
- **THEN** 系统 SHALL 抛出 informative error，提示用户配置该变量

### Requirement: Neo4j 连接配置
系统 SHALL 从环境变量读取 Neo4j 连接信息，不硬编码。

#### Scenario: 环境变量配置
- **WHEN** KG builder 初始化 Neo4j 连接
- **THEN** 系统 SHALL 读取 `NEO4J_URI`（默认 `bolt://localhost:7687`）、`NEO4J_USER`（默认 `neo4j`）、`NEO4J_PASSWORD` 三个环境变量

#### Scenario: 连接失败时报错
- **WHEN** Neo4j 连接无法建立
- **THEN** 系统 SHALL 抛出包含 `NEO4J_URI` 值的 informative error，提示用户检查 Neo4j 是否运行
