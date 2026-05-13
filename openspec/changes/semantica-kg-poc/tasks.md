## 1. 环境准备

- [ ] 1.1 安装 semantica 依赖到 venv（`uv add semantica`），验证 `from semantica.graph_store import GraphStore` 可正常 import
- [ ] 1.2 验证 Semantica EmbeddingGenerator 可加载默认模型（`BAAI/bge-small-en-v1.5`），记录 venv 大小增量

## 2. 图构建（Graph Construction）

- [ ] 2.1 实现 `load_material_library()`：从 4 个维度 JSON 文件读取所有元素，返回元素列表
- [ ] 2.2 实现节点创建：用 `GraphStore` API 创建 Element / Style / Signal / Dimension / Keyword 节点
- [ ] 2.3 实现结构边创建：BELONGS_TO_STYLE / IN_DIMENSION / HAS_SIGNAL / HAS_KEYWORD
- [ ] 2.4 实现推导边计算：SIGNAL_BRIDGE / KEYWORD_BRIDGE（Style↔Style），计算 weight 属性
- [ ] 2.5 输出图统计信息，验证节点/边数量与素材库数据一致

## 3. 检索模式验证（Retrieval Modes）

- [ ] 3.1 图遍历测试：按 Style 查找 Element、按 Element 查找 Signal 邻居、多跳 bridge 遍历
- [ ] 3.2 Embedding 语义搜索测试：生成 Element embedding、查询 "蜂蜜色滋养精华" 的 top-5、评估中文效果
- [ ] 3.3 Hybrid 混合检索测试：Style-scoped 语义搜索、bridge-expanded 语义搜索

## 4. 评估与结论

- [ ] 4.1 汇总测试结果，输出 Go/No-Go 评估报告：API 可用性、中文 embedding 质量、踩坑记录、建议
