# Codex Skills

本目录保存安装到目标项目后的 Codex Skill 模板。

`xian-*` 是通用 Harness 治理 skills，负责协议、计划、验证、门禁、看板和归档。

注意：本目录是 Harness Pack 资产，不是 `xian-agent-harness` 自身开发时的全局 skill 根。开发 `xian-agent-harness` 源码时不要以 `harness-pack/` 作为默认 cwd。

## 技能分组

通用治理 Skills：

- `xian-open`
- `xian-next`
- `xian-spec`
- `xian-design`
- `xian-plan`
- `xian-build`
- `xian-diagnose`
- `xian-project-startup`
- `xian-project-status`
- `xian-project-sync`
- `xian-project-research`
- `xian-verify`
- `xian-review`
- `xian-gate`
- `xian-workbench`
- `xian-archive`
- `xian-cost`

以上不是完整清单，完整内容以本目录下实际 `SKILL.md` 为准。

## 原则

Skill 负责约束 Agent 行为和加载领域知识；确定性工具只作为 Skill 的执行支撑。
