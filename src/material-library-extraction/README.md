# Material Library

结构化素材库，从趋势报告中提取设计元素卡片，供下游 AI 系统消费以生成产品设计方案。

## 目录结构

```
material_library/
├── index.json       # 全局元数据 + 处理记录
├── color.json       # 颜色维度：所有品类的颜色元素，按成熟度分组
├── decoration.json  # 装饰物维度：所有品类的装饰物元素，按成熟度分组
├── texture.json     # 透明度与质地维度：所有品类的元素，按成熟度分组
├── style.json    # Aesthetic style 目录
├── .cache/          # 每份报告的原始提取结果缓存（支持增量更新）
└── README.md
```

## 元素卡片 Schema

每个元素包含以下字段：

| 字段 | 说明 |
|------|------|
| `id` | 确定性 ID（基于品类+维度+名称+来源的哈希） |
| `dimension` | 颜色 / 装饰物 / 透明度与质地 |
| `name` | 中文名称 |
| `name_en` | 英文名称 |
| `visual_keywords` | 可视化描述关键词（3-8项） |
| `aesthetic_style` | 美学风格：科技净澈/天然奢养/奢华克制/感官甜品/自然清体/可视科技 |
| `signals` | 向消费者传达的信息（2-5项） |
| `maturity` | 主流 / 上升 / 实验性 |
| `typical_use` | 典型使用场景 |
| `source_report` | 来源报告文件名 |
| `product_category` | 产品品类（饮料/洗发水/面部精华） |

## 使用方法

### 首次提取

```bash
uv run python src/material-library-extraction/extract_material_library.py
```

### 增量更新（新增报告后）

```bash
# 将新报告放入 reports/ 目录，然后运行：
uv run python src/material-library-extraction/extract_material_library.py
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

## Aesthetic Style 体系

下游 AI 通过 style 匹配判断元素组合兼容性：

| Style | 典型颜色 | 典型装饰 | 典型质地 |
|---------|---------|---------|---------|
| 科技净澈 | 无色透明、冷感透明 | 微囊悬浮、双相结构 | 高折光水感、液晶反光 |
| 天然奢养 | 浅琥珀、蜂蜜金 | 油珠悬浮、双相分层 | 丝缎油感、半透明柔光 |
| 奢华克制 | 香槟微金、乳白半透明 | 细微珠光、精致油珠 | 丝缎光泽、柔润内发光 |
| 感官甜品 | 奶白、焦糖色 | 奶盖、拉花、顶部碎料 | 绵密厚乳、慕斯感 |
| 自然清体 | 植物绿、番茄红 | 纤维悬浮、浆感痕迹 | 浆感浑浊、纤维感 |
| 可视科技 | 冷感透明、冰透感 | 肉眼可见微囊、悬浮珠粒 | 凝胶结构感、冻感流体 |
