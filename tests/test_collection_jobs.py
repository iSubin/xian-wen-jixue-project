import os
import sys
import tempfile
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src", "main", "python"))

from xianwen.collection_jobs import (
    build_aggregate_markdown,
    build_bilibili_parts_collection,
    build_wechat_history_collection,
    derive_collection_status,
    extract_urls_from_text,
)
from xianwen.db import TaskDB, TaskStatus
from xianwen.wechat_article import WechatAccountHistory, WechatHistoryArticle


class CollectionJobHelpersTest(unittest.TestCase):
    def test_extract_urls_from_text_keeps_order_and_removes_duplicates(self):
        text = """
        第一条 https://www.bilibili.com/video/BV1111111111/?spm_id_from=333
        第二条：https://b23.tv/abc123）
        重复 https://www.bilibili.com/video/BV1111111111/?spm_id_from=333
        """

        self.assertEqual(
            extract_urls_from_text(text),
            [
                "https://www.bilibili.com/video/BV1111111111/?spm_id_from=333",
                "https://b23.tv/abc123",
            ],
        )

    def test_build_bilibili_parts_collection_converts_pages_to_items(self):
        preview = build_bilibili_parts_collection(
            "https://www.bilibili.com/video/BV1234567890/",
            {
                "title": "Codex 教程",
                "bvid": "BV1234567890",
                "duration": 300,
                "parts": [
                    {"index": 0, "title": "开场", "duration": 60},
                    {"index": 1, "title": "实战", "duration": 240},
                ],
            },
        )

        self.assertEqual(preview["provider"], "bilibili")
        self.assertEqual(preview["source_type"], "bilibili_multi_part")
        self.assertEqual(preview["title"], "Codex 教程")
        self.assertEqual(preview["total_items"], 2)
        self.assertEqual(preview["items"][0]["title"], "P1 开场")
        self.assertEqual(preview["items"][0]["part_index"], 0)
        self.assertEqual(preview["items"][1]["duration"], 240)

    def test_build_wechat_history_collection_converts_articles_to_items(self):
        history = WechatAccountHistory(
            account_name="测试公众号",
            source_url="https://mp.weixin.qq.com/s/source",
            biz="MzTestBiz",
            items=[
                WechatHistoryArticle(
                    source_url="https://mp.weixin.qq.com/s/a",
                    title="第一篇",
                    digest="摘要",
                    publish_time="2026-04-09 16:58:00",
                    cover_url=None,
                    item_index=0,
                ),
                WechatHistoryArticle(
                    source_url="https://mp.weixin.qq.com/s/b",
                    title="第二篇",
                    digest=None,
                    publish_time=None,
                    cover_url=None,
                    item_index=1,
                ),
            ],
            metadata={"ret": 0},
        )

        preview = build_wechat_history_collection(history)

        self.assertEqual(preview["provider"], "wechat")
        self.assertEqual(preview["source_type"], "wechat_account_history")
        self.assertEqual(preview["source_url"], "https://mp.weixin.qq.com/s/source")
        self.assertEqual(preview["title"], "测试公众号 - 公众号历史文章")
        self.assertEqual(preview["total_items"], 2)
        self.assertEqual(preview["items"][0]["provider"], "wechat")
        self.assertEqual(preview["items"][0]["source_url"], "https://mp.weixin.qq.com/s/a")
        self.assertEqual(preview["items"][0]["title"], "第一篇")

    def test_derive_collection_status_counts_task_states(self):
        items = [
            {"task": {"status": TaskStatus.COMPLETED.value}},
            {"task": {"status": TaskStatus.SUMMARIZING.value}},
            {"task": {"status": TaskStatus.FAILED.value}},
            {"task": None},
        ]

        status = derive_collection_status(items)

        self.assertEqual(status["status"], "RUNNING")
        self.assertEqual(status["total_items"], 4)
        self.assertEqual(status["completed_items"], 1)
        self.assertEqual(status["failed_items"], 1)
        self.assertEqual(status["running_items"], 1)

    def test_build_aggregate_markdown_uses_completed_task_summaries(self):
        markdown = build_aggregate_markdown(
            {"title": "Codex 合集"},
            [
                {
                    "sort_order": 0,
                    "title": "P1 开场",
                    "task": {
                        "status": TaskStatus.COMPLETED.value,
                        "summary": "# 开场总结\n\n内容 A",
                    },
                },
                {
                    "sort_order": 1,
                    "title": "P2 实战",
                    "task": {
                        "status": TaskStatus.FAILED.value,
                        "summary": "失败内容不应进入聚合",
                    },
                },
            ],
        )

        self.assertIn("# Codex 合集", markdown)
        self.assertIn("## 1. P1 开场", markdown)
        self.assertIn("内容 A", markdown)
        self.assertIn("P2 实战", markdown)
        self.assertIn("暂未完成", markdown)
        self.assertNotIn("失败内容不应进入聚合", markdown)


class CollectionJobPersistenceTest(unittest.TestCase):
    def test_collection_job_persists_items_and_derives_progress_from_tasks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            database = TaskDB(database_url=f"sqlite:///{os.path.join(tmpdir, 'test.db')}")
            job = database.create_collection_job(
                {
                    "id": "job-1",
                    "provider": "bilibili",
                    "source_type": "url_list",
                    "source_url": "https://www.bilibili.com/video/BV1",
                    "title": "测试合集",
                    "folder_id": "folder-1",
                    "status": "PENDING",
                },
                [
                    {
                        "id": "item-1",
                        "job_id": "job-1",
                        "sort_order": 0,
                        "provider": "bilibili",
                        "source_url": "https://www.bilibili.com/video/BV1",
                        "title": "第一集",
                    },
                    {
                        "id": "item-2",
                        "job_id": "job-1",
                        "sort_order": 1,
                        "provider": "bilibili",
                        "source_url": "https://www.bilibili.com/video/BV2",
                        "title": "第二集",
                    },
                ],
            )
            self.assertEqual(job["total_items"], 2)

            database.save_task(
                "task-1",
                {
                    "id": "task-1",
                    "video_url": "https://www.bilibili.com/video/BV1",
                    "status": TaskStatus.COMPLETED,
                    "progress": 100.0,
                    "title": "第一集",
                    "summary": "第一集总结",
                },
            )
            database.link_collection_item_task("item-1", "task-1")

            reloaded = database.get_collection_job("job-1", include_items=True)

            self.assertEqual(reloaded["status"], "RUNNING")
            self.assertEqual(reloaded["completed_items"], 1)
            self.assertEqual(reloaded["failed_items"], 0)
            self.assertEqual(reloaded["items"][0]["task_id"], "task-1")
            self.assertEqual(reloaded["items"][0]["task"]["status"], TaskStatus.COMPLETED.value)


if __name__ == "__main__":
    unittest.main()
