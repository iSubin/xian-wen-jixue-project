import os
import sys
import unittest


path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, path)

from src.main.python.xianwen.api import app


class TestTaskAssetsStaticMount(unittest.TestCase):
    def test_task_assets_static_route_is_mounted(self):
        mounted_paths = {getattr(route, "path", "") for route in app.routes}

        self.assertIn("/task-assets", mounted_paths)


if __name__ == "__main__":
    unittest.main()
