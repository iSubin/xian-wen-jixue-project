# 先闻继学「内容订阅」产品设计：Homeway 讲师订阅首个落地

状态：已实现；2026-08-22 调整为一帖一文稿
日期：2026-08-14
首个订阅源：投研大师 / Homeway `GraphicLecturer`

> **2026-08-22 产品调整**：本文最初设计的“每日内容包”已由“一帖一文稿、日期只做目录索引”取代。当前正文实体使用 `source_type = homeway_post`，归档结构为 `订阅 / 投研大师 / 讲师 / YYYY-MM-DD / 独立帖子`；确认同日帖子及图片全部迁移完成后，旧的 `homeway_daily_digest` 和重复图片副本会被清除。每篇帖子的原始 HTML、Markdown 等响应继续仅在本地按帖子保存，Git/Obsidian 只发布单篇 Markdown 正文、必要元数据以及日期目录索引。

## 1. 产品判断

先闻继学应增加一种区别于“单次采集”和“合集采集”的长期能力：

> 用户订阅一个持续更新的内容来源，先闻继学按计划发现新增内容、保存原文、形成每日内容包，并继续交付到藏经阁、Git 和 Obsidian。

它不是一个只服务 Homeway 的定时脚本。Homeway 是第一个 Adapter，用来验证“持续来源 → 原子条目 → 每日内容包 → 知识库发布”这条稳定产品链路。

### 1.1 三种采集对象的区别

| 对象 | 生命周期 | 典型输入 | 结束条件 |
|---|---|---|---|
| 单次采集 `Task` | 一次性 | 一条视频或文章 URL | 单条内容处理完成 |
| 合集 `Collection` | 一次性批量 | 一组已经存在的内容 | 所有选中条目处理完成 |
| 订阅 `Subscription` | 长期存在 | 讲师主页、作者主页、Feed | 用户暂停或取消订阅 |

不能把订阅实现成“每天重新创建一个合集”。合集没有持久游标、权限失效、周期运行和跨日去重语义，强行复用会导致重复任务与状态混乱。

## 2. 首期目标

用户粘贴一个 Homeway 讲师主页，例如：

```text
https://tyds.homeway.com.cn/#/GraphicLecturer?lecturerId=1669029704
```

先闻继学完成以下工作：

1. 识别讲师并预览订阅范围。
2. 绑定用户已有的 Homeway `web_qtstr` 账号。
3. 在计划时间内增量发现讲师发布的文字内容。
4. 对每个站点内容 ID 做幂等采集，保留正文、图片、发布时间和来源信息。
5. 按讲师和自然日形成一份每日内容包。
6. 可选生成忠实于来源的整理稿。
7. 每日内容包进入藏经阁，并通过现有 Git Publisher 自动发布到 Obsidian 文库。
8. 登录过期、权限不足或站点异常时，不丢失已经采集的内容，并给用户明确状态。

## 3. 明确不做

首期不包括：

- 绕过登录、付费墙、合同签署、风险测评或其他访问限制。
- 采集用户账号无权阅读的付费正文。
- 股票交易、自动跟单、投资建议或站内互动。
- 秒级实时推送；首期是周期轮询。
- 将每一条短消息发布成一个 Git 目录。
- Git / Obsidian 到先闻继学数据库的反向同步。
- 同时建设所有网站的订阅 Adapter。

## 4. 核心产品对象

### 4.1 `ContentSubscription`：订阅源

表示用户长期关注的一个外部内容来源。

建议字段：

```text
id
user_id
provider                     # homeway
source_type                  # homeway_lecturer
source_url
external_source_id           # lecturerId
display_name                 # 枪大侠
connected_account_id
folder_id
status
poll_interval_minutes
active_window_start
active_window_end
digest_time
timezone                     # Asia/Shanghai
initial_sync_mode
last_cursor
last_polled_at
last_success_at
next_poll_at
last_error
lease_owner
lease_expires_at
created_at
updated_at
```

首期 `initial_sync_mode` 提供三个选择：

- `from_now`：只订阅创建后的新内容，默认推荐。
- `today`：补采当天已经发布的内容。
- `last_7_days`：补采最近七天，用于首次建立上下文。

不默认提供“全部历史”，避免首次操作产生无法预估的请求量和内容规模。

### 4.2 `SubscriptionItem`：订阅条目

表示站点发布的一条原子内容。它是准确采集、去重和审计的基础，不直接等于 Git 中的一篇笔记。

建议字段：

```text
id
subscription_id
provider
external_item_id             # Homeway lecturer_feed id
source_url
published_at
source_updated_at
first_seen_at
last_seen_at
captured_at
content_hash
preview_text
raw_html
raw_markdown
image_manifest
access_scope                 # public | entitled | locked | unknown
capture_status               # discovered | captured | locked | failed
failure_code
failure_detail
digest_date
digest_task_id
source_missing_at
created_at
updated_at
```

