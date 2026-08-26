---
name: xian-cost
description: Use when estimating or recording time, token, command, commit, and artifact cost for work done.
---

# xian-cost

## 用途

估算和记录 change 的时间、token、命令、提交和 artifact 成本，让治理成本可观察。

## 触发条件

Use this skill after a change, after a learning run, or when the user asks whether a workflow is economically worthwhile.

## 协议输入

- `.xian-harness/changes/{change-id}/.change-state.json`
- `.xian-harness/changes/{change-id}/verify/verify-result.json`
- `.xian-harness/changes/{change-id}/gate/gate-result.json`
- `.xian-harness/releases/{change-id}/release-acceptance.json`
- `.xian-harness/interaction-policy.json`
- `.xian-harness/runtime/hook-decisions.jsonl`
- commit list, elapsed time, command count, and token usage when available

## 执行流程

1. Count elapsed time when known.
2. Count commits and changed files.
3. Count generated artifacts and verification commands.
4. Inspect `hookObservability` collection policy before treating hook runtime data as representative.
5. Inspect hook decision output and duration cost by mode when runtime hook logs exist.
6. Record command/test cost.
7. Recommend whether future similar tasks need full, tweak, hotfix, or note-capture mode.

## 确定性工具

- `git log --oneline --decorate`
- `git diff --stat <base>..HEAD`
- `xian-harness cost hooks --target <target-project> --json`
- `xian-harness gate status <change-id> --target <target-project> --json`
- `xian-harness workbench status <change-id> --target <target-project> --json`

## 必需证据

- Commit count and changed-file count.
- Verification command count and gate status.
- Artifact list under `.xian-harness/changes/{change-id}`, evidence, gate, release, archive, and workbench directories.
- Hook decision summary from `.xian-harness/runtime/hook-decisions.jsonl` when available.
- Hook collection policy (`enabled`, `sampleRate`, `metrics`, `decisions`) when discussing hook observability.
- Cost recommendation with reasoning.

## 参考样例

- 暂无；当后续出现 cost observability 或 artifact cost 类归档 change 时补齐。

## 自检清单

- 是否遵守当前 Interaction Budget？
- 是否从 canonical facts 而不是聊天记忆开始？
- 是否留下了可复查的 evidence 或明确说明无需证据？
- 是否没有越过当前 skill 的职责边界？

## 输出

- Cost summary.
- Hook collection status and sampling rate when hook observability is inspected.
- Hook output-bytes and duration summary by mode/skill when available.
- Suggested future mode.
- Notes for product roadmap or process tuning.

## 交互预算

- 必须：obey the current hook-provided Interaction Budget before reading files or running commands.
- 必须：keep chat-mode requests tool-free unless the user explicitly asks for inspection, snapshot refresh, deep audit, or change execution.
- 必须：require explicit deep-audit or change intent before reading pack state, workbench, quality-gate, archive, or other large project status artifacts.

## 交接规则

- 输出时先说明当前结论、证据缺口和风险；末尾输出 `下一步建议：<中文下一步>`，空一行后单独输出 `$xian-xxx`，再空一行输出 `直接回复“继续”即可进入该步骤。`；不要在首屏附加“因为...”。

- Expensive but valuable workflow -> keep full gate for similar risk.
- Overly heavy workflow -> `xian-open` should choose tweak/hotfix next time.
- Missing evidence -> `xian-verify` or `xian-gate` before cost judgement.

## 约束与原因

- 不要overfit all tasks into the heaviest workflow。 原因：违反该约束会破坏 xian-cost 的协议边界、证据链或 profile 隔离。
- Small tasks should stay lightweight unless risk is high。 原因：违反该约束会破坏 xian-cost 的协议边界、证据链或 profile 隔离。
- 不要present token/time numbers as exact if they were inferred。 原因：违反该约束会破坏 xian-cost 的协议边界、证据链或 profile 隔离。
- Hook `output_bytes` is context-injection cost evidence, not API token billing; do not convert it into exact tokens。 原因：违反该约束会破坏 xian-cost 的协议边界、证据链或 profile 隔离。
- Hook observability is sampled data and may be disabled by policy; do not treat missing runtime logs as zero cost。 原因：违反该约束会破坏 xian-cost 的协议边界、证据链或 profile 隔离。
- `xian-harness cost hooks` is read-only over collected samples. It must not imply that sampling is free or always enabled。 原因：违反该约束会破坏 xian-cost 的协议边界、证据链或 profile 隔离。
