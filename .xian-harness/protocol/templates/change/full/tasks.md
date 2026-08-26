<!-- xian-harness:generated-view-seed.v1
view: tasks.md
authority: legacy-markdown
rendererId: template-registry.change.full
contractRevision: none
editPolicy: contract-ready; after contract authority is enabled, submit a contract patch instead of hand-editing this generated view.
-->

# Tasks: {change-id}

Template Contract: xian-harness/change/full/tasks

## Template Quality Contract

| 项 | 内容 |
|---|---|
| Fact Sources | proposal、design、acceptance criteria、verification commands、gate issues。 |
| Owner Role | Planner Agent / Builder Agent。 |
| Verification Commands | `xian-harness check {change-id} --target <target-project> --json`。 |
| Evidence Paths | `.xian-harness/changes/{change-id}/tasks.md`。 |

## 1. Intake / Spec

- [ ] 1.1 明确需求背景、业务规则、影响范围和非目标。
- [ ] 1.2 明确 `acceptance-criteria.md` 的 AC、事实源、验证规则和证据路径。

## 2. Design

- [ ] 2.1 完成技术方案。
- [ ] 2.2 明确数据模型、接口、权限、UI、文档和验证策略。

## Dependencies

| 任务 | 依赖 | 阻塞条件 | 回退条件 |
|---|---|---|---|
| 3.1 | 1.2, 2.1 | {blocker} | {rollback} |

## 3. Build

- [ ] 3.1 实现代码或资产变更。
- [ ] 3.2 同步必要文档事实源。
- [ ] 3.3 更新模板、registry、manifest 或 profile 边界时补对应测试。

## Verification Mapping

| 任务 | 覆盖验收项 | 验证规则 / 命令 | 证据路径 |
|---|---|---|---|
| 3.1 | AC-001 | {verification-command} | {evidence-path} |

## TDD / Evidence Notes

- 测试或等价验证先行证据：{test-or-equivalent-evidence}
- TDD Exception：{reason-or-none}
- 替代验证：{replacement-verification}

## 4. Verify

- [ ] 4.1 运行静态检查、单元测试或 smoke。
- [ ] 4.2 写入 verify evidence 和 verify report。

## 5. Gate / Archive

- [ ] 5.1 运行 quality gate 并处理 open issues。
- [ ] 5.2 归档 change，沉淀可复用经验候选。