数据库唯一约束：

```text
UNIQUE(subscription_id, external_item_id)
```

`published_at` 只用于分页和分组，不作为去重键。遇到同秒发布、置顶、重新排序或回填历史内容时，仍以站点内容 ID 为准。

### 4.3 `SubscriptionRun`：一次运行

每次定时或手动拉取都留下轻量运行记录，以便判断“今天是否真的采集过”，而不是只看最后一个错误字符串。

建议字段：

```text
id
subscription_id
trigger                      # scheduled | manual | reconciliation
status                       # running | success | partial | failed
started_at
finished_at
discovered_count
captured_count
updated_count
locked_count
failed_count
cursor_before
cursor_after
error_code
error_detail
```

运行记录保留最近一段时间即可，不进入 Git 文库。

### 4.4 `DailyContentPackage`：每日内容包

首期不新增第四张表，而是复用一个可进入藏经阁的 `Task`：

```text
source_type = homeway_daily_digest
source_url = 讲师主页
title = 枪大侠｜2026-08-14
transcript = 当日全部获授权原文的确定性 Markdown
summary = 可选的每日整理稿
source_meta = subscription_id、日期、item_ids、条目数、内容版本
library_visible = true
```

订阅条目继续保留原子性；每日内容包是人类阅读和发布层的聚合视图。

## 5. Homeway Adapter 契约

Homeway 订阅能力应作为独立 Adapter，而不是继续堆进视频 resolver：

```text
recognize_subscription_url(url)
preview_subscription(url, credential)
validate_credential(credential)
list_items(source_id, cursor, credential)
capture_item(item_id, credential)
redact_secret(value)
```

### 5.1 列表发现

已验证的 Homeway 内容列表具备：

- `lecturer_id`：讲师 ID。
- `mainMenuId` / `subMenuId`：栏目和内容类型。
- `published_at`：向历史翻页的时间游标。
- 内容 ID、发布时间、预览文本、图片、标签、内容权限标记。

轮询算法：

1. 从最新内容开始读取。
2. 对每条内容按 `external_item_id` upsert。
3. 遇到已经见过的内容后仍保留一页重叠窗口，避免同时间戳或重新排序造成遗漏。
4. 达到本次同步的时间边界或空页后停止。
5. 每晚额外重读最近两天内容，用 `content_hash` 识别修改。

不能把 `published_at` 当成严格递增主键。

### 5.2 单条详情

单条详情需要标准化：

- 公开正文与已授权正文。
- HTML 到 Markdown 的转换。
- 正文实际引用的图片。
- 作者、发布时间、标签和免责声明。
- 稳定的原始内容 URL。

只下载正文实际引用的图片；广告图、头像、推荐课程和页面装饰不进入内容资产。

### 5.3 权限判定

权限必须 fail closed（默认拒绝）：

1. 使用用户绑定的 Homeway Connected Account 请求。
2. 只有站点返回明确的正向可读信号时，才保存权限正文。
3. 如果响应同时出现正文数据和“无权阅读”信号，以无权阅读为准。
4. 无法判断时标记为 `unknown`，不得发布正文。
5. 锁定内容只保存 ID、发布时间和状态，不保存或发布受限正文。

不允许利用站点实现缺陷，把“接口返回了字段”等同于用户获得了阅读授权。

## 6. 调度策略

### 6.1 默认策略

Homeway 金融内容更新频繁，默认建议：

```text
08:30–18:30  每 15 分钟增量轮询
20:30        当日全量补漏并形成每日内容包
非活跃时段   不高频轮询
```

界面只向普通用户展示：

- 自动订阅开关。
- 每日内容包生成时间。
- “立即检查更新”。

轮询间隔和活跃时间放入高级设置，不暴露 cron 表达式。

### 6.2 持久化与进程恢复

调度事实保存在数据库，不只存在内存定时器中：

- 应用启动后扫描 `next_poll_at <= now` 的有效订阅。
- 通过短租约避免多进程重复执行同一订阅。
- 运行完成后计算新的 `next_poll_at`。
- 应用停机期间错过的任务在恢复后执行一次补偿检查，不补跑每个历史时间点。

先闻继学必须通过 Docker Compose、`launchd` 或其他常驻方式运行；终端退出即停止的前台进程不能承诺“每日订阅”。

## 7. 每日内容包设计

### 7.1 为什么不“一条消息一个目录”

Homeway 短消息通常没有稳定标题，一天可能发布数十条。如果直接映射成普通内容：

- 会生成大量用首句伪造的目录标题。
- 藏经阁和 Git 提交噪音过高。
- Obsidian 更难形成当天的连续阅读体验。
- 每次轮询都可能触发多次 Git commit。

