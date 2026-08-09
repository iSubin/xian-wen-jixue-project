---
name: xian-commit
description: AI coding agent 的 Git 交付治理入口。当用户要求提交、commit、push、推送、收口或处理 dirty worktree（当前工作区有未提交变化）时使用本 skill。按 prompts/commit-message.md 写 message,调用标准 git 命令,hook/policy 兜底校验。普通 push 由 policy 控制,force push 和破坏性 git 动作必须显式授权。
---

# xian-commit 工作流

xian-commit 是面向 code agent 的 Git 交付治理资产集合。你(AI agent)处理 commit / push / dirty worktree（当前工作区有未提交变化） / commit message / hook 拦截时,按下面工作流走。

## 核心原则

1. **细粒度 commit**:不要把一堆无关改动塞进一个 commit。按逻辑单元拆分,一个 commit 做一件事。
2. **commit message 由你写**:你看 diff,自己想 type / 标题 / 正文。**不要让工具替你想**。
3. **形式兜底靠 hook**:`hooks/pre-commit` 和 `hooks/commit-msg` 校验形式。你写错了它们会拦,但你不能依赖它们替你思考。
4. **普通 push 由 policy 控制**:默认配置为 `push.mode=auto-safe`,安全条件全部满足时可执行普通 push;配置缺失或 `explicit-only` 时需要用户明确说"push"或"推送"。commit 是本地动作,push 是对外发布。
5. **不绕过 hook**:永远不要 `git commit --no-verify`。hook 误拦修 hook,不绕过。
6. **无状态优先**:只从当前 git 事实、hook 输出、policy/config 和本轮明确授权判断,不要记忆"上次授权"。

## 触发语义

| 用户说法 | 进入路径 |
|---|---|
| "提交吧" / "commit it" | 本地交付收口:检查 dirty worktree（当前工作区有未提交变化）,拆分并执行 commit |
| "推送一下" / "push" | 远端交付收口:检查 clean、ahead/behind、upstream 后执行普通 push |
| "commit and push" / "提交并推送" | 先本地收口,再远端收口;这句话可作为普通 push 授权 |
| "收口" / "交付一下" | 先读 git 事实;dirty 走本地收口,clean 且 ahead 走远端收口 |

change finished / archived 只说明业务完成,不代表 Git 交付完成。worktree clean + commit 完成才是本地交付收口;分支不再 ahead 且 push 完成才是远端交付收口。

## commit 流程

### 1. Dirty worktree 归因

提交前先把当前工作区事实归因清楚。运行:

```sh
git status --short --branch
git diff --stat
git diff --cached --stat
git ls-files --others --exclude-standard
```

必要时再读 `git diff`、`git diff --cached` 或新建文件内容。

把 staged / unstaged / untracked 分成三类:

1. **属于本次交付**: 与用户当前要求或已完成工作一致,可以进入 commit 计划。
2. **不属于本次交付**: 暂停并询问用户是保留、拆分、丢弃还是另开处理。
3. **来源不明**: 暂停,列出文件和判断依据,不要提交。

dirty worktree（当前工作区有未提交变化）只是代码事实,不自动代表可以提交,也不推进任何业务 change 状态。禁止在未归因前 `git add -A`。

### 2. 交付收口的即时状态

xian-commit 不写长期状态,但本轮运行要按 Git 事实判断即时状态:

| 状态 | 判定 | 下一步 |
|---|---|---|
| `dirty-unattributed` | staged / unstaged / untracked 尚未归因 | 先归因 |
| `committable` | 文件归因清楚,提交范围可解释 | 做 commit 计划 |
| `local-delivered` | worktree clean,本地 commit 完成 | 检查是否 ahead |
| `pending-push` | worktree clean 且 branch ahead | 等待本轮明确 push 授权 |
| `remote-delivered` | worktree clean 且 branch 不 ahead | 无需 Git 收口 |
| `blocked` | behind、diverged、protected branch 或来源不明 | 停止并说明阻断 |

### 3. 拆细粒度 commit 计划

在你的脑子里(不调用工具),决定:

- 这次改动要拆成 N 个 commit?
- 每个 commit 涉及哪些文件?
- 每个 commit 是什么 type?(feat/fix/refactor/docs/test/chore)
- 每个 commit 的标题(纯中文)和正文(说明为什么)?

拆分原则:

- 一个 commit 一个逻辑单元(feature / bugfix / refactor / doc / test)
- 源码和对应测试可以放一起(测试跟代码一起 commit)
- 跨模块的大重构,按模块拆
- 生成日志、runtime、临时文件和证据噪声不能混入业务 commit
- hook / skill / policy 同步属于治理资产,应和业务代码分开提交

### 4. 逐个 commit

对每个 commit:

