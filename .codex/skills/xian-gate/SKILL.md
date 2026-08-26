---
name: xian-gate
description: Use when running or judging the quality gate for a change within the verify phase. Harness gate is the only pass/fail authority; gate is not a persisted ChangePhase.
---

# xian-gate

## 用途

基于 policy、issues 和验证证据做质量门禁判断。`xian-gate` 是 verify phase 内的裁决面，不是独立 persisted phase。

默认 governed-lite 主路径是：

```text
open -> verify -> gate -> close
```

Gate pass 后，ordinary governed change 应进入 governed close；只有 audit change、release/archive/gate/verify 机制变更、生产/客户交付或用户显式要求时，才进入 release acceptance / archive finalize 路径。

## 触发条件

Use this skill after verification, before release acceptance, before archive, or when a Workbench/Agent SDK board needs a quality decision. In the 5-phase lifecycle this work happens inside `verify`.

## 协议输入

- governed/lite 默认：`.xian-harness/changes/{change-id}/change.md`、`verify.json`、`gate.json`
- `.xian-harness/changes/{change-id}/acceptance-criteria.md`
- `.xian-harness/changes/{change-id}/spec/spec-result.json`
- `.xian-harness/changes/{change-id}/build/build-result.json`
- `.xian-harness/changes/{change-id}/verify.md`
- `.xian-harness/changes/{change-id}/verify/verify-result.json`
- adapter `verifyPolicy`
- `.xian-harness/changes/{change-id}/gate/`
- Harness Pack status and activation policy
- Builder Agent and Verifier Agent metadata when known

## 执行流程

1. Read policy and acceptance criteria.
2. Read upstream phase result facts before judging closeout readiness.
3. Prefer deterministic execution first.
4. Inspect generated issues and severity.
5. Decide whether Spec Agent, Builder Agent, Verifier Agent, or Human Owner owns the repair.
6. Return one status: `pass`, `needs-fix`, `fail`, `needs-human`, or `blocked`.

## 阶段事实边界

Gatekeeper 只消费事实并作裁决，不生成或修复上游阶段事实。

- `spec/spec-result.json` 缺失、invalid 或 non-pass 时，返回 `upstream-blocker`，下一步交给 `xian-spec`。
- `build/build-result.json` 缺失、invalid 或 non-pass 时，返回 `upstream-blocker`，下一步交给 `xian-build`。
- `verify.json` 缺失、failed 或 stale 时，返回 verification repair，下一步交给 `xian-verify`。
- release / archive 只处理终态证据和归档，不承担需求覆盖或实现覆盖判断。

不要把缺失的 spec/build facts 解释成“再跑一次完整 verify”或“finalize 自动补材料”。Gate 可以建议具体上游阶段，但不能替该阶段补写事实。

## 分级指引

- Small: full gate is skipped only after passing `quick-verify`, while the change remains non-upgraded `tier=small`, and no open P0/P1 or blocking Quality Issue exists.
- Standard: run the slim gate before archive. Keep verification, acceptance, runner environment, tier, and Quality Issue checks, but skip Major-only pack/registry/lifecycle/methodology audits unless an explicit pack audit is in scope.
- Major: run the full gate before release or archive, including pack status, registry, lifecycle, methodology, and profile contamination audits.
- If a Small change contains schema、state-machine、gate、archive、release、pack、profile、skill contract、security、migration、cross-module runtime、quality mechanism 或不可局部验证风险, require upgrade before close.
- `quality mechanism` includes gate rules, Quality Issue lifecycle, verification command registry, runner environment, acceptance coverage, release verify, archive guard, Workbench release routing, methodology provider, skill contract tests, registry consistency tests, and pack validation rules.
- `cross-module runtime` includes routing or state-flow changes across continue, state-machine, workbench, quick-lane, hook/context injection, trace, release, archive, or gate modules.
- Open P0/P1 issues always block quick close and archive.

### 真实项目 Lane Gate 判断

- lightweight lane：只有在 fresh verification 已覆盖实际改动、无 open P0/P1、无 blocking Quality Issue，且不涉及生产/交付升级信号时，才允许跳过 full gate 和 release/archive。
- production lane：必须检查生产数据、外部服务、备份/回滚、数据核对和启动 smoke 的证据；证据缺失时返回 `needs-fix`、`needs-human` 或 `blocked`，不能降级为 lightweight lane。
- delivery lane：必须保留 full gate、release acceptance、archive 和可复盘 evidence；客户交付、上线门禁和安全边界不能 quick-close。
- 当 acceptance rule 只写自然语言、没有 command-anchor（命令锚点）或明确证据路径时，Gatekeeper 应提示补充可执行验证载体。

## 常见分支

