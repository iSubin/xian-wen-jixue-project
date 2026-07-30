"""测试 ChunkedSummarizer 的 on_chunk_delta 回调。"""

import asyncio
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# 将项目根目录添加到 Python 路径
path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, path)

from src.main.python.xianwen.llm.llm import LLMError
from src.main.python.xianwen.summarization.chunked_summarizer import ChunkedSummarizer


def _make_summarizer():
    """构造一个最小可用的 ChunkedSummarizer 实例。"""
    llm_client = MagicMock()
    config = {
        "llm_client": llm_client,
        "chunk_system_prompt": "You are a summarizer.",
        "chunk_target_duration_sec": 300,
        "chunk_min_duration_sec": 60,
        "chunk_max_duration_sec": 600,
        "boundary_jump_sec": 5,
        "prev_tail_timestamp_lines_m": 3,
        "prev_summary_tail_chars_j": 200,
        "llm_call_retry_max": 1,
        "max_agent_value_chars": 2000,
    }
    return ChunkedSummarizer(**config)


def _stub_transcript():
    """返回一段足够长、会被分块的最小文本（HHMMSS 时间戳格式）。"""
    lines = []
    for i in range(60):
        total_sec = i * 30
        hh = total_sec // 3600
        mm = (total_sec % 3600) // 60
        ss = total_sec % 60
        lines.append(f"{hh:02d}{mm:02d}{ss:02d} 这是一个测试句子编号{i}。")
    return "\n".join(lines)


class TestOnChunkDeltaCallback(unittest.TestCase):
    """测试 on_chunk_delta 回调在 _call_llm_once 中的行为。"""

    def test_delta_receives_each_raw_token(self):
        """on_chunk_delta 应收到每个原始 token 字符串。"""
        summarizer = _make_summarizer()
        received = []

        async def fake_response(messages, resp_callback):
            for token in ["Hello", " ", "World", "!"]:
                resp_callback(token)

        summarizer._llm_client.response = AsyncMock(side_effect=fake_response)

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(
                summarizer._call_llm_once("test prompt", on_chunk_delta=received.append)
            )
        finally:
            loop.close()

        self.assertEqual(received, ["Hello", " ", "World", "!"])

    def test_delta_and_on_partial_coexist(self):
        """on_chunk_delta 和 on_partial 应共存互不干扰。"""
        summarizer = _make_summarizer()
        deltas = []
        partials = []

        async def fake_response(messages, resp_callback):
            for token in ["A", "B", "C", "D", "E"]:
                resp_callback(token)

        summarizer._llm_client.response = AsyncMock(side_effect=fake_response)

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(
                summarizer._call_llm_once(
                    "test prompt",
                    on_partial=partials.append,
                    on_chunk_delta=deltas.append,
                )
            )
        finally:
            loop.close()

        # delta 收到每个 token
        self.assertEqual(deltas, ["A", "B", "C", "D", "E"])
        # on_partial 受 0.5s 防抖限制，触发次数 <= token 数
        # 关键：两者互不影响，各自独立工作
        self.assertTrue(len(partials) <= 5)
        for p in partials:
            self.assertIsInstance(p, str)

    def test_delta_none_no_side_effects(self):
        """on_chunk_delta=None 时不应有任何副作用。"""
        summarizer = _make_summarizer()

        async def fake_response(messages, resp_callback):
            for token in ["X", "Y"]:
                resp_callback(token)

        summarizer._llm_client.response = AsyncMock(side_effect=fake_response)

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                summarizer._call_llm_once("test prompt", on_chunk_delta=None)
            )
        finally:
            loop.close()

        self.assertEqual(result, "XY")

    def test_delta_exception_does_not_break_stream(self):
        """on_chunk_delta 抛异常不应中断 LLM 流。"""
        summarizer = _make_summarizer()

        def bad_delta(chunk):
            if chunk == "B":
                raise RuntimeError("delta callback error")

        async def fake_response(messages, resp_callback):
            for token in ["A", "B", "C"]:
                resp_callback(token)

        summarizer._llm_client.response = AsyncMock(side_effect=fake_response)

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                summarizer._call_llm_once("test prompt", on_chunk_delta=bad_delta)
            )
        finally:
            loop.close()

        # B 的 delta 失败，但 LLM 流不应中断
        self.assertEqual(result, "ABC")

    def test_delta_skips_empty_string(self):
        """空字符串 token 不应触发 on_chunk_delta。"""
        summarizer = _make_summarizer()
        received = []

        async def fake_response(messages, resp_callback):
            for token in ["A", "", "B"]:
                resp_callback(token)

        summarizer._llm_client.response = AsyncMock(side_effect=fake_response)

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(
                summarizer._call_llm_once("test prompt", on_chunk_delta=received.append)
            )
        finally:
            loop.close()

        self.assertEqual(received, ["A", "B"])


class TestCallLlmWithRetryDeltaPassthrough(unittest.TestCase):
    """测试 _call_llm_with_retry 正确透传 on_chunk_delta。"""

    def test_retry_passes_delta_through(self):
        """_call_llm_with_retry 应将 on_chunk_delta 透传到 _call_llm_once。"""
        summarizer = _make_summarizer()
        received = []

        async def fake_response(messages, resp_callback):
            for token in ["Hello"]:
                resp_callback(token)

        summarizer._llm_client.response = AsyncMock(side_effect=fake_response)

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                summarizer._call_llm_with_retry("test prompt", on_chunk_delta=received.append)
            )
        finally:
            loop.close()

        self.assertEqual(received, ["Hello"])
        self.assertEqual(result, "Hello")


class TestSummarizeDeltaIntegration(unittest.TestCase):
    """测试 summarize() 集成 on_chunk_delta。"""

    def test_summarize_passes_delta_to_llm(self):
        """summarize() 应将 on_chunk_delta 传到 LLM 调用层。"""
        summarizer = _make_summarizer()
        received_deltas = []

        async def fake_response(messages, resp_callback):
            for token in ["Chunk", " result"]:
                resp_callback(token)

        summarizer._llm_client.response = AsyncMock(side_effect=fake_response)

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                summarizer.summarize(
                    transcript_text=_stub_transcript(),
                    on_chunk_delta=received_deltas.append,
                )
            )
        finally:
            loop.close()

        # 应收到 LLM 输出的每个 token（每个 chunk 都会触发 delta）
        # 转录被分成多个 chunk，每个 chunk 的 delta 为 ["Chunk", " result"]
        chunk_count = result.chunk_total
        expected = ["Chunk", " result"] * chunk_count
        self.assertEqual(received_deltas, expected)


if __name__ == "__main__":
    unittest.main()
