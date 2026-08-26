---
name: xian-pack-governance
description: Use when modifying harness pack manifest, templates, sync logic, or profile boundaries.
---

# xian-pack-governance

## 用途

治理 Harness Pack、profile overlay、manifest、模板和同步边界。

## 触发条件

Use this skill before changing `harness-pack/manifest.yaml`, `harness-pack/base/`, `harness-pack/profiles/{profile}/`, installable templates, profile overlays, pack status rules, or pack sync behavior.

## 协议输入

- `harness-pack/manifest.yaml`
- `harness-pack/base/`
- `harness-pack/profiles/{profile}/`
- `.xian-harness/skill-registry.json`
- `.xian-harness/bootstrap-context.json`
- `.xian-harness/pack-state.json`
- `docs/Harness开发测试环境隔离方案.md`

## 执行流程

1. Identify whether the change belongs to base, a vertical profile, an adapter, a template, or a generated target artifact.
2. Update manifest groups and profile includes before relying on file placement alone.
3. Keep base profile installable without vertical-only rules.
4. Keep profile overlay additions explicit and testable.
5. Let the Pack Runtime machine authority preflight and execute every public `pack sync` / `pack update`; this Skill does not decide rollout, mutation, rollback, conflict, mode, Git index, or final-status outcomes.

## Runtime machine authority

- `xian-agent-harness/src/protocol/pack.ts` is the public Pack policy consumer for rollout receipt, active change, dirty worktree, profile, tombstone, mode, Git index and final status.
- `xian-agent-harness/src/protocol/pack-mutation-transaction.ts` is the single local mutation coordinator for deterministic plans, recoverable locks, CAS rollback and source/target/index identity.
- A Skill instruction is explanatory only. It must not replace, weaken or duplicate either Runtime decision, and it must not turn `sync` into a lower-governance bypass.

## 确定性工具

- `xian-harness pack status --target <target-project> --profile base --json`
- `npm test -- --run test/pack.test.ts test/cli/pack.test.ts test/skill-contract.test.ts test/workbench/pack-profile.test.ts test/product-surface.test.ts`
- `rg --files harness-pack/base harness-pack/profiles`

## 必需证据

- Manifest group and profile include change.
- Pack status showing active and excluded groups.
- Installed file list or sync report when target assets change.
- Contract test proving profile isolation.
- Registry and bootstrap context evidence when installed facts change.

## Primary Asset Scope

Primary Asset Scope: Harness Pack and profile overlays

## 晋升规则

- Put cross-stack assets in base.
- Put vertical project rules in a profile overlay.
- Put target-generated evidence under target project `.xian-harness`, not inside the Harness Pack source.
- Keep templates installable and deterministic.
- Keep structured install facts in JSON or existing protocol files.

## 参考样例

- `fix-small-workbench-snapshot-path`: pack drift 和安装态同步风险参考。

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

- Skill content or activation change -> `xian-skill-governance`.
- Hook installation or runtime behavior -> `xian-hook-governance`.
- Agent role installation or routing -> `xian-agent-governance`.
- Boundary issue -> `xian-gate`.

## 约束与原因

- 不要把 profile-specific 资产复制到 base。 原因：违反该约束会破坏 xian-pack-governance 的协议边界、证据链或 profile 隔离。
- 不要用修改目标 case 文件掩盖 Harness Pack 源问题。 原因：违反该约束会破坏 xian-pack-governance 的协议边界、证据链或 profile 隔离。
- 不要在缺少 manifest 归属时仅依赖目录存在。 原因：违反该约束会破坏 xian-pack-governance 的协议边界、证据链或 profile 隔离。
- 不要在缺少 pack tests 时修改可安装资产。 原因：违反该约束会破坏 xian-pack-governance 的协议边界、证据链或 profile 隔离。
