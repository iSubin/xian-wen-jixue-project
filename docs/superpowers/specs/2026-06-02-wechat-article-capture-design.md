# WeChat Article Capture Design

## Purpose

XianWen is evolving toward a video learning note library first, then a broader personal knowledge system. The first non-video source will be single WeChat public-account article capture.

The goal is to let a user paste one `mp.weixin.qq.com` article URL, capture the article as text, generate a learning note through the existing LLM summary pipeline, and store the result in the same task/folder reading experience as video notes.

This feature is intentionally scoped as a first text-source adapter, not a general web crawler or full personal knowledge base.

## Product Decisions

- Product positioning: video learning note library.
- First non-video source: WeChat public-account article.
- First release scope: one article URL per submission.
- UI entry: a new explicit `公众号文章` entry near the existing start-processing actions, not automatic URL detection in the current video submission form.
- Task card: reuse the existing task card and add a `公众号` source label instead of introducing a separate article task list.
- Output surface: reuse the current right-side reading area.
- Source processing: capture can be multimodal at the edge, but the knowledge-processing layer consumes text-first normalized assets.

## Reference Skill

The local skill `/Users/subin/.codex/skills/wechat-article-export` is the reference implementation. Its script already demonstrates:

- HTTP request with browser-like headers.
- Metadata extraction from Open Graph tags.
- Body extraction from `#js_content`.
- Image discovery through `data-src` or `src`.
- Markdown conversion through `markdownify`.
- YAML front matter output.

XianWen should not depend on the external skill path at runtime. The implementation should internalize the reusable logic as a backend adapter so the app can run independently after deployment.

## User Flow

1. User clicks `公众号文章` in the sidebar.
2. A focused modal opens with:
   - WeChat article URL input.
   - Folder selector that defaults to the currently selected folder when available, otherwise root.
   - Summary mode selector using the same `standard | agent | auto` model as existing tasks.
   - Primary action `采集并生成笔记`.
3. Frontend validates that the URL host is `mp.weixin.qq.com`.
4. Backend captures the article.
5. Backend creates one task with `source_type = wechat_article`.
6. The task enters `SUMMARIZING` directly because no download or ASR step is required.
7. The existing LLM worker generates the learning note from the captured Markdown text.
8. The task appears in the existing task list with a `公众号` label.
9. The reading area shows:
   - `AI 总结`: generated learning note.
   - `原文`: captured article Markdown.
   - task metadata: source URL, author, publish time, image count.

## Architecture

```text
Frontend Article Modal
        |
        v
POST /articles/wechat
        |
        v
WechatArticleAdapter
        |
        v
NormalizedTextAsset
        |
        v
TaskModel(source_type=wechat_article)
        |
        v
Existing LLM Summary Worker
        |
        v
Existing Task Reading UI
```

## Backend Components

### WechatArticleAdapter

Add a backend module responsible for WeChat article capture. It should expose a small interface:

```text
capture(url: str) -> CapturedArticle
```

`CapturedArticle` should contain:

```text
source_type: "wechat_article"
source_url: str
title: str
author: str | None
publish_time: str | None
description: str | None
raw_markdown: str
plain_text: str
images: list[CapturedImage]
metadata: dict
```

`CapturedImage` should contain:

```text
original_url: str
local_path: str | None
markdown_path: str | None
status: "downloaded" | "skipped" | "failed"
```

### Capture Behavior

The adapter should:

- Accept only `https://mp.weixin.qq.com/...` URLs.
- Use browser-like request headers.
- Extract title, author, publish time, account name, and description from Open Graph tags when present.
- Fall back to `var createTime = 'yyyy-mm-dd hh:mm'` for publish time.
- Extract article body from `#js_content`.
- Convert the body HTML to Markdown.
- Download article images into XianWen-managed task assets when possible.
- Replace Markdown image references with local asset paths when images are downloaded.
- Keep the original source URL in metadata.

### Task Creation

Create an article task through a dedicated endpoint rather than overloading the video `POST /tasks/` endpoint.

Endpoint:

```text
POST /articles/wechat
```

Request:

```json
{
  "url": "https://mp.weixin.qq.com/s/example",
  "folder_id": null,
  "summary_mode": "auto"
}
```

Response should reuse the existing `Task` response shape after adding source metadata fields.

The backend should create a normal task with:

```text
video_url = source_url
source_type = "wechat_article"
source_url = source_url
title = captured title
transcript = captured Markdown
summary = ""
status = SUMMARIZING
progress = existing summarization start value
folder_id = requested folder
summary_mode = resolved summary mode
summary_meta includes author, publish_time, description, image_count
```

Using `video_url = source_url` is a compatibility bridge for the current schema. The implementation should also add explicit `source_type` and `source_url` task fields so future content sources do not remain tied to video naming.

