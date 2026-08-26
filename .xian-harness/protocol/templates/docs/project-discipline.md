# 项目开发纪律

Template Contract: xian-harness/docs/project-discipline

## Template Quality Contract

| 项 | 内容 |
|---|---|
| Fact Sources | `AGENTS.md`、`CLAUDE.md`、`.xian-harness/`、项目目录结构、profile 规则。 |
| Owner Role | Human Owner / Doc Steward / Gatekeeper。 |
| Verification Commands | `xian-harness docs inspect --target <target-project> --json`、`xian-harness continue --target <target-project> --json`。 |
| Evidence Paths | `docs/项目开发纪律.md`。 |

本文件定义目标项目的顶层开发纪律。它不是一次性需求文档，而是项目长期运行时的目录治理协议。

## 产品特性保全纪律

- 修复技术兼容性问题时，必须先识别被删除或修改的字段、文件、状态、提示或机制原本承载的产品目的。
- 不得为了让当前技术实现可运行，而直接牺牲已经定义过的产品特性，例如可校验、可审计、可恢复、可提示、可追踪或低侵入体验。
- 如果原实现方式与当前工具、runtime 或 parser 冲突，应优先寻找等价替代方案，例如 sidecar schema、测试契约、生成步骤、适配层、降级视图或文档化边界。
- 只有在替代方案已经落地并验证后，才能移除原载体；否则只能标记为兼容性限制，不能把特性当作已删除或已完成。
- 任何移除字段、状态、证据、提示或协议入口的改动，都必须说明：原目的、冲突原因、替代实现和验证方式。

## 摘要

- 项目：{project}
- 场景：takeover / refactor / new-project
- Profile：base / typescript / python / deployment-ops / custom
- 生成时间：yyyy-MM-dd HH:mm:ss
- 生成者：

## 顶层目录职责

| 目录 / 文件 | 职责 | 更新时机 | 维护角色 | 变更规则 |
|---|---|---|---|---|
| `AGENTS.md` | Codex / 通用 Agent 入口纪律。 | 开发纪律、提交规范、禁令或 profile 规则变化时。 | Human Owner / Doc Steward | 只写最高优先级规则和导航，不堆具体业务实现细节。 |
| `CLAUDE.md` | Claude Code 入口纪律。 | Claude 专属命令、hook、skill 或协作方式变化时。 | Human Owner / Doc Steward | 与 `AGENTS.md` 保持语义一致，但可保留 Claude 专属用法。 |
| `.xian-harness/` | 项目级协议、状态、profile、registry 和 pack 安装事实。 | 初始化、pack sync、状态机或 profile 资产变化时。 | Deterministic Tool / Gatekeeper | 只由确定性工具或明确授权的 Agent 更新。 |
| `.xian-harness/changes/` | change 级事实源、证据、门禁、Workbench、归档和 Agent/Harness 运行资产。 | 每个 change 推进时持续写入；运行资产随 Harness 规则变化更新。 | Builder / Verifier / Gatekeeper / Workbench Operator / Doc Steward | 不用聊天总结替代本目录下的事实文件；Agent 运行协议不放入业务项目文档根目录。 |
| `docs/项目基线.md` | 项目识别、技术栈、启动、测试和接管风险基线。 | 接管、重构、新建项目初始化，或项目基础架构变化时。 | Intake Agent / Doc Steward | 静态识别不足时必须标记 unknown，不捏造运行事实。 |
| `docs/项目开发纪律.md` | 本文件，定义目录职责、维护边界和事实源优先级。 | 目录结构、维护责任或治理规则变化时。 | Human Owner / Doc Steward | 变更后需要同步 `AGENTS.md` / `CLAUDE.md` 的入口导航。 |
| `docs/项目状态.md` | 当前项目阶段、active change、风险和下一步。 | 重要 change 完成、暂停、归档或外部状态变化时。 | Workbench Operator / Doc Steward | 状态结论必须能追溯到本地事实源。 |
| `docs/需求文档.md` | 产品需求、业务规则、验收口径和关联 change。 | 新需求进入、需求调整或验收口径变化时。 | Product Steward / Intake Agent | 不把技术实现决策伪装成业务需求。 |
| `docs/待办清单.md` | 轻量后续项。 | 非阻断事项出现、转入正式 change 或完成时。 | Doc Steward | 影响交付、质量或协作的事项必须升级为 change。 |
| `templates/` | 可复用模板资产。 | 模板协议、样例或 profile 输出规则变化时。 | Pack Maintainer | 模板变更要经过 template registry 和 gate 检查。 |

