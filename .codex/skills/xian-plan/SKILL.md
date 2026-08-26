---
name: xian-plan
description: Use when turning accepted spec/design into an ordered task list with verification mapping for the plan phase.
---

# xian-plan

## 用途

创建 Builder Agent、Verifier Agent 或人类都能执行的有序计划。`xian-plan` owns the `plan` phase discipline: it turns accepted WHAT/spec into HOW/tasks/verification mapping before build.

## 触发条件

Use this skill after spec/design approval or for an already-clear small change that still needs task sequencing and verification mapping. In the runtime lifecycle this planning work happens in `plan`, before `build`.

## 方法论来源

- Provider: Xian internal engineering discipline
- Role: engineering-discipline-provider
- Absorption Mode: planning discipline is absorbed into `xian-plan`; implementation plans must remain under Xian change workspace.

## 吸收的纪律

- `writing-plans`: decompose implementation into verifiable, ordered tasks with exact evidence expectations.

## 执行前必须确认

- 必须：read `change.md` before writing tasks; legacy/audit changes may also require proposal, design, and acceptance criteria.
- 必须：map each implementation task to an AC, verification rule, command, or explicit non-verifiable decision.
- 必须：identify task dependencies, rollback points, and human decisions before Builder Agent starts.
- 必须：把 design 中列出的 future implementation path 标记为 candidate-only，除非它已经是当前 active change 或用户明确选择的新 change。

## 协议输入

- governed/lite 默认：`.xian-harness/changes/{change-id}/change.md`
- `.xian-harness/changes/{change-id}/design.md`
- `.xian-harness/changes/{change-id}/acceptance-criteria.md`
- `.xian-harness/changes/{change-id}/tasks.md`
- `.xian-harness/harness-protocol.yaml`
- adapter rules and target test/build commands

## 执行流程

1. Break work into independently verifiable tasks.
2. Attach each task to files, modules, or artifacts.
3. Place verification steps next to implementation steps.
4. Identify tasks that require human confirmation.
5. Keep future batch change names as roadmap candidates; do not convert them into executable child workflows.
6. Update the task section in `change.md` with clear done criteria; legacy/audit changes may update `tasks.md`.

## 确定性工具

- `xian-harness change inspect <change-id> --target <target-project> --json`
- project-native inspection commands when planning implementation work
- `rg --files` and package/build metadata inspection to choose real commands

## 必需证据

- Ordered task list in `.xian-harness/changes/{change-id}/change.md`.
- Verification checklist mapped to acceptance criteria.
- Explicit scope boundaries and files/modules likely to be touched.

## 事实映射

- Execution tasks -> `.xian-harness/changes/{change-id}/change.md`
- Verification mapping -> `.xian-harness/changes/{change-id}/change.md`
- Human decisions -> `.xian-harness/changes/{change-id}/.change-state.json` pause or handoff evidence

## 参考样例

- `standardize-chinese-skill-contract-v2/tasks.md`: 先 review 再实现的 major change 计划参考。

## 自检清单

- 是否遵守当前 Interaction Budget？
- 是否从 canonical facts 而不是聊天记忆开始？
- 是否留下了可复查的 evidence 或明确说明无需证据？
- 是否没有越过当前 skill 的职责边界？

## 输出

- Ordered task list.
- Verification checklist.
- Risk and decision markers.

## 交互预算

- 必须：obey the current hook-provided Interaction Budget before reading files or running commands.
- 必须：keep chat-mode requests tool-free unless the user explicitly asks for inspection, snapshot refresh, deep audit, or change execution.
- 必须：require explicit deep-audit or change intent before reading pack state, workbench, quality-gate, archive, or other large project status artifacts.

## 交接规则

- 当前请求携带 publish intent 且不存在真实阻塞时，完成 plan 后由同一主 Agent 在同一任务中直接进入下一个 lifecycle skill，不输出等待用户回复“继续”的 handoff。
- 当前请求不携带 publish intent 时，输出时先说明当前结论、证据缺口和风险；末尾输出 `下一步建议：<中文下一步>`，空一行后单独输出 `$xian-xxx`，再空一行输出 `直接回复“继续”即可进入该步骤。`；不要在首屏附加“因为...”。

- Plan with incomplete decisions -> human decision or `xian-design`.
- Approved plan -> `xian-build`.
- Verification-only plan -> `xian-verify`.

## 约束与原因

- 不要创建无法检查的任务。 原因：违反该约束会破坏 xian-plan 的协议边界、证据链或 profile 隔离。
- 不要把无关变更混入同一个 plan。 原因：违反该约束会破坏 xian-plan 的协议边界、证据链或 profile 隔离。
- 不要把 future implementation path 当成当前 active workflow。原因：batch plan 中的未来 change 名称只是 candidate-only roadmap evidence，必须等用户明确选择并由 Harness CLI 创建后才能进入执行计划。
- 不要在 gate 和 release acceptance evidence 存在前安排 archive。 原因：违反该约束会破坏 xian-plan 的协议边界、证据链或 profile 隔离。
