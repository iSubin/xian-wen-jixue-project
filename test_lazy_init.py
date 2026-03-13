import os
import sys
import unittest


path = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, path)


def main() -> int:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromName("src.test.python.test_lazy_worker_manager"))
    suite.addTests(loader.loadTestsFromName("src.test.python.test_transcription_settings_manager"))

    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
