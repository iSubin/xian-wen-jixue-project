---
name: xian-spec
description: Use when writing governed-lite change intent and acceptance in change.md, or legacy/audit proposals and acceptance criteria.
---

# xian-spec

## 用途

把意图转成清晰的 WHAT：范围、业务规则、验收和非目标。

## 触发条件

Use this skill after open when the request needs new or updated requirement content in `change.md` before implementation. For legacy/audit changes, it may also update proposal and acceptance artifacts.

## 方法论来源

- Provider: Xian internal engineering discipline
- Role: engineering-discipline-provider
- Absorption Mode: discipline absorbed into `xian-spec`; do not invoke or write to a parallel engineering discipline fact source.

## 吸收的纪律

- `brainstorming`: clarify outcome-changing uncertainty before locking scope; reuse explicit decisions already made for the same boundary.

## 决策暂停与答复适用性

仅在重大歧义、关键假设被证伪、实质方案/成本/风险分叉，或无新信息的重复失败会改变下一步时提出 Checkpoint。已授权的同 Scope 修复、正常阶段衔接与有进展的长操作不是新决策：不新增固定阶段审批，不重复索取同一许可，保留同一在途长操作。

先区分产品取舍、技术澄清、权限请求、机器 blocker 与进度通知。机器拒绝不能由聊天批准绕过；进度通知不要求答复。确需决策时，一次给出目标、新事实、影响、推荐方案/替代项、一个明确问题、已停动作与可继续工作，以及预期暂停时间；未知时标明未知，不猜测 owner 答复时长。只暂停依赖答案的动作，无关已授权工作可继续。

有 active Change 时使用现役官方 human-decision 暂停路径并读回状态；研究或未建 Change 场景不为询问制造空 Change。答复到达后核对 target/Change、当前 contract/Candidate、待决问题、答案和原假设。重复、迟到、错误对象或上下文缺失的答复不得重放旧操作；只对不适用部分澄清。resume 建议不是 owner 答复，也不是新授权。

答复改变 Scope/AC 时必须经支持的 contract revision 与现役准入，保持 append-only 历史；不能手写 accepted/frozen 或修改旧 Attempt。先查 readiness 和合法 pause/revision/resume 顺序，不承诺任何阶段都能先 patch。若合法修订要求先 resume，待决边界解决前仍不恢复受影响构建。普通已授权继续请求直接路由，不要求第二次“继续”。

本节是 Agent 指导，不新增 CLI、schema、phase、权限或 Runtime enforcement；跨 Host 一致执行和自动暂停恢复未得到保证。

## Change Design Quality Lenses

这是一项 advisory discipline（建议性纪律），用于提高设计判断的命中率，不是新的治理事实源。

采用一个默认项和三个条件触发项：

- 确认边界：所有 change 都先判断谁依据什么确认到什么程度，以及不能推出什么。
- 不变量优先：行为、状态、数据、权限或业务规则变化时，提炼 1 至 3 条必须始终成立的可观察语义。
- 反例先行：存在重放、fallback、恢复、多状态源或不可信输入时，寻找最低成本反例。
- 独立证明：P1、权威、安全、发布或迁移结论需要一个不同 evidence source（证据来源）的观察路径。

ROI 约束：如果判断不能改变 Scope、Non-goals、Acceptance Criteria、设计约束、验证策略或 Review 重点，就不产生额外治理内容。Small 和普通 Standard change 默认只做内部判断；Protocol、Authority、Security、Audit 上下文必须在现有 Spec/Design 位置显式留下适用结论。

机器风险事实优先：当 canonical Change facts 提供 `sourceDelta.riskDelta` 时，其中所有适用的 canonical machine-risk categories 都直接触发条件式 failure modeling，包括 external side effects（含 `external.*`）、multiple authorities、asynchronous delivery、retry/idempotency、concurrency、auth/tenant boundaries、migration/deployment 与 irreversible operations。`owner-declared risk categories` 只在 canonical machine facts 缺失时补充风险事实；自然语言关键词命中本身不能成为第二套触发 authority。没有适用风险的 low-risk UI、copy、documentation 或 pure-function Change 可以完全省略 failure model 和 pilot measurement 内容。

