# WeChat Article Capture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dedicated single-article WeChat public-account capture flow that turns one `mp.weixin.qq.com` URL into a normal ShengWen learning-note task.

**Architecture:** Internalize the reusable logic from the local `wechat-article-export` skill as a focused backend adapter. Create article tasks through a dedicated `/articles/wechat` endpoint, store captured Markdown in the existing `transcript` field, and enqueue the current LLM worker directly for summarization. Add a separate frontend entry and modal while keeping existing video submission stable.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, unittest, requests, beautifulsoup4, lxml, markdownify, Vue 3, TypeScript, Axios, Vite.

---

## File Structure

Backend:

- Modify `requirements.txt`: add `requests`, `beautifulsoup4`, `lxml`, `markdownify`.
- Modify `src/main/python/sheng_wen/db.py`: add `source_type`, `source_url`, and `source_meta` to task persistence, schema migration, and JSON fallback.
- Create `src/main/python/sheng_wen/wechat_article.py`: WeChat article adapter, metadata extraction, Markdown conversion, image handling.
- Modify `src/main/python/sheng_wen/api.py`: add request model, response fields, `/articles/wechat` endpoint, and LLM enqueue helper.
- Test with `tests/test_wechat_article.py`: adapter and persistence tests.

Frontend:

- Modify `frontend/src/types.ts`: add task source fields and WeChat article request type.
- Modify `frontend/src/composables/useTaskViewModel.ts`: add `createWechatArticleTask` and `isCreatingWechatArticle`.
- Create `frontend/src/components/WechatArticleCaptureModal.vue`: dedicated article capture modal.
- Modify `frontend/src/components/Sidebar.vue`: add `公众号文章` button and emit.
- Modify `frontend/src/components/FolderBrowser/TaskCard.vue`: show `公众号` label for article tasks.
- Modify `frontend/src/App.vue`: wire modal state and success toast.
- Test with `frontend/src/components/WechatArticleCaptureModal.test.mjs` and extend existing package scripts.

Docs:

- Modify `README.md` lightly only if the implementation ships in this same pass. Keep it short: one line in supported inputs and one line in usage notes.

---

## Task 1: Task Source Fields And Dependencies

**Files:**

- Modify: `requirements.txt`
- Modify: `src/main/python/sheng_wen/db.py`
- Test: `tests/test_wechat_article.py`

- [ ] **Step 1: Write failing persistence tests**

Add `tests/test_wechat_article.py` with this initial content:

```python
import json
import os
import sys
import tempfile
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src", "main", "python"))

from sheng_wen.db import TaskDB, TaskStatus


class TaskSourceFieldsPersistenceTest(unittest.TestCase):
    def test_task_source_fields_round_trip_in_sqlite(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            database = TaskDB(database_url=f"sqlite:///{os.path.join(tmpdir, 'test.db')}")
            source_meta = {
                "author": "作者",
                "account": "公众号",
                "publish_time": "2026-04-09 16:58",
                "image_count": 2,
            }

            database.save_task(
                "article-task",
                {
                    "id": "article-task",
                    "video_url": "https://mp.weixin.qq.com/s/example",
                    "source_type": "wechat_article",
                    "source_url": "https://mp.weixin.qq.com/s/example",
                    "source_meta": json.dumps(source_meta, ensure_ascii=False),
                    "status": TaskStatus.SUMMARIZING,
                    "progress": 0.0,
                    "title": "文章标题",
                    "transcript": "# 文章标题\n\n正文",
                    "summary": "",
                },
            )

            task = database.get_task("article-task")

            self.assertEqual(task["source_type"], "wechat_article")
            self.assertEqual(task["source_url"], "https://mp.weixin.qq.com/s/example")
            self.assertEqual(json.loads(task["source_meta"])["account"], "公众号")

    def test_regular_video_task_defaults_to_video_source_type(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            database = TaskDB(database_url=f"sqlite:///{os.path.join(tmpdir, 'test.db')}")
            database.save_task(
                "video-task",
                {
                    "id": "video-task",
                    "video_url": "https://www.bilibili.com/video/BV123",
                    "status": TaskStatus.PENDING,
                    "progress": 0.0,
                },
            )

            task = database.get_task("video-task")

            self.assertEqual(task["source_type"], "video")
            self.assertEqual(task["source_url"], "https://www.bilibili.com/video/BV123")
            self.assertIsNone(task["source_meta"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python -m unittest tests.test_wechat_article -v
```

