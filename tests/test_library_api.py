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


if __name__ == "__main__":
    unittest.main()
