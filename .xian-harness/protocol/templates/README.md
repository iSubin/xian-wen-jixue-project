# Templates

本目录保存目标项目中的 Harness 文档模板。

模板由 `harness-pack/manifest.yaml` 的 `templateRegistry` 登记。当前 change 主流程只登记 `change.full`，协议 schema 也只允许 `full`。流程轻重差异通过 change 范围、证据数量、隔离策略和可选产物处理，不通过新增 mode 处理；项目文档、hook 和 agent 角色等模板以独立模板族登记。

## Template Authority

`templateRegistry` 是权威协议模板注册表。新 change、项目文档、hook、agent 和样例证据包必须从 `templateRegistry` 下对应模板族取事实源：

- `templateRegistry.change.full`：新 change 的 Core Change Record 模板，服务 `proposal.md`、`design.md`、`tasks.md`、`acceptance-criteria.md` 和 `verify.md`。
- `templateRegistry.docs`：项目级文档模板，服务 `docs/项目基线.md`、`docs/项目开发纪律.md`、`docs/项目状态.md`、`docs/需求文档.md` 等长期项目事实。
- `templateRegistry.hooks` / `templateRegistry.agents` / `templateRegistry.evidenceSamples`：运行钩子、Agent 角色和样例证据包的模板事实源。

根目录 `templates/*.md` 中的同名或近似文件是 legacy compatibility alias（旧版兼容别名）。它们可以继续安装，服务旧入口、旧 pack 消费者或 profile 兼容，但不能作为新协议设计、gate 检查或 change 生成的权威事实源。若 root alias（根别名）与 `templateRegistry` 的结构化模板冲突，以 `templateRegistry` 为准。

已登记的 Markdown 模板必须包含 `Template Contract`、`Fact Sources`、`Owner Role`、`Verification Commands` 和 `Evidence Paths`。`xian-harness check` 会执行 Template Quality Gate；缺失任一项会产生 `template-registry.*` P1 issue。

固定流程资产由 `harness-pack/manifest.yaml` 的 `lifecycleContract` 登记。它登记 change 主阶段、状态文件、转换日志和 build / verify / gate / archive 阶段出口 guard，让 Gatekeeper 能检查固定流程是否仍有明确事实源和接线。

标准治理资产由 `harness-pack/manifest.yaml` 的 `standardRegistry` 登记。它不登记具体模板内容，而是登记 quality policy、verification registry、skill registry 和 template registry 的 `kind`、`sourcePath`、`ownerSkill`、`profile`、`gateInput` 和 `evidencePath`，让 Gatekeeper 能检查标准资产是否有明确责任、profile 边界和证据路径。

当前模板族：

- `.xian-harness/protocol/templates/change/full/`：change 工作区模板，服务 `proposal.md`、`design.md`、`tasks.md`、`acceptance-criteria.md` 和 `verify.md`。
- `.xian-harness/protocol/templates/docs/`：项目级文档与 Harness 运行资产模板，服务 `docs/项目基线.md`、`docs/项目开发纪律.md`、`docs/项目状态.md`、`docs/需求文档.md`、`docs/待办清单.md`、`.xian-harness/goal-runbook.md`、`docs/样例索引.md`、文档同步报告和技术决策记录。
- `.xian-harness/protocol/templates/hooks/`：Hook Contract 模板，服务 Codex / Claude hook 变更的生命周期、输入输出、跳过条件、profile 边界和验证命令审查。
- `.xian-harness/protocol/templates/agents/`：Agent Role Contract 模板，服务 Builder、Verifier、Reviewer、Gatekeeper、Doc Steward 和 Workbench Operator 等角色的边界、权限、触发、事实源、输出、issue 模型和状态事件映射审查。
- `.xian-harness/protocol/templates/evidence-samples/`：样例证据包，服务 Agent 学习 acceptance、verify、gate、Workbench、archive 和 experience review 的证据关系。
- 根目录 `templates/`：只留给 profile 专属项目脚手架或目标项目业务模板，不承载 base 协议模板。

模板必须同时满足：

- 人类可读。
- Agent 可恢复上下文。
- 工具可解析关键字段。
- 文档与代码同为事实文件，模板必须表达事实源、责任和同步关系。

## Documentation Contract

项目级文档包含入口基线和日常三件套：

- `docs/项目基线.md`：接管、重构、新建入口的项目识别、技术栈、启动健康、测试基线、风险清单和接管报告。
- `docs/项目开发纪律.md`：目标项目顶层目录职责、维护时机、维护角色、变更规则和事实源优先级。
- `.xian-harness/goal-runbook.md`：Codex `/goal` 与 `xian-harness continue` 配合推进长程任务的标准提示词、暂停条件和最小验收；这是 Harness / Agent 运行资产，不是业务项目文档。
- `docs/项目状态.md`：项目当前状态、active change、验证状态、门禁状态和下一步。
- `docs/需求文档.md`：产品需求、业务边界、验收口径和影响范围。
- `docs/待办清单.md`：轻量后续项；影响交付或质量的任务必须升级为正式 change。
- `docs/样例索引.md`：记录本地相似实现、测试样例、命名风格和复用决策，约束 Builder 在编辑前先读本项目样例。
- `docs/技术决策记录.md` 或 change-local decision record：记录技术选型背景、项目约束、方案对比、决策理由、影响范围和复审条件。

文档同步不是格式整理。若文档与代码、Git、测试、verify、gate 或 archive 结果冲突，优先以可复现事实为准，并把文档更新为新的事实状态。

## Acceptance Criteria

`acceptance-criteria.md` 是新 change 的唯一验收契约母版。它必须包含：

- AC 编号。
- 关联事实源。
- 验证规则引用。
- 验收覆盖矩阵。
- Verification Commands。
- 跨 Agent 推进说明。
- Documentation Contract。

## Sample Evidence Bundle

`.xian-harness/protocol/templates/evidence-samples/base-golden/` 是 base profile 黄金样例的证据结构示例。它不是某次真实运行的完成证明，不能直接复制为 change 完成证据。它的作用是让 Agent 和维护者快速理解一套合格证据包应该如何关联：

- Acceptance Criteria 说明业务和技术验收项。
- Verification Evidence 证明命令执行和日志位置。
- Quality Gate 说明门禁裁决和 quality issues。
- Workbench Snapshot 给下一棒 Agent 读取状态和路线。
- Archive 和 Experience Review 固化收口结论和可复用经验。
