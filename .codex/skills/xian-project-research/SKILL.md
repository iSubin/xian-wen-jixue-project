---
name: xian-project-research
description: Use when researching, comparing, or absorbing external projects and reference engineering work into the harness.
---

# xian-project-research

## 用途

治理 project 级外部知识输入，把开源项目、参考工程、技术方案、竞品实践或既有 `docs/archetype-research/` 资料转化为可审计的研究结论。

`docs/archetype-research/` 的产出治理归 `xian-project-research`；晋升、候选审查和 promote 归 `xian-experience`。

## 触发条件

当用户要求调研、比较、吸收、复盘外部项目或参考工程，或明确指定 `docs/archetype-research/explore-<target>/` 作为研究目标时使用。

普通“继续”、“下一步”或 “go” 不要触发本 skill；这些词先交给 `xian-next` / `xian-open` 仲裁。

## 方法论来源

- Provider: Xian internal engineering discipline
- Role: engineering-discipline-provider
- Absorption Mode: research discipline absorbed into `xian-project-research`; do not create parallel research facts.

## 吸收的纪律

- Directory-driven research: 先按目录、入口和资产类型定位研究范围，再深入关键文件。
- Evidence-first judgment: 区分文件事实、源码事实、测试事实、本地运行事实和跨项目归纳。
- Adoption discipline: 每个结论必须说明是否吸收、吸收到哪里、需要什么验证。

## 执行前必须确认

- 必须：确认 research target、目标目录和 source material，不使用未验证的固定路径。
- 必须：说明研究问题，而不是只说“继续看这个目录”。
- 必须：区分外部事实、推断结论和 Xian 侧可吸收资产。
- 必须：确认本轮不会复制外部业务代码、专有 schema 或商业样例。

## 协议输入

- `docs/archetype-research/`
- `docs/archetype-research/explore-<target>/`
- `references/<target>/`
- `.xian-harness/changes/{change-id}` when research is attached to an active change
- Target project README, source, config, tests, scripts, skills, hooks, commands, agents, docs, templates, or profile assets.

## 执行流程

1. 确认研究问题、target 名称和研究目录，必要时创建 `docs/archetype-research/explore-<target>/`。
2. 先做目录级扫描，记录入口文件、资产分组、镜像关系和明显边界，不全量读取无关文件。
3. 对关键模块追踪机制链：入口、配置、状态事实源、skill / hook / command / runtime 路径、产物和验证方式。
4. 为每个研究切片标注证据等级、对比基线、优势、成本、失败边界和可迁移性。
5. 输出吸收建议：`absorb-now`、`absorb-later`、`document-only`、`reject` 或 `needs-verification`。
6. 更新目标 research 文档、目标 README 和 `docs/archetype-research/README.md` 中的导航。
7. 当研究结论形成可复用经验时，只写 candidate hint 或 adoption recommendation；交给 `xian-experience` 审查晋升。
8. 如果研究直接驱动产品改动，要求后续进入 `xian-spec` / `xian-design` 创建 governed change。

## 常见分支

- 新目标调研：创建 `explore-<target>/README.md`，先沉淀目录地图和研究问题。
- 既有目标续作：读取目标 README 和最近更新的切片，继续同一目录树，不另开散落文档。
- 参考项目机制吸收：先写 research 结论，再由 `xian-design` 或 `xian-experience` 决定是否进入产品资产。
- 证据不足：标注 `needs-verification`，不要把 L1 README claims 写成确定结论。

## 研究标准

每个深度切片至少回答：

- 研究问题：这个切片要支持什么产品判断？
- 机制链：从入口到产物的工作路径是什么？
- 证据等级：L1 文件名 / README、L2 源码配置、L3 测试或已提交产物、L4 本地运行、L5 跨项目重复。
- 对比优势：相比 Xian 当前实践或普通项目实践，强在哪里，代价是什么？
- 迁移分类：Principle、Protocol、Tooling、Asset、Case-specific 或 Restricted。
- 失败边界：缺文件、过期产物、隐藏上下文、profile 污染、secret / license / commercial boundary、不可验证点。
- 吸收建议：吸收什么、为什么、落到哪里、需要什么验证、哪些不是目标。

## 确定性工具

- `git status --short --branch`
- `git diff --check -- docs/archetype-research`
- `rg --files docs/archetype-research references`
- `rg -n "<keyword>" docs/archetype-research references`
- `find docs/archetype-research -maxdepth 3 -type f -name '*.md'`
- Local Markdown link check for the active `docs/archetype-research/explore-<target>/` tree.

## 必需证据

- Research target and exact source paths inspected.
- Research question and mechanism chain for each deep slice.
- Evidence level and whether conclusions are facts or inference.
- Comparative advantage and cost against a named baseline.
- Transferability classification and adoption recommendation.
- Failure / boundary analysis.
- Link-check or diff-check result when writing research docs.

## 事实映射

- Research output -> `docs/archetype-research/explore-<target>/`
- Research index -> `docs/archetype-research/README.md`
- Adoption recommendation -> target research slice or absorption index
- Experience promotion input -> `xian-experience` as `research-only`
- Product change follow-up -> `.xian-harness/changes/{change-id}`

## 参考样例


## 自检清单

- 是否明确了 target 和研究问题？
- 是否说明了证据等级，而不是把推断写成事实？
- 是否给出迁移分类和吸收建议？
- 是否没有替代 `xian-experience` 做经验晋升？
- 是否没有把外部项目规则直接当成 Xian base 规则？

## 输出

- Research slice markdown under `docs/archetype-research/explore-<target>/`.
- Updated target README or top-level research index when navigation changes.
- Adoption recommendation and candidate hint when research should feed experience governance.
- Next governed skill recommendation.

## 交互预算

- 必须：读取文件或运行命令前遵守当前 hook 提供的 Interaction Budget。
- 必须：优先读取目录索引、README、配置和关键入口；不要把整仓库全量读取当作调研。
- 必须：chat-mode 下只给方向和边界；只有用户明确进入调研执行时才写 research docs。

## 交接规则

- 输出时先说明当前结论、证据缺口和风险；末尾输出 `下一步建议：<中文下一步>`，空一行后单独输出 `$xian-xxx`，再空一行输出 `直接回复“继续”即可进入该步骤。`；不要在首屏附加“因为...”。

- 研究发现可复用经验 -> `xian-experience`。
- 研究发现产品能力缺口 -> `xian-spec`。
- 研究需要方案取舍或 batch change -> `xian-design`。
- 项目骨架、基线或目录约束缺失 -> `xian-project-startup`。
- 普通“继续”不进入 research；run `$xian-next` or `xian-harness continue --json` for arbitration.

## 约束与原因

- 不要把外部参考项目规则直接写入 base profile。原因：未经迁移分类和验证的规则会污染通用 Harness 边界。
- 不要复制外部业务代码、专有 schema、商业样例或 secret。原因：research 只吸收可独立表达的方法、协议和治理思路。
- 不要把 `docs/archetype-research/` 的研究结论直接当成 canonical project state。原因：研究资料是输入，产品事实必须进入协议、skill、template、docs 或 change 证据。
- 不要替代 `xian-experience` 做 promotion。原因：research 负责形成知识输入，晋升需要候选质量、风险和目标资产审查。
- 不要让普通“继续”触发 research。原因：继续语义属于项目恢复和 change 路由，误触发会打断当前工作流。
