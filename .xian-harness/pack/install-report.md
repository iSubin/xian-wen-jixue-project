# Harness Pack Install

Target: <target-project>
Source: <harness-pack-source>
Requested Profile: auto
Effective Profile: python
Profile Reason: auto selected python because Python project markers were detected
Generated At: 2026-08-26T20:38:57+08:00
Source Snapshot: 787bf18865005e38b32d4e435d14a2eacfda24a3657276b1e7c055ac992f7eec
Manifest: xian-harness-pack@1
Snapshot File Count: 133
Content Hash: 787bf18865005e38b32d4e435d14a2eacfda24a3657276b1e7c055ac992f7eec
Activation Skill Groups: governance, experience-governance
Excluded Skill Groups: none
Provenance Groups: governance:xian-agent-harness/generic-governance, experience-governance:xian-agent-harness/generic-experience-asset-governance
Missing Provenance Groups: none
Target Classification: python
Activation Markers: pyproject.toml, requirements.txt, setup.py, setup.cfg, tox.ini, pytest.ini

## Summary

- Total: 133
- Created: 131
- Updated: 0
- Unchanged: 1
- Conflict: 1
- Profile Excluded: 0
- Renamed Dirs: 0

## Asset Drift

- Status: needs-review
- Severity: P1
- Reasons: 1 Harness Pack file conflicts with unmanaged target content.
- Next Actions: Review local modifications before running xian-harness pack sync.
- Evidence: .codex/skills/xian-commit/SKILL.md

## Renamed Directories

| From | To | Status | Reason |
|---|---|---|---|
| - | - | - | - |

## Files

