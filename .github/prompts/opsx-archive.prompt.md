---
description: 归档已完成的 change — 先做 SDD 验收检查，再归档，最后 Quick Replan
---

归档一个已完成的 change。遵循 SDD 流程：**先做验收检查 → 确认 docs/changelog 已同步 → 归档 → Quick Replan**。

**Input**: 可以在 `/opsx:archive` 后指定 change 名称（如 `/opsx:archive add-auth`）。省略时从对话上下文推断；歧义时必须提示可选项。

---

## 步骤

### Step 1：确认要归档的 change

如果没有提供名称，运行 `openspec list --json` 获取可用 changes。使用 **AskUserQuestion tool** 让用户选择。

只显示活跃的 changes（未归档的）。如果可用，显示每个 change 使用的 schema。

**重要：不要猜测或自动选择。始终让用户确认。**

### Step 2：SDD 验收检查（归档前必须完成）

在归档前，依次检查以下验收项目：

#### 2a. 检查 artifact 完成状态

```bash
openspec status --change "<name>" --json
```

解析 JSON：
- `artifacts`：所有 artifacts 的状态（`done` 或其他）

如果有未完成的 artifacts，显示警告并用 **AskUserQuestion tool** 询问是否继续。

#### 2b. 检查任务完成状态

读取 `tasks.md`，统计：
- `- [ ]`（未完成）vs `- [x]`（已完成）的数量

如果有未完成任务，显示警告并确认。

#### 2c. 对照 spec 做高层 Review

读取 spec 文件：
- `specs/<date>-<name>/requirements.md`
- `specs/<date>-<name>/validation.md`（逐条验收标准）

检查以下 SDD Review 清单：

```
SDD 高层 Review 清单
--------------------
[ ] 实现是否符合 requirements.md 中的 scope？
[ ] 有没有 scope creep（做了 spec 没有的事）？
[ ] validation.md 中的验收标准是否逐一覆盖？
[ ] 有没有该改但没改的文件？
[ ] 有没有不该改但被改动的文件？
[ ] 是否复用了现有模式而不是重新发明？
```

**先问"做对了吗"，再问"写优雅了吗"。**

如果发现问题，使用 **AskUserQuestion tool** 询问：
- "Review 发现以下问题：<问题列表>。是先修复再归档，还是记录到 open questions 后归档？"

#### 2d. 运行验证

提示用户运行（或代为运行，如果可以）：

```bash
# Lint 检查
ruff check src/

# 运行测试
uv run pytest tests/ -v

# 检查 import（基本 smoke test）
uv run python -c "import deep_research_from_scratch"
```

如果测试失败，显示失败信息并询问用户是否继续归档。

#### 2e. 检查 docs / changelog / roadmap 是否已同步

检查以下文件是否需要更新：
- `specs/roadmap.md` — 这个 phase 是否已标记完成？
- `README.md` — 是否需要更新功能描述？
- notebooks 中的文档单元

如果有需要同步的地方，使用 **AskUserQuestion tool** 询问是否更新后再归档。

### Step 3：检查 delta spec 同步状态

检查 `openspec/changes/<name>/specs/` 下是否有 delta specs。

如果不存在，直接进入 Step 4。

如果存在：
- 对比每个 delta spec 与对应的主 spec（`openspec/specs/<capability>/spec.md`）
- 确定会产生的变更（增加、修改、删除、重命名）
- 在提示前展示合并摘要

**提示选项：**
- 如果有变更需要同步："立即同步（推荐）"、"不同步直接归档"
- 如果已同步："立即归档"、"仍然同步"、"取消"

如果用户选择同步，使用 Task tool（subagent_type: "general-purpose"）调用 openspec-sync-specs。无论如何选择，都继续归档。

### Step 4：执行归档

创建归档目录（如不存在）：
```bash
mkdir -p openspec/changes/archive
```

使用当前日期生成目标名称：`YYYY-MM-DD-<change-name>`

检查目标是否已存在：
- 存在：报错，建议重命名或等到不同日期
- 不存在：移动

```bash
mv openspec/changes/<name> openspec/changes/archive/YYYY-MM-DD-<name>
```

### Step 5：Quick Replan（归档后必做）

归档完成后，输出一个 Quick Replan 提示：

```
## Quick Replan

本次 feature 结束，花 1 分钟回顾：

1. **下一个 roadmap item 还是最优先的吗？**
   当前 roadmap.md 下一步：<读取 specs/roadmap.md 显示下一步>

2. **刚完成的 feature 暴露了什么新信息？**
   （请告诉我是否有新发现需要记录）

3. **constitution / roadmap 需要小更新吗？**
   - specs/mission.md 是否仍然准确？
   - specs/tech-stack.md 是否需要补充新依赖？
   - specs/roadmap.md 是否需要调整优先级？

回答这些问题后，我可以帮你更新相关文件，或直接进入下一个 feature。
```

### Step 6：显示归档摘要

```
## 归档完成

**Change：** <name>
**Schema：** <schema>
**归档位置：** openspec/changes/archive/YYYY-MM-DD-<name>/
**Spec 同步：** ✓ 已同步 / 跳过同步 / 无 delta specs

SDD 验收结果：
- Artifact 完成：✓ 全部完成 / ⚠️ N 个未完成
- 任务完成：✓ 全部完成 / ⚠️ N 个未完成
- Spec Review：✓ 已完成 / ⚠️ 有待处理问题
- 测试：✓ 通过 / ⚠️ 跳过 / ✗ 失败
- Docs 同步：✓ 已同步 / ⚠️ 待处理

下一步：运行 Quick Replan，然后 `/opsx:propose` 开始下一个 feature。
```

---

## 有警告时的输出

```
## 归档完成（含警告）

**Change：** <name>
**Schema：** <schema>
**归档位置：** openspec/changes/archive/YYYY-MM-DD-<name>/

**警告：**
- 归档时有 2 个未完成的 artifacts
- 归档时有 3 个未完成的任务
- Delta spec 同步已跳过（用户选择跳过）

如果这不是预期的，请检查归档内容。
```

---

## 归档失败时的输出

```
## 归档失败

**Change：** <name>
**目标路径：** openspec/changes/archive/YYYY-MM-DD-<name>/

目标归档目录已存在。

**选项：**
1. 重命名现有归档
2. 如果是重复，删除现有归档
3. 等到不同日期再归档
```

---

## Guardrails

- 如果没有提供 change 名称，必须提示选择
- 使用 artifact graph（openspec status --json）检查完成状态
- 不要因为警告阻塞归档——告知并确认即可
- 移动时保留 .openspec.yaml（随目录一起移动）
- 显示清晰的发生了什么的摘要
- 如果请求同步，使用 Skill tool 调用 `openspec-sync-specs`（agent 驱动）
- 如果存在 delta specs，始终先运行同步评估并显示合并摘要再提示
- **始终在归档后做 Quick Replan 提示**——这让开发成为闭环而不是直线
