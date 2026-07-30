import os
import sys
import tempfile
import unittest


path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, path)

from src.main.python.xianwen.frame_enricher import (
    enrich_summary_with_video_frames,
    select_frame_candidates,
    select_transcript_frame_candidates,
)


class TestFrameEnricher(unittest.TestCase):
    def test_select_frame_candidates_deduplicates_and_keeps_spacing(self):
        summary = "\n".join(
            [
                "第一段包含关键画面（见 00:00:10）。",
                "重复时间戳不应重复抽图（见 00:00:10）。",
                "太近的时间戳也应跳过（见 00:00:25）。",
                "足够远的时间戳应保留（见 00:01:00）。",
                "超过上限的时间戳不应保留（见 00:02:00）。",
            ]
        )

        candidates = select_frame_candidates(summary, max_frames=2, min_interval_sec=30)

        self.assertEqual([candidate.seconds for candidate in candidates], [10, 60])
        self.assertEqual([candidate.label for candidate in candidates], ["00:00:10", "00:01:00"])

    def test_enrich_summary_inserts_frame_markdown_after_timestamp_lines(self):
        calls = []

        def fake_frame_writer(video_path: str, seconds: int, output_path: str):
            calls.append((video_path, seconds, output_path))
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(b"fake-jpeg")

        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = os.path.join(temp_dir, "source.mp4")
            with open(video_path, "wb") as f:
                f.write(b"fake-video")

            summary = "## 1. 主题\n\n这里讲到核心页面（见 00:00:10）。\n\n下一段继续。"

            enriched = enrich_summary_with_video_frames(
                summary,
                task_id="task-123",
                video_path=video_path,
                assets_root=os.path.join(temp_dir, "task-assets"),
                frame_writer=fake_frame_writer,
                max_frames=3,
                min_interval_sec=30,
            )

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1], 10)
        self.assertIn("这里讲到核心页面（见 00:00:10）。", enriched)
        self.assertIn(
            "![关键画面 00:00:10](/task-assets/task-123/frames/frame_000010.jpg)",
            enriched,
        )
        self.assertLess(
            enriched.index("这里讲到核心页面（见 00:00:10）。"),
            enriched.index("![关键画面 00:00:10]"),
        )

    def test_select_transcript_frame_candidates_samples_across_transcript(self):
        transcript = "\n".join(
            [
                "000000开场",
                "000010第一段",
                "000040第二段",
                "000110第三段",
                "000150第四段",
                "000230收尾",
            ]
        )

        candidates = select_transcript_frame_candidates(
            transcript,
            max_frames=3,
            min_interval_sec=30,
            preferred_count=3,
        )

        self.assertEqual([candidate.seconds for candidate in candidates], [10, 70, 110])
        self.assertEqual([candidate.label for candidate in candidates], ["00:00:10", "00:01:10", "00:01:50"])

    def test_enrich_summary_uses_transcript_timestamps_when_summary_has_no_marks(self):
        calls = []

        def fake_frame_writer(video_path: str, seconds: int, output_path: str):
            calls.append((video_path, seconds, output_path))
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(b"fake-jpeg")

        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = os.path.join(temp_dir, "source.mp4")
            with open(video_path, "wb") as f:
                f.write(b"fake-video")

            summary = "\n".join(
                [
                    "{{主题}}",
                    "",
                    "## 市场概况",
                    "",
                    "这里没有时间标记。",
                    "",
                    "## 操作建议",
                    "",
                    "这里也没有时间标记。",
                ]
            )
            transcript = "\n".join(
                [
                    "000000开场",
                    "000010第一段",
                    "000040第二段",
                    "000110第三段",
                    "000150第四段",
                ]
            )

            enriched = enrich_summary_with_video_frames(
                summary,
                task_id="task-123",
                video_path=video_path,
                transcript_text=transcript,
                assets_root=os.path.join(temp_dir, "task-assets"),
                frame_writer=fake_frame_writer,
                max_frames=6,
                min_interval_sec=30,
            )

        self.assertEqual([call[1] for call in calls], [10, 70])
        self.assertIn("## 市场概况\n\n![关键画面 00:00:10]", enriched)
        self.assertIn("## 操作建议\n\n![关键画面 00:01:10]", enriched)

    def test_enrich_summary_supplements_sparse_summary_timestamps_from_transcript(self):
        calls = []

        def fake_frame_writer(video_path: str, seconds: int, output_path: str):
            calls.append((video_path, seconds, output_path))
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(b"fake-jpeg")

        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = os.path.join(temp_dir, "source.mp4")
            with open(video_path, "wb") as f:
                f.write(b"fake-video")

            summary = "\n".join(
                [
                    "{{主题}}",
                    "",
                    "## 第一节",
                    "",
                    "正文。",
                    "",
                    "## 第二节",
                    "",
                    "正文。",
                    "",
                    "> 结尾标记（见 00:03:52）",
                ]
            )
            transcript = "\n".join(
                [
                    "000000开场",
                    "000010第一段",
                    "000050第二段",
                    "000130第三段",
                    "000210第四段",
                    "000352结尾",
                ]
            )

            enriched = enrich_summary_with_video_frames(
                summary,
                task_id="task-123",
                video_path=video_path,
                transcript_text=transcript,
                assets_root=os.path.join(temp_dir, "task-assets"),
                frame_writer=fake_frame_writer,
                max_frames=6,
                min_interval_sec=30,
            )

        self.assertEqual([call[1] for call in calls], [232, 50, 130])
        self.assertIn("## 第一节\n\n![关键画面 00:00:50]", enriched)
        self.assertIn("## 第二节\n\n![关键画面 00:02:10]", enriched)
        self.assertIn("> 结尾标记（见 00:03:52）\n\n![关键画面 00:03:52]", enriched)

    def test_enrich_summary_returns_original_when_video_missing(self):
        summary = "这里没有可用视频，但有时间戳（见 00:00:10）。"

        enriched = enrich_summary_with_video_frames(
            summary,
            task_id="task-123",
            video_path="/path/that/does/not/exist.mp4",
        )

        self.assertEqual(enriched, summary)


if __name__ == "__main__":
    unittest.main()
