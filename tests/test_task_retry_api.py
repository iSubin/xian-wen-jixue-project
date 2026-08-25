import importlib
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from src.main.python.xianwen import api as api_module
from src.main.python.xianwen.db import TaskDB, TaskStatus


class TaskRetryApiTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)

        self.previous_data_dir = os.environ.get("XIANWEN_DATA_DIR")
        os.environ["XIANWEN_DATA_DIR"] = str(self.root / "data")
        self.addCleanup(self._restore_data_dir)

        self.db_module = importlib.import_module("src.main.python.xianwen.db")
        self.original_api_db = api_module.db
        self.original_shared_db = self.db_module.db
        self.store = TaskDB(sqlite_path=str(self.root / "tasks.db"))
        api_module.db = self.store
        self.db_module.db = self.store
        self.addCleanup(lambda: setattr(api_module, "db", self.original_api_db))
        self.addCleanup(lambda: setattr(self.db_module, "db", self.original_shared_db))

        self.notify_patch = patch.object(api_module, "notify_task_update", new=AsyncMock())
        self.notify_patch.start()
        self.addCleanup(self.notify_patch.stop)
        self.client = TestClient(api_module.app)

    def _restore_data_dir(self):
        if self.previous_data_dir is None:
            os.environ.pop("XIANWEN_DATA_DIR", None)
        else:
            os.environ["XIANWEN_DATA_DIR"] = self.previous_data_dir

    def _save_task(self, task_id: str, **overrides):
        now = datetime.utcnow()
        data = {
            "video_url": "https://example.com/video",
            "source_url": "https://example.com/video",
            "source_type": "video",
            "status": TaskStatus.FAILED,
            "created_at": now,
            "latest_modified_at": now,
            "progress": 0.5,
            "title": "重试测试",
            "transcript": "",
            "summary": "",
            "error_message": "原失败原因",
            "summary_mode": "standard",
        }
        data.update(overrides)
        self.store.save_task(task_id, data)

    def test_failed_task_with_transcript_resumes_from_summary(self):
        self._save_task("failed-summary", transcript="已经保存的逐字稿")
        llm_worker = SimpleNamespace(add_task=AsyncMock())

        with patch.object(
            api_module,
            "get_llm_worker",
            new=AsyncMock(return_value=llm_worker),
        ):
            response = self.client.post(
                "/tasks/failed-summary/retry",
                json={"summary_mode": "agent"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], TaskStatus.SUMMARIZING.value)
        self.assertIsNone(response.json()["error_message"])
        payload = llm_worker.add_task.await_args.args[0]
        self.assertEqual(payload["summary_mode"], "agent")
        self.assertEqual(
            Path(payload["intermediate_file_path"]).read_text(encoding="utf-8"),
            "已经保存的逐字稿",
        )

    def test_completed_video_reuses_preserved_original(self):
        self._save_task(
            "completed-video",
            status=TaskStatus.COMPLETED,
            transcript="旧逐字稿",
            summary="旧整理稿",
            error_message=None,
        )
        media_path = self.root / "data" / "originals" / "video" / "source.mp4"
        media_path.parent.mkdir(parents=True, exist_ok=True)
        media_path.write_bytes(b"media")
        self.store.upsert_content_asset(
            {
                "id": "asset-completed-video",
                "task_id": "completed-video",
                "role": "original",
                "asset_type": "video",
                "relative_path": "originals/video/source.mp4",
                "original_filename": "source.mp4",
                "content_type": "video/mp4",
                "sha256": "0" * 64,
                "size_bytes": 5,
                "source_url": "https://example.com/video",
                "status": "available",
            }
        )
        transcriber = SimpleNamespace(add_task=AsyncMock())

        with patch.object(
            api_module,
            "get_transcriber_worker",
            new=AsyncMock(return_value=transcriber),
        ):
            response = self.client.post("/tasks/completed-video/retry", json={})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], TaskStatus.TRANSCRIBING.value)
        self.assertEqual(response.json()["transcript"], "")
        payload = transcriber.add_task.await_args.args[0]
        self.assertEqual(Path(payload["video_file"]).resolve(), media_path.resolve())
        self.assertTrue(media_path.exists())

    def test_failed_online_video_redownloads_with_matching_account(self):
        source_url = (
            "https://shop.h5.xet.pomoho.com/p/course/video/v_123"
            "?product_id=course_123"
        )
        self._save_task(
            "failed-download",
            video_url=source_url,
            source_url=source_url,
        )
        self.store.upsert_connected_account(
            user_id="shop-user",
            provider="xiaoetong",
            credential_type="cookie_header",
            secret_payload={"cookie_header": "xiaoet_session=retry-cookie"},
            display_name="测试店铺",
            domain_scope="shop.h5.xet.pomoho.com",
        )
        downloader = SimpleNamespace(add_task=AsyncMock())

        with patch.object(
            api_module,
            "get_downloader_worker",
            new=AsyncMock(return_value=downloader),
        ):
            response = self.client.post(
                "/tasks/failed-download/retry",
                headers={"X-XianWen-User-Id": "shop-user"},
                json={},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], TaskStatus.DOWNLOADING.value)
        payload = downloader.add_task.await_args.args[0]
        self.assertEqual(payload["xiaoet_cookie_header"], "xiaoet_session=retry-cookie")

    def test_completed_article_reuses_saved_text_and_active_task_is_rejected(self):
        self._save_task(
            "completed-article",
            status=TaskStatus.COMPLETED,
            source_type="wechat_article",
            transcript="公众号原文",
            summary="旧整理稿",
            error_message=None,
        )
        self._save_task("active-task", status=TaskStatus.TRANSCRIBING)
        llm_worker = SimpleNamespace(add_task=AsyncMock())

        with patch.object(
            api_module,
            "get_llm_worker",
            new=AsyncMock(return_value=llm_worker),
        ):
            article_response = self.client.post("/tasks/completed-article/retry", json={})
            active_response = self.client.post("/tasks/active-task/retry", json={})

        self.assertEqual(article_response.status_code, 200)
        self.assertEqual(article_response.json()["status"], TaskStatus.SUMMARIZING.value)
        self.assertEqual(active_response.status_code, 409)
        self.assertIn("正在处理中", active_response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
