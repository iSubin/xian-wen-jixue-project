import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.main.python.xianwen.db import TaskDB
from src.main.python.xianwen.storage import (
    ensure_storage_layout,
    get_task_download_dir,
    get_task_work_dir,
    preserve_article_source,
    preserve_original_file,
    resolve_data_path,
)


class StorageLayoutTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.env = patch.dict(
            os.environ,
            {
                "XIANWEN_DATA_DIR": str(self.root / "data"),
                "XIANWEN_RUNTIME_DIR": str(self.root / "runtime"),
                "XIANWEN_EXPORTS_DIR": str(self.root / "exports"),
            },
        )
        self.env.start()
        self.addCleanup(self.env.stop)
        ensure_storage_layout()

    def test_preserves_downloaded_original_and_registers_hash(self):
        task_id = "task-12345678"
        download = get_task_download_dir(task_id) / "source.mp4"
        download.write_bytes(b"original-video")

        target, record = preserve_original_file(
            download,
            task_id=task_id,
            title="一段/原始:视频",
            source_url="https://www.bilibili.com/video/BV1TEST",
            source_type="video",
        )

        self.assertFalse(download.exists())
        self.assertEqual(target.read_bytes(), b"original-video")
        self.assertIn("originals/bilibili/", record["relative_path"])
        self.assertEqual(resolve_data_path(record["relative_path"]), target.resolve())
        manifest = json.loads((target.parent / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["content_id"], task_id)
        self.assertEqual(manifest["assets"][0]["sha256"], record["sha256"])

    def test_preserves_article_html_markdown_and_images(self):
        task_id = "article-1"
        image = self.root / "data" / "assets" / task_id / "images" / "cover.jpg"
        image.parent.mkdir(parents=True)
        image.write_bytes(b"cover")

        records = preserve_article_source(
            task_id=task_id,
            content_id=task_id,
            title="原始文章",
            source_url="https://mp.weixin.qq.com/s/example",
            source_type="wechat_article",
            raw_html="<html>原文</html>",
            raw_markdown="# 原文",
            asset_paths=[image],
        )

        self.assertEqual({record["asset_type"] for record in records}, {"article_html", "article_markdown", "image"})
        self.assertTrue(all(resolve_data_path(record["relative_path"]).exists() for record in records))

    def test_database_keeps_original_asset_after_task_delete(self):
        store = TaskDB(sqlite_path=str(self.root / "test.db"))
        store.save_task(
            "task-1",
            {
                "video_url": "https://example.com/video",
                "status": "COMPLETED",
                "title": "测试视频",
            },
        )
        source = get_task_download_dir("task-1") / "source.mp4"
        source.write_bytes(b"video")
        _, record = preserve_original_file(
            source,
            task_id="task-1",
            title="测试视频",
            source_url="https://example.com/video",
        )
        store.upsert_content_asset(record)

        self.assertEqual(len(store.list_content_assets("task-1")), 1)
        store.delete_task("task-1")
        self.assertEqual(len(store.list_content_assets("task-1")), 1)
        self.assertTrue(resolve_data_path(record["relative_path"]).exists())

    def test_task_work_files_are_scoped_by_task(self):
        self.assertEqual(
            get_task_work_dir("task-1"),
            self.root / "runtime" / "tasks" / "task-1",
        )


if __name__ == "__main__":
    unittest.main()
