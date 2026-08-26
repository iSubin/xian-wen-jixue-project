---
name: xian-agent-governance
description: Use when adjusting agent roles, handoffs, trigger sources, or role contracts.
---

# xian-agent-governance

## 用途

治理 Agent 和角色资产，确保职责、输入、输出、权限和交接规则在自动化或暴露到 Workbench 前保持显性。

## 触发条件

Use this skill before adding an Agent role, changing Verifier or Gatekeeper responsibilities, routing work to a subagent, or translating a role document into a Harness skill, command, hook, or Workbench action.

## 协议输入

- `.xian-harness/agents/`
- `.xian-harness/changes/{change-id}`
- `.xian-harness/changes/{change-id}/verify/evidence/`
- `.xian-harness/changes/{change-id}/gate/`
- `.xian-harness/skill-registry.json`
- `harness-pack/manifest.yaml`
- `harness-pack/base/.xian-harness/protocol/templates/agents/agent-role-contract.md`

## 执行流程

1. Start from `.xian-harness/protocol/templates/agents/agent-role-contract.md` for every new or changed role.
2. Fill Role Boundary, Tool Permissions, Trigger Sources, Fact Sources, Output Contract, Issue Model, State Event Mapping, Profile Boundary, and Verification Commands.
3. Define the role's inputs and outputs as protocol facts, not chat memory.
4. Decide whether the role is implemented by a skill, command, hook, Workbench action, or future SDK agent.
5. Keep Builder, Verifier, Reviewer, Doc Steward, and Gatekeeper approval responsibilities separate.
6. Add tests or gate evidence proving the role cannot approve its own work when that would violate quality discipline.

## 确定性工具

- `xian-harness workbench status <change-id> --target <target-project> --json`
- `xian-harness check <change-id> --target <target-project> --json`
- `npm test -- --run test/agent-workbench.test.ts test/gate.test.ts`
- `rg -n "Builder|Verifier|Reviewer|Gatekeeper|Workbench" docs xian-agent-harness/src xian-agent-harness/test`

## 必需证据

- Role definition and boundary.
- Completed Agent Role Contract when role behavior, permission, trigger, issue model, or state event mapping changes.
- Input and output artifact paths.
- Handoff rule to the next role or state.
- Verification or gate evidence when the role affects approval.
- Registry entry when the role changes skill activation or routing.

## Primary Asset Scope

Primary Asset Scope: agent and role assets

## 晋升规则

- Translate external role documents into Harness roles, skills, hooks, or Workbench actions instead of copying them blindly.
- Use Markdown for role behavior and JSON for state, evidence, routing, and summaries.
- Keep independent verification separate from build execution.
- Treat Gatekeeper as decision orchestration, not another Builder.
- Treat severity reports as a reusable Issue Model, while keeping project-specific rules outside the base profile.
- Treat project document maintenance as Doc Steward behavior, and require explicit output paths and trigger sources before writing docs.

## 参考样例

- 暂无；当后续出现 Agent role / handoff 类归档 change 时补齐。

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

- Skill-based role behavior -> `xian-skill-governance`.
- Hook-based auto-trigger behavior -> `xian-hook-governance`.
- Workbench display or action routing -> `xian-workbench`.
- Gate decision logic -> `xian-gate`.

## 约束与原因

- 不要let a Builder Agent self-approve a change。 原因：违反该约束会破坏 xian-agent-governance 的协议边界、证据链或 profile 隔离。
- 不要create an Agent role without explicit inputs and outputs。 原因：违反该约束会破坏 xian-agent-governance 的协议边界、证据链或 profile 隔离。
- 不要map a role to both execution and approval unless the protocol allows it。 原因：违反该约束会破坏 xian-agent-governance 的协议边界、证据链或 profile 隔离。
- 不要depend on vendor-specific Agent file formats as the only source of truth。 原因：违反该约束会破坏 xian-agent-governance 的协议边界、证据链或 profile 隔离。
