---
name: xian-build
description: Use when implementing approved tasks from change.md or legacy tasks.md, modifying files, or coordinating builder agents. Never approve your own gate.
---

# xian-build

## 用途

在不破坏 Harness 状态、证据链和用户未提交改动的前提下，实现已批准的任务。

`xian-build` 只负责构建和修复，不负责批准自己的质量结论。

## 触发条件

当 `change.md` 中存在已批准的 plan / acceptance / verify 任务，或 legacy/audit change 的 `tasks.md` 中存在已批准任务，或用户明确授权一个范围清晰的 hotfix 时使用。

不要在需求、设计、验收口径仍不清楚时直接进入 `xian-build`。

## 方法论来源

- Provider: Xian internal engineering discipline
- Role: engineering-discipline-provider
- Absorption Mode: TDD 和 verification discipline 被吸收到 `xian-build`；不要再创建并行的 `工程纪律` runtime facts。

## 吸收的纪律

- `test-driven-development`: 在改变行为前建立测试、smoke、静态检查或等价验证证据。
- `verification-before-completion`: 没有验证证据前，不声明实现完成。

## 执行前必须确认

- 必须：确认本次编辑要满足的 AC、任务和验证规则。
- 必须：在行为变更前新增或选择测试、smoke、静态检查或等价验证命令。
- 必须：无法 test-first 时记录 `TDD Exception`，说明原因和替代验证证据。
- 必须：确认当前任务属于 active change；如果任务只是 design 中列出的 future implementation path，停止并要求用户明确选择或先创建对应 change。

## 协议输入

- governed/lite 默认：`.xian-harness/changes/{change-id}/change.md`
- `.xian-harness/changes/{change-id}/tasks.md`
- `.xian-harness/changes/{change-id}/design.md`
- `.xian-harness/changes/{change-id}/acceptance-criteria.md`
- `.xian-harness/changes/{change-id}/.change-state.json`
- `docs/样例索引.md`，或基于 `.xian-harness/protocol/templates/docs/exemplar-catalog.md` 的 change-local Exemplar Catalog
- dirty worktree status
- adapter-specific skills when relevant

## 执行流程

1. 读取下一个未完成任务和它对应的验证步骤。
2. 编辑前读取本地相似实现。
3. 如存在 Exemplar Catalog，读取测试样例、命名约定和风格说明。
4. 没有本地样例时，先记录搜索结果和 fallback rule。
5. 如果下一个任务要求启动 future batch change，确认它已经由 Harness lifecycle CLI 创建；否则只记录为 candidate-only，不进入实现。
6. 编辑前检查相关文件，避免凭路径猜测。
7. 行为变更前先写或选择测试；不能 test-first 时记录 `TDD Exception` 和替代验证。
8. 做最小范围修改。
9. Build 期间只运行直接覆盖当前编辑的 targeted development tests（定向开发测试）；这些测试用于 TDD 反馈，不生成 formal Verify evidence（正式验证证据）。
10. Build 交接前，前置执行 verification plan 中已声明且可低成本运行的 `typecheck`、lint 或静态检查；失败时留在 Build 修复，不用 formal Verify 发现便宜错误。
11. 在源码和 accepted contract 稳定后，运行一次只读 `xian-harness verify plan <change-id> --target <target-project> --json`，检查 `changedPaths`、`selectedTestFiles`、`sourceFanout`、`fallback` 和 `selectionFingerprint`。
12. 若 plan 出现 generic protocol fallback、缺失 impact target，或 selected tests 无法由 changed paths 和 source fanout 解释，不启动 formal Verify；先修正源码归因、impact mapping 或 verification plan。未知路径仍保持 fail closed，不以删测试或跳过覆盖来降本。
13. source、accepted contract、required review snapshot 或 `selectionFingerprint` 变化后，重新执行上述轻量检查和只读 plan；Formal Verify 不是 test-plan 调试入口。
14. 源码、accepted contract、build phase facts 和 verify plan 稳定后，完成 effective policy 要求的 `build.review`；review fresh accepted 后才交给 `xian-verify`。
    `build.review` 与先前 `spec.review` 使用同一 Change-scoped logical Reviewer；新 Candidate 只追加 delta Review attempt，不覆盖旧 Candidate 或旧 issue，也不因 physical session cache 丢失改变 authority identity。
15. 只有任务真实完成时才更新任务状态。
16. 为 `xian-verify` 准备需要运行的命令和验证说明。

## 常见分支

- Small：仅当 change 仍是非升级 `tier=small` 时使用；保持最小改动，并准备 `xian-harness quick-verify` 的定向命令。
- Standard：走正常 build -> verify -> gate 链路。
- Major：保留完整审计证据，不跳过 gate、release 或 archive。
- 本地检查失败：停留在 `xian-build` 修复，不交给 `xian-verify`。
- required `build.review` 未 fresh accepted：继续留在 `xian-build` 完成 review 或修复发现的问题，不提前生成 formal Verify evidence。
- `verify plan` 显示 generic protocol fallback、无法解释的高 fanout 或缺失 impact target：继续留在 `xian-build` 修正 attribution / mapping；不要启动 formal Verify 后再根据耗时反推选择计划。
- 需求歧义暴露：回到 `xian-spec` 或 `xian-design`，不要把猜测写进实现。

