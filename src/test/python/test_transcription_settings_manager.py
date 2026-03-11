import os
import sys
import unittest
from unittest.mock import patch


path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, path)

from src.main.python.sheng_wen.transcriber.settings_manager import TranscriptionSettingsManager


class TestTranscriptionSettingsManager(unittest.TestCase):
    def test_toggle_bilibili_subtitle_fetch(self):
        manager = TranscriptionSettingsManager(initial_device="cpu", model_size="tiny")

        original = manager.get_settings()
        self.assertTrue(original["enable_bilibili_subtitle_fetch"])

        updated = manager.update_settings(enable_bilibili_subtitle_fetch=False)
        self.assertFalse(updated["enable_bilibili_subtitle_fetch"])

        reverted = manager.update_settings(enable_bilibili_subtitle_fetch=True)
        self.assertTrue(reverted["enable_bilibili_subtitle_fetch"])

    def test_reject_empty_update(self):
        manager = TranscriptionSettingsManager(initial_device="cpu", model_size="tiny")
        with self.assertRaises(ValueError):
            manager.update_settings()

    def test_bilibili_cookie_priority(self):
        with patch.dict(os.environ, {"BILIBILI_SESSDATA": "env_cookie_123456"}, clear=False):
            manager = TranscriptionSettingsManager(initial_device="cpu", model_size="tiny")

            settings = manager.get_settings()
            self.assertTrue(settings["has_bilibili_sessdata"])
            self.assertEqual(settings["bilibili_cookie_source"], "env")
            self.assertIn("****", settings["bilibili_sessdata_masked"])

            manager.update_settings(bilibili_sessdata="global_cookie_abcdef")
            settings = manager.get_settings()
            self.assertEqual(settings["bilibili_cookie_source"], "global")

            value, source = manager.resolve_bilibili_sessdata("task_cookie_xyz")
            self.assertEqual(source, "task")
            self.assertEqual(value, "task_cookie_xyz")


if __name__ == "__main__":
    unittest.main()