Expected: fails because `source_type`, `source_url`, and `source_meta` are missing from task dictionaries.

- [ ] **Step 3: Add dependencies**

Append these lines to `requirements.txt`:

```text
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=4.9.0
markdownify>=0.11.6
```

- [ ] **Step 4: Add task source columns and schema migration**

In `src/main/python/sheng_wen/db.py`, update `TaskModel`:

```python
    source_type = Column(String, nullable=False, default="video")
    source_url = Column(Text, nullable=True)
    source_meta = Column(Text, nullable=True)
```

Update `TaskModel.to_dict()`:

```python
            "source_type": self.source_type or "video",
            "source_url": self.source_url or self.video_url,
            "source_meta": self.source_meta,
```

Extend `_ensure_schema()` to detect and add columns:

```python
            has_source_type = "source_type" in columns
            has_source_url = "source_url" in columns
            has_source_meta = "source_meta" in columns
```

Include these flags in the early return condition, then add migrations:

```python
                if not has_source_type:
                    conn.execute(text("ALTER TABLE tasks ADD COLUMN source_type VARCHAR"))
                    conn.execute(text("UPDATE tasks SET source_type = 'video' WHERE source_type IS NULL"))
                    logger.info("Database schema updated: added tasks.source_type")
                if not has_source_url:
                    conn.execute(text("ALTER TABLE tasks ADD COLUMN source_url TEXT"))
                    conn.execute(text("UPDATE tasks SET source_url = video_url WHERE source_url IS NULL"))
                    logger.info("Database schema updated: added tasks.source_url")
                if not has_source_meta:
                    conn.execute(text("ALTER TABLE tasks ADD COLUMN source_meta TEXT"))
                    logger.info("Database schema updated: added tasks.source_meta")
```

When migrating from `tasks.json`, pass:

```python
                    source_type=task_data.get("source_type") or "video",
                    source_url=task_data.get("source_url") or task_data.get("video_url"),
                    source_meta=task_data.get("source_meta"),
```

Before creating a new `TaskModel` in `save_task()`, normalize defaults:

```python
                    task_data_copy.setdefault("source_type", "video")
                    task_data_copy.setdefault("source_url", task_data_copy.get("video_url"))
                    task_data_copy.setdefault("source_meta", None)
```

In the JSON fallback `_deserialize_task()`, add:

```python
        data.setdefault("source_type", "video")
        data.setdefault("source_url", data.get("video_url"))
        data.setdefault("source_meta", None)
```

- [ ] **Step 5: Run persistence tests**

Run:

```bash
.venv/bin/python -m unittest tests.test_wechat_article -v
```

Expected: both tests pass.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt src/main/python/sheng_wen/db.py tests/test_wechat_article.py
git commit -m "feat: add task source metadata"
```

---

## Task 2: WeChat Article Adapter

**Files:**

- Create: `src/main/python/sheng_wen/wechat_article.py`
- Modify: `tests/test_wechat_article.py`

- [ ] **Step 1: Add adapter tests**

Append these tests to `tests/test_wechat_article.py`:

```python
from sheng_wen.wechat_article import (
    WechatArticleCaptureError,
    capture_wechat_article_from_html,
    is_wechat_article_url,
)


SAMPLE_WECHAT_HTML = """
<html>
  <head>
    <meta property="og:title" content="测试文章">
    <meta property="og:article:author" content="测试公众号">
    <meta property="og:description" content="这是一段描述">
    <script>var createTime = '2026-04-09 16:58';</script>
  </head>
  <body>
    <div id="js_content">
      <h2>第一节</h2>
      <p>正文内容</p>
      <img data-src="https://mmbiz.qpic.cn/test.jpg">
    </div>
  </body>
</html>
"""


