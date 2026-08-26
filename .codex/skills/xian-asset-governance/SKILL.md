---
name: xian-asset-governance
description: Use when classifying AI assets, judging profile ownership, or handling contamination risk between profiles.
---

# xian-asset-governance

## 用途

治理 AI 资产分类、profile 归属和污染风险，避免把垂直经验误提升到 base。

## 触发条件

当经验、规则、profile 资产、hook、skill、Agent 角色、模板、命令或协议说明需要判断归属位置时使用。

## 协议输入

- `harness-pack/manifest.yaml`
- `.xian-harness/skill-registry.json`
- `.xian-harness/bootstrap-context.json`
- `harness-pack/base/`
- `harness-pack/profiles/{profile}/`
- `.xian-harness/changes/{change-id}`
- `docs/Harness开发测试环境隔离方案.md`

## 执行流程

1. Classify the asset as skill, hook, agent role, pack/profile asset, command, template, protocol, documentation, or research-only.
2. Decide whether the asset is installable, generated, documentation-only, or archival evidence.
3. Assign ownership to base profile, vertical profile, adapter, case fixture, or research archive.
4. Route concrete edits to the specialized governance skill:
   - Skill asset -> `xian-skill-governance`.
   - Hook asset -> `xian-hook-governance`.
   - Agent or role asset -> `xian-agent-governance`.
   - Pack, profile, template, or install boundary -> `xian-pack-governance`.
5. Require evidence that the selected route does not pollute another profile.

## 确定性工具

- `xian-harness pack status --target <target-project> --profile base --json`
- `npm test -- --run test/pack.test.ts test/skill-contract.test.ts test/skill-registry.test.ts`
- `rg --files harness-pack/base harness-pack/profiles`

## 必需证据

- Asset classification and owner profile.
- Specialized governance skill selected for the edit.
- Pack install/status evidence when installable assets change.
- Registry, hook, Workbench, or gate evidence when routing affects execution.

## Primary Asset Scope

Primary Asset Scope: asset classification and routing

## 晋升规则

- Use JSON for machine-readable registry, bootstrap, and state facts.
- Use Markdown for Agent-readable skill behavior, review notes, and conceptual docs.
- Use YAML only where the existing protocol or adapter policy already uses YAML.
- Keep vertical-only paths, commands, and native skills inside their profile overlay.
- Prefer updating an existing asset before creating a new one.

## 参考样例

- `docs/Xian协作治理Harness产品内核.md`: 产品资产分类和治理边界讨论参考。

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

- Skill creation or update -> `xian-skill-governance`.
- Hook behavior or bootstrap change -> `xian-hook-governance`.
- Agent role or responsibility change -> `xian-agent-governance`.
- Pack manifest, profile overlay, or template boundary -> `xian-pack-governance`.
- Reusable lesson discovered during asset work -> `xian-experience`.
- Profile boundary issue -> `xian-gate`.

## 约束与原因

- 不要把上游垂直 profile 资产复制到工作区根目录或 base profile。 原因：违反该约束会破坏 xian-asset-governance 的协议边界、证据链或 profile 隔离。
- 不要用修改目标 case 资产替代 Harness Pack 源资产修复。 原因：违反该约束会破坏 xian-asset-governance 的协议边界、证据链或 profile 隔离。
- 不要让通用资产名称掩盖 profile-specific 规则。 原因：违反该约束会破坏 xian-asset-governance 的协议边界、证据链或 profile 隔离。
- 分类后不要在本 skill 中执行专门编辑；交接给更窄的治理 skill。 原因：违反该约束会破坏 xian-asset-governance 的协议边界、证据链或 profile 隔离。