### Summary Pipeline

Do not create a new article-specific LLM worker for the MVP. Reuse the existing summary worker by writing the captured Markdown into the intermediate text input path that the worker already consumes.

The article prompt can initially reuse the existing summarization prompt. If output quality is weak, a later iteration can add a text-source prompt that asks for:

- Article thesis.
- Key arguments.
- Important examples.
- Actionable takeaways.
- Terms or concepts worth retaining.
- Source-aware notes without hallucinated timestamps.

## Frontend Components

### Sidebar Entry

Add a `公众号文章` button beside the current source actions. It should use an article/document icon and open the article capture modal.

### WeChatArticleCaptureModal

The modal should include:

- URL input.
- Folder selector, defaulting to the currently selected folder when available and root otherwise.
- Summary mode selector.
- Validation message for non-WeChat URLs.
- Loading state while capture is running.
- Error state with actionable messages.

Primary button copy:

```text
采集并生成笔记
```

### Task Card Label

Extend the task card to show a small source label when `task.source_type === "wechat_article"`:

```text
公众号
```

This should be visually secondary to task status and should not resize or destabilize the existing card layout.

### Reading Area

The existing tabs remain:

- `AI 总结`
- `原文`

For article tasks:

- `原文` renders the captured Markdown article body.
- Timestamp-specific interactions should be hidden or no-op because article text has no video timestamp.
- Metadata should show source URL, author, publish time, and image count where available.

## Data Model

Add fields to the task model:

```text
source_type: string, default "video"
source_url: text | null
source_meta: text | null
```

`source_meta` stores JSON for source-specific metadata. For WeChat articles:

```json
{
  "author": "作者",
  "account": "公众号名称",
  "publish_time": "2026-04-09 16:58",
  "description": "描述",
  "image_count": 3
}
```

The existing `video_url` field remains during the MVP for compatibility. New code should read `source_url` when available and only fall back to `video_url`.

## Errors And User Messages

The backend should return clear errors:

- Invalid URL: `请输入有效的微信公众号文章链接`.
- HTTP failure: `公众号文章下载失败，请确认链接可访问后重试`.
- Missing body: `无法找到文章正文，文章可能需要登录、已删除、私密或被微信限制`.
- Empty Markdown: `文章正文为空，无法生成笔记`.
- Summary enqueue failure: `文章已采集，但生成笔记任务启动失败，请稍后重试`.

Image download failures should not fail the article task. Failed images should be skipped and counted in metadata.

## Security And Compliance

- Do not ask users for WeChat account passwords.
- Do not store cookies for WeChat article capture in the MVP.
- Do not log full private tokens or signed image URLs.
- Treat article source URL and downloaded content as user-submitted knowledge assets.
- Keep source attribution visible in task metadata and exported Markdown.

## Out Of Scope For MVP

- Batch WeChat article capture.
- WeChat login-state capture.
- Browser-extension capture.
- Official-account feed subscription.
- Article recommendation or scraping by account.
- Cross-article knowledge graph.
- PDF, OCR, generic webpage, or podcast sources.
- Rewriting the whole task model into a universal content-asset model.

## Testing

Backend tests should cover:

- URL validation.
- Metadata extraction from representative HTML.
- `#js_content` body extraction.
- `createTime` publish-time fallback.
- Markdown conversion.
- Image URL replacement with failed-image tolerance.
- Task creation with `source_type = wechat_article`.
- Existing video task creation remains unchanged.

Frontend tests should cover:

- Sidebar contains the `公众号文章` entry.
- Modal validates non-WeChat URLs.
- Modal posts to `/articles/wechat`.
- Task card renders the `公众号` label for article tasks.
- Existing video task cards render without the label.

Manual verification should include:

- One publicly accessible WeChat article can be captured and summarized.
- A non-WeChat URL is rejected before task creation.
- A deleted or inaccessible article shows a clear failure message.
- Existing video upload, video link submission, and collection capture still work.

## Rollout Plan

1. Add backend adapter and unit tests.
2. Add task source fields with schema migration compatibility for SQLite and PostgreSQL.
3. Add `POST /articles/wechat`.
4. Reuse existing LLM summary worker for article Markdown.
5. Add sidebar entry, modal, and task-card label.
6. Run backend tests, frontend static tests, and full frontend build.
7. Capture one real public WeChat article for manual validation.

## Acceptance Criteria

- User can create one WeChat article task from a dedicated `公众号文章` entry.
- The article task appears in the existing task list with a `公众号` label.
- The original article Markdown appears in `原文`.
- The generated learning note appears in `AI 总结`.
- Metadata includes source URL and available author/publish-time fields.
- Existing video and collection workflows are unaffected.
