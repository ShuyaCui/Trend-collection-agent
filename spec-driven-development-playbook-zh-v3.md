# Spec-Driven Development（SDD）Playbook

> 适用于使用 Copilot、Cursor 或其他 coding agent 的项目开发流程。

---

## 一句话说明

**Spec-Driven Development 不是“先写点文档再写代码”，而是：先把长期规则和本轮功能合同写清楚，再让 agent 实现，然后按 spec 验收，并在 feature 之间做干净切换。**

它的核心不是 prompt，而是 artifact：

- constitution
- feature spec
- code
- validation result
- roadmap / changelog 更新

---

# 1. 总体框架

SDD 的核心结构可以分成两层：

## 项目层
- **Constitution**：项目级长期规则

## Feature 层循环
- **清场**
- **Draft spec**
- **Review spec**
- **Commit spec**
- **Implement**
- **High-level review**
- **Validation**
- **Commit feature**
- **Update docs / changelog**
- **Merge**
- **Quick replan**

---

# 2. 项目启动：先写 Constitution

Constitution 解决的是：

> 这个项目长期要遵守什么规则？

建议固定这几块：

## 2.1 Mission
项目目标是什么。

## 2.2 Users
主要用户是谁。

## 2.3 Core Use Cases
主要支持哪些工作流。

## 2.4 Non-goals
明确不做什么。

## 2.5 Tech Stack
技术栈、运行环境和系统约束。

## 2.6 Architecture Principles
架构原则。

## 2.7 Working Principles
工程习惯和做事原则。

## 2.8 Quality Bar
最低质量线。

## 2.9 Current Priorities / Roadmap
当前阶段重点。

### 判断标准
**凡是跨多个 feature 都成立的约束，都进 constitution。**

例如：
- 优先复用现有代码
- 不做大重构
- 输出要可验证
- 不确定时显式标注假设

---

# 3. 每个 Feature 开始前，先做“清场”

开始新 feature 前，先确认：

- 上一个 feature 有没有 unfinished work
- 上一个 feature branch 有没有 merge 回 main
- roadmap 里的下一个 feature 还是不是当前最该做的
- agent 的 context 有没有清掉

## 这一步的目的
- 减少 AI fatigue
- 防止 context 污染
- 避免把上一轮临时记忆带进下一轮
- 让 spec 真正承载意图，而不是依赖聊天残影

## 推荐动作
开始新 feature 前，先做这 4 件事：

1. 合并或收尾上一轮
2. 回到 main / trunk
3. 看一眼 roadmap
4. 开新 chat / 清 agent 上下文

---

# 4. 先起草 Feature Spec，而不是直接实现

Feature spec 是这轮工作的“合同”。

建议固定结构：

- **Summary**
- **Problem / User Need**
- **Goal**
- **Scope**
- **Non-goals**
- **Constraints**
- **Inputs / Outputs**
- **Acceptance Criteria**
- **Validation Plan**
- **Dependencies**
- **Risks / Tradeoffs**
- **Open Questions**

## 关键原则
agent 起草 spec 后，**必须人工 review 一遍**。

发现 agent 没抓住你的真实意图，就改 spec，而不是等代码出来再抱怨。

## 额外提醒
改一处 spec，要让相关 spec 工件一起同步。不要让 requirements、design、validation 彼此不一致。

---

# 5. Spec 先 commit，再进入实现

先 commit spec 的好处：

- 把本轮功能的设计意图固定下来
- 后面如果实现偏了，能判断是 spec 写漏了，还是 implementation 没照着做
- review 和 validation 时有明确参照物

## 建议动作
- spec review 完成后，先单独提交一次
- 再进入 implementation 阶段

---

# 6. 实现阶段：大 feature 分块做，小步推进

如果一个 feature 太大，不要一次性全实现。

## 推荐做法
把 feature 切成多个阶段：

- **Phase A**：先打通骨架
- **Phase B**：补主要逻辑
- **Phase C**：补边界、测试、文档

## 核心原则
**planning phase 和 implementation phase 分开。**

不要把“写 spec + 写代码 + 验证”挤在一个超长对话里。

---

