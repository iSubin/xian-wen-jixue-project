import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from src.main.python.xianwen.db import TaskDB
from src.main.python.xianwen.git_sync import (
    GeneratedFile,
    GitSyncError,
    apply_managed_files,
    build_library_files,
    validate_branch,
    validate_repository_url,
    validate_root_path,
)


class GitSyncExportTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.store = TaskDB(
            file_path=str(self.root / "tasks.json"),
            sqlite_path=str(self.root / "xianwen.db"),
        )

    def test_builds_folder_tree_obsidian_index_and_assets(self):
        parent_id = "parent"
        child_id = "child"
        task_id = "task-001"
        now = datetime.utcnow()
        self.store.create_folder(
            {
                "id": parent_id,
                "name": "经世",
                "parent_id": None,
                "folder_type": "manual",
                "source_video_url": None,
                "sort_order": 0,
                "created_at": now,
            }
        )
        self.store.create_folder(
            {
                "id": child_id,
                "name": "人工智能",
                "parent_id": parent_id,
                "folder_type": "manual",
                "source_video_url": None,
                "sort_order": 0,
                "created_at": now,
            }
        )
        asset_dir = self.root / "temp" / "task-assets" / task_id / "frames"
        asset_dir.mkdir(parents=True)
        (asset_dir / "frame.jpg").write_bytes(b"frame")
        self.store.save_task(
            task_id,
            {
                "video_url": "https://example.com/video",
                "source_url": "https://example.com/video",
                "source_type": "video",
                "status": "COMPLETED",
                "created_at": now,
                "latest_modified_at": now,
                "progress": 1.0,
                "title": "从感知到知识",
                "summary": f"![关键帧](/task-assets/{task_id}/frames/frame.jpg)",
                "transcript": "[000001] 原始转写",
                "folder_id": child_id,
            },
        )

        generated, document_count = build_library_files(
            self.store,
            project_root=self.root,
        )

        document_path = "经世/人工智能/从感知到知识.md"
        self.assertEqual(document_count, 1)
        self.assertIn(document_path, generated)
        content = generated[document_path].content.decode("utf-8")
        self.assertIn("# 从感知到知识", content)
        self.assertIn("../../_assets/task-001/frames/frame.jpg", content)
        self.assertIn("经世/人工智能/从感知到知识", generated["_索引.md"].content.decode("utf-8"))
        self.assertIn("_assets/task-001/frames/frame.jpg", generated)

    def test_preserves_obsidian_edits_as_conflicts(self):
        repository = self.root / "repository"
        repository.mkdir()
        first = {"课程/第一课.md": GeneratedFile(b"version one\n", task_id="task-1")}
        result = apply_managed_files(repository, "先闻继学", first)
        self.assertEqual(result["created"], 1)

        document = repository / "先闻继学" / "课程" / "第一课.md"
        document.write_text("user edit\n", encoding="utf-8")
        second = {"课程/第一课.md": GeneratedFile(b"version two\n", task_id="task-1")}
        result = apply_managed_files(repository, "先闻继学", second)

        self.assertEqual(document.read_text(encoding="utf-8"), "user edit\n")
        self.assertEqual(result["conflicts"], ["课程/第一课.md"])

    def test_rejects_unsafe_git_inputs(self):
        self.assertEqual(
            validate_repository_url("git@github.com:owner/repo.git"),
            "git@github.com:owner/repo.git",
        )
        with self.assertRaises(GitSyncError):
            validate_repository_url("https://github.com/owner/repo.git")
        with self.assertRaises(GitSyncError):
            validate_branch("../main")
        with self.assertRaises(GitSyncError):
            validate_root_path("../../outside")
        with self.assertRaises(GitSyncError):
            validate_root_path(".git/hooks")


if __name__ == "__main__":
    unittest.main()
