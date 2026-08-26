# Hook Contract

Template Contract: xian-harness/hooks/hook-contract

## Template Quality Contract

| 项 | 内容 |
|---|---|
| Fact Sources | hook source file、runtime config、skill registry、profile policy、hook smoke evidence。 |
| Owner Role | Hook Steward / Gatekeeper Agent。 |
| Verification Commands | `xian-harness check {change-id} --target <target-project> --json`。 |
| Evidence Paths | `.xian-harness/changes/{change-id}/gate/gate-result.json`。 |

## Hook Summary

- Hook name:
- Runtime path:
- Owner skill: `xian-hook-governance`
- Target profile: base / typescript / python / deployment-ops / custom
- Status: proposed / active / deprecated

## Lifecycle Event

| Runtime | Event | Matcher | Command |
|---|---|---|---|
| Codex | SessionStart / UserPromptSubmit / PreToolUse | {matcher} | {command} |
| Claude | SessionStart / UserPromptSubmit / PreToolUse | {matcher} | {command} |

## Runtime Adapter

说明此 hook 面向哪个运行时，以及为什么不能直接复制到另一个运行时。

| 项 | 说明 |
|---|---|
| 输入来源 | stdin JSON / environment / cwd |
| 输出协议 | Codex hookSpecificOutput / Claude decision / empty JSON |
| 超时策略 | {timeout} |
| 失败策略 | fail-open / fail-closed / warn-only |

## Input Schema

列出 hook 会读取的字段。没有使用的字段不要写成依赖。

| 字段 | 来源 | 是否必需 | 用途 |
|---|---|---:|---|
| `cwd` | runtime input | yes/no | 判断目标项目和 profile。 |
| `prompt` | runtime input | yes/no | 判断 skill 激活或跳过条件。 |
| `tool_name` | runtime input | yes/no | 判断工具类型。 |
| `tool_input` | runtime input | yes/no | 判断命令、patch 或文件路径。 |

## Output Contract

| 输出 | 语义 | 何时使用 |
|---|---|---|
| `{}` | 放行，不注入上下文。 | 无需拦截或注入。 |
| `hookSpecificOutput.additionalContext` | 注入轻量上下文。 | Codex SessionStart 读取 bootstrap context，UserPromptSubmit 注入 skill routing。 |
| `hookSpecificOutput.permissionDecision=deny` | 阻断工具执行。 | 高危命令或越界写入。 |
| `systemMessage` | 警告但不阻断。 | 敏感文件写入、发布提醒。 |

## Fact Sources

Hook 只能执行事实源，不应把规则写死成唯一事实源。

| 事实源 | 用途 | 是否允许缺失 |
|---|---|---:|
| `.xian-harness/skill-registry.json` | skill 激活和 profile 路由。 | yes/no |
| `.xian-harness/bootstrap-context.json` | session bootstrap context。 | yes/no |
| `harness-pack/manifest.yaml` | Pack profile 和 hook 资产声明。 | yes/no |
| `.xian-harness/pack-state.json` | 安装状态和资产漂移。 | yes/no |

## Skip Conditions

| 条件 | 原因 | 期望输出 |
|---|---|---|
| Resume / context compaction | 避免重复注入大段上下文。 | `{}` |
| Explicit slash command | slash command 自带工作流入口。 | `{}` |
| Reserved pack / reference path | 避免开发 Harness 自身时误触垂直 profile。 | `{}` |
| Missing optional fact source | 保持 hook fail-open，避免阻断普通工作。 | `{}` |

## Profile Boundary

| 场景 | 应激活 | 禁止 |
|---|---|---|
| base project | `xian-*` skills / base hooks | profile-specific skills、commands、hooks |
| typed / ops project | base + selected profile assets | 把 profile-specific 规则写入 base |
| references project | read-only exploration | 写入参考工程或复制商业代码 |
| harness-pack development | asset governance only | 垂直业务 skill 误触 |

## Guard Rules

| 规则 | 行为 | 证据 |
|---|---|---|
| 危险命令 | deny | hook unit test / smoke |
| 敏感文件写入 | warn-only | hook unit test / smoke |
| skill registry 命中 | inject required skills | hook unit test |
| profile mismatch | no injection or gate issue | hook + gate test |

## Verification Commands

- [ ] `npm test -- --run test/skill-registry.test.ts test/skill-contract.test.ts`
- [ ] `npm test -- --run test/pack.test.ts`
- [ ] `xian-harness pack status --target <target-project> --profile auto --json`

## Change Notes

- 修改内容：
- 为什么修改：
- 影响范围：
- 回滚方式：
- 后续观察：
