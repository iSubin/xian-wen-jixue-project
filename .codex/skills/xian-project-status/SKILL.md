---
name: xian-project-status
description: Use when read-only viewing overall project status, tech debt, health, or next-step rationale. Does not modify state.
---

# xian-project-status

## 用途

只读汇总项目当前状态，把 project 级事实、流程债务和健康风险呈现给用户或后续 skill。

`xian-project-status` 不初始化项目、不修改项目文档、不承接具体需求，也不替代 change 级 `xian-gate`。

## 触发条件

当用户要求“看项目状态”“当前项目怎么样”“项目健康度”“有哪些流程债务”“为什么下一步这样走”时使用。

不要因首次接手、项目骨架缺失或基线严重失真触发本 skill；这些属于 `xian-project-startup`。

不要因普通“继续”、“下一步”或 “go” 触发本 skill；这些属于 `xian-next` 或 `xian-open` 仲裁。

## 协议输入

- `AGENTS.md`
- `CLAUDE.md`
- `.xian-harness/harness-protocol.yaml`
- `.xian-harness/state.yaml`
- `docs/项目情况.md`
- `docs/项目状态.md`
- `docs/待办清单.md`
- `.xian-harness/changes/{change-id}`
- current branch and dirty worktree status

## 执行流程

1. 确认 target project root，不使用未验证的固定路径。
2. 运行或引用 `xian-harness project status --target <target-project> --json`。
3. 检查 active change、dangling / failed / release-pending change、dirty worktree、branch ahead/behind、pack drift 和项目文档缺口。
4. 区分 canonical facts、derived reports 和人工判断，不把 Workbench 或 summary 当事实源。
5. 输出项目状态摘要、流程债务和下一步建议；如需要写回文档，交给 `xian-project-sync`。

## 常见分支

- 项目已初始化且无债务：报告 clean 状态，交给 `xian-next` 或等待用户新需求。
- 有 active / dangling change：报告 change id 和阻塞原因，交给 `xian-next`。
- 工作区 dirty 或 branch ahead：报告 Git delivery debt，交给 `xian-commit`。
- 项目文档缺失或过期：只报告缺口，写回交给 `xian-project-sync`。
- 项目基线缺失或严重失真：交给 `xian-project-startup`。

## 确定性工具

- `xian-harness project status --target <target-project> --json`
- `xian-harness continue --target <target-project> --json`
- `git status --short --branch`
- `git diff --stat`

## 必需证据

- Target project root.
- Project status command or equivalent project fact source.
- Active / dangling change summary.
- Dirty worktree and branch ahead/behind summary.
- Project document health summary.

## 事实映射

- Project facts -> `.xian-harness/state.yaml`
- Project status report -> `xian-harness project status --json`
- Next route -> `xian-harness continue --target <target-project> --json`
- Git delivery facts -> `git status --short --branch`

## 参考样例

- `xian-commit` 接手验证：用项目状态识别 clean + ahead 的 pending-push，而不是创建新 change。

## 自检清单

- 是否保持只读？
- 是否没有修改项目文档？
- 是否区分了 project 状态和 change gate？
- 是否把写回文档交给 `xian-project-sync`？

## 输出

- Project status summary.
- Process debt summary.
- Health risks and stale facts.
- Next skill recommendation.

## 交互预算

- 必须：读取文件或运行命令前遵守当前 hook 提供的 Interaction Budget。
- 必须：优先使用 summary / JSON 输出，不读取 heavy workbench、quality-gate 或 archive evidence。
- 必须：只读状态检查不创建 change。

## 交接规则

- 输出时先说明当前结论、证据缺口和风险；末尾输出 `下一步建议：<中文下一步>`，空一行后单独输出 `$xian-xxx`，再空一行输出 `直接回复“继续”即可进入该步骤。`；不要在首屏附加“因为...”。
- 如果结论是 project idle advisory 或需要用户选择，不要输出 `直接回复“继续”即可进入该步骤。`；改为提示用户明确回复“查看项目状态”或给出一个真实小需求。

- 需要继续当前 change -> `xian-next`。
- 需要写回项目文档 -> `xian-project-sync`。
- 需要首次接手或重建基线 -> `xian-project-startup`。
- 需要 commit / push / dirty worktree 收口 -> `xian-commit`。

## 约束与原因

- 不要在 `xian-project-status` 中写文件。原因：status 是只读观察入口，写回会和 sync 职责重叠。
- 不要把 project status 当成 change gate。原因：change 是否通过质量门禁仍归 `xian-gate`。
- 不要把 branch ahead 忽略为“无流程债务”。原因：本地提交未推送仍是 Git delivery debt。
- 不要把 derived summary 当 canonical facts。原因：状态判断必须来自 state、CLI JSON 或 Git 事实。
