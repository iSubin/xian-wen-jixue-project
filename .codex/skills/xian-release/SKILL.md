---
name: xian-release
description: Use when an explicitly approved release candidate needs version preparation, a human-readable changelog, exact-SHA CI validation, tagging, and atomic publication.
---

# xian-release

## 用途

协调显式 release candidate（发布候选）：准备一次版本号与人读 `CHANGELOG.md`，把不可变 candidate commit 交给 release runner 的 Release Verify（发版验证），导入带 Harness Ed25519 Attestation（签名证明）的 Result Commit（结果提交），再由 Git Publication Adapter（Git 发布适配器）只消费 Result 中已封存的 Publication Intent（发布意图），原子发布 default branch 与 annotated tag。

普通 commit、普通 change、普通 push 和 change archive 不是版本边界，不调用本 skill。

## 触发条件

Use this skill only when the owner explicitly asks to release、发版、准备 release candidate、递增版本、生成版本 changelog 或创建版本 tag。`xian-archive` 生成 change 内部 release/archive facts，不等于产品版本发布。

## 协议输入

- `.xian-harness/state.yaml`
- `.xian-harness/changes/{change-id}` 的已归档 change facts，仅用于确认没有 active lifecycle；不从其中拼接用户 changelog。
- 显式目标 SemVer，例如 `0.2.0-rc.3` 或 `0.2.0`。
- 目标 `package.json`、`package-lock.json` 与 `CHANGELOG.md` 路径。
- 最近可达 `v<semver>` tag 以及从该 tag 到 source HEAD 的全部 non-merge commits。
- 远端 default branch baseline、目标 tag 与 candidate ref 状态。
- 受保护 default branch 或 owner 指定固定 SHA 上的 `.github/workflows/harness-integration.yml`，以及它对 candidate SHA 导出的 `harness-release-result-<candidate-sha>` artifact。
- owner/root 预配置的固定 host trust store `/etc/xian-harness/release-trust/v1` 中的 repository identity、trusted signer key ID 与 Ed25519 public key；私钥只能存在于隔离 signer environment（签名环境）。

## ReleasePurpose 权威

- Host 必须把 owner 的显式发布目的编译成 canonical `ReleasePurpose = { version: 1, kind, target }`；`kind` 只能是 `version`、`annotated-tag`、`pack`、`registry` 或 `deploy`。
- 本 Skill 的版本发布会创建 `v<version>` annotated tag，因此全链统一使用 `--purpose-kind annotated-tag --purpose-target v<version>`。同一 purpose 必须进入 Release Verify candidate/attempt/result、Result Commit，并在 `status/import/publish` 时复验。
- 缺少 purpose 的历史 passing attempt 可以保留作诊断，但不得授权 Result Commit 或 Publication。purpose 变化必须形成新的 release candidate identity，不能复用旧 Verify 结果。
- 普通 Change、Gate、archive、commit、push、Release suite 修复、Reviewer 建议和历史失败都不能代替 owner release intent，也不能由 Skill 静默补出 purpose。

## 版本边界

- 版本粒度由 release candidate 决定，不由 commit 或 change 数量决定。
- 多个 changes 可以合并为一个 release；单个 change 也可以单独 release，但必须显式进入本边界。
- 目标版本是最终 authority。Skill 可以对同一 pre-release 通道建议递增序号，但 stable、major、minor 或通道切换必须由 owner 明确指定。
- 一次 release 只有一个 release-preparation commit；version、lock root version 与 changelog 必须同树提交。

## CHANGELOG 内容契约

- `CHANGELOG.md` 面向使用者完整说明本次版本改变了什么，而不是复制 Git 索引。
- 只写版本、`Asia/Shanghai` 日期与行为级摘要；不得写 commit SHA、source SHA、candidate SHA、compare hash 或逐 commit 列表。
- 使用提交标题与正文中的“改了什么、为什么、影响范围”作为事实输入，按“新增功能、问题修复、能力改进、文档与兼容性、工程治理、其他”分组。
- 从最近可达 release tag 到 source HEAD 的每个 non-merge commit 都必须映射为一个条目；只有规范化后完全相同的描述可以去重。
- Git、CI check 与 tag 保存机器 provenance（来源追溯）；不要把这些标识塞进 changelog。

