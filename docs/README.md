# 先闻继学文档中心

本目录保存先闻继学的正式产品、架构、使用、研究和交接文档。临时产物、运行缓存和用户内容不应放入此目录。

## 文档导航

### 品牌

- [先闻继学品牌与命名规范](brand/先闻继学品牌与命名规范.md)

### 架构

- [统一知识采集与内容分发架构](architecture/xianwen-content-ingestion-architecture.md)
- [用户级采集账号设计](architecture/用户级采集账号设计.md)

### 使用指南

- [使用说明](guides/使用说明.md)

### 示例

- [长视频总结示例（Agent 增强模式）](examples/长视频总结-带agent.md)
- [长视频总结示例（标准模式）](examples/长视频总结-非agent.md)

### 交接

- [开发主线交接文档](handoff/xianwen-session-handoff.md)

### 历史设计记录

- `superpowers/specs/`：已经形成的功能设计。
- `superpowers/plans/`：对应功能的实施计划。

### 图片资源

- `images/`：README、指南和示例文档使用的图片与动图。

## 维护约定

- 正式文档统一进入 `docs/`，不再使用 `prj-docs/`。
- 产品和技术边界放入 `architecture/`，外部方案比较放入 `research/`。
- 面向使用者的说明放入 `guides/`，交接快照放入 `handoff/`。
- 新的重要架构决策应在文档中说明背景、结论、边界和迁移方式。
- 不提交 API Key、Cookie、SESSDATA、访问令牌或用户私有内容。
- Claude Code 课程、飞书发布和课程专用抓取资产已迁至独立工程 `xian-courses-ai/xian-claude-code-course`。