| Path | Action | Reason |
|---|---|---|
| .claude/commands/README.md | created |  |
| .claude/commands/xian-archive.md | created |  |
| .claude/commands/xian-build.md | created |  |
| .claude/commands/xian-design.md | created |  |
| .claude/commands/xian-gate.md | created |  |
| .claude/commands/xian-next.md | created |  |
| .claude/commands/xian-plan.md | created |  |
| .claude/commands/xian-review.md | created |  |
| .claude/commands/xian-spec.md | created |  |
| .claude/commands/xian-verify.md | created |  |
| .claude/commands/xian-workbench.md | created |  |
| .claude/hooks/hook-metrics.cjs | created |  |
| .claude/hooks/pre-tool-use.cjs | created |  |
| .claude/hooks/README.md | created |  |
| .claude/hooks/session-start.cjs | created |  |
| .claude/hooks/stop.cjs | created |  |
| .claude/hooks/user-prompt-submit.cjs | created |  |
| .claude/settings.json | created |  |
| .codex/config.toml | created |  |
| .codex/hooks.json | created |  |
| .codex/hooks.schema.json | created |  |
| .codex/hooks/hook-metrics.cjs | created |  |
| .codex/hooks/hook-output.cjs | created |  |
| .codex/hooks/hook-routing.cjs | created |  |
| .codex/hooks/hook-skill-selection.cjs | created |  |
| .codex/hooks/pre-tool-use.cjs | created |  |
| .codex/hooks/session-start.cjs | created |  |
| .codex/hooks/skill-forced-eval.cjs | created |  |
| .codex/hooks/stop.cjs | created |  |
| .codex/skills/README.md | created |  |
| .codex/skills/using-xian-harness/SKILL.md | created |  |
| .codex/skills/xian-agent-governance/agents/openai.yaml | created |  |
| .codex/skills/xian-agent-governance/SKILL.md | created |  |
| .codex/skills/xian-archive/agents/openai.yaml | created |  |
| .codex/skills/xian-archive/SKILL.md | created |  |
| .codex/skills/xian-asset-governance/agents/openai.yaml | created |  |
| .codex/skills/xian-asset-governance/SKILL.md | created |  |
| .codex/skills/xian-backlog/agents/openai.yaml | created |  |
| .codex/skills/xian-backlog/SKILL.md | created |  |
| .codex/skills/xian-batch/agents/openai.yaml | created |  |
| .codex/skills/xian-batch/SKILL.md | created |  |
| .codex/skills/xian-build/agents/openai.yaml | created |  |
| .codex/skills/xian-build/SKILL.md | created |  |
| .codex/skills/xian-commit/agents/openai.yaml | created |  |
| .codex/skills/xian-commit/SKILL.md | conflict | Target file already exists with different content. |
| .codex/skills/xian-cost/agents/openai.yaml | created |  |
| .codex/skills/xian-cost/SKILL.md | created |  |
| .codex/skills/xian-design/agents/openai.yaml | created |  |
| .codex/skills/xian-design/SKILL.md | created |  |
| .codex/skills/xian-diagnose/agents/openai.yaml | created |  |
| .codex/skills/xian-diagnose/SKILL.md | created |  |
| .codex/skills/xian-experience/agents/openai.yaml | created |  |
| .codex/skills/xian-experience/SKILL.md | created |  |
| .codex/skills/xian-gate/agents/openai.yaml | created |  |
| .codex/skills/xian-gate/SKILL.md | created |  |
| .codex/skills/xian-hook-governance/agents/openai.yaml | created |  |
| .codex/skills/xian-hook-governance/SKILL.md | created |  |
| .codex/skills/xian-next/agents/openai.yaml | created |  |
| .codex/skills/xian-next/SKILL.md | created |  |
| .codex/skills/xian-open/agents/openai.yaml | created |  |
| .codex/skills/xian-open/SKILL.md | created |  |
| .codex/skills/xian-pack-governance/agents/openai.yaml | created |  |
| .codex/skills/xian-pack-governance/SKILL.md | created |  |
| .codex/skills/xian-plan/agents/openai.yaml | created |  |
| .codex/skills/xian-plan/SKILL.md | created |  |
| .codex/skills/xian-project-research/agents/openai.yaml | created |  |
| .codex/skills/xian-project-research/SKILL.md | created |  |
| .codex/skills/xian-project-startup/agents/openai.yaml | created |  |
| .codex/skills/xian-project-startup/SKILL.md | created |  |
| .codex/skills/xian-project-status/agents/openai.yaml | created |  |
| .codex/skills/xian-project-status/SKILL.md | created |  |
| .codex/skills/xian-project-sync/agents/openai.yaml | created |  |
| .codex/skills/xian-project-sync/SKILL.md | created |  |
| .codex/skills/xian-release/agents/openai.yaml | created |  |
| .codex/skills/xian-release/scripts/prepare-release.mjs | created |  |
| .codex/skills/xian-release/SKILL.md | created |  |
| .codex/skills/xian-review/agents/openai.yaml | created |  |
| .codex/skills/xian-review/SKILL.md | created |  |
| .codex/skills/xian-skill-governance/agents/openai.yaml | created |  |
| .codex/skills/xian-skill-governance/SKILL.md | created |  |
| .codex/skills/xian-spec/agents/openai.yaml | created |  |
| .codex/skills/xian-spec/SKILL.md | created |  |
| .codex/skills/xian-verify/agents/openai.yaml | created |  |
| .codex/skills/xian-verify/SKILL.md | created |  |
| .codex/skills/xian-workbench/agents/openai.yaml | created |  |
| .codex/skills/xian-workbench/SKILL.md | created |  |
| .xian-harness/.gitignore | created |  |
| .xian-harness/bootstrap-context.json | created |  |
| .xian-harness/cache/.gitignore | created |  |
| .xian-harness/harness-pack-manifest.yaml | created |  |
| .xian-harness/integrations/README.md | created |  |
| .xian-harness/interaction-policy.json | created |  |
| .xian-harness/local/.gitignore | unchanged |  |
| .xian-harness/protocol/templates/acceptance-criteria.md | created |  |
| .xian-harness/protocol/templates/agents/agent-role-contract.md | created |  |
| .xian-harness/protocol/templates/change/full/acceptance-criteria.md | created |  |
| .xian-harness/protocol/templates/change/full/design.md | created |  |
| .xian-harness/protocol/templates/change/full/proposal.md | created |  |
| .xian-harness/protocol/templates/change/full/tasks.md | created |  |
| .xian-harness/protocol/templates/change/full/verify.md | created |  |
| .xian-harness/protocol/templates/delivery-note.md | created |  |
| .xian-harness/protocol/templates/docs/decision-record.md | created |  |
| .xian-harness/protocol/templates/docs/doc-sync-report.md | created |  |
| .xian-harness/protocol/templates/docs/exemplar-catalog.md | created |  |
| .xian-harness/protocol/templates/docs/project-baseline.md | created |  |
| .xian-harness/protocol/templates/docs/project-discipline.md | created |  |
| .xian-harness/protocol/templates/docs/project-status.md | created |  |
| .xian-harness/protocol/templates/docs/requirement.md | created |  |
| .xian-harness/protocol/templates/docs/todo-list.md | created |  |
| .xian-harness/protocol/templates/evidence-samples/base-golden/acceptance-criteria.md | created |  |
| .xian-harness/protocol/templates/evidence-samples/base-golden/archive-summary.md | created |  |
| .xian-harness/protocol/templates/evidence-samples/base-golden/experience-disposition.json | created |  |
| .xian-harness/protocol/templates/evidence-samples/base-golden/gate-result.json | created |  |
| .xian-harness/protocol/templates/evidence-samples/base-golden/README.md | created |  |
| .xian-harness/protocol/templates/evidence-samples/base-golden/verify-result.json | created |  |
| .xian-harness/protocol/templates/evidence-samples/base-golden/workbench-snapshot.json | created |  |
| .xian-harness/protocol/templates/hooks/hook-contract.md | created |  |
| .xian-harness/protocol/templates/project-status.md | created |  |
| .xian-harness/protocol/templates/quality-gate-report.md | created |  |
| .xian-harness/protocol/templates/README.md | created |  |
| .xian-harness/protocol/templates/requirement.md | created |  |
| .xian-harness/protocol/templates/tasks.md | created |  |
| .xian-harness/protocol/templates/verify-report.md | created |  |
| .xian-harness/protocol/templates/workbench-snapshot.md | created |  |
| .xian-harness/README.md | created |  |
| .xian-harness/schemas/agent-pair-providers.schema.json | created |  |
| .xian-harness/skill-registry.json | created |  |
| AGENTS.md | created |  |
| CLAUDE.md | created |  |
| hooks/pre-tool-use-core.cjs | created |  |
| hooks/session-start-core.cjs | created |  |
| hooks/stop-core.cjs | created |  |
| templates/python-project-checklist.md | created |  |