本纪律不新增 phase、不新增 schema，也不新增固定“四问”章节、per-change attestation 或 Gate 条件。Skill contract 只能证明提示文本已安装，不能证明具体 change 实际应用或质量提升。

## 执行前必须确认

- 必须：clarify the user goal, business boundary, constraints, and non-goals before writing proposal content.
- 必须：record at least two solution options or an explicit reason why multi-option exploration is unnecessary.
- 必须：bind every acceptance item to a measurable outcome in `change.md`; legacy/audit changes may keep the binding in `acceptance-criteria.md`.

## 协议输入

- governed/lite 默认：`.xian-harness/changes/{change-id}/change.md`
- `.xian-harness/changes/{change-id}/proposal.md`
- `.xian-harness/changes/{change-id}/acceptance-criteria.md`
- `.xian-harness/changes/{change-id}/.change-state.json`
- relevant Xian spec contract proposal/delta specs when the project uses Xian spec contract
- adapter docs and vertical profile rules when scope touches a known stack
- user constraints and business language

## Xian-Native Semantic Provider Overlay

默认继续使用 native provider。只有 bounded multi-file Change 已经具备完整、repo-contained 的外部 semantic artifacts 时，才可把它们作为 optional authoring inputs 引用；trivial、read-only、operational 和没有这些 artifacts 的 Change 不增加任何负担。

每个被引用的 artifact 必须同时满足：

- 是 repo 内 regular non-symlink file；不得依赖 external semantic-provider CLI/runtime、provider cache 或第二事实存储。
- 在 accepted contract 的 `sections.sourceDelta.boundaryDelta[].item.semanticProviderArtifact` 中记录 `version: 1`、repo-relative `path` 与 `sha256:<64-lowercase-hex>`。
- 同一规范化 `path` 必须是 `sections.scope.changedPaths` 的 exact member，使现有 current Candidate Workset/source snapshot 绑定实际 bytes；late writer 由现有 seal/revalidation fail closed。

External artifacts 只组织 authoring。不得复制第二份 proposal、design、spec、task 或 acceptance authority；Harness 仍是 Scope、Candidate、Review、Verify、Gate、Result 与 publication 的 mandatory sole execution authority。

分类边界必须可观察：source identity/digest、accepted Scope、Candidate freshness、Review、Verify、Gate 或 publication rejection 是 product/runtime blocker；仅 wording、layout 或 duplicated narrative，且所有 machine facts 完整时，才是 governance presentation Quality Issue。

## 执行流程

1. Capture background, target user, business outcome, and non-goals.
2. Read canonical `sourceDelta.riskDelta` when available, then apply the confirmation boundary and trigger the other quality lenses only from applicable machine facts or explicit owner-declared risk categories.
3. Separate product requirements from implementation decisions; acceptance criteria describe observable business outcomes and must not freeze implementation order unless that order is independently confirmed as a business invariant.
4. Define acceptance criteria before implementation.
5. Note affected modules, data, permissions, deployment, rollback, and observability concerns. For an unverified external transaction, idempotency, uniqueness, delivery, or rollback assumption, require a probe, a design that removes the dependency, or an explicit residual-risk decision before Spec acceptance.
6. Update `change.md`; for legacy/audit changes, update `proposal.md`, `acceptance-criteria.md`, or Xian spec contract delta specs.

## 完整草案与适用准入

首次 seal/Review 前一起核对 requirement.nonGoals、sourceDelta、真实 Scope、授权来源、TASK/AC/VC 双向映射、唯一 IDs 和独立命令。业务 AC 写可观察结果，不冻结 shell 变量复用或实现顺序；Scope、Candidate Workset 与 mandatory preflight 保持唯一机器边界，不复制为产品 AC，也不让 verificationPlan 递归调用当前 Change guard/verify/lifecycle。

先区分实际 lifecycle/freeze 和 directCompile 对应的调用分支（现役 requiresReviewedPromotion）；仅适用 reviewed promotion 时检查其 admission。compile pass 不等于实际 admission，但未进入分支的失败也不是当前调用 blocker。prospective owner self-binding 使用当前 Runtime 所需 patch identity 和 canonical path，保留旧授权，不安装固定 patch id。

