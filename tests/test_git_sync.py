import os
import subprocess
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from src.main.python.xianwen.db import TaskDB
from src.main.python.xianwen.git_sync import (
    GeneratedFile,
    GitSyncError,
    apply_managed_files,
    build_library_files,
    sync_library_to_git,
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

    def test_builds_human_readable_content_library_indexes_and_assets(self):
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
        (asset_dir / "unused.jpg").write_bytes(b"unused")
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

        content_dir = "内容/从感知到知识"
        document_path = f"{content_dir}/从感知到知识.md"
        transcript_path = f"{content_dir}/原始逐字稿.md"
        self.assertEqual(document_count, 1)
        self.assertIn(document_path, generated)
        self.assertIn(transcript_path, generated)
        content = generated[document_path].content.decode("utf-8")
        self.assertIn("# 从感知到知识", content)
        self.assertIn("assets/frames/frame.jpg", content)
        self.assertIn("[[原始逐字稿]]", content)
        self.assertNotIn("[000001] 原始转写", content)
        self.assertIn("[000001] 原始转写", generated[transcript_path].content.decode("utf-8"))
        self.assertIn("内容/从感知到知识/从感知到知识", generated["_索引.md"].content.decode("utf-8"))
        self.assertIn("藏经阁/经世/人工智能/_目录.md", generated)
        self.assertIn(
            "内容/从感知到知识/从感知到知识",
            generated["藏经阁/经世/人工智能/_目录.md"].content.decode("utf-8"),
        )
        self.assertIn(f"{content_dir}/assets/frames/frame.jpg", generated)
        self.assertNotIn(f"{content_dir}/assets/frames/unused.jpg", generated)

    def test_uses_original_article_body_name_and_keeps_metadata_minimal(self):
        task_id = "article-001"
        now = datetime.utcnow()
        asset_dir = self.root / "temp" / "task-assets" / task_id / "images"
        asset_dir.mkdir(parents=True)
        (asset_dir / "cover.jpg").write_bytes(b"cover")
        self.store.save_task(
            task_id,
            {
                "video_url": "https://mp.weixin.qq.com/s/example",
                "source_url": "https://mp.weixin.qq.com/s/example",
                "source_type": "wechat_article",
                "source_meta": '{"publish_time":"2026-08-01","account_name":"测试公众号"}',
                "status": "COMPLETED",
                "created_at": now,
                "latest_modified_at": now,
                "progress": 1.0,
                "title": "一篇原始文章",
                "author_name": "测试作者",
                "summary": "整理后的内容",
                "transcript": "原始正文\n\n![封面](/task-assets/article-001/images/cover.jpg)",
            },
        )

        generated, _ = build_library_files(self.store, project_root=self.root)

        main = generated["内容/一篇原始文章/一篇原始文章.md"].content.decode("utf-8")
        raw = generated["内容/一篇原始文章/原始正文.md"].content.decode("utf-8")
        self.assertIn('author: "测试作者"', main)
        self.assertIn('published_at: "2026-08-01"', main)
        self.assertIn("[[原始正文]]", main)
        self.assertIn("assets/images/cover.jpg", raw)
        self.assertIn("内容/一篇原始文章/assets/images/cover.jpg", generated)

    def test_disambiguates_duplicate_titles_and_reuses_published_directory_name(self):
        now = datetime.utcnow()
        for task_id in ("task-aaa11111", "task-bbb22222"):
            self.store.save_task(
                task_id,
                {
                    "video_url": f"https://example.com/{task_id}",
                    "source_type": "video",
                    "status": "COMPLETED",
                    "created_at": now,
                    "latest_modified_at": now,
                    "progress": 1.0,
                    "title": "同名内容",
                    "summary": "整理稿",
                    "transcript": "逐字稿",
                },
            )

        generated, _ = build_library_files(self.store, project_root=self.root)
        self.assertIn("内容/同名内容/同名内容.md", generated)
        self.assertIn("内容/同名内容__task-bbb/同名内容__task-bbb.md", generated)

        generated, _ = build_library_files(
            self.store,
            project_root=self.root,
            content_directory_names={"task-aaa11111": "首次发布标题"},
        )
        self.assertIn("内容/首次发布标题/首次发布标题.md", generated)

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

    def test_hidden_documents_are_removed_from_next_snapshot(self):
        now = datetime.utcnow()
        self.store.save_task(
            "manual-001",
            {
                "video_url": "manual://manual-001",
                "source_url": "",
                "source_type": "manual",
                "status": "COMPLETED",
                "created_at": now,
                "latest_modified_at": now,
                "progress": 1.0,
                "title": "手写文档",
                "summary": "",
                "transcript": "",
                "library_visible": True,
            },
        )
        generated, document_count = build_library_files(self.store, project_root=self.root)
        self.assertEqual(document_count, 1)
        self.assertIn("内容/手写文档/手写文档.md", generated)
        self.assertNotIn("内容/手写文档/原始逐字稿.md", generated)

        self.store.update_task("manual-001", {"library_visible": False})
        generated, document_count = build_library_files(self.store, project_root=self.root)
        self.assertEqual(document_count, 0)
        self.assertNotIn("内容/手写文档/手写文档.md", generated)

    def test_manifest_records_stable_content_directory_names(self):
        repository = self.root / "repository"
        repository.mkdir()
        generated = {
            "内容/原始标题/原始标题.md": GeneratedFile(
                b"content\n",
                task_id="task-1",
                content_directory="原始标题",
            )
        }

        apply_managed_files(repository, "先闻继学", generated)

        manifest = (repository / "先闻继学" / ".xianwen-manifest.json").read_text(encoding="utf-8")
        self.assertIn('"version": 2', manifest)
        self.assertIn('"task-1": "原始标题"', manifest)

    def test_sync_commits_and_pushes_human_readable_vault_to_git(self):
        remote = self.root / "remote.git"
        seed = self.root / "seed"
        subprocess.run(["git", "init", "--bare", "--initial-branch=main", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "init", "--initial-branch=main", str(seed)], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=seed, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=seed, check=True)
        (seed / "README.md").write_text("# Knowledge\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=seed, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=seed, check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=seed, check=True)
        subprocess.run(["git", "push", "-u", "origin", "main"], cwd=seed, check=True, capture_output=True)

        now = datetime.utcnow()
        self.store.save_task(
            "task-e2e",
            {
                "video_url": "https://example.com/video",
                "source_type": "video",
                "status": "COMPLETED",
                "created_at": now,
                "latest_modified_at": now,
                "progress": 1.0,
                "title": "真实 Git 归档",
                "summary": "整理稿",
                "transcript": "逐字稿",
            },
        )

        def fake_key(directory: Path, _: str) -> Path:
            key_path = directory / "deploy_key"
            key_path.write_text("test", encoding="utf-8")
            return key_path

        with (
            patch("src.main.python.xianwen.git_sync.validate_repository_url", side_effect=lambda value: value),
            patch("src.main.python.xianwen.git_sync.derive_public_key", return_value="ssh-ed25519 test"),
            patch("src.main.python.xianwen.git_sync._write_private_key", side_effect=fake_key),
        ):
            first = sync_library_to_git(
                self.store,
                repository_url=str(remote),
                branch="main",
                root_path="先闻继学",
                private_key="test",
                author_name="先闻继学",
                author_email="xianwen@example.com",
                include_transcript=True,
            )
            second = sync_library_to_git(
                self.store,
                repository_url=str(remote),
                branch="main",
                root_path="先闻继学",
                private_key="test",
                author_name="先闻继学",
                author_email="xianwen@example.com",
                include_transcript=True,
            )

        checkout = self.root / "checkout"
        subprocess.run(["git", "clone", "--branch", "main", str(remote), str(checkout)], check=True, capture_output=True)
        self.assertTrue(first["committed"])
        self.assertFalse(second["committed"])
        self.assertTrue((checkout / "先闻继学" / "内容" / "真实 Git 归档" / "真实 Git 归档.md").is_file())
        self.assertTrue((checkout / "先闻继学" / "藏经阁" / "_索引.md").is_file())

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
