# 先闻继学 Design System

> 构建页面前先检查 `design-system/pages/[page-name].md`。页面级规范存在时，以页面规范为准；否则遵循本文件。

**Project:** XianWen 先闻继学
**Updated:** 2026-08-09
**Category:** Knowledge library / editorial reading platform
**Direction:** 高饱和编辑部 / 数字书房

## 核心判断

先闻继学不是一套“工具面板”，而是一个让人愿意停留、阅读、回看的知识现场。视觉需要在第一眼建立记忆点，在长时间阅读时退到背景里。

- 用深蓝建立品牌锚点，用暖纸色承托阅读。
- 用珊瑚红、电光蓝、柠檬黄做大面积但有秩序的视觉撞色。
- 用衬线字体表达内容的重量，用无衬线字体维持产品操作清晰度。
- 形状可以夸张，信息结构不能夸张；装饰必须服务于导航、层级或记忆点。

## Color Palette

| Role | Hex | CSS Variable | Usage |
|------|-----|--------------|-------|
| Ink | `#17152A` | `--xw-ink` | 正文、标题、主要图标 |
| Ink Soft | `#5D596E` | `--xw-ink-soft` | 辅助文字、摘要 |
| Brand Navy | `#141A33` | `--xw-blue-deep` | 左侧导航、品牌底色 |
| Vermilion | `#F05A3C` | `--xw-accent` | 主行动、章节标记、视觉焦点 |
| Vermilion Deep | `#D53D2C` | `--xw-accent-strong` | hover、强调文字 |
| Electric Blue | `#2956D7` | `--xw-blue` | 选中态、辅助视觉块 |
| Lemon Yellow | `#FFD24D` | `--xw-yellow` | active tab、线条、提示 |
| Paper | `#FFFAF2` | `--xw-paper` | 阅读纸张、内容容器 |
| Canvas | `#F1ECE4` | `--xw-canvas` | 页面背景、阅读区 |
| Surface Muted | `#F8F1E8` | `--xw-surface-muted` | 搜索框、次级区域 |
| Border | `#E5D9CC` | `--xw-border` | 分隔线、输入框边界 |
| Success | `#0F766E` | `--xw-success` | 同步成功、完成状态 |
| Danger | `#B42318` | `--xw-danger` | 删除、错误状态 |

**Color rule:** 同一视图最多使用一个主色块、一个辅助色块和一个点缀色。鲜艳色彩负责建立节奏，不承担唯一的信息含义。

## Typography

| Role | Font | Rule |
|------|------|------|
| UI | `Noto Sans SC` | 导航、按钮、表单、状态 |
| Display | `Noto Serif SC` | 页面标题、空状态主文案 |
| Reading | `Noto Serif SC` | 正文、引用、长文阅读 |
| Editorial Latin | `Source Serif 4` | 英文副标题、编辑部标记 |
| Metadata | `JetBrains Mono` | 编号、时间、短标签 |

阅读正文建议 `17px–19px`、`1.9–2.05` 行高；页面主标题使用 `clamp()`，保持大字带来的冲击力，但不得挤压操作区。英文标签使用全大写与宽字距，中文不要强行加字母间距。

## Layout & Spacing

| Token | Value | Usage |
|-------|-------|-------|
| `--space-xs` | `4px` | 图标与文字、细小间距 |
| `--space-sm` | `8px` | 标签、紧凑控件 |
| `--space-md` | `16px` | 常规内边距 |
| `--space-lg` | `24px` | 模块间距 |
| `--space-xl` | `32px` | 内容块间距 |
| `--space-2xl` | `48px` | 区域间距 |
| `--space-3xl` | `64px` | 空状态、阅读页大留白 |

- 桌面端固定深蓝导航轨道，内容区使用暖纸色层次。
- 文库列表是扫描界面：标题、更新时间、选中态必须形成清晰纵向节奏。
- 阅读页是纸张界面：正文宽度优先，工具栏作为浮层，不抢正文注意力。
- 视觉大色块可以越界或错位，但不能遮挡可读文本和可操作控件。
- 移动端优先保证单列阅读与触控目标，禁止横向滚动。

