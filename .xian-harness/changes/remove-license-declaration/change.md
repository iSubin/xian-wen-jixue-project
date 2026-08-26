<!-- xian-harness:generated-view.v1
view: change.md
authority: contract-revision
rendererId: change-contract-markdown.v1
contractRevision: rev-0004
renderHash: sha256:cc8121920a107a7a7ce7227d40d39c172d8426248dcfe998e0a2a2c6cb9e077e
editPolicy: submit-contract-patch
editCommand: xian-harness change contract-patch remove-license-declaration --file <candidate.json> --target <target-project> --json
-->
# Change: remove-license-declaration

## Intent

删除 README 中所有 GPL 和 LICENSE 相关声明、链接及导航，消除当前仓库的错误许可证表述和失效链接。

## Source

用户明确请求删除 LICENSE 相关内容。

## Scope

Changed paths:

  - README.md

Out of scope:

- This open does not execute, verify, gate, close, commit, or push the change.
- Implementation details remain owned by the future active change lifecycle.

## Plan

- [ ] Inspect the captured intent, source, scope, acceptance, and verification commands.
- [ ] Implement only the captured scope, then run verify/check/close through the normal lifecycle.

## Acceptance

Gate 前 AC 只写 verify/check 可证明的事实；不要把 `close.json`、`archive-result.json` 或 close/archive 已完成写成已勾选 AC。终态证据由 close/archive action 后证明。

- [ ] AC-001 README.md 不再包含 GPL、LICENSE 或许可证导航与章节。
  Verify: `! rg -n 'GPL|LICENSE|许可证' README.md`
- [ ] AC-002 Harness 文档检查不再报告 docs.root-entry.broken-link:LICENSE。
  Verify: `xian-harness docs inspect --target . --json`
- [ ] AC-003 本次工作树变更仅限 README.md 与 .xian-harness 治理记录，不修改业务代码或依赖。
  Verify: `git diff --exit-code -- . ':(exclude)README.md' ':(exclude).xian-harness/**'`
- [ ] AC-004 Generated contract views, tasks, and verification mappings remain consistent with the captured facts. <!-- xian-harness:generated-acceptance -->
  Verify: `xian-harness docs inspect --target . --json`

## Verification Commands

- [ ] **VC-001** `! rg -n 'GPL|LICENSE|许可证' README.md`
- [ ] **VC-002** `xian-harness docs inspect --target . --json`
- [ ] **VC-003** `xian-harness change inspect remove-license-declaration --target . --json`
- [ ] **VC-004** `git diff --exit-code -- . ':(exclude)README.md' ':(exclude).xian-harness/**'`
- [ ] **VC-005** `git diff --check -- README.md`

## Risk

Mode: lite
Tier: small
Risk: lite/small

## Result

Status: active
