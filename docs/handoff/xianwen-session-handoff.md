# XianWen 开发主线交接文档

日期：2026-07-18

本文用于把当前长 session 的上下文交给新的 XianWen 独立开发主线。新的 session 可以直接从本文开始，不需要重新翻完整对话。

---

## 1. 当前结论

XianWen 后续应作为一个独立产品继续维护，定位是：

> 面向个人和小团队的内容采集、转录、摘要、知识文档生成工具。

另一个“基于飞书文档的中文学习平台”应当拆成新产品，不要继续混进 XianWen 仓库。XianWen 保持采集与加工能力，新学习平台负责内容阅读、课程化、学习进度、搜索和后续知识 Agent。

---

## 2. 仓库状态

当前仓库：

```text
路径：/Users/subin/Documents/Claude-Project/xian-wen-jixue-project
当前分支：master
主远程：git@github.com:iSubin/xian-wen-jixue-project.git
品牌与文档基线提交：9db838c docs: establish xianwen brand and docs layout
```

编写本文前，工作区为干净状态：

```text
master...origin/master
```

近期关键提交：

```text
adae0a6 feat: polish lark course export styling
f441075 feat: backfill lark wiki links
8eabbd3 feat: add web docs lark export tool
f2aeb89 feat: add wechat article capture UI
1df26ae feat: add wechat article capture API
5db5b00 feat: add wechat article adapter
219dde3 feat: add collection capture UI
580628d feat: add collection job backend
68fb18c Fix Bilibili authenticated downloads
```

---

## 3. 本轮已经形成的产品能力

### 3.1 视频采集与转录

当前 XianWen 已经从原始长视频总结工具，扩展成多来源内容采集工具：

- B 站视频采集。
- B 站字幕优先，失败后回退到下载 + ASR。
- B 站 `SESSDATA` 支持。
- B 站时间戳可点击跳转到原视频对应位置。
- 全文转录做了更清晰的时间线 UI。
- 全文转录支持下载逐字稿，去掉时间线标签，方便用户交给其他 Agent 使用。
- 视频截图/抽帧使用高质量源视频，不走低清视频。
- 支持 B 站多 P / 合集任务，能拆成条目执行，并生成聚合 Markdown。

### 3.2 多站点采集

当前已经支持的站点与凭据类型：

```text
Bilibili：SESSDATA
小鹅通：Cookie Header
Homeway / 投研大师：web_qtstr
```

用户侧的推荐流程已经统一成：

1. 用户先在本机浏览器登录目标站点。
2. 打开 XianWen 的“转录设置”。
3. 在“采集账号”中选择对应站点。
4. 点击“从浏览器获取”。
5. 系统保存脱敏后的站点凭据，不向前端回显明文。

手动填写 Cookie 只作为高级兜底入口，不应该作为默认用户路径。

### 3.3 用户级采集账号

已经沉淀的设计文档：

```text
docs/architecture/用户级采集账号设计.md
```

关键结论：

- 不应该让所有用户共享一个全局 B 站 `SESSDATA`。
- 每个用户应该维护自己的站点凭据。
- 任务执行时只使用当前用户自己的凭据。
- 凭据需要加密存储、不可回显、日志脱敏、可删除、可重新授权。
- 当前本地单用户模式使用 `local-user`。
- 后续上线时需要接入真实用户体系。

本地 PostgreSQL 开发实例已经提供：

```text
docker-compose.postgres.yml
```

本地启动示例：

```bash
docker compose -f docker-compose.postgres.yml up -d postgres
export XIANWEN_DATABASE_URL='postgresql+psycopg://xianwen:xianwen_dev_password@127.0.0.1:54329/xianwen'
```

### 3.4 微信公众号文章采集

当前 master 已落地的是单篇微信公众号文章采集：

- 左侧入口：“公众号文章”。
- 支持 `mp.weixin.qq.com` 单篇文章链接。
- 采集正文、图片资源，并生成可进入现有 AI 总结流程的任务。
- 相关代码：

