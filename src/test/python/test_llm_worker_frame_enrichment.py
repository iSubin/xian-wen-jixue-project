import os
import sys
import tempfile
import unittest
import asyncio


path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, path)

from src.main.python.xianwen.llm.llm import LLM, LLMConfig
from src.main.python.xianwen.llm.llm_worker import LLMWorker


class DummyLLM(LLM):
    async def response(self, messages, resp_callback, stream=True, timeout=60):
        resp_callback("unused")


class SequenceLLM(LLM):
    def __init__(self, responses):
        super().__init__(LLMConfig(base_url="", api_key="", model_id="dummy"))
        self.responses = list(responses)
        self.call_count = 0

    async def response(self, messages, resp_callback, stream=True, timeout=60):
        response = self.responses[self.call_count]
        self.call_count += 1
        resp_callback(response)


class HangingLLM(LLM):
    async def response(self, messages, resp_callback, stream=True, timeout=60):
        await asyncio.sleep(1)


class FastTimeoutLLMWorker(LLMWorker):
    def _standard_summary_timeout_sec(self) -> float:
        return 0.01


class TestLLMWorkerFrameEnrichment(unittest.TestCase):
    def test_enrich_summary_uses_video_file_from_payload(self):
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

            worker = LLMWorker(
                "test-llm-worker",
                DummyLLM(LLMConfig(base_url="", api_key="", model_id="dummy")),
                frame_assets_root=os.path.join(temp_dir, "task-assets"),
                frame_writer=fake_frame_writer,
            )

            enriched = worker._enrich_summary_with_frames(
                "这里需要图文说明（见 00:00:10）。",
                task_id="task-123",
                payload={"video_file": video_path},
            )

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], video_path)
        self.assertIn("/task-assets/task-123/frames/frame_000010.jpg", enriched)

    def test_enrich_summary_uses_transcript_fallback_when_summary_has_no_timestamps(self):
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

            worker = LLMWorker(
                "test-llm-worker",
                DummyLLM(LLMConfig(base_url="", api_key="", model_id="dummy")),
                frame_assets_root=os.path.join(temp_dir, "task-assets"),
                frame_writer=fake_frame_writer,
            )

            enriched = worker._enrich_summary_with_frames(
                "{{主题}}\n\n## 第一节\n\n正文。\n\n## 第二节\n\n正文。",
                task_id="task-123",
                payload={"source_video_file": video_path},
                transcript_text="000000开场\n000010第一段\n000050第二段\n000130第三段",
            )

        self.assertEqual([call[1] for call in calls], [10, 50])
        self.assertIn("/task-assets/task-123/frames/frame_000010.jpg", enriched)
        self.assertIn("/task-assets/task-123/frames/frame_000050.jpg", enriched)

    def test_standard_summary_retries_truncated_markdown(self):
        llm = SequenceLLM(
            [
                "{{市场修复不改下行趋势，量能萎缩与顶背离形态需警惕》\n\n## ",
                "{{市场修复反弹背后：警惕缩量反抽}}\n\n## 1. 市场整体表现\n\n"
                "这是一个足够完整的总结段落，用于验证短输出会触发重试，"
                "而第二次完整输出会被正常接收。"
            ]
        )
        worker = LLMWorker("test-llm-worker", llm)
        worker.system_prompt = "system"

        summary, topic = asyncio.run(
            worker._run_standard_summary(
                "000000第一句\n000010第二句\n" * 40,
                task_id=None,
            )
        )

        self.assertEqual(llm.call_count, 2)
        self.assertIn("## 1. 市场整体表现", summary)
        self.assertEqual(topic, "市场修复反弹背后：警惕缩量反抽")

    def test_standard_summary_raises_when_all_attempts_are_truncated(self):
        llm = SequenceLLM(
            [
                "{{市场修复不改下行趋势，量能萎缩与顶背离形态需警惕》\n\n## ",
                "{{仍然不完整}}\n\n## ",
                "{{还是不完整}}\n\n## ",
            ]
        )
        worker = LLMWorker("test-llm-worker", llm)
        worker.system_prompt = "system"

        with self.assertRaisesRegex(RuntimeError, "LLM 总结输出疑似截断"):
            asyncio.run(
                worker._run_standard_summary(
                    "000000第一句\n000010第二句\n" * 40,
                    task_id=None,
                )
            )

    def test_standard_summary_call_times_out_when_llm_hangs(self):
        worker = FastTimeoutLLMWorker(
            "test-llm-worker",
            HangingLLM(LLMConfig(base_url="", api_key="", model_id="dummy")),
        )
        worker.system_prompt = "system"

        with self.assertRaisesRegex(RuntimeError, "LLM 请求超时"):
            asyncio.run(worker._call_standard_summary_once("000000第一句", task_id=None))


if __name__ == "__main__":
    unittest.main()
