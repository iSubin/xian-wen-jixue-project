# 已授权多 Change 批次

仅在 owner 明确授权多 Change 批次时读取。普通入口的 Scope、证据、只读和外部授权边界始终适用。

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
