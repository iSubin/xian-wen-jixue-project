---
name: xian-experience
description: Use when reviewing or promoting reusable AI coding experience captured during project work.
---

# xian-experience

## 用途

把 change 中出现的可复用经验显性化为候选项，再决定是否晋升到协议、profile、skill 或模板资产。

## 触发条件

当以下场景出现时使用：a change reveals a repeated failure mode, a reusable practice, an upstream mechanism worth absorbing, or a case-specific lesson that may affect future work.

## 协议输入

- `.xian-harness/changes/{change-id}/summary.md`
- `.xian-harness/changes/{change-id}/gate/quality-gate.md`
- `.xian-harness/changes/{change-id}/workbench/summary.md`
- `.xian-harness/skill-registry.json`
- `git diff --name-only HEAD --` when the target project is a Git repository
- `docs/archetype-research/` when the source is external research
- Boundary: `xian-project-research` owns research output governance; `xian-experience` owns promotion review.
- Process sources such as commits, reviews, conversations, debug sessions, and benchmark notes

## 执行流程

1. Identify the experience source and the exact evidence that supports it.
2. Classify it as `base`, profile-specific, adapter-specific, or research-only.
3. Assign quality metadata: candidate type, signal sources, Why, confidence, dedupe key, recurrence, scope, risk, suggested action, and suggested target asset.
4. Decide whether the experience should become a skill update, registry entry, template, checklist, or documentation note.
5. Keep profile-specific lessons out of the base profile unless they are generalized.
6. Record rejected or deferred candidates with the reason when evidence is weak, low-confidence, or overfit.
7. Treat Git diff signals as candidate evidence only; they still require review or promotion before becoming long-lived assets.
8. For process-sourced lessons without an active archived change, record a project-level candidate first; do not directly edit long-lived assets.
9. Mark old unresolved process-sourced candidates as `stale` instead of deleting them; stale is cleanup, not rejection or promotion.
10. Classify process candidates explicitly; do not use `practice-doc` as a catch-all for product discussions, diagnostics, or pending proposals.
11. Treat `docs/archetype-research/` as research input produced by `xian-project-research`; review only reusable `research-only` candidates for promotion.

## 确定性工具

- `xian-harness experience add --target <target-project> --source-type <commit|review|conversation|debug|benchmark> --source <source> --title <title> --why <why> --summary <summary> --candidate-type <type> --json`
- `xian-harness experience stale --target <target-project> --older-than-days <days> --reason <reason> --json`
- `xian-harness workbench status <change-id> --target <target-project> --json`
- `xian-harness gate issues <change-id> --target <target-project> --json`
- `xian-harness experience review <change-id> --target <target-project> --json`
- `xian-harness experience promote <change-id> --target <target-project> --candidate <candidate-id> --json`
- `xian-harness pack status --target <target-project> --profile auto --json`
- `rg --files .xian-harness docs/archetype-research`
- `git diff --name-only HEAD --`

## 必需证据

- Source path of the lesson or research note.
- Candidate type, signal sources, confidence, recurrence, risk, and Why.
- Promotion decision and target asset path when promoted.
- Rejection reason when not promoted.
- Profile classification showing whether the lesson is generic or vertical.
- For process-sourced candidates: source type, source id/path, title, Why, summary, and the project-level candidate file.
- For stale cleanup: stale status, reason, age threshold, and confirmation that no candidate was deleted or promoted.

## 晋升规则

- Promote to `base` only when the practice applies to TypeScript, Python, Java, and generic product changes.
- Promote to a profile only when the lesson depends on that profile's stack or project markers.
- Promote to `.xian-harness/skill-registry.json` only when the lesson changes activation, routing, roles, commands, or evidence ownership.
- Promote to documentation when the lesson explains concepts but does not change execution behavior.
- 不要promote `low` or `blocked` confidence candidates.
- 不要promote `risk.level=high` candidates until the profile pollution, sensitive data, or overfitting risk is resolved.
- 不要promote a candidate without a concrete target asset or a generated promotion change.
- Use `experience promote` to create an asset-promotion change; do not edit long-lived assets directly from the source change archive.
- Process-sourced candidates are an intake queue, not approval; they need explicit review before promotion.
- Stale process candidates remain audit records; do not treat stale as rejected, accepted, or safe to delete.
- Use `engineering-practice` or `design-principle` for reusable lessons; use `product-decision`, `diagnostic-snapshot`, or `pending-proposal` for project-specific product artifacts that need routing, not automatic promotion.
- 不要record a conversation just because it is interesting; record it only when it has a clear reusable lesson or a concrete routing decision.

## 参考样例

- `docs/xian-harness/evidence/product-usage-fit-diagnosis-20260615.md`: 产品诊断沉淀为候选资产的参考。

## 自检清单

- 是否遵守当前 Interaction Budget？
- 是否从 canonical facts 而不是聊天记忆开始？
- 是否留下了可复查的 evidence 或明确说明无需证据？
- 是否没有越过当前 skill 的职责边界？

## 交互预算

- 必须：obey the current hook-provided Interaction Budget before reading files or running commands.
- 必须：keep chat-mode requests tool-free unless the user explicitly asks for inspection, snapshot refresh, deep audit, or change execution.
- 必须：require explicit deep-audit or change intent before reading pack state, workbench, quality-gate, archive, or other large project status artifacts.

## 交接规则

- 输出时先说明当前结论、证据缺口和风险；末尾输出 `下一步建议：<中文下一步>`，空一行后单独输出 `$xian-xxx`，再空一行输出 `直接回复“继续”即可进入该步骤。`；不要在首屏附加“因为...”。

- Candidate changes to profile assets -> `xian-asset-governance`.
- Candidate changes to verification, gate, or evidence rules -> `xian-gate`.
- Candidate changes to Workbench routing -> `xian-workbench`.

## 约束与原因

- 不要复制上游业务代码、专有 schema 或商业样例。 原因：违反该约束会破坏 xian-experience 的协议边界、证据链或 profile 隔离。
- 不要在未泛化前把单个项目特有教训提升为 base 规则。 原因：违反该约束会破坏 xian-experience 的协议边界、证据链或 profile 隔离。
- 不要只把可复用经验留在聊天中；必须记录到受治理资产。 原因：违反该约束会破坏 xian-experience 的协议边界、证据链或 profile 隔离。
