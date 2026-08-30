---
name: using-xian-harness
description: Use when routing xian-harness work to the minimal relevant governed-lite or audit skill without forcing full lifecycle context.
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, skip this skill.
</SUBAGENT-STOP>

# using-xian-harness

## Purpose

`using-xian-harness` is a lightweight router for Xian projects. It chooses the smallest useful `xian-*` skill for the current situation and keeps ordinary context clean.

Default product path:

```text
open -> verify -> gate -> close
```

Audit path:

```text
verify -> gate/check -> finalize
```

The audit path is available for protocol, pack, profile, security, release/archive/gate/verify behavior, production, customer delivery, or explicit deep-audit work. `finalize` writes release evidence and archive readiness facts as one default closeout step; `release accept` and `archive plan` are expert diagnostics, not the everyday route. It is not the default for ordinary governed changes.

## Phase Fact Boundary

Harness work advances by consuming phase-owned facts:

- `spec` owns requirement facts and writes `.xian-harness/changes/<change-id>/spec/spec-result.json`.
- `build` owns implementation facts and writes `.xian-harness/changes/<change-id>/build/build-result.json`.
- `verify` owns fresh command evidence and writes `verify.json` plus command logs.
- `gate`, `release`, and `archive` consume those facts for decision and closeout; they do not generate, repair, or backfill upstream `spec` / `build` facts.

If gate or closeout reports `upstream-blocker`, route back to the responsible upstream phase:

- missing or invalid spec facts -> `xian-spec`
- missing or invalid build facts -> `xian-build`
- stale or missing command evidence -> `xian-verify`

Do not treat a missing upstream phase result as a generic closeout problem, and do not recommend repeated full verify/finalize runs unless the changed paths genuinely require fresh command evidence.

## Routing Model

```text
chat -> no harness flow
project status -> read-only status / next
governed change -> one skill at a time; publish intent continues in the same task
audit change -> full governance path
```

不要为纯聊天加载完整 change 流程。用户只是问概念、命名、解释或讨论方向时，先回答问题；只有当用户要求 inspect、execute、change、verify、gate、commit、push、archive、batch 或 project status 时，才进入 Harness 工具链。

## Decision Steps

1. Check whether the current cwd is a Xian project by looking for `.xian-harness/` or AGENTS.md Xian instructions.
2. Read `.xian-harness/state.yaml` only when the request is a change/project workflow request or when an active change may affect the answer.
3. If there is an active change, follow its `nextAction` and select one next skill. When the current request carries publish intent, repeat this selection in the same task after each successful phase until Git delivery completes.
4. If there is no active change and the user gives a concrete task, route to `xian-open`.
5. If the request is only "继续 / 下一步 / go", route to `xian-next` or `xian-harness continue --target . --json`.
6. If the owner explicitly asks for a version release, release candidate, version bump, changelog, tag, Pack, registry, or deploy publication, route to `xian-release`; ordinary commit/change publication must not select it. 修复 Release suite、准备普通 push、Reviewer 建议运行 full suite 或历史 Release Verify 失败，都不能推导新的 release intent。
7. If the request asks for commit, push, dirty worktree closeout, or delivery close without an explicit version release, route to `xian-commit`.
8. If the request is project status, docs status, baseline, or current direction, prefer read-only project status/continue commands.

## Continuous Change Host Loop

当用户显式要求连续处理时，Agent Host 在每个边界重新读取 current facts，不在 Harness Core 中创建 Auto-Next scheduler、runtime state、lease 或 events：

```bash
xian-harness continue --target . --json
xian-harness change list --parked --target . --json
```

- 存在 active change 时，按 `continue` 返回的 current `nextCommand` 和 skill 路由完成该 Change。
- `activeChange=null` 时，只从 owner 本次明确授权的 parked 列表中选择依赖已满足的一项，再走正常 `change activate` 与单 Change lifecycle。
- 每个 Change terminal 后重新读取 Git tree、active change 和 parked facts；blocked、空列表或选择不唯一时停止并报告。
- Host loop 只是 session-local coordination policy（会话内协调策略），不持久化第二套 run state，也不跳过 Review、Verify、Gate、Result、commit 或 release boundary。

