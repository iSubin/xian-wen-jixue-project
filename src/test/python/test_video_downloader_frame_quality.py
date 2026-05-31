import os
import sys
import unittest
import asyncio
import tempfile
from unittest.mock import patch


path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, path)

from src.main.python.sheng_wen.downloader.homeway_resolver import HomewayResolvedVideo
from src.main.python.sheng_wen.downloader.xiaoet_resolver import XiaoetResolvedVideo
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

    def test_ydl_opts_include_bilibili_cookiefile_when_available(self):
        worker = VideoDownloaderWorker(name="test-downloader")

        fd, cookie_path = tempfile.mkstemp(prefix="shengwen-test-", suffix=".cookies.txt")
        os.close(fd)
        try:
            opts = worker._build_ydl_opts(
                quality="audio_only",
                progress_hook=lambda _: None,
                enable_frame_snapshots=True,
                bilibili_sessdata="sess-value",
                bilibili_cookiefile=cookie_path,
            )

            self.assertEqual(opts["cookiefile"], cookie_path)
            self.assertNotIn("Cookie", opts.get("http_headers", {}))
        finally:
            os.remove(cookie_path)

    def test_writes_bilibili_sessdata_as_netscape_cookie_file(self):
        worker = VideoDownloaderWorker(name="test-downloader")

        cookie_path = worker._write_bilibili_sessdata_cookie_file("sess-value")

        try:
            with open(cookie_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn(".bilibili.com\tTRUE\t/\tFALSE\t", content)
            self.assertIn("\tSESSDATA\tsess-value\n", content)
        finally:
            os.remove(cookie_path)

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

    def test_normalizes_bilibili_bare_domain_to_www(self):
        worker = VideoDownloaderWorker(name="test-downloader")

        normalized = worker._normalize_bilibili_url_for_download(
            "https://bilibili.com/video/BV1YZGB6cEBN/?spm_id_from=333.40164.0.0"
        )

        self.assertEqual(
            normalized,
            "https://www.bilibili.com/video/BV1YZGB6cEBN/?spm_id_from=333.40164.0.0",
        )

    def test_download_path_uses_normalized_bilibili_url_for_ytdlp(self):
        worker = VideoDownloaderWorker(name="test-downloader")
        worker._try_process_with_bilibili_subtitle = lambda payload: False
        worker._validate_downloaded_media_duration = lambda **kwargs: None
        captured_urls = []

        class FakeYDL:
            def __init__(self, opts):
                self.opts = opts

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def extract_info(self, video_url, download=True):
                captured_urls.append(video_url)
                return {"id": "BV1YZGB6cEBN", "duration": 120, "title": "title"}

            def prepare_filename(self, info_dict):
                return "/tmp/video.mp4"

        with patch(
            "src.main.python.sheng_wen.downloader.video_downloader_worker.yt_dlp.YoutubeDL",
            FakeYDL,
        ):
            worker.process_task(
                {
                    "video_url": "https://bilibili.com/video/BV1YZGB6cEBN/?spm_id_from=333.40164.0.0",
                    "quality": "best",
                    "enable_frame_snapshots": False,
                }
            )

        self.assertEqual(
            captured_urls,
            ["https://www.bilibili.com/video/BV1YZGB6cEBN/?spm_id_from=333.40164.0.0"],
        )

    def test_download_path_resolves_homeway_graphic_video_url_for_ytdlp(self):
        worker = VideoDownloaderWorker(name="test-downloader")
        worker._try_process_with_bilibili_subtitle = lambda payload: False
        worker._validate_downloaded_media_duration = lambda **kwargs: None
        captured_urls = []

        class FakeYDL:
            def __init__(self, opts):
                self.opts = opts

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def extract_info(self, video_url, download=True):
                captured_urls.append(video_url)
                return {"id": "homeway-hls", "duration": 465, "title": "投研大师视频"}

            def prepare_filename(self, info_dict):
                return "/tmp/homeway.mp4"

        with patch(
            "src.main.python.sheng_wen.downloader.video_downloader_worker.resolve_homeway_graphic_video",
            return_value=HomewayResolvedVideo(
                media_url="https://cdn.example.com/video.m3u8?token=media-token",
                title="投研大师视频",
                source_url="https://tyds.homeway.com.cn/#/GraphicVideo?key=5269",
                vhall_id="260368304",
            ),
        ), patch(
            "src.main.python.sheng_wen.downloader.video_downloader_worker.yt_dlp.YoutubeDL",
            FakeYDL,
        ):
            worker.process_task(
                {
                    "video_url": "https://tyds.homeway.com.cn/#/GraphicVideo?key=5269",
                    "quality": "best",
                    "enable_frame_snapshots": False,
                }
            )

        self.assertEqual(
            captured_urls,
            ["https://cdn.example.com/video.m3u8?token=media-token"],
        )

    def test_download_path_resolves_xiaoet_video_url_for_ytdlp(self):
        worker = VideoDownloaderWorker(name="test-downloader")
        worker._try_process_with_bilibili_subtitle = lambda payload: False
        worker._validate_downloaded_media_duration = lambda **kwargs: None
        captured_urls = []

        class FakeYDL:
            def __init__(self, opts):
                self.opts = opts

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def extract_info(self, video_url, download=True):
                captured_urls.append(video_url)
                return {"id": "xiaoet-hls", "duration": 1939, "title": "小鹅通视频"}

            def prepare_filename(self, info_dict):
                return "/tmp/xiaoet.mp4"

        with patch(
            "src.main.python.sheng_wen.downloader.video_downloader_worker.resolve_xiaoet_video",
            return_value=XiaoetResolvedVideo(
                media_url="https://vod.example.com/video.m3u8?sign=s&t=t&us=u",
                title="小鹅通视频",
                source_url="https://appexpqpqic7617.h5.xiaoeknow.com/p/course/video/v_abc?product_id=course_1",
                resource_id="v_abc",
                product_id="course_1",
                quality="1080p_hls",
            ),
        ), patch(
            "src.main.python.sheng_wen.downloader.video_downloader_worker.yt_dlp.YoutubeDL",
            FakeYDL,
        ):
            worker.process_task(
                {
                    "video_url": "https://appexpqpqic7617.h5.xiaoeknow.com/p/course/video/v_abc?product_id=course_1",
                    "quality": "best",
                    "enable_frame_snapshots": False,
                }
            )

        self.assertEqual(
            captured_urls,
            ["https://vod.example.com/video.m3u8?sign=s&t=t&us=u"],
        )

    def test_xiaoet_resolved_title_is_not_overwritten_by_hls_filename(self):
        captured_updates = []

        async def fake_update_and_notify(task_id, updates):
            captured_updates.append((task_id, updates))
            return None

        def submit_coro(coro):
            asyncio.run(coro)

        worker = VideoDownloaderWorker(name="test-downloader")
        worker._submit_coro = submit_coro
        worker._try_process_with_bilibili_subtitle = lambda payload: False
        worker._validate_downloaded_media_duration = lambda **kwargs: None
        worker.is_task_cancelled = lambda task_id: False

        class FakeYDL:
            def __init__(self, opts):
                self.opts = opts

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def extract_info(self, video_url, download=True):
                return {"id": "v.f421220", "duration": 1939, "title": "v.f421220"}

            def prepare_filename(self, info_dict):
                return "/tmp/xiaoet.mp4"

        with patch(
            "src.main.python.sheng_wen.downloader.video_downloader_worker.resolve_xiaoet_video",
            return_value=XiaoetResolvedVideo(
                media_url="https://vod.example.com/video.m3u8?sign=s&t=t&us=u",
                title="第15课.mp4",
                source_url="https://appexpqpqic7617.h5.xiaoeknow.com/p/course/video/v_abc?product_id=course_1",
                resource_id="v_abc",
                product_id="course_1",
                quality="720p_hls",
            ),
        ), patch(
            "src.main.python.sheng_wen.downloader.video_downloader_worker.yt_dlp.YoutubeDL",
            FakeYDL,
        ), patch(
            "src.main.python.sheng_wen.task_updater.update_and_notify",
            fake_update_and_notify,
        ):
            worker.process_task(
                {
                    "task_id": "task-xiaoet",
                    "video_url": "https://appexpqpqic7617.h5.xiaoeknow.com/p/course/video/v_abc?product_id=course_1",
                    "quality": "best",
                    "enable_frame_snapshots": False,
                }
            )

        title_updates = [updates for _task_id, updates in captured_updates if "title" in updates]
        self.assertEqual(title_updates[-1]["title"], "第15课.mp4")

    def test_rejects_downloaded_media_when_duration_is_much_shorter_than_metadata(self):
        worker = VideoDownloaderWorker(name="test-downloader")
        worker._probe_downloaded_media_duration = lambda _: 960.0

        with self.assertRaisesRegex(RuntimeError, "下载不完整"):
            worker._validate_downloaded_media_duration(
                video_path="/tmp/partial.mp4",
                expected_duration=2156.831,
                video_url="https://www.bilibili.com/video/BV1YZGB6cEBN/",
            )

    def test_accepts_downloaded_media_when_duration_matches_metadata(self):
        worker = VideoDownloaderWorker(name="test-downloader")
        worker._probe_downloaded_media_duration = lambda _: 2154.0

        worker._validate_downloaded_media_duration(
            video_path="/tmp/full.mp4",
            expected_duration=2156.831,
            video_url="https://www.bilibili.com/video/BV1YZGB6cEBN/",
        )

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