## Shape, Shadow & Motion

| Token | Value | Usage |
|-------|-------|-------|
| `--xw-radius-sm` | `8px` | 小控件、标签 |
| `--xw-radius-md` | `12px` | 输入框、列表项 |
| `--xw-radius-lg` | `22px` | 纸张、浮动工具栏 |
| `--xw-shadow-sm` | `0 1px 2px rgba(42,31,25,.06), 0 8px 22px rgba(90,63,47,.06)` | 轻浮层 |
| `--xw-shadow-md` | `0 20px 48px rgba(55,40,31,.12), 0 3px 10px rgba(55,40,31,.06)` | 阅读纸张、重要卡片 |

- 交互过渡统一使用 `150ms–300ms`。
- hover 优先改变颜色、阴影或边框，不通过放大造成布局跳动。
- 纸张、色块和浮层的层级要稳定：品牌导航 > 主要内容 > 辅助工具 > 装饰。
- 必须保留清晰 focus ring，并尊重 `prefers-reduced-motion`。

## Component Rules

### Navigation

- 左侧 rail 使用 `--xw-blue-deep`，当前 tab 使用 `--xw-yellow`，形成“夜色中的书签”记忆点。
- 品牌区使用暖纸色；橙色标记与深蓝错位阴影是固定识别元素。
- tab 图标来自统一的 Phosphor 图标集，不使用 emoji。

### Buttons

- Primary：`--xw-accent` 背景、深蓝文字或白色文字，必要时加深蓝偏移阴影。
- Secondary：暖纸底色、`--xw-border-strong` 边界；hover 转为淡珊瑚色。
- Active：电光蓝或柠檬黄，只在当前状态使用，不把所有按钮都染成鲜艳色。
- 所有可点击元素必须有 `cursor: pointer`、hover、focus 和 disabled 状态。

### Library List

- 搜索区保持暖色低对比，结果列表使用白色纸面。
- 选中项使用电光蓝整行背景配白字；不可只依赖一条细边框表达选中。
- 新建动作使用珊瑚红，作为列表区唯一主 CTA。

### Reading Sheet

- 阅读纸张使用 `--xw-paper`，顶部固定出现珊瑚红 / 柠檬黄 / 电光蓝三段色带。
- 标题用 `Noto Serif SC`，章节标题左侧使用珊瑚红方形标记。
- 引用使用淡珊瑚底色与珊瑚色竖线；不使用厚重卡片包裹正文。
- 工具栏保持圆润、轻量和半透明，服务阅读动作而不是成为第二个导航。

### Empty State

- 空状态必须同时包含：编辑部编号、明确主句、下一步指引。
- 大色块只做构图和品牌记忆，不承载关键文字。
- 主标题允许错位和跨色块，但移动端仍需完整可读。

## Anti-Patterns

- ❌ 把每个模块都做成独立卡片，导致页面像拼贴仪表盘。
- ❌ 同时使用多套蓝色、圆角和阴影，破坏颜色与层级的统一。
- ❌ 用渐变、玻璃拟态或噪声背景替代内容层级。
- ❌ 用 emoji 代替图标；使用统一的 SVG 图标集。
- ❌ 只用颜色表达状态；同时提供文字、图标或位置变化。
- ❌ hover 改变布局、隐藏 focus 状态或制造横向滚动。
- ❌ 正文使用低于 `4.5:1` 对比度的灰色。

## Pre-Delivery Checklist

- [ ] 色彩遵循深蓝 + 暖纸 + 红 / 蓝 / 黄三色角色分工
- [ ] 标题、正文、UI、metadata 使用正确字体
- [ ] 所有按钮和列表项具有 hover / focus / disabled 状态
- [ ] 视觉大色块不遮挡内容或操作
- [ ] `prefers-reduced-motion` 已处理
- [ ] 已验证 375px、768px、1024px、1440px
- [ ] 移动端没有横向滚动，正文没有被固定工具栏遮挡
