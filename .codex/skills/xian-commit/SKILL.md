---
name: xian-commit
description: Use when a verified or archived change needs Git delivery, or when the user asks to commit, push, close out, or handle a dirty worktree.
---

# xian-commit

## 用途

收口 Git delivery（代码交付）：归因 dirty worktree（当前工作区有未提交变化）、拆分合理 commit（提交），并按项目策略决定是否 push（推送）。

## 触发条件

Use this skill when the user asks to commit, push, close out, deliver, handle dirty worktree, or finish Git delivery after a change is verified or archived.

## 协议输入

- `git status --short --branch`
- `git diff --stat`
- `git diff --cached --stat`
- `git ls-files --others --exclude-standard`
- `.xian-commit/config`
- `AGENTS.md` / `CLAUDE.md` commit message rules
- `.xian-harness/changes/{change-id}` when closing a governed change
- `.xian-harness/releases/{change-id}` when closing archive evidence

## 执行流程

1. Attribute dirty worktree（归因未提交文件） before staging anything.
2. Split unrelated changes into separate commits or stop when scope is unclear.
3. Stage only explicit pathspecs for the current logical commit.
4. Write a Chinese commit message with type, title, and explanatory body.
5. Commit without `--no-verify`.
6. Follow `.xian-commit/config` push policy and the current task's publish intent.
7. Report commit hash, push status, and any remaining worktree state.

## 默认交付意图

- 实现、修复、执行或完成类 change 携带默认 publish intent。最终 commit clean 且 review / Gate 已通过时，当前主 Agent 直接完成 fast-forward push，不得停下来等待用户再次授权；普通发布不自动承担 integration coordinator。
- `push.mode=explicit-only` 只禁止 post-commit hook 自动 push；它不禁止当前主 Agent 显式 push。普通 push 只执行 Git tree、远端分叉和 force-push 安全检查，不触发 full suite。
- 只读、评审、分析、设计、parked 或 `no-commit/no-push` 请求不进入默认发布路径。普通中间 commit 仍只保存在本地。

## Workspace Finish 边界

- 串行 change 默认 `serial-trunk`（串行主线）：在当前主工作区的本地默认分支持续小粒度 commit，不自动创建 feature branch 或 worktree（工作树）。
- `serial-trunk` 必须使用 `push.mode=explicit-only`；中间 commit 只保存在本地，普通发布在 change-local 验证、Gate、clean tree 和远端安全检查通过后显式 push。
- 只有真实并行、用户明确要求、无法归因的 dirty worktree 或长时间高风险实验才使用 `parallel-isolated`（并行隔离），创建 worktree 与本地临时 branch，默认不推远端。
- worktree 管理是本地执行纪律，不新增 change phase，不新增 tracked worktree registry，也不新增强制治理文档或 commit evidence（提交证据）。
- 创建、删除或 prune worktree 等 worktree 拓扑变化不得触发 verify evidence 失效、full verify 或项目投影 churn（投影抖动）。
- 如果确实因真实并行、用户明确要求、无法归因的 dirty worktree 或长时间高风险实验使用 worktree，创建者负责 merge、目标分支验证和清理。
- 只有 Git tree matches verified tree（Git 文件树匹配已验证文件树）时，才允许 commit-bound evidence reuse（提交绑定证据复用）；真实代码树变化必须重新验证。

## Release Verify 边界

- 普通 commit 与普通 push 不运行或读取 Release Verify，也不因 branch merge、batch 或代码规模自动形成 release candidate。
- 普通 commit、push、branch merge、batch 或 Goal 完成本身不触发 full suite。
- 只有版本、tag、Pack rollout、registry artifact 或 deploy candidate 等明确 release intent 才单独运行：

```sh
xian-harness release verify --target <target-project> --json
```

- Publication adapter 只消费精确匹配 immutable release candidate 的 passing Release Verify result；缺少结果时拒绝发布，不在 publish 命令内部自动补跑。
- Release Verify 后不得修改 candidate tree；Git tree、test portfolio、toolchain、release policy 或 current accepted contracts 变化都会形成新的 release candidate identity。
- CI 对同一 immutable candidate 只运行一次 Release Verify；tag、registry 与 deploy stage 消费同一 result，不重复执行 full suite。

## 快速归档证据收口

当 dirty worktree 只包含同一个 change 的 archive evidence（归档证据）和 project projection（项目投影）时，可以走快路径，但必须先运行只读 close-plan（收口计划）命令：

```sh
xian-harness delivery close-plan --target <target-project> --json
```

只有当返回的 `status` 是 `archive-evidence-close`，且 `changeId` 指向本次归档 change 时，才允许进入快路径。`status` 是 `unknown`、`changeId` 为空、`unknownPaths` 非空或 `mixedChangeIds` 非空时，必须回到常规 dirty worktree 归因。

快路径仍必须确认：