## 执行流程

1. 确认 `activeChange=null`、没有 open goal、tracked/untracked worktree clean，且当前分支与远端 default branch 没有 behind/diverged。
2. 记录远端 default branch baseline，并确认显式目标版本合法、递增且目标 tag 不存在。
3. 运行 bundled helper（随 Skill 分发的辅助脚本），只准备版本文件与人读 changelog：

   ```sh
   node .codex/skills/xian-release/scripts/prepare-release.mjs \
     --target <target-project> \
     --package-path <package-json-path> \
     --lock-path <package-lock-path> \
     --changelog-path CHANGELOG.md \
     --version <target-version>
   ```

4. 定向审查生成 diff，确认 changelog 无 SHA 且全部范围内 commits 已映射；随后创建唯一 release-preparation commit。脚本本身不得 commit、tag、push 或 dispatch。
5. 读取 candidate SHA，创建唯一 candidate ref，例如 `xian-release/v<version>-<short-sha>`，只把 candidate commit 推送到该 ref。
6. 从 protected signer environment 配置读取唯一适用的 `attestation_key_id`，并确定受保护的 `<trusted-workflow-ref>`。使用该可信 ref dispatch（派发）CI，Candidate 只作为 `expected_sha` 数据输入；Publication Intent 必须在 Result Commit 前确定，不能在 publish 时临时改写：

   ```sh
   gh workflow run harness-integration.yml \
     --ref <trusted-workflow-ref> \
     -f expected_sha=<candidate-sha> \
     -f publication_branch=<default-branch> \
     -f publication_tag=v<version> \
     -f publication_tag_message="Release v<version>" \
     -f attestation_key_id=<trusted-key-id>
   ```

   随后定位本次 dispatch 之后 `workflowName=Harness Release Verify`、`event=workflow_dispatch`、`displayTitle=Release <candidate-sha>`、`headSha=<trusted-workflow-sha>` 的唯一 run。Verify job 不持有签名私钥；Candidate 命令只在固定 OCI image digest、无 host mount 的 Docker sandbox 中运行，实际 image ID 与容器 Node/npm/OS/arch 必须进入 Result identity；独立 `xian-release-signer` protected environment 只执行 trusted controller，不 checkout 或执行 Candidate。GitHub Actions 只是可替换 runner，不是 Harness provenance（来源证明）的信任 authority。当前 Candidate lock 必须与 trusted controller 已批准 lock projection 一致；依赖升级在无密钥 dependency bundle preparation 落地前 fail closed，不通过预先更新 trusted baseline 或开放 Candidate 联网绕过。

   trusted workflow 调用 `release verify` 与 `release commit` 时必须使用同一个 `annotated-tag` purpose：`--purpose-kind annotated-tag --purpose-target v<version>`；现有受保护的 `publication_tag` 输入是该 purpose 的结构化 Host 来源，不由 Candidate 自行生成。
7. 等待 run terminal。只有 `conclusion=success` 且 workflow、event、headSha 全部精确匹配时继续；失败、取消、超时、缺失或歧义都 fail closed（失败关闭）。下载该 run 的 `harness-release-result-<candidate-sha>` artifact，并执行：

   ```sh
   xian-harness release import \
     --target <target-project> \
     --manifest <download-dir>/manifest.json \
     --attestation <download-dir>/attestation.json \
     --purpose-kind annotated-tag \
     --purpose-target v<version> \
     --json
   ```

   import 必须验证仓库 trust policy、Ed25519 signature、Manifest 精确字节、release candidate、HEAD、tree 与 Publication Intents，并写入 immutable Import Receipt；不得把 GitHub check conclusion 或自计算 hash 单独当作发布 authority。
