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
