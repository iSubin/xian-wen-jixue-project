# commit message 规范(给 AI 写 message 时参考)

## 格式

```
<type>: <纯中文简短标题>

<中文正文,说明改了什么 / 为什么改 / 影响范围>
```

## type 白名单

- `feat` —— 新功能
- `fix` —— bug 修复
- `refactor` —— 重构(不改行为)
- `docs` —— 文档
- `test` —— 测试
- `chore` —— 杂项(构建、CI、依赖等)

## 标题要求

- 纯中文(默认)
- 简短,一行内能读完(建议 < 30 字)
- 不含 type 前缀(防 `feat: feat xxx` 二次拼接)
- 不含英文(英文项目用配置关闭,见 Phase 2)
- 不含 emoji

## 正文要求

必须有正文。正文要说明:

- 改了什么
- 为什么改(动机 / 上下文 / 触发场景)
- 影响范围(哪些模块、哪些用户场景)

正文不写"做了什么"——diff 已经能看出来。写"为什么",这是 commit message 的核心价值。

## 例子

```
feat: 加强 bridge 状态机与产物校验

bridge 在多 agent 协作时容易状态错乱,新增状态机校验避免中途状态丢失,
重构流式输出逻辑减少内存峰值,影响 bridge 模块及其下游调用方。
```

```
fix: 修复 relay 模式下 gate.md 解析空指针

gate.md 在 active change 刚切换但未写盘时会短暂不存在,旧逻辑直接读取
触发 NPE。改为先 stat 再读,影响 .xian-relay/changes/ 加载链路。
```

```
refactor: 收敛配置加载入口到 config.py

原本 config 加载散落在 5 个模块各自实现,导致默认值不一致。统一到
config.py 一个入口,各模块 import。不影响外部行为。
```

```
docs: 补充 install.sh 用法到 README

社区反馈不知道怎么装 hook,补 README 安装小节,加入常见问题。
```

## 反例

`update`

缺 type、缺标题、缺正文。

`fix`

单 type,无意义。

`feat: improve bridge state machine`

英文标题,默认要求中文。

`feat: feat 加强 bridge`

标题重复 type 前缀,会被 commit-msg hook 拦。

`feat: 加强 bridge`(单行)

缺正文。

`feat: 加强 bridge [emoji]`

含 emoji,会被 commit-msg hook 拦。emoji 包括但不限于表情、庆祝手势、箭头等 Unicode 符号。

## 执行要求

- 每次提交必须可运行(Python 脚本通过 `python3 -c "import ast; ast.parse(...)"` 等)
- 不要用 `--no-verify` 绕过 hook
- 不要禁用测试
- 解释"为什么",而不是"做了什么"

## 给 AI 的提醒

你(AI agent)写 commit message 时,本文件是质量参考。

hook 只校验形式(type 在不在白名单、标题是不是中文、有没有正文),hook 校验不了"标题是否真简短""正文是否真解释为什么"——这部分由你负责。

如果 commit 被 commit-msg hook 拦,看 hook 输出的"问题"和"期望格式",按本文件调整。
