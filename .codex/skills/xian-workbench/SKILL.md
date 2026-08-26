---
name: xian-workbench
description: Use when creating or reading workbench snapshot, queue, or handoff artifacts.
---

# xian-workbench

## 用途

通过协议 facts 把当前 change 状态渲染为 Workbench、看板、CI dashboard 或 Agent SDK 产品视图。

默认 governed-lite 主路径是：

```text
open -> verify -> gate -> close
```

Workbench 是视图层，不是普通 change 的默认 closeout 事实源。release、archive、完整 Workbench 持久化只属于 audit 或用户显式要求。

## 触发条件

Use this skill when a human/board needs a read-only protocol view, a cached preview, or an explicit audit Workbench artifact.

## 协议输入

- `.xian-harness/state.yaml`
- `.xian-harness/changes/{change-id}/.change-state.json`
- `.xian-harness/changes/{change-id}/verify/evidence/`
- `.xian-harness/changes/{change-id}/gate/`
- `.xian-harness/agents/{change-id}/handoffs.json`
- `.xian-harness/releases/{change-id}/release-acceptance.md` when present

## 执行流程

1. Confirm the target project is initialized.
2. Prefer read-only status / cached view unless the user explicitly asks to write.
3. Render local HTML only when the user needs a direct visual preview.
4. Treat generated Workbench files as derived views; canonical facts remain change-local state, verify, gate, close, and audit facts.
5. Use `index.html` as a local static view of the snapshot, not as a source of truth.
6. Route action by `nextAction`.

## 分级指引

- Small `closed` changes are complete through quick close; review `quick-close/quick-close-result.json` and `quick-verify/quick-verify-result.json` when evidence is needed.
- Small `closed` Workbench status defaults to `snapshot-summary.json` and `summary.md`; do not expect a full `snapshot.json` unless a later deep audit explicitly regenerates it.
- Standard legacy changes may still have `snapshot-summary.json` and `summary.md`; treat them as views, not required governed-lite facts.
- Governed changes should normally follow `open -> verify -> gate -> close`; do not create release/archive/workbench docs just because gate passed.
- Major changes and deep audits may persist the full snapshot and complete gate/release/archive evidence.

## 常见分支

- 常规路径：按 `nextAction` 和当前 change state 选择下一步。
- 证据不足：先补 verify evidence 或明确记录 blocked reason。
- 发现职责不匹配：交接到 `xian-open` 重新路由。

## 确定性工具

- `xian-harness workbench status <change-id> --target <target-project> --json`
- `xian-harness workbench render <change-id> --target <target-project> --json`
- `xian-harness workbench snapshot <change-id> --target <target-project> --json` when explicit persistence or audit is required

## 必需证据

- Read-only summary from canonical facts for ordinary governed flow.
- `.xian-harness/workbench/{change-id}/snapshot-summary.json` / `summary.md` / `index.html` only when explicitly persisted.
- Full `snapshot.json` for audit or deep-audit.
- Visible gate, acceptance, adapter, and Harness Pack profile status when relevant.

## 参考样例

- `harden-xian-next-user-facing-guidance`: Workbench summary 作为展示而非事实源的参考。

## 自检清单

- 是否遵守当前 Interaction Budget？
- 是否从 canonical facts 而不是聊天记忆开始？
- 是否留下了可复查的 evidence 或明确说明无需证据？
- 是否没有越过当前 skill 的职责边界？

## 输出

- Workbench snapshot.
- Local HTML preview.
- Human queue and next-action status.

## 交互预算

- 必须：obey the current hook-provided Interaction Budget before reading files or running commands.
- 必须：keep chat-mode requests tool-free unless the user explicitly asks for inspection, snapshot refresh, deep audit, or change execution.
- 必须：require explicit deep-audit or change intent before reading pack state, workbench, quality-gate, archive, or other large project status artifacts.

## 交接规则

- 从运行时 `nextAction` 开始；末尾输出 `下一步建议：<中文下一步>`，空一行后单独输出 `$xian-xxx`，再空一行输出 `直接回复“继续”即可进入该步骤。`；不要在首屏附加“因为...”。
- Default mapping: quality gate pass -> governed close; audit trigger -> release acceptance and `xian-archive`; open issues -> `xian-build`; missing evidence -> `xian-verify`; human queue item -> human owner.
- If the mapping conflicts with runtime `nextAction`, state the conflict and run `$xian-next` or `xian-harness continue --json` for arbitration.
- Workbench displays direction; it must not override `nextAction`.

## 约束与原因

- 不要让 Workbench 覆盖 Gatekeeper 决策。 原因：违反该约束会破坏 xian-workbench 的协议边界、证据链或 profile 隔离。
- 不要在已有 Workbench snapshot artifact 时让 UI 解析散落文件。 原因：违反该约束会破坏 xian-workbench 的协议边界、证据链或 profile 隔离。
- 不要让 `index.html` 在运行时 fetch 本地 JSON；为 `file://` 测试生成自包含 HTML。 原因：违反该约束会破坏 xian-workbench 的协议边界、证据链或 profile 隔离。
- 不要在 quality gate status 不是 `pass` 时从 Workbench status 标记 change complete。 原因：违反该约束会破坏 xian-workbench 的协议边界、证据链或 profile 隔离。
