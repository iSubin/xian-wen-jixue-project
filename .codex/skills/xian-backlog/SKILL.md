---
name: xian-backlog
description: Use when recording, listing, importing, promoting, or closing project backlog/todo items through the registry-first project work queue.
---

# xian-backlog

## 用途

操作 Project Backlog（项目待办队列）的公开入口。它把用户的后续项写入 `.xian-harness/backlog/registry.json`，再由 Document Render Pipeline 渲染 `docs/待办清单.md`。

`xian-backlog` 不直接编辑 `docs/待办清单.md`，不自动 activate change，也不替代 `xian-batch` 或 future goal runtime。

## 触发条件

当用户要求“记录待办”“列出待办”“导入候选 change”“promote 待办”“关闭待办”“处理 backlog / todo / 工作队列”时使用。

不要因普通“继续”直接触发本 skill；普通 continuation 由 `xian-next` 调用 `xian-harness continue` 决策。

## 协议输入

- `.xian-harness/backlog/registry.json`
- `docs/待办清单.md`
- `.xian-harness/state.yaml`
- `.xian-harness/changes/{change-id}/.change-state.json`

## 执行流程

1. 确认 target project root。
2. 判断用户意图是 list、add、import、promote 还是 close。
3. 使用 `xian-harness todo ...` 作为公开命令入口；仅在兼容旧脚本时使用 hidden `xian-harness backlog ...`。
4. mutation 后检查命令输出，并确认 `docs/待办清单.md` 是 render output，不手写。
5. promote 默认创建 parked change；真正执行必须再走 `xian-harness change activate <change-id>`。

## 确定性工具

- `xian-harness todo list --target <target-project> --json`
- `xian-harness todo add <item-id> --title "<title>" --priority P1 --source user-request --summary "<summary>" --target <target-project> --json`
- `xian-harness todo import --target <target-project> --file <file> --dry-run --json`
- `xian-harness todo import --target <target-project> --file <file> --json`
- `xian-harness todo promote <item-id> --target <target-project> --as-change <change-id> --json`
- `xian-harness todo close <item-id> --target <target-project> --reason "<reason>" --json`
- `xian-harness docs render --target <target-project> --doc todo-list --fix --json`

## 必需证据

- Target project root。
- Backlog registry mutation command output。
- `.xian-harness/backlog/registry.json` 中对应 item。
- `docs/待办清单.md` 的渲染结果或 render status。
- 如果 promote，必须记录 linked parked change id。

## 参考样例

用户说“记录一个待办：后续补登录超时测试”时，使用：

```text
xian-harness todo add add-login-timeout-test --title "补登录超时测试" --priority P2 --source user-request --summary "补登录超时测试，未来 promote 成独立 change。" --target <target-project> --json
```

用户说“把这个待办转成 change”时，使用：

```text
xian-harness todo promote add-login-timeout-test --target <target-project> --as-change add-login-timeout-test --json
```

然后明确下一步是 activate，而不是自动开始开发。

## 自检清单

- 是否写入的是 `.xian-harness/backlog/registry.json`？
- 是否没有手写 `docs/待办清单.md`？
- 是否没有自动 activate parked change？
- 是否给出了下一条确定性命令？
- 是否把冲突和 skipped item 如实报告？

## 禁止事项

- 不手写 `docs/待办清单.md` 来改变待办状态。
- 不把聊天里的候选列表当作执行授权。
- 不在 import/promote 后自动 activate change。
- 不创建 batch runtime、goal runtime 或 parallel worker。
- 不绕过 backlog registry。

## 输出

- Backlog item id、状态、priority 和 linkedChange。
- 下一条确定性命令，例如 promote、activate 或 close。
- 如有冲突，列出 skipped/conflict item，不猜测覆盖。

## 交互预算

- 记录单个待办：最多读取 project root、registry 和命令输出。
- 批量 import：先 `--dry-run`，再等待用户确认是否真实导入。
- 不读取 unrelated change evidence，除非用户要求 promote 或 activate。

## 交接规则

输出末尾必须使用以下格式：

末尾先输出 `下一步建议：<中文下一步>`，空一行后单独输出 `$xian-xxx`，再空一行输出 `直接回复“继续”即可进入该步骤。`。

```text
下一步建议：<中文下一步>

`$xian-xxx`

直接回复“继续”即可进入该步骤。
```

当下一步仍需要用户选择 item 或确认 import 时，`$xian-xxx` 应为 `$xian-backlog`；当下一步是执行 parked change 时，应为 `$xian-next` 或 `$xian-open`。

## 约束与原因

- 不直接编辑 `docs/待办清单.md`。原因：该文件是 rendered view，直接编辑会让 registry 与人读表面分叉。
- 不自动 activate change。原因：parked change 是候选容器，activate 才是执行授权边界。
- 不创建 batch runtime。原因：本 skill 只负责 project backlog，goal/batch execution 需要独立事实源和恢复语义。
- 不把聊天列表当事实源。原因：跨 session 恢复必须依赖 registry，而不是一次聊天上下文。
