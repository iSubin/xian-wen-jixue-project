---
name: xian-diagnose
description: Use when diagnosing a bug, test failure, slow behavior, timeout, or unclear defect. Must come before fix proposals.
---

# xian-diagnose

## 用途

在修复前建立 bug、性能或环境问题的复现事实、假设和证据边界。

## 触发条件

当用户报告以下场景时使用：

- bug, error, failure, broken behavior, regression, not working
- 报错、不生效、失败、回归、逻辑不对、数据不对
- performance, slow, timeout, memory, CPU, SQL slow
- 性能、慢、超时、卡顿、内存高、CPU 高、SQL 慢

## 方法论来源

- Provider: Xian internal engineering discipline
- Role: engineering-discipline-provider
- Absorption Mode: systematic debugging discipline is absorbed into `xian-diagnose`.

## 吸收的纪律

- `systematic-debugging`: reproduce, hypothesize, gather evidence, and eliminate causes before repair.

## 执行前必须确认

- 必须：record reproduction steps or a clear reason the symptom cannot be reproduced.
- 必须：state at least one hypothesis and the evidence needed to confirm or reject it.
- 必须：collect logs, command output, metrics, API response, or other facts before assigning repair work.

## 协议输入

- `.xian-harness/changes/{change-id}/acceptance-criteria.md`
- `.xian-harness/changes/{change-id}/design.md`
- `.xian-harness/changes/{change-id}/verify/verify-result.json`
- `.xian-harness/changes/{change-id}/gate/quality-issues.json`
- project-native logs, test output, browser console output, API responses, or runtime metrics when available
- user-provided symptom, expected behavior, actual behavior, reproduction steps, and time window

## 执行流程

1. Classify `diagnosisType` as `bug`, `performance`, `environment`, `data`, `permission`, `integration`, or `unknown`.
2. Record reproduction facts: entry point, exact command or request, expected behavior, actual behavior, affected files or endpoints, and whether the issue is reproducible.
3. Collect logs and evidence before changing code. For performance issues, capture baseline timing or resource facts before optimization.
4. Split the problem by layer: UI, API, service/domain, data/query, integration, runtime/environment, or Harness protocol.
5. Decide the next role:
   - confirmed code defect -> `xian-build`
   - missing or weak reproduction -> `xian-verify`
   - open quality issue -> `xian-review`
   - evidence complete and fix verified -> `xian-gate`
6. Write diagnosis output into the current change, review note, issue, or handoff before repair begins.

## 常见分支

- 常规路径：按 `nextAction` 和当前 change state 选择下一步。
- 证据不足：先补 verify evidence 或明确记录 blocked reason。
- 发现职责不匹配：交接到 `xian-open` 重新路由。

## 确定性工具

- `xian-harness continue <change-id> --target <target-project> --json`
- `xian-harness gate issues <change-id> --target <target-project> --json`
- `xian-harness verify <change-id> --target <target-project> --command "<reproduction-or-regression-command>" --json`
- project-native commands for logs, tests, API smoke checks, browser checks, or performance baselines

## 必需证据

- diagnosisType
- reproduction status and steps
- expected behavior and actual behavior
- logs, command output, API response, screenshot, metric, or affected data sample when available
- baseline measurement for performance issues
- suspected layer and confidence
- recommended next role and concrete next command

## 事实映射

- Reproduction and hypothesis -> current change diagnosis note or issue
- Evidence -> `.xian-harness/changes/{change-id}/verify/verify-result.json` or linked runtime artifact
- Next role -> Workbench handoff or issue lifecycle

## 参考样例

- 暂无；当后续出现 bug/performance 诊断闭环 change 时补齐。

## 自检清单

- 是否遵守当前 Interaction Budget？
- 是否从 canonical facts 而不是聊天记忆开始？
- 是否留下了可复查的 evidence 或明确说明无需证据？
- 是否没有越过当前 skill 的职责边界？

## 输出

- Diagnosis summary.
- Structured issue or handoff note when repair is needed.
- Regression or baseline command to preserve the diagnosis.
- Residual uncertainty when evidence is incomplete.

## 交互预算

- 必须：obey the current hook-provided Interaction Budget before reading files or running commands.
- 必须：keep chat-mode requests tool-free unless the user explicitly asks for inspection, snapshot refresh, deep audit, or change execution.
- 必须：require explicit deep-audit or change intent before reading pack state, workbench, quality-gate, archive, or other large project status artifacts.

## 交接规则

- 输出时先说明当前结论、证据缺口和风险；末尾输出 `下一步建议：<中文下一步>`，空一行后单独输出 `$xian-xxx`，再空一行输出 `直接回复“继续”即可进入该步骤。`；不要在首屏附加“因为...”。

- Reproducible bug with suspected code cause -> `xian-build`.
- Bug fixed or diagnosis requires proof -> `xian-verify`.
- Performance issue with no baseline -> `xian-verify` to capture baseline first.
- Performance issue with baseline and suspected implementation cause -> `xian-build`.
- Conflicting evidence or risk acceptance -> `xian-review`.
- Fix verified and issues closed -> `xian-gate`.

## 约束与原因

- 诊断事实记录前不要编辑代码。 原因：违反该约束会破坏 xian-diagnose 的协议边界、证据链或 profile 隔离。
- 不要把症状标签当作根因。 原因：违反该约束会破坏 xian-diagnose 的协议边界、证据链或 profile 隔离。
- 不要在缺少独立证据时混合 bug 诊断和性能优化。 原因：违反该约束会破坏 xian-diagnose 的协议边界、证据链或 profile 隔离。
- 不要在缺少前后测量时声称性能提升。 原因：违反该约束会破坏 xian-diagnose 的协议边界、证据链或 profile 隔离。
- 不要把项目特有后端规则复制到 base profile；profile-specific 规则属于当前 profile 的质量策略。 原因：违反该约束会破坏 xian-diagnose 的协议边界、证据链或 profile 隔离。
