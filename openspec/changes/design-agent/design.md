## Context

素材库（`material_library/`）包含约 150 个结构化设计元素，按维度（颜色/装饰/质地/风格）和成熟度（主流/上升/实验性）组织。报告目录（`reports/*/images/`）包含约 100 张带描述的参考图（`images_metadata.json`）。

当前没有任何检索工具。设计师必须手动翻阅 JSON 文件来寻找灵感元素和参考图。

本设计新增一个 Design Agent，采用 **多策略并行检索 + LLM 策展** 架构，将自然语言查询转化为按维度组织的元素推荐 + 参考图。

### 与现有系统的集成点

- **`material_library/*.json`**: 只读数据源，schema 不变
- **`reports/*/images/images_metadata.json`**: 只读图片索引
- **`Helper.py → GenAIToken`**: 复用 Azure OpenAI 认证
- **`notebooks/` 工作流**: 遵循 `%%writefile` 模式生成 `src/` 文件

## Goals / Non-Goals

**Goals:**

- 设计师通过自然语言描述设计意图，获得按维度（颜色/装饰/质地）分别推荐的元素列表
- 每个推荐元素附带 N 张参考图（默认 3）
- 推荐结果既包含直觉匹配的安全选择，也包含有创意启发价值的跨界元素
- CLI 可用，输出结构化（JSON + 终端格式化），为后续 UI 留接口

**Non-Goals:**

- 不构建 Web UI
- 不使用向量数据库或 embedding 模型（Phase 1）
- 不修改现有素材库 schema
- 不生成 moodboard 拼图

## Decisions

### Decision 1: 多策略并行检索 vs 单一相似度排序

**选择**: 多策略并行

**理由**: 单一相似度函数（无论是关键词、embedding 还是 LLM 打分）只能在一个维度上排序，产出的结果从"很像"到"有点像"渐变，缺乏创意惊喜。多策略架构让每种策略用不同的创意逻辑独立产生候选，确保结果包含不同思维角度的元素。

**备选**: embedding cosine similarity 全排序。放弃原因：Phase 1 不引入向量基础设施，且单一排序无法提供结构化的创意发散。

### Decision 2: 四种检索策略选型

| 策略 | 逻辑 | 创意来源 |
|------|------|---------|
| **直觉匹配** | `aesthetic_style == target` + `visual_keywords` 重叠 | 安全基线 |
| **角色类比** | 其他风格中扮演相同角色（核心色/核心质地）的元素 | 跨风格嫁接 |
| **跨品类迁移** | 不同 `product_category` 但 `signals` 有交集的元素 | 饮品→护肤翻译 |
| **趋势前沿** | `maturity ∈ ["上升", "实验性"]`，不限风格 | 时间维度机会 |

**为什么不是更多策略**: 场景联想、互补配对、属性反转等策略在 v1 中省略。理由：当前素材库约 150 个元素，4 个策略已经能充分覆盖候选池。后续可按需扩展。

### Decision 3: 策略层做粗过滤，LLM 做精排策展

**选择**: 策略层用确定性逻辑（字段过滤 + 关键词子串匹配）产生候选池（每策略每维度 top-5），然后将候选池交给 LLM 做最终推荐。

**理由**:
- 确定性过滤快速、可调试、不消耗 token
- LLM 擅长语义理解和跨元素比较，适合从 ~20 个候选中选 3 个
- 两阶段分离后可以独立优化（换 LLM 不影响策略，加策略不影响策展）

**备选**: 全 LLM 方案（把 150 个元素全塞给 LLM）。放弃原因：token 浪费，且 LLM 在长列表上排序不稳定。

### Decision 4: 参考图匹配方式

**选择**: 关键词匹配（element.visual_keywords ∩ image.description 子串匹配）

**理由**: `images_metadata.json` 中的 description 字段已经包含丰富的视觉描述（颜色、质地、品牌等），关键词子串匹配能覆盖大部分场景。~100 张图，不需要向量搜索。

**备选**: LLM 判断相关性。放弃原因：每个元素对每张图做一次 LLM 调用开销过大。

### Decision 5: LLM 调用结构化输出

查询解析和策展都使用 Pydantic `model.with_structured_output()` 确保输出可靠：

```python
class ParsedQuery(BaseModel):
    """LLM 解析用户自然语言输入后的结构化查询。"""
    target_style: str | None  # 目标风格，可能为 None
    color_keywords: list[str]
    decoration_keywords: list[str]
    texture_keywords: list[str]
    product_context: str  # 产品类型

class DimensionRecommendation(BaseModel):
    """单个维度的推荐结果。"""
    element_id: str
    element_name: str
    strategy: str  # 来自哪个策略
    reason: str  # 一句话推荐理由

class CurationResult(BaseModel):
    """LLM 策展的完整输出。"""
    colors: list[DimensionRecommendation]
    decorations: list[DimensionRecommendation]
    textures: list[DimensionRecommendation]
```

### Decision 6: 风格邻接图

角色类比策略需要一个风格邻接图来确定"其他风格"的范围。硬编码为 Python dict：

```python
STYLE_ADJACENCY = {
    "科技净澈": ["奢华克制", "可视科技"],
    "天然奢养": ["奢华克制", "自然清体", "感官甜品"],
    "奢华克制": ["科技净澈", "天然奢养"],
    "感官甜品": ["天然奢养", "自然清体"],
    "自然清体": ["天然奢养", "感官甜品"],
    "可视科技": ["科技净澈"],
}
```

## Risks / Trade-offs

- **[关键词匹配召回率有限]** → 子串匹配可能漏掉语义相近但用词不同的元素（如"琥珀"vs"蜂蜜金"）。Phase 1 可接受；Phase 2 迁移到 embedding 可解决。
- **[LLM 策展结果不稳定]** → temperature=0 + structured output 减少波动；但不同次运行可能推荐不同元素。可接受，因为设计探索本身就期望多样性。
- **[图片匹配质量]** → 部分图片的 description 为空（e602 报告中 48/55 张），会导致这些图片永远匹配不到。后续需补全描述。
- **[素材库规模小]** → 150 个元素 + 100 张图，某些风格/维度组合可能只有 2-3 个候选。策略可能返回空结果。LLM 策展层需要处理候选不足的情况。

## Open Questions

- 是否需要支持多轮对话（用户先选颜色，再基于已选颜色推荐装饰）？当前设计为单轮查询。
- 后续 Phase 2 是否从关键词匹配直接升级到 embedding，还是中间加一步 BM25？
