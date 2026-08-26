---
name: xian-verify
description: Use when running tests, builds, or smoke checks before gate pass.
---

# xian-verify

## 用途

运行验证命令并持久化证据。

## 触发条件

Use this skill after implementation, before quality gate, or whenever a completion claim requires fresh command evidence.

## 协议输入

- governed/lite 默认：`.xian-harness/changes/{change-id}/change.md`
- `.xian-harness/changes/{change-id}/acceptance-criteria.md`
- `.xian-harness/changes/{change-id}/tasks.md`
- adapter verify policy when present
- changed files and selected command list
- existing `.xian-harness/changes/{change-id}/verify/`

## 执行流程

1. Confirm source, accepted contract, build phase facts, the latest read-only verify plan, and any required `build.review` are stable; a required review must be fresh accepted before formal Verify starts.
2. Build a verification plan from adapter policy and change acceptance. Before command execution, inspect `changedPaths`, `selectedTestFiles`, `sourceFanout`, `fallback`, and `selectionFingerprint`.
3. If the plan has a generic protocol fallback, a missing impact target, or selected tests that cannot be explained by changed paths and source fanout, return to `xian-build` to repair attribution, mapping, or the verification plan. Formal Verify is not a test-plan debugging entry.
4. Run commands exactly as recorded only after the plan is stable and explainable.
5. Capture logs under `.xian-harness/changes/{change-id}/verify/evidence/logs/`.
6. Write compact verify facts through `xian-harness verify`; only write Markdown reports when audit or explicit report persistence requires it.
7. Mark pass with sealed evidence and advance. Any post-spawn non-pass seals the immutable ActionAttempt result/terminal and stops that attempt. Consume the current machine `failureRecovery.decision`: `prepare-new-candidate` stabilizes a deterministic Candidate failure under the same Business Change; `retry-same-candidate` is only available for a machine-proven environment interruption; `suspend-for-incident-repair` may authorize the `incident-repair` relation for repository-baseline only after complete current classifier/admission proof; only `terminalize-business-change` from the `business-boundary classifier` may terminalize or replace the Business Change. Never mechanically rerun or hand-author a successor.

## 变更类型与验证范围

`xian-verify` 负责 fresh command evidence，不负责生成需求事实或实现事实。

- Behavior change：运行覆盖实际行为的项目测试、build、smoke 或静态检查。
- Acceptance-contract change：验证 `change.md` / `acceptance-criteria.md` 的命令锚点，并运行会消费这些契约的 gate / archive / product-surface 回归。
- Metadata-only change：优先运行 `git diff --check`、`xian-harness docs status --target <target-project> --json` 或明确相关的轻量命令；只有源码、runtime、release、archive、gate 或 product surface 变化时才升级到完整验证。

`verify` 不补写 `spec/spec-result.json` 或 `build/build-result.json`。如果 gate 或 closeout 指出缺少上游 phase result，下一步应回到 `xian-spec` 或 `xian-build`，而不是反复完整 verify。

Change Runtime contract revision 进入 verify 时，`xian-verify` 只消费 frozen / accepted revision 与 candidate patch validation result；不要在 verify 阶段接受、冻结或 supersede revision。若 candidate patch 会改变已 seal section，在任何写入前以 `CHANGE_ATTEMPT_IMMUTABLE` 拒绝，并消费 current machine `failureRecovery.decision`；Skill 不自行选择 repair relation 或创建 successor。

## 常见分支

- 常规路径：按 `nextAction` 和当前 change state 选择下一步。
- 命令证据不足：先补 verify evidence 或明确记录 blocked reason。
- 上游阶段事实不足：不要伪造 verify pass，交还给 `xian-spec` 或 `xian-build`。
- required build review 缺失、未接受或 stale：回到 `xian-build` 完成 review 或修复，不先跑 formal Verify 再刷新 evidence。
- `verify plan` 的 changed paths、fanout、fallback 或 impact mapping 无法解释：回到 `xian-build` 修正选择计划，不把 formal Verify 当作昂贵的选择器探测。
- 发现职责不匹配：交接到 `xian-open` 重新路由。

每个 change attempt 最多启动一次 Formal Verify 或 Quick Verify；这里的 attempt 绑定唯一 ActionAttempt identity。runner 启动后的任何 non-pass 只 terminalize 该 immutable ActionAttempt；不得机械重跑、调 timeout、覆盖 evidence 或手写 successor。后续动作必须消费 current machine `failureRecovery.decision`：`prepare-new-candidate` 在 same Business Change 内形成 meaningful Candidate delta；`retry-same-candidate` 仅用于获机器授权的 environment interruption；`suspend-for-incident-repair` 仅在完整 current classifier/admission proof 下授权 repository-baseline 的 `incident-repair` relation；只有 `business-boundary classifier` 给出 `terminalize-business-change` 时才可终结或替换 Business Change。

## 确定性工具

- small hotfix targeted verification: `xian-harness quick-verify <change-id> --target <target-project> --command "<command>" --json`
- `xian-harness verify <change-id> --target <target-project> --command "<command>" --json`
- `xian-harness verify plan <change-id> --target <target-project> --json`
- project-native checks selected by the Verify plan
- project-native tests/builds/smoke scripts listed in the plan
- self-hosted targeted Vitest：`npm --prefix xian-agent-harness test -- --run test/<target>.test.ts`。该形式由 npm 在包根加载 `vitest.config.ts`；不要用缺少 `--root xian-agent-harness` 或 `--config vitest.config.ts` 的 `npm --prefix xian-agent-harness exec -- vitest` 替代。

