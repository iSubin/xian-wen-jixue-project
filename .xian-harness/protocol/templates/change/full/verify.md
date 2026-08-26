<!-- xian-harness:generated-view-seed.v1
view: verify.md
authority: legacy-markdown
rendererId: template-registry.change.full
contractRevision: none
editPolicy: contract-ready; after contract authority is enabled, submit a contract patch instead of hand-editing this generated view.
-->

# Verify: {change-id}

Template Contract: xian-harness/change/full/verify

## Template Quality Contract

| 项 | 内容 |
|---|---|
| Fact Sources | acceptance criteria、tasks、verification commands、runner environment。 |
| Owner Role | Verifier Agent。 |
| Verification Commands | `xian-harness verify {change-id} --target <target-project> --json`。 |
| Evidence Paths | `.xian-harness/changes/{change-id}/verify/verify-result.json`。 |

## Status

pending

## Evidence

运行 `xian-harness verify {change-id}` 后由系统写入验证结果、命令日志和 residual risk。

## Documentation Check

- [ ] 项目级文档同步要求已按 `acceptance-criteria.md` 的 Documentation Contract 判断。
- [ ] 若代码、协议、pack、registry 或 profile 边界发生变化，相关文档已同步或记录不更新原因。
