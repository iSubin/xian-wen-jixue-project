import asyncio
import os
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.main.python.xianwen import api as api_module
from src.main.python.xianwen.db import TaskDB


def run_async(coroutine):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coroutine)


class LibraryApiTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.original_db = api_module.db
        api_module.db = TaskDB(
            file_path=os.path.join(self.temp_dir.name, "tasks.json"),
            sqlite_path=os.path.join(self.temp_dir.name, "test.db"),
        )
        self.addCleanup(lambda: setattr(api_module, "db", self.original_db))
        api_module._git_auto_sync_pending.clear()
        api_module._git_auto_sync_tasks.clear()
        api_module._git_sync_locks.clear()
        self.client = TestClient(api_module.app)

    def test_library_projects_documents_and_rejects_folder_cycles(self):
        root = self.client.post("/folders/", json={"name": "根目录"}).json()
        child = self.client.post(
            "/folders/",
            json={"name": "子目录", "parent_id": root["id"]},
        ).json()
        response = self.client.patch(
            f"/folders/{root['id']}",
            json={"parent_id": child["id"]},
        )
        self.assertEqual(response.status_code, 400)

        now = datetime.utcnow()
        api_module.db.save_task(
            "document-1",
            {
                "video_url": "https://example.com",
                "source_url": "https://example.com",
                "source_type": "video",
                "status": "COMPLETED",
                "created_at": now,
                "latest_modified_at": now,
                "progress": 1.0,
                "title": "第一篇",
                "summary": "# 正文",
                "folder_id": child["id"],
            },
        )

        library = self.client.get("/library/tree")
        self.assertEqual(library.status_code, 200)
        payload = library.json()
        self.assertEqual(payload["document_count"], 1)
        self.assertEqual(payload["folder_count"], 2)
        self.assertEqual(payload["documents"][0]["title"], "第一篇")

    def test_git_settings_never_return_private_key(self):
        with patch.object(api_module, "derive_public_key", return_value="ssh-ed25519 public"):
            response = self.client.put(
                "/git/settings",
                json={
                    "repository_url": "git@github.com:owner/repo.git",
                    "branch": "main",
                    "root_path": "先闻继学",
                    "private_key": "-----BEGIN OPENSSH PRIVATE KEY-----\nsecret\n-----END OPENSSH PRIVATE KEY-----",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["has_private_key"])
        self.assertTrue(payload["auto_sync"])
        self.assertNotIn("private_key", payload)
        self.assertNotIn("secret", response.text)

    def test_task_assets_do_not_expose_local_source_paths(self):
        api_module.db.save_task(
            "local-asset-1",
            {
                "video_url": "file:///private/runtime/incoming.mp4",
                "status": "COMPLETED",
                "title": "本地物料",
            },
        )
        api_module.db.upsert_content_asset(
            {
                "id": "asset-1",
                "task_id": "local-asset-1",
                "role": "original",
                "asset_type": "video",
                "relative_path": "originals/local/2026/local-asset/source.mp4",
                "original_filename": "incoming.mp4",
                "content_type": "video/mp4",
                "sha256": "0" * 64,
                "size_bytes": 123,
                "source_url": "file:///private/runtime/incoming.mp4",
                "status": "available",
            }
        )

        response = self.client.get("/tasks/local-asset-1/assets")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["assets"][0]["source_url"])
        self.assertNotIn("/private/runtime", response.text)

    def test_completed_content_marks_git_pending_and_requests_auto_sync(self):
        now = datetime.utcnow()
        api_module.db.save_task(
            "completed-1",
            {
                "video_url": "https://example.com/video",
                "status": "COMPLETED",
                "created_at": now,
                "latest_modified_at": now,
                "progress": 1.0,
                "title": "完成内容",
                "summary": "整理稿",
                "transcript": "逐字稿",
            },
        )

        with patch.object(api_module, "_schedule_git_auto_sync", return_value=True) as schedule:
            run_async(api_module.notify_task_update("completed-1"))

        schedule.assert_called_once_with(api_module.DEFAULT_LOCAL_USER_ID)

    def test_saved_git_account_sync_updates_runtime_status(self):
        with patch.object(api_module, "derive_public_key", return_value="ssh-ed25519 public"):
            response = self.client.put(
                "/git/settings",
                json={
                    "repository_url": "git@github.com:owner/repo.git",
                    "branch": "main",
                    "root_path": "先闻继学",
                    "auto_sync": True,
                    "private_key": "-----BEGIN OPENSSH PRIVATE KEY-----\nsecret\n-----END OPENSSH PRIVATE KEY-----",
                },
            )
        self.assertEqual(response.status_code, 200)

        expected = {
            "success": True,
            "document_count": 0,
            "committed": False,
            "commit_sha": "",
            "created": 0,
            "updated": 0,
            "adopted": 0,
            "removed": 0,
            "conflicts": [],
        }
        with patch.object(api_module, "sync_library_to_git", return_value=expected) as sync:
            result = run_async(api_module._sync_saved_git_account(api_module.DEFAULT_LOCAL_USER_ID))

        self.assertEqual(result, expected)
        self.assertEqual(self.client.get("/git/settings").json()["status"], "connected")
        sync.assert_called_once()

    def test_document_crud_preserves_source_task(self):
        invalid = self.client.post(
            "/library/documents",
            json={"title": "   ", "content": ""},
        )
        self.assertEqual(invalid.status_code, 400)

        folder = self.client.post("/folders/", json={"name": "产品"}).json()
        created = self.client.post(
            "/library/documents",
            json={
                "title": "手写笔记",
                "content": "# 初稿",
                "folder_id": folder["id"],
            },
        )
        self.assertEqual(created.status_code, 201)
        document_id = created.json()["id"]
        self.assertEqual(created.json()["source_type"], "manual")

        updated = self.client.patch(
            f"/library/documents/{document_id}",
            json={
                "title": "手写笔记（二稿）",
                "content": "# 二稿",
                "folder_id": None,
            },
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["summary"], "# 二稿")
        self.assertIsNone(updated.json()["folder_id"])

        removed = self.client.delete(f"/library/documents/{document_id}")
        self.assertEqual(removed.status_code, 204)
        self.assertEqual(self.client.get("/library/tree").json()["document_count"], 0)

        source_record = self.client.get(f"/tasks/{document_id}")
        self.assertEqual(source_record.status_code, 200)
        self.assertFalse(source_record.json()["library_visible"])


if __name__ == "__main__":
    unittest.main()
