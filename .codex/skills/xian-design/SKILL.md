---
name: xian-design
description: Use when designing architecture, data flow, test strategy, integration points, or risk controls within the spec phase. Auxiliary skill; not a persisted ChangePhase owner.
---

# xian-design

## 用途

定义 change 应该如何实现，同时不丢失 spec 中已确认的 WHAT。`xian-design` 是 spec phase 内的辅助 skill，不是独立 persisted phase owner。

## 触发条件

Use this skill after requirements are clear and before implementation for cross-module, risky, adapter-driven, or user-facing changes. In the 5-phase lifecycle this work happens inside `spec`.

## 方法论来源

- Provider: Xian internal engineering discipline
- Role: engineering-discipline-provider
- Absorption Mode: discipline absorbed into `xian-design`; do not create parallel 工程纪律 design facts.

## 吸收的纪律

- `brainstorming`: compare approaches and surface trade-offs.
- `writing-plans`: make design constraints specific enough for execution planning.

## Change Design Quality Lenses

`xian-design` 消费 Spec 已识别的确认边界和产品不变量，不重复生成固定四问模板。

- 把适用的产品不变量转换为 1 至 3 条可观察的技术不变量，不用字段、hash 或 artifact 名称代替语义。
- 为存在绕过面的技术不变量描述 failure model（失败模型）和最低成本反例；只有会改变设计、测试或风险结论时才写入现有内容。
- 为最高风险结论选择不同 evidence source 的验证策略，避免测试、Gate 和 archive 只重复读取同一判断结果。
- 如果这些判断不改变设计约束、验证策略或 Review 重点，不产生额外治理内容。

本纪律不新增 phase、不新增 schema，也不新增独立 Design artifact 或 Runtime 状态。独立证据只降低证据共模；同一个设计者的推理共模仍需现有独立 Review 策略处理。

## 执行前必须确认

- 必须：restate the accepted WHAT from proposal and acceptance before choosing implementation details.
- 必须：compare options or record why only one viable option exists.
- 必须：map design decisions to acceptance criteria, verification strategy, and rollback or risk controls.

## 协议输入

- governed/lite 默认：`.xian-harness/changes/{change-id}/change.md`
- `.xian-harness/changes/{change-id}/proposal.md`
- `.xian-harness/changes/{change-id}/acceptance-criteria.md`
- `.xian-harness/changes/{change-id}/design.md`
- `harness-pack/base/.xian-harness/protocol/templates/docs/decision-record.md`
- `.xian-harness/harness-protocol.yaml`
- project quality policy declared by the accepted contract
- relevant reference projects and existing architecture

## 执行流程

1. Restate the requirement briefly.
2. Translate applicable product invariants into technical invariants, failure models, and cheapest counterexamples.
3. Identify affected components, ownership boundaries, data flow, and integration points.
4. Define error handling, rollback, observability, and migration concerns.
5. Define verification and quality gate strategy, including an independent evidence source only for high-risk conclusions.
6. For 技术选型, multi-option design, dependency introduction, framework choice, or high-risk tradeoff, create a Decision Record from `.xian-harness/protocol/templates/docs/decision-record.md`.
7. Record alternatives, rejected options, impacts, and risks.

## Batch Planning Contract

当一个需求可能需要拆成多个 change 时，`xian-design` 负责先判断是否需要 batch plan。不要让 AI agent 只凭“看起来很大”随意拆分。

Trigger Signals:

- 跨多个治理 skill 或职责边界，例如 skill surface、experience、pack、gate、真实案例验证同时受影响。
- 涉及 schema、protocol、pack、profile 隔离或质量机制等多层事实源。
- 预计实现需要多个可独立验收、提交和回退的阶段。
- 需要先设计产品边界，再做实现，再用真实 case 验证体验。

Anti-patterns:

- 不要为单文件 hotfix、单 skill 内纯实现或紧耦合 schema+test 强行拆 batch。
- 不要把一个必须原子提交的协议改动拆成多个互相等待的 change。
- 不要把纯文档措辞调整、无依赖的小修补或一次性清理包装成 batch。
- 如果拆分后每个子 change 不能独立验收，说明它不是合格 batch。

Minimal Schema:

