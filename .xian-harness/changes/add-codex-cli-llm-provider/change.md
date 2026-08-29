<!-- xian-harness:generated-view.v1
view: change.md
authority: contract-revision
rendererId: change-contract-markdown.v1
contractRevision: rev-0005
renderHash: sha256:b9f9080aecbf18726e56f1a1ab1d4fdf8a6401fbaf229f8c90fd839e0070bf66
editPolicy: submit-contract-patch
editCommand: xian-harness change contract-patch add-codex-cli-llm-provider --file <candidate.json> --target <target-project> --json
-->
# Change: add-codex-cli-llm-provider

## Intent

在现有 LLM Profile 体系中新增 codex_cli provider，通过受约束的 subprocess 调用本机 Codex CLI 分析逐字稿，同时保持现有 standard/agent/auto 总结与其他 LLM provider 行为不变。

## Source

Owner request; reference evidence from the running xian-harness Codex CLI reviewer adapter.

## Scope

Changed paths:

  - src/main/python/xianwen/llm
  - src/main/python/xianwen/config/settings.py
  - src/main/python/xianwen/api.py
  - config/settings.example.json
  - frontend/src
  - tests

Out of scope:

- This open does not execute, verify, gate, close, commit, or push the change.
- Implementation details remain owned by the future active change lifecycle.

## Plan

- [ ] Inspect the captured intent, source, scope, acceptance, and verification commands.
- [ ] Implement only the captured scope, then run verify/check/close through the normal lifecycle.

## Acceptance

Gate 前 AC 只写 verify/check 可证明的事实；不要把 `close.json`、`archive-result.json` 或 close/archive 已完成写成已勾选 AC。终态证据由 close/archive action 后证明。

- [ ] AC-001 LLM 设置可创建、保存、切换和识别 codex_cli Profile，且不要求 API Key。
  Verify: `.venv/bin/python -m pytest -q tests/test_codex_cli_llm.py`
- [ ] AC-002 codex_cli 通过无 shell subprocess、stdin、read-only sandbox、ephemeral session 和隔离环境执行，并从结构化结果读取最终 Markdown。
  Verify: `.venv/bin/python -m pytest -q tests/test_codex_cli_llm.py`
- [ ] AC-003 Codex CLI 不可用、未登录、超时、取消、异常退出或输出超限时给出可操作错误，并可靠回收子进程。
  Verify: `.venv/bin/python -m pytest -q tests/test_codex_cli_llm.py`
- [ ] AC-004 standard 与 agent 总结可使用 codex_cli，现有 DeepSeek/OpenAI兼容 provider 无回归。
  Verify: `.venv/bin/python -m pytest -q tests/test_codex_cli_llm.py`
- [ ] AC-005 后端聚焦测试与前端构建通过。
  Verify: `.venv/bin/python -m pytest -q tests/test_codex_cli_llm.py`
- [ ] AC-006 Generated contract views, tasks, and verification mappings remain consistent with the captured facts. <!-- xian-harness:generated-acceptance -->
  Verify: `.venv/bin/python -m pytest -q tests/test_codex_cli_llm.py`

## Verification Commands

- [ ] **VC-001** `.venv/bin/python -m pytest -q tests/test_codex_cli_llm.py`
- [ ] **VC-002** `frontend/node_modules/.bin/vue-tsc -b frontend/tsconfig.json`

## Risk

Mode: governed
Tier: standard
Risk: governed/standard

## Result

Status: active
