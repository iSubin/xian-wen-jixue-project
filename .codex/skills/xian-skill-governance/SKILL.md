---
name: xian-skill-governance
description: Use when authoring Harness-owned Skill sources, scoped development mirrors, references or registry triggers; not unrelated third-party skills.
---

# xian-skill-governance

## 用途

把 skill 资产作为可执行流程契约治理，而不是松散说明文档。

## 触发条件

在修改 Harness-owned Skill 的 source、同 Scope 开发镜像、references 或 registry 触发描述时使用；不覆盖无关第三方 Skill，也不由编写授权推导真实安装权限。

## 协议输入

- `harness-pack/registry/skills.json`
- `harness-pack/manifest.yaml`（generated projection）
- `.xian-harness/skill-registry.json`（installed generated projection）
- `harness-pack/base/.codex/skills/{skill}/SKILL.md`
- `harness-pack/profiles/{profile}/.codex/skills/{skill}/SKILL.md`
- `.xian-harness/changes/{change-id}`
- `docs/Harness开发测试环境隔离方案.md`

## 执行流程

1. Decide whether the requested change updates an existing skill or creates a new skill.
2. Choose the owning profile before writing content.
3. Keep frontmatter trigger-focused: `description` says when to use the skill, not the workflow.
4. Update `harness-pack/registry/skills.json` when the skill list, role, group, layer, activation, description, or keywords change; do not hand-edit generated manifest/registry projections.
5. Run `npm run pack:registry:compile`, then `npm run pack:registry:check` to materialize and verify every Pack-source projection.
6. Add or update contract tests that prove the skill is generic, profile-isolated, and discoverable.
7. Route command-like assets through the command naming rules before treating them as ordinary skills.

## 常见分支

- 常规路径：按 `nextAction` 和当前 change state 选择下一步。
- 证据不足：先补 verify evidence 或明确记录 blocked reason。
- 发现职责不匹配：交接到 `xian-open` 重新路由。

## 确定性工具

- `npm test -- --run test/skill-contract.test.ts test/skill-registry.test.ts`
- `npm run pack:registry:compile && npm run pack:registry:check`
- `npm test -- --run test/pack.test.ts`
- `xian-harness pack status --target <target-project> --profile auto --json`
- `rg -n "name:|description:|Primary Asset Scope" harness-pack/base/.codex/skills harness-pack/profiles`

## 必需证据

- Skill path and owner profile.
- `harness-pack/registry/skills.json` canonical entry and generated manifest/registry check.
- Installed `.xian-harness/skill-registry.json` compatibility when activation, role, routing, or group changes.
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
7. 同一 accepted Scope 明确包含 Pack source、当前仓库开发镜像和 references 时，可配对编写并验证 bytes/引用闭包；Pack source 仍是唯一分发源，开发镜像不是 authority。canonical registry 经现有 compiler/check 生成；仅本仓已授权的开发 registry 可取 compiler base 输出原 bytes，同步不改 pack-state 或 installed 账本。真实用户/项目安装、Pack rollout 仍须独立授权与现役 exact-source Release Verify，不能用开发镜像一致冒充安装完成。

## 晋升规则

- Promote to base only when the skill applies across project stacks.
- Promote to a vertical profile when the trigger depends on that profile's markers, commands, or technology rules.
- 不要create a new skill when a narrower update to an existing skill is enough.
- Keep machine-readable activation and routing in `harness-pack/registry/skills.json`; installed `.xian-harness/skill-registry.json` is its generated compatibility projection.
- Keep human-readable process rules in `SKILL.md`.

## 参考样例

- `standardize-chinese-skill-contract-v2`: 中文 Skill 契约 v2 和 authoring 元流程参考。

## 自检清单

- 是否判断了 create vs update？
- 是否确认 owner profile？
- 是否套用中文 Skill 契约 v2？
- 是否更新 canonical registry、运行 compiler/check，并补齐 tests 与 pack status 证据？

## 交互预算

- 遵守当前实际提供的 Interaction Budget；没有提供时不虚构 hook 预算或额外审批。
- 普通聊天保持 tool-free，除非用户明确要求检查；已授权任务的必要定向读取不另索 deep-audit。
- 不为无关问题预读大型 pack state、workbench、quality-gate、archive 或历史材料；专用 release 的等待与失败边界不被本段覆盖。

## 交接规则

- 当前请求携带 publish intent 且不存在真实阻塞时，按 current nextAction 在同一任务内连续完成已授权工作，不等待重复许可；只读 Review 不获得写入权。
- 当前请求不携带 publish intent 时，自然收尾：说明结论、必要风险和仍待决定的具体问题，不强制固定末尾、skill 行或回复“继续”；仅真实待决问题才请求明确选择。已有 Runtime 路由时从运行时 `nextAction` 开始，不把建议变成授权。

- Hook trigger or bootstrap behavior -> `xian-hook-governance`.
- Profile install boundary -> `xian-pack-governance`.
- Reusable lesson source -> `xian-experience`.
- Gate enforcement gap -> `xian-gate`.

## 约束与原因

- 不要在缺少 manifest 和 registry 归属时引入 skill。 原因：违反该约束会破坏 xian-skill-governance 的协议边界、证据链或 profile 隔离。
- 不要用宽泛 skill 名称隐藏多个无关职责。 原因：违反该约束会破坏 xian-skill-governance 的协议边界、证据链或 profile 隔离。
- 不要把 profile-specific 触发规则放进 base skill。 原因：违反该约束会破坏 xian-skill-governance 的协议边界、证据链或 profile 隔离。
- 不要让 hook 代码成为 skill 激活规则的唯一来源。 原因：违反该约束会破坏 xian-skill-governance 的协议边界、证据链或 profile 隔离。
