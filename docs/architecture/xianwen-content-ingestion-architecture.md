# XianWen 统一知识采集与内容分发架构

状态：方向确认，渐进实施
日期：2026-07-18

## 1. 背景

XianWen 最初以长视频下载、转录和总结为核心，之后逐步增加了 Bilibili 合集、微信公众号文章、小鹅通、Homeway、本地文件、用户级采集账号和飞书文档导出等能力。

这些扩展说明 XianWen 已不再只是“视频总结工具”，而具备成为统一知识采集入口的基础。它需要从按单项功能扩展，逐渐转向按稳定的内容生命周期组织。

## 2. 产品定位

XianWen 的长期定位是：

> 面向个人和小团队的统一知识采集与加工中台，负责从外部来源获取内容，将其标准化、加工并交付给不同的知识消费端。

XianWen 负责：

- 外部网站、视频、文章和本地文件的采集。
- 用户级站点凭据管理。
- 正文提取、转录、清洗、抽帧、摘要和内容增强。
- 任务、合集、资源和内容产物管理。
- 向飞书、Markdown、内容包或其他系统发布标准化内容。

XianWen 不负责：

- 课程学习进度、收藏、练习和学习路径。
- 课程售卖、会员、支付和完整 LMS 能力。
- 特定消费端的页面体验和业务数据。

飞书课程 Web 学习平台是独立的内容消费方，不与 XianWen 共用内部数据库或业务实现。

## 3. 稳定的内容主线

```text
外部来源
  -> Provider 采集
  -> 统一内容模型
  -> Processor 加工
  -> 标准知识产物
  -> Publisher 发布
  -> 飞书 / 学习平台 / Markdown / 其他知识库
```

目录和模块应围绕这条主线组织，而不是继续按“视频功能、微信功能、飞书功能”横向堆积。

## 4. 核心模块边界

### 4.1 Provider：采集来源

Provider 只负责识别来源、获取原始内容和返回统一采集结果，不决定内容如何总结或发布到哪里。

首批 Provider：

- Bilibili
- 微信公众号
- 小鹅通
- Homeway
- 本地音视频和文件

后续增加知乎、YouTube、论坛或播客时，应新增 Provider，而不是修改所有任务流程。

### 4.2 Domain：统一内容模型

核心领域对象包括：

- `SourceRef`：来源 URL、站点、作者和采集时间。
- `ContentItem`：标准化后的文章、视频、音频或文档。
- `Artifact`：逐字稿、摘要、Markdown、截图和附件等产物。
- `Collection`：合集、课程或批量采集任务。
- `Publication`：一次对外发布及其目标、版本和状态。
- `Credential`：按用户隔离的站点授权信息。

来源差异应在进入 `ContentItem` 前被吸收，消费方不应依赖某个站点的任务字段。

### 4.3 Processor：内容加工

Processor 负责来源无关的内容加工能力：

- 正文提取与标准化。
- 音视频转录。
- 图片、附件和视频帧处理。
- 内容分块、摘要和组装。
- 元数据补全与内容增强。

文章可以跳过转录，视频可以走完整流水线，但最终都应形成一致的内容与产物模型。

### 4.4 Publisher：内容交付

Publisher 负责把标准内容交付到消费端：

- 飞书 Wiki / Docx。
- Markdown 文件。
- 版本化 Content Package。
- Webhook 或外部 API。
- 后续可能增加的 Notion、语雀或对象存储。

Publisher 不应读取 Provider 的内部状态，也不应直接承担采集逻辑。

## 5. 目标目录结构

以下结构是渐进迁移目标，不要求一次性完成：

```text
src/main/python/xianwen/
  api/
    routers/
    schemas/
    dependencies.py
  domain/
    content.py
    artifact.py
    task.py
    collection.py
    publication.py
    credential.py
  application/
    capture_content.py
    process_content.py
    publish_content.py
    pipelines/
  providers/
    base.py
    registry.py
    bilibili/
    wechat/
    xiaoet/
    homeway/
    local_file/
  processors/
    extraction/
    transcription/
    summarization/
    enrichment/
    normalization/
  publishers/
    base.py
    markdown/
    lark/
    content_package/
    webhook/
  infrastructure/
    database/
    storage/
    credentials/
    browser/
    queue/
  workers/
  config/
  shared/
```

仓库级目录逐步规范为：

```text
frontend/        Vue 管理和采集界面
contracts/       与消费方共享的版本化契约
tests/           unit / integration / contract / e2e
docs/            正式文档
data/            需要长期保留的本地数据
runtime/         cache / work / logs 等可再生数据
exports/         用户可见的最终导出物
```

## 6. Git / Obsidian 内容契约

Git 文库首先服务于人类阅读，不把运行态字段拆成大量 JSON 文件。每份内容只在 `内容/` 中保存一次，目录使用采集来源提供的原始标题；藏经阁和后续专题只通过 WikiLink 组织关系：

