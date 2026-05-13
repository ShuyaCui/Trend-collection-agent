## 1. Data Loading & Schema

- [ ] 1.1 Create `src/deep_research_from_scratch/design_agent/` package with `__init__.py`
- [ ] 1.2 Implement `data_loader.py`: `load_material_library()` 读取 color/decoration/texture/style JSON，返回按维度+成熟度组织的 dict；`load_image_metadata()` 扫描所有 `reports/*/images/images_metadata.json` 并合并为统一列表
- [ ] 1.3 Implement `schemas.py`: 定义 `ParsedQuery`、`DimensionRecommendation`、`CurationResult` Pydantic models + `STYLE_ADJACENCY` 风格邻接图 dict

## 2. Retrieval Strategies

- [ ] 2.1 Implement `strategies.py` 基础框架：`RetrievalStrategy` protocol/base class，输入 `(ParsedQuery, material_library)` → 输出 `dict[str, list[MaterialElement]]`（key = dimension）
- [ ] 2.2 Implement `IntuitionStrategy`: 过滤 aesthetic_style == target_style，按 visual_keywords 子串重叠度排序，每维度 top-5
- [ ] 2.3 Implement `AnalogyStrategy`: 从 STYLE_ADJACENCY 获取邻接风格，匹配 style.json 中 typical_colors/decorations/textures 对应的元素，每维度 top-5
- [ ] 2.4 Implement `CrossCategoryStrategy`: 过滤 product_category 不同但 signals 有子串交集的元素，每维度 top-5
- [ ] 2.5 Implement `TrendFrontierStrategy`: 过滤 maturity ∈ ["上升", "实验性"]，按实验性优先排序，每维度 top-5
- [ ] 2.6 Implement `run_all_strategies()`: 并行执行所有策略，合并候选池并标注每个元素的来源策略

## 3. LLM Curation

- [ ] 3.1 Implement `query_parser.py`: 用 Azure OpenAI + `with_structured_output(ParsedQuery)` 解析用户自然语言输入
- [ ] 3.2 Implement `curator.py`: 将候选池 + ParsedQuery 组装成策展 prompt，调用 LLM + `with_structured_output(CurationResult)` 输出每维度 top-N 推荐
- [ ] 3.3 Implement `image_matcher.py`: 对每个推荐元素，用 visual_keywords 在图片 description 中做子串匹配，返回 top-M 图片

## 4. CLI Entry Point

- [ ] 4.1 Create `notebooks/design_agent.py`: argparse CLI（位置参数 query, --top-n, --images-per-element, --json, --model），加载数据 → 解析查询 → 检索 → 策展 → 图片匹配 → 输出
- [ ] 4.2 实现终端格式化输出（按维度分区块，Rich panel 显示元素卡片和图片路径）
- [ ] 4.3 实现 `--json` 模式输出

## 5. Integration & Validation

- [ ] 5.1 端到端手动测试：用 "天然奢养沐浴露" 查询验证完整流程
- [ ] 5.2 边界测试：空素材库、缺失环境变量、无图片匹配等场景
- [ ] 5.3 Ruff lint 通过 `src/deep_research_from_scratch/design_agent/`
