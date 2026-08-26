# Project Doc Sync Report

- Generated at: 2026-08-26T21:09:18+08:00
- Status: warning
- Issues: 2
- Blocking: 0

## Inputs

| Input | Path |
|---|---|
| Project Status | .xian-harness/project/project-status.json |
| Docs Index | docs/README.md |

## Fixes

- Applied: no
- Created documents: none
- Updated indexes: none
- Skipped rules: none

## Freshness Issues

| Severity | Rule | Path | Message | Recommendation | Evidence |
|---|---|---|---|---|---|
| P2 | project-docs.render-freshness | docs/项目状态.md | Rendered project document is stale: Canonical source facts changed since the document was rendered. Rerun docs render with --fix to update this managed projection. | Run xian-harness docs render --doc project-status --target <target-project> --fix. | templates/docs/project-status.md.tmpl, 6e41b5b5d510102b1739f16682b499d38c3c34d4018a15ea0e3e1ec428a50e5f, source-stale |
| P2 | project-docs.render-freshness | docs/待办清单.md | Rendered project document is stale: Canonical source facts changed since the document was rendered. Rerun docs render with --fix to update this managed projection. | Run xian-harness docs render --doc todo-list --target <target-project> --fix. | templates/docs/todo-list.md.tmpl, 2665b7c0209517f78ccc51238c4f378fc67e7c096fee3f1c9a1ab415b0136547, source-stale |
## Issues

| Severity | Rule | Path | Message | Recommendation | Evidence |
|---|---|---|---|---|---|
| P2 | project-docs.render-freshness | docs/项目状态.md | Rendered project document is stale: Canonical source facts changed since the document was rendered. Rerun docs render with --fix to update this managed projection. | Run xian-harness docs render --doc project-status --target <target-project> --fix. | templates/docs/project-status.md.tmpl, 6e41b5b5d510102b1739f16682b499d38c3c34d4018a15ea0e3e1ec428a50e5f, source-stale |
| P2 | project-docs.render-freshness | docs/待办清单.md | Rendered project document is stale: Canonical source facts changed since the document was rendered. Rerun docs render with --fix to update this managed projection. | Run xian-harness docs render --doc todo-list --target <target-project> --fix. | templates/docs/todo-list.md.tmpl, 2665b7c0209517f78ccc51238c4f378fc67e7c096fee3f1c9a1ab415b0136547, source-stale |