1. `archive-result.json` status 是 `archived`。
2. `release verify` 或 release acceptance evidence 是 pass（通过）。
3. `git diff --check` 通过。
4. secret literal scan（敏感字面量扫描）没有发现真实密钥。

## 常见分支

- 常规路径：归因 dirty worktree，拆分 scoped commit，再按 push policy 收口。
- archive evidence close：只在 close-plan 明确归因同一 change 时使用快路径。
- 来源不明：停止并列出文件，不提交。
- branch behind/diverged：停止，说明需要先同步，不自动 rebase 或 force push。
- push policy 禁止：只完成本地 commit，并说明远端未发布。

## 确定性工具

- `git status --short --branch`
- `git diff --stat`
- `git diff --cached --stat`
- `git ls-files --others --exclude-standard`
- `git diff --check`
- `git commit`
- `git push`
- `xian-harness delivery close-plan --target <target-project> --json`

## 必需证据

- Dirty worktree attribution（工作区归因） summary.
- Staged path list for each commit.
- Commit hash and Chinese commit message.
- Push decision and policy reason.
- Remaining dirty / ahead / behind state.

## commit message 格式

```text
<type>: 中文简短标题

中文正文，说明改了什么、为什么改、影响范围。
```

常用 type：`feat`、`fix`、`refactor`、`docs`、`test`、`chore`。

## 参考样例

- `replace-change-session-lease-with-scoped-file-lock`: archive evidence close 后的 commit / push 收口参考。
- `compact-historical-change-artifacts`: path-scoped staging 与 auto-safe push 参考。

## 自检清单

- 是否先归因 staged / unstaged / untracked 文件？
- 是否避免了 `git add -A` 和 `git add .`？
- 是否每个 commit 只包含一个逻辑单元？
- 是否写了中文标题和中文正文？
- 是否没有使用 `--no-verify`？
- 是否按 `.xian-commit/config` 判断 push？

## 输出

- Commit hash（提交哈希）和标题。
- Push（推送）是否完成，以及原因。
- Remaining worktree / ahead / behind status.
- 如果阻断，给出最小下一步。

## 交互预算

- 必须：obey the current hook-provided Interaction Budget before reading files or running commands.
- 必须：keep chat-mode requests tool-free unless the user explicitly asks for inspection, snapshot refresh, deep audit, or change execution.
- 必须：require explicit deep-audit or change intent before reading pack state, workbench, quality-gate, archive, or other large project status artifacts.

## 交接规则

- 当前请求携带 publish intent 且不存在真实阻塞时，由同一主 Agent在同一任务中完成 commit 与 push；只有明确 release intent 才另行执行 Release Verify。只有 Git delivery 完成后才输出终态结果，不输出等待用户回复“继续”的 handoff。
- 当前请求不携带 publish intent 时，输出时先说明 commit / push 结果、剩余工作区状态和阻断风险；末尾输出 `下一步建议：<中文下一步>`，空一行后单独输出 `$xian-xxx`，再空一行输出 `直接回复“继续”即可进入该步骤。`；不要在首屏附加“因为...”。
- 如果 Git delivery 已完成且项目 idle，不要推荐继续提交；推荐下一项真实需求或项目状态查看。
- 如果 dirty worktree 来源不明，不要输出 `直接回复“继续”即可进入该步骤。`；改为要求用户决定保留、拆分或另开处理。
- 表达层原则：中文优先，默认用自然中文给结论、必要风险和下一步；必须保留英文术语、协议字段、状态名或命令名时，紧跟中文括注解释；不写“流程报告 / Review 报告 / evidence 清单”式长篇；只有 deep-audit、gate、verify 或用户明确要求完整显性化时才展开治理细节。
- Default mapping: clean + ahead -> push policy check; dirty attributed -> commit; dirty unknown -> stop for attribution; behind/diverged -> stop for synchronization decision.
- If the mapping conflicts with runtime `nextAction`, state the conflict and run `$xian-next` or `xian-harness continue --json` for arbitration.

## 约束与原因

- 不要使用 `git add -A` 或 `git add .`。原因：无差别 staging 会把临时文件、运行态派生产物或 unrelated changes 混进交付，破坏 commit 事实边界。
- 不要使用 `git commit --no-verify`。原因：绕过 hook 会跳过项目提交格式、安全和路径策略，破坏交付证据链。
- 不要提交来源不明的 dirty 文件。原因：Git commit 是产品事实，不能把未知运行态漂移包装成已完成工作。
- 不要把多个无关逻辑单元放进一个 commit。原因：后续 review、revert 和 release attribution 需要 commit 边界清晰。
- 不要把 read-only、review、design、parked 或 `no-push` 意图推断成 publish intent。原因：默认授权只来自当前具体实现任务与项目规则，明确的范围缩小始终优先。
- 不要执行 force push、reset、clean、stash pop 或删除分支。原因：这些动作会覆盖或删除用户状态，必须逐项获得本轮明确授权。
