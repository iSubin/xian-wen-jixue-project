"""测试 notify_summary_delta 和双通道更新机制。"""

import json
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# 将项目根目录添加到 Python 路径
path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, path)


class TestNotifySummaryDelta(unittest.TestCase):
    """测试高频增量文本广播函数。"""

    @patch("src.main.python.sheng_wen.api.manager")
    def test_delta_message_format_basic(self, mock_manager):
        """测试基本 delta 消息格式。"""
        import asyncio
        from src.main.python.sheng_wen.api import notify_summary_delta

        mock_manager.broadcast = AsyncMock()

        asyncio.get_event_loop().run_until_complete(
            notify_summary_delta("task-123", delta="Hello")
        )

        mock_manager.broadcast.assert_called_once()
        msg = json.loads(mock_manager.broadcast.call_args[0][0])
        self.assertEqual(msg["type"], "summary_delta")
        self.assertEqual(msg["task_id"], "task-123")
        self.assertEqual(msg["delta"], "Hello")
        self.assertNotIn("chunk_done", msg)
        self.assertNotIn("chunk_total", msg)

    @patch("src.main.python.sheng_wen.api.manager")
    def test_delta_message_with_chunk_metadata(self, mock_manager):
        """测试包含 chunk 元数据的 delta 消息。"""
        import asyncio
        from src.main.python.sheng_wen.api import notify_summary_delta

        mock_manager.broadcast = AsyncMock()

        asyncio.get_event_loop().run_until_complete(
            notify_summary_delta("task-456", delta="World", chunk_done=2, chunk_total=5)
        )

        msg = json.loads(mock_manager.broadcast.call_args[0][0])
        self.assertEqual(msg["chunk_done"], 2)
        self.assertEqual(msg["chunk_total"], 5)

    @patch("src.main.python.sheng_wen.api.manager")
    def test_delta_does_not_write_db(self, mock_manager):
        """测试 delta 通道不调用 db.update_task。"""
        import asyncio
        from src.main.python.sheng_wen.api import notify_summary_delta

        mock_manager.broadcast = AsyncMock()

        with patch("src.main.python.sheng_wen.db.db") as mock_db:
            asyncio.get_event_loop().run_until_complete(
                notify_summary_delta("task-789", delta="test")
            )
            mock_db.update_task.assert_not_called()
            mock_db.get_task.assert_not_called()

    @patch("src.main.python.sheng_wen.api.manager")
    def test_delta_partial_chunk_metadata(self, mock_manager):
        """测试只传 chunk_done 不传 chunk_total 的情况。"""
        import asyncio
        from src.main.python.sheng_wen.api import notify_summary_delta

        mock_manager.broadcast = AsyncMock()

        asyncio.get_event_loop().run_until_complete(
            notify_summary_delta("task-000", delta="x", chunk_done=1)
        )

        msg = json.loads(mock_manager.broadcast.call_args[0][0])
        self.assertEqual(msg["chunk_done"], 1)
        self.assertNotIn("chunk_total", msg)


class TestUpdateAndNotifyUnaffected(unittest.TestCase):
    """测试低频通道 update_and_notify 不受 delta 通道影响。"""

    @patch("src.main.python.sheng_wen.api.manager")
    def test_update_and_notify_still_writes_db(self, mock_manager):
        """测试 update_and_notify 仍然写入 DB。"""
        import asyncio
        from src.main.python.sheng_wen.task_updater import update_and_notify

        mock_manager.broadcast = AsyncMock()

        with patch("src.main.python.sheng_wen.db.db") as mock_db:
            mock_db.get_task.return_value = {"status": "PENDING"}
            mock_db.update_task.return_value = {
                "id": "task-1",
                "status": "SUMMARIZING",
                "summary": "test",
            }

            asyncio.get_event_loop().run_until_complete(
                update_and_notify("task-1", {"status": "SUMMARIZING", "summary": "test"})
            )

            mock_db.update_task.assert_called_once_with(
                "task-1", {"status": "SUMMARIZING", "summary": "test"}
            )

    @patch("src.main.python.sheng_wen.api.manager")
    def test_update_and_notify_broadcasts_task_update(self, mock_manager):
        """测试 update_and_notify 广播 task_update 类型（非 summary_delta）。"""
        import asyncio
        from src.main.python.sheng_wen.task_updater import update_and_notify

        mock_manager.broadcast = AsyncMock()

        with patch("src.main.python.sheng_wen.db.db") as mock_db:
            mock_db.get_task.return_value = {"status": "PENDING"}
            mock_db.update_task.return_value = {
                "id": "task-2",
                "status": "SUMMARIZING",
                "summary": "hello",
            }

            asyncio.get_event_loop().run_until_complete(
                update_and_notify("task-2", {"status": "SUMMARIZING", "summary": "hello"})
            )

            msg = json.loads(mock_manager.broadcast.call_args[0][0])
            self.assertEqual(msg["type"], "task_update")
            self.assertNotEqual(msg["type"], "summary_delta")


if __name__ == "__main__":
    unittest.main()