class WechatArticleAdapterTest(unittest.TestCase):
    def test_is_wechat_article_url_accepts_mp_domain_only(self):
        self.assertTrue(is_wechat_article_url("https://mp.weixin.qq.com/s/example"))
        self.assertTrue(is_wechat_article_url("https://mp.weixin.qq.com/mp/appmsgalbum?action=getalbum"))
        self.assertFalse(is_wechat_article_url("https://weixin.qq.com/s/example"))
        self.assertFalse(is_wechat_article_url("https://example.com/s/example"))

    def test_capture_from_html_extracts_metadata_and_markdown(self):
        result = capture_wechat_article_from_html(
            "https://mp.weixin.qq.com/s/example",
            SAMPLE_WECHAT_HTML,
            download_images=False,
        )

        self.assertEqual(result.title, "测试文章")
        self.assertEqual(result.author, "测试公众号")
        self.assertEqual(result.publish_time, "2026-04-09 16:58")
        self.assertEqual(result.description, "这是一段描述")
        self.assertIn("## 第一节", result.raw_markdown)
        self.assertIn("正文内容", result.raw_markdown)
        self.assertEqual(result.metadata["image_count"], 1)

    def test_capture_from_html_rejects_missing_body(self):
        with self.assertRaisesRegex(WechatArticleCaptureError, "无法找到文章正文"):
            capture_wechat_article_from_html(
                "https://mp.weixin.qq.com/s/example",
                "<html><body></body></html>",
                download_images=False,
            )
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python -m unittest tests.test_wechat_article -v
```

Expected: import fails because `sheng_wen.wechat_article` does not exist.

- [ ] **Step 3: Implement adapter module**

Create `src/main/python/sheng_wen/wechat_article.py`:

```python
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as html_to_markdown


class WechatArticleCaptureError(RuntimeError):
    pass


@dataclass
class CapturedImage:
    original_url: str
    local_path: str | None = None
    markdown_path: str | None = None
    status: str = "skipped"


@dataclass
class CapturedArticle:
    source_type: str
    source_url: str
    title: str
    author: str | None
    publish_time: str | None
    description: str | None
    raw_markdown: str
    plain_text: str
    images: list[CapturedImage] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


def is_wechat_article_url(url: str) -> bool:
    try:
        parsed = urlparse(str(url or "").strip())
    except Exception:
        return False
    return parsed.scheme == "https" and (parsed.hostname or "").lower() == "mp.weixin.qq.com"


def _meta_content(soup: BeautifulSoup, property_name: str) -> str | None:
    tag = soup.find("meta", property=property_name)
    value = tag.get("content") if tag else None
    value = str(value or "").strip()
    return value or None


def _extract_create_time(html: str) -> str | None:
    match = re.search(r"var\s+createTime\s*=\s*['\"]([^'\"]+)['\"]", html or "")
    return match.group(1).strip() if match else None


def _collect_images(content_div) -> list[CapturedImage]:
    images: list[CapturedImage] = []
    for img in content_div.find_all("img"):
        src = str(img.get("data-src") or img.get("src") or "").strip()
        if not src or src.startswith("data:"):
            continue
        images.append(CapturedImage(original_url=src, status="skipped"))
    return images


