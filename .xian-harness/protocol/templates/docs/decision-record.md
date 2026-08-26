# 技术决策记录

Template Contract: xian-harness/docs/decision-record

## Template Quality Contract

| 项 | 内容 |
|---|---|
| Fact Sources | `docs/项目基线.md`、adapter inspect、source search、change facts。 |
| Owner Role | Designer Agent / Doc Steward。 |
| Verification Commands | `xian-harness docs inspect --target <target-project> --json`。 |
| Evidence Paths | `docs/技术决策记录.md` 或 change-local decision record。 |

## 决策元信息

- 决策编号：
- Change：
- 状态：proposed / accepted / superseded / rejected
- 创建时间：
- 决策人 / 角色：
- 关联文档：

## 决策背景

说明为什么现在需要做这个技术决策。只描述已确认的问题、约束和目标，不把未确认的猜测写成事实。

## 项目约束

| 约束 | 当前事实 | 来源 |
|---|---|---|
| 技术栈 | {stack} | `docs/项目基线.md` / adapter inspect |
| 已有模块 | {modules} | source search / project baseline |
| 运行环境 | {runtime} | runner environment / project baseline |
| Profile | base / typescript / python / deployment-ops / custom | `.xian-harness/harness-protocol.yaml` |

## 方案对比

| 方案 | 复用度 | 复杂度 | 风险 | 验证成本 | 结论 |
|---|---:|---:|---:|---:|---|
| 方案 A | high / medium / low | high / medium / low | high / medium / low | high / medium / low | accept / reject |
| 方案 B | high / medium / low | high / medium / low | high / medium / low | high / medium / low | accept / reject |

## 决策结论

明确选择哪个方案，以及不选择哪些方案。

## 决策理由

- 优先复用当前项目已有能力。
- 优先选择能被现有测试、smoke、gate 或 adapter policy 验证的方案。
- 不要因为单点需求引入大框架。
- 不要绕过 active profile 的技术约束。

## 影响范围

| 范围 | 影响 | 后续动作 |
|---|---|---|
| 代码 | {impact} | {action} |
| 配置 | {impact} | {action} |
| 数据 | {impact} | {action} |
| 测试 / Gate | {impact} | {action} |
| 文档 | {impact} | {action} |

## 风险与后续

| 风险 | 概率 | 影响 | 缓解方式 | 是否阻断 |
|---|---:|---:|---|---:|
| {risk} | high / medium / low | high / medium / low | {mitigation} | yes/no |

## 复审条件

- 上游框架或关键依赖升级。
- 当前方案无法通过 verification / gate。
- 目标项目 profile 或业务约束变化。
- 成本、性能、安全或运维风险显著变化。