8. 重新 fetch 远端 default branch，确认它仍等于步骤 2 的 baseline；再次确认 candidate SHA 没变、目标 tag 在本地和远端都不存在。
9. 只通过 Harness Git Publication Adapter 执行一次原子 branch+tag 发布：

   ```sh
   xian-harness release publish \
     --target <target-project> \
     --purpose-kind annotated-tag \
     --purpose-target v<version> \
     --json
   ```

   Adapter 必须消费已导入的 Result Commit 及其中唯一 Git Publication Intent、执行单次 `git push --atomic`，并为成功、失败或复用追加 immutable Publication Attempt/Receipt（发布尝试/回执）；atomic push 失败时禁止分步补发。
10. 报告版本、changelog 行为摘要、candidate SHA、CI run URL、Result Commit identity、tag 与 Publication Receipt。SHA 只出现在机器/交付报告，不写回 `CHANGELOG.md`。

## 失败与恢复

- 当 release candidate 属于 active change 时，任何已启动 CI、Gate 或发布验证的 non-pass 只 terminalize 对应 immutable ActionAttempt，不自动终结 Business Change。后续必须消费 current machine `failureRecovery.decision`：`prepare-new-candidate` 在 same Business Change 内形成新的 candidate SHA；`retry-same-candidate` 仅用于获机器授权的 environment interruption；repository-baseline 只有在完整 current classifier/admission proof 下由 `suspend-for-incident-repair` 授权 `incident-repair` relation；只有 `business-boundary classifier` 给出 `terminalize-business-change` 时才可 terminalize 或 replace Business Change。不得改写 sealed evidence、机械重跑或手写 successor。

- helper 失败：修复输入或版本内容；尚无远端 release mutation。
- candidate CI 失败：default branch 与 tag 保持不变；candidate ref 可保留诊断，修复后形成新的 candidate commit 与 SHA。
- 远端 baseline 漂移或 tag 冲突：停止发布，重新选择基线或版本；不要 force push。
- Result artifact 缺失、损坏或 candidate identity 不匹配：停止发布，不以 CI conclusion 代替 Result Commit。
- Publication Adapter 失败：读取 immutable failed Receipt 的 diagnostics，branch 与 tag 必须共同保持未发布；不要绕过 Adapter 或拆成两次 push 补发。

## 确定性工具

- `node .codex/skills/xian-release/scripts/prepare-release.mjs ...`
- `git status --short --branch`
- `git describe --tags --abbrev=0 --match 'v[0-9]*' HEAD`
- `git log --no-merges <previous-tag>..HEAD`
- `git rev-parse HEAD`
- `git ls-remote --heads --tags origin`
- `gh workflow run harness-integration.yml --ref <trusted-workflow-ref> -f expected_sha=<candidate-sha> -f publication_branch=<default-branch> -f publication_tag=v<version> -f publication_tag_message="Release v<version>" -f attestation_key_id=<trusted-key-id>`
- `gh run list --workflow harness-integration.yml --event workflow_dispatch --json databaseId,workflowName,displayTitle,event,headSha,status,conclusion,url,createdAt`
- `gh run watch <database-id> --exit-status`
- `gh run download <database-id> -n harness-release-result-<candidate-sha> -D <download-dir>`
- `xian-harness release import --target <target-project> --manifest <download-dir>/manifest.json --attestation <download-dir>/attestation.json --purpose-kind annotated-tag --purpose-target v<version> --json`
- `xian-harness release publish --target <target-project> --purpose-kind annotated-tag --purpose-target v<version> --json`

## 必需证据

- 显式目标版本和 release baseline。
- release-preparation commit 与 clean immutable tree。
- 不含 Git SHA 的 `CHANGELOG.md` 人读版本摘要。
- trusted workflow ref/SHA、workflow name、event、displayTitle、conclusion、databaseId 与 URL。
- CI 导出的 Result Commit Manifest、Harness Ed25519 Attestation、导入后的 `Import Receipt`、`resultCommitIdentity` 与 current-candidate match。
- 发布前远端 baseline/tag recheck。
- Git Publication Receipt 与 atomic branch+tag push 结果。

## 事实映射