def _download_images(content_div, images: list[CapturedImage], output_dir: str | None) -> None:
    if not output_dir:
        return
    images_dir = os.path.join(output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)
    session = requests.Session()
    session.headers.update({"Referer": "https://mp.weixin.qq.com/"})

    index = 0
    for img in content_div.find_all("img"):
        src = str(img.get("data-src") or img.get("src") or "").strip()
        if not src or src.startswith("data:"):
            continue
        index += 1
        image_record = images[index - 1]
        try:
            response = session.get(src, timeout=20, stream=True)
            response.raise_for_status()
            ext = ".jpg"
            content_type = response.headers.get("Content-Type", "").lower()
            if "png" in content_type:
                ext = ".png"
            elif "webp" in content_type:
                ext = ".webp"
            elif "gif" in content_type:
                ext = ".gif"
            filename = f"wechat_{index:02d}{ext}"
            local_path = os.path.join(images_dir, filename)
            with open(local_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
            markdown_path = f"images/{filename}"
            img["src"] = markdown_path
            img.attrs.pop("data-src", None)
            image_record.local_path = local_path
            image_record.markdown_path = markdown_path
            image_record.status = "downloaded"
        except Exception:
            image_record.status = "failed"


def capture_wechat_article_from_html(
    url: str,
    html: str,
    *,
    output_dir: str | None = None,
    download_images: bool = True,
) -> CapturedArticle:
    if not is_wechat_article_url(url):
        raise WechatArticleCaptureError("请输入有效的微信公众号文章链接")

    soup = BeautifulSoup(html or "", "lxml")
    title = _meta_content(soup, "og:title") or "未知标题"
    author = _meta_content(soup, "og:article:author")
    description = _meta_content(soup, "og:description")
    publish_time = _meta_content(soup, "og:article:published_time") or _extract_create_time(html)

    content_div = soup.find("div", id="js_content")
    if not content_div:
        raise WechatArticleCaptureError("无法找到文章正文，文章可能需要登录、已删除、私密或被微信限制")

    images = _collect_images(content_div)
    if download_images:
        _download_images(content_div, images, output_dir)

    markdown = html_to_markdown(str(content_div), heading_style="ATX").strip()
    if not markdown:
        raise WechatArticleCaptureError("文章正文为空，无法生成笔记")

    plain_text = BeautifulSoup(str(content_div), "lxml").get_text("\n", strip=True)
    metadata = {
        "author": author,
        "account": author,
        "publish_time": publish_time,
        "description": description,
        "image_count": len(images),
    }

    return CapturedArticle(
        source_type="wechat_article",
        source_url=url,
        title=title,
        author=author,
        publish_time=publish_time,
        description=description,
        raw_markdown=markdown,
        plain_text=plain_text,
        images=images,
        metadata=metadata,
    )


def capture_wechat_article(url: str, *, output_dir: str | None = None) -> CapturedArticle:
    if not is_wechat_article_url(url):
        raise WechatArticleCaptureError("请输入有效的微信公众号文章链接")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://mp.weixin.qq.com/",
    })
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise WechatArticleCaptureError("公众号文章下载失败，请确认链接可访问后重试") from exc

    return capture_wechat_article_from_html(url, response.text, output_dir=output_dir)
```

- [ ] **Step 4: Run adapter tests**

Run:

```bash
.venv/bin/python -m unittest tests.test_wechat_article -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/main/python/sheng_wen/wechat_article.py tests/test_wechat_article.py
git commit -m "feat: add wechat article adapter"
```

---

## Task 3: Article Capture API And LLM Enqueue

**Files:**

- Modify: `src/main/python/sheng_wen/api.py`
- Modify: `tests/test_wechat_article.py`

- [ ] **Step 1: Add API helper tests**

Append these tests to `tests/test_wechat_article.py`:

```python
class WechatArticleTaskPayloadTest(unittest.TestCase):
    def test_article_task_payload_contains_source_metadata(self):
        from sheng_wen.api import _build_wechat_article_task_data
        from sheng_wen.wechat_article import CapturedArticle

        article = CapturedArticle(
            source_type="wechat_article",
            source_url="https://mp.weixin.qq.com/s/example",
            title="测试文章",
            author="测试公众号",
            publish_time="2026-04-09 16:58",
            description="描述",
            raw_markdown="# 测试文章\n\n正文",
            plain_text="正文",
            metadata={"author": "测试公众号", "publish_time": "2026-04-09 16:58", "image_count": 0},
        )

        payload = _build_wechat_article_task_data(
            "task-1",
            article,
            folder_id="folder-1",
            summary_mode="standard",
        )

        self.assertEqual(payload["source_type"], "wechat_article")
        self.assertEqual(payload["source_url"], "https://mp.weixin.qq.com/s/example")
        self.assertEqual(payload["video_url"], "https://mp.weixin.qq.com/s/example")
        self.assertEqual(payload["folder_id"], "folder-1")
        self.assertEqual(payload["transcript"], "# 测试文章\n\n正文")
        self.assertEqual(payload["status"], TaskStatus.SUMMARIZING)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python -m unittest tests.test_wechat_article -v