对已 materialized、非 terminal Change 的拟提交完整补丁，使用 `xian-harness change contract-patch <change-id> --file <patch.json> --preflight --target <target-project> --json`。这是成功/失败均零写（含 telemetry）的公开前置检查；读取 checks 的 source、fail 和 not-run 原因。报告不覆盖完整命令 readiness、Workset/source fence、Reviewer 或锁内最终重验，不是接受 token；正式提交仍重验当前事实。原始 inputBytesDigest 与 normalizedInputIdentity 分开，不能把补 proposedAt 后的投影视为原文件字节。不要对无关查询或身份未变化的相同输入反复预检，不要求外部导入私有 TS。未 materialized/terminal 等前提不满足时拒绝，不隐式初始化。省略 --preflight 的 contract-patch 仍是写入口。

## 确定性工具

- `xian-harness change inspect <change-id> --target <target-project> --json`
- Xian spec contract validation when Xian spec contract is the requirement source of truth.
- `rg` over adjacent docs/specs before introducing new terminology.

## 必需证据

- Proposal with explicit goals and non-goals.
- Acceptance checklist with measurable outcomes.
- Open questions or decisions that still require human input.
- Adapter-specific acceptance items when a vertical profile is active.

## 事实映射

- Requirements -> `.xian-harness/changes/{change-id}/change.md`
- Acceptance -> `.xian-harness/changes/{change-id}/change.md`
- Open decisions -> `.xian-harness/changes/{change-id}/design.md` or user handoff notes

## Contract Revision Boundary

当项目启用 Change Runtime contract revision 时，`xian-spec` 只能生成或修改 candidate contract patch。不要把 LLM、用户口述或 Agent 推测直接写成 accepted / frozen revision；accepted、frozen、superseded 状态必须由 lifecycle event 或 phase owner review 产生。

Agent Pair 启用时，首次 `spec.review` 为该 Change 建立唯一的持续 logical Reviewer。后续 contract refinement 产生新的不可变 Review attempt，但不得按 revision 或 Candidate 冷启动另一个 Reviewer；session memory 不能代替 canonical contract 与 Review identity。

## 参考样例

- `standardize-chinese-skill-contract-v2/proposal.md`: 明确吸收/不吸收边界的 spec 参考。

## 自检清单

- 是否遵守当前 Interaction Budget？
- 是否从 canonical facts 而不是聊天记忆开始？
- 是否留下了可复查的 evidence 或明确说明无需证据？
- 是否没有越过当前 skill 的职责边界？

## 输出

- Requirements document or Xian spec contract proposal.
- Acceptance criteria.
- Open questions and decisions.

## 交互预算

- 遵守当前实际提供的 Interaction Budget；没有提供时不虚构 hook 预算或额外审批。
- 普通聊天保持 tool-free，除非用户明确要求检查；已授权任务的必要定向读取不另索 deep-audit。
- 不为无关问题预读大型 pack state、workbench、quality-gate、archive 或历史材料；专用 release 的等待与失败边界不被本段覆盖。

## 交接规则

- 当前请求携带 publish intent 且不存在真实阻塞时，完成 spec 后由同一主 Agent 在同一任务中直接进入下一个 lifecycle skill，不输出等待用户回复“继续”的 handoff。
- 当前请求不携带 publish intent 时，自然收尾：说明结论、必要风险和仍待决定的具体问题，不强制固定末尾、skill 行或回复“继续”；仅真实待决问题才请求明确选择。已有 Runtime 路由时从运行时 `nextAction` 开始，不把建议变成授权。

- Ambiguous requirements remain in `xian-spec`.
- Requirements with architectural risk -> `xian-design`.
- Trivial approved tweak -> `xian-plan` or `xian-build` only when the user has already authorized the scope.

## 约束与原因

- 不要把未解决的业务决策藏进实现任务。 原因：违反该约束会破坏 xian-spec 的协议边界、证据链或 profile 隔离。
- 不要把设计选择写成需求。 原因：违反该约束会破坏 xian-spec 的协议边界、证据链或 profile 隔离。
- Keep machine anchors in English and business content in Chinese by default。 原因：违反该约束会破坏 xian-spec 的协议边界、证据链或 profile 隔离。
