import os
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.main.python.xianwen import api as api_module
from src.main.python.xianwen.db import TaskDB


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
        self.assertNotIn("private_key", payload)
        self.assertNotIn("secret", response.text)

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