```

Expected: fails because `_build_wechat_article_task_data` is missing.

- [ ] **Step 3: Add API models**

In `src/main/python/sheng_wen/api.py`, add these Pydantic models near existing task models:

```python
class WechatArticleCreate(BaseModel):
    url: HttpUrl
    folder_id: Optional[str] = Field(default=None, description="目标文件夹，NULL 为根目录")
    summary_mode: Optional[str] = Field(default=None, description="总结模式: standard | agent | auto")
```

Extend the `Task` response model:

```python
    source_type: Optional[str] = "video"
    source_url: Optional[str] = None
    source_meta: Optional[str] = None
```

- [ ] **Step 4: Add task builder and endpoint**

In `src/main/python/sheng_wen/api.py`, add this helper before route definitions:

```python
def _build_wechat_article_task_data(task_id: str, article, folder_id: str | None, summary_mode: str) -> dict:
    return {
        "id": task_id,
        "video_url": article.source_url,
        "source_type": "wechat_article",
        "source_url": article.source_url,
        "source_meta": json.dumps(article.metadata or {}, ensure_ascii=False),
        "status": TaskStatus.SUMMARIZING,
        "created_at": datetime.utcnow(),
        "latest_modified_at": datetime.utcnow(),
        "progress": 0.0,
        "title": article.title,
        "transcript": article.raw_markdown,
        "summary": "",
        "error_message": None,
        "audio_duration": None,
        "transcription_time": None,
        "topic": None,
        "author_name": article.author,
        "author_url": article.source_url,
        "summary_mode": summary_mode,
        "summary_chunk_total": None,
        "summary_chunk_done": None,
        "summary_meta": json.dumps(article.metadata or {}, ensure_ascii=False),
        "folder_id": folder_id,
    }
```

Add this endpoint:

```python
@app.post("/articles/wechat", response_model=Task, status_code=201)
async def create_wechat_article_task(payload: WechatArticleCreate):
    from .wechat_article import WechatArticleCaptureError, capture_wechat_article

    source_url = str(payload.url)
    task_id = str(uuid.uuid4())
    article_assets_dir = os.path.join(task_assets_dir, task_id)
    resolved_summary_mode = _normalize_summary_mode(payload.summary_mode)

    try:
        article = capture_wechat_article(source_url, output_dir=article_assets_dir)
    except WechatArticleCaptureError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    task_data = _build_wechat_article_task_data(
        task_id,
        article,
        folder_id=payload.folder_id,
        summary_mode=resolved_summary_mode,
    )
    db.save_task(task_id, task_data)

    temp_dir = "temp"
    os.makedirs(temp_dir, exist_ok=True)
    intermediate_file = os.path.join(temp_dir, f"{task_id}_wechat_article.md")
    with open(intermediate_file, "w", encoding="utf-8") as file:
        file.write(article.raw_markdown)

    worker = await get_llm_worker()
    await worker.add_task({
        "task_id": task_id,
        "intermediate_file_path": intermediate_file,
        "output_file": os.path.join(temp_dir, f"{task_id}_wechat_summary.md"),
        "summary_mode": resolved_summary_mode,
    })

    await notify_task_update(task_id)
    return task_data
```

- [ ] **Step 5: Run backend tests**

Run:

```bash
.venv/bin/python -m unittest tests.test_wechat_article -v
.venv/bin/python -m unittest tests.test_collection_jobs -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/main/python/sheng_wen/api.py tests/test_wechat_article.py
git commit -m "feat: add wechat article capture API"
```

---

## Task 4: Frontend State And Types

**Files:**

- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/composables/useTaskViewModel.ts`

- [ ] **Step 1: Add frontend type fields**

In `frontend/src/types.ts`, extend `Task`:

```ts
  source_type?: 'video' | 'wechat_article' | string;
  source_url?: string | null;
  source_meta?: string | null;
```

Add request type:

```ts
export interface CreateWechatArticleRequest {
  url: string;
  folder_id?: string | null;
  summary_mode?: SummaryMode;
}
```

- [ ] **Step 2: Add article creation state and action**

In `frontend/src/composables/useTaskViewModel.ts`, import `CreateWechatArticleRequest`, then add state:

```ts
  const isCreatingWechatArticle = ref(false)
```

Add action near `createCollection`:

