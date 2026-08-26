---
name: xian-archive
description: Use when finalizing a change from the verify phase after gate pass and release conclusion are complete. Archive is a finalize action; `archived` is the persisted terminal ChangePhase.
---

# xian-archive

## 用途

在 implementation、verification、review、quality gate 和 release acceptance 之后关闭 audit/finalize change 循环。`xian-archive` 是 verify phase 内的 finalize/归档辅助 skill；持久终态是 `archived`。Workbench 是 change detail 的派生可视化视图，不是 archive lifecycle 的必需证据。

## 触发条件

Use this skill only after `xian-gate` returns pass and release acceptance evidence exists, usually via `xian-harness change finalize`.

## 方法论来源

- Provider: Xian internal engineering discipline
- Role: engineering-discipline-provider
- Absorption Mode: development branch finishing discipline is absorbed into `xian-archive`.

## 吸收的纪律

- `finishing-a-development-branch`: close only after verification, gate, release evidence, and integration recommendation exist.

## 执行前必须确认

- 必须：confirm Gate pass or explicit accepted-risk decision before archive.
- 必须：confirm release acceptance and final summary exist.
- 必须：record reusable experience candidates or an explicit reason none should be promoted.

## small hotfix 边界

- `quick-close` is the terminal path for non-upgraded small hotfix changes; it is not a full archive.
- 不要invoke `xian-archive` for a `tier=small` terminal change. 若需要 Standard/Major 行为，创建新的 follow-up change；不得 reopen 已 seal attempt。
- `terminalKind=failed` 不是 archive success，也不得被 accepted-risk、rerun Verify 或补写 Gate 转成成功；只读取其脱敏 failure evidence 和 current machine `failureRecovery.decision`，不得自行选择 relation。`prepare-new-candidate` 与 `retry-same-candidate` 不会把该 failed Business Change 转为成功；只有 `suspend-for-incident-repair` 且完整 current repository-baseline classifier/admission proof 才可授权 `incident-repair` relation；只有 `business-boundary classifier` 给出 `terminalize-business-change` 时才可 terminalize、replace 或新建 Business Change。
- Standard/Major audit/finalize changes still require gate, release acceptance, and archive records. Workbench evidence is optional and generated only when a user or skill explicitly asks for a detail view.
- small hotfix quick close does not integrate branches; review the quick-close Branch Finish section and run project-native git/PR handoff as needed.

## 协议输入

- governed/lite 默认：close 不进入 `xian-archive`；只在 audit/finalize 路径读取完整证据。
- audit/finalize 默认：`.xian-harness/changes/{change-id}/change.md`
- `.xian-harness/changes/{change-id}/tasks.md`
- `.xian-harness/changes/{change-id}/acceptance-criteria.md`
- `.xian-harness/changes/{change-id}/gate/gate-result.json`
- `.xian-harness/releases/{change-id}/release-acceptance.md`
- synced specs if Xian spec contract is used
- branch/worktree status

## 执行流程

1. Confirm all required tasks are complete.
2. Confirm verification and quality gate pass.
3. Sync delta specs to main specs when applicable.
4. Review existing release acceptance / release verify evidence first; if it is pass and fresh, do not regenerate it.
5. Run deterministic archive.
6. Inspect archive status.

## 默认交付意图

- 当前 change 来自实现、修复、执行或完成类请求时，继承 `默认 publish intent`；archive pass 后无需用户二次确认，直接进入 xian-commit 收口。
- archive 只负责终态事实，不在内部暗中运行 Release Verify 或 push；同一主 Agent 应继续路由到 Git delivery，而不是停下来要求用户回复“提交”或“推送”。

## Branch Finish 边界

- 串行 change 默认 `serial-trunk`：在本地默认分支完成，archive 不创建 feature branch 或 worktree；已安装 xian-commit 时必须使用 `push.mode=explicit-only`。
- 真实并行才使用 `parallel-isolated`：创建 worktree 与本地临时 branch，默认不推远端。
- worktree 管理是本地执行纪律，不新增 change phase，不新增 tracked worktree registry，也不新增强制治理文档或 archive evidence（归档证据）。
- 创建、删除或 prune worktree 等 worktree 拓扑变化不得触发 verify evidence 失效、full verify 或项目投影 churn（投影抖动）。
- 如果确实因真实并行、用户明确要求、无法归因的 dirty worktree 或长时间高风险实验使用 worktree，创建者负责 merge、目标分支验证和清理。
- 只有 Git tree matches verified tree（Git 文件树匹配已验证文件树）时，archive 才能复用 commit-bound evidence（提交绑定证据）；真实代码树变化必须重新验证。

