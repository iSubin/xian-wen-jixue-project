---
name: xian-next
description: Use when the user explicitly invokes $xian-next, or gives a bare “继续 / 下一步 / go” direction request without a concrete new change.
---

# xian-next

## 用途

为现有 Xian next-action 入口提供 Codex 侧显式方向入口。

`xian-next` 不拥有独立状态源；它解释 `xian-harness continue` 的 canonical direction，并按 `direction.nextSkill` 路由到 `xian-project-startup`、`xian-open` 或其他下一步 skill。

产品角色：当用户不确定如何继续时，把项目事实翻译成清晰的下一步方向，而不是只报出下一个 skill 名称。

裸“继续”融合规则：优先继续执行当前已经存在但没有完成的任务；如果当前没有可继续执行的任务，则进入方向建议，回答“接下来应该做什么”。这两个语义必须在用户可见输出中明确区分，避免把建议误解释成执行授权。

## 迁移说明

`xian-harness continue` 现在返回五要素 `direction` 结构。`nextAction` 是方向事实源；命令和 skill 名称只是派生指引，不能覆盖它。

## 触发条件

当用户显式调用 `$xian-next`、点名 `xian-next`，或只给出“继续 / 下一步 / go / 推进当前项目”这类没有具体新需求的方向请求时使用。

有具体新需求、bugfix、refactor、文档更新或运维动作时，交给 `xian-open` 打开或恢复 governed change。

## 协议输入

- `.xian-harness/state.yaml`
- `.xian-harness/changes/{change-id}/`
- `.xian-harness/project/next-decision.json`
- `.xian-harness/project/doc-sync-report.json`
- `docs/项目状态.md`

## 执行流程

1. 运行或解释 `xian-harness continue --target <target-project> --json`。
2. 当 direction 指向 `xian-project-startup` 时，不要再转入 `xian-open`；先完成 project startup / baseline。
3. 当 direction 指向 `xian-open` 时，要求 `xian-open` 判断下一条 route：继续 change、创建新 change、处理 dirty state、修复 docs-sync drift，或请求人工决策。
4. 把结果翻译成 current situation、process debt、recommended target、reason、minimum next step 和 next skill。
5. 根据 reasonCode / confidence 标注“当前是执行态”或“当前是方向建议态”。
6. 不从 `xian-next` 直接实现、验证、gate 或 archive。

## 独立判断边界

`xian-next` 不只是 `xian-harness continue` 的传声筒。在 CLI 输出基础上，必须做以下二级判断：

1. **reasonCode 验证**：基于 continue CLI 提供的 `reasonCode` 枚举（`failed-gate` / `active-change-continue` / `release-pending-archive` / `baseline-create` / `dirty-workspace-close` / `inspect-parked-changes` / `inspect-orphan-changes` / `pending-push-close` / `high-priority-todo` / `docs-sync-drift` / `project-idle-next`）判断推荐类别，不要混淆"必须做"和"建议做"。
2. **confidence 验证**：基于 `confidence`（`high` / `medium` / `low`）调整 handoff 语气：
   - `high`：允许 executable handoff（"直接回复'继续'即可进入该步骤"）。
   - `medium`：要求用户明确动作或选择，不提示 bare `继续`。
   - `low`：只报告，不催促行动；如果同时是 `project-idle-next`，必须进入方向建议态。
3. **selectedChangeId 相关性验证**：如果 `selectedChangeId` 非 null，核对它与当前 dirty worktree 的 path overlap（基于 `git status` 输出和 change 的 changed-path）；若 zero overlap 且 `confidence` 不是 `high`，降级为 inspect 而非 executable handoff，并在输出说明"CLI 推荐与当前工作上下文弱相关"。
4. **冲突仲裁**：如果二级判断与 CLI 输出冲突，显式说明冲突，并建议用户明确目标；不要无条件转发 CLI 推荐也不要默默替换。

## 执行态与方向建议态

`xian-next` 对裸“继续”必须先判定用户正在进入哪种状态：

| 状态 | 判定 | 输出要求 | 是否可提示“直接回复继续” |
|---|---|---|---|
| 执行态 | 存在 active change、failed gate、release pending archive、dirty workspace、pending push、baseline create、high-priority todo 或其他 high-confidence 可执行下一步 | 开头写“当前是执行态：已有可继续推进的任务。”并说明将继续推进什么 | 仅当 `confidence=high` 且下一步不需要额外人工选择时可以 |
| 方向建议态 | 项目 clean / idle、`reasonCode=project-idle-next`、`confidence=low`，或没有明确可执行任务 | 开头写“当前是方向建议态：没有可继续执行的任务。以下是下一步建议，不会自动执行。” | 不可以 |

方向建议态可以给出推荐方向和候选 change id，但必须写清：

- “以下是下一步建议，不会自动执行。”
- “要执行它，请明确回复：‘开这个 change’、‘执行这个方向’或给出具体需求。”
- 不要输出 `直接回复“继续”即可进入该步骤。`

## 常见分支

