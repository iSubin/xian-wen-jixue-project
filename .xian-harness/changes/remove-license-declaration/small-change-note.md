# Small Change Note: remove-license-declaration

## Intent

删除 README 中所有 GPL 和 LICENSE 相关声明、链接及导航，消除当前仓库的错误许可证表述和失效链接。

## Scope

- Tier: small
- Changed paths:
  - README.md

## Acceptance

- [ ] **AC-001** README.md 不再包含 GPL、LICENSE 或许可证导航与章节。
- [ ] **AC-002** Harness 文档检查不再报告 docs.root-entry.broken-link:LICENSE。
- [ ] **AC-003** 本次工作树变更仅限 README.md 与 .xian-harness 治理记录，不修改业务代码或依赖。
- [ ] **AC-004** Generated contract views, tasks, and verification mappings remain consistent with the captured facts.

## Targeted Verification

- [ ] **VC-001** `! rg -n 'GPL|LICENSE|许可证' README.md`
- [ ] **VC-002** `xian-harness docs inspect --target . --json`
- [ ] **VC-003** `xian-harness change inspect remove-license-declaration --target . --json`
- [ ] **VC-004** `git diff --exit-code -- . ':(exclude)README.md' ':(exclude).xian-harness/**'`
- [ ] **VC-005** `git diff --check -- README.md`

## Upgrade Triggers

如果变更触及 schema、state-machine、gate、archive、pack、skill contract、quality mechanism、安全、迁移或跨模块运行时行为，必须升级到 standard 或 major，不允许继续 quick close。