- 人读版本变化 -> `CHANGELOG.md`
- 版本事实 -> `package.json` 与 `package-lock.json`
- 候选 tree identity -> release-preparation commit SHA
- full authority -> trusted controller 对精确 candidate SHA 生成的 Harness Result Commit，以及不执行 Candidate 代码的隔离 signer 所生成的可信 Attestation
- 已发布版本 -> Publication Adapter receipt 所证明的 default branch 与 annotated tag

## 参考样例

- 普通 change 完成 `open -> verify -> gate -> close`：不调用 xian-release，不 bump 版本。
- owner 指定 `0.2.0-rc.3` release candidate：准备 version/changelog commit，CI 验证精确 SHA，再原子发布 branch+tag。
- 一个紧急修复单独发版：允许，但仍走相同 candidate、CI 与 tag 边界。

## 自检清单

- 是否有 owner 明确的 release intent 和目标版本？
- `CHANGELOG.md` 是否完整描述行为变化且没有任何 SHA？
- version、lock 与 changelog 是否在同一 candidate tree？
- CI run 的 workflow、event、displayTitle、trusted workflow SHA、conclusion 是否全部匹配？
- CI Result Manifest 是否已导入并与当前 candidate identity 精确匹配？
- 远端 baseline 与 tag 是否在发布前重新校验？
- 是否只通过 Publication Adapter 使用一次 atomic push 发布 branch+tag？

## 交互预算

- 必须：release preflight 只读取当前 release 所需的状态、Git refs、版本文件与 CI run，不扫描无关历史资产。
- 必须：CI 长操作使用一次与预计耗时匹配的等待，并至少每 60 秒向 owner 转述安全进度。
- 必须：失败后读取一次明确 conclusion/log，不机械重复 dispatch 或 full authority。

## 交接规则

- 当前请求明确要求 release 且 preflight/CI/remote recheck 全部通过时，当前主 Agent直接完成 atomic publication，不再次请求 push 授权。
- CI 或远端一致性失败时，说明未发布的 branch/tag 状态、candidate ref 和最小恢复动作；不要把“候选已推送”表述成“版本已发布”。
- 本 skill 不创建 GitHub Release、不部署生产环境；后续若需要这些动作，交给独立 deployment/release-note consumer。
- 当前请求不携带 release publish intent 时，末尾输出 `下一步建议：<中文下一步>`，空一行后单独输出 `$xian-xxx`，再空一行输出 `直接回复“继续”即可进入该步骤。`；不要把建议写成执行完成事实。

## 约束与原因

- 不要为普通 commit 或 change 自动 bump 版本。原因：开发粒度不是发布粒度，自动绑定会制造无意义版本并阻止多 change 聚合。
- 不要在 `CHANGELOG.md` 写 commit SHA、candidate SHA 或 compare hash。原因：这些事实属于 Git/CI provenance，重复写入会让版本说明退化成索引。
- 不要从聊天历史或 Agent 自述生成 changelog。原因：输入不可重放，也无法证明范围内 commits 没有静默丢失。
- 不要读取 Candidate tree 内的 trust policy、从 CLI 临时指定 policy，或把本地自计算 hash/GitHub check conclusion 伪装成跨机器 Result authority。原因：跨机器发布必须由固定 host trust store 验证同一 immutable candidate Result Commit；本机真实 Release Verify 只授权同机连续路径。
- 不要用 Candidate ref dispatch workflow，也不要在执行 Candidate 代码的 job 注入签名私钥。原因：Candidate 不能选择自己的 verifier、workflow 或 signer authority。
- 不要绕过 `release publish` 直接创建 tag 或 push。原因：外部发布必须消费 Result Commit 并留下 Publication Receipt。
- 不要在 CI 之后修改 candidate tree。原因：tree 变化会使成功 check 与实际发布对象失配。
- 不要分步推送 default branch 与 tag。原因：任一步骤失败都会留下远端部分发布状态。
- 不要声称 branch protection 或所有原生 Git 操作都不可绕过。原因：当前实用闭环只保护受管 xian-release 路径。
