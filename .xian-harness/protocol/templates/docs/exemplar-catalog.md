# 样例索引

Template Contract: xian-harness/docs/exemplar-catalog

## Template Quality Contract

| 项 | 内容 |
|---|---|
| Fact Sources | `rg` / `rg --files` 搜索结果、目标项目本地实现、测试文件、项目约定。 |
| Owner Role | Builder Agent / Doc Steward。 |
| Verification Commands | `xian-harness docs inspect --target <target-project> --json`。 |
| Evidence Paths | `docs/样例索引.md` 或 change-local Exemplar Catalog。 |

本文件记录目标项目内可复用的本地样例。它的目标是让 Agent 在实现前优先模仿本项目已有风格，而不是凭空生成或复制外部参考代码。

## Scope

| 字段 | 内容 |
|---|---|
| Target Project | {target-project} |
| Profile | {base-or-vertical-profile} |
| Change / Scene | {change-or-scene} |
| Last Reviewed At | {yyyy-MM-dd HH:mm:ss} |
| Maintainer | {owner-or-agent} |

## Similar Implementations

记录和当前需求最相近的本地实现。优先选择同项目、同技术栈、同 profile 下的实现。

| 用途 | 本地文件 / 模块 | 为什么可参考 | 可复用点 | 禁止照搬点 |
|---|---|---|---|---|
| {feature} | `{path}` | {reason} | {patterns} | {do-not-copy} |

## Test Exemplars

记录测试样例，帮助 Builder 先补测试或维持当前测试风格。

| 测试类型 | 本地测试文件 | 覆盖点 | 推荐命令 |
|---|---|---|---|
| {unit-smoke-e2e} | `{path}` | {coverage} | `{command}` |

## Naming And Style

| 维度 | 本项目约定 | 证据 |
|---|---|---|
| 文件命名 | {style} | `{path}` |
| 函数 / 类命名 | {style} | `{path}` |
| 错误处理 | {style} | `{path}` |
| API / CLI 输出 | {style} | `{path}` |
| 测试断言 | {style} | `{path}` |

## Reuse Decision

实现前必须记录本次选择。

| 问题 | 结论 |
|---|---|
| 是否找到本地样例 | {yes-no} |
| 采用哪个样例 | `{path-or-none}` |
| 为什么采用 / 不采用 | {reason} |
| 是否需要新增样例 | {yes-no} |
| 是否需要进入 experience promote | {yes-no} |

## No Local Exemplar

如果没有找到本地样例，必须写明搜索范围和 fallback 规则。

| 搜索范围 | 命令 / 方法 | 结果 |
|---|---|---|
| `{path-or-glob}` | `{command}` | {result} |

Fallback 规则：

- 优先使用当前 profile 的模板、quality policy、verification registry 和 project conventions。
- 只把外部参考作为设计启发，不能复制外部参考代码。
- 生成新实现后，如果它具备复用价值，应在 archive 或 experience review 阶段提议加入本文件。

## Guardrails

- Do not copy external reference code.
- 不要把项目特有样例用于 base profile 工作。
- 不要把过期样例当作当前事实；样例必须能被当前仓库文件证明。
- 样例索引不是验收证据。验收仍以 acceptance、verify、gate、release 和 archive 事实为准。