因此把“讲师在一个自然日内发布的内容集合”定义为这一来源的原始内容单元。标题是确定性的来源包标题，不由 AI 生成。

### 7.2 Git / Obsidian 结构

```text
内容/
  枪大侠｜2026-08-14/
    枪大侠｜2026-08-14.md
    原始正文.md
    assets/
藏经阁/
  订阅/
    投研大师/
      枪大侠/
        _目录.md
专题/
  # 后续只链接每日内容包，不复制正文
```

### 7.3 `原始正文.md`

按发布时间正序排列，每条内容保留：

```markdown
## 09:20｜波段早评

- 来源 ID：198470
- 发布时间：2026-08-14 09:20:09
- 原始链接：...
- 标签：实战圈·机会点评

原始正文……

相关图片……
```

要求：

- 不把多条内容改写成一段“仿原文”。
- 不遗漏条目 ID、时间和来源。
- 图片靠近原始条目，不建立独立素材索引文件。
- 相同免责声明可在文末合并一次，但必须保留其来源属性。

### 7.4 主文档

主文档默认包含：

- 今日内容数量和覆盖时间。
- 来源讲师与原始主页。
- 确定性的条目目录。
- 可选 AI 整理稿。
- 指向 `[[原始正文]]` 的入口。

AI 整理稿必须：

- 把讲师观点写成“来源观点”，不伪装成系统事实。
- 区分短线、波段、复盘等原始标签。
- 保留观点变化和时间顺序。
- 不生成交易指令，不补充来源中不存在的价格或结论。
- 明确提示内容仅作知识整理，不构成投资建议。

即使 AI 总结失败，只要原始内容包组装成功，当日采集仍然成功；总结可独立重试。

### 7.5 发布时机

- 日内轮询只更新数据库原子条目，不为每条内容触发 Git push。
- 到达 `digest_time` 后组装每日内容包并完成一次 Git 发布。
- 晚间补漏发现遗漏后，在同一次组装中纳入。
- 次日发现前一日内容被修改时，更新对应内容包；源站删除不自动删除已经合法采集的内容，只标记来源已不可见。

## 8. 用户流程

### 8.1 创建订阅

1. 用户进入侧边栏“内容订阅”。
2. 点击“添加订阅”，粘贴讲师主页。
3. 系统识别来源和讲师，显示：
   - 讲师名称。
   - 来源平台。
   - 可订阅的文字栏目。
   - 当前账号状态。
4. 用户选择首次同步范围和每日内容包时间。
5. 用户确认后创建订阅。
6. 系统立即执行一次预览或首次同步，并显示结果。

### 8.2 订阅中心

每张订阅卡只显示必要信息：

- 讲师与平台。
- `正常`、`已暂停`、`需要重新登录` 或 `异常`。
- 今日新增条目数。
- 最近成功时间。
- 下一次检查时间。
- “立即检查”“暂停/继续”操作。

不向普通用户展示游标、租约、内部任务 ID 或原始错误堆栈。

### 8.3 取消订阅

取消只停止未来采集：

- 保留已经采集的条目。
- 保留已经生成的每日内容包。
- 保留 Git / Obsidian 中的历史内容。
- 界面必须明确说明不会删除历史资料。

## 9. 状态与恢复

### 9.1 订阅状态

```text
ACTIVE
PAUSED
AUTH_REQUIRED
DEGRADED
ERROR
```

- `ACTIVE`：最近运行正常。
- `PAUSED`：用户主动暂停。
- `AUTH_REQUIRED`：登录失效或权限需要用户处理。
- `DEGRADED`：部分条目失败，但订阅仍可继续。
- `ERROR`：连续失败，且当前无法可靠采集。

一次网络失败不应立刻把订阅永久置为 `ERROR`。短暂错误指数退避；权限错误直接进入 `AUTH_REQUIRED`，避免无意义重试。

### 9.2 条目状态

```text
DISCOVERED -> CAPTURED
DISCOVERED -> LOCKED
DISCOVERED -> FAILED -> CAPTURED
CAPTURED -> CAPTURED_UPDATED
```

`LOCKED` 条目在用户恢复合法访问权限后允许重新检查。

### 9.3 与现有任务状态解耦

- 订阅运行失败不修改已经完成的每日内容包。
- 单条图片失败可形成 `PARTIAL`，正文仍保存。
- AI 总结失败不等于原始内容采集失败。
- Git 发布失败不等于订阅采集失败，继续沿用现有可重试 Publisher 状态。

## 10. API 草案

```text
POST   /subscriptions/preview
POST   /subscriptions
GET    /subscriptions
GET    /subscriptions/{subscription_id}
PATCH  /subscriptions/{subscription_id}
DELETE /subscriptions/{subscription_id}
POST   /subscriptions/{subscription_id}/poll
GET    /subscriptions/{subscription_id}/runs
```

WebSocket 事件：