```ts
  const createWechatArticleTask = async (payload: CreateWechatArticleRequest): Promise<Task> => {
    isCreatingWechatArticle.value = true
    try {
      const response = await axios.post(`${apiBaseUrl}/articles/wechat`, payload)
      await fetchTasks()
      return response.data as Task
    } catch (err) {
      console.error('Failed to create WeChat article task:', err)
      error.value = getAxiosErrorMessage(err, '公众号文章采集失败')
      throw err
    } finally {
      isCreatingWechatArticle.value = false
    }
  }
```

Return both from `useTaskViewModel()`:

```ts
    isCreatingWechatArticle,
    createWechatArticleTask,
```

- [ ] **Step 3: Run TypeScript build to catch type errors**

Run:

```bash
nvm use 22
npm run build
```

Expected: build passes or fails only on missing UI wiring that will be added in Task 5. If it fails because imports are unused, keep the import until Task 5 and run the build again after UI wiring.

- [ ] **Step 4: Commit**

If the build passes:

```bash
git add frontend/src/types.ts frontend/src/composables/useTaskViewModel.ts
git commit -m "feat: add wechat article frontend state"
```

If the build fails only because the new action is unused in this intermediate state, defer commit until Task 5 and include these two files in that commit.

---

## Task 5: Frontend Entry, Modal, And Task Label

**Files:**

- Create: `frontend/src/components/WechatArticleCaptureModal.vue`
- Create: `frontend/src/components/WechatArticleCaptureModal.test.mjs`
- Modify: `frontend/src/components/Sidebar.vue`
- Modify: `frontend/src/components/FolderBrowser/TaskCard.vue`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/package.json`

- [ ] **Step 1: Create modal component**

Create `frontend/src/components/WechatArticleCaptureModal.vue`:

```vue
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { PhArticle, PhSpinner, PhX } from '@phosphor-icons/vue'
import type { CreateWechatArticleRequest, Folder, SummaryMode, Task } from '../types'

const props = defineProps<{
  isOpen: boolean
  folders: Folder[]
  currentFolderId?: string | null
  summaryMode: Exclude<SummaryMode, 'auto'>
  isCreatingWechatArticle: boolean
  createWechatArticleTask: (payload: CreateWechatArticleRequest) => Promise<Task>
}>()

const emit = defineEmits<{
  close: []
  created: [task: Task]
}>()

const articleUrl = ref('')
const folderId = ref<string | null>(null)
const errorMessage = ref('')

const isWechatUrl = (raw: string) => {
  try {
    return new URL(raw.trim()).hostname.toLowerCase() === 'mp.weixin.qq.com'
  } catch {
    return false
  }
}

const canSubmit = computed(() =>
  articleUrl.value.trim().length > 0
  && isWechatUrl(articleUrl.value)
  && !props.isCreatingWechatArticle
)

const resetState = () => {
  articleUrl.value = ''
  folderId.value = props.currentFolderId || null
  errorMessage.value = ''
}

const handleSubmit = async () => {
  const url = articleUrl.value.trim()
  if (!isWechatUrl(url)) {
    errorMessage.value = '请输入有效的微信公众号文章链接'
    return
  }

  errorMessage.value = ''
  try {
    const task = await props.createWechatArticleTask({
      url,
      folder_id: folderId.value,
      summary_mode: props.summaryMode,
    })
    emit('created', task)
    resetState()
    emit('close')
  } catch (err) {
    errorMessage.value = err instanceof Error ? err.message : '公众号文章采集失败'
  }
}

watch(() => props.isOpen, (isOpen) => {
  if (isOpen) {
    folderId.value = props.currentFolderId || null
    errorMessage.value = ''
  }
})
</script>