# 7. Review：先看高层，不先抠细节

Review 的目标不是找茬，而是确认：

> agent 做出来的是不是你真正要的、而且你愿意负责的代码。

## 推荐顺序

### 7.1 看改动边界
- 改了哪些文件
- 有没有不该动的文件
- 有没有该动却没动的文件

### 7.2 对照 spec 看高层是否对齐
- 功能是不是按 spec 做了
- scope 有没有偷偷膨胀
- acceptance criteria 是否覆盖

### 7.3 再看实现质量
- 结构是否清晰
- 是否复用了已有模式
- 是否留下明显技术债

## 一个判断句
**先问“做对了吗”，再问“写优雅了吗”。**

---

# 8. 发现新偏好，不算失败，要补回 spec

spec 不是一次写完的，它会随着 review 逐渐变完整。

如果 review 时发现：
- 某种写法不符合你的工程习惯
- 某个结构应该单独拆类型
- 某条约束之前没写清

这不算 spec 失败。

## 正确做法
- 让 agent 修正代码
- 把这个新发现的偏好或约束补回 spec
- 让后续结果更稳定

---

# 9. Validation：验证的不只是“能跑”，还有“我真的理解了吗”

Validation 至少包含三层：

## 9.1 功能验证
- 运行应用
- 手动走主要流程
- 看结果是不是符合预期

## 9.2 理解验证
不仅要确认 changes are good，还要确认：

> 你真的理解这些改动。

推荐动作：
- 读一部分测试
- 跑测试
- 用 debugger 探索流程
- 理解核心代码路径

## 9.3 第二遍深审
如果你怀疑 agent 有遗漏，可以让它做 second look / deep review：

- 从多个角度复查整个项目
- 找隐藏问题
- 给出 issues 和 recommendations
- 再修正、再验证

## Validation 的实际步骤
1. 跑应用
2. 走核心用例
3. 读一部分测试
4. 跑测试 / debugger 探索
5. 必要时做 second look / deep review
6. 修复问题
7. 再验证一次

---

# 10. 小步提交，最后再 merge

不要攒一个巨型提交。

## 建议的提交节奏
- **Commit 1**：constitution / spec
- **Commit 2**：implementation skeleton
- **Commit 3**：review 后修正
- **Commit 4**：validation fixes
- **Commit 5**：changelog / docs

## 原则
- 小步提交更容易 review
- 出问题时更容易回滚
- cognitive debt 更低

---

# 11. Merge 后做 Quick Replan

每轮 feature 结束后，问自己：

- 下一个 roadmap item 还是最优先的吗？
- 刚做完的 feature 暴露了什么新信息？
- constitution / roadmap 要不要小更新？

## 这一步的意义
让开发变成**闭环**，而不是一条直线。

---

# 12. 给 Copilot / Coding Agent 的简化指令模板



## 12.0 写 Constitution 的课程版 Prompt 模板

这是课程里演示过的一类 prompt，核心思想是：

- 先从仓库现有文档里读取 stakeholder 输入
- 在 `specs/` 目录下生成 constitution 相关文件
- roadmap 要基于 `TODO.md` 拆成**非常小的 phases**
- 在真正落盘前，先用提问工具把 mission、target audience、tech stack gaps 这些关键信息补齐

### 课程示例（整理版）

```text
We have an AgentClinic project, a place for AI agents to get relief from their humans.

Look in README.md for input from stakeholders. Make a constitution in a specs directory:
- mission.md
- tech-stack.md
- roadmap.md — should be based on the TODO.md for high-level implementation order, in very small phases of work.

Interview me about mission, target audience, tech stack gaps.

Important: You must use your AskUserQuestion tool, grouped on these 3, before writing to disk.
```

### 这段 prompt 在教什么

它不是单纯让 agent “写一份 constitution”，而是在教一套更稳的 constitution 生成流程：

1. **先读仓库证据**
   - 从 `README.md` 读取 stakeholder input
   - 从 `TODO.md` 推出 roadmap 的高层实现顺序

2. **把 constitution 拆成多个 artifact**
   - `mission.md`
   - `tech-stack.md`
   - `roadmap.md`