```text
subscription_update
subscription_run_update
```

`DELETE` 的产品语义是停止订阅，不级联删除内容。若以后需要清除历史数据，必须提供独立、带明确影响范围的操作。

## 11. 与现有能力的复用关系

可以复用：

- Connected Account 的用户级加密凭据存储。
- Homeway `web_qtstr` 导入能力。
- 文章 Markdown、图片资产和任务字段。
- Folder / 藏经阁组织。
- 现有摘要 Worker。
- Git / Obsidian 自动归档和冲突保护。

不能直接复用为领域对象：

- `CollectionJob`：它没有长期调度和跨运行去重语义。
- `HomewayVideoResolver`：它只负责单条视频媒体解析。
- 内存 `asyncio.Task`：它不能作为持久订阅事实。

首期保持模块化单体，不引入微服务和独立消息系统。

## 12. 安全、合规与内容边界

- 只采集用户自己的合法账号可以阅读的内容。
- 不记录或发布 `web_qtstr`、请求 token、临时签名 URL。
- 日志中的 URL 和响应错误必须脱敏。
- Git 文库不包含账号状态、权限判断细节和运行错误。
- 用户暂停或重新登录不应泄露历史凭据。
- 站点接口变化时停止受影响的采集，不使用模糊 DOM 抓取静默生成残缺内容。
- 订阅内容用于个人知识管理时仍应保留来源、作者和免责声明，不把采集结果包装成先闻继学原创内容。

## 13. MVP 验收标准

### 13.1 功能验收

1. 输入合法 `GraphicLecturer` URL 能识别 `lecturerId` 和讲师名称。
2. 无 Homeway 账号或登录失效时，不创建伪成功订阅。
3. 首次同步范围可选 `from_now`、`today`、`last_7_days`。
4. 至少跨两页枚举历史内容，无重复、无游标死循环。
5. 同一内容 ID 连续发现两次，只产生一条 `SubscriptionItem`。
6. 内容改变时更新 hash 和正文，不创建重复条目。
7. 只有正向权限确认的正文才进入数据库和每日内容包。
8. 图片下载失败不会丢失正文，并能在运行结果中看到部分失败。
9. 一天三十条短消息只生成一个 Git 内容目录。
10. 每日内容包中的条目数量、ID、发布时间与已采集原子条目一致。
11. 应用重启后订阅计划恢复，不需要用户重新创建。
12. 两个进程同时扫描到期订阅时，只有一个获得执行租约。
13. 暂停和取消订阅不会删除历史内容。
14. Git 失败不会把已采集条目标记为失败。

### 13.2 安全验收

1. API、WebSocket、日志和 Git 中均不出现完整 `web_qtstr`。
2. 未授权或权限不明的正文不会落库、落盘或进入摘要输入。
3. 错误信息不包含请求 token、签名 URL 或响应中的敏感字段。
4. 用户级订阅只能使用同一用户的 Connected Account。

### 13.3 一日真实试点

使用用户有合法权限的测试账号完成一个完整活跃日：

- 日内自动运行按计划触发。
- 20:30 对照站点当天列表，已授权文字条目数量一致。
- 无重复条目。
- 正文和实际引用图片可读。
- Git 中只有一个当日内容目录和一次正常的最终发布。
- 次日首次轮询不重复创建前一日条目。
- 人工令登录态失效后，订阅进入 `AUTH_REQUIRED` 并可在重新绑定后恢复。

配置成功不能代替这一日真实证据。

## 14. 实现顺序

1. Homeway Lecturer Adapter 与固定响应 fixture 测试。
2. `ContentSubscription`、`SubscriptionItem`、`SubscriptionRun` 数据表及迁移。
3. 手动预览、创建订阅和“立即检查更新” API。
4. 权限判定、详情转 Markdown、图片下载和幂等 upsert。
5. 每日内容包组装，复用现有 Task、Folder 和 Git Publisher。
6. 数据库驱动的调度器、租约、退避和启动恢复。
7. 订阅中心前端、状态提示和重新登录入口。
8. 单元测试、集成测试、重启恢复测试和并发租约测试。
9. 使用真实授权账号进行一日受控试点。

## 15. 后续扩展

Homeway 验证完成后，下一批来源可以复用同一订阅领域模型：

- 微信公众号作者更新。
- YouTube / Bilibili UP 主更新。
- 播客 Feed。
- 网站栏目或研究机构文章列表。

新增来源只实现 Adapter，不改变订阅、调度、原子条目、每日内容包和 Publisher 的核心关系。

## 16. 最终产品定义

> 内容订阅不是“定时抓网页”，而是先闻继学对持续变化内容源的长期承诺：知道上次采到了哪里，知道哪些内容有权读取，知道哪些条目已经保存，并每天交付一份稳定、可追溯、适合人类阅读的知识产物。
