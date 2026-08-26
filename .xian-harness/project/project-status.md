# Project Status

- Generated at: 2026-08-26T21:21:02+08:00
- Risk level: attention
- Active change: none
- Change count: 0

## 当前结论

项目当前处于：idle

项目没有 active change、blocking failure 或高优先级待办；可以通过 continue 或 backlog 选择下一项工作。

## 推荐下一步

| Field | Value |
|---|---|
| Recommended action | project-idle-next |
| Recommended role | orchestrator |
| Recommended skill | using-xian-harness |
| Next command | `xian-harness continue --target . --json` |
| Why | No active change, blocking risk, or actionable high-priority backlog item is visible. |

## 当前工作

| Change | Phase | Categories | Gate | Release | Archive | Next |
|---|---|---|---|---|---|---|
| none |  |  |  |  |  | `xian-harness continue --target . --json` |

## 已完成 Change 索引

| Change | Completion | Evidence | Residual Risk | Next |
|---|---|---|---|---|
| none | none | none | none | `xian-harness continue --target . --json` |

## 阻塞与风险

| Severity | Issue | Evidence | Next |
|---|---|---|---|
| none | none | none | `xian-harness continue --target . --json` |

## 项目队列

| Priority | Item | Status | Next |
|---|---|---|---|
| none | none | empty | `xian-harness todo add <id> --target . --title <title> --priority P2 --source user-request --summary <summary> --json` |

## Summary

| Metric | Count |
|---|---:|
| Active | 0 |
| Archived | 0 |
| Blocked | 0 |
| Failed | 0 |
| Accepted risk | 0 |
| Release pending | 0 |
| Missing project documents | 0 |
| High priority todos | 0 |

## Project Documents

| Document | Role | Class | Audience | Status | Source of Truth | Update | Next |
|---|---|---|---|---|---|---|---|
| docs/README.md | Project Documentation Index | active-entry | human, agent | present | docs directory, Project Document Registry | xian-harness project docs-sync --target . --fix | Follow the current-status, requirements, todo, or operating-policy links for the task at hand. |
| docs/项目说明.md | Project Brief | canonical-source | human, agent | present | manual project brief, product positioning decisions | manual | Use docs/项目状态.md for current progress and docs/需求文档.md for requirement status. |
| docs/项目基线.md | Project Baseline | generated-surface | human, agent | present | project marker inspection, .xian-harness/project-risks.json, .xian-harness/project-boundaries.json | xian-harness docs render --doc project-baseline --target . --fix | Use it to choose the correct cwd, profile, and verification entrypoint before changing code. |
| docs/项目开发纪律.md | Project Discipline | operating-policy | human, agent | present | AGENTS.md, docs/xian-harness/current-change-protocol.md, docs/xian-harness/slimming-product-contract.md | manual | Follow this document before opening or closing a governed/audit change. |
| docs/项目情况.md | Project Situation | diagnostic-surface | human, agent | present | Project Situation inspection, .xian-harness/project-risks.json, .xian-harness/capability-registry.json | xian-harness docs render --doc project-situation --target . --fix | Use this for project takeover or diagnosis, not as the daily next-step router. |
| docs/项目状态.md | Project Status | generated-surface | human, agent | present | .xian-harness/state.yaml, .xian-harness/project/project-status.json, .xian-harness/project/next-decision.json | xian-harness docs render --doc project-status --target . --fix | Follow the Recommended Next Step or run xian-harness continue --target . --json. |
| docs/需求文档.md | Requirement | canonical-source | human, agent | present | manual product requirements, linked change evidence | manual | Open or link backlog/change items for accepted requirement gaps. |
| docs/待办清单.md | Todo List | generated-surface | human, agent | present | .xian-harness/backlog/registry.json, .xian-harness/project/project-status.json, ProjectWorkQueue | xian-harness docs render --doc todo-list --target . --fix | Use xian-harness todo/backlog commands; do not edit the generated markdown directly. |

## Governance File Boundary

| Class | Purpose | Track in Git | Rebuildable | Authority |
|---|---|---|---|---|
| canonical facts | Machine-readable lifecycle, project, backlog, and projection state. | yes | no | canonical facts win over every generated surface and presentation cache. |
| tracked evidence | Verify, gate, close, release, archive, and accepted manual evidence used to prove delivery. | yes | partially | tracked evidence is appendable or immutable according to lifecycle rules. |
| generated surface | Human-readable project status, todo, baseline, situation, reports, and Markdown summaries. | yes, when project-facing | yes | regenerate from canonical facts instead of editing by hand. |
| local runtime cache | Local logs, hook metrics, temporary runtime files, scratch outputs, and project-specific runtime folders. | no, unless explicitly promoted as evidence | yes or disposable | never a canonical fact source. |
| presentation cache | Workbench, board, handoff preview, and manager history under `.xian-harness/local/reports/`. | no | yes | presentation cache is a view and must not block close/archive by itself. |

## Workspace

| Fact | Value |
|---|---|
| Source control | git |
| Branch | master |
| Ahead / behind |  /  |
| Dirty / untracked | 0 / 0 |
| Risk level | clean |
| Artifact boundary | none |

Workspace continuity is intentionally normalized in committed project-status surfaces; use xian-harness continue or project status JSON refresh for live dirty/untracked counts.

No heavy generated artifact root was detected in the current workspace status.


## Project Situation

- Baseline: present
- Baseline risks: 1
- Recommended profile: base
- Present markers: requirements.txt
- Entrypoints: requirements.txt, Dockerfile
- Top-level directories: __pycache__, .pytest_cache, .venv, .xian-commit, config, data, design-system, docs, exports, frontend, hooks, runtime, scripts, src, temp, templates, tests, tools
- Active-source TODO / FIXME: 534 / 66

## High Priority Todos

| Priority | Path | Line | Text | Next |
|---|---|---:|---|---|
| none |  |  | none | `xian-harness todo list --target . --json` |
