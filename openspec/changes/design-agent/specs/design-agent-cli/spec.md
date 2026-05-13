## ADDED Requirements

### Requirement: CLI accepts natural language query

`design_agent.py` SHALL 接受一个位置参数作为自然语言查询字符串，并可选参数 `--top-n`（每维度推荐数量，默认 3）和 `--images-per-element`（每元素参考图数量，默认 3）。

#### Scenario: Basic invocation

- **WHEN** 用户运行 `python notebooks/design_agent.py "天然奢养风格的沐浴露"`
- **THEN** 系统输出按维度（颜色/装饰/质地）组织的推荐元素列表，每个元素附带参考图路径

#### Scenario: Custom parameters

- **WHEN** 用户运行 `python notebooks/design_agent.py "清爽夏日磨砂" --top-n 5 --images-per-element 2`
- **THEN** 每维度推荐 5 个元素，每元素附带 2 张参考图

### Requirement: Output format per dimension

CLI SHALL 按维度分别输出推荐结果。每个推荐元素 SHALL 显示：元素名称（中英文）、来源策略、aesthetic_style、maturity、visual_keywords、以及匹配到的参考图路径列表。

#### Scenario: Terminal formatted output

- **WHEN** CLI 正常运行完成
- **THEN** 终端输出包含三个维度区块（颜色/装饰/质地），每个区块下列出推荐元素和参考图

### Requirement: JSON output mode

CLI SHALL 支持 `--json` 参数，输出完整推荐结果的 JSON 格式，结构为 `{"colors": [...], "decorations": [...], "textures": [...]}`, 每个元素对象包含完整元素字段和 `matched_images` 列表。

#### Scenario: JSON output

- **WHEN** 用户运行 `python notebooks/design_agent.py "天然奢养" --json`
- **THEN** 系统输出有效 JSON 到 stdout，可被 `jq` 或其他工具解析

### Requirement: Error handling for missing credentials

当 Azure OpenAI 环境变量未设置时，CLI SHALL 在启动时给出明确错误信息并退出（exit code 1），而不是在 LLM 调用时抛出未处理异常。

#### Scenario: Missing API credentials

- **WHEN** `AZURE_OPENAI_ENDPOINT` 未设置
- **THEN** CLI 输出 "Error: AZURE_OPENAI_ENDPOINT not set" 并退出

### Requirement: Script follows notebook workflow

`design_agent.py` SHALL 放在 `notebooks/` 目录下，通过 `%%writefile` 或直接作为独立脚本运行。脚本 SHALL 将 `src/` 目录加入 `sys.path` 以导入项目模块。

#### Scenario: Run from notebooks directory

- **WHEN** 用户在 `notebooks/` 目录下运行 `python design_agent.py "query"`
- **THEN** 脚本正确导入 `deep_research_from_scratch` 模块并执行
