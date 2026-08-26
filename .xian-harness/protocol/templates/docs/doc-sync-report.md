# 文档同步报告

Template Contract: xian-harness/docs/doc-sync-report

## Template Quality Contract

| 项 | 内容 |
|---|---|
| Fact Sources | Git diff、测试输出、verify、gate、archive、项目文档。 |
| Owner Role | Doc Steward。 |
| Verification Commands | `xian-harness docs inspect --target <target-project> --json`。 |
| Evidence Paths | `.xian-harness/changes/{change-id}/docs/doc-sync-report.md` 或 `docs/文档同步报告.md`。 |

## 同步范围

- 代码：
- Git：
- Change：
- 项目文档：
- Pack / Profile：

## 冲突判定

当文档与代码、Git、测试、verify、gate 或 archive 结果冲突时，优先以可复现事实为准，并把文档更新为新的事实状态。

| 冲突项 | 文档说法 | 事实来源 | 处理结果 |
|---|---|---|---|
| {item} | {doc-fact} | {actual-fact} | {resolution} |

## 已同步文档

| 文档 | 更新原因 | 证据 |
|---|---|---|
| `docs/项目状态.md` | {reason} | {evidence} |
| `docs/需求文档.md` | {reason} | {evidence} |
| `docs/待办清单.md` | {reason} | {evidence} |

## 未同步但已确认

| 文档 | 不更新原因 |
|---|---|
| {path} | {reason} |