- 明确 `$xian-next`：使用本 skill，输出方向和下一步建议。
- 普通“继续/下一步/推进当前项目/go”等重新判断请求：留在 `xian-next`，解释 `xian-harness continue` 的 canonical direction；有可执行任务时输出执行态，没有可执行任务时输出方向建议态；如果项目基线缺失，`continue` 应给出 `xian-project-startup`。
- 有具体新需求：交给 `xian-open` 判断下一条 route，不在 `xian-next` 内创建 change。
- `direction.nextSkill` 存在：优先使用该字段。
- `nextAction` 与静态预期冲突：说明冲突，并重新运行 `xian-harness continue --json` 仲裁。

## 确定性工具

- `xian-harness continue --target <target-project> --json`
- `git status --short --branch`

## 必需证据

- `xian-harness continue` result path 或摘要输出。
- 当前 selected route 和 reason。
- `xian-open` 暴露的 process debt，如果存在。

## 参考样例

- `harden-xian-next-user-facing-guidance`: `$xian-next` brief / JSON 分离和方向感增强参考。
- 暂无更多样例；当后续出现 direction routing 或 project next-decision 类变更时补齐。

## 自检清单

- 是否把 `nextAction` 当作方向事实源？
- 是否没有把 `xian-next` 当成状态源？
- 是否没有绕过 `xian-project-startup` / `xian-open` 创建 change？
- 是否给出 current situation、process debt、minimum next step 和 next skill？
- 是否没有直接执行 build / verify / gate / archive？
- 是否基于 `reasonCode` 枚举判断推荐类别？
- 是否基于 `confidence`（high / medium / low）调整 handoff 语气？
- 是否明确标注“当前是执行态”或“当前是方向建议态”？
- 方向建议态是否明确写了“以下是下一步建议，不会自动执行”？
- 方向建议态是否没有输出 `直接回复“继续”即可进入该步骤。`？
- 是否核对 `selectedChangeId` 与当前 dirty worktree 的 path overlap？
- 当 CLI 推荐与上下文冲突时，是否显式说明而非无条件转发？

## 输出

- 推荐的 next skill。
- 一条简洁 next action。
- `reasonCode`（来自 continue CLI，非自创）。
- `confidence`（来自 continue CLI，非自创）。
- 存在 process debt 时，给出显式选择。
- 面向用户的 current situation。
- recommended target 和 reason。
- 用户不确定时的 minimum safe next step。
- 执行态 / 方向建议态标签，以及对应的授权边界提示。

## 交互预算

- 必须：读取文件或运行命令前遵守当前 hook 提供的 Interaction Budget。
- 必须：chat-mode 请求保持 tool-free，除非用户明确要求 inspection、snapshot refresh、deep audit 或 change execution。
- 必须：读取 pack state、workbench、quality-gate、archive 或其他大型项目状态前，确认用户有明确 deep-audit 或 change intent。

## 交接规则

- 从运行时 `nextAction` 开始，并读取 `direction.nextSkill`；先输出 current situation、process debt、recommended target、minimum next step 和 confidence；再判断执行态 / 方向建议态。执行态且 `confidence=high` 时，末尾可以输出 `下一步建议：<中文下一步>`，空一行后单独输出 `$xian-xxx`，再空一行输出 `直接回复“继续”即可进入该步骤。`。方向建议态、`confidence=low` 或需要用户明确选择时，不要输出 `直接回复“继续”即可进入该步骤。`，改为提示“要执行它，请明确回复‘开这个 change’或‘执行这个方向’”。不要在首屏附加“因为...”。
- 表达层原则：中文优先，默认用自然中文给结论、必要风险和下一步；必须保留英文术语、协议字段、状态名或命令名时，紧跟中文括注解释；不写“流程报告 / Review 报告 / evidence 清单”式长篇；只有 deep-audit、gate、verify 或用户明确要求完整显性化时才展开治理细节。
- 优先使用 `direction.nextSkill`；如果缺失，再从 `nextAction` 推导 skill。
- 如果静态预期与运行时 `nextAction` 冲突，说明冲突，并 run `$xian-next` or `xian-harness continue --json` for arbitration。
- 不要添加绕过 `nextAction` 的第二套 handoff narrative。
- 不要把具体新需求误判成裸“继续”；具体需求由 `xian-open` 处理。
- 发现误开 change、错误 `activeChange` 或纠偏场景时，停止并交回 deterministic lifecycle 命令处理；change 生命周期由框架状态机和命令行工具驱动，不要推荐创建新 change 来关闭旧 change。

## 约束与原因

- 不要复制 `xian-open` 或 `xian-project-startup` 的 workflow。原因：`xian-next` 是方向入口，重复 workflow 会造成多个事实入口。
- 不要在没有 `direction.nextSkill` route confirmation 时创建新 change。原因：继续请求需要先判断项目基线、现有状态和流程债务。
- 不要用新 change 管理误开的 change。原因：方向入口不能把 Agent 自己造成的流程错误升级成新的业务事实；change-over-change 会破坏 activeChange、nextAction 和证据链；关闭或撤销已有 change 应由 Harness lifecycle CLI 或未提交状态撤销完成。
- 不要把 `xian-next` 当作状态源；状态源是 `xian-harness continue`。原因：别名 skill 不能覆盖 canonical project/change facts。
- 不要为了让流程看起来完整而补造 verify、gate、release 或 archive evidence。原因：守诚实要求显性化的证据必须真实。
- 高频方向检查默认只读解释；只有用户要求 refresh 或 persist 时才保留生成的 Workbench 变更。原因：避免方向入口制造不必要状态噪声。
