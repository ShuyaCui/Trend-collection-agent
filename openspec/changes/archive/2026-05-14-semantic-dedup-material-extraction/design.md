## Context

`extract_material_library.py` 中的 `_deduplicate_elements` 函数当前只按 `(dimension, name)` 精确匹配来合并重复条目。由于 LLM 对同一概念可能产生措辞各异的 `name`（例如"珠光效果"与"珠光质感"），精确匹配无法覆盖这类语义重复，导致材料库存在冗余条目。

当前架构：
1. 各 report 的 LLM 提取结果汇总为 `list[MaterialElement]`
2. `_deduplicate_elements` 按 `(dim, name)` 精确分组并合并
3. 分维度写出 JSON 文件

新架构在步骤 2 后插入步骤 2b：对同一维度内剩余条目做 embedding 语义去重。

认证方式与现有 LLM 调用完全一致：使用 `GenAIToken().token()` 获取 Azure AD token，通过 `AzureOpenAIEmbeddings` 调用 `TEXT-EMBEDDING-3-SMALL`。

## Goals / Non-Goals

**Goals:**

- 实现 `_semantic_deduplicate_elements` 函数，对同一 dimension 内的条目 `name` 批量 embedding，对 cosine similarity > 0.7 的条目对执行合并（规则与精确去重一致）。
- 使用 Union-Find 进行聚类，避免贪心顺序影响结果。
- 新增 `--no-semantic-dedup` CLI 参数以便跳过此步骤。
- 合并日志与现有 `_deduplicate_elements` 风格保持一致。

**Non-Goals:**

- 不对 `visual_keywords` / `signals` 字段做语义去重。
- 不引入 embedding 持久化缓存。
- 不自动调优相似度阈值。
- 不修改 schema、提取 prompt 或 JSON 输出格式。

## Decisions

### 1. Union-Find 聚类而非贪心逐对合并

**选择**: Union-Find（并查集）聚类。

**原因**: 贪心逐对合并（扫描所有对，逐次合并）的结果依赖于遍历顺序；若 A-B、B-C 均超阈值但 A-C 未超，结果不一致。Union-Find 将所有相互超阈值的条目归入同一组，语义确定、幂等。

**备选**: DBSCAN / 层次聚类——引入额外依赖且对小数据集过重，舍弃。

### 2. 只对 `name` 字段做 embedding

**选择**: 只用 `name` 向量化。

**原因**: `name` 是最简洁、最代表性的字段，embedding 质量高、成本低；`visual_keywords` / `signals` 较长且部分重叠属于预期，不作语义等价判断依据。

### 3. 仅在同一 dimension 内比较

**选择**: 跨 dimension 不比较。

**原因**: 不同维度的元素即使名称相似也属于不同概念类别（例如"透明感"在"透明度与质地"和"颜色"维度意义不同），强制跨维度合并会破坏 schema 约束。

### 4. 复用 `_merge_group` 合并规则

**选择**: 抽取共用 `_merge_group(group: list[MaterialElement]) -> MaterialElement` 辅助函数，由精确去重和语义去重共同调用。

**原因**: 保持合并逻辑单一来源，避免两处合并规则漂移。

### 5. Embedding 客户端初始化

```python
from langchain_openai import AzureOpenAIEmbeddings

_EMBEDDING_MODEL = AzureOpenAIEmbeddings(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    deployment="TEXT-EMBEDDING-3-SMALL",
    api_version="2024-09-01-preview",
    api_key=GenAIToken().token(),
    default_headers={
        "project-name": os.getenv("HEADERS_PROJECT_NAME"),
        "userid": os.getenv("HEADERS_USERID"),
    },
)
```

初始化时机：`--no-semantic-dedup` 时不初始化，避免无谓的 token 刷新。

## Risks / Trade-offs

- **[额外 API 延迟]** → 每次运行批量调用 Embeddings API；条目数通常 < 200，延迟可接受（单批 < 2s）。如需规避，用 `--no-semantic-dedup`。
- **[阈值固定]** → 0.7 是合理起点，但对某些领域可能过松或过严 → 后续可通过 CLI 参数 `--semantic-dedup-threshold` 暴露，当前版本暂不实现。
- **[GenAIToken 有效期]** → token 在运行期内通常不过期；若长时间运行需刷新 → 已有 `GenAIToken` 负责管理，无额外风险。
- **[numpy 依赖]** → 余弦相似度计算需要 numpy；假设已在项目环境中安装（langchain-openai 本身依赖 numpy）。

## Migration Plan

1. 修改 notebook 对应的 `%%writefile` 单元（或直接修改 `src/material-library-extraction/extract_material_library.py` 如无对应 notebook 单元）。
2. 新增 `--no-semantic-dedup` 参数，默认启用语义去重。
3. 现有精确去重逻辑不变，语义去重在其后追加。
4. 回滚：传入 `--no-semantic-dedup` 即可完全跳过新逻辑，行为与当前版本等同。

## Open Questions

- `extract_material_library.py` 是否有对应 notebook `%%writefile` 单元？若有，需同步修改 notebook。（[假设] 当前直接存在于 `src/material-library-extraction/`，无对应 notebook 单元。）
