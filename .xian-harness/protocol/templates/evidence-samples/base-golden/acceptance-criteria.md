# Acceptance Criteria: base-golden-sample

Template Contract: xian-harness/evidence-samples/base-golden/acceptance-criteria

## Template Quality Contract

| Item | Value |
|---|---|
| Fact Sources | Sample proposal, tasks, verify result, gate result, Workbench snapshot, archive summary, experience disposition. |
| Owner Role | Verifier Agent / Gatekeeper Agent. |
| Verification Commands | `bash script/smoke/base-profile-smoke.sh`; `xian-harness check base-golden-sample --target . --json`. |
| Evidence Paths | `verify-result.json`, `gate-result.json`, `workbench-snapshot.json`, `archive-summary.md`. |

This is a sample acceptance contract. Do not copy it as real completion proof.

## Change Goal

Demonstrate how a base profile change links business acceptance, technical acceptance, verification evidence, quality gate evidence, Workbench status, archive summary, and experience review.

## Business Acceptance

- [x] **AC-001** Base profile user can inspect the generated welcome behavior through a deterministic smoke command.

## Technical Acceptance

- [x] **AC-002** Harness Pack is installed with base profile assets and no profile-specific contamination.
- [x] **AC-003** Verification, gate, Workbench, archive, and experience review evidence are linked from the change workspace.

## Documentation Contract

| 文档事实源 | 责任 | 本次是否更新 | 原因 |
|---|---|---:|---|
| `docs/项目基线.md` | 接管、重构、新建入口基线 | no | Sample evidence only. |
| `docs/项目状态.md` | 项目当前状态、活动 change、下一步 | yes | Sample package documents the evidence closure shape. |
| `docs/需求文档.md` | 产品需求、业务边界、验收口径 | no | No product requirement change in sample. |
| `docs/待办清单.md` | 轻量后续项、非阻塞任务 | no | No follow-up item in sample. |
| `.xian-harness/changes/base-golden-sample/summary.md` | 本 change 收口摘要 | yes | Archive sample explains closure. |

## 关联事实源

| 类型 | 文件 | 用途 |
|---|---|---|
| Proposal | `.xian-harness/changes/base-golden-sample/proposal.md` | Defines the sample change goal. |
| Tasks | `.xian-harness/changes/base-golden-sample/tasks.md` | Shows implementation checklist. |
| Verify Result | `verify-result.json` | Shows passed verification evidence. |
| Gate Result | `gate-result.json` | Shows gate decision. |
| Workbench Snapshot | `workbench-snapshot.json` | Shows handoff state. |
| Archive Summary | `archive-summary.md` | Shows closure. |
| Experience Disposition | `experience-disposition.json` | Shows experience review closure. |

## 验证规则引用

| 规则 ID | 来源 | 负责 Skill | 执行载体 | 覆盖验收项 |
|---|---|---|---|---|
| `base.profile.smoke` | Verification Registry | `xian-verify` | `bash script/smoke/base-profile-smoke.sh` | AC-001, AC-002 |
| `gate.acceptance.coverage` | Quality Gate | `xian-gate` | `xian-harness check base-golden-sample` | AC-001, AC-002, AC-003 |

## 验收覆盖矩阵

| 验收项 | 事实源 | 验证规则 / 命令 | 验证证据 | 门禁 / 发布证据 |
|---|---|---|---|---|
| AC-001 | `src/golden.ts` | `bash script/smoke/base-profile-smoke.sh` | `verify/evidence/logs/run-001.log` | `gate/gate-result.json` |
| AC-002 | `.xian-harness/pack-state.json` | `xian-harness pack status --profile base` | `verify/evidence/evidence-manifest.json` | `gate/gate-result.json` |
| AC-003 | `.xian-harness/changes/base-golden-sample/` | `xian-harness workbench snapshot base-golden-sample` | `workbench/snapshot.json` | `archive/archive-result.json` |

## Verification Commands

- [x] **VC-001** `bash script/smoke/base-profile-smoke.sh`
- [x] **VC-002** `xian-harness check base-golden-sample --target . --json`
- [x] **VC-003** `xian-harness workbench snapshot base-golden-sample --target . --json`

## Cross-Agent Recovery

Read this file first, then inspect `verify-result.json`, `gate-result.json`, `workbench-snapshot.json`, `archive-summary.md`, and `experience-disposition.json`.