3. **先补齐关键缺口，再写文件**
   - mission
   - target audience
   - tech stack gaps

4. **roadmap 要切得很小**
   - 不是大而空的阶段
   - 而是 very small phases of work

### 你可以借鉴的中文版本

```text
先不要直接写代码，也不要立刻落盘。

请先阅读 README.md，提取其中的 stakeholder input。
然后在 specs/ 目录下起草 constitution，至少包含：
- mission.md
- tech-stack.md
- roadmap.md

其中：
- mission.md 说明项目目标、服务对象、核心价值。
- tech-stack.md 说明当前技术栈、已确定约束、以及仍存在的 tech stack gaps。
- roadmap.md 基于 TODO.md 梳理高层实现顺序，并拆成非常小、可独立验证的 phases。

在写入磁盘之前，先一次性向我确认以下三类问题：
1. mission
2. target audience
3. tech stack gaps

请把问题分组后统一提问；在这些问题得到回答前，不要写入文件。
```

### 适用场景

这类 prompt 特别适合：

- 新项目刚起步，README / TODO 已经有一些雏形
- 你想让 agent **先采访你**，而不是直接脑补 constitution
- 你希望 roadmap 天然就是小步推进，便于后续 SDD feature loop

### 实战建议

如果你不是在课程演示环境里，没有一个叫 `AskUserQuestion` 的专用工具，也可以把要求改成：

- “先统一列出你需要确认的 3 组问题，等我回答后再写文件”
- 或者“先生成 interview questions，不要落盘”

本质不变：**先补关键约束，再生成 constitution artifact。**

## 12.1 写 Feature Spec 的课程版 Prompt 模板

这是课程里用于进入 **next phase / 生成 feature spec** 的一类 prompt。它的核心思想是：

- 先从 `specs/roadmap.md` 找到下一个 phase
- 先开分支
- 在真正落盘前，先围绕 feature spec 向用户提问
- 在 `specs/` 下为这个 feature 建一个独立目录
- 把 spec 拆成 `plan.md`、`requirements.md`、`validation.md` 三类 artifact
- 并要求 agent 参考已有 constitution 文件，如 `specs/mission.md` 和 `specs/tech-stack.md`

### 课程示例（整理版）

```text
Find the next phase on specs/roadmap.md and make a branch, ask me about the feature spec.
Create:
- A new directory YYYY-MM-DD-feature-name under specs for this feature work
- In there:
  - plan.md as a series of numbered task groups
  - requirements.md for the scope, decisions, context
  - validation.md for how to know the implementation succeeded and can be merged

Refer to specs/mission.md and specs/tech-stack.md for guidance.

Important: You must use your AskUserQuestion tool, grouped on these 3, before writing to disk.
```

### 这段 prompt 在教什么

它不是单纯让 agent “写个 spec”，而是在教一套更规范的 **feature kickoff 流程**：

1. **从 roadmap 里取下一步**
   - 不是临时想到什么就做什么
   - 而是从 `specs/roadmap.md` 读取下一个 phase

2. **每个 feature 都有独立工作目录**
   - 目录名里带日期和 feature 名
   - 方便追踪 spec、实现和后续 merge 的关系

3. **把 feature spec 拆成 3 个文件**
   - `plan.md`：任务分组与实现顺序
   - `requirements.md`：范围、关键决策、上下文
   - `validation.md`：验收和 merge 条件

4. **spec 不是脱离 constitution 写的**
   - 要参考 `specs/mission.md`
   - 要参考 `specs/tech-stack.md`
   - 也就是 feature spec 要继承项目级长期规则

5. **先采访，再落盘**
   - 通过提问补齐 feature 的关键信息
   - 不要让 agent 靠猜测把 spec 写死

### 你可以借鉴的中文版本

