# Base Golden Sample Evidence Bundle

Template Contract: xian-harness/evidence-samples/base-golden

## Template Quality Contract

| Item | Value |
|---|---|
| Fact Sources | Sample acceptance, verify result, gate result, Workbench snapshot, archive summary, experience disposition. |
| Owner Role | Gatekeeper Agent / Doc Steward. |
| Verification Commands | `xian-harness check base-golden-sample --target <target-project> --json`. |
| Evidence Paths | `.xian-harness/protocol/templates/evidence-samples/base-golden/` and generated change-local evidence paths. |

This bundle is a sample hard asset for learning and review.

Do not treat this sample as completion evidence for a real change. A real change must generate its own verification logs, gate result, Workbench snapshot, release review, archive result, and experience disposition inside `.xian-harness/changes/{change-id}/`.

## Purpose

The sample shows how a complete base profile evidence chain should connect:

```text
Acceptance Criteria
  -> Verification Evidence
  -> Quality Gate
  -> Workbench Snapshot
  -> Archive
  -> Experience Review
```

## Files

| File | Role |
|---|---|
| `acceptance-criteria.md` | Demonstrates AC IDs, fact sources, verification commands, and evidence mapping. |
| `verify-result.json` | Demonstrates a passed verification result and evidence directory. |
| `gate-result.json` | Demonstrates a passed quality gate result with no blocking issues. |
| `workbench-snapshot.json` | Demonstrates handoff-readable status and recommended route. |
| `archive-summary.md` | Demonstrates human-readable archive closure. |
| `experience-disposition.json` | Demonstrates experience review closure after archive. |

## Acceptance Criteria

The sample acceptance contract should show:

- AC IDs.
- Linked fact sources.
- Verification Commands.
- Evidence paths.
- Gate or release evidence paths.

## Verification Evidence

Verification evidence should show:

- command status.
- evidence directory.
- log paths.
- no local absolute paths.

## Quality Gate

Quality Gate should show:

- gate status.
- blocking count.
- open quality issues.
- evidence that connects back to acceptance and verification.

## Workbench Snapshot

Workbench Snapshot should show:

- current phase.
- recommended route.
- latest verification and gate status.
- next Agent handoff context.

## Archive

Archive should show:

- why the change can be closed.
- which evidence files prove closure.
- which follow-up work remains outside the change.

## Experience Review

Experience Review should show:

- candidate decision.
- target asset when promoted.
- why the experience is or is not reusable.
