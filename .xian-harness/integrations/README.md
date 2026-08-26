# Host integration authority

本目录记录 Harness host integration 的 canonical authority。目标根的 `.codex/`、Pack 分发的 `.claude/` 与 self-hosted `.claude.disabled/`（包括 hooks）只作为 Harness Pack 生成或同步的 thin entry；需要修改集成能力时，先修改 Pack source，再通过现有 Pack parity 检查同步，不直接把宿主入口提升为第二套 authority。