```text
src/main/python/xianwen/wechat_article.py
src/main/python/xianwen/api.py
frontend/src/components/Sidebar.vue
tests/test_wechat_article.py
```

注意：公众号历史文章批量拉取不应当在新 session 中默认认为已经完成。后续如果继续做，建议作为独立需求设计和验证。

### 3.5 飞书课程文档导出

已经新增工具：

```text
tools/export_web_docs_to_lark.py
tests/test_lark_export_style.py
```

用途：

- 采集外部文档站页面。
- 按原站目录结构写入飞书 Wiki。
- 为每个目录和正文页生成更统一的飞书排版。
- 自动修复内部链接，让飞书内文档之间互相跳转。
- 移除公开文档中的原文链接、来源提示、查看原文等信息。
- 本地保留 source URL 映射，方便维护者追溯。

本轮输出的映射文件：

```text
temp/web-doc-exports/20260715-220654/source-url-map.md
temp/web-doc-exports/20260715-220654/source-url-map.json
```

已验证：

- 飞书侧 236 个节点已覆盖更新，包括根节点、目录页和正文页。
- 公开飞书文档中已去掉“原文链接 / 原文页面 / 查看原文 / 本文由原网页采集生成”等来源信息。
- 本地映射文件继续保留源站 URL 和飞书 URL 对照。
- `tests/test_lark_export_style.py` 已覆盖来源移除、内部链接映射、目录页、正文页和“任务完成后”精细排版。

---

## 4. 运行和部署注意事项

README 中的部署脚本是可用路径。新 session 处理部署时应先读 README，再用项目脚本，不要直接绕过脚本手动安装。

已踩过的环境坑：

- Python 3.14 会导致 `onnxruntime` 依赖解析失败。
- 这个项目建议使用 Python 3.12 或 3.13。
- 默认 Node 20.11.1 对 Vite 7 太旧。
- Node 需要 `20.19+` 或 `22.12+`，本机可用 Node 22。
- 如果 B 站下载报多格式合并失败，需要确认 `ffmpeg` 已安装并在 PATH 中。

推荐启动路径：

```bash
./deploy一键部署.sh
./run一键启动.sh
```

默认访问：

```text
http://127.0.0.1:8000/
```

---

## 5. 后续开发边界

### 应该继续放在 XianWen 的能力

- 内容采集。
- 视频下载和解析。
- 字幕、转录、抽帧。
- AI 总结。
- 任务管理。
- 多站点凭据管理。
- 合集采集和聚合笔记生成。
- 本地或服务端任务执行能力。

### 不应该继续混进 XianWen 的能力

- 面向 C 端的课程学习平台。
- 用户学习进度。
- 课程售卖、会员、支付。
- 公开知识库站点前台。
- 面向中文用户的独立品牌学习产品。
- 基于飞书文档的内容站。

这些应当进入新的学习平台项目。

---

## 6. 新 session 建议开场提示词

可以直接把下面这段给新的 XianWen 开发主线 session：

```text
请先阅读 /Users/subin/Documents/Claude-Project/xian-wen-jixue-project/docs/handoff/xianwen-session-handoff.md，
再检查当前仓库状态。这个项目后续作为 XianWen 独立产品维护，不要把新的学习平台能力混进来。

如果涉及部署，请先阅读 README.md 并优先使用 deploy一键部署.sh 和 run一键启动.sh。
如果涉及用户凭据，请遵守 docs/architecture/用户级采集账号设计.md 的边界：凭据不可回显、日志脱敏、按用户隔离。
```

---

## 7. 开发提醒

- 任何凭据、Cookie、API Key 不要写入文档和提交。
- 新增站点采集能力时，优先抽成 Provider Adapter，不要把站点逻辑散落在 worker 中。
- 对用户可见的采集账号操作，以“从浏览器获取”为主流程。
- 对外服务时，全局 `SESSDATA` 只能作为系统兜底，不应成为所有用户的默认凭据。
- 新增采集能力后，要补测试，至少覆盖 URL 识别、凭据传递、失败提示和任务 payload。
- 飞书课程站相关工作应进入新产品项目，不要继续扩大 XianWen 的职责。
