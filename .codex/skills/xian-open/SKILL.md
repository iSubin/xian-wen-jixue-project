---
name: xian-open
description: Use when receiving a concrete user request, opening or resuming a governed change, activating a parked change, or deciding whether work needs a change lifecycle. Must come before spec for any non-trivial work.
---

# xian-open

> Version note: this phase and skill were named `intake` before `rename-xian-intake-to-xian-open`. New protocol facts use `open`; old `intake` facts are legacy input only.

## 用途

把具体用户诉求打开为可治理 change，或把用户请求路由到已有 change、parked change、project startup、delivery close 或人工决策。

`xian-open` 是 change 入口，不是一般方向入口。用户只是说“继续 / 下一步 / go”时，优先交给 `xian-next` 消费上一条 handoff 或解释 canonical direction。

首次接手项目、初始化项目骨架、建立项目基线或项目开发纪律时，先使用 `xian-project-startup`。

默认 governed-lite 主路径是：

```text
open -> verify -> gate -> close
```

`xian-spec`、`xian-design`、`xian-plan`、`xian-build` 是需要澄清、设计、拆任务或实现时调用的辅助工作面，不是每个普通 change 都必须让用户感知的一串阶段。命中 audit trigger（审计升级触发器）时，才进入完整 verify / gate / release / archive 路径。

## 触发条件

在用户提出具体需求、bugfix、refactor、文档更新、运维动作，或请求可能对应已有 / parked change 时使用。

不要因裸回复“继续 / 下一步 / go”触发本 skill；这些词属于 `xian-next`。

## 默认交付意图

- 实现、修复、执行或完成具体 change 的请求携带默认 publish intent，授权当前主 Agent持续执行 Runtime-selected ordinary close 或 audit finalize/archive，再完成 `commit -> push`，无需用户二次确认。只有明确 release intent 才另行执行 `release verify`。
- 只读、评审、分析、设计、parked，以及用户明确给出的 `no-commit/no-push` 请求不携带 publish intent；不要把它们升级为 Git 交付。
- publish intent 是 Agent 执行纪律，不写入 change schema 或新 phase。真实阻塞、远端分叉、生产部署、密钥操作和无法归因的 dirty worktree 仍按既有边界暂停。

## 协议输入

- `AGENTS.md` / `CLAUDE.md`
- `.xian-harness/harness-protocol.yaml`
- `.xian-harness/state.yaml`
- `docs/项目基线.md` as project context when it already exists
- `.xian-harness/changes/{change-id}/`
- `.xian-harness/changes/{change-id}/gate/gate-result.json` when continuing after verification
- active Xian spec contract changes if this project uses Xian spec contract
- current branch, worktree status, and uncommitted changes

## 执行流程

1. Identify whether the request is a new change, continuation, refactor request, learning task, or operational task.
2. Inspect active changes, parked changes, and local dirty state.
3. If project baseline, AGENTS.md, CLAUDE.md, or project discipline is missing, route to `xian-project-startup` before opening a business change.
4. 路由前先暴露流程债务:
   - Active or dangling changes that are not closed or archived.
   - Dirty worktree or pack drift that can contaminate the next change.
   - Project docs-sync warnings or missing project documents.
   - Human decisions required before selecting a route.
5. Choose one route: resume current change, activate parked change, open a new change, capture a note, route to delivery close, or ask for human decision if active changes conflict.
   - 当 intent、acceptance 和 verification facts 已明确时，在同一次 `change open` 中传入 `--intent`、至少一个 `--acceptance` 和至少一个 `--verify`，让 `rev-0001` 直接成为真实契约；不要再用 `small-change-note.md` 建立第二事实源。
   - 结构化 facts 不完整时应让 CLI fail closed，不要退回模板化 open 后手工补治理文件。
6. Identify the next skill to load and the target project cwd.
7. 如果 proposal / design / tasks 中列出 future implementation path 或 future batch change name，默认标记为 candidate-only；只有用户明确选择并由 Harness lifecycle CLI 创建后，才可以成为 active workflow。
8. 不要 edit code in this skill.

## 工作区隔离策略