## 分级指引

- Small: use `quick-verify` with explicit targeted commands. It writes `quick-verify/quick-verify-result.json`, `quick-verify/quick-verify.md`, and command logs.
- small hotfix 的轻量只减少不必要的文档和 release/archive 产物，不降低验证要求；`quick-verify` 必须运行 fresh command，并覆盖实际改动。
- 如果 targeted verification 暴露 schema、state-machine、gate、archive、release、pack、profile、skill contract、security、migration、cross-module runtime、quality mechanism 或不可局部验证风险，停止 quick close，回到 `xian-spec` / `xian-design` 升级。
- Standard: use `verify` with normal command logs and reports, but keep evidence slim; Standard verification does not provide a sha256 hash-chain manifest unless the change is upgraded or explicitly audited.
- Major: use full `verify`, including command logs, verification report, and evidence manifest; do not replace required verification with quick verify.
- If quick verification exposes broader risk or changed scope, stop the small hotfix path and upgrade before close.
- Metadata-only follow-up after docs/status/projection refresh should not automatically rerun heavy behavior suites; choose the lightest fresh command that proves the touched facts are current.

### 真实项目 Lane 验证

- lightweight lane：必须运行覆盖实际改动的 fresh verification（新鲜验证命令），优先使用真实 command-anchor（命令锚点），例如项目脚本、单测、smoke 或静态检查；不能用“我认为 OK”或聊天结论替代。
- production lane：验证证据必须覆盖外部服务连通性、生产配置边界、备份/回滚、数据核对和启动 smoke；如果任一项无法验证，记录 blocked 或 residual risk，不降级成 lightweight lane。
- delivery lane：验证命令必须能支撑 full gate、release acceptance 和 archive；客户验收、安全边界和上线门禁不能只保留自然语言说明。
- 自然语言可以解释验收意图，但 verification rule 的执行载体优先写可执行命令、脚本或明确证据路径。

## 必需证据

- `.xian-harness/changes/{change-id}/verify/verify-result.json`
- one log file per command under `.xian-harness/changes/{change-id}/verify/evidence/logs/`
- `.xian-harness/changes/{change-id}/verify.md`
- `.xian-harness/changes/{change-id}/verify/evidence/evidence-manifest.json` for Major or explicit audits
- explicit residual risks for skipped or partial checks

## 参考样例

- `harden-xian-next-user-facing-guidance`: targeted tests、typecheck、diff-check 的验证参考。

## 自检清单

- 是否运行 fresh command？
- 是否在执行命令前确认只读 `verify plan` 的 fanout、fallback 和 selection fingerprint 可解释且稳定？
- 是否保存每条命令的日志或结果？
- 是否如实记录 failed/partial/blocked？
- 是否区分 behavior、acceptance-contract 和 metadata-only 变化？
- 是否没有用 LLM review 替代测试？

## 输出

- Verification report.
- Evidence files.
- Residual risks.

## 交互预算

- 必须：obey the current hook-provided Interaction Budget before reading files or running commands.
- 必须：keep chat-mode requests tool-free unless the user explicitly asks for inspection, snapshot refresh, deep audit, or change execution.
- 必须：require explicit deep-audit or change intent before reading pack state, workbench, quality-gate, archive, or other large project status artifacts.

## 交接规则

- 当前请求携带 publish intent 且不存在真实阻塞时，完成 verify 后由同一主 Agent 在同一任务中直接进入下一个 lifecycle skill，不输出等待用户回复“继续”的 handoff。
- 当前请求不携带 publish intent 时，从运行时 `nextAction` 开始；末尾输出 `下一步建议：<中文下一步>`，空一行后单独输出 `$xian-xxx`，再空一行输出 `直接回复“继续”即可进入该步骤。`；不要在首屏附加“因为...”。
- 对 non-upgraded small hotfix，如果 `quick-verify` 已 pass 且无升级信号，末尾建议写成：`下一步建议：quick-verify 已通过，使用 quick-close 完成 small hotfix 收口`，下一行 skill 仍使用 `$xian-verify`。
- 表达层原则：中文优先，默认用自然中文给结论、必要风险和下一步；必须保留英文术语、协议字段、状态名或命令名时，紧跟中文括注解释；不写“流程报告 / Review 报告 / evidence 清单”式长篇；只有 deep-audit、gate、verify 或用户明确要求完整显性化时才展开治理细节。
- Default mapping: verification pass -> `xian-gate`; pre-spawn environment preflight failure -> keep attempt unstarted; every post-spawn non-pass -> immutable ActionAttempt terminal, then consume the current machine `failureRecovery.decision` without mechanically rerunning or hand-authoring a successor.
- If the mapping conflicts with runtime `nextAction`, state the conflict and run `$xian-next` or `xian-harness continue --json` for arbitration.
- 不要let a static pass/fail rule override `nextAction`.

## 约束与原因

- 不要在缺少新鲜命令输出时声称 pass。 原因：违反该约束会破坏 xian-verify 的协议边界、证据链或 profile 隔离。
- 不要隐藏失败命令。 原因：违反该约束会破坏 xian-verify 的协议边界、证据链或 profile 隔离。
- 不要把 LLM review 当作测试替代品。 原因：违反该约束会破坏 xian-verify 的协议边界、证据链或 profile 隔离。
- 不要用 verify 生成或修复 spec/build phase result。原因：verify 只证明命令证据，上游事实必须由对应阶段产生。
- 不要把 weak quick verification 当作 small hotfix pass。原因：targeted verification 必须覆盖实际改动，否则 quick-close 会制造虚假的轻量可信闭环。
