<!-- xian-harness:generated-view-seed.v1
view: design.md
authority: legacy-markdown
rendererId: template-registry.change.full
contractRevision: none
editPolicy: contract-ready; after contract authority is enabled, submit a contract patch instead of hand-editing this generated view.
-->

# Design: {change-id}

Template Contract: xian-harness/change/full/design

## Template Quality Contract

| 项 | 内容 |
|---|---|
| Fact Sources | proposal、acceptance criteria、project baseline、source search、decision record。 |
| Owner Role | Designer Agent。 |
| Verification Commands | `xian-harness check {change-id} --target <target-project> --json`。 |
| Evidence Paths | `.xian-harness/changes/{change-id}/design.md`。 |

## Approach

请用中文说明技术方案，保留类名、函数名、命令和路径等英文工程锚点。

## Options Considered

| 方案 | 说明 | 优点 | 风险 | 决策 |
|---|---|---|---|---|
| Option A | {option-a} | {pros} | {risks} | {accept-reject} |
| Option B | {option-b} | {pros} | {risks} | {accept-reject} |

## Acceptance Mapping

| 设计决策 | 覆盖验收项 | 验证方式 |
|---|---|---|
| {decision} | AC-001 | {verification} |

## Risk And Rollback

- 风险：{risk}
- 回退策略：{rollback}
- 需要回到 `xian-spec` / `xian-plan` 的条件：{return-condition}

### Conditional Failure Model（仅在触发时保留）

canonical `sourceDelta.riskDelta` machine facts 中所有适用的 canonical machine-risk categories 都直接触发本节，包括 external side effects（含 `external.*`）、multiple authorities、asynchronous delivery、retry/idempotency、concurrency、auth/tenant boundaries、migration/deployment 与 irreversible operations。Explicit owner-declared risk category 只在 canonical machine facts 缺失时补充风险事实；自然语言关键词本身不是触发 authority。Low-risk UI、copy、documentation 或 pure-function Change 应完整删除本节及下面的 pilot measurement plan。

| observableInvariant | failureCutPoint | expectedState | recovery | probeEvidence |
|---|---|---|---|---|
| {observable-invariant-1} | {failure-cut-point-1} | {expected-state-1} | {recovery-1} | {probe-or-evidence-1} |

只记录 1 至 3 条 observable technical invariants。Business acceptance 不得固定 implementation order，除非该顺序已被独立确认是 business invariant。未验证的 external transaction、idempotency、uniqueness、delivery 或 rollback assumption，必须选择 probe、移除依赖的设计或 explicit residual-risk decision 后，才能进入 formal `spec.review`；formal `spec.review` 仍是唯一 acceptance authority。

### Post-Delivery Pilot Measurement Plan（仅在触发时保留）

这是待执行的 measurement plan，不是本 Change 已获得 external observation 的证据。

```yaml
observationStatus: pending
metrics:
  addedSpecMinutes: pending
  falsePositive: pending
  avoidedBuildRework: pending
  avoidedReplacement: pending
```

- 观测对象：{pilot-sample}
- 观测方式：{measurement-method}
- 观测责任与时间边界：{owner-and-window}

## Documentation Contract

本 change 的设计必须说明文档事实源如何随实现一起更新。代码、配置、测试、证据、Workbench 和归档产物发生变化时，对应文档不能只停留在聊天上下文中。

| 文档事实源 | 是否需要更新 | 原因 |
|---|---|---|
| `docs/项目状态.md` | {yes-no} | {reason} |
| `docs/需求文档.md` | {yes-no} | {reason} |
| `docs/待办清单.md` | {yes-no} | {reason} |
| `.xian-harness/changes/{change-id}/acceptance-criteria.md` | yes | 验收契约必须覆盖本 change。 |

## Trade-offs

请用中文说明关键取舍、风险和非目标。

## Verification Strategy

- {verification-strategy}