## Host Batch Dispatch Loop

当 owner 一次授权多个 Change 时，当前主 Agent是唯一 coordinator，并用 session-local `HostBatchPlan` 保存声明顺序与依赖；不得把该计划写入 Harness canonical facts，也不得要求 owner 逐项回复“继续”。

1. 每个 Change 边界重新读取 `change list --parked`、`continue`、Git tree 与 `activeChange`，只推进 owner 已授权且依赖满足的一项。
2. 普通串行批次在当前 session 连续执行；只有真实并行、用户明确要求、无法归因的 dirty worktree 或长时间高风险实验才使用 bounded worktree executor。
3. 每个 executor 只完成一个 Change 的 activate、implement、targeted stabilization、Formal Verify、Gate、finalize 与 commit；不得选择下一项、运行 integration checkpoint 或 push。
4. 当前 Change terminal 后，主 Agent重新读取 canonical facts，确认 `activeChange=null`、commit/tree identity 一致，再推进 `HostBatchPlan` 的下一项。
5. 全部 Change 完成后，仅主 Agent执行 shared final checks 与当前 Git delivery；只有 owner 明确形成 immutable release candidate 时，才在同一 clean tree 上单独运行一次 Release Verify。普通 batch、代码 churn、high fanout 或风险分类本身都不触发 full suite，也不建立第二套 integration authority。
6. 长操作期间只消费 `continue` 或 `project status` 返回的 `progress` machine facts；当状态为 `quiet`/`stalled` 时，主 Agent按不超过 60 秒的单一间隔转述安全摘要。不得从聊天历史、chain-of-thought、raw stdout 或 worker 自述重建进度，也不得让 `progress` 参与 lifecycle、Gate、retry、release 或 push 裁决。

这只是 Host Skill policy：不新增 Agent role、daemon、second scheduler、persisted batch/session schema、CLI command、phase、receipt 或 compatibility reader。

## Minimal Skill Selection

| Situation | Skill |
|---|---|
| New concrete demand | `xian-open` |
| Bare continuation / next direction | `xian-next` |
| Requirements or acceptance unclear | `xian-spec` |
| Design/risk/architecture decision needed | `xian-design` |
| Implementation tasks approved | `xian-build` |
| Fresh command evidence needed | `xian-verify` |
| Gate decision needed | `xian-gate` |
| Governed close or dirty worktree closeout | `xian-commit` |
| Audit finalize closeout | `xian-archive` |
| Explicit version release, release candidate, changelog, or tag | `xian-release` |
| Pack/profile/skill/hook asset governance | related governance skill |

Choose one primary skill at a time. Do not stack multiple skills just because they exist.

一次只选择一个 primary skill 不等于结束当前任务。当前请求携带 publish intent 且不存在真实阻塞时，完成当前 skill 后由同一主 Agent 在同一任务内继续选择下一个 skill，直到 archive / close、commit 和 push 完成；只有明确 release intent 才另行运行 Release Verify。

## Default Governed Flow

For ordinary runtime code, tests, docs, and small product fixes:

```text
xian-open -> xian-verify -> xian-gate -> xian-commit / close
```

Spec, design, plan, review, workbench, version release, and archive remain available when they add value, but they are not mandatory mental steps for every governed change. `xian-release` is never inferred from an ordinary commit, change, archive, or push.

路由到 `xian-release` 时，Host 必须把 owner 明确给出的发布目的编译成结构化 `ReleasePurpose`（`kind + target`），并在 `release verify`、`release commit/status/import/publish` 全链传递同一值。Core 只验证该结构化 purpose 与 immutable candidate、Result Commit 和 Publication Intent 一致；Core 不从自然语言、普通开发状态或 Agent 建议自行推断 owner 授权。

## 产品范围与治理深度分离

进入 substantial implementation（实质实现）前，Host 必须显式给出：

