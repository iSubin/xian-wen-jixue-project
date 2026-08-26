---
name: xian-project-startup
description: Use when taking over a project for the first time, initializing the project skeleton, establishing an initial baseline, or rebuilding a drifted baseline.
---

# xian-project-startup

## 用途

把一个项目纳入 xian-agent-harness 管理，建立初始项目目录骨架、目录约束、入口文件、项目基线和第一版项目认识。

`xian-project-startup` 只负责 project 级启动、接手和基线重建，不负责日常项目状态同步、承接具体需求或实现代码。

## 触发条件

首次进入一个已有项目、新项目接入 Harness、项目基线缺失、AGENTS.md / CLAUDE.md 缺失，项目基线与真实项目严重失真，或用户要求“接手项目”“初始化项目管理”“建立项目骨架”时使用。

不要仅因完成了一个 change、需要刷新项目状态、需要同步项目总览或需要判断下一步而触发本 skill；这些属于 `$xian-next`、`xian-harness project status` / `xian-harness project docs-sync`，或等待对应 project status/sync skill 落地。

## 协议输入

- `AGENTS.md`
- `CLAUDE.md`
- `.xian-harness/harness-protocol.yaml`
- `.xian-harness/state.yaml`
- `docs/项目基线.md`
- `docs/项目开发纪律.md`
- `docs/目标运行手册.md`
- project marker files such as `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `pom.xml`, `README.md`, or `LICENSE`
- current branch, worktree status, and uncommitted changes

## 执行流程

1. 确认 target project root，不使用未验证的固定路径。
2. 检查 Harness Pack、`.xian-harness`、`AGENTS.md`、`CLAUDE.md` 和项目文档骨架是否存在。
3. 缺少底层协议或模板时，调用确定性工具初始化或重建基线，不手写散落状态。
4. 扫描项目 marker files、目录结构、测试入口、提交规则、风险和现有文档。
5. 创建初始 `docs/项目基线.md`、`docs/项目开发纪律.md` 和必要的目录约束说明；只有在基线缺失或明显失真时才重建。
6. 暴露 project 级流程债务：dirty worktree、pack drift、缺失文档、未闭环 change、需要人类决策的事项。
7. 输出项目接手报告和唯一下一步 skill，通常是 `$xian-open` 或 `$xian-next`。

## 常见分支

- 首次接手：初始化入口文件、项目基线、工程纪律和目录约束后，再交给 `xian-open`。
- 已接手项目续作：不使用本 skill，交给 `xian-next` 恢复下一步。
- 项目骨架缺失：先补 `AGENTS.md`、`CLAUDE.md` 和 docs 骨架，不创建业务 change。
- 项目基线严重失真：先说明失真证据，再重建 baseline；不能把普通状态同步伪装成 startup。
- 发现 active/dangling change：暴露流程债务，交给 `xian-next` 或人类决策。

## 确定性工具

- `xian-harness pack status --target <target-project> --profile auto --json`
- `xian-harness init --target <target-project> --json`
- `xian-harness baseline create --target <target-project> --json`
- `xian-harness baseline inspect --target <target-project> --json`
- `xian-harness project status --target <target-project> --json`
- `git status --short --branch`
- `find <target-project> -maxdepth 2 \( -name package.json -o -name pyproject.toml -o -name go.mod -o -name Cargo.toml -o -name pom.xml \)`

## 必需证据

- Chosen target project root.
- Pack and protocol initialization status.
- `AGENTS.md` and `CLAUDE.md` status.
- Project Baseline path and freshness.
- Project discipline and directory constraints status.
- Dirty worktree and active/dangling change summary.
- Next skill recommendation.

## 事实映射

- Project baseline -> `docs/项目基线.md`
- Project discipline -> `docs/项目开发纪律.md`
- Host batch execution guidance -> root / Pack `xian-batch` skill
- Harness install facts -> `.xian-harness/` and `.xian-harness/pack/`
- Next route -> `xian-harness continue --target <target-project> --json`

## 参考样例

- 暂无；当 `xian-commit` 完成首次外部项目接手闭环后补齐。

## 自检清单

- 是否确认了 target project root？
- 是否区分了 project 接手和 change open？
- 是否确认本次确实是首次接手、骨架缺失或基线严重失真，而不是普通项目状态同步？
- 是否建立或检查了项目基线、工程纪律和目录约束？
- 是否没有在 project startup 阶段实现业务代码？

## 输出

- Project startup / takeover report.
- Project baseline and discipline status.
- Process debt summary.
- Next skill to load.

## 交互预算

- 必须：读取文件或运行命令前遵守当前 hook 提供的 Interaction Budget。
- 必须：不要读取 heavy workbench、quality-gate、archive evidence 或 pack state，除非用户明确要求 deep-audit。
- 必须：project startup 只做 project 级接手，不把业务需求藏进初始化动作。

## 交接规则

- 输出时先说明当前结论、证据缺口和风险；末尾输出 `下一步建议：<中文下一步>`，空一行后单独输出 `$xian-xxx`，再空一行输出 `直接回复“继续”即可进入该步骤。`；不要在首屏附加“因为...”。

- 首次接手完成且有新需求 -> `xian-open`。
- 已有 active change -> `xian-next` 仲裁下一步。
- 项目已接手且只是需要继续推进、刷新方向或同步状态 -> `xian-next`、`xian-harness project status` 或 `xian-harness project docs-sync`，不留在 `xian-project-startup`。
- 缺少 pack 或 baseline -> 保持在 `xian-project-startup` 补齐 project 事实。
- 需要启动本地服务、端口或健康检查 -> 后续 runtime-specific skill，不在 base project startup 内处理。

## 约束与原因

- 不要把 `xian-project-startup` 当作需求入口。原因：project 接手负责建立长期项目事实，需求进入应由 `xian-open` 管理。
- 不要把 `xian-project-startup` 当作日常项目状态同步入口。原因：startup 是一次性接手/重建基线动作，频繁触发会和 `xian-next`、`xian-harness project status`、`xian-harness project docs-sync` 的职责重叠。
- 不要在项目基线缺失时直接进入 `xian-build`。原因：缺少项目骨架和工程纪律会让后续 change 无法审计。
- 不要捏造启动命令、健康端点或测试入口。原因：项目第一版认识必须来自已验证文件和命令。
- 不要把 dirty worktree 或 dangling change 隐藏在接手报告之外。原因：项目级债务会污染第一个业务 change。