- 串行 change 默认 `serial-trunk`：在当前主工作区的本地默认分支持续小粒度 commit，不自动创建 feature branch 或 worktree。
- 采用 `serial-trunk` 且已安装 xian-commit 时，项目必须使用 `push.mode=explicit-only`；中间 commit 只保存在本地，普通发布在 change-local 验证、Gate、clean tree 和远端安全检查通过后显式 push，不触发 full suite。
- 只有真实并行、用户明确要求、无法归因的 dirty worktree 或长时间高风险实验，才使用 `parallel-isolated`：创建 worktree 与本地临时 branch，默认不推远端。
- worktree 决策是本地执行纪律，不新增 change phase，不新增 tracked worktree registry，也不新增强制治理文档。
- 创建、删除或 prune worktree 等 worktree 拓扑变化不得触发 verify evidence 失效、full verify 或项目投影 churn（投影抖动）。
- 只要 Git tree matches verified tree（Git 文件树匹配已验证文件树），允许后续 close / commit 复用 commit-bound evidence（提交绑定证据）；真实代码树变化必须重新验证。

## 常见分支

- 常规路径：按 `nextAction` 和当前 change state 选择下一步；对普通 governed change，优先保持 `open -> verify -> gate -> close` 的轻量主路径。
- small hotfix 候选：仅当用户需求是单点低风险修复、文档 typo、交互文案修复、局部测试补充或不会改变协议状态机的轻量 bugfix 时，建议 `change open --tier small`，后续走 `quick-verify` 和 `quick-close`。
- small hotfix 升级：如果需求触及 schema、state-machine、gate、archive、release、pack、profile、skill contract、security、migration、cross-module runtime、quality mechanism 或不可局部验证范围，必须按 Standard / Major lane 进入 `xian-spec` / `xian-design`。
- 证据不足：先补 verify evidence 或明确记录 blocked reason。
- 发现职责不匹配：缺 project 事实时交接到 `xian-project-startup`；纯方向仲裁交给 `xian-next`。

## 真实项目 Lane 判断

真实项目的新需求入口必须先判断 real-project lane（真实项目执行通道），再选择 change tier 和后续 skill：

| Lane | 适用场景 | 最小闭环 |
|---|---|---|
| lightweight lane | 配置小改、局部代码、小验证、无生产数据和客户交付风险 | 任务记录、明确 command-anchor（命令锚点）、fresh verification、提交收口；不默认 release/archive。 |
| production lane | 真实数据库、外部服务、生产配置、备份、数据迁移、启动 smoke | 备份/回滚说明、连通性验证、数据核对、启动 smoke、必要 gate evidence。 |
| delivery lane | 客户验收、上线门禁、安全边界、可审计交付 | full gate、release acceptance、archive 和可复盘 evidence。 |

- 入口输出必须用中文说明选择了哪条 lane，以及为什么不是更轻或更重。
- lightweight lane 不是免治理；它只减少不必要的 release/archive 产物，不降低验证要求。
- 只要需求涉及生产数据、安全、客户交付、协议栈、state-machine、gate、archive、release、pack、profile、跨模块 runtime 或不可局部验证风险，就不能停留在 lightweight lane。

## 确定性工具

- `xian-harness status --target <target-project> --json`
- `xian-harness continue --target <target-project> --json`
- `xian-harness change list --target <target-project> --json`
- `xian-harness change list --target <target-project> --parked --json`
- `xian-harness change inspect <change-id> --target <target-project> --json`
- `xian-harness change open <change-id> --target <target-project> --json`
- `xian-harness change open <change-id> --target <target-project> --intent <text> --source <text> --acceptance <text> --verify <command> --json`
- `xian-harness change activate <change-id> --target <target-project> --json`
- `git status --short --branch`
- `find <target-project> -maxdepth 2 \( -name package.json -o -name pom.xml -o -name requirements.txt -o -name go.mod -o -name Cargo.toml \)`

## 必需证据

- Chosen target project.
- Scene classification: new-change / continuation / refactor-request / learning / operational.
- Project Baseline path and status when available, or route to `xian-project-startup` when missing.
- Chosen change id or reason no change is needed.
- Current phase/mode from `.change-state.json` when available.
- Dirty worktree summary and risk notes.
- Process debt summary: active or dangling changes, parked candidates, docs-sync warnings, pack drift, and required human decisions.

## 参考样例

- `standardize-chinese-skill-contract-v2`: 从用户意图进入正式 change 的 open 参考。

## 自检清单

- 是否识别 scene、target project 和候选 change？
- 是否暴露 active/dangling changes、dirty worktree、docs-sync、pack drift 等流程债务？
- 是否只选择一个下一步 route？
- 是否没有在 open 阶段编辑代码？

## 输出

- Recommended route.
- Project startup requirement when project baseline or discipline is missing.
- Change id when known.
- Next skill to load.
- 流程债务以可执行选择形式暴露，而不是只给原始 CLI 输出。
- Any blocking human decision.

## 交互预算

