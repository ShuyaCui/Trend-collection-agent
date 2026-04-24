---
description: 起草 Feature Spec — 读取 Constitution、找到下一个 Roadmap Phase、先采访再落盘
---

起草一个新的 feature spec，并生成所有 artifacts。遵循 Spec-Driven Development 流程：**先读 constitution → 找 roadmap 下一步 → 向用户提问 → 再落盘**。

生成的 artifacts：
- `proposal.md`（what & why）
- `design.md`（how）
- `tasks.md`（实现任务清单）

以及在 `specs/YYYY-MM-DD-<name>/` 下生成 SDD 三件套：
- `requirements.md`（scope、决策、约束）
- `plan.md`（分阶段任务组）
- `validation.md`（验收与 merge 标准）

落盘后运行 `/opsx:apply` 进入实现阶段。

---

**Input**: `/opsx:propose` 后的参数为 feature 名称（kebab-case）或自然语言描述。

---

## 步骤

### Step 0：清场检查（先于一切）

在做任何事之前，确认：
1. 上一个 feature 是否已收尾（branch merged 或明确 WIP）
2. 当前 agent context 是否干净（本次对话是否是新开的）

如果发现明显的上一轮残留（如用户提到 "继续上次"），记录下来，但不要阻塞流程。

### Step 1：读取 Constitution

读取以下文件（如存在）：
- `specs/mission.md` — 项目目标、服务对象、核心价值
- `specs/tech-stack.md` — 技术栈、已确定约束、tech stack gaps
- `specs/roadmap.md` — 当前实现顺序与优先级

如果这些文件不存在，继续但在 proposal 中标注"constitution 缺失"。

### Step 2：确认要做什么

**如果没有提供输入**，使用 **AskUserQuestion tool**（开放式）询问：
> "你想做什么？请描述想构建或修复的内容。"

从描述中推导 kebab-case 名称（例如 "add trend dimensions" → `add-trend-dimensions`）。

**如果提供了输入**，从 roadmap 中找到对应的 phase。如果用户描述的内容与当前 roadmap 下一步不符，使用 **AskUserQuestion tool** 确认：
> "Roadmap 显示下一步是 <roadmap-item>，你现在想做的是 <user-request>。是继续按 roadmap 顺序，还是优先处理你提到的内容？"

### Step 3：在落盘前向用户提问（必须）

使用 **AskUserQuestion tool**，**分 3 组一次性提问**（不要分多次问）：

**第 1 组：Feature Scope & Non-goals**
- 这个 feature 的核心目标是什么？
- 明确不做什么（non-goals）？（⚠️ 不写 non-goals 是 scope 膨胀的主因）

**第 2 组：Key Decisions & Context**
- 有哪些关键的技术或产品决策需要提前确认？
- 有没有依赖项、前置条件或约束？

**第 3 组：Validation & Merge Criteria**
- 如何判断这个 feature 实现成功？
- merge 的最低标准是什么（测试通过 / 手动验证 / 文档更新等）？

**在得到回答前，不要写入任何文件。**

### Step 4：创建 OpenSpec change 目录

```bash
openspec new change "<name>"
```

### Step 5：获取 artifact 构建顺序

```bash
openspec status --change "<name>" --json
```

解析 JSON，获取：
- `applyRequires`：实现前必须完成的 artifact 列表
- `artifacts`：所有 artifact 的状态和依赖关系

### Step 6：按依赖顺序创建 artifacts

对每个状态为 `ready` 的 artifact：

```bash
openspec instructions <artifact-id> --change "<name>" --json
```

返回字段说明：
- `context`、`rules`：对你的约束，**不要**写入文件
- `template`：输出文件的结构，照此填写
- `instruction`：该 artifact 类型的专项指导
- `outputPath`：写入路径
- `dependencies`：先读取这些已完成的 artifact

创建每个 artifact 时：
- 遵循用户在 Step 3 中的回答
- 遵循 constitution 的长期约束
- 区分"已确认事实"与"当前假设"，假设要显式标注
- 在 proposal 中**必须包含 Non-goals 部分**

每创建完一个 artifact：
```bash
openspec status --change "<name>" --json
```
检查所有 `applyRequires` artifact 是否都为 `done`。

### Step 7：在 `specs/` 下同步创建 SDD 三件套

在 `specs/YYYY-MM-DD-<name>/` 目录下创建：

**`requirements.md`** 包含：
- Objective（目标）
- User / Problem Context（用户与问题背景）
- Scope（范围）
- Non-goals（非目标）
- Constraints（约束）
- Key Decisions（关键决策）
- Inputs / Outputs
- Open Questions / Assumptions（区分事实与假设）

**`plan.md`** 包含：
- 按编号组织的任务组（Group 1、Group 2...）
- 每组说明：目标、具体任务、涉及文件
- Phase A（骨架）/ Phase B（主逻辑）/ Phase C（边界/测试/文档）三阶段拆分

**`validation.md`** 包含：
- 逐条验收标准（V1、V2...）
- merge checklist
- 验证步骤（有序）

### Step 8：显示最终状态

```bash
openspec status --change "<name>"
```

---

## 输出格式

完成后输出摘要：
- change 名称和路径
- 创建的 artifacts 列表（含简要描述）
- SDD 三件套路径
- 下一步提示："Spec 已就绪。建议先 commit spec，再运行 `/opsx:apply` 进入实现阶段。"

---

## ⚠️ 常见陷阱（来自 SDD Playbook）

- **没有 Non-goals** → scope 无限膨胀
- **spec 和实现在同一个对话里** → context 变脏，意图丢失
- **spec 没有 commit 就开始写代码** → 偏航后无法判断是哪一层出了问题
- **review 时先抠细节** → 错过高层错位
- **假设没有标注** → 后续实现与预期不符

---

## Guardrails

- 创建所有 `applyRequires` 要求的 artifacts
- 读取 dependency artifacts 后再创建新的
- 如果 context 极不清晰，使用 AskUserQuestion 提问；优先做合理决策而非频繁中断
- 如果同名 change 已存在，询问用户是继续还是新建
- 写入文件前验证 artifact 是否存在
