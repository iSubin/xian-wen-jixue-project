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