## 维护规则

- 目录职责变化必须先更新本文件，再同步入口规则和相关模板。
- 任何 Agent 改动 `.xian-harness/` 或 `templates/` 前，必须说明对应 change 和事实源。
- 项目运行、测试、部署事实必须来自命令输出、日志、配置或本地文件，不能来自猜测。
- Python-only、TypeScript-only、deployment-only 等垂直规则只能进入对应 profile 或目标项目文档，不能污染 base profile。
- `.xian-harness/changes/{change-id}/acceptance-criteria.md` 是单个 change 的验收契约；本文件是项目级长期纪律。

## 事实源优先级

当聊天记录、看板、文档和本地证据冲突时，按以下顺序判断：

1. 可复现命令输出、测试日志、Git 状态、运行日志。
2. `.xian-harness/changes/{change-id}/` 下的 change-local 事实源。
3. `.xian-harness/` 下的项目级协议和状态文件。
4. `docs/项目基线.md`、`docs/项目状态.md`、`docs/需求文档.md` 等项目级文档。
5. `AGENTS.md`、`CLAUDE.md`、skills、commands、hooks 中的入口规则。
6. 聊天上下文和口头说明。

## 状态权威性

### Canonical State

| 状态 | 权威范围 | 更新路径 |
|---|---|---|
| `.xian-harness/state.yaml` | 项目初始化、active change、change 索引、pack install/sync 摘要。 | `xian-harness init`、`pack install`、`pack sync`、change lifecycle 命令。 |
| `.xian-harness/changes/{change-id}/.change-state.json` | 单个 change 的 phase、status、tier、nextAction 和执行暂停状态。 | `xian-harness change`、`guard`、`verify`、`check`、`workbench`、`archive`。 |
| `.xian-harness/pack-state.json` | Pack 受管文件、source hash、target hash、install/sync 时间。 | `xian-harness pack install`、`xian-harness pack sync`。 |
| `.xian-harness/skill-registry.json` / `.xian-harness/harness-pack-manifest.yaml` | profile、skill registry、template registry 和 pack 分组声明。 | Pack 安装或同步。 |
| `.xian-harness/interaction-policy.json` | hook 交互模式、预算、禁读范围和输出预算。 | Pack 安装、同步或明确的 hook governance change。 |
| `verify/verify-result.json`、`gate/gate-result.json`、`archive/archive-result.json` | 对应阶段的机器可读结论。 | `xian-harness verify`、`xian-harness check`、`xian-harness archive`。 |

### Derived / Degraded Views

| 视图 | 用途 | 降权规则 |
|---|---|---|
| `.xian-harness/workbench/**` | 给人和下一棒 Agent 阅读的一屏状态、handoff、HTML 展示。 | display / handoff only，不能覆盖 canonical `nextAction`。 |
| `.xian-harness/workbench/project/*` | project status、doc sync、project gate、next decision 的聚合视图。 | 只能解释项目状态；冲突时回到 `.xian-harness/state.yaml` 和 deterministic CLI。 |
| `.change-transition.log` / `trace.jsonl` | 审计轨迹和事件回放。 | audit only，不能作为下一步事实源。 |
| `*.md` 报告和 CLI brief 文本 | 人类可读渲染。 | rendering only；对应 JSON / state 文件优先。 |

规则：

- derived view 不能覆盖 canonical state。
- 如果 Workbench、Markdown 报告、CLI brief 与 `nextAction` 冲突，先运行 `xian-harness continue --target <target-project> --json` 仲裁。
- 不手改 derived view 来“修正”事实；先更新 canonical state 或重新生成对应视图。
- 缺少 fresh canonical state 时，输出必须声明不确定性，不用 derived view 伪造确定感。

## 变更检查

每次修改本文件或目录治理规则后，至少执行：

```bash
xian-harness docs inspect --target <target-project> --json
xian-harness continue --target <target-project> --json
```

如果目标项目尚未初始化 Harness，先执行 pack install 和 baseline create。