- `Requested outcome`：owner 本轮要求的可观察结果。
- `Must-have capabilities`：实现该结果不可缺少的能力；不能把证据要求写成产品能力。
- `Existing mechanisms to reuse`：当前可复用的 Runtime、Pack、CLI 或项目机制。
- `Explicitly deferred items`：非必要 hardening、generalized recovery 和 platform capability；记录为 `non-blocking deferred risks`，不吸收到当前 Scope。
- `Route/lane evidence`：选择治理深度的当前事实，以及相对更轻/更重 lane 的理由。

按以下优先级裁决：

1. 当前 Runtime command result 若提供本 Change 的 `tierDecision.riskSignals`、`runtimePlan.budget.riskSignalIds` 或 `structured Verify/Gate blockers`，消费这些 current machine facts；它们只能提高 Review、Verify、Gate 和 evidence 深度，不能扩展产品能力。
2. 上述 current machine facts 不存在时，检查 concrete changed paths 和 intended side effects。`keyword-only` 的 production、deployment、delivery 或 security 文本不是 capability、Scope 或 operational authority。
3. `owner-authorized Scope` 始终约束产品结果。ordinary 与 audit route 面对同一 requested outcome 时，`capabilityDiff` 必须为空；治理深度只改变 evidence obligations。`mid-task owner scope contraction` 立即收窄后续实现，已发现但非必须的风险进入 deferred items。
4. `production helper authoring` 可因 executable-surface risk 进入更深治理，但不等于 `real production execution`；真实外部变更必须另有 `separate explicit operational authorization`。read-only review 不获得 mutation authority。

| Scenario | Expected decision |
|---|---|
| current machine risk facts | Raise evidence obligations only; keep `owner-authorized Scope` and `capabilityDiff` unchanged. |
| production-keyword-only request | Do not escalate capability or authorize mutation; inspect concrete paths and side effects. |
| production helper authoring | Deeper evidence is allowed; no real production operation is authorized. |
| real production execution | Require `separate explicit operational authorization` before mutation. |
| read-only review | Keep mutation authority absent. |
| mid-task owner scope contraction | Stop or remove out-of-scope implementation; the narrower owner boundary wins. |
| non-blocking deferred risks | Record them without expanding the current capability or Scope. |

不得新增 phase、schema、scheduler、daemon、persistent authority、generalized recovery 或 canonical Scope object 来实现本规则。

## Audit Trigger

Use this audit trigger when the request touches higher-risk Harness behavior.

Escalate to audit when the request touches any of these:

- protocol core, state machine, change lifecycle, projection, or event/reducer behavior
- gate, verify, release, archive, evidence inventory, or quality mechanism behavior
- Harness Pack, profile isolation, registry, skill contracts, hook contracts, or asset distribution
- security, sandbox, command execution safety, secrets, permissions, production data, deployment, customer delivery
- broad cross-module runtime behavior or migration/compatibility logic

When audit is triggered, keep full verification/gate/finalize evidence; release/archive artifacts remain internal facts generated by finalize. When audit is not triggered, keep the governed flow lightweight.

## State Discipline

- Do not create a second active change.
- Do not open a new change to manage a mistaken existing change.
- Do not bypass `nextAction` when an active change exists.
- Do not use `git add -A`, `git reset --hard`, `git clean`, `git push --force`, or `git commit --no-verify`.
- Attribute dirty worktree files before staging.
- Preserve user changes you did not make.

## Context Hygiene

- Prefer summaries and JSON outputs over heavy workbench/archive evidence unless deep audit is requested.
- Do not read large pack status, quality gate, release, archive, workbench, or historical evidence just to answer chat.
- Do not inject process text into user-facing answers unless it changes the next action.
- Keep Chinese user-facing communication concise; keep code identifiers, commands, paths, and protocol fields in English.

## Output Rule

When doing actual change work, report:

- current route
- active change id when relevant
- verification/gate/commit status when relevant
- one next action，仅在请求不携带 publish intent、存在真实阻塞或需要用户决策时作为 handoff 输出

When the request is chat, just answer the question.
