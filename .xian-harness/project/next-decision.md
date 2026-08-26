# Project Next Decision

- Status: empty
- Active change: none
- Selected change: none
- Recommended action: delivery-close
- Recommended role: orchestrator
- Governance route: none
- Reason: Workspace has dirty or untracked files; inspect ownership before opening a new demand.
- Reason code: dirty-workspace-close
- Confidence: medium
- Next action: Attribute dirty worktree changes and close local delivery before opening a new demand.
- Direction source: project-recommendation
- Current situation: Project is initialized and has no tracked changes.
- Recommended target: project-level next work
- Minimum next step: Attribute dirty worktree changes and close local delivery before opening a new demand.
- Next skill: xian-commit

## Process Debt

- [soft-debt] Workspace has 4 dirty and 3 untracked file(s)
- [background] Rendered document freshness drift is advisory; review doc-sync only when planning docs work.

## Recommended Skills

- $xian-commit (codex-skill)

## Recommended Commands

- git status --short (shell-command; executable=true; available=true)

## Closeout Readiness

- Status: blocked
- Next state: attribute-worktree-before-closeout
- Reason: Workspace has dirty or untracked files, so closeout must first attribute local delivery changes.
- Commit suggested: false
- Commit message: none
- Tag suggested: false
- Release suggested: false

## Evidence

- .xian-harness/project/project-status.json
- .xian-harness/project/doc-sync-report.json
- .xian-harness/project/project-status.json

## Next Commands

- git status --short

## Fallback Commands

- git status --short --branch
- git diff --stat

## Commands

- git status --short

## Project Documents

| Document | Role | Status | Title |
|---|---|---|---|
| docs/README.md | Project Documentation Index | present | 先闻继学文档中心 |
| docs/项目说明.md | Project Brief | present | 项目说明 |
| docs/项目基线.md | Project Baseline | present | 项目基线 |
| docs/项目开发纪律.md | Project Discipline | present | 项目开发纪律 |
| docs/项目情况.md | Project Situation | present | 项目情况 |
| docs/项目状态.md | Project Status | present | Project Status |
| docs/需求文档.md | Requirement | present | 需求文档 |
| docs/待办清单.md | Todo List | present | 待办清单 |

## Workspace Continuity

| Fact | Value |
|---|---|
| Source control | git |
| Git present | yes |
| Branch | master |
| Upstream | origin/master |
| Ahead / behind | 1 /  |
| Git root | . |
| Pathspec | . |
| Modified or staged files | 4 |
| Untracked files | 3 |
| Risk level | dirty |
| Commit staging | path-scoped |
| Push policy | explicit-only |
| Rule source | AGENTS.md and active profile |

Git workspace has 4 modified/staged and 3 untracked file(s) under the selected target path.

## Project Situation

| Fact | Value |
|---|---|
| Baseline | present |
| Baseline risk count | 1 |
| TODO count | 534 |
| FIXME count | 66 |
| Scanned files | 5000 |
| Risk level | attention |

Project baseline has 1 risk item(s), and code scan found 600 TODO/FIXME signal(s).

### Baseline Risks

| Severity | Risk | Evidence | Mitigation |
|---|---|---|---|
| P2 | Rendered document may drift from canonical facts | redefine-project-status-md-as-render-output | Run docs status and docs render --fix during archive. |

### Code Signals

| Type | Path | Line | Text |
|---|---|---|---|
| TODO | .venv/lib/python3.12/site-packages/Cryptodome/SelfTest/Hash/test_keccak.py:141 | 141 | add ExtremelyLong tests |
| TODO | .venv/lib/python3.12/site-packages/Cryptodome/SelfTest/PublicKey/test_RSA.py:45 | 45 | PyCryptodome treats the message as starting *after* the leading "00" |
| TODO | .venv/lib/python3.12/site-packages/Cryptodome/SelfTest/PublicKey/test_RSA.py:46 | 46 | That behaviour should probably be changed in the future. |
| TODO | .venv/lib/python3.12/site-packages/Cryptodome/Util/number.py:360 | 360 | maybe we shouldn't abort but rather start over. |
| TODO | .venv/lib/python3.12/site-packages/_pytest/assertion/rewrite.py:858 | 858 | This assert should not be needed. |
| TODO | .venv/lib/python3.12/site-packages/_pytest/cacheprovider.py:580 | 580 | evaluate generating upward relative paths |
| TODO | .venv/lib/python3.12/site-packages/_pytest/capture.py:708 | 708 | This type error is real, need to fix. |
| TODO | .venv/lib/python3.12/site-packages/_pytest/compat.py:127 | 127 | (RonnyPfannschmidt): This function should be refactored when we |
| TODO | .venv/lib/python3.12/site-packages/_pytest/config/argparsing.py:404 | 404 | (py313): Replace with `exit_on_error=False`. Note that while it |
| TODO | .venv/lib/python3.12/site-packages/_pytest/doctest.py:316 | 316 | Type ignored -- breaks Liskov Substitution. |

## Change Decisions

| Change | Status | Phase | Action | Role | Blocked Reason |
|---|---|---|---|---|---|
| none | empty | none | create-change | orchestrator | |

## Archived Context

Returned 0/0 archived/closed change(s) because `--include-archived` is enabled.