<template>
  <Teleport to="body">
    <transition name="modal">
      <div
        v-if="isOpen"
        class="fixed inset-0 z-[72] flex items-center justify-center bg-slate-950/45 p-4 backdrop-blur-sm"
        @click.self="emit('close')"
      >
        <section class="flex w-full max-w-xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
          <header class="flex items-center justify-between border-b border-slate-100 px-6 py-4">
            <div class="flex items-center gap-3">
              <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600">
                <PhArticle :size="22" weight="fill" />
              </div>
              <div>
                <h2 class="text-base font-semibold text-slate-900">公众号文章</h2>
                <p class="text-xs text-slate-500">采集单篇文章并生成学习笔记</p>
              </div>
            </div>
            <button
              class="flex h-9 w-9 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700"
              @click="emit('close')"
            >
              <PhX :size="20" />
            </button>
          </header>

          <div class="space-y-4 px-6 py-5">
            <label class="block">
              <span class="mb-1.5 block text-xs font-medium text-slate-500">文章链接</span>
              <input
                v-model="articleUrl"
                class="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none transition focus:border-emerald-400 focus:ring-4 focus:ring-emerald-100"
                placeholder="https://mp.weixin.qq.com/s/..."
              />
            </label>

            <label class="block">
              <span class="mb-1.5 block text-xs font-medium text-slate-500">保存到文件夹</span>
              <select
                v-model="folderId"
                class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none transition focus:border-emerald-400 focus:ring-4 focus:ring-emerald-100"
              >
                <option :value="null">根目录</option>
                <option v-for="folder in folders" :key="folder.id" :value="folder.id">
                  {{ folder.name }}
                </option>
              </select>
            </label>

            <p v-if="errorMessage" class="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-600">
              {{ errorMessage }}
            </p>
          </div>

          <footer class="flex items-center justify-end gap-3 border-t border-slate-100 px-6 py-4">
            <button
              class="rounded-xl px-4 py-2 text-sm font-medium text-slate-500 transition hover:bg-slate-100 hover:text-slate-700"
              @click="emit('close')"
            >
              取消
            </button>
            <button
              class="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-slate-300"
              :disabled="!canSubmit"
              @click="handleSubmit"
            >
              <PhSpinner v-if="isCreatingWechatArticle" :size="16" class="animate-spin" />
              采集并生成笔记
            </button>
          </footer>
        </section>
      </div>
    </transition>
  </Teleport>
</template>
```

- [ ] **Step 2: Add sidebar emit and button**

In `frontend/src/components/Sidebar.vue`, import `PhArticle` and add emit:

```ts
  openWechatArticleCapture: []
```

Add the button beside `合集采集`:

```vue
<button
  type="button"
  class="flex w-full items-center justify-center gap-2 rounded-xl border border-emerald-100 bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-700 transition hover:border-emerald-200 hover:bg-emerald-100"
  @click="emit('openWechatArticleCapture')"
>
  <PhArticle :size="16" weight="fill" />
  公众号文章
</button>
```

- [ ] **Step 3: Add task card label**

In `frontend/src/components/FolderBrowser/TaskCard.vue`, add:

```ts
const sourceLabel = computed(() => {
  if (props.task.source_type === 'wechat_article') return '公众号'
  return ''
})
```

Render near the status chip:

```vue
<span
  v-if="sourceLabel"
  class="text-xs font-medium px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700"
>
  {{ sourceLabel }}
</span>
```

- [ ] **Step 4: Wire App modal**

In `frontend/src/App.vue`, import the modal and add state:

```ts
import WechatArticleCaptureModal from './components/WechatArticleCaptureModal.vue'

const isWechatArticleCaptureOpen = ref(false)

const handleWechatArticleCreated = (task: Task) => {
  success('公众号文章任务已创建')
  handleSelectTask(task)
}
```

Pass handler to `Sidebar`:

```vue
@openWechatArticleCapture="isWechatArticleCaptureOpen = true"
```

Mount modal near `CollectionCaptureModal`:

```vue
<WechatArticleCaptureModal
  :isOpen="isWechatArticleCaptureOpen"
  :folders="folders"
  :currentFolderId="selectedTask?.folder_id || null"
  :summaryMode="summaryMode"
  :isCreatingWechatArticle="isCreatingWechatArticle"
  :createWechatArticleTask="createWechatArticleTask"
  @close="isWechatArticleCaptureOpen = false"
  @created="handleWechatArticleCreated"
/>
```

- [ ] **Step 5: Add static frontend test**

Create `frontend/src/components/WechatArticleCaptureModal.test.mjs`:

```js
import fs from 'node:fs'
import path from 'node:path'
import assert from 'node:assert/strict'