```yaml
batchId: project-research-productization
goal: 用一句话说明大需求目标。
triggerSignals:
  - 跨多个治理 skill 或职责边界
antiPatternsChecked:
  - 不拆：单文件 hotfix
changes:
  - id: formalize-example
    type: design / batch-plan
    goal: 明确产品定位和拆分边界。
    dependsOn: []
    acceptance:
      - 用户 review 通过。
    rollbackBoundary: 删除本 change 产物不影响后续实现。
```

最小校验规则：每个 change 必须有 `id`、`type`、`goal`、`acceptance`、`rollbackBoundary`；`dependsOn` 只能引用已声明 change；依赖图不能有环；至少记录一个 `triggerSignals` 和一个 `antiPatternsChecked`。

## 确定性工具

- `xian-harness change inspect <change-id> --target <target-project> --json`
- project-native architecture inspection commands
- source search with `rg` to ground architecture in existing modules

## 必需证据

- Design document or design section under `.xian-harness/changes/{change-id}/design.md`.
- Decision Record when choosing between two or more technical options, introducing a dependency, or making a high-risk architectural tradeoff.
- Explicit affected-file or affected-module list.
- Verification strategy that maps acceptance to commands, smoke scripts, or gate issues.

## 事实映射

- Design decisions -> `.xian-harness/changes/{change-id}/change.md`
- Decision records -> `docs/决策记录/` or project-specific decision record path when configured
- Verification strategy -> `.xian-harness/changes/{change-id}/change.md`

## Contract Revision Boundary

当设计内容进入 Change Runtime contract revision 时，`xian-design` 只产出 candidate patch 和 deterministic validation 所需的设计事实。设计 Agent 不得自行把 candidate patch 标记为 accepted / frozen；如果设计语义修改已冻结 section，必须声明 semanticImpact 和需要重开的 lifecycle phase。

## 参考样例

- `standardize-chinese-skill-contract-v2`: 中文契约 v2 设计和取舍参考。

## 自检清单

- 是否遵守当前 Interaction Budget？
- 是否从 canonical facts 而不是聊天记忆开始？
- 是否留下了可复查的 evidence 或明确说明无需证据？
- 是否没有越过当前 skill 的职责边界？

## 输出

- `design.md` or equivalent design document.
- Decision Record for 技术选型 / 方案对比, including 决策背景, 项目约束, 方案对比, 决策结论, 决策理由, 影响范围, 风险与后续.
- Verification strategy.
- Implementation constraints for `xian-plan`.

## 交互预算

- 必须：obey the current hook-provided Interaction Budget before reading files or running commands.
- 必须：keep chat-mode requests tool-free unless the user explicitly asks for inspection, snapshot refresh, deep audit, or change execution.
- 必须：require explicit deep-audit or change intent before reading pack state, workbench, quality-gate, archive, or other large project status artifacts.

## 交接规则

- 当前请求携带 publish intent 且不存在真实阻塞时，完成 design 后由同一主 Agent 在同一任务中直接进入下一个 lifecycle skill，不输出等待用户回复“继续”的 handoff。
- 当前请求不携带 publish intent 时，输出时先说明当前结论、证据缺口和风险；末尾输出 `下一步建议：<中文下一步>`，空一行后单独输出 `$xian-xxx`，再空一行输出 `直接回复“继续”即可进入该步骤。`；不要在首屏附加“因为...”。

- Approved design -> `xian-plan`.
- Design discovers missing WHAT -> back to `xian-spec`.
- High-risk unresolved tradeoff -> human decision before build.

## 约束与原因

- 不要把需求改写成设计决策。 原因：违反该约束会破坏 xian-design 的协议边界、证据链或 profile 隔离。
- 不要跳过跨模块或高风险工作的设计。 原因：违反该约束会破坏 xian-design 的协议边界、证据链或 profile 隔离。
- 不要在未检查现有项目能力前引入新框架、依赖、服务或 adapter。 原因：违反该约束会破坏 xian-design 的协议边界、证据链或 profile 隔离。
- 不要加入与 acceptance criteria 无关的重构。 原因：违反该约束会破坏 xian-design 的协议边界、证据链或 profile 隔离。
