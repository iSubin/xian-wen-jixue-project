---
name: xian-review
description: Use when reviewing an implementation, issue lifecycle, closeout results, or risk acceptance. Independent from the builder who wrote the code.
---

# xian-review

## 用途

把 review 转换成可修复、可接受风险或可关闭的结构化 issues。

## 触发条件

Use this skill after implementation or verification when an independent review, risk decision, or issue lifecycle is needed.

## 方法论来源

- Provider: Xian internal engineering discipline
- Role: engineering-discipline-provider
- Absorption Mode: code review reception and request discipline are absorbed into `xian-review`.

## 吸收的纪律

- `requesting-code-review`: define review scope and evidence before asking for approval.
- `receiving-code-review`: verify external feedback against this codebase before applying it.

## Change Design Quality Lenses

Review 使用四项透镜尝试推翻当前设计或实现，不要求 Reviewer 输出四段式报告：

- 确认边界：检查当前 evidence 最多能推出什么，不能把 schema、测试或 artifact 存在扩大成产品完成。
- 不变量优先：检查实现是否真正消费并维持核心语义，而不是只增加字段、命令或入口。
- 反例先行：尝试最低成本的重放、删除、矛盾状态、fallback、恢复失败或手写 artifact 绕过。
- 独立证明：识别测试、Gate、archive 是否共享同一 evidence source 或判断函数造成证据共模。

Evidence source（证据来源）独立不等于 reasoning source（推理来源）独立。同一 Agent 即使使用不同验证路径仍可能共享推理共模；需要第二观察者时使用现有独立 Review 策略。本纪律只通过现有 `issues[]` 表达发现，不新增 phase、不新增 schema，也不新增 review 次数或 final-decision authority。

## 执行前必须确认

- 必须：review against proposal, design, acceptance, and actual diff rather than general preference.
- 必须：classify each issue with severity, evidence, recommendation, and lifecycle status.
- 必须：verify review feedback technically before accepting, rejecting, or converting it into a build task.

## 协议输入

- diff against the intended base branch
- `.xian-harness/changes/{change-id}/proposal.md`
- `.xian-harness/changes/{change-id}/design.md`
- `.xian-harness/changes/{change-id}/acceptance-criteria.md`
- `.xian-harness/changes/{change-id}/verify/verify-result.json`
- existing `.xian-harness/changes/{change-id}/gate/quality-issues.json` when available

## 执行流程

1. Review for correctness, regressions, missing tests, security, and policy violations.
2. Record issues with id, severity, status, file, evidence, and recommendation.
3. Require fixes for P0/P1 issues.
4. Allow P2 only with explicit accepted-risk reason.
5. Update review documents or issues.

## 分级指引

- Small: review the quick verify and quick close evidence first; if the change is still low-risk and no P0/P1 issue exists, `closed` is acceptable.
- Standard/Major: review against full verification, gate, and archive expectations.
- If review finds protocol, state-machine, gate, archive, pack, skill contract, quality mechanism, security, migration, or broad runtime risk, require upgrade before closure.

## 常见分支

- 常规路径：按 `nextAction` 和当前 change state 选择下一步。
- 证据不足：先补 verify evidence 或明确记录 blocked reason。
- 发现职责不匹配：交接到 `xian-open` 重新路由。

## 确定性工具

- `git diff --stat`
- `git diff --check`
- `xian-harness review agent-pair <change-id> --action <spec.review|build.review> --target <target-project> --json`
- `xian-harness gate issues <change-id> --target <target-project> --json`
- targeted tests when a issue can be reproduced

默认 Agent Pair reviewer 是独立于 Builder、read-only 且按 Change 持续存在的 logical Reviewer，不需要 `--command`。同一 Change 的 spec.review、build.review 和 Candidate delta rereview 恢复同一 provider session；多个 Candidate 仍分别产生不可变 Review attempt。session pointer 只存在 ignored local area，不是 correctness authority。项目显式选择 `claude-code` 的 `glm-backed` profile 时，只从项目内 ignored local 文件 `.xian-harness/local/agent-pair-providers.json` 读取 provider 配置；先通过 `xian-harness pack status --target <target-project> --json` 检查 `requiredLocalConfiguration`，不得从全局环境变量补齐或把 secret 写入治理 artifact。

## 必需证据

- Issues list or clear statement that no issues were found.
- File/line references for code issues.
- Verification command evidence for fixed issues.
- Accepted-risk reason when a issue remains open by policy.

## 事实映射

- Review issues -> `.xian-harness/changes/{change-id}/gate/quality-issues.json` or review report
- Risk decisions -> `.xian-harness/changes/{change-id}/gate/gate-result.json`
- Feedback handling -> `.xian-harness/changes/{change-id}/tasks.md` or issue lifecycle

## 参考样例

- 本 change 的 GLM review 反馈：外部 review 转化为 AC 和任务约束的参考。

## 自检清单

- 是否遵守当前 Interaction Budget？
- 是否从 canonical facts 而不是聊天记忆开始？
- 是否留下了可复查的 evidence 或明确说明无需证据？
- 是否没有越过当前 skill 的职责边界？

## 输出

- Review report.
- Structured issues.
- Risk decisions.

## 交互预算

- 必须：obey the current hook-provided Interaction Budget before reading files or running commands.
- 必须：keep chat-mode requests tool-free unless the user explicitly asks for inspection, snapshot refresh, deep audit, or change execution.
- 必须：require explicit deep-audit or change intent before reading pack state, workbench, quality-gate, archive, or other large project status artifacts.

## 交接规则

- 输出时先说明当前结论、证据缺口和风险；末尾输出 `下一步建议：<中文下一步>`，空一行后单独输出 `$xian-xxx`，再空一行输出 `直接回复“继续”即可进入该步骤。`；不要在首屏附加“因为...”。

- P0/P1 issue -> `xian-build`.
- Fixed issue -> `xian-verify`.
- All issues closed and verification exists -> `xian-gate`.

## 约束与原因

- Issues first, summary second。 原因：违反该约束会破坏 xian-review 的协议边界、证据链或 profile 隔离。
- 不要批准未解决的 P0/P1 issues。 原因：违反该约束会破坏 xian-review 的协议边界、证据链或 profile 隔离。
- 不要用 review 替代测试或 smoke evidence。 原因：违反该约束会破坏 xian-review 的协议边界、证据链或 profile 隔离。