- 常规路径：按 `nextAction` 和当前 change state 选择下一步。
- 上游事实不足：返回 `upstream-blocker` 并路由到 `xian-spec` 或 `xian-build`。
- 命令证据不足：先补 verify evidence 或明确记录 blocked reason。
- 发现职责不匹配：交接到 `xian-open` 重新路由。

## 确定性工具

- `xian-harness check <change-id> --target <target-project> --json`
- `xian-harness gate status <change-id> --target <target-project> --json`
- `xian-harness gate issues <change-id> --target <target-project> --json`
- `xian-harness closeout preflight <change-id> --target <target-project> --json`
- repeated `--command` values for explicit verification commands when needed

## 必需证据

- governed/lite 默认：`.xian-harness/changes/{change-id}/gate.json`
- legacy/audit：`.xian-harness/changes/{change-id}/gate/gate-result.json`
- legacy/audit：`.xian-harness/changes/{change-id}/gate/quality-issues.json`
- legacy/audit：`.xian-harness/changes/{change-id}/gate/quality-gate.md`
- canonical `xian-harness pack status --target <target-project> --json` read model when Major or explicit pack audits require Pack status
- adapter policy artifact when an adapter is active

## 参考样例

- `harden-xian-next-user-facing-guidance`: gate pass 和 archiveAllowed 参考。

## 自检清单

- 是否遵守当前 Interaction Budget？
- 是否从 canonical facts 而不是聊天记忆开始？
- 是否留下了可复查的 evidence 或明确说明无需证据？
- 是否没有越过当前 skill 的职责边界？

## 输出

- Gate status and archive decision.
- Structured issues.
- Repair or release recommendation.

## 交互预算

- 必须：obey the current hook-provided Interaction Budget before reading files or running commands.
- 必须：keep chat-mode requests tool-free unless the user explicitly asks for inspection, snapshot refresh, deep audit, or change execution.
- 必须：require explicit deep-audit or change intent before reading pack state, workbench, quality-gate, archive, or other large project status artifacts.

## 交接规则

- 当前请求携带 publish intent 且不存在真实阻塞时，Gate pass 后由同一主 Agent 在同一任务中直接进入 close / archive 和 Git delivery；Gate fail 时留在当前任务内修复，不输出等待用户回复“继续”的 handoff。
- 当前请求不携带 publish intent 时，从运行时 `nextAction` 开始；末尾输出 `下一步建议：<中文下一步>`，空一行后单独输出 `$xian-xxx`，再空一行输出 `直接回复“继续”即可进入该步骤。`；不要在首屏附加“因为...”。
- 对 non-upgraded small hotfix，`quick-close` 是 terminal path；`xian-gate` 只在 quick close 被 open P0/P1、blocking issue、forcedUpgrade、deep-audit 或治理事实源风险拦住时介入。
- 表达层原则：中文优先，默认用自然中文给结论、必要风险和下一步；必须保留英文术语、协议字段、状态名或命令名时，紧跟中文括注解释；不写“流程报告 / Review 报告 / evidence 清单”式长篇；只有 deep-audit、gate、verify 或用户明确要求完整显性化时才展开治理细节。
- Default mapping: `pass` -> governed close for ordinary changes; `pass` + audit trigger -> audit finalize / `xian-archive`; open P0/P1 issues -> `xian-build`; missing or weak verification -> `xian-verify`; human-risk decision -> pause for human owner.
- Upstream-blocker mapping: missing spec result -> `xian-spec`; missing build result -> `xian-build`; stale verify result -> `xian-verify`; release/archive manifest mismatch after fresh upstream facts -> `xian-archive`.
- If the mapping conflicts with runtime `nextAction`, state the conflict and run `$xian-next` or `xian-harness continue --json` for arbitration.
- 不要let Gate invent a separate route after `nextAction` is available.

## 约束与原因

- Builder Agent cannot self-approve。 原因：违反该约束会破坏 xian-gate 的协议边界、证据链或 profile 隔离。
- P0/P1 open issues block archive。 原因：违反该约束会破坏 xian-gate 的协议边界、证据链或 profile 隔离。
- Human approval is required for risk acceptance。 原因：违反该约束会破坏 xian-gate 的协议边界、证据链或 profile 隔离。
- Non-`pass` gate execution must block archive and return to Builder/Verifier repair loop。 原因：违反该约束会破坏 xian-gate 的协议边界、证据链或 profile 隔离。
- 不要在 gate 或 closeout 中生成、修复或补写 `spec-result.json` / `build-result.json`。原因：这些是上游阶段事实，closeout 只能消费和阻断。
- 不要把 non-upgraded small hotfix 强行送入 full gate / release / archive。原因：small hotfix 已由 `quick-verify`、blocking issue 检查和 `quick-close` 形成轻量可信闭环。
