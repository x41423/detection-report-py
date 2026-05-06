import logging
import tempfile
import unittest
from pathlib import Path

from shared.logging_utils import configure_application_logging
from shared.project_paths import ProjectPaths


class ProjectPathsTests(unittest.TestCase):
    def test_for_root_builds_expected_layout(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            paths = ProjectPaths.for_root(root)

            self.assertEqual(paths.root, root.resolve())
            self.assertEqual(paths.config_file, root / "config" / "app.json")
            self.assertEqual(paths.legacy_root_config_file, root / "config.json")
            self.assertEqual(paths.database_file, root / "data" / "app.db")
            self.assertEqual(paths.legacy_database_file, root / "app" / "data" / "app.db")
            self.assertEqual(paths.history_rates_file, root / "data" / "pesticide" / "history_rates.json")
            self.assertEqual(paths.legacy_history_rates_file, root / "history_rates.json")
            self.assertEqual(paths.runtime_dir, root / ".runtime")

    def test_log_file_creates_logs_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = ProjectPaths.for_root(Path(tmpdir))

            log_path = paths.log_file("backend.log")

            self.assertEqual(log_path, Path(tmpdir) / "logs" / "backend.log")
            self.assertTrue(log_path.parent.exists())


class LoggingUtilsTests(unittest.TestCase):
    def test_configure_application_logging_writes_to_logs_directory(self):
        root_logger = logging.getLogger()
        previous_handlers = root_logger.handlers[:]
        previous_level = root_logger.level
        temp_dir = tempfile.TemporaryDirectory()

        try:
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
                handler.close()

            paths = ProjectPaths.for_root(Path(temp_dir.name))
            log_path = configure_application_logging(
                "desktop.log",
                paths=paths,
                force=False,
            )
            logging.info("hello from tests")

            for handler in logging.getLogger().handlers:
                handler.flush()

            self.assertTrue(log_path.exists())
            self.assertIn("hello from tests", log_path.read_text(encoding="utf-8"))
        finally:
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
                handler.close()
            root_logger.setLevel(previous_level)
            for handler in previous_handlers:
                root_logger.addHandler(handler)
            temp_dir.cleanup()