```text
先不要写代码，也不要立刻写入磁盘。

请先阅读 specs/roadmap.md，找到当前最合适的下一个 phase，并基于它准备 feature spec。
同时参考：
- specs/mission.md
- specs/tech-stack.md

然后为这次 feature 工作在 specs/ 下创建一个新目录，目录名格式建议为：
YYYY-MM-DD-feature-name

目录中至少包含：
- plan.md：按编号组织的任务组，表示实现顺序与阶段拆分
- requirements.md：记录 scope、关键决策、上下文、非目标与约束
- validation.md：记录如何判断实现成功、可以 merge，以及需要做的验证步骤

在真正写入文件前，先统一向我确认这 3 类信息：
1. feature scope / non-goals
2. key decisions / context
3. validation / merge criteria

请把问题分组后一次性提问；在这些问题得到回答前，不要写入文件。
```

### 适用场景

这类 prompt 特别适合：

- roadmap 已经存在，下一步 feature 有明确顺序
- 你希望每个 feature 都有独立 spec 目录，便于追踪
- 你想把 plan / requirements / validation 三层分开，而不是混成一个文件
- 你希望 agent 先采访你，再进入 spec drafting

### 实战建议

如果你当前使用的工具没有 `AskUserQuestion` 这种专用能力，可以改成：

- “先列出你需要确认的 3 组问题，等我回答后再落盘”
- 或者“先输出 interview questions 和 feature directory plan，不要写文件”

本质不变：**先从 roadmap 取 phase，先补齐 feature 约束，再生成结构化 spec artifact。**


## 12.2 实现阶段

```text
根据已确认的 feature spec 实现第一阶段，不要一次做完整个大功能。
优先复用现有模式，不做广泛重构。
完成后给我一个高层改动摘要，并列出改动文件。
```

## 12.3 Review / Validation 阶段

```text
不要只总结，请按 spec 对本轮改动做高层 review。
重点检查：
- 是否符合 spec
- 是否有 scope creep
- 是否有遗漏的 acceptance criteria
- 是否需要同步更新 docs / changelog / roadmap

然后执行 validation：
- 运行应用
- 跑相关测试
- 列出发现的问题
必要时做第二轮深度审查。
```

---

# 13. 最短版心法

## SDD 不是：
“想到啥 → 让 agent 写 → 差不多就 merge”

## SDD 是：
“先写规则 → 再写合同 → 按合同实现 → 按合同验收 → 收尾后再进下一轮”

---

# 14. 最容易踩的 5 个坑

## 14.1 没写 non-goals
结果 scope 无限膨胀。

## 14.2 spec 和实现混在一个大对话里
结果 context 很快变脏。

## 14.3 spec 写完不 commit
后面偏航时很难判断是哪一层出了问题。

## 14.4 review 先抠细节
结果自己很累，却没发现高层错位。

## 14.5 validation 只看能不能跑
结果 cognitive debt 越滚越大。

---

# 15. 推荐落地目录

```text
.github/
  copilot-instructions.md
  prompts/
    write-constitution.prompt.md
    write-feature-spec.prompt.md

docs/
  constitution.md
  specs/
    <feature-name>.md
```

---

# 16. 最终操作清单（Checklist）

## 每个新 feature 开始前
- [ ] 上一个 feature 已收尾
- [ ] 分支已合并或明确未合并原因
- [ ] roadmap 已复查
- [ ] agent context 已清理

## spec 阶段
- [ ] 已读取 constitution
- [ ] 已起草 feature spec
- [ ] 已 review spec
- [ ] 已补充真实意图和约束
- [ ] 已 commit spec

## 实现阶段
- [ ] 按 spec 实现
- [ ] 大功能已切片
- [ ] 改动规模可审查

## review / validation 阶段
- [ ] 已做高层 review
- [ ] 已检查是否符合 spec
- [ ] 已运行应用
- [ ] 已跑测试或做最小验证
- [ ] 必要时已做 second look
- [ ] docs / changelog / roadmap 已同步

## 收尾阶段
- [ ] feature 已提交
- [ ] 已 merge
- [ ] 已 quick replan 下一个 feature

---

# 17. 结语

Spec-Driven Development 的关键，不是让 agent 替你决定一切，而是：

- 用 constitution 固定长期规则
- 用 feature spec 固定本轮合同
- 用 review 和 validation 保持控制权
- 用 replanning 维持项目演化方向

**抓住这 5 个控制点——constitution、spec、implementation、validation、replanning——你就抓住了 SDD 的骨架。**
