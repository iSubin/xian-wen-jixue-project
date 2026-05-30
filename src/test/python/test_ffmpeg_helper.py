import os
import sys
import unittest
from unittest.mock import patch


path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, path)

from src.main.python.sheng_wen.utils.ffmpeg_helper import FFmpegHelper


class TestFFmpegHelper(unittest.TestCase):
    def setUp(self):
        self._old_ffmpeg_path = FFmpegHelper._ffmpeg_path
        self._old_ffmpeg_dir = FFmpegHelper._ffmpeg_dir
        FFmpegHelper._ffmpeg_path = None
        FFmpegHelper._ffmpeg_dir = None

    def tearDown(self):
        FFmpegHelper._ffmpeg_path = self._old_ffmpeg_path
        FFmpegHelper._ffmpeg_dir = self._old_ffmpeg_dir

    @patch("src.main.python.sheng_wen.utils.ffmpeg_helper.shutil.which")
    @patch("src.main.python.sheng_wen.utils.ffmpeg_helper.os.path.isfile")
    def test_falls_back_to_system_ffmpeg_when_imageio_returns_nonexistent_command(self, mocked_isfile, mocked_which):
        mocked_isfile.return_value = False
        mocked_which.return_value = "/usr/local/bin/ffmpeg"

        ffmpeg_path = FFmpegHelper.get_ffmpeg_path()

        self.assertEqual(ffmpeg_path, "/usr/local/bin/ffmpeg")


if __name__ == "__main__":
    unittest.main()
