import importlib.util
import os
import sys
import unittest


path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, path)


class TestAppStaticMounts(unittest.TestCase):
    def test_built_frontend_has_index_and_assets(self):
        dist_dir = os.path.join(path, "frontend", "dist")
        assets_dir = os.path.join(dist_dir, "assets")

        self.assertTrue(os.path.isfile(os.path.join(dist_dir, "index.html")))
        self.assertTrue(os.path.isdir(assets_dir))
        with os.scandir(assets_dir) as entries:
            self.assertTrue(any(entries))

    def test_runtime_app_mounts_task_assets(self):
        module_path = os.path.join(path, "xianwen-app.py")
        spec = importlib.util.spec_from_file_location("xianwen_app_for_test", module_path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)

        mounted_paths = {getattr(route, "path", "") for route in module.app.routes}

        self.assertIn("/task-assets", mounted_paths)
        self.assertIn("/assets", mounted_paths)


if __name__ == "__main__":
    unittest.main()
