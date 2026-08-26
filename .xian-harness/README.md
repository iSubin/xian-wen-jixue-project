# `.xian-harness/` canonical filesystem inventory

`.xian-harness/` 是目标项目中唯一的 Harness-managed operational authority。Runtime、Gate、Verify、projection、status、goal 和 Pack consumers 不读取 `docs/xian-harness/`；后者只保留 Git-only cold archive 与人读历史文档。

| Path | Purpose | Owner | Tracked / ignored policy | Retention | Producer | Consumers |
|---|---|---|---|---|---|---|
| `harness-protocol.yaml` | 项目级 Harness 配置与治理策略 | project owner | tracked | 当前配置持续保留 | `xian-harness init` / owner | all Runtime commands |
| `state.yaml` | 唯一 current state authority | lifecycle Runtime | tracked | 当前状态持续保留 | lifecycle mutations | status / change / goal / verify / gate |
| `changes/` | current change contract、phase facts、Verify/Gate/finalize evidence | lifecycle Runtime | tracked；`.manifest.json`、locks 与 HTML cache ignored | current records 按 lifecycle 保留；终态历史由 Git 追溯 | change / review / verify / gate / finalize | continue / Gate / merge-ready / project projection |
| `goals/` | serial goal 与 child order facts | goal Runtime | tracked | goal close 后由 Git 保留 | `xian-harness goal` | continue / goal close / integration coordinator |
| `project/` | project status、next decision、doc sync 与 projection watermark | project projection | tracked | current projection 可重建，提交时保留 | project / docs render | status / docs / Gate |
| `backlog/` | machine-readable parked/backlog registry | backlog Runtime | tracked | 当前 backlog 持续保留 | `xian-harness todo` / capture | project queue / docs render |
| `archive/`、`releases/` | current lifecycle closeout 与 release evidence | finalize Runtime | tracked | source-bound Git evidence | finalize / release | Gate / review / merge-ready |
| `evidence/`、`quality-gates/` | project-level verification、gate outputs 与 uninstall-retained change snapshots | Verify / Gate / uninstall | tracked；redacted logs explicitly trackable | source-bound Git evidence；`uninstall --preserve-evidence` 快照不再作为 current authority 读取 | verify / gate / uninstall | evidence status / merge-ready / human audit |
| `agents/`、`workbench/` | current handoff facts 与显式派生视图 | collaboration Runtime | tracked；HTML cache ignored | facts source-bound，views 可重建 | agent / workbench | review / downstream agents |
| `protocol/` | Pack-distributed protocol templates | Harness Pack | tracked | 随 Pack version 更新 | Pack sync | init / renderers |
| `schemas/` | Pack-distributed machine schemas | Harness Pack | tracked | 随 schema version 更新 | Pack sync | Runtime validators / integrations |
| `integrations/` | host integration authority 与 thin-entry parity boundary | Harness Pack | tracked | 随 Pack version 更新 | Pack sync | `.codex` / `.claude.disabled` / hooks thin entries |
| `runtime/` | locks、execution ledger、provider logs 与 session state | Runtime | ignored | local / ephemeral | Runtime commands and hooks | current process / diagnostics |
| `cache/` | derived manifests、verify plans 与 render caches | Runtime | ignored | disposable | Runtime commands | performance and rebuild paths |
| `local/` | machine-local config、telemetry epoch、private overrides，以及 `change-supply/{pending,processing,quarantine,done,locks}/` Producer/Consumer queue | local owner | contents ignored；directory policy tracked | local policy；`pending` append-only，唯一 Consumer 在安全项目边界把请求移入 `done` 或 `quarantine`，失败事务恢复 `pending` | local setup / telemetry / `change supply submit` / `change supply consume` | local Runtime；全部 supply queue 均不是 lifecycle authority |
| `pack/` | content-addressed Pack status facts | Gate / Pack | tracked when emitted | source-bound facts | pack status / Gate | Gate reuse / evidence |
| `pack-state.json`、`harness-pack-manifest.yaml` | installed Pack file identity 与 source snapshot | Harness Pack | tracked | current installation state | pack install / sync | pack status / Gate |
| `capability-registry.json`、`project-boundaries.json`、`project-risks.json`、`project-accepted-exceptions.json` | current project governance registries | project owner / render pipeline | tracked | current facts持续保留 | docs source maintainer / Gate | project status / baseline / Gate |
| `cli-default-surface-usage-baseline.json` | current CLI default-surface generation input | CLI maintainer | tracked | 当前 baseline 持续保留 | owner / CLI generator | default-surface generator |

Host-required `.codex/` 与 `.claude.disabled/`（包括 hooks）是 Pack-managed generated/disabled thin entries，不是第二套可编辑 operational authority。`references/` 是外部输入：本仓库不跟踪、不扫描、不迁移、不修改。