const root = path.resolve(new URL('../..', import.meta.url).pathname)
const modal = fs.readFileSync(path.join(root, 'src/components/WechatArticleCaptureModal.vue'), 'utf8')
const sidebar = fs.readFileSync(path.join(root, 'src/components/Sidebar.vue'), 'utf8')
const taskCard = fs.readFileSync(path.join(root, 'src/components/FolderBrowser/TaskCard.vue'), 'utf8')

assert.match(modal, /公众号文章/)
assert.match(modal, /mp\.weixin\.qq\.com/)
assert.match(modal, /createWechatArticleTask/)
assert.match(modal, /采集并生成笔记/)
assert.match(sidebar, /openWechatArticleCapture/)
assert.match(taskCard, /wechat_article/)
assert.match(taskCard, /公众号/)
```

Add script to `frontend/package.json`:

```json
"test:wechat-ui": "node src/components/WechatArticleCaptureModal.test.mjs"
```

- [ ] **Step 6: Run frontend tests and build**

Run:

```bash
nvm use 22
npm run test:wechat-ui
npm run test:collection-ui
npm run build
```

Expected: all commands pass. Existing Vite chunk-size warnings are acceptable.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/WechatArticleCaptureModal.vue frontend/src/components/WechatArticleCaptureModal.test.mjs frontend/src/components/Sidebar.vue frontend/src/components/FolderBrowser/TaskCard.vue frontend/src/App.vue frontend/src/types.ts frontend/src/composables/useTaskViewModel.ts frontend/package.json
git commit -m "feat: add wechat article capture UI"
```

---

## Task 6: Final Verification And Docs

**Files:**

- Modify: `README.md` only if the feature is fully working.

- [ ] **Step 1: Add short README note**

Add a short bullet near supported input/features:

```markdown
- 支持单篇微信公众号文章采集：粘贴 `mp.weixin.qq.com` 链接后生成学习笔记。
```

- [ ] **Step 2: Run complete automated checks**

Run:

```bash
.venv/bin/python -m unittest tests.test_wechat_article -v
.venv/bin/python -m unittest tests.test_collection_jobs -v
nvm use 22
npm run test:transcript
npm run test:accounts-ui
npm run test:collection-ui
npm run test:wechat-ui
npm run build
```

Expected: all tests pass; Vite chunk-size warnings are acceptable.

- [ ] **Step 3: Manual local smoke test**

Start the app:

```bash
.venv/bin/python ShengWen-app.py
```

Open:

```text
http://127.0.0.1:8000/
```

Manual checks:

- Sidebar shows `公众号文章`.
- Non-WeChat URL shows `请输入有效的微信公众号文章链接`.
- A public `https://mp.weixin.qq.com/...` article creates a task.
- Task card shows `公众号`.
- `原文` contains captured Markdown.
- `AI 总结` eventually completes.
- Existing video URL submission still creates video tasks.

- [ ] **Step 4: Commit docs**

If README was changed:

```bash
git add README.md
git commit -m "docs: mention wechat article capture"
```

- [ ] **Step 5: Final status**

Run:

```bash
git status --short --branch
git log --oneline -6
```

Expected: only intended commits are ahead of `origin/master`; no unstaged files remain.

---

## Self-Review

Spec coverage:

- Dedicated `公众号文章` entry: Task 5.
- Single article only: Task 5 modal validates one URL and Task 3 endpoint accepts one URL.
- Internal adapter instead of external skill runtime path: Task 2.
- Task source fields and compatibility with `video_url`: Task 1 and Task 3.
- Existing LLM summary reuse: Task 3.
- Existing task card plus `公众号` label: Task 5.
- Clear errors and image failure tolerance: Task 2 and Task 3.
- Tests and manual validation: Tasks 1 through 6.

Unfinished-marker scan:

- This plan contains no unfinished work markers outside executable code examples.

Type consistency:

- Backend source field names are `source_type`, `source_url`, `source_meta`.
- Frontend request type is `CreateWechatArticleRequest`.
- Frontend action is `createWechatArticleTask`.
- Endpoint is `POST /articles/wechat`.
