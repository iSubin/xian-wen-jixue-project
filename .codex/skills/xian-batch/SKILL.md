---
name: xian-batch
description: Use when the user asks to order or continuously execute multiple parked Harness changes through one Agent Host session.
---

# xian-batch

## 用途

`xian-batch` 是 Agent Host 的多 Change 协调策略，不是 Harness Core scheduler（核心调度器），也不创建 Goal / Job authority。

它只负责：

1. 读取 current parked Change facts 与当前 `activeChange`。
2. 按 owner 目标、`dependsOn`、风险和降摩擦价值形成 session-local `HostBatchPlan`（会话内批次计划）。
3. 在同一个主 Agent session 中一次推进一个 Change；每个 terminal 后重新读取 canonical facts，再选择下一项。
4. 全部 Change 独立完成后，在明确的 release boundary（发布边界）执行一次最终集成验收和发布。

`HostBatchPlan` 只存在于当前 Agent session，不写 `batch-state.json`、`goal.json`、execution card、lease、events 或新的 tracked registry。每个 Change 自己的 accepted contract、lifecycle、Candidate、ActionAttempt、Result 与 commit 仍是唯一交付事实。

## 触发条件

当用户要求以下任一行为时使用：

- 对 parked Change 排序；
- 连续执行一批 Change；
- 批量推进多个已登记 Change；
- 为多 Change 工作形成精简的 Host execution brief（Host 执行说明）。

单个 Change、普通“继续”或只读项目状态不进入本 skill。

## 协议输入

优先读取：

- `xian-harness change list --parked --target <target-project> --json`
- `xian-harness status --target <target-project> --json`
- `xian-harness continue --target <target-project> --json`
- `.xian-harness/changes/<change-id>/.change-state.json`
- `.xian-harness/changes/<change-id>/change.md`
- `.xian-harness/changes/{change-id}/change.md`（governed/lite 默认契约入口）
- current accepted contract 与 `dependsOn` facts

`docs/待办清单.md` 是 generated view（生成视图），不能替代 current Change facts。历史 `.xian-harness/goals/` 或冷归档 Goal 只作为历史数据，不参与新批次调度。

## HostBatchPlan

Host 在内存中保持最小计划：

```text
objective
orderedChangeIds
dependsOn
ownerAuthorizedIds
currentIndex
finalDeliveryIntent
```

计划不授权工作。每个 Change 必须独立携带 owner request、requirement/backlog reference、Scope 与 Acceptance。并发到达但未被本次 owner 授权的 parked Change 不得进入当前计划。

排序规则：

1. 先处理修复执行断点或降低后续成本的 Change。
2. 依赖先于 dependent（依赖项）。
3. 同一热路径或迁移链的 Change 保持相邻，但每次只激活一个。
4. 纯增强和可延后风险最后处理。
5. 选择不唯一、依赖循环或业务边界不清时停止并报告，不持久化猜测。

## 执行流程

governed/lite 默认沿用单 Change 的 `open -> verify -> gate -> close` 路径；只有 Change 自身明确采用 audit mode 时，才执行 audit 所需的 spec/build/Review/finalize evidence。Batch 不改变任何 Change 的 mode 或 tier。

1. 若存在 active Change，只收口它，不重新排序或激活第二项。
2. 若 `activeChange=null`，从 owner-authorized 且依赖已 terminal 的列表中选择唯一下一项。
3. 通过正常 Change lifecycle 执行：activate -> implement -> targeted stabilization -> Review -> Formal Verify -> Gate -> Result/close -> commit。
4. 一个 Change terminal 且 commit/tree identity 一致后，重新读取 status、parked pool 和依赖 facts，再推进下一项。
5. 不从聊天历史重建 contract，不提前修改 later Change，不让 later parked capture 改变 current Candidate identity。
6. 普通 serial batch 在当前主 Agent session 连续执行；只有 owner 明确要求真实并行且 Runtime/worktree 边界安全时，Host 才创建 bounded isolated worker。
7. worker 只处理一个 Change，不选择下一项、不执行最终发布。
8. 全部 Change 完成后，由主 Agent执行最终 shared checks 和当前 release policy；普通 child 循环不运行 full suite。

## Attempt 与失败边界

- preflight 未启动 ActionAttempt 时，可以修正环境输入后继续。
- Review、Verify 或 Gate 的 non-pass 终结本次 immutable ActionAttempt，不自动终结 business Change。
- 同一 business identity 下，只有 meaningful Candidate delta（有意义的候选差异）才能创建新的 ActionAttempt。
- timeout、OOM、runner crash 等 execution interruption（执行中断）按 Runtime recovery/fencing authority 处理，不修改旧 result。
- 只有 owner cancellation、business identity 改变、明确越权或 Acceptance 不可实现等 business-boundary rule 才终结 Change。
- batch 不自动创建 successor Change；需要独立交付或扩大业务 Scope 时，停止并等待新的 owner authorization。

