## Context

`reports/` 目录包含 3 份中文趋势报告（饮料、洗发水、面部精华），每份约 800-900 行 Markdown 叙事文本。报告按「颜色→装饰→纹理/透明度」章节组织，每个趋势项包含表现特征、典型场景、适用品类、驱动因素。

当前状态：报告是人类可读的散文，无法被下游 AI 直接消费来生成设计方案。需要一个结构化提取层，将叙事文本拆解为 JSON 元素卡片。

下游消费者：另一个 AI 系统，负责根据素材库中的元素组合生成产品设计方案。

## Goals / Non-Goals

**Goals:**
- 从现有 3 份报告中提取结构化设计元素，输出为 JSON
- 定义标准化元素卡片 schema，支持跨品类比较和组合推理
- 提供增量更新能力：新报告加入后只处理增量
- 输出对下游 AI 友好：机器可解析、语义丰富、包含组合性线索

**Non-Goals:**
- 不修改现有 agent pipeline（Scope/Research/Write）
- 不构建 UI 或可视化
- 不实现下游「设计方案生成」AI
- 不处理非 Markdown 报告格式

## Decisions

### Decision 1: 后处理提取（方案 A）而非修改报告生成流程

**选择**: 独立提取脚本，读取已生成的 `.md` 报告，通过 LLM 提取为 JSON。

**替代方案**: 修改 deep research agent 的 Write 阶段，在生成报告时同步输出结构化数据。

**理由**:
- 3 份现有报告已存在，需要立即处理
- 不影响现有 agent pipeline 稳定性
- 解耦关注点：报告生成专注叙事质量，素材提取专注结构化精度

### Decision 2: 提取脚本作为独立 Python 脚本，不集成到 LangGraph

**选择**: `scripts/extract_material_library.py`，可通过 `uv run python scripts/extract_material_library.py` 执行。

**替代方案**: 作为 LangGraph subgraph 集成到现有 pipeline。

**理由**:
- 提取是离线批处理，不需要 agent 状态管理
- 独立脚本更容易调试和手动触发
- 复用现有 `init_chat_model` + `GenAIToken` 认证模式即可

### Decision 3: Aesthetic Persona 作为组合性引擎

**选择**: 每个元素卡片标注 `aesthetic_persona`（如"科技净澈""天然奢养"），下游 AI 通过 persona 匹配判断组合兼容性。

**替代方案**: 显式枚举所有有效组合对。

**理由**:
- 避免组合爆炸（3 维度 × 多元素 = 大量组合）
- 报告数据已隐含 persona 映射（精华报告 §5 明确了「如何传达高端/功效/科技/天然/稀缺感」）
- 下游 AI 可基于 persona 距离做灵活推理

### Decision 4: 透明度维度扩展为「透明度+质地」

**选择**: 第三维度覆盖通透性、黏度、流动性、光泽、表面状态。

**理由**: 报告中「透明度」和「纹理/质地」高度交织（如凝胶感、浆感、丝缎流动），拆分会导致信息割裂，合并更符合设计思维。

### Decision 5: LLM 结构化输出使用 Pydantic schema

**选择**: 定义 Pydantic `BaseModel` 作为 LLM `with_structured_output()` 的 schema，确保提取结果类型安全。

**模型类**:
```python
class MaterialElement(BaseModel):
    id: str                          # e.g. "serum-color-001"
    dimension: Literal["颜色", "装饰物", "透明度与质地"]
    name: str                        # e.g. "浅琥珀 / 蜂蜜金"
    name_en: str                     # English name
    visual_keywords: list[str]       # Scannable visual descriptors
    aesthetic_persona: str           # e.g. "科技净澈"
    signals: list[str]               # What this element communicates
    maturity: Literal["主流", "上升", "实验性"]
    year_range: str                  # e.g. "2025-2026"
    typical_use: str                 # Typical product/usage context
    source_section: str              # Report section reference

class ReportExtraction(BaseModel):
    source_report: str
    product_category: str
    extraction_date: str
    elements: list[MaterialElement]
```

### Decision 6: 输出目录结构

```
material_library/
├── index.json              # 全局元数据 + 处理记录
├── beverage.json           # 饮料报告提取结果
├── shampoo.json            # 洗发水报告提取结果
├── serum.json              # 精华报告提取结果
└── cross_reference.json    # 跨品类汇总（按维度 + 成熟度组织，含组合建议）
```

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| LLM 提取不完整（遗漏元素） | 提取后对比报告章节数量，人工抽查验证；prompt 明确要求覆盖所有趋势项 |
| LLM 输出 schema 不一致 | 使用 `with_structured_output()` 强制 Pydantic schema；失败时重试 |
| 报告格式变化导致提取失败 | 提取 prompt 基于内容语义而非硬编码格式；graceful degradation |
| Aesthetic persona 标签不一致 | 在 prompt 中提供预定义 persona 列表，LLM 从中选择 |
| 大报告超出 context window | 每份报告约 800-900 行，中文约 15k-20k tokens，在 GPT-4o/Claude 的 context 内 |

## Integration Points

- **认证**: 复用 `src/deep_research_from_scratch/Helper.py` 中的 `GenAIToken`
- **LLM 调用**: 复用 `init_chat_model("azure_openai:...")` 模式
- **环境变量**: 复用现有 `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT` 等
- **不影响**: notebooks、src/ 源文件、langgraph.json、现有 agent 状态
