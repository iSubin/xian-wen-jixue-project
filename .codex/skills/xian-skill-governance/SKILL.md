---
name: xian-skill-governance
description: Use when modifying harness skills, SKILL.md contracts, registry, or trigger rules.
---

# xian-skill-governance

## 用途

把 skill 资产作为可执行流程契约治理，而不是松散说明文档。

## 触发条件

在修改任何 `SKILL.md`、增删 skill 目录、更新 frontmatter、调整触发描述，或修改 `.xian-harness/skill-registry.json` 前使用。

## 协议输入

- `harness-pack/manifest.yaml`
- `.xian-harness/skill-registry.json`
- `harness-pack/base/.codex/skills/{skill}/SKILL.md`
- `harness-pack/profiles/{profile}/.codex/skills/{skill}/SKILL.md`
- `.xian-harness/changes/{change-id}`
- `docs/Harness开发测试环境隔离方案.md`

## 执行流程

1. Decide whether the requested change updates an existing skill or creates a new skill.
2. Choose the owning profile before writing content.
3. Keep frontmatter trigger-focused: `description` says when to use the skill, not the workflow.
4. Update `harness-pack/manifest.yaml` and `.xian-harness/skill-registry.json` together when the skill list, role, group, or activation changes.
5. Add or update contract tests that prove the skill is generic, profile-isolated, and discoverable.
6. Route command-like assets through the command naming rules before treating them as ordinary skills.

## 常见分支

- 常规路径：按 `nextAction` 和当前 change state 选择下一步。
- 证据不足：先补 verify evidence 或明确记录 blocked reason。
- 发现职责不匹配：交接到 `xian-open` 重新路由。

## 确定性工具

- `npm test -- --run test/skill-contract.test.ts test/skill-registry.test.ts`
- `npm test -- --run test/pack.test.ts`
- `xian-harness pack status --target <target-project> --profile auto --json`
- `rg -n "name:|description:|Primary Asset Scope" harness-pack/base/.codex/skills harness-pack/profiles`

## 必需证据

- Skill path and owner profile.
- Manifest skill group entry.
- `.xian-harness/skill-registry.json` entry when activation, role, routing, or group changes.
- Contract test proving required sections and profile isolation.
- Pack status evidence when the skill is installable.

## Primary Asset Scope

Primary Asset Scope: skills and skill registry entries

## Skill Authoring Flow

1. 先判断是更新现有 skill 还是创建新 skill；能窄改时不新增独立 authoring skill。
2. 新建或修改前先写 contract test，覆盖中文 Skill 契约 v2、profile 归属、description 触发条件和 registry 可发现性。
3. description 只描述触发条件，不写 workflow、protocol、evidence 或长流程摘要。
4. SKILL.md 使用中文 Skill 契约 v2；技术锚点、命令、字段名和路径保持英文。
5. 补齐“常见分支”、“参考样例”、“自检清单”和“约束与原因”段；暂无参考样例时说明补齐条件。
6. 每条约束必须写具体原因，引用协议边界、证据链、profile 隔离或已发生教训，不能写成笼统最佳实践。
7. 修改 installable skill 后同步 `harness-pack` 源、当前工作区 `.codex/skills`、registry/manifest 和 pack status 证据。

## 晋升规则

- Promote to base only when the skill applies across project stacks.
- Promote to a vertical profile when the trigger depends on that profile's markers, commands, or technology rules.
- 不要create a new skill when a narrower update to an existing skill is enough.
- Keep machine-readable activation and routing in `.xian-harness/skill-registry.json`.
- Keep human-readable process rules in `SKILL.md`.

## 参考样例

- `standardize-chinese-skill-contract-v2`: 中文 Skill 契约 v2 和 authoring 元流程参考。

## 自检清单

- 是否判断了 create vs update？
- 是否确认 owner profile？
- 是否套用中文 Skill 契约 v2？
- 是否同步 manifest、registry、tests 和 pack status 证据？

## 交互预算

- 必须：obey the current hook-provided Interaction Budget before reading files or running commands.
- 必须：keep chat-mode requests tool-free unless the user explicitly asks for inspection, snapshot refresh, deep audit, or change execution.
- 必须：require explicit deep-audit or change intent before reading pack state, workbench, quality-gate, archive, or other large project status artifacts.

## 交接规则

- 输出时先说明当前结论、证据缺口和风险；末尾输出 `下一步建议：<中文下一步>`，空一行后单独输出 `$xian-xxx`，再空一行输出 `直接回复“继续”即可进入该步骤。`；不要在首屏附加“因为...”。

- Hook trigger or bootstrap behavior -> `xian-hook-governance`.
- Profile install boundary -> `xian-pack-governance`.
- Reusable lesson source -> `xian-experience`.
- Gate enforcement gap -> `xian-gate`.

## 约束与原因

- 不要在缺少 manifest 和 registry 归属时引入 skill。 原因：违反该约束会破坏 xian-skill-governance 的协议边界、证据链或 profile 隔离。
- 不要用宽泛 skill 名称隐藏多个无关职责。 原因：违反该约束会破坏 xian-skill-governance 的协议边界、证据链或 profile 隔离。
- 不要把 profile-specific 触发规则放进 base skill。 原因：违反该约束会破坏 xian-skill-governance 的协议边界、证据链或 profile 隔离。
- 不要让 hook 代码成为 skill 激活规则的唯一来源。 原因：违反该约束会破坏 xian-skill-governance 的协议边界、证据链或 profile 隔离。