```sh
git add <这个 commit 涉及的文件>
git commit -m "$(cat <<'EOF'
<type>: <纯中文标题>

<中文正文,说明为什么>
EOF
)"
```

注意:

- 用 heredoc 写多行 message,不要用多个 `-m`
- `--no-verify` 永远不要加

### 5. 如果 hook 拦截

`pre-commit` 或 `commit-msg` 会输出问题 + 期望格式。看输出,按 [prompts/commit-message.md](prompts/commit-message.md) 调整。

**不要绕过**(不加 `--no-verify`)。修 message 或修 staged 文件,重新 commit。

### 6. 全部 commit 完成后

读取 `.xian-commit/config` 的 `push.mode`:

- `explicit-only` 或未配置:停下来,告诉用户:"已完成 N 个细粒度 commit,是否 push?"
- `auto-safe`:如果本轮刚完成 commit、tracked/staged worktree 干净、当前分支只 ahead、不 behind / diverged、有 upstream、未匹配 protected branch,则允许显式 push 到 upstream 分支。未跟踪文件不单独阻断 auto-safe。如果任一条件不满足,停下来说明原因并等待用户明确授权。
- `never`:不要 push,并说明项目 policy 禁止 push。

**不要把"继续"解释为 push 授权**。只有本轮明确说 push,或 `push.mode=auto-safe` 且安全条件同时满足,才能 push。

## push 流程(显式授权或 auto-safe)

```sh
git push
```

`pre-push` hook 会检查当前分支相对 upstream 的 behind 状态。如果被拦:

```sh
git pull --rebase origin <branch>
git push
```

如果用户没有明确说 push,只报告当前分支 ahead/behind 状态,不要代替用户发布远端。

例外:`push.mode=auto-safe` 且本地交付收口后安全条件全部满足时,可以执行普通 push。post-commit 仍会触发 `pre-push` 做第二道 behind / protected / never 校验。auto-safe 不允许 `--force`、`--force-with-lease` 或任何会改写历史的动作。

## explicit-only 动作

以下动作必须逐项获得本轮明确授权:

- `git push`、`git push --force`、`git push --force-with-lease`
- `git reset`、`git clean`
- 删除 branch / tag
- `git stash pop` 或可能覆盖工作区的 stash 操作
- 对已发布提交执行 rebase / amend / squash

普通 push 可以由"push"、"推送一下"、"commit and push"明确授权,或由 `push.mode=auto-safe` 在安全条件全部满足时触发。force、reset、clean、delete 不能从"继续"、auto-safe 或历史上下文推断授权。

## policy/config

可选配置文件为 `.xian-commit/config`,格式见 [policy.example.conf](policy.example.conf)。

最小 schema 只覆盖:

- `push.mode`
- `branch.protected`
- `path.allow`
- `path.deny`
- `message.types`
- `message.title_language`
- `message.body_required`

`path.allow` 在 denylist 前生效,用于放行项目明确拥有的协议证据或审计产物。默认 pre-commit 不拒绝普通 `*.log`;项目如需限制日志,应通过 `path.deny` 自行配置。

`push.mode` 取值:

- `auto-safe`:默认配置,commit 完成后安全条件满足时自动普通 push。
- `explicit-only`:关闭自动 push,只有当前用户请求明确说 push 才执行普通 push。
- `never`:拒绝所有 push。旧配置 `disabled` 视为 `never` 兼容。

policy/config 是规则,不是运行状态。不要在里面记录 change 阶段、上次 push 授权或 agent 计划。

本 skill 同时适用于 Codex 和 Claude Code。第一版不分叉平台专用说明,如果未来触发语义明显分化再拆源文件。

changelog 只做非阻断提醒,不作为 commit / push / gate 的阻断条件。

## changelog 策略

默认不生成、不维护 changelog。只有项目 policy 或用户明确要求时,才检查 staged 范围是否包含对应 changelog 文件。

检查结果只进入交付摘要:

- `not-required`
- `recommended`
- `required-by-policy`
- `present`
- `missing-nonblocking`

即使项目 policy 声明 changelog required,缺失也只作为 `missing-nonblocking` 进入交付摘要;`xian-commit` 不因 changelog 缺失阻断 commit、push 或 gate。

## 不要做的事

- 无脑 `git add -A` 或 `git add .`(会污染 commit,把临时文件、`.xian-relay/`、secrets 一并加)
- `git commit --no-verify`(绕过 hook)
- 把 `.xian-relay/`、`*.env`、`*.tmp`、`*.swp`、`id_rsa`、`*.pem`、`.DS_Store` 等 staged
- push 时未经用户授权
- force push / reset / clean / delete / stash pop 未逐项确认
- 用英文写 commit 标题
- commit message 加 emoji
- 缺正文的 commit(只有 `<type>: <标题>` 一行)

详细规范见 [prompts/commit-message.md](prompts/commit-message.md)。
