import os
import sys
import tempfile
import unittest
from unittest import mock


path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, path)

from src.main.python.xianwen.config.settings import DEFAULT_SETTINGS, JSONConfigManager


class TestJSONConfigManager(unittest.TestCase):
    def test_default_profile_id_is_stable_for_example_file(self):
        self.assertEqual(DEFAULT_SETTINGS["llm"]["active_profile_id"], "default")
        self.assertEqual(DEFAULT_SETTINGS["llm"]["profiles"][0]["id"], "default")

    def test_switch_to_auto_download_clears_manual_model_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "settings.json")
            manager = JSONConfigManager(config_path=config_path)

            manager.update_section(
                "whisper",
                {
                    "model_source": "manual_path",
                    "model_path": "E:/models/faster-whisper/tiny",
                    "faster_whisper_model_path": "E:/legacy/model",
                },
            )
            manager.save_transcription_config({"model_source": "auto_download"})

            whisper = manager.get_whisper_config()
            self.assertEqual(whisper.model_source, "auto_download")
            self.assertIsNone(whisper.model_path)
            self.assertIsNone(whisper.faster_whisper_model_path)

    def test_database_url_environment_overrides_json_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "settings.json")
            manager = JSONConfigManager(config_path=config_path)
            manager.update_section("database", {"url": "sqlite:///from-settings.db"})

            with mock.patch.dict(
                os.environ,
                {"XIANWEN_DATABASE_URL": "postgresql+psycopg://env-user:placeholder@postgres:5432/envdb"},
                clear=False,
            ):
                database = manager.get_database_config()

            self.assertEqual(
                database.url,
                "postgresql+psycopg://env-user:placeholder@postgres:5432/envdb",
            )


if __name__ == "__main__":
    unittest.main()