```text
先闻继学/
  内容/<原始标题>/
    <原始标题>.md
    原始逐字稿.md | 原始正文.md
    assets/
  藏经阁/<目录层级>/_目录.md
  专题/                         # 后续专题索引，不复制正文
  _索引.md
  .xianwen-manifest.json
```

- 主文档使用少量 YAML Properties 保存来源 URL、作者、发布时间、采集时间和 `xianwen_id`。
- 原始逐字稿或提炼后的原始正文与整理稿分开，保持人类可读；原始音视频、原始 HTML、来源图片和物料 manifest 永不进入普通 Git。
- Git 对二进制资产采用 fail-closed：只发布 `content_assets.role=derived` 且被正文引用的必要衍生资产；未登记资产和 `role=original` 资产均不发布。
- 内容目录名在首次发布后写入 manifest 并保持稳定，藏经阁分类变化不移动正文。
- `.xianwen-manifest.json` 只负责受管文件 hash 与稳定目录映射，不作为阅读入口。
- 用户新增文件不纳入 manifest；用户修改过的受管文件报告冲突并保留外部版本。

学习平台不应直接读取 `xianwen.db`。如后续消费方确实需要机器契约，可以新增独立的 Content Package Publisher，但不应让机器格式污染默认的 Git / Obsidian 文库。

## 7. 数据目录原则

本地数据按生命周期分为三层，业务代码统一通过 `storage.py` 获取路径，不再直接写入根目录 `temp/` 或 `download/`：

```text
data/                                      # 持久层：不得自动删除
  originals/
    <provider>/<YYYY>/<原始标题>__<内容ID>/
      source.<ext>                         # 原始视频或音频
      article.html                         # 原始文章页面
      original.md                          # 忠实转换的原始正文
      manifest.json                        # URL、大小、SHA-256、物料清单
  assets/<task_id>/
    images/                                # 原文图片
    homeway/<item_id>/                     # 投研大师原文图片
    frames/                                # 被知识文档引用的关键帧
  migrations/                              # 数据迁移报告

runtime/                                   # 运行层：可再生、按任务隔离
  downloads/<task_id>/                     # yt-dlp 下载中转
  uploads/<task_id>/                       # 上传接收中转
  tasks/<task_id>/
    audio.mp3                              # 转录用衍生音频
    transcript.txt                         # 中间逐字稿
    summary.md                             # 中间整理稿
  debug/chunks/                            # 可选调试输出

exports/                                   # 用户明确生成的交付结果
```

其中：

- `data/originals/` 与 `content_assets` 表共同构成原始物料账本；每项记录保存相对路径、角色、类型、大小、SHA-256、来源 URL 和状态。
- 在线视频先下载到 `runtime/downloads/<task_id>/`，校验后原子移动到 `data/originals/`，后续转录始终读取固化后的文件。
- 微信文章保存原始 HTML、原始 Markdown 和图片；投研大师保存原始 HTML、Markdown 和图片。原文图片与知识文档引用资产进入持久层。
- `runtime/` 只保存下载/上传中转和可再生衍生物；任一任务不与其他任务平铺混放。
- `exports/`：用户明确生成并需要交付的结果。
- 删除知识任务默认不删除 `content_assets` 和物理原始物料。未来若增加“删除原始物料”，必须是独立、明确确认的操作。
- 普通 Git/Obsidian 发布只包含采集后的 Markdown、原始正文/逐字稿、整理稿，以及明确登记为 `derived` 的必要衍生资产；原始物料全部留在本地。

历史数据使用 `python tools/migrate_storage_layout.py` 先 dry-run，再以 `--apply` 执行；迁移报告写入 `data/migrations/storage-layout-v1.json`。

## 8. 渐进迁移顺序

1. 定义 `ContentItem`、`SourceRef`、`Artifact` 和 `Publication`。
2. 建立 Provider 接口与注册表。
3. 先迁移相对独立的微信公众号采集模块，验证模式可行。
4. 将现有大型 `api.py` 按路由和 schema 拆分，保持 API 地址不变。
5. 建立 `content-package/v1` 契约与契约测试。
6. 将飞书导出从一次性工具逐步收敛为 Lark Publisher。
7. 最后整理数据库、持久资源和运行时目录。

每个阶段都应保持现有部署脚本、启动脚本和主要用户流程可运行，避免一次性重写。

## 9. 当前明确不做

- 不拆成微服务。
- 不把学习平台放进 XianWen 前端。
- 不一次性移动全部后端代码。
- 不让消费方依赖 XianWen 内部数据库。
- 不为尚未出现的来源和发布端预先实现复杂插件系统。

## 10. 架构判断

当前最合适的形态是模块化单体：保留现有技术栈和部署方式，通过清晰的 Provider、Domain、Processor 和 Publisher 边界获得扩展能力。只有在任务执行、部署规模或团队协作出现明确压力后，才考虑把 Worker 或发布服务拆成独立进程。
