---
name: xian-project-sync
description: Use when writing verified project-level facts back to overview/status documents and registry-backed backlog facts.
---

# xian-project-sync

## 用途

把已验证的 project 级事实写回项目级文档和 backlog registry，让人类和后续 Agent 能从 `docs/项目情况.md`、`docs/项目状态.md`、`.xian-harness/backlog/registry.json` 和渲染后的 `docs/待办清单.md` 恢复项目认识。

`xian-project-sync` 只同步项目级文档，不创建业务 change，不替代 `xian-project-startup` 建立初始基线。

`docs/待办清单.md` 是 Document Render Pipeline 生成面，不是待办事实源；后续项必须通过 backlog registry mutation 写入 `.xian-harness/backlog/registry.json`。

## 触发条件

当用户要求“同步项目文档”“刷新项目总览”“更新项目状态文档”“把今晚的能力升级写进项目状态”时使用。

不要因为普通“继续”、下一步判断或单个 change 的 verify/gate/archive 自动触发本 skill。

## 协议输入

- `docs/项目情况.md`
- `docs/项目状态.md`
- `docs/待办清单.md`
- `.xian-harness/backlog/registry.json`
- `docs/README.md`
- `.xian-harness/state.yaml`
- `.xian-harness/changes/{change-id}`
- `.xian-harness/changes/*/batch-change-plan.md`
- validated project evidence named by the user or by `xian-project-status`

## 执行流程

1. 确认本轮要同步的项目级事实和证据来源。
2. 运行或引用 `xian-harness project status --target <target-project> --json` 和 `xian-harness project docs-sync --target <target-project> --json`。
3. 区分已完成事实、风险、后续项和推断；不把未验证聊天结论写成项目状态。
4. 最小修改 `docs/项目情况.md`、`docs/项目状态.md` 或 `docs/README.md`。
5. 如有后续项，使用 `xian-harness todo add ...` 或 `xian-harness todo import ...` 写入 backlog registry；不要直接编辑 `docs/待办清单.md`。
6. 需要刷新人读待办面时，运行 `xian-harness docs render --doc todo-list --fix`，让 render pipeline 从 registry 生成 `docs/待办清单.md`。
7. 做 `git diff --check` 和关键词回扫，确认文档同步可检索。

## 常见分支

- 阶段性能力升级：更新项目状态和项目情况，记录完成事实、证据路径和边界。
- 只有后续观察项：只写入 `.xian-harness/backlog/registry.json`，再渲染 `docs/待办清单.md`。
- 事实不足：先交给 `xian-project-status` 补只读状态，不直接写文档。
- 项目基线缺失或严重失真：交给 `xian-project-startup`。

## 确定性工具

- `xian-harness project status --target <target-project> --json`
- `xian-harness project docs-sync --target <target-project> --json`
- `xian-harness todo add <id> --target <target-project> --priority <P1|P2|P3> --summary "<summary>" --json`
- `xian-harness todo import --target <target-project> --file <candidates.json> --json`
- `xian-harness todo list --target <target-project> --json`
- `xian-harness docs render --target <target-project> --doc todo-list --fix --json`
- `git diff --check -- docs`
- `rg -n "<keyword>" docs/项目情况.md docs/项目状态.md docs/待办清单.md docs/README.md .xian-harness/backlog/registry.json`

## 必需证据

- Facts being synchronized and their source paths.
- Files updated.
- Backlog registry mutation result when follow-up items are recorded.
- Todo-list render result when `docs/待办清单.md` is refreshed.
- Diff-check result.
- Keyword回扫 result for the synchronized capability or status.

## 事实映射

- Project overview -> `docs/项目情况.md`
- Project state -> `docs/项目状态.md`
- Follow-up items -> `.xian-harness/backlog/registry.json`
- Rendered todo view -> `docs/待办清单.md`
- Navigation -> `docs/README.md`
- Machine status -> `xian-harness project status --json`

## 参考样例

- 2026-06-19 项目级能力同步：把 Batch Change Contract、`xian-project-research` 和真实 research case 验证写回项目状态、项目情况和待办清单。

## 自检清单

- 是否只写入 project 级文档？
- 是否没有创建新的 feature change？
- 是否把后续项通过 `xian-harness todo add/import` 放进 `.xian-harness/backlog/registry.json`？
- 是否没有直接编辑 generated `docs/待办清单.md` 来改变待办状态？
- 是否没有把未验证推断写成完成事实？
- 是否保留了证据路径或可检索关键词？

## 输出

- Updated project-level documents.
- Synchronized facts summary.
- Backlog registry mutation summary when applicable.
- Rendered todo summary when applicable.
- Verification commands and result.

## 交互预算

- 必须：读取文件或运行命令前遵守当前 hook 提供的 Interaction Budget。
- 必须：只读取与本次同步相关的项目文档和证据，不打开 heavy workbench、quality-gate 或 archive evidence。
- 必须：文档同步不自动进入 build / verify / gate / archive。

## 交接规则

- 输出时先说明当前结论、证据缺口和风险；末尾输出 `下一步建议：<中文下一步>`，空一行后单独输出 `$xian-xxx`，再空一行输出 `直接回复“继续”即可进入该步骤。`；不要在首屏附加“因为...”。

- 需要先读取项目状态 -> `xian-project-status`。
- 发现初始基线缺失或严重失真 -> `xian-project-startup`。
- 文档同步后需要提交 -> `xian-commit`。
- 同步暴露新需求 -> `xian-open`。

## 约束与原因

- 不要把 `xian-project-sync` 当作项目启动入口。原因：sync 写回已有事实，startup 建立初始治理环境。
- 不要在证据不足时写完成状态。原因：项目总览会被后续 Agent 当作恢复上下文。
- 不要把单个 change 的验收结论改写为项目级事实，除非它已经完成并有证据路径。原因：项目状态需要稳定事实，不是中间过程快照。
- 不要创建新的 feature change。原因：项目文档同步是 project-level maintenance，只有用户明确要求时才进入需求生命周期。
- 不要直接编辑 `docs/待办清单.md` 来新增、promote 或关闭待办。原因：它是 render pipeline 输出，事实源是 `.xian-harness/backlog/registry.json`。
