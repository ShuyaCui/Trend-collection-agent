---
description: 按 SDD 流程实现 feature — 先读 spec、分阶段实现、不做 scope creep、完成后高层摘要
---

按 Spec-Driven Development 流程实现 OpenSpec change 中的任务。

**核心原则：先读 spec，再实现；大功能分阶段；完成后对照 spec 做高层 review。**

**Input**: 可以在 `/opsx:apply` 后指定 change 名称（如 `/opsx:apply add-auth`）。省略时从对话上下文推断；歧义时必须提示可选项。

---

## 步骤

### Step 1：确定要实现的 change

如果提供了名称，直接使用。否则：
- 从对话上下文推断
- 如果只有一个活跃 change，自动选择
- 如果有歧义，运行 `openspec list --json`，使用 **AskUserQuestion tool** 让用户选择

始终声明："使用 change：<name>"，并说明如何切换（`/opsx:apply <other>`）。

### Step 2：读取 spec，理解要做什么

```bash
openspec status --change "<name>" --json
```

解析 JSON：
- `schemaName`：使用的工作流
- 找到包含任务的 artifact（通常是 `tasks`）

```bash
openspec instructions apply --change "<name>" --json
```

返回：
- `contextFiles`：需要读取的 artifact 文件路径（按 schema 而定）
- 任务列表和状态
- 当前进度

**处理特殊状态：**
- `state: "blocked"`（缺少 artifacts）：显示提示，建议运行 `/opsx:propose` 完成 spec
- `state: "all_done"`：恭喜完成，建议运行 `/opsx:archive`

### Step 3：读取所有 context 文件

读取 `contextFiles` 中的每一个路径。对于 spec-driven schema，通常包括：
- `proposal.md`（what & why）
- `design.md`（how）
- `tasks.md`（任务清单）
- `specs/YYYY-MM-DD-<name>/requirements.md`（scope、约束）
- `specs/YYYY-MM-DD-<name>/validation.md`（验收标准）

**同时读取 constitution：**
- `specs/mission.md`
- `specs/tech-stack.md`

> ⚠️ **在充分理解 spec 之前，不要开始写代码。**

### Step 4：显示当前进度

输出：
- 使用的 schema
- 进度："N/M 任务已完成"
- 剩余任务概览
- 当前阶段（Phase A / B / C）

### Step 5：分阶段实现（核心）

#### 阶段划分原则

| 阶段 | 内容 |
|------|------|
| **Phase A** | 骨架：目录结构、接口定义、空函数签名、依赖关系 |
| **Phase B** | 主逻辑：核心功能实现、状态流转 |
| **Phase C** | 边界/测试/文档：错误处理、单元测试、%%writefile 单元更新 |

**大功能不要一次全实现。** 完成一个 Phase 后，给用户看高层摘要，等待确认再进入下一阶段。

#### 每个任务的执行规范

1. 声明正在处理的任务："Working on task N/M: <描述>"
2. 只做该任务范围内的改动（不做 scope creep）
3. 优先复用已有代码模式，不做广泛重构
4. 该项目所有 Python 源文件须通过 notebook `%%writefile` 单元生成，**不直接修改 `src/` 下的文件**
5. 完成后把 `- [ ]` 改为 `- [x]`
6. 进入下一个任务

**暂停条件：**
- 任务描述不清楚 → 使用 AskUserQuestion 提问
- 发现设计问题 → 建议更新 design.md，不要自行决策
- 遇到报错或阻塞 → 报告并等待指导
- 用户中断

### Step 6：每个 Phase 结束时输出高层摘要

```
## Phase A 完成

**改动文件：**
- src/deep_research_from_scratch/foo.py：新增 X（通过 notebooks/N.ipynb 生成）
- notebooks/N.ipynb：新增 %%writefile 单元

**改动摘要：**
<2-3 句话说明做了什么>

**是否符合 spec：**
- [x] requirements.md 中的 Constraint Y
- [x] proposal.md 中的 Goal Z

**下一步：** Phase B — 主逻辑实现
```

### Step 7：完成或暂停时的输出

**全部完成时：**

```
## 实现完成

**Change：** <name>
**Schema：** <schema>
**进度：** N/N 任务完成 ✓

### 本次完成的任务
- [x] 任务 1
- [x] 任务 2
...

**改动文件列表：**
- <文件路径>：<改动说明>

建议下一步：
1. 对照 spec 做高层 review（检查是否有 scope creep）
2. 运行测试：`uv run pytest tests/`
3. 运行 lint：`ruff check src/`
4. Commit spec（如果尚未 commit）
5. 运行 `/opsx:archive` 归档
```

**暂停时：**

```
## 实现暂停

**Change：** <name>
**进度：** N/M 任务完成

### 遇到的问题
<问题描述>

**选项：**
1. <选项 1>
2. <选项 2>
3. 其他方案

请告诉我如何继续。
```

---

## SDD 对齐检查（贯穿整个实现过程）

在实现过程中，持续检查：
- [ ] 改动是否在 spec 定义的 scope 内？
- [ ] 有没有偷偷做 spec 里没有的事（scope creep）？
- [ ] acceptance criteria 是否逐一覆盖？
- [ ] 是否复用了现有模式而不是重新发明？
- [ ] `%%writefile` 单元是否同步更新？

---

## Guardrails

- 读取所有 context 文件后再开始实现
- 任务不清楚时暂停提问，不要猜测
- 实现发现设计问题时暂停，建议更新 artifacts，不要自行重构
- 每个任务完成后立即标记 `[x]`
- 保持改动最小化和可审查
- 使用 CLI 输出的 contextFiles，不假设文件名
- 不直接修改 `src/` 下的源文件——改 notebook，再生成
