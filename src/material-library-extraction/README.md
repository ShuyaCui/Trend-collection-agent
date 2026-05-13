# Material Library

结构化素材库，从趋势报告中提取设计元素卡片，供下游 AI 系统消费以生成产品设计方案。

## 目录结构

```
material_library/
├── index.json       # 全局元数据 + 处理记录
├── color.json       # 颜色维度：所有品类的颜色元素，按成熟度分组
├── decoration.json  # 装饰物维度：所有品类的装饰物元素，按成熟度分组
├── texture.json     # 透明度与质地维度：所有品类的元素，按成熟度分组
├── style.json       # 风格维度：报告中观察到的整体审美风格元素，按成熟度分组
├── .cache/          # 每份报告的原始提取结果缓存（支持增量更新）
└── README.md
```

## 提取架构

提取使用**两轮 LLM 调用**（每份报告）：

- **第一轮**：一次性提取「颜色」「装饰物」「透明度与质地」三个维度的所有元素。每个元素自主声明其主维度，prompt 包含互斥分类规则，从根源上避免同一概念被重复分配到多个维度。
- **第二轮**：单独提取「风格」维度，保留 `aesthetic_style = 元素名称` 的不变式。

旧架构（四轮 × 维度，依赖报告章节关键词切分）在报告章节名不含维度关键词时会将完整报告发给所有维度提取器，导致跨维度重复条目。新架构从根本上消除了这一问题。

**缓存兼容性**：`ReportExtraction.schema_version` 字段追踪提取 schema 版本。版本不匹配的缓存条目会自动触发重新提取，无需手动清除。

## 元素卡片 Schema

每个元素包含以下字段：

| 字段 | 说明 |
|------|------|
| `id` | 确定性 ID（基于品类+维度+名称+来源的哈希） |
| `dimension` | 颜色 / 装饰物 / 透明度与质地 / 风格 |
| `name` | 中文名称 |
| `name_en` | 英文名称 |
| `visual_keywords` | 可视化描述关键词（3-8项） |
| `aesthetic_style` | 美学风格：科技净澈/天然奢养/奢华克制/感官甜品/自然清体/可视科技 |
| `signals` | 向消费者传达的信息（2-5项） |
| `maturity` | 主流 / 上升 / 实验性 |
| `typical_use` | 典型使用场景 |
| `source_report` | 来源报告标识（嵌套格式为 `{uuid}/report.md`） |
| `product_category` | 产品品类（饮料/洗发水/面部精华） |

## 使用方法

### 首次提取

```bash
uv run python src/material-library-extraction/extract_material_library.py
```

### 增量更新（新增报告后）

报告需放在 `reports/` 的子目录中，目录名为唯一 ID（如 UUID）：

```
reports/
└── e602b08d-bcdd-452c-95d0-823ae66e19e3/
    ├── report.md
    └── images/
```

```bash
# 将新报告目录放入 reports/，然后运行：
uv run python src/material-library-extraction/extract_material_library.py   --reports-dir reports/
# 只会提取新文件，已处理的报告会跳过
```

### 强制全量重新提取

```bash
uv run python src/material-library-extraction/extract_material_library.py --force
```

### 自定义参数

```bash
uv run python src/material-library-extraction/extract_material_library.py \
  --reports-dir reports/ \
  --output-dir material_library/ \
  --model azure_openai:GPT-55-2026-04-24
```