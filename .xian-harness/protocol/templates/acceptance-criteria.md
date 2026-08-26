# Acceptance Criteria: {change-id}

> Legacy Compatibility Template（旧版兼容模板）：本 root template（根模板）只服务旧入口和安装兼容；新 change 的权威验收模板是 `.xian-harness/protocol/templates/change/full/acceptance-criteria.md`，由 `templateRegistry.change.full.acceptanceCriteria` 登记。

## Change Goal

说明本 change 的业务目标、工程目标，以及为什么它可以进入 verify / gate / archive。

本文件是 change 的核心验收契约，不是普通备注。它必须让一个没有聊天上下文的新 Agent 能恢复：

- 这次 change 要完成什么。
- 哪些事实源是权威输入。
- 每条 AC 由什么规则和证据证明。
- 下游 Verifier、Gatekeeper、Workbench、Release、Archive 应该如何继续。

## Business Acceptance

- [ ] **AC-001** {business-acceptance}
- [ ] **AC-002** {business-acceptance}

## Technical Acceptance

- [ ] **AC-003** {technical-acceptance}
- [ ] **AC-004** {technical-acceptance}
- [ ] **AC-005** {technical-acceptance}

## Regression

- [ ] **AC-006** {regression}
- [ ] **AC-007** {regression}

## 关联事实源

| 类型 | 文件 | 用途 |
|---|---|---|
| Change State | [.change-state.json](./.change-state.json) | 记录当前 phase、mode、pause、next action。 |
| Proposal | [proposal.md](./proposal.md) | 定义业务背景和本次 change 的目标。 |
| Design | [design.md](./design.md) | 定义技术方案、边界和取舍。 |
| Tasks | [tasks.md](./tasks.md) | 定义 Builder 应完成的任务。 |
| Quality Policy | {quality-policy-path} | 定义 profile 级验证规则或 registry 规则。 |
| Gate Result | [gate/gate-result.json](./gate/gate-result.json) | 记录门禁输入、规则命中和裁决。 |
| Workbench Summary | [workbench/summary.md](./workbench/summary.md) | 给人和下一棒 Agent 阅读的一屏状态。 |
| Release Verify | {release-verify-path} | 校验发布证据清单、语义契约、skill 契约和命令契约。 |
| Archive Result | [archive/archive-result.json](./archive/archive-result.json) | 记录归档输入、关键 artifact 和归档结论。 |

## 验证规则引用

Gatekeeper 不从自然语言关键词推断 smoke；每条需要门禁裁决的 AC 必须在本表显式引用验证规则。执行载体可以是 smoke、unit test、E2E、static review 或 command，但必须能在 verify / gate evidence 中定位到结果。

command-anchor first（命令锚点优先）：执行载体必须优先写真实可执行命令、脚本、测试文件或明确证据路径。自然语言只能解释验收意图，不能替代 command-anchor，也不能让 Gatekeeper 从描述里猜测验证已完成。

| 规则 ID | 来源 | 负责 Skill | 执行载体 | 覆盖验收项 |
|---|---|---|---|---|
| `{rule-id}` | `{rule-source}` | `{owner-skill}` | `{verification-carrier}` | AC-001, AC-002 |
| `{rule-id}` | `{rule-source}` | `{owner-skill}` | `{verification-carrier}` | AC-003, AC-004 |

## 验收覆盖矩阵

| 验收项 | 事实源 | 验证规则 / 命令 | 验证证据 | 门禁 / 发布证据 |
|---|---|---|---|---|
| AC-001 | `{fact-source}` | `{rule-or-command}` | `{evidence-path}` | `{gate-or-release-path}` |
| AC-002 | `{fact-source}` | `{rule-or-command}` | `{evidence-path}` | `{gate-or-release-path}` |
| AC-003 | `{fact-source}` | `{rule-or-command}` | `{evidence-path}` | `{gate-or-release-path}` |

## Verification Commands

这些命令是验证规则的执行载体，不是验收契约本身。Review 时优先看“验收覆盖矩阵”和“验证规则引用”，再检查命令是否仍然能产生对应证据。不要只写 `startup + DB check` 这类自然语言组合；应写真实命令或脚本，例如 `{verification-command}`。

- [ ] **VC-001** `{verification-command}`
- [ ] **VC-002** `{verification-command}`

## 跨 Agent 推进

新 Agent 接手本 change 时，按以下顺序恢复上下文：

1. 读取 [.change-state.json](./.change-state.json)，确认当前 phase、mode、pause 和 next action。
2. 读取本文件，确认 AC 编号、关联事实源、验证规则引用和验收覆盖矩阵。
3. 读取 [gate-result.json](./gate/gate-result.json) 和 [quality-gate.md](./gate/quality-gate.md)，确认验收覆盖、registry、runner environment 和 open issues。
4. 读取 Workbench / Agent Worker Input，确认下一棒角色、推荐 skills 和 deterministic commands。
5. 读取 release / archive 产物，确认发布证据和归档输入没有断链。

如果上下文丢失，按以下链路恢复：

```text
AC 编号
  -> 关联事实源
  -> 验证规则引用
  -> 验收覆盖矩阵
  -> Verification Commands
  -> Gate / Release / Archive 结果
```

如果某条 AC 缺少证据，不允许直接宣布完成；应先补事实源、验证规则、smoke / test、verify evidence 或 gate / release 结果，再重新进入 Gatekeeper 判断。

## Out Of Scope

- {out-of-scope}
