<!-- xian-harness:generated-view-seed.v1
view: proposal.md
authority: legacy-markdown
rendererId: template-registry.change.full
contractRevision: none
editPolicy: contract-ready; after contract authority is enabled, submit a contract patch instead of hand-editing this generated view.
-->

# Proposal: {change-id}

Template Contract: xian-harness/change/full/proposal

## Template Quality Contract

| 项 | 内容 |
|---|---|
| Fact Sources | 用户输入、项目状态、需求文档、待办清单、source facts。 |
| Owner Role | Intake Agent。 |
| Verification Commands | `xian-harness check {change-id} --target <target-project> --json`。 |
| Evidence Paths | `.xian-harness/changes/{change-id}/proposal.md`。 |

## Why

请用中文说明业务背景、用户价值、触发原因，以及为什么现在需要做。

## Options

记录进入本 change 前的方案选项。若不需要多方案，必须在表格中写明“不需要多方案”的原因。

| 方案选项 | 说明 | 取舍 | 是否采用 |
|---|---|---|---|
| Option A | {option-a} | {trade-off} | {yes-no} |
| Option B | {option-b-or-not-needed} | {trade-off-or-reason} | {yes-no} |

## Confirmation Or Assumption

记录用户确认结论，或在没有显式确认时列出可继续推进的假设边界。

- 用户确认：{confirmation}
- 当前假设：{assumption}
- 需要回到 `xian-spec` 的条件：{return-condition}

## Source Facts

| 类型 | 文件或来源 | 用途 |
|---|---|---|
| 用户输入 | `{user-request}` | 说明本 change 的原始诉求。 |
| 项目文档 | `docs/项目状态.md` | 对齐项目当前状态、活动任务和下一步。 |
| 需求文档 | `docs/需求文档.md` | 对齐业务需求、范围和验收口径。 |
| 待办清单 | `docs/待办清单.md` | 对齐轻量任务和已知后续项。 |

## What Changes

请用中文列出本次业务变化；文件名、命令、接口和代码锚点保持英文。

## Project Source Delta

如果本 change 会改变项目级能力、边界或风险，请在下面 JSON 中声明结构化 delta。没有变化时保留三个空数组。`archive run` 只从这里读取 delta，并由 `document-source-maintainer` 写入 canonical project source JSON。

```json
{
  "capabilityDelta": [],
  "boundaryDelta": [],
  "riskDelta": []
}
```

## Non-goals

- {non-goal}

## Impact

- Product:
- Protocol:
- Pack:
- Adapter:
- Docs:
- Tests:
