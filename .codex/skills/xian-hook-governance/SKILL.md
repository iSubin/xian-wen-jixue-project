---
name: xian-hook-governance
description: Use when modifying codex or claude hooks, bootstrap, or forced skill routing.
---

# xian-hook-governance

## 用途

治理 hook runtime entrypoints、bootstrap 和 prompt activation，避免 hook 代码成为唯一事实源。

## 触发条件

Use this skill before changing `.codex/hooks`, `.claude/hooks`, `session-start`, `skill-forced-eval`, `user-prompt-submit`, bootstrap context loading, or hook fallback behavior.

## 协议输入

- `harness-pack/base/.codex/hooks/`
- `harness-pack/base/.claude/hooks/`
- `harness-pack/registry/hooks.json`
- `.xian-harness/bootstrap-context.json`
- `.xian-harness/skill-registry.json`
- `harness-pack/manifest.yaml`
- `.xian-harness/protocol/templates/hooks/hook-contract.md`
- `docs/Harness开发测试环境隔离方案.md`

## 执行流程

1. Identify which lifecycle event the hook controls: session start, prompt submit, pre-tool use, or stop.
2. Create or update a Hook Contract from `.xian-harness/protocol/templates/hooks/hook-contract.md`.
3. Fill Lifecycle Event, Runtime Adapter, Input Schema, Output Contract, Skip Conditions, Profile Boundary, and Verification Commands before changing hook behavior.
4. Check whether the hook reads registry, bootstrap context, pack state, cwd markers, or target project files.
5. Keep `harness-pack/registry/hooks.json`, Skill registry, and bootstrap context as the facts of record; hook code should execute installed projections, not replace or compile them.
6. Run `npm run pack:registry:compile`, then `npm run pack:registry:check`; do not hand-edit generated `.codex/hooks.json` or manifest Hook aliases.
7. Preserve only generic name-based fail-open behavior when the installed Skill registry is missing or malformed; do not add a second semantic keyword table.
8. Add hook tests for profile boundaries, reserved paths, malformed registry, and missing optional files.

## 确定性工具

- `npm test -- --run test/skill-registry.test.ts test/skill-contract.test.ts`
- `npm run pack:registry:compile && npm run pack:registry:check`
- `npm test -- --run test/pack.test.ts`
- `xian-harness pack status --target <target-project> --profile auto --json`
- `rg -n "skill-registry|bootstrap-context|reserved|profile" harness-pack/base/.codex/hooks harness-pack/base/.claude/hooks`

## 必需证据

- Hook path, lifecycle event, and canonical `harness-pack/registry/hooks.json` entry.
- Hook Contract path or reason the change does not need a contract update.
- Input fact files read by the hook.
- Test proving expected activation and non-activation.
- Pack status evidence when hook install behavior changes.
- Fallback rule and reason when legacy targets remain supported.

## Primary Asset Scope

Primary Asset Scope: Codex and Claude hooks

## 晋升规则

- Store hook-readable structured facts in JSON.
- Keep profile-specific hook behavior behind profile detection or overlay assets.
- Prefer registry-driven activation over hardcoded skill names.
- Remove fallback behavior only when pack migration or compatibility policy allows it.

## 参考样例

- `fix-small-workbench-snapshot-path`: hook / Workbench 状态路径问题的治理教训参考。

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

- New or changed skill activation target -> `xian-skill-governance`.
- Pack install or overlay change -> `xian-pack-governance`.
- Workbench visibility gap -> `xian-workbench`.
- Profile boundary issue -> `xian-gate`.

## 约束与原因

- 不要让 hook 代码成为 skill routing 的事实源。 原因：违反该约束会破坏 xian-hook-governance 的协议边界、证据链或 profile 隔离。
- 不要在 base 项目中激活垂直 skills。 原因：违反该约束会破坏 xian-hook-governance 的协议边界、证据链或 profile 隔离。
- 不要在 session bootstrap 时读取大型文档树。 原因：违反该约束会破坏 xian-hook-governance 的协议边界、证据链或 profile 隔离。
- 不要在没有测试时隐藏 hook 行为变更。 原因：违反该约束会破坏 xian-hook-governance 的协议边界、证据链或 profile 隔离。
