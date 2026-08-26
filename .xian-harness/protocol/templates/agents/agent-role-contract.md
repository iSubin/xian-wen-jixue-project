# Agent Role Contract

Template Contract: xian-harness/agents/agent-role-contract

## Template Quality Contract

| 项 | 内容 |
|---|---|
| Fact Sources | change workspace、Workbench snapshot、role input、role result、quality issues。 |
| Owner Role | Agent Steward / Gatekeeper Agent。 |
| Verification Commands | `xian-harness check {change-id} --target <target-project> --json`。 |
| Evidence Paths | `.xian-harness/agents/{change-id}/`。 |

## Role Summary

- Role name:
- Owner skill: `xian-agent-governance`
- Target profile: base / typescript / python / deployment-ops / custom
- Runtime shape: skill / command / hook / Workbench action / future Agent SDK worker
- Status: proposed / active / deprecated

## Role Boundary

说明该角色负责什么、不负责什么，以及是否允许影响 change 状态。

| 项 | 说明 |
|---|---|
| Primary responsibility | {role responsibility} |
| Explicit non-goals | {forbidden responsibilities} |
| Approval authority | none / verify-only / gate-only / human-required |
| State machine event | none / verified / quality-gate-checked / archived / custom |

## Tool Permissions

角色权限必须最小化。只读审查角色不应拥有写入权限；项目状态维护角色必须说明写入范围。

| Tool class | Allowed | Reason | Boundary |
|---|---:|---|---|
| Read / Grep / Glob | yes/no | {reason} | {paths} |
| Bash / deterministic CLI | yes/no | {reason} | {commands} |
| Write / Edit / Patch | yes/no | {reason} | {paths} |
| Network / external API | yes/no | {reason} | {approval or fallback} |

## Trigger Sources

| Trigger | Source | Required facts |
|---|---|---|
| Manual request | user prompt / command | {facts} |
| Change phase | build / verify / gate / archive | `.change-state.json` |
| Gate or review issue | quality issue / review report | `gate/quality-issues.json` |
| Project status update | docs sync / archive closure | `docs/项目状态.md` |

## Fact Sources

角色只能读取明确事实源，不应依赖聊天记忆。

| Fact source | Purpose | Required |
|---|---|---:|
| `.xian-harness/changes/{change-id}/acceptance-criteria.md` | 验收契约。 | yes/no |
| `.xian-harness/changes/{change-id}/.change-state.json` | 状态机 checkpoint。 | yes/no |
| `.xian-harness/changes/{change-id}/workbench/snapshot.json` | 下一步、证据和 route 摘要。 | yes/no |
| `.xian-harness/changes/{change-id}/gate/quality-issues.json` | issues 和阻断项。 | yes/no |
| `.xian-harness/skill-registry.json` | skill / profile 路由。 | yes/no |
| `harness-pack/manifest.yaml` | Pack 资产和模板登记。 | yes/no |

## Output Contract

| Output | Path | Required | Consumer |
|---|---|---:|---|
| Role report | `.xian-harness/agents/{role}/{change-id}.md` | yes/no | human / Workbench |
| Role result JSON | `.xian-harness/agents/{role}/{change-id}.json` | yes/no | CLI / state machine |
| Handoff update | `.xian-harness/changes/{change-id}/handoff.md` | yes/no | next role |
| Project doc update | `docs/项目状态.md` / `docs/待办清单.md` / `docs/需求文档.md` | yes/no | project next decision |

## Issue Model

Reviewer、Verifier、Gatekeeper 类角色必须用结构化 issues，而不是只写自然语言结论。

| Field | Meaning |
|---|---|
| `id` | 稳定问题编号。 |
| `severity` | blocker / warning / suggestion。 |
| `blocking` | 是否阻断下一阶段。 |
| `evidence` | 文件、命令、日志或规则来源。 |
| `recommendedFix` | 可执行修复方向。 |
| `ownerRole` | Builder / Verifier / Gatekeeper / Doc Steward / human。 |

## State Event Mapping

| Role result | Allowed event | Required evidence |
|---|---|---|
| verifier passed | `verified` | verify result / evidence inventory |
| gatekeeper passed | `quality-gate-checked` | gate result / quality issues |
| doc steward synced | none / custom | doc sync report |
| reviewer found blocking issue | none | issues report |

## Profile Boundary

| Profile | Allowed role behavior | Forbidden behavior |
|---|---|---|
| base | 通用角色、通用审查结构、通用文档同步。 | 项目特有代码规则和固定路径。 |
| typescript / python / deployment-ops | base 角色结构 + 对应 profile 资产。 | 把 profile-specific 规则回写到 base profile。 |
| references | 只读研究和机制提炼。 | 写入参考工程或复制商业代码。 |

## Verification Commands

- [ ] `npm test -- --run test/agent-workbench.test.ts test/skill-contract.test.ts`
- [ ] `npm test -- --run test/gate.test.ts test/workbench.test.ts`
- [ ] `xian-harness agent role-input --role verifier --change-id <change-id> --target <target-project>`
- [ ] `xian-harness agent role-result --role verifier --change-id <change-id> --target <target-project> --status passed`

## Change Notes

- 修改内容：
- 为什么修改：
- 影响范围：
- 回滚方式：
- 后续观察：