## 验证与交付

- 每个 Change 保留独立 Review、Formal Verify、Gate、Result 和 commit。
- Build 阶段只运行定向开发测试；Formal Verify 消费稳定 Candidate，不作为 test-plan debugging 入口。
- shared checks 只做最终确认，不能替代 Change-local failure signal。
- 普通 Host Batch 不运行 full suite；branch merge、代码 churn 和风险分类本身也不触发。
- Batch、Goal、child 数量、代码 churn 或风险分类本身均不触发 full suite；普通 batch 完成独立 Change 验收与最终检查后直接进入普通 Git delivery。
- 只有 owner 明确创建 version、tag、Pack rollout、registry artifact 或 deploy candidate 等显式 release candidate 时，才在最终 immutable tree 上单独运行一次 `xian-harness release verify --target . --json`。
- 禁止 `git add -A`、destructive Git、`--no-verify` 和 force push。

## 必需证据

- 每个 Change 的 current contract、terminal state、Result 或 closeout fact。
- 每个 Change 对应的 Review、Verify 与 Gate 摘要；not-required 必须由 Runtime 明确给出。
- 每个 Change 的 commit/tree identity，以及批次结束时的 clean worktree 与 publication 状态。
- HostBatchPlan 只作为当前 session 的协调记录，不进入上述交付证据。

## 确定性工具

- `xian-harness status --target <target-project> --json`
- `xian-harness continue --target <target-project> --json`
- `xian-harness change list --parked --target <target-project> --json`
- 单 Change lifecycle 的既有 CLI

不调用：

- `xian-harness goal open/status/next/close`
- `xian-harness auto-next`
- `xian-harness batch`
- `goal run` 或 `goal resume`

## 参考样例

```text
owner 选择 [change-a, change-b]
HostBatchPlan: change-a -> change-b
change-a terminal + commit -> 重新读取 canonical facts
change-b terminal + commit -> 最终 shared checks -> publish
```

如果执行 `change-a` 时另一个 session 新增 `change-c`，它继续 parked，不进入当前 HostBatchPlan，也不影响 `change-a` 的 Candidate identity。

## 自检清单

- 当前是否至多存在一个 active Change？
- ordered Change IDs 是否全部由 owner 授权，且 `dependsOn` 无循环？
- 是否在每个 terminal 后重新读取 canonical facts，而不是相信聊天记忆？
- 每个 Change 是否保留独立 Review、Verify、Gate、Result 与 commit？
- 是否避免写入 Goal、batch-state、execution card 或第二套 scheduler state？
- 最终 full authority 是否只在明确 integration boundary 执行一次？

## 交互预算

开始执行后由主 Agent 连续协调，不要求 owner 逐 Change 回复“继续”。长命令开始、完成、失败或超过 60 秒无结果时，给 owner 一条简短进度；不使用固定短 timeout 人为终止正常 Reviewer 或 Verify。

## 交接规则

只有发生真正阻塞时才交接。交接必须列出 current Change、current action、canonical evidence pointer、最后一次可归因结果和恢复条件；不得只说“上下文已满”，也不得要求 owner 手工重建 HostBatchPlan。

## 约束与原因

- 不持久化 HostBatchPlan。原因：跨 Change 顺序属于 Agent Host 的执行策略，持久化会重新形成 Goal / Job 第二 authority。
- 一次只激活一个 Change。原因：当前 State Machine 与 mutation lock 仍以单 active Change 为安全边界。
- 不从聊天历史判定 terminal。原因：聊天不是 canonical fact，可能遗漏失败、取消或外部 session 写入。
- 不自动吸收新 parked Change。原因：parked capture 不等于 owner 对当前批次的执行授权。
- 不在普通 child 循环运行 full suite。原因：完整集成验证只属于最终 immutable release boundary，重复运行会放大治理成本。

## 输出契约

只做排序时，输出：

- parked 总数与 current `activeChange`；
- ordered Change IDs、`dependsOn` 和排序理由；
- owner-authorized 范围；
- 一个精简 Host execution brief；
- 最终交付意图。

开始执行时，主 Agent直接消费上述内存计划并持续推进，不要求 owner 逐 Change 回复“继续”，也不要求 owner 创建新 session 或粘贴 packet。

最终报告列出每个 Change 的 terminal status、commit、验证摘要，以及最终 worktree、push 和 release verification 状态。

## 暂停条件

仅在以下事实出现时停止：

- 无法归因的 dirty worktree；
- 依赖循环、选择不唯一或 current facts 冲突；
- business-boundary classifier 终结当前 Change；
- 需要外部凭证、不可逆操作或 owner 接受新风险；
- 需要扩大 owner-authorized Change 集合或新增产品能力。

并发 Producer 新增的非干扰 parked Change 不改变当前 `HostBatchPlan`，也不使 current Candidate 或 evidence stale。
