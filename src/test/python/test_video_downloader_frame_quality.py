import os
import sys
import unittest
import asyncio


path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, path)

from src.main.python.sheng_wen.downloader.video_downloader_worker import VideoDownloaderWorker


class TestVideoDownloaderFrameQuality(unittest.TestCase):
    def test_frame_snapshots_use_high_quality_video_format(self):
        worker = VideoDownloaderWorker(name="test-downloader")

        opts = worker._build_ydl_opts(
            quality="audio_only",
            progress_hook=lambda _: None,
            enable_frame_snapshots=True,
        )

        self.assertIn("bestvideo", opts["format"])
        self.assertNotIn("worstvideo", opts["format"])
        self.assertEqual(opts["merge_output_format"], "mp4")

    def test_ydl_opts_include_bilibili_sessdata_cookie_when_available(self):
        worker = VideoDownloaderWorker(name="test-downloader")

        opts = worker._build_ydl_opts(
            quality="audio_only",
            progress_hook=lambda _: None,
            enable_frame_snapshots=True,
            bilibili_sessdata="sess-value",
        )

        self.assertEqual(opts["http_headers"]["Cookie"], "SESSDATA=sess-value")

    def test_frame_source_download_uses_task_scoped_output_template(self):
        worker = VideoDownloaderWorker(name="test-downloader")

        outtmpl = worker._build_frame_source_outtmpl("task-123")

        self.assertIn("task-123", outtmpl)
        self.assertIn("%(id)s.%(ext)s", outtmpl)

    def test_ydl_opts_can_use_custom_output_template(self):
        worker = VideoDownloaderWorker(name="test-downloader")

        opts = worker._build_ydl_opts(
            quality="audio_only",
            progress_hook=lambda _: None,
            enable_frame_snapshots=True,
            output_template="temp/task-123_source_%(id)s.%(ext)s",
        )

        self.assertEqual(opts["outtmpl"], "temp/task-123_source_%(id)s.%(ext)s")

    def test_bilibili_subtitle_path_passes_high_quality_source_video_for_frames(self):
        captured_payloads = []

        class FakeSummaryWorker:
            async def add_task(self, payload):
                captured_payloads.append(payload)

        worker = VideoDownloaderWorker(name="test-downloader", summary_worker=FakeSummaryWorker())
        worker._try_extract_bilibili_subtitle = lambda video_url, sessdata: {
            "title": "视频标题",
            "duration": 120,
            "transcript": "000010这里是字幕\n",
            "language": "zh",
        }
        worker.is_task_cancelled = lambda task_id: False
        worker._download_source_video_for_frames = (
            lambda video_url, task_id, quality, bilibili_sessdata=None: "/tmp/high-quality-source.mp4"
        )

        def submit_coro(coro):
            if getattr(coro, "cr_code", None) and coro.cr_code.co_name == "add_task":
                asyncio.run(coro)
            else:
                coro.close()

        worker._submit_coro = submit_coro

        processed = worker._try_process_with_bilibili_subtitle(
            {
                "video_url": "https://www.bilibili.com/video/BV1234567890",
                "task_id": "task-123",
                "quality": "audio_only",
                "enable_frame_snapshots": True,
            }
        )

        self.assertTrue(processed)
        self.assertEqual(captured_payloads[0]["source_video_file"], "/tmp/high-quality-source.mp4")


if __name__ == "__main__":
    unittest.main()
