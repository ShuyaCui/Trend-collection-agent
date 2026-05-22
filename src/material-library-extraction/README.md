# Material Library Extraction

从趋势报告中提取结构化设计元素卡片，供下游 AI 系统消费以生成产品设计方案。

---

## 目录结构

```
material-library-extraction/
├── extract_material_library.py  # 主提取脚本（CLI 入口）
└── material_schema.py           # Pydantic 数据模型定义

material_library/                # 输出目录（项目根目录）
├── index.json                   # 全局元数据 + 各报告处理记录
├── color.json                   # 颜色维度元素
├── decoration.json              # 装饰物维度元素
├── texture.json                 # 透明度与质地维度元素
└── .cache/                      # 每份报告的原始提取结果缓存（支持增量更新）
```

---

## 元素卡片 Schema

每个 `MaterialElement` 包含以下字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | str | 确定性 ID（`{品类slug}-{维度en}-{名称slug}-{hash6}`） |
| `dimension` | enum | `颜色` / `装饰物` / `透明度与质地` |
| `name` | str | 中文名称 |
| `name_en` | str | 英文名称 |
| `trend_time` | str | 趋势时间范围，从报告标题提取（如 `2025年11月—2026年5月`） |
| `visual_keywords` | list[str] | 可视化描述关键词（3–8 项，合并后超 20 项按 embedding 相似度截断） |
| `signals` | list[str] | 向消费者传达的信息（2–5 项，同上截断规则） |
| `typical_use` | str | 典型使用场景 |
| `source_section` | str | 报告中的章节编号（如 `§4.1`） |
| `source_heading` | str | 报告中的原始章节标题文本 |
| `source_report` | str | 来源报告标识（嵌套格式为 `{uuid}/report.md`，合并后多个用 ` + ` 拼接） |
| `product_category` | str | 产品品类，由 LLM 从报告标题提取（如 `面部精华`、`饮品`、`身体护理`） |

---

## 提取架构

### 整体流程

```
reports/{uuid}/report.md
        │
        ▼
1. _extract_report_metadata()   — 1 次 LLM 调用，从报告标题提取 product_category + trend_time
        │
        ▼
2. 按 H2/H3 章节切块（breadcrumb 上下文拼接）
        │
        ├─ chunk 1 → _THREE_DIM_EXTRACTION_PROMPT → ThreeDimExtraction
        ├─ chunk 2 → ...
        └─ chunk N → ...
        │
        ▼
3. 精确名称去重（_deduplicate_elements）
   — 同一 (dimension, name) 跨报告合并；union visual_keywords/signals；拼接 source_report
        │
        ▼
4. 语义去重（_semantic_deduplicate_elements，可用 --no-semantic-dedup 跳过）
   — 在每个维度内，对 composite string（name + visual_keywords[:10]）做 embedding 相似度
   — 余弦相似度 > 0.7 的元素用 Union-Find 聚类后合并
        │
        ▼
5. 关键词截断（_trim_by_similarity，在 _merge_group 内）
   — visual_keywords 或 signals 超过 20 项时，按对主题 embedding 相似度保留 top-20
        │
        ▼
6. 写入 color.json / decoration.json / texture.json + index.json
```

### 关键设计决策

**单轮三维度提取**：一次 LLM 调用同时提取颜色、装饰物、透明度与质地三个维度。每个元素自主声明所属维度，prompt 包含互斥分类规则，从根源上避免同一概念被重复分配到多个维度。

**Structured Output**：使用 `model.with_structured_output(ThreeDimExtraction)` 强制 LLM 输出符合 Pydantic schema 的 JSON，所有枚举字段在 schema 层校验。

**品类与时间自动推断**：每份报告调用一次 LLM，从标题前 300 字符提取 `product_category` 和 `trend_time`，无需维护关键词映射表。

**Azure AD Token 自动刷新**：使用 `azure_ad_token_provider=lambda: GenAIToken().token()` 而非静态 `api_key`，LangChain 在每次 HTTP 请求前调用 lambda，自动处理长时间运行时的 token 过期。

**增量缓存**：每份报告的提取结果缓存在 `.cache/{uuid}.json`（`ReportExtraction` schema）。`schema_version` 字段追踪 schema 版本，版本不匹配时自动重新提取。

---

## 运行方式

### 环境变量

```bash
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_DEPLOYMENT=...          # 聊天模型，默认 GPT-54-2026-03-05
AZURE_OPENAI_API_VERSION=...
HEADERS_PROJECT_NAME=...
HEADERS_USERID=...
TAVILY_API_KEY=...                   # 暂未使用，备用
```

### 报告目录结构

报告需放在 `reports/` 的子目录中，目录名为唯一 ID（推荐 UUID）：

```
reports/
├── e602b08d-bcdd-452c-95d0-823ae66e19e3/
│   └── report.md
└── e9f1f27f-2779-4214-82a4-fa5c64f36343/
    └── report.md
```

### 常用命令

```bash
# 增量提取（只处理新报告，已处理的自动跳过）
uv run python src/material-library-extraction/extract_material_library.py

# 强制全量重新提取（忽略缓存）
uv run python src/material-library-extraction/extract_material_library.py --force

# 迁移缓存（修改了 schema 字段但不需要重新提取内容时使用）
# 每份报告只调用 1 次 LLM，用于更新 product_category / trend_time 等元数据字段
uv run python src/material-library-extraction/extract_material_library.py --migrate-cache

# 纯重建（无 LLM，从缓存重新合并/去重/写入 JSON）
# 适用于调整合并逻辑、去重阈值等不影响原始提取的变更
uv run python src/material-library-extraction/extract_material_library.py --rebuild-only

# 跳过语义去重（仅精确名称去重，速度更快）
uv run python src/material-library-extraction/extract_material_library.py --no-semantic-dedup

# 自定义参数
uv run python src/material-library-extraction/extract_material_library.py \
  --reports-dir reports/ \
  --output-dir material_library/ \
  --model azure_openai:GPT-55-2026-04-24
```

### 手动修改库文件后更新 index.json

当手工编辑 `color.json` / `decoration.json` / `texture.json`（如删除若干元素）后，
运行以下命令重新计算各维度元素数量并写回 `index.json`：

```bash
# 同步 index.json 的元素统计（不调用 LLM，不修改库文件本身）
uv run python src/material-library-extraction/update_index.py

# 指定自定义输出目录
uv run python src/material-library-extraction/update_index.py --output-dir material_library/
```

### 何时使用哪种命令

| 场景 | 命令 |
|---|---|
| 新增报告 | 默认（增量，自动跳过已处理） |
| 修改了提取 prompt 或 schema | `--force` |
| 只修改了元数据字段（如新增 `trend_time`） | `--migrate-cache` |
| 只调整了合并/去重逻辑 | `--rebuild-only` |
| 调试时想跳过耗时的 embedding 去重 | `--no-semantic-dedup` |
| 手动删改库文件后同步 index.json | `update_index.py` |

---

## Schema 版本管理

`material_schema.py` 中的 `EXTRACTION_SCHEMA_VERSION` 控制缓存兼容性：

- **字段移除/新增（需重新提取内容）**：bump schema version → 旧缓存自动失效，触发全量重提取
- **字段移除/新增（元数据类，无需重新提取）**：用 `--migrate-cache` 原地修补，无需 bump version
- **合并/去重逻辑变更**：用 `--rebuild-only` 重建，无需重提取也无需 bump version