## 分级指引

- Small: only use when the change remains non-upgraded `tier=small`; keep edits minimal and prepare a targeted quick verify command for `xian-harness quick-verify`.
- Standard: use the normal build -> verify -> gate loop.
- Major: preserve full audit evidence and do not shortcut gate, release, or archive.
- 如果实现触及 schema、state-machine、gate、archive、pack、skill contracts、quality mechanisms、security、migrations 或广泛 runtime behavior，记录风险并在收口前按升级处理。

## 确定性工具

- `git status --short --branch`
- `xian-harness change inspect <change-id> --target <target-project> --json`
- 用于寻找本地样例的 `rg`、`rg --files` 和项目原生测试发现命令
- project-native checks selected by the accepted change contract
- `change.md` 中选择的本地 test/build commands；legacy/audit change 可读取 `tasks.md`

## 必需证据

- 与任务绑定的代码或文档 diff。
- Exemplar Catalog entry，或明确的 no-local-exemplar note。
- 行为变更的 red/green test evidence，或带替代验证的 `TDD Exception`。
- 已更新的任务状态，或任务仍未完成的明确原因。
- `xian-verify` 必须运行的命令说明。

## 事实映射

- Build tasks -> `.xian-harness/changes/{change-id}/change.md`
- Test or equivalent evidence -> `.xian-harness/changes/{change-id}/verify/verify-result.json`
- TDD Exception -> `.xian-harness/changes/{change-id}/change.md` or `verify/verify-result.json`

## Contract Revision Boundary

当实现发现需求、设计、验收或 verification plan 需要语义调整时，Builder 只能提交 candidate contract patch，并标明 `semanticImpact`、`baseRevision`、`reason` 和受影响 section。不要在 build 中原地修改已冻结 revision；需要重开 spec / plan / build / verify 时，交还 lifecycle 决策。

## 参考样例

- `harden-xian-next-user-facing-guidance`: 用户引导类变更的 build / verify / gate 闭环参考。
- `fix-small-workbench-snapshot-path`: small hotfix 与 Workbench 状态债务的反例参考。

## 自检清单

- 是否已经把当前任务映射到 AC 和验证规则？
- 是否在编辑前读取了本地相似实现，或记录了没有本地样例？
- 是否没有覆盖用户无关改动？
- 是否为 `xian-verify` 留下了明确命令和预期证据？
- 是否已在 Build 内运行便宜的静态检查，并审核只读 `verify plan` 的 fanout、fallback 与 selection fingerprint？
- 是否没有让 Builder Agent 自己批准 gate？

## 输出

- 代码或文档改动。
- 已更新的任务状态。
- 给 `xian-verify` 的验证说明。

## 交互预算

- 必须：读取文件或运行命令前遵守当前 hook 提供的 Interaction Budget。
- 必须：chat-mode 请求保持 tool-free，除非用户明确要求 inspection、snapshot refresh、deep audit 或 change execution。
- 必须：读取 pack state、workbench、quality-gate、archive 或其他大型项目状态前，确认用户有明确 deep-audit 或 change intent。

## 交接规则

- 当前请求携带 publish intent 且不存在真实阻塞时，完成 build 后由同一主 Agent 在同一任务中直接进入下一个 lifecycle skill，不输出等待用户回复“继续”的 handoff。
- 当前请求不携带 publish intent 时，从运行时 `nextAction` 开始；末尾输出 `下一步建议：<中文下一步>`，空一行后单独输出 `$xian-xxx`，再空一行输出 `直接回复“继续”即可进入该步骤。`；不要在首屏附加“因为...”。
- 表达层原则：中文优先，默认用自然中文给结论、必要风险和下一步；必须保留英文术语、协议字段、状态名或命令名时，紧跟中文括注解释；不写“流程报告 / Review 报告 / evidence 清单”式长篇；只有 deep-audit、gate、verify 或用户明确要求完整显性化时才展开治理细节。
- 默认映射：实现完成 -> `xian-verify`；本地检查失败 -> 留在 `xian-build` 修复；需求歧义 -> `xian-spec` 或 `xian-design`。
- 如果静态映射与运行时 `nextAction` 冲突，说明冲突，并 run `$xian-next` or `xian-harness continue --json` for arbitration。
- 不要在没有把下一步 skill 绑定到 `nextAction` 时宣布实现完成。

## 约束与原因

- 不要在 spec 和 plan 不存在时实现，除非用户明确批准 hotfix。原因：缺少 WHAT 和验收口径会让实现变成不可审计的猜测。
- 不要实现未创建的 future implementation path。原因：future path 是 candidate-only roadmap evidence，不是当前 active change；直接实现会制造 scope 混淆和隐形 child workflow。
- 不要复制外部参考代码。原因：外部代码可能带来版权、上下文不匹配和 profile 污染风险。
- 不要在 base profile work 中使用项目特有 exemplars。原因：垂直经验直接进入 base 会污染通用治理层。
- 不要覆盖无关用户改动。原因：工作区可能包含用户或其他 agent 的并行成果。
- Builder Agent 不能批准自己的 quality gate。原因：执行和批准同属一个角色会破坏独立验证。