## 快速归档路径

- 当 `release-acceptance.json` 与 `release-acceptance.md` 已存在且结构有效时，直接执行 `archive run`（归档执行），不要重复执行 `release accept`（生成 change-local closeout 投影）。发版级 `release verify` 不属于单个 change 的 archive 前置。
- 只有 archive plan（归档计划）或 archive preflight（归档预检）明确指出 missing/stale（缺失/过期）时，才按 `nextCommand` 补证据。
- 面向用户输出只保留关键结果：archive status（归档状态）、阻断原因、最小下一步。详细证据路径留在 JSON / Markdown artifact（产物）里。

## 常见分支

- 常规路径：按 `nextAction` 和当前 change state 选择下一步。
- 证据不足：先补 verify evidence 或明确记录 blocked reason。
- release evidence 已通过：直接 archive run，不重复生成 release acceptance。
- 发现职责不匹配：交接到 `xian-open` 重新路由。

## 确定性工具

- `xian-harness archive run <change-id> --target <target-project> --json`
- `xian-harness archive status <change-id> --target <target-project> --json`
- `git status --short --branch`

## 必需证据

- `.xian-harness/changes/{change-id}/archive/archive-result.json`
- audit Markdown archive report only when explicitly persisted
- `.xian-harness/changes/{change-id}/.change-state.json` phase changed to `archived`
- `.xian-harness/state.yaml` `lastArchive`
- release acceptance report path

## 事实映射

- Archive result -> `.xian-harness/changes/{change-id}/archive/archive-result.json`
- Final summary -> `.xian-harness/changes/{change-id}/archive/summary.md`
- Experience candidates -> `.xian-harness/changes/{change-id}/archive/experience-candidates.json`

## 参考样例

- `harden-xian-next-user-facing-guidance`: gate pass、release acceptance、archive 闭环参考。

## 自检清单

- 是否遵守当前 Interaction Budget？
- 是否从 canonical facts 而不是聊天记忆开始？
- 是否留下了可复查的 evidence 或明确说明无需证据？
- 是否没有越过当前 skill 的职责边界？

## 输出

- Archive record.
- Final change state.
- Branch integration recommendation.

## 交互预算

- 必须：obey the current hook-provided Interaction Budget before reading files or running commands.
- 必须：keep chat-mode requests tool-free unless the user explicitly asks for inspection, snapshot refresh, deep audit, or change execution.
- 必须：require explicit deep-audit or change intent before reading pack state, workbench, quality-gate, archive, or other large project status artifacts.

## 交接规则

- 当前请求携带 publish intent 且 archive pass 时，不要输出等待用户回复“继续”的 handoff；在同一任务中直接进入 xian-commit 收口。
- 当前请求不携带 publish intent 时，从运行时 `nextAction` 开始；末尾输出 `下一步建议：<中文下一步>`，空一行后单独输出 `$xian-xxx`，再空一行输出 `直接回复“继续”即可进入该步骤。`；不要在首屏附加“因为...”。
- 表达层原则：中文优先，默认用自然中文给结论、必要风险和下一步；必须保留英文术语、协议字段、状态名或命令名时，紧跟中文括注解释；不写“流程报告 / Review 报告 / evidence 清单”式长篇；只有 deep-audit、gate、verify 或用户明确要求完整显性化时才展开治理细节。
- Default mapping: archive pass -> branch finish workflow; missing release report -> release acceptance generation; gate not pass -> `xian-gate`.
- If the mapping conflicts with runtime `nextAction`, state the conflict and run `$xian-next` or `xian-harness continue --json` for arbitration.
- 不要invent post-archive handoff evidence; cite `nextAction` and existing archive/release facts.

## 约束与原因

- 不要在存在 open P0/P1 issues 时 archive。 原因：违反该约束会破坏 xian-archive 的协议边界、证据链或 profile 隔离。
- 不要在缺少 verification evidence 时 archive。 原因：违反该约束会破坏 xian-archive 的协议边界、证据链或 profile 隔离。
- 不要在缺少 release acceptance report 时 archive。 原因：违反该约束会破坏 xian-archive 的协议边界、证据链或 profile 隔离。
- 不要在 deterministic archive 期间移动或删除 change 目录；archive 是可审计记录层。 原因：违反该约束会破坏 xian-archive 的协议边界、证据链或 profile 隔离。