- 必须：obey the current hook-provided Interaction Budget before reading files or running commands.
- 必须：keep chat-mode requests tool-free unless the user explicitly asks for inspection, snapshot refresh, deep audit, or change execution.
- 必须：require explicit deep-audit or change intent before reading pack state, workbench, quality-gate, archive, or other large project status artifacts.

## 交接规则

- 当前请求携带 publish intent 且不存在真实阻塞时，不要输出等待用户回复“继续”的 handoff；在同一任务中直接进入下一 lifecycle skill，直到 Git delivery 完成。
- 当前请求不携带 publish intent 时，从运行时 `nextAction` 开始；先输出 scene、target project、流程债务和 recommended route；末尾输出 `下一步建议：<中文下一步>`，空一行后单独输出 `$xian-xxx`，再空一行输出 `直接回复“继续”即可进入该步骤。`；不要在首屏附加“因为...”。
- 如果运行时 `recommendedAction` 是 `project-idle-next` 或下一步需要用户二选一，不要输出 `直接回复“继续”即可进入该步骤。`；改为提示用户明确回复“查看项目状态”或给出一个真实小需求。
- 如果下一步来自 proposal / design / tasks 中的 future implementation path 或 future batch change name，不要输出 `直接回复“继续”即可进入该步骤。`；改为提示用户明确选择要创建的 change，或先查看项目状态。
- 如果用户需求是 small hotfix 候选，末尾建议写成：`下一步建议：按 small hotfix 打开轻量 change，使用 targeted verification 后 quick-close`，下一行 skill 使用 `$xian-spec`；不要把 small hotfix 写成免验证路径。
- 如果命中升级信号，末尾建议写成：`下一步建议：本需求命中升级信号，按 Standard / Major lane 明确 spec 和 design`，下一行 skill 使用 `$xian-spec`。
- 表达层原则：中文优先，默认用自然中文给结论、必要风险和下一步；必须保留英文术语、协议字段、状态名或命令名时，紧跟中文括注解释；不写“流程报告 / Review 报告 / evidence 清单”式长篇；只有 deep-audit、gate、verify 或用户明确要求完整显性化时才展开治理细节。
- Default mapping: concrete demand -> `xian-open`; fresh evidence needed -> `xian-verify`; gate decision needed -> `xian-gate`; governed delivery close -> `xian-commit` / close. Use `xian-spec` / `xian-design` / `xian-plan` / `xian-build` only when the current request actually needs requirement clarification, design, task sequencing, or implementation work.
- If the mapping conflicts with runtime `nextAction`, state the conflict and run `$xian-next` or `xian-harness continue --json` for arbitration.
- 不要 create a second handoff source from static rules alone.
- 如果发现误开 change、错误 `activeChange` 或错误工作流，先停止并用 Harness lifecycle CLI 或撤销未提交状态恢复 canonical state；change 生命周期由框架状态机和命令行工具驱动，不要新建另一个 change 去管理这个错误。

## 约束与原因

- 不要在本 skill 中实现代码。原因：open 负责需求进入和路由，混入实现会破坏 change 边界。
- 不要为同一目标创建重复 change。原因：重复 change 会制造流程债务并稀释事实源。
- `change open` 的 relation 与 work authorization 由 `xian-agent-harness/src/protocol/change.ts` 和 accepted contract Runtime authority 裁决；Skill 不用自由文本判断 change-over-change。Runtime 拒绝 `manage` / `close` / `reject` / `replace` relation 后，消费其提示并改走现有 `pause` / `resume` / `abandon` lifecycle，或在 machine admission 完整时使用 `incident-repair` relation。原因：结构化 relation 才能稳定区分合法 linkage 与用新 change 管理旧 change 的流程错误。
- 不要因为 proposal / design / tasks 中列出 future implementation path 或 future batch change name，就自动创建、继续或 handoff 到该 future change。原因：future path 是 candidate-only roadmap evidence，不是当前 lifecycle command；只有用户明确选择并由 Harness CLI 创建后才进入 active workflow。
- 不要把项目接手、项目基线或目录骨架初始化塞进 open。原因：project 级长期事实属于 `xian-project-startup`。
- 不要把 small hotfix 当成默认省流程入口。原因：small hotfix 只减少不必要的文档和 release/archive 产物，不降低验证要求。
- 不要把 CLI 当作主要决策源；CLI 只支持检查。原因：路由决策必须结合用户意图、项目基线和 change 状态。
- 不要激活垂直 profile，除非 cwd、prompt 或 adapter policy 证明它相关。原因：错误 profile 会污染通用 change 流程。
