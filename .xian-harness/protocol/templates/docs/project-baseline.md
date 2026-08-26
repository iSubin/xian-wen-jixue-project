# 项目基线

Template Contract: xian-harness/docs/project-baseline

## Template Quality Contract

| 项 | 内容 |
|---|---|
| Fact Sources | Git、项目文件、运行时标志、启动脚本、测试命令、adapter inspect。 |
| Owner Role | Intake Agent / Doc Steward。 |
| Verification Commands | `xian-harness baseline inspect --target <target-project> --json`。 |
| Evidence Paths | `docs/项目基线.md`。 |

## 摘要

- 项目：
- 场景：takeover / refactor / new-project
- Profile：base / typescript / python / deployment-ops / auto / custom
- 生成时间：yyyy-MM-dd HH:mm:ss
- 生成者：

## 目标项目识别

| 项 | 结论 | 证据 |
|---|---|---|
| 根目录 | {path} | `pwd` / `git rev-parse --show-toplevel` |
| 代码仓库 | {repo} | `git remote -v` |
| 技术栈标志 | {markers} | `pom.xml` / `package.json` / `requirements.txt` / `go.mod` / `Cargo.toml` |
| Profile 判断 | {profile} | marker、目录结构、用户上下文 |

规则：

- 先判断目标项目，再使用 profile 规则。
- 不使用未验证的固定路径。
- 如果目标项目与当前 cwd 不一致，先停止实现并确认目标路径。

## 技术栈与运行时

| 类型 | 当前事实 | 验证方式 |
|---|---|---|
| 后端 | {backend} | {command-or-file} |
| 前端 | {frontend} | {command-or-file} |
| 移动端 | {mobile} | {command-or-file} |
| 数据库 | {database} | {command-or-file} |
| 缓存 / 中间件 | {middleware} | {command-or-file} |
| 包管理器 | {package-manager} | {command-or-file} |

## 架构与资源索引

| 资源 | 路径 | 说明 | 证据 |
|---|---|---|---|
| 启动入口 | {path} | {description} | {evidence} |
| 业务模块 | {path} | {description} | {evidence} |
| API / Controller | {path} | {description} | {evidence} |
| 数据模型 | {path} | {description} | {evidence} |
| 前端页面 | {path} | {description} | {evidence} |
| 配置文件 | {path} | {description} | {evidence} |
| 部署脚本 | {path} | {description} | {evidence} |

## 启动与健康检查

| 目标 | 命令 / 操作 | 期望结果 | 当前状态 |
|---|---|---|---|
| 后端启动 | {command} | {expected} | unknown |
| 前端启动 | {command} | {expected} | unknown |
| 数据库连接 | {command} | {expected} | unknown |
| 健康端点 | {endpoint} | {expected} | unknown |

规则：

- 不捏造健康端点。
- 未确认端点前，先从路由、Controller、配置或文档中查证。
- GUI、交互式登录、sudo 安装等非 Agent 可控动作必须标记为人工动作。

## 测试基线

| 层级 | 命令 | 当前结果 | 证据 |
|---|---|---|---|
| 单元测试 | {command} | unknown | {evidence} |
| 集成测试 | {command} | unknown | {evidence} |
| Smoke | {command} | unknown | {evidence} |
| E2E | {command} | unknown | {evidence} |
| 类型检查 / 编译 | {command} | unknown | {evidence} |

已知失败：

| 命令 | 失败原因 | 是否阻断接管 | 后续处理 |
|---|---|---|---|
| {command} | {reason} | yes/no | {next-action} |

## 风险清单

| Severity | 风险 | 证据 | 缓解动作 |
|---|---|---|---|
| P1 | {risk} | {evidence} | {mitigation} |

风险分类：

- 代码风险。
- 配置风险。
- 安全风险。
- 数据迁移风险。
- 运行环境风险。
- Harness profile 污染风险。

## 接管报告

- 当前是否可接管：
- 已安装 / 应安装 Harness Pack：
- 后续需求应从哪里进入：
- 第一个建议 change：
- 需要人工确认的事项：

## 后续 Change 候选

| Change | 类型 | 原因 | 优先级 |
|---|---|---|---|
| {change-id} | takeover / refactor / new-project / fix / feature | {reason} | P1 |
